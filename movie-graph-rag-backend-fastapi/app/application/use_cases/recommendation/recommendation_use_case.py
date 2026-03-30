from __future__ import annotations

import logging
from time import perf_counter

from app.core.connection_explorer import ConnectionExplorer
from app.core.fuseki_client import execute_select_query
from app.core.metrics import ListMetrics, compute_metrics
from app.core.profile_service import ProfileService
from app.core.query_strategy import build_strategy
from app.core.scorer import score_and_select
from app.domain.entities.recommendation_models import Movie, UserContext
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort

logger = logging.getLogger(__name__)

_MIN_RESULTS = 5


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

    def get_recommendation(self, query: str, user_id: str) -> dict:
        return self._run(query, user_id).to_api_dict()

    def get_recommendation_debug(self, query: str, user_id: str) -> dict:
        result = self._run(query, user_id)
        d = result.to_api_dict()
        d["debugPayload"] = result.debug
        return d

    # ── Pipeline ────────────────────────────────────────────────────────────

    def _run(self, query: str, user_id: str) -> _Result:
        start = perf_counter()

        ctx = self._llm.extract_user_context(query)
        profile = self._profile_svc.get(user_id)

        attempts = build_strategy(ctx, profile)
        candidates, strategy = _run_strategy(attempts)
        movies = score_and_select(candidates, ctx, profile, n=5)
        explorer = ConnectionExplorer()
        metrics = compute_metrics(movies, profile, explorer=explorer)

        query_type = _query_type(ctx, profile.is_cold_start)
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
                f"Encontré {len(movies)} película(s) que coinciden con tu consulta."
                if movies
                else "No encontré películas para esta consulta. Intenta con términos más generales."
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
