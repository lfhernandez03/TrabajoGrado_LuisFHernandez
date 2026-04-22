from __future__ import annotations

import logging
from time import perf_counter

from app.core.fuseki_client import execute_select_query
from app.core.metrics import ListMetrics, compute_metrics
from app.core.profile_service import ProfileService
from app.core.query_strategy import build_strategy
from app.core.scorer import score_and_select
from app.domain.entities.recommendation_models import Movie, UserContext
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort

logger = logging.getLogger(__name__)

_MIN_RESULTS = 5
_COLD_START_MMR_LAMBDA = 0.45   # diversity > relevance when no known preferences


def _unique_movie_count(rows: list[dict]) -> int:
    """Count distinct movie URIs in a list of raw Fuseki rows.

    A single movie can appear multiple times when it has several genre
    assignments (each ?genreName produces a separate row despite SELECT
    DISTINCT).  Using URI count instead of row count avoids treating 30
    rows for 1 movie as a successful strategy result.
    """
    return len({row.get("movie", "") for row in rows if row.get("movie", "")})


def _run_strategy(attempts: list[tuple[str, str]]) -> tuple[list[dict], str]:
    """Execute attempts in order until >= _MIN_RESULTS unique movies are found."""
    for name, sparql in attempts:
        try:
            rows = execute_select_query(sparql)
            if _unique_movie_count(rows) >= _MIN_RESULTS:
                return rows, name
        except Exception as exc:
            logger.warning("strategy '%s' failed: %s", name, exc)
    # Last pass: return first non-empty result even if below min
    for name, sparql in reversed(attempts):
        try:
            rows = execute_select_query(sparql)
            if rows:
                return rows, name
        except Exception:
            pass
    return [], "empty"


def _run_cold_start_strategy(attempts: list[tuple[str, str]]) -> tuple[list[dict], str]:
    """Aggregate candidates from ALL genre strategies for cold start.

    Unlike _run_strategy(), does not stop at the first hit with >= _MIN_RESULTS.
    Accumulates candidates from multiple genres so the scorer has real diversity.
    Stops when >= 40 unique movies are found or the fallbacks ('centrality_ranking', 'broad') are reached.
    """
    all_rows: list[dict] = []
    seen_uris: set[str] = set()
    names_used: list[str] = []

    for name, sparql in attempts:
        if name in ("centrality_ranking", "broad"):
            break  # fallbacks only if aggregation did not reach the minimum
        try:
            rows = execute_select_query(sparql)
            new_rows = [r for r in rows if r.get("movie", "") not in seen_uris]
            for r in new_rows:
                seen_uris.add(r.get("movie", ""))
            all_rows.extend(new_rows)
            names_used.append(name)
            if len(seen_uris) >= 40:
                break
        except Exception as exc:
            logger.warning("cold-start strategy '%s' failed: %s", name, exc)

    if _unique_movie_count(all_rows) >= _MIN_RESULTS:
        return all_rows, "+".join(names_used) if names_used else "cold_start_merged"

    # Fallback to original behavior if not enough candidates were found
    return _run_strategy(attempts)


def _query_type(ctx: UserContext, is_cold_start: bool) -> str:
    if is_cold_start:
        return "cold_start"
    if ctx.mood:
        return "mood_driven"
    if ctx.companion:
        return "social"
    return "general"


def _context_summary(ctx: UserContext) -> str:
    parts = []
    if ctx.mood:
        parts.append(f"mood={ctx.mood}")
    if ctx.companion:
        parts.append(f"companion={ctx.companion}")
    if ctx.genres:
        parts.append(f"genres={','.join(ctx.genres)}")
    if ctx.runtime_max:
        parts.append(f"runtime_max={ctx.runtime_max}")
    return "; ".join(parts) if parts else "general"


