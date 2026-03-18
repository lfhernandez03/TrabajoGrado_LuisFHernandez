from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter
import asyncio
import logging
from time import perf_counter
from uuid import uuid4

from pydantic import BaseModel

from app.application.use_cases.query_history import QueryHistoryUseCase
from app.application.use_cases.recommendation_adaptive_weights import adapt_scoring_weights
from app.application.use_cases.recommendation_components import (
    build_query_attempts as rc_build_query_attempts,
    build_rdf_context as rc_build_rdf_context,
    build_sparql_query as rc_build_sparql_query,
    fetch_fuseki_candidates as rc_fetch_fuseki_candidates,
    parse_optional_float,
    parse_optional_int,
)
from app.application.use_cases.recommendation_metrics import RecommendationMetricsUseCase
from app.application.use_cases.recommendation_ranking import (
    rank_fuseki_movies,
    score_network_cold_start_movies,
)
from app.application.use_cases.recommendation_response import (
    build_context_extracted,
    build_context_summary,
    build_debug_payload,
    build_recommendation_response,
)
from app.application.use_cases.recommendation_signals import RecommendationSignalService
from app.application.use_cases.user_favorites import UserFavoritesUseCase
from app.core.fuseki_client import (
    FusekiQueryError,
    copy_graph_to_user_history,
    execute_select_query,
    get_user_context_history,
    user_history_graph_exists,
)
from app.core.ontology_query_builder import (
    build_cross_ontology_sparql,
    build_cross_ontology_sparql_from_signals,
    delete_context_snapshot,
    inject_context_snapshot,
)
from app.domain.entities.query_context import QueryContext
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort
from app.domain.entities.query_history import QueryHistory
from app.domain.entities.recommendation_metric import RecommendationMetric

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weight defaults (can be updated via update_scoring_weights_from_metrics)
# ---------------------------------------------------------------------------

_DEFAULT_SCORING_WEIGHTS: dict[str, float] = {
    "rating": 0.58,
    "degree": 0.42,
    "freshness": 0.08,
    "novelty": 0.0,
    "genre_bonus": 0.15,
    "genre_mismatch_penalty": 0.03,
    "runtime_bonus": 0.10,
    "runtime_mismatch_penalty": 0.08,
    "ranking_bonus_base": 0.10,
    "ranking_decay": 0.015,
}

_MMR_LAMBDA = 0.7  # relevance vs diversity trade-off
_SIGNAL_DECAY_LAMBDA = 0.03  # exp(-0.03*60)=0.165 -> interactions >60d keep <20%
_EXPLICIT_SIGNAL_BASE = 2.0  # favorites
_IMPLICIT_SIGNAL_BASE = 1.0  # search history


# ---------------------------------------------------------------------------
# Rich SPARQL parameter object (improvement #5)
# ---------------------------------------------------------------------------

@dataclass
class SparqlParams:
    genres: list[str] = field(default_factory=list)
    runtime_max: int | None = None
    director: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    exclude_titles: list[str] = field(default_factory=list)
    limit: int = 30


class SemanticSnapshot(BaseModel):
    snapshotID: str
    requestTimestamp: datetime
    userIntent: str
    hourOfDay: int
    dayOfWeek: str
    socialContext: dict | None = None
    emotionalContext: dict | None = None
    requirementContext: dict | None = None


