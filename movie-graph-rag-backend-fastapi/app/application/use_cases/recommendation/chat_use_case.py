from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter

from app.core.metrics import ListMetrics, compute_metrics
from app.core.conversation_context import (
    get_time_of_day,
    merge_contexts,
    query_context_to_user_context,
    session_store,
)
from app.core.fuseki_client import execute_select_query
from app.core.profile_service import ProfileService
from app.core.query_strategy import build_strategy
from app.core.scorer import score_and_select
from app.domain.entities.recommendation_models import (
    ConversationTurn,
    Movie,
    UserContext,
)
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort

logger = logging.getLogger(__name__)

# Minimum candidates before trying the next strategy
_MIN_RESULTS = 5


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ChatResult:
    session_id: str
    movies: list[Movie]
    explanation: str
    strategy_used: str
    context: UserContext
    execution_ms: int
    metrics: ListMetrics | None = None
    debug: dict = field(default_factory=dict)

    @property
    def was_successful(self) -> bool:
        return len(self.movies) > 0


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

def _unique_movie_count(rows: list[dict]) -> int:
    """Count distinct movie URIs in a list of raw Fuseki rows."""
    return len({row.get("movie", "") for row in rows if row.get("movie", "")})


def _run_strategy(
    attempts: list[tuple[str, str]],
    min_results: int = _MIN_RESULTS,
) -> tuple[list[dict], str]:
    """Execute strategies in order until min_results unique movies are found.

    Counts unique ?movie URIs rather than raw rows so that a strategy with
    30 rows for a single movie does not incorrectly signal success.

    Returns ``(rows, strategy_name)``.  Returns ``([], "empty")`` if every
    attempt fails or returns fewer than min_results unique movies.
    """
    for name, sparql in attempts:
        try:
            rows = execute_select_query(sparql)
            if _unique_movie_count(rows) >= min_results:
                return rows, name
        except Exception as exc:
            logger.warning("strategy '%s' failed: %s", name, exc)
    # Last resort: return whatever the final attempt yielded (even if < min)
    for name, sparql in reversed(attempts):
        try:
            rows = execute_select_query(sparql)
            if rows:
                return rows, name
        except Exception:
            pass
    return [], "empty"


def _query_type(ctx: UserContext, is_cold_start: bool) -> str:
    """Select the prompt type for Gemini's explanation generation."""
    if is_cold_start:
        return "cold_start"
    if ctx.mood:
        return "mood_driven"
    if ctx.companion:
        return "social"
    return "general"


# ---------------------------------------------------------------------------
# ChatUseCase
# ---------------------------------------------------------------------------

class ChatUseCase:
    """Conversational recommendation pipeline.

    Each call processes the full message history sent by the frontend,
    extracts context from the latest user turn, merges it with the accumulated
    session context, and returns a fresh set of recommendations.

    This is the first use case to use the Phase 2 core components
    (query_strategy, scorer, profile_service) end-to-end.
    """

    def __init__(
        self,
        llm_client: RecommendationLlmClientPort,
        profile_service: ProfileService,
    ) -> None:
        self._llm = llm_client
        self._profile_svc = profile_service

    def execute(
        self,
        session_id: str,
        messages: list[dict],  # [{"role": "user"|"assistant", "content": str}, ...]
        user_id: str,
    ) -> ChatResult:
        start = perf_counter()
        now = datetime.utcnow()

        # ── 1. Extract last user message ────────────────────────────────────
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return ChatResult(
                session_id=session_id,
                movies=[],
                explanation="No se encontró ningún mensaje del usuario en la conversación.",
                strategy_used="empty",
                context=UserContext(session_id=session_id),
                execution_ms=0,
            )
        last_query = user_messages[-1]["content"]

        # ── 2. NLU: extract context from last user message ──────────────────
        try:
            qctx = self._llm.extract_query_context(last_query)
            new_ctx = query_context_to_user_context(
                qctx,
                raw_query=last_query,
                session_id=session_id,
                now=now,
            )
        except Exception as exc:
            logger.warning("NLU extraction failed: %s — using bare context", exc)
            new_ctx = UserContext(
                session_id=session_id,
                time_of_day=get_time_of_day(now),
                raw_query=last_query,
                confidence=0.3,
            )

        # ── 3. Load session and merge contexts ──────────────────────────────
        session = session_store.get_or_create(session_id, user_id)
        accumulated = session.accumulated_context
        merged_ctx = merge_contexts(accumulated, new_ctx)

        # ── 4. Load user profile ────────────────────────────────────────────
        profile = self._profile_svc.get(user_id)

        # ── 5. Build SPARQL strategy and run ───────────────────────────────
        attempts = build_strategy(merged_ctx, profile)
        candidates, strategy_used = _run_strategy(attempts)

        # ── 6. Score and select with MMR ────────────────────────────────────
        movies = score_and_select(candidates, merged_ctx, profile, n=5)
        metrics = compute_metrics(movies, profile)

        # ── 7. Generate explanation ─────────────────────────────────────────
        query_type = _query_type(merged_ctx, profile.is_cold_start)
        context_summary = _build_context_summary(merged_ctx)
        movies_payload = [m.to_response_dict() for m in movies]

        try:
            explanation = self._llm.generate_recommendation_explanation(
                query=last_query,
                context_summary=context_summary,
                movies_with_scores=movies_payload,
                semantic_hint=query_type,
                query_type=query_type,
            )
        except Exception as exc:
            logger.warning("Explanation generation failed: %s", exc)
            explanation = (
                f"Encontré {len(movies)} película(s) basándome en tu consulta."
                if movies
                else "No encontré películas que coincidan con tu consulta actual. Intenta ser más específico."
            )

        # ── 8. Update session ───────────────────────────────────────────────
        session.accumulated_context = merged_ctx
        session.add_turn(ConversationTurn(role="user", content=last_query, context=merged_ctx))
        if movies:
            assistant_msg = explanation[:200] + "..." if len(explanation) > 200 else explanation
            session.add_turn(ConversationTurn(role="assistant", content=assistant_msg))
        session_store.update(session)

        # ── 9. Archive context to Fuseki ────────────────────────────────────
        self._profile_svc.archive_context(user_id, merged_ctx)

        return ChatResult(
            session_id=session_id,
            movies=movies,
            explanation=explanation,
            strategy_used=strategy_used,
            context=merged_ctx,
            metrics=metrics,
            execution_ms=int((perf_counter() - start) * 1000),
            debug={
                "strategy_attempts": [n for n, _ in attempts],
                "candidates_found": len(candidates),
                "query_type": query_type,
                "is_cold_start": profile.is_cold_start,
                "metrics": {
                    "ild": metrics.ild,
                    "semantic_precision": metrics.semantic_precision,
                    "cold_start_threshold": metrics.cold_start_threshold,
                    "graph_diversity_score": metrics.graph_diversity_score,
                },
            },
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_context_summary(ctx: UserContext) -> str:
    parts: list[str] = []
    if ctx.mood:
        parts.append(f"Estado de ánimo: {ctx.mood}")
    if ctx.companion:
        parts.append(f"Compañía: {ctx.companion}")
    if ctx.genres:
        parts.append(f"Géneros: {', '.join(ctx.genres)}")
    if ctx.runtime_max:
        parts.append(f"Duración máxima: {ctx.runtime_max} min")
    if ctx.exclusions:
        parts.append(f"Excluir: {', '.join(ctx.exclusions)}")
    return "; ".join(parts) if parts else "consulta general"