class RecommendationUseCase:
    def __init__(
        self,
        llm_client: RecommendationLlmClientPort,
        profile_service: ProfileService,
    ) -> None:
        self._llm = llm_client
        self._profile_svc = profile_service

    def get_recommendation(self, query: str, user_id: str, n: int = 5, query_type_override: str | None = None) -> dict:
        return self._run(query, user_id, n=n, query_type_override=query_type_override).to_api_dict()

    def get_activity_recommendation(self, user_id: str) -> dict:
        """Deprecated: use endpoint's intelligent query building instead.
        
        This fallback is kept for backward compatibility.
        The /recommendation/activity endpoint now builds much smarter queries
        that use favorites, topological profile, and exploration metrics.
        """
        from datetime import datetime

        # Get user's profile for basic fallback personalization
        profile = self._profile_svc.get(user_id)
        
        # Base time-of-day query
        hour = datetime.now().hour
        if 6 <= hour < 12:
            time_query = "to watch in the morning"
        elif 12 <= hour < 18:
            time_query = "to watch in the afternoon"
        else:
            time_query = "to watch in the evening"

        # Enrich query with user's preferred genres
        enrichment = ""
        if profile and profile.genre_weights and not profile.is_cold_start:
            # Get top 2 genres by weight
            top_genres = sorted(profile.genre_weights.items(), key=lambda x: x[1], reverse=True)[:2]
            if top_genres:
                genre_names = [g[0] for g in top_genres]
                enrichment = f" in the {' or '.join(genre_names)} genre"

        query = f"Recommend me a movie {time_query}{enrichment}"
        return self._run(query, user_id).to_api_dict()

    def get_recommendation_debug(self, query: str, user_id: str) -> dict:
        result = self._run(query, user_id)
        d = result.to_api_dict()
        d["debugPayload"] = result.debug
        return d

    # ── Pipeline ────────────────────────────────────────────────────────────

    def _run(self, query: str, user_id: str, n: int = 5, query_type_override: str | None = None) -> _Result:
        start = perf_counter()

        ctx = self._llm.extract_user_context(query)
        profile = self._profile_svc.get(user_id)

        attempts = build_strategy(ctx, profile)
        if profile.is_cold_start:
            candidates, strategy = _run_cold_start_strategy(attempts)
            movies = score_and_select(candidates, ctx, profile, n=n,
                                      mmr_lambda=_COLD_START_MMR_LAMBDA)
        else:
            candidates, strategy = _run_strategy(attempts)
            movies = score_and_select(candidates, ctx, profile, n=n)
        metrics = compute_metrics(movies, profile)

        query_type = query_type_override or _query_type(ctx, profile.is_cold_start)
        explanation = self._explain(query, ctx, movies, query_type)

        self._profile_svc.archive_context(user_id, ctx)

        return _Result(
            query=query,
            movies=movies,
            explanation=explanation,
            strategy_used=strategy,
            sparql_executed=attempts[0][1] if attempts else "",
            candidates_found=len(candidates),
            context=ctx,
            metrics=metrics,
            execution_ms=int((perf_counter() - start) * 1000),
            debug={
                "strategy_used": strategy,
                "strategy_attempts": [n for n, _ in attempts],
                "candidates_found": len(candidates),
                "query_type": query_type,
                "is_cold_start": profile.is_cold_start,
                "context": {
                    "mood": ctx.mood,
                    "companion": ctx.companion,
                    "genres": ctx.genres,
                    "runtime_max": ctx.runtime_max,
                    "confidence": ctx.confidence,
                },
                "metrics": {
                    "ild": metrics.ild,
                    "semantic_precision": metrics.semantic_precision,
                    "cold_start_threshold": metrics.cold_start_threshold,
                    "graph_diversity_score": metrics.graph_diversity_score,
                },
            },
        )

    def _explain(
        self,
        query: str,
        ctx: UserContext,
        movies: list[Movie],
        query_type: str,
    ) -> str:
        try:
            return self._llm.generate_recommendation_explanation(
                query=query,
                context_summary=_context_summary(ctx),
                movies_with_scores=[m.to_response_dict() for m in movies],
                semantic_hint=query_type,
                query_type=query_type,
            )
        except Exception as exc:
            logger.warning("explanation generation failed: %s", exc)
            return (
                f"Found {len(movies)} movie(s) matching your query."
                if movies
                else "No movies found for this query. Try using more general terms."
            )


# ---------------------------------------------------------------------------
# Internal result type (not exported — API layer uses to_api_dict())
# ---------------------------------------------------------------------------

class _Result:
    def __init__(
        self,
        query: str,
        movies: list[Movie],
        explanation: str,
        strategy_used: str,
        sparql_executed: str,
        candidates_found: int,
        context: UserContext,
        metrics: ListMetrics,
        execution_ms: int,
        debug: dict,
    ) -> None:
        self.query = query
        self.movies = movies
        self.explanation = explanation
        self.strategy_used = strategy_used
        self.sparql_executed = sparql_executed
        self.candidates_found = candidates_found
        self.context = context
        self.metrics = metrics
        self.execution_ms = execution_ms
        self.debug = debug

    def to_api_dict(self) -> dict:
        return {
            "query": self.query,
            "isColdStart": self.debug.get("is_cold_start", False),
            "contextExtracted": {
                "mood": self.context.mood,
                "companion": self.context.companion,
                "has_children": self.context.has_children,
                "children_age_hint": self.context.children_age_hint,
                "energy": self.context.energy,
                "genres": self.context.genres,
                "runtime_max": self.context.runtime_max,
                "exclusions": self.context.exclusions,
                "confidence": self.context.confidence,
                "time_of_day": self.context.time_of_day,
            },
            "rdfGenerated": "",
            "sparqlQuery": self.sparql_executed,
            "moviesFound": self.candidates_found,
            "moviesWithScores": [m.to_response_dict() for m in self.movies],
            "explanation": self.explanation,
            "executionTimeMs": self.execution_ms,
            "metrics": {
                "ild": self.metrics.ild,
                "graphDiversityScore": self.metrics.graph_diversity_score,
                "semanticPrecision": self.metrics.semantic_precision,
                "coldStartThreshold": self.metrics.cold_start_threshold,
                "movieCount": self.metrics.movie_count,
            },
        }