class RecommendationUseCase:
    def __init__(
        self,
        favorites_use_case: UserFavoritesUseCase,
        history_use_case: QueryHistoryUseCase,
        metrics_use_case: RecommendationMetricsUseCase,
        llm_client: RecommendationLlmClientPort,
    ) -> None:
        self.favorites_use_case = favorites_use_case
        self.history_use_case = history_use_case
        self.metrics_use_case = metrics_use_case
        self.llm_client = llm_client
        # NOTE: scoring_weights is global to this instance. If registered as a singleton
        # in the DI container (FastAPI default), weights are shared across all users.
        # To make weights per-user, move this dict to an external store keyed by user_id.
        # Mutable copy so update_scoring_weights_from_metrics can adjust at runtime
        self.scoring_weights: dict[str, float] = dict(_DEFAULT_SCORING_WEIGHTS)
        self._weights_last_updated: datetime | None = None
        self._weights_refresh_interval_seconds: int = 300
        self._activity_last_signal_counts: dict[str, tuple[int, int]] = {}
        self._activity_last_intent: dict[str, str] = {}
        self.signal_service = RecommendationSignalService(
            favorites_use_case=favorites_use_case,
            history_use_case=history_use_case,
            signal_decay_lambda=_SIGNAL_DECAY_LAMBDA,
            explicit_signal_base=_EXPLICIT_SIGNAL_BASE,
            implicit_signal_base=_IMPLICIT_SIGNAL_BASE,
            profile_cache_ttl_seconds=180,
        )

    def _build_sparql_query(self, params: SparqlParams) -> str:
        return rc_build_sparql_query(
            genres=params.genres,
            runtime_max=params.runtime_max,
            director=params.director,
            year_min=params.year_min,
            year_max=params.year_max,
            exclude_titles=params.exclude_titles,
            limit=params.limit,
        )

    def _build_query_attempts(
        self,
        preferred_genres: list[str],
        runtime_max: int | None,
        director_hint: str | None,
        year_min: int | None,
        year_max: int | None,
        excluded_titles: set[str],
        ontology_attempts: list[tuple[str, str]] | None = None,
    ) -> list[tuple[str, str]]:
        return rc_build_query_attempts(
            ontology_attempts=ontology_attempts,
            preferred_genres=preferred_genres,
            runtime_max=runtime_max,
            director_hint=director_hint,
            year_min=year_min,
            year_max=year_max,
            excluded_titles=excluded_titles,
        )

    def _build_rdf_context(
        self,
        snapshot_id: str,
        query: str,
        social_context: dict | None,
        emotional_context: dict | None,
        requirement_context: dict | None,
        preferred_genres: list[str],
    ) -> str:
        return rc_build_rdf_context(
            snapshot_id=snapshot_id,
            query=query,
            social_context=social_context,
            emotional_context=emotional_context,
            requirement_context=requirement_context,
            preferred_genres=preferred_genres,
        )

    def _fetch_fuseki_candidates(
        self,
        query_attempts: list[tuple[str, str]],
        excluded_titles: set[str],
        minimum_candidates: int = 5,
    ) -> tuple[list[dict], int, str, str]:
        return rc_fetch_fuseki_candidates(
            query_attempts=query_attempts,
            excluded_titles=excluded_titles,
            minimum_candidates=minimum_candidates,
        )

    def _derive_activity_signals(
        self,
        history_rows: list[dict],
    ) -> tuple[str | None, str | None, str | None, bool]:
        mood_counter: Counter[str] = Counter()
        companion_counter: Counter[str] = Counter()
        energy_counter: Counter[str] = Counter()
        has_children = False

        for row in history_rows:
            mood_value = str(row.get("moodDescription") or "").strip()
            companion_value = str(row.get("companionType") or "").strip()
            energy_value = str(row.get("desiredEnergyLevel") or "").strip()

            if mood_value:
                mood_counter[mood_value] += 1
            if companion_value:
                companion_counter[companion_value] += 1
            if energy_value:
                energy_counter[energy_value] += 1
            if companion_value == "familia con niños":
                has_children = True

        mood_es = mood_counter.most_common(1)[0][0] if mood_counter else None
        companion_es = companion_counter.most_common(1)[0][0] if companion_counter else None
        energy_es = energy_counter.most_common(1)[0][0] if energy_counter else None
        return mood_es, companion_es, energy_es, has_children

    def _process_and_score_movies(self, rows: list[dict]) -> list[dict]:
        movies_with_scores: list[dict] = []
        for row in rows:
            title = row.get("title")
            if not title:
                continue

            compatibility_score = parse_optional_float(row.get("compatibilityScore"))
            rating_value = parse_optional_float(row.get("rating"))
            if compatibility_score is None:
                compatibility_score = min(0.99, max(0.4, (rating_value or 6.0) / 10.0))

            centrality = parse_optional_float(row.get("centrality"))
            pagerank = parse_optional_float(row.get("pagerank"))
            centrality_norm = min(1.0, max(0.0, centrality if centrality is not None else 0.0))
            pagerank_norm = min(1.0, max(0.0, pagerank if pagerank is not None else 0.0))

            network_score = (
                0.75 * float(compatibility_score)
                + 0.15 * centrality_norm
                + 0.10 * pagerank_norm
            )

            release_date = row.get("releaseDate")
            release_year = str(release_date)[:4] if release_date else None

            semantic_scores = {
                "overallCompatibility": parse_optional_float(row.get("compatibilityScore")),
                "moodMatchScore": parse_optional_float(row.get("moodMatch")),
                "socialMatchScore": parse_optional_float(row.get("socialMatch")),
                "energyMatchScore": parse_optional_float(row.get("energyMatch")),
            }

            movies_with_scores.append(
                {
                    "title": title,
                    "posterUrl": row.get("posterUrl"),
                    "runtime": parse_optional_int(row.get("runtime")),
                    "genreName": row.get("genreName"),
                    "releaseDate": release_year,
                    "averageRating": rating_value,
                    "compatibilityScore": round(min(0.99, max(0.4, network_score)), 2),
                    "semanticScores": semantic_scores,
                }
            )

        movies_with_scores.sort(
            key=lambda item: (
                item.get("compatibilityScore") or 0,
                item.get("averageRating") or 0,
            ),
            reverse=True,
        )
        return movies_with_scores[:5]

    def _format_recommendation_response(
        self,
        *,
        query: str,
        snapshot: SemanticSnapshot,
        sparql_query: str,
        movies_with_scores: list[dict],
        explanation: str,
        execution_time_ms: int,
    ) -> dict:
        return {
            "query": query,
            "contextExtracted": snapshot.model_dump(mode="python"),
            "rdfGenerated": "",
            "sparqlQuery": sparql_query,
            "moviesFound": len(movies_with_scores),
            "moviesWithScores": movies_with_scores,
            "explanation": explanation,
            "executionTimeMs": execution_time_ms,
        }

    def get_recommendation(self, query: str, user_id: str) -> dict:
        response, _ = self._build_recommendation(query, user_id)
        return response

    def get_recommendation_debug(self, query: str, user_id: str) -> dict:
        response, debug = self._build_recommendation(query, user_id)
        return {
            "recommendation": response,
            "debug": debug,
        }

    def _build_recent_title_set(
        self,
        history_entries: list[QueryHistory],
        limit: int = 25,
    ) -> set[str]:
        return self.signal_service.build_recent_title_set(history_entries=history_entries, limit=limit)

    def _get_user_genre_profile(self, user_id: str, history_limit: int = 20) -> dict[str, float]:
        return self.signal_service.get_user_genre_profile(user_id=user_id, history_limit=history_limit)

    def _maybe_refresh_weights(
        self,
        user_id: str,
        *,
        favorites_count: int | None = None,
        history_count: int | None = None,
        user_intent: str | None = None,
    ) -> bool:
        now = datetime.utcnow()
        if (
            self._weights_last_updated is None
            or (now - self._weights_last_updated).total_seconds()
            > self._weights_refresh_interval_seconds
        ):
            self.update_scoring_weights_from_metrics(user_id=user_id)
            self._weights_last_updated = now

        if favorites_count is None or history_count is None:
            return True

        last_intent = self._activity_last_intent.get(user_id)
        if user_intent and last_intent and user_intent != last_intent:
            return True

        previous_counts = self._activity_last_signal_counts.get(user_id)
        if previous_counts is None:
            return True

        new_favorites = max(0, favorites_count - previous_counts[0])
        new_history = max(0, history_count - previous_counts[1])
        new_signals = new_favorites + new_history
        return new_signals >= 3

    def _mark_activity_recalculated(
        self,
        *,
        user_id: str,
        favorites_count: int,
        history_count: int,
        user_intent: str,
    ) -> None:
        self._activity_last_signal_counts[user_id] = (favorites_count, history_count)
        self._activity_last_intent[user_id] = user_intent

    def _build_network_cold_start_recommendation(self, user_id: str) -> dict | None:
        self._maybe_refresh_weights(user_id=user_id)
        start = perf_counter()
        context_snapshot_id = str(uuid4())
        now = datetime.utcnow()
        graph_uri = ""
        query = "Recomendación cold start basada en centralidad de red"
        try:
            graph_uri = inject_context_snapshot(
                context_snapshot_id,
                QueryContext(intent=query),
                user_id,
                now,
            )
        except Exception:
            graph_uri = ""

        sparql_query = (
            "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX schema1: <http://schema.org/>\n"
            "SELECT ?movie ?title (SAMPLE(?posterUrl) AS ?posterUrl) (SAMPLE(?genreName) AS ?genreName) "
            "(MAX(?ratingRaw) AS ?rating) (SAMPLE(?releaseDate) AS ?releaseDate) (COUNT(DISTINCT ?neighbor) AS ?degree)\n"
            "WHERE {\n"
            "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
            "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
            "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
            "  OPTIONAL { ?movie movie:hasAverageRating ?ratingRaw }\n"
            "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
            "  OPTIONAL {\n"
            "    {\n"
            "      ?movie movie:hasMainGenre ?g .\n"
            "      ?neighbor movie:hasMainGenre ?g .\n"
            "      FILTER(?neighbor != ?movie)\n"
            "    }\n"
            "    UNION\n"
            "    {\n"
            "      ?movie movie:hasDirector ?d .\n"
            "      ?neighbor movie:hasDirector ?d .\n"
            "      FILTER(?neighbor != ?movie)\n"
            "    }\n"
            "  }\n"
            "}\n"
            "GROUP BY ?movie ?title\n"
            "ORDER BY DESC(?degree) DESC(?rating) DESC(?releaseDate)\n"
            "LIMIT 120"
        )
        try:
            try:
                rows = execute_select_query(sparql_query)
            except FusekiQueryError:
                return None

            if not rows:
                return None

            candidates: list[dict] = []
            max_degree = 1
            for row in rows:
                title = row.get("title")
                if not title:
                    continue

                degree = 0
                try:
                    degree = int(float(str(row.get("degree") or 0)))
                except Exception:
                    degree = 0

                rating_value = None
                try:
                    if row.get("rating") is not None:
                        rating_value = float(str(row.get("rating")))
                except Exception:
                    rating_value = None

                if degree > max_degree:
                    max_degree = degree

                release_year = None
                if row.get("releaseDate"):
                    try:
                        release_year = str(row["releaseDate"])[:4]
                    except Exception:
                        release_year = None

                candidates.append(
                    {
                        "title": title,
                        "posterUrl": row.get("posterUrl"),
                        "runtime": None,
                        "genreName": row.get("genreName"),
                        "releaseDate": release_year,
                        "averageRating": rating_value,
                        "degree": degree,
                    }
                )

            if not candidates:
                return None

            user_genre_profile = self._get_user_genre_profile(user_id=user_id, history_limit=10)
            selected = score_network_cold_start_movies(
                candidates=candidates,
                scoring_weights=self.scoring_weights,
                user_genre_profile=user_genre_profile,
                user_id=user_id,
                limit=5,
                pool_size=40,
            )

            explanation = (
                "Aplicamos estrategia de arranque en frío con señales de redes complejas: "
                "priorizamos películas con alta centralidad estructural en el grafo "
                "(conectividad por género/director), balanceadas con calificación global y diversidad temática."
            )

            execution_time_ms = max(1, int((perf_counter() - start) * 1000))
            context_extracted = {
                "snapshotID": context_snapshot_id,
                "requestTimestamp": now,
                "userIntent": "cold_start_network_centrality",
                "hourOfDay": now.hour,
                "dayOfWeek": now.strftime("%A"),
                "socialContext": None,
                "emotionalContext": None,
                "requirementContext": None,
            }

            return {
                "query": query,
                "contextExtracted": context_extracted,
                "rdfGenerated": "",
                "sparqlQuery": sparql_query,
                "moviesFound": len(selected),
                "moviesWithScores": selected,
                "explanation": explanation,
                "executionTimeMs": execution_time_ms,
            }
        finally:
            try:
                delete_context_snapshot(context_snapshot_id)
            except Exception:
                pass

    async def get_activity_recommendation(self, user_id: str) -> dict:
        signal_snapshot = self.signal_service.collect_activity_snapshot(user_id=user_id)
        favorites = signal_snapshot["favorites"]
        history = signal_snapshot["history"]
        recent_queries = signal_snapshot.get("recent_queries") or []
        current_intent = recent_queries[0] if recent_queries else "activity_recent_profile"

        favorites_count = len(favorites)
        history_count = len(history)
        previous_counts = self._activity_last_signal_counts.get(user_id)
        previous_signals_total = (
            (previous_counts[0] + previous_counts[1])
            if previous_counts is not None
            else 0
        )
        current_signals_total = favorites_count + history_count
        previous_intent = self._activity_last_intent.get(user_id)
        intent_changed = bool(previous_intent and previous_intent != current_intent)
        logger.info(
            "Checking cache for user %s | Signals: Prev=%s, Curr=%s | Intent Changed=%s",
            user_id,
            previous_signals_total,
            current_signals_total,
            intent_changed,
        )
        needs_recalculation = self._maybe_refresh_weights(
            user_id=user_id,
            favorites_count=favorites_count,
            history_count=history_count,
            user_intent=current_intent,
        )

        if not needs_recalculation:
            cached_payload = self.signal_service.get_cached_activity_snapshot(
                user_id=user_id,
                max_age_seconds=12 * 60 * 60,
            )
            if cached_payload and isinstance(cached_payload.get("response"), dict):
                logger.info("[CACHE_HIT] user_id=%s", user_id)
                return cached_payload["response"]

        excluded_from_history = self._build_recent_title_set(history_entries=history, limit=30)
        favorite_titles = {
            str(movie.title).strip().lower()
            for movie in favorites
            if movie.title and str(movie.title).strip()
        }
        excluded_titles_normalized = excluded_from_history.union(favorite_titles)

        has_history = user_history_graph_exists(user_id)
        profile_source = "fuseki_history" if has_history else "cold_start"
        mood_es: str | None = None
        companion_es: str | None = None
        energy_es: str | None = None

        if has_history:
            history_rows = get_user_context_history(user_id, limit=20)
            mood_es, companion_es, energy_es, has_children = self._derive_activity_signals(history_rows)

            if mood_es or companion_es or energy_es:
                sparql = build_cross_ontology_sparql_from_signals(
                    mood_es=mood_es,
                    companion_es=companion_es,
                    energy_es=energy_es,
                    has_children=has_children,
                    runtime_max=None,
                    excluded_normalized=excluded_titles_normalized,
                    limit=30,
                )
                try:
                    rows = execute_select_query(sparql)
                except Exception:
                    rows = []

                if rows:
                    movies_with_scores = self._process_and_score_movies(rows)

                    now = datetime.utcnow()
                    activity_query = (
                        f"Recomendación basada en perfil semántico: mood={mood_es}, "
                        f"compañía={companion_es}"
                    )
                    semantic_hint = (
                        f"mood={mood_es or 'none'}, social={companion_es or 'none'}, "
                        f"energy={energy_es or 'none'}, children={str(has_children).lower()}"
                    )
                    explanation = await asyncio.to_thread(
                        self.llm_client.generate_recommendation_explanation,
                        query=activity_query,
                        context_summary=(
                            f"mood={mood_es or 'none'}, social={companion_es or 'none'}, "
                            f"energy={energy_es or 'none'}"
                        ),
                        movies_with_scores=movies_with_scores,
                        semantic_hint=semantic_hint,
                        query_type="activity",
                    )

                    snapshot = SemanticSnapshot(
                        snapshotID=str(uuid4()),
                        requestTimestamp=now,
                        userIntent=activity_query,
                        hourOfDay=now.hour,
                        dayOfWeek=now.strftime("%A"),
                        socialContext=(
                            {
                                "companionType": companion_es,
                                "hasChildren": has_children,
                            }
                            if companion_es
                            else None
                        ),
                        emotionalContext=(
                            {
                                "moodDescription": mood_es,
                                "desiredEnergyLevel": energy_es,
                            }
                            if mood_es or energy_es
                            else None
                        ),
                        requirementContext=None,
                    )

                    response = self._format_recommendation_response(
                        query=activity_query,
                        snapshot=snapshot,
                        sparql_query=sparql,
                        movies_with_scores=movies_with_scores,
                        explanation=explanation,
                        execution_time_ms=1,
                    )
                    response["debugPayload"] = {
                        "profileSource": profile_source,
                        "dominantMood": mood_es,
                        "dominantCompanion": companion_es,
                    }
                    self.signal_service.cache_activity_snapshot(
                        user_id,
                        {
                            "snapshot": snapshot.model_dump(mode="python"),
                            "response": response,
                        },
                    )
                    self._mark_activity_recalculated(
                        user_id=user_id,
                        favorites_count=favorites_count,
                        history_count=history_count,
                        user_intent=current_intent,
                    )
                    logger.info("[RECALCULATED] user_id=%s", user_id)
                    return response

        cold_start_response = self._build_network_cold_start_recommendation(user_id)
        if cold_start_response is not None:
            cold_start_response["debugPayload"] = {
                "profileSource": profile_source,
                "dominantMood": mood_es,
                "dominantCompanion": companion_es,
            }
            try:
                cold_snapshot = SemanticSnapshot.model_validate(cold_start_response["contextExtracted"])
                self.signal_service.cache_activity_snapshot(
                    user_id,
                    {
                        "snapshot": cold_snapshot.model_dump(mode="python"),
                        "response": cold_start_response,
                    },
                )
                self._mark_activity_recalculated(
                    user_id=user_id,
                    favorites_count=favorites_count,
                    history_count=history_count,
                    user_intent=current_intent,
                )
            except Exception:
                pass
            logger.info("[RECALCULATED] user_id=%s", user_id)
            return cold_start_response

        fallback_query = "Recomendación cold start basada en centralidad de red"
        fallback_response = {
            "query": fallback_query,
            "contextExtracted": {
                "snapshotID": str(uuid4()),
                "requestTimestamp": datetime.utcnow(),
                "userIntent": fallback_query,
                "hourOfDay": datetime.utcnow().hour,
                "dayOfWeek": datetime.utcnow().strftime("%A"),
                "socialContext": None,
                "emotionalContext": None,
                "requirementContext": None,
            },
            "rdfGenerated": "",
            "sparqlQuery": "",
            "moviesFound": 0,
            "moviesWithScores": [],
            "explanation": "No se encontraron recomendaciones para este usuario.",
            "executionTimeMs": 1,
            "debugPayload": {
                "profileSource": profile_source,
                "dominantMood": mood_es,
                "dominantCompanion": companion_es,
            },
        }
        try:
            fallback_snapshot = SemanticSnapshot.model_validate(fallback_response["contextExtracted"])
            self.signal_service.cache_activity_snapshot(
                user_id,
                {
                    "snapshot": fallback_snapshot.model_dump(mode="python"),
                    "response": fallback_response,
                },
            )
            self._mark_activity_recalculated(
                user_id=user_id,
                favorites_count=favorites_count,
                history_count=history_count,
                user_intent=current_intent,
            )
        except Exception:
            pass
        logger.info("[RECALCULATED] user_id=%s", user_id)
        return fallback_response

    def _build_recommendation(
        self,
        query: str,
        user_id: str,
        excluded_titles: set[str] | None = None,
    ) -> tuple[dict, dict]:
        self._maybe_refresh_weights(user_id=user_id)
        total_start = perf_counter()
        query_lower = query.lower()
        excluded_normalized = {
            title.strip().lower()
            for title in (excluded_titles or set())
            if isinstance(title, str) and title.strip()
        }
        timings: dict[str, int] = {}
        debug_errors: list[str] = []

        def elapsed_ms(start_time: float) -> int:
            return max(0, int((perf_counter() - start_time) * 1000))

        context_start = perf_counter()

        # --- Semantic NLU (LLM with keyword fallback) ---
        nlu = self.llm_client.extract_query_context(query)
        import logging
        _nlu_logger = logging.getLogger("nlu_debug")
        _nlu_logger.setLevel(logging.DEBUG)
        _nlu_logger.debug(
            "[NLU] query=%r | mood=%r | intent=%r | social=%r | genres=%r",
            query,
            nlu.mood,
            nlu.intent,
            nlu.social_context,
            nlu.genres,
        )
        mood_to_energy = {
            "relaxed": "low",
            "excited": "high",
            "sad": "low",
            "happy": "medium",
            "neutral": "medium",
        }

        social_context = nlu.social_context
        emotional_context = None
        if nlu.mood:
            emotional_context = {
                "moodDescription": nlu.mood,
                "desiredEnergyLevel": mood_to_energy.get(nlu.mood, "medium"),
            }
        requirement_context = {
            "availableTime": nlu.runtime_max,
            "excludedGenre": nlu.exclusions if nlu.exclusions else None,
        }
        preferred_genres = nlu.genres
        director_hint = nlu.director_hint
        year_range = nlu.year_range  # [min_year, max_year] or None

        for exclusion in nlu.exclusions:
            normalized_exclusion = str(exclusion).strip().lower()
            if normalized_exclusion:
                excluded_normalized.add(normalized_exclusion)

        timings["contextExtraction"] = elapsed_ms(context_start)

        _current_year = datetime.utcnow().year
        user_genre_profile = self._get_user_genre_profile(user_id=user_id)

        build_query_start = perf_counter()
        context_snapshot_id = str(uuid4())
        now = datetime.utcnow()
        graph_uri = ""
        try:
            graph_uri = inject_context_snapshot(context_snapshot_id, nlu, user_id, now)
        except Exception:
            graph_uri = ""

        rdf_generated = self._build_rdf_context(
            snapshot_id=context_snapshot_id,
            query=query,
            social_context=social_context,
            emotional_context=emotional_context,
            requirement_context=requirement_context,
            preferred_genres=preferred_genres,
        )

        _runtime_max = (
            int(requirement_context["availableTime"])
            if requirement_context and requirement_context.get("availableTime")
            else None
        )
        _year_min = int(year_range[0]) if year_range and len(year_range) >= 1 else None
        _year_max = int(year_range[1]) if year_range and len(year_range) >= 2 else None

        sparql_query = self._build_sparql_query(
            SparqlParams(
                genres=preferred_genres,
                runtime_max=_runtime_max,
                director=director_hint,
                year_min=_year_min,
                year_max=_year_max,
                exclude_titles=sorted(excluded_normalized)[:10],
                limit=30,
            )
        )
        timings["rdfAndSparqlBuild"] = elapsed_ms(build_query_start)

        favorites = self.favorites_use_case.get_my_favorites(user_id)
        top_candidates = favorites[:5]

        fuseki_start = perf_counter()
        ontology_attempts = build_cross_ontology_sparql(
            ctx=nlu,
            excluded_normalized=excluded_normalized,
        )
        query_attempts = self._build_query_attempts(
            preferred_genres=preferred_genres,
            runtime_max=_runtime_max,
            director_hint=director_hint,
            year_min=_year_min,
            year_max=_year_max,
            excluded_titles=excluded_normalized,
            ontology_attempts=ontology_attempts,
        )

        try:
            (
                fuseki_candidates,
                fuseki_rows_count,
                fuseki_strategy,
                selected_query,
            ) = self._fetch_fuseki_candidates(
                query_attempts=query_attempts,
                excluded_titles=excluded_normalized,
                minimum_candidates=5,
            )
            sparql_query = selected_query
        except FusekiQueryError as exc:
            fuseki_candidates = []
            fuseki_rows_count = 0
            fuseki_strategy = "strict"
            debug_errors.append(f"fuseki_query_error: {exc}")
        timings["fusekiQuery"] = elapsed_ms(fuseki_start)

        movies_with_scores: list[dict] = []
        scoring_start = perf_counter()
        recommendation_source = "fuseki"
        if fuseki_candidates:
            movies_with_scores = rank_fuseki_movies(
                fuseki_candidates=fuseki_candidates,
                preferred_genres=preferred_genres,
                runtime_max=_runtime_max,
                current_year=_current_year,
                user_genre_profile=user_genre_profile,
                scoring_weights=self.scoring_weights,
                mmr_lambda=_MMR_LAMBDA,
                limit=5,
            )
            recommendation_source = f"fuseki_{fuseki_strategy}"
        else:
            recommendation_source = "favorites_fallback"
            for index, movie in enumerate(top_candidates):
                normalized_title = (movie.title or "").strip().lower()
                if normalized_title in excluded_normalized:
                    continue
                score = max(0.5, 0.95 - (index * 0.08))
                movies_with_scores.append(
                    {
                        "title": movie.title,
                        "posterUrl": movie.posterUrl,
                        "runtime": movie.runtime,
                        "genreName": movie.genres[0] if movie.genres else None,
                        "releaseDate": str(movie.year) if movie.year else None,
                        "averageRating": movie.rating,
                        "compatibilityScore": round(score, 2),
                    }
                )
        timings["scoring"] = elapsed_ms(scoring_start)

        context_summary = build_context_summary(
            social_context=social_context,
            emotional_context=emotional_context,
            requirement_context=requirement_context,
        )

        context_extracted = build_context_extracted(
            snapshot_id=context_snapshot_id,
            request_timestamp=now,
            user_intent=query,
            social_context=social_context,
            emotional_context=emotional_context,
            requirement_context=requirement_context,
        )

        mood_driven_signal = bool(nlu.mood and preferred_genres)
        if recommendation_source == "favorites_fallback" or not movies_with_scores:
            query_type = "cold_start"
        elif mood_driven_signal:
            query_type = "mood_driven"
        elif nlu.social_context:
            query_type = "social"
        else:
            query_type = "general"

        llm_start = perf_counter()
        explanation = self.llm_client.generate_recommendation_explanation(
            query=query,
            context_summary=context_summary,
            movies_with_scores=movies_with_scores,
            query_type=query_type,
        )
        timings["llmExplanation"] = elapsed_ms(llm_start)

        execution_time_ms = max(1, elapsed_ms(total_start))

        response = build_recommendation_response(
            query=query,
            context_extracted=context_extracted,
            rdf_generated=rdf_generated,
            sparql_query=sparql_query,
            movies_with_scores=movies_with_scores,
            explanation=explanation,
            execution_time_ms=execution_time_ms,
        )

        history_start = perf_counter()
        try:
            self.history_use_case.create_entry(
                QueryHistory(
                    userId=user_id,
                    query=query,
                    rdfGenerated=response["rdfGenerated"],
                    sparqlExecuted=response["sparqlQuery"],
                    contextExtracted=context_extracted,
                    resultsFound=movies_with_scores,
                    explanation=explanation,
                    executionTimeMs=execution_time_ms,
                    wasSuccessful=len(movies_with_scores) > 0,
                )
            )
        except Exception as exc:
            debug_errors.append(f"history_write_error: {exc}")
        timings["historyWrite"] = elapsed_ms(history_start)
        timings["total"] = max(1, elapsed_ms(total_start))

        try:
            self.metrics_use_case.create_entry(
                RecommendationMetric(
                    userId=user_id,
                    query=query,
                    source=recommendation_source,
                    fallbackUsed=not any(
                        recommendation_source.startswith(p) for p in ("fuseki", "ontology")
                    ),
                    fusekiRows=fuseki_rows_count,
                    errors=debug_errors,
                    timingsMs=timings,
                    moviesFound=len(movies_with_scores),
                    executionTimeMs=execution_time_ms,
                    createdAt=now,
                )
            )
        except Exception as exc:
            debug_errors.append(f"metrics_write_error: {exc}")

        ontology_navigation_used = recommendation_source.startswith("ontology")
        debug_payload = build_debug_payload(
            recommendation_source=recommendation_source,
            fuseki_rows_count=fuseki_rows_count,
            debug_errors=debug_errors,
            timings=timings,
            ontology_navigation_used=ontology_navigation_used,
            context_graph_injected=bool(graph_uri),
        )

        try:
            copy_graph_to_user_history(context_snapshot_id, user_id)
        except Exception as exc:
            debug_errors.append(f"archive_snapshot_error: {exc}")
        finally:
            try:
                delete_context_snapshot(context_snapshot_id)
            except Exception:
                pass

        return response, debug_payload

    def update_scoring_weights_from_metrics(self, user_id: str | None = None) -> None:
        """Closed feedback loop: update adaptive scoring weights from recent metrics.

        Since explicit click/watch events are not stored yet, this method estimates
        engagement from ``moviesFound``, ``fallbackUsed``, ``executionTimeMs`` and
        error presence, then applies bounded correlation-based updates.
        """
        try:
            recent = self.metrics_use_case.list_recent(limit=200)
        except Exception:
            return

        if user_id:
            recent = [metric for metric in recent if metric.userId == user_id]

        self.scoring_weights = adapt_scoring_weights(
            current_weights=self.scoring_weights,
            default_weights=_DEFAULT_SCORING_WEIGHTS,
            metrics=recent,
        )
