from dataclasses import dataclass, field
from datetime import datetime
import math
from time import perf_counter
from uuid import uuid4
from collections import Counter
import hashlib

from app.application.use_cases.query_history import QueryHistoryUseCase
from app.application.use_cases.recommendation_metrics import RecommendationMetricsUseCase
from app.application.use_cases.user_favorites import UserFavoritesUseCase
from app.core.fuseki_client import FusekiQueryError, execute_select_query
from app.core.recommendation_llm import (
    extract_query_context,
    generate_recommendation_explanation,
)
from app.domain.entities.query_history import QueryHistory
from app.domain.entities.recommendation_metric import RecommendationMetric

# ---------------------------------------------------------------------------
# Scoring weight defaults (can be updated via update_scoring_weights_from_metrics)
# ---------------------------------------------------------------------------

_DEFAULT_SCORING_WEIGHTS: dict[str, float] = {
    "rating": 0.58,
    "degree": 0.42,
    "freshness": 0.08,
    "genre_bonus": 0.15,
    "runtime_bonus": 0.10,
    "ranking_bonus_base": 0.10,
}

_MMR_LAMBDA = 0.7  # relevance vs diversity trade-off


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
    limit: int = 30


# ---------------------------------------------------------------------------
# MMR diversity helpers (improvement #4)
# ---------------------------------------------------------------------------

def _genre_similarity(a: dict, b: dict) -> float:
    """Jaccard similarity between the primary genre of two candidate movies."""
    ga = {(a.get("genreName") or "").strip().lower()}
    gb = {(b.get("genreName") or "").strip().lower()}
    ga.discard("")
    gb.discard("")
    if not ga and not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def _mmr_select(
    candidates: list[dict],
    n: int = 5,
    lambda_: float = _MMR_LAMBDA,
    relevance_key: str = "compatibilityScore",
) -> list[dict]:
    """Maximal Marginal Relevance selection.

    mmr_score = lambda_ * relevance - (1 - lambda_) * max_sim(candidate, selected)
    """
    if not candidates:
        return []
    remaining = list(candidates)
    selected: list[dict] = []
    while remaining and len(selected) < n:
        if not selected:
            best = max(remaining, key=lambda m: m.get(relevance_key, 0.0))
        else:
            def _mmr(m: dict, _sel: list[dict] = selected) -> float:
                relevance = m.get(relevance_key, 0.0)
                max_sim = max(_genre_similarity(m, s) for s in _sel)
                return lambda_ * relevance - (1 - lambda_) * max_sim
            best = max(remaining, key=_mmr)
        selected.append(best)
        remaining.remove(best)
    return selected


class RecommendationUseCase:
    def __init__(
        self,
        favorites_use_case: UserFavoritesUseCase,
        history_use_case: QueryHistoryUseCase,
        metrics_use_case: RecommendationMetricsUseCase,
    ) -> None:
        self.favorites_use_case = favorites_use_case
        self.history_use_case = history_use_case
        self.metrics_use_case = metrics_use_case
        # Mutable copy so update_scoring_weights_from_metrics can adjust at runtime
        self.scoring_weights: dict[str, float] = dict(_DEFAULT_SCORING_WEIGHTS)

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
        recent_titles: set[str] = set()
        for entry in history_entries:
            results = entry.resultsFound or []
            if not isinstance(results, list):
                continue
            for result in results:
                if not isinstance(result, dict):
                    continue
                title = result.get("title")
                if not title:
                    continue
                normalized = str(title).strip().lower()
                if normalized:
                    recent_titles.add(normalized)
                if len(recent_titles) >= max(1, limit):
                    return recent_titles
        return recent_titles

    def _build_network_cold_start_recommendation(self, user_id: str) -> dict | None:
        start = perf_counter()
        now = datetime.utcnow()
        query = "Recomendación cold start basada en centralidad de red"
        sparql_query = (
            "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "SELECT ?movie ?title (SAMPLE(?posterUrl) AS ?posterUrl) (SAMPLE(?genreName) AS ?genreName) "
            "(MAX(?ratingRaw) AS ?rating) (SAMPLE(?releaseDate) AS ?releaseDate) (COUNT(DISTINCT ?neighbor) AS ?degree)\n"
            "WHERE {\n"
            "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
            "  OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }\n"
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

        current_year = datetime.utcnow().year
        scored: list[dict] = []
        for movie in candidates:
            rating_norm = 0.55
            if movie.get("averageRating") is not None:
                rating_norm = min(1.0, max(0.35, float(movie["averageRating"]) / 10))

            degree_norm = 0.0
            if max_degree > 0:
                degree_norm = math.log1p(max(0, int(movie.get("degree") or 0))) / math.log1p(
                    max_degree
                )

            freshness = 0.0
            try:
                if movie.get("releaseDate"):
                    age = current_year - int(str(movie["releaseDate"])[:4])
                    freshness = max(0.0, 1.0 - age / 40.0)
            except Exception:
                freshness = 0.0

            w = self.scoring_weights
            score = (
                w.get("rating", 0.58) * rating_norm
                + w.get("degree", 0.42) * degree_norm
                + w.get("freshness", 0.08) * freshness
            )
            movie_with_score = dict(movie)
            movie_with_score["compatibilityScore"] = round(min(0.99, max(0.4, score)), 2)
            scored.append(movie_with_score)

        scored.sort(
            key=lambda item: (
                item.get("compatibilityScore", 0),
                item.get("averageRating") or 0,
                int(item.get("degree") or 0),
            ),
            reverse=True,
        )

        # MMR diversity selection instead of set-based genre deduplication
        selected = _mmr_select(scored, n=5)

        if selected:
            day_key = datetime.utcnow().strftime("%Y-%m-%d")
            hash_source = f"{user_id}:{day_key}".encode("utf-8")
            rotation_seed = int(hashlib.sha256(hash_source).hexdigest()[:8], 16)
            offset = rotation_seed % len(selected)
            selected = selected[offset:] + selected[:offset]

        explanation = (
            "Aplicamos estrategia de arranque en frío con señales de redes complejas: "
            "priorizamos películas con alta centralidad estructural en el grafo "
            "(conectividad por género/director), balanceadas con calificación global y diversidad temática."
        )

        execution_time_ms = max(1, int((perf_counter() - start) * 1000))
        context_extracted = {
            "snapshotID": str(uuid4()),
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

    def get_activity_recommendation(self, user_id: str) -> dict:
        favorites = self.favorites_use_case.get_my_favorites(user_id)
        history = self.history_use_case.find_by_user(user_id=user_id, limit=20)

        if not favorites and not history:
            cold_start_response = self._build_network_cold_start_recommendation(user_id)
            if cold_start_response:
                return cold_start_response

        genre_counter: Counter[str] = Counter()
        director_counter: Counter[str] = Counter()
        recent_titles: list[str] = []

        # Temporal decay parameters:  exp(-0.035 * 60) ≈ 0.12  → >60 days < 20% weight
        _DECAY_LAMBDA = 0.035
        _EXPLICIT_BASE = 2.0   # favorites = explicit signal
        _IMPLICIT_BASE = 1.0   # search history = implicit signal
        now_ts = datetime.utcnow()

        for movie in favorites:
            days = 0.0
            if movie.addedAt:
                try:
                    days = max(0.0, (now_ts - movie.addedAt.replace(tzinfo=None)).total_seconds() / 86400)
                except Exception:
                    days = 0.0
            weight = _EXPLICIT_BASE * math.exp(-_DECAY_LAMBDA * days)
            for genre in movie.genres or []:
                if genre:
                    genre_counter[str(genre).strip()] += weight
            if movie.director:
                director_counter[str(movie.director).strip()] += weight
            if movie.title and len(recent_titles) < 4:
                recent_titles.append(movie.title.strip())

        ignored_queries = {
            "busqueda de peliculas",
            "búsqueda de películas",
            "recomiéndame una película basada en mi actividad reciente",
        }
        recent_queries: list[str] = []
        for entry in history:
            raw_query = (entry.query or "").strip()
            normalized = raw_query.lower()
            if not raw_query:
                continue
            if normalized in ignored_queries:
                continue
            if normalized.startswith("connection "):
                continue
            if raw_query not in recent_queries:
                recent_queries.append(raw_query)
            if len(recent_queries) >= 3:
                break

            days = 0.0
            if entry.createdAt:
                try:
                    days = max(0.0, (now_ts - entry.createdAt.replace(tzinfo=None)).total_seconds() / 86400)
                except Exception:
                    days = 0.0
            weight = _IMPLICIT_BASE * math.exp(-_DECAY_LAMBDA * days)

            for result in entry.resultsFound or []:
                if not isinstance(result, dict):
                    continue
                if result.get("genreName"):
                    genre_counter[str(result["genreName"]).strip()] += weight
                if result.get("director"):
                    director_counter[str(result["director"]).strip()] += weight
                result_genres = result.get("genres")
                if isinstance(result_genres, list):
                    for genre in result_genres:
                        if genre:
                            genre_counter[str(genre).strip()] += weight
                if result.get("title") and len(recent_titles) < 6:
                    title = str(result["title"]).strip()
                    if title and title not in recent_titles:
                        recent_titles.append(title)

        top_genres = [name for name, _ in genre_counter.most_common(2)]
        top_directors = [name for name, _ in director_counter.most_common(1)]

        query_parts = ["Recomiéndame una película basada en mi actividad reciente"]
        if top_genres:
            query_parts.append(f"con preferencia por género {', '.join(top_genres)}")
        if top_directors:
            query_parts.append(f"considerando directores como {', '.join(top_directors)}")
        if recent_titles:
            query_parts.append(f"similar a {', '.join(recent_titles[:2])}")
        if recent_queries:
            query_parts.append(f"teniendo en cuenta búsquedas como {', '.join(recent_queries[:2])}")

        activity_query = ". ".join(query_parts)

        recent_titles = self._build_recent_title_set(history_entries=history, limit=30)
        favorite_titles = {
            str(movie.title).strip().lower()
            for movie in favorites
            if movie.title and str(movie.title).strip()
        }
        excluded_titles = recent_titles.union(favorite_titles)

        response, _ = self._build_recommendation(
            activity_query,
            user_id,
            excluded_titles=excluded_titles,
        )

        if response.get("moviesFound", 0) == 0:
            response, _ = self._build_recommendation(activity_query, user_id)

        return response

    def _build_recommendation(
        self,
        query: str,
        user_id: str,
        excluded_titles: set[str] | None = None,
    ) -> tuple[dict, dict]:
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

        def safe_rdf_literal(value: str) -> str:
            return (
                value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", " ")
                .replace("\r", " ")
            )

        context_start = perf_counter()

        # --- Semantic NLU (LLM with keyword fallback) ---
        nlu = extract_query_context(query)
        social_context = nlu.social_context
        emotional_context = nlu.emotional_context
        requirement_context = nlu.requirement_context
        preferred_genres = nlu.preferred_genres
        director_hint = nlu.director_hint
        year_range = nlu.year_range  # [min_year, max_year] or None

        timings["contextExtraction"] = elapsed_ms(context_start)

        def build_rdf_context(snapshot_id: str) -> str:
            social_companion = social_context["companionType"] if social_context else "unknown"
            mood = emotional_context["moodDescription"] if emotional_context else "neutral"
            energy = emotional_context["desiredEnergyLevel"] if emotional_context else "medium"
            available_time = (
                str(requirement_context["availableTime"])
                if requirement_context and requirement_context.get("availableTime")
                else "unknown"
            )
            genres_literal = ", ".join(preferred_genres) if preferred_genres else "none"
            safe_query = safe_rdf_literal(query)
            return (
                "@prefix ctx: <http://www.semanticweb.org/movierecommendation/context/> .\n"
                f"ctx:{snapshot_id} ctx:userIntent \"{safe_query}\" ;\n"
                f"    ctx:companionType \"{social_companion}\" ;\n"
                f"    ctx:mood \"{mood}\" ;\n"
                f"    ctx:energy \"{energy}\" ;\n"
                f"    ctx:availableTime \"{available_time}\" ;\n"
                f"    ctx:preferredGenres \"{genres_literal}\" ."
            )

        def build_sparql_query(params: SparqlParams) -> str:
            """Build a SPARQL SELECT query from a rich SparqlParams object.

            Validates the generated query; falls back to a safe broad query on failure.
            """
            genre_filter = ""
            if params.genres:
                genre_values = " ".join(f'"{g}"' for g in params.genres)
                genre_filter = f"FILTER(?genreName IN ({genre_values}))"

            runtime_filter = ""
            if params.runtime_max is not None:
                runtime_filter = f"FILTER(!BOUND(?runtime) || ?runtime <= {int(params.runtime_max)})"

            director_filter = ""
            if params.director:
                safe_dir = params.director.replace('"', '\\"')
                director_filter = f'FILTER(CONTAINS(LCASE(STR(?directorName)), LCASE("{safe_dir}")))'

            year_filter = ""
            if params.year_min is not None:
                year_filter += f"FILTER(YEAR(?releaseDate) >= {int(params.year_min)})\n  "
            if params.year_max is not None:
                year_filter += f"FILTER(YEAR(?releaseDate) <= {int(params.year_max)})"

            director_block = ""
            if params.director:
                director_block = (
                    "  OPTIONAL { ?movie movie:hasDirector/movie:directorName ?directorName }\n"
                )

            candidate = (
                "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
                "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
                "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl ?releaseDate\n"
                "WHERE {\n"
                "  ?movie rdf:type movie:FeatureFilm ;\n"
                "         movie:hasTitle ?title .\n"
                "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
                "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
                "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
                "  OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }\n"
                "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
                f"{director_block}"
                f"  {genre_filter}\n"
                f"  {runtime_filter}\n"
                f"  {year_filter}\n"
                f"  {director_filter}\n"
                "}\n"
                "ORDER BY DESC(?rating) DESC(?releaseDate)\n"
                f"LIMIT {params.limit}"
            )

            # Basic validation: balanced braces and mandatory keywords
            if candidate.count("{") != candidate.count("}") or "SELECT" not in candidate:
                # Safe fallback broad query
                return (
                    "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
                    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
                    "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl ?releaseDate\n"
                    "WHERE {\n"
                    "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
                    "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
                    "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
                    "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
                    "  OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }\n"
                    "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
                    "}\n"
                    "ORDER BY DESC(?rating) DESC(?releaseDate)\n"
                    "LIMIT 60"
                )
            return candidate

        def is_runtime_match(runtime_value: int | None) -> bool:
            if not (requirement_context and requirement_context.get("availableTime")):
                return True
            if runtime_value is None:
                return True
            return runtime_value <= int(requirement_context["availableTime"])

        def is_genre_match(genre_name: str | None) -> bool:
            if not preferred_genres:
                return True
            if not genre_name:
                return False
            return genre_name in preferred_genres

        _current_year = datetime.utcnow().year

        def score_fuseki_candidate(movie: dict, rank_hint: int) -> float:
            w = self.scoring_weights
            rating_value = movie.get("averageRating")
            normalized_rating = 0.6
            if rating_value is not None:
                normalized_rating = min(1.0, max(0.45, float(rating_value) / 10))

            freshness = 0.0
            try:
                if movie.get("releaseDate"):
                    age = _current_year - int(str(movie["releaseDate"])[:4])
                    freshness = max(0.0, 1.0 - age / 40.0)
            except Exception:
                freshness = 0.0

            genre_bonus = w.get("genre_bonus", 0.15) if is_genre_match(movie.get("genreName")) else -0.03
            runtime_bonus = w.get("runtime_bonus", 0.10) if is_runtime_match(movie.get("runtime")) else -0.08
            ranking_bonus = max(0.0, w.get("ranking_bonus_base", 0.10) - rank_hint * 0.015)

            final_score = (
                normalized_rating
                + w.get("freshness", 0.08) * freshness
                + genre_bonus
                + runtime_bonus
                + ranking_bonus
            )
            return min(0.99, max(0.4, round(final_score, 2)))

        build_query_start = perf_counter()
        context_snapshot_id = str(uuid4())
        rdf_generated = build_rdf_context(context_snapshot_id)

        _runtime_max = (
            int(requirement_context["availableTime"])
            if requirement_context and requirement_context.get("availableTime")
            else None
        )
        _year_min = int(year_range[0]) if year_range and len(year_range) >= 1 else None
        _year_max = int(year_range[1]) if year_range and len(year_range) >= 2 else None

        sparql_query = build_sparql_query(
            SparqlParams(
                genres=preferred_genres,
                runtime_max=_runtime_max,
                director=director_hint,
                year_min=_year_min,
                year_max=_year_max,
                limit=30,
            )
        )
        timings["rdfAndSparqlBuild"] = elapsed_ms(build_query_start)

        favorites = self.favorites_use_case.get_my_favorites(user_id)
        top_candidates = favorites[:5]

        fuseki_candidates: list[dict] = []
        fuseki_rows_count = 0
        fuseki_start = perf_counter()
        fuseki_strategy = "strict"
        query_attempts: list[tuple[str, str]] = []

        has_genre_constraint = bool(preferred_genres)
        has_runtime_constraint = bool(_runtime_max)

        query_attempts.append((
            "strict",
            build_sparql_query(SparqlParams(
                genres=preferred_genres if has_genre_constraint else [],
                runtime_max=_runtime_max if has_runtime_constraint else None,
                director=director_hint,
                year_min=_year_min,
                year_max=_year_max,
                limit=30,
            )),
        ))

        if has_genre_constraint and has_runtime_constraint:
            query_attempts.append((
                "relaxed_runtime",
                build_sparql_query(SparqlParams(
                    genres=preferred_genres,
                    runtime_max=None,
                    director=director_hint,
                    year_min=_year_min,
                    year_max=_year_max,
                    limit=40,
                )),
            ))

        if has_genre_constraint:
            query_attempts.append((
                "relaxed_genre",
                build_sparql_query(SparqlParams(
                    genres=[],
                    runtime_max=_runtime_max,
                    director=director_hint,
                    year_min=_year_min,
                    year_max=_year_max,
                    limit=40,
                )),
            ))

        query_attempts.append((
            "broad",
            build_sparql_query(SparqlParams(limit=60)),
        ))

        unique_attempts: list[tuple[str, str]] = []
        seen_queries: set[str] = set()
        for attempt_name, attempt_query in query_attempts:
            if attempt_query in seen_queries:
                continue
            seen_queries.add(attempt_query)
            unique_attempts.append((attempt_name, attempt_query))

        query_attempts = unique_attempts

        try:
            seen_titles: set[str] = set()

            selected_query = sparql_query
            for attempt_name, attempt_query in query_attempts:
                selected_query = attempt_query
                raw_rows = execute_select_query(attempt_query)
                fuseki_rows_count += len(raw_rows)

                for row in raw_rows:
                    title = row.get("title")
                    if not title:
                        continue

                    normalized_title = title.strip().lower()
                    if normalized_title in excluded_normalized:
                        continue
                    if normalized_title in seen_titles:
                        continue

                    rating_value = None
                    if row.get("rating") is not None:
                        try:
                            rating_value = float(row["rating"])
                        except ValueError:
                            rating_value = None

                    runtime_value = None
                    if row.get("runtime") is not None:
                        try:
                            runtime_value = int(float(row["runtime"]))
                        except ValueError:
                            runtime_value = None

                    release_date = row.get("releaseDate")
                    release_year = None
                    if release_date:
                        release_year = str(release_date)[:4]

                    fuseki_candidates.append(
                        {
                            "title": title,
                            "posterUrl": row.get("posterUrl"),
                            "runtime": runtime_value,
                            "genreName": row.get("genreName"),
                            "releaseDate": release_year,
                            "averageRating": rating_value,
                            "queryStrategy": attempt_name,
                        }
                    )
                    seen_titles.add(normalized_title)

                if len(fuseki_candidates) >= 5:
                    fuseki_strategy = attempt_name
                    break

            sparql_query = selected_query
        except FusekiQueryError as exc:
            fuseki_candidates = []
            debug_errors.append(f"fuseki_query_error: {exc}")
        timings["fusekiQuery"] = elapsed_ms(fuseki_start)

        movies_with_scores: list[dict] = []
        scoring_start = perf_counter()
        recommendation_source = "fuseki"
        if fuseki_candidates:
            sorted_candidates = sorted(
                fuseki_candidates,
                key=lambda movie: (
                    is_genre_match(movie.get("genreName")),
                    is_runtime_match(movie.get("runtime")),
                    (movie.get("averageRating") or 0),
                ),
                reverse=True,
            )

            # Score all candidates first, then use MMR for diversity selection
            pre_scored: list[dict] = []
            for index, movie in enumerate(sorted_candidates):
                scored_movie = dict(movie)
                scored_movie["compatibilityScore"] = score_fuseki_candidate(movie, index)
                pre_scored.append(scored_movie)

            for movie in _mmr_select(pre_scored, n=5):
                movies_with_scores.append(
                    {
                        "title": movie.get("title"),
                        "posterUrl": movie.get("posterUrl"),
                        "runtime": movie.get("runtime"),
                        "genreName": movie.get("genreName"),
                        "releaseDate": movie.get("releaseDate"),
                        "averageRating": movie.get("averageRating"),
                        "compatibilityScore": movie["compatibilityScore"],
                    }
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

        now = datetime.utcnow()

        context_summary_parts = []
        if social_context:
            context_summary_parts.append(
                f"social={social_context['companionType']}"
            )
        if emotional_context:
            context_summary_parts.append(
                f"mood={emotional_context['moodDescription']}"
            )
        if requirement_context and requirement_context.get("availableTime"):
            context_summary_parts.append(
                f"availableTime={requirement_context['availableTime']}"
            )
        context_summary = ", ".join(context_summary_parts) if context_summary_parts else "general"

        context_extracted = {
            "snapshotID": context_snapshot_id,
            "requestTimestamp": now,
            "userIntent": query,
            "hourOfDay": now.hour,
            "dayOfWeek": now.strftime("%A"),
            "socialContext": social_context,
            "emotionalContext": emotional_context,
            "requirementContext": requirement_context,
        }

        llm_start = perf_counter()
        explanation = generate_recommendation_explanation(
            query=query,
            context_summary=context_summary,
            movies_with_scores=movies_with_scores,
        )
        timings["llmExplanation"] = elapsed_ms(llm_start)

        execution_time_ms = max(1, elapsed_ms(total_start))

        response = {
            "query": query,
            "contextExtracted": context_extracted,
            "rdfGenerated": rdf_generated,
            "sparqlQuery": sparql_query,
            "moviesFound": len(movies_with_scores),
            "moviesWithScores": movies_with_scores,
            "explanation": explanation,
            "executionTimeMs": execution_time_ms,
        }

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
                    fallbackUsed=not recommendation_source.startswith("fuseki"),
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

        debug_payload = {
            "source": recommendation_source,
            "fusekiRows": fuseki_rows_count,
            "fallbackUsed": not recommendation_source.startswith("fuseki"),
            "errors": debug_errors,
            "timingsMs": timings,
        }

        return response, debug_payload

    def update_scoring_weights_from_metrics(self, user_id: str | None = None) -> None:
        """Closed feedback loop: adjust scoring weights based on recent metric observations.

        Uses ``moviesFound`` and ``fallbackUsed`` as engagement proxies since explicit
        click/watch signals are not yet stored in RecommendationMetric.
        """
        try:
            recent = self.metrics_use_case.list_recent(limit=100)
        except Exception:
            return

        if not recent:
            return

        total = len(recent)
        fallback_count = sum(1 for m in recent if m.fallbackUsed)
        avg_movies_found = sum(m.moviesFound for m in recent) / total
        fallback_rate = fallback_count / total

        # High fallback rate → strict SPARQL filters are too narrow → trust rating more
        if fallback_rate > 0.3:
            self.scoring_weights["rating"] = min(
                0.75, self.scoring_weights.get("rating", 0.58) + 0.04
            )
            self.scoring_weights["degree"] = max(
                0.25, self.scoring_weights.get("degree", 0.42) - 0.04
            )

        # Good result volume → boost freshness to surface newer films
        if avg_movies_found >= 4.0:
            self.scoring_weights["freshness"] = min(
                0.15, self.scoring_weights.get("freshness", 0.08) + 0.02
            )

        # Poor result volume → reduce freshness penalty, lean on rating
        if avg_movies_found < 2.0:
            self.scoring_weights["freshness"] = max(
                0.0, self.scoring_weights.get("freshness", 0.08) - 0.02
            )
            self.scoring_weights["rating"] = min(
                0.80, self.scoring_weights.get("rating", 0.58) + 0.02
            )
