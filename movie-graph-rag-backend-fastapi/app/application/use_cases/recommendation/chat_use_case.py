from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
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
from app.domain.ports.user_favorites_repository import UserFavoritesRepositoryPort
from app.domain.ports.query_history_repository import QueryHistoryRepositoryPort

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
    sparql_query: str = ""
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
) -> tuple[list[dict], str, str]:
    """Execute strategies in order until min_results unique movies are found.

    Counts unique ?movie URIs rather than raw rows so that a strategy with
    30 rows for a single movie does not incorrectly signal success.

    Returns ``(rows, strategy_name, sparql_query)``.  Returns ``([], "empty", "")`` if every
    attempt fails or returns fewer than min_results unique movies.
    """
    for name, sparql in attempts:
        try:
            rows = execute_select_query(sparql)
            if _unique_movie_count(rows) >= min_results:
                return rows, name, sparql
        except Exception as exc:
            logger.warning("strategy '%s' failed: %s", name, exc)
    # Last resort: return whatever the final attempt yielded (even if < min)
    for name, sparql in reversed(attempts):
        try:
            rows = execute_select_query(sparql)
            if rows:
                return rows, name, sparql
        except Exception:
            pass
    return [], "empty", ""


def _query_type(ctx: UserContext, is_cold_start: bool) -> str:
    """Select the prompt type for the explanation generation."""
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
    """Conversational recommendation pipeline with Graph RAG integration.

    Each call processes the full message history sent by the frontend,
    fetches the user's profile and topological graph data BEFORE NLU,
    runs a profile-aware NLU extraction, then builds SPARQL strategies that
    include community-based graph traversal.
    """

    def __init__(
        self,
        llm_client: RecommendationLlmClientPort,
        profile_service: ProfileService,
        favorites_repo: UserFavoritesRepositoryPort,
        query_history_repo: QueryHistoryRepositoryPort,
    ) -> None:
        self._llm = llm_client
        self._profile_svc = profile_service
        self._favorites_repo = favorites_repo
        self._query_history_repo = query_history_repo

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
                explanation="No user message found in the conversation.",
                strategy_used="empty",
                context=UserContext(session_id=session_id),
                execution_ms=0,
            )
        last_query = user_messages[-1]["content"]

        # ── 2. Fetch favorites (needed for topo profile + NLU enrichment) ───
        favorites_raw = self._get_favorites_raw(user_id, limit=10)
        favorites_titles = [f.title for f in favorites_raw if f.title]

        # ── 3. Load basic profile (cached, fast) and enrich genre_weights ─────
        profile = self._profile_svc.get(user_id)
        genre_weights = self._profile_svc.build_genre_weights(favorites_raw)
        if genre_weights:
            profile = replace(profile, genre_weights=genre_weights)

        # ── 4. Get topological profile (requires favorites_raw) ─────────────
        dominant_cluster_ids: list[str] = []
        adjacent_cluster_ids: list[str] = []
        topological_type = "balanced"
        dominant_cluster_labels: list[str] = []
        topo_profile = None

        try:
            topo_profile = self._profile_svc.get_topological_profile(user_id, favorites_raw)
            dominant_cluster_ids = [c.clusterId for c in topo_profile.dominantClusters]
            adjacent_cluster_ids = [c.clusterId for c in topo_profile.unexploredAdjacent]
            topological_type = topo_profile.userType
            dominant_cluster_labels = [c.label for c in topo_profile.dominantClusters[:3]]
        except Exception as exc:
            logger.warning("get_topological_profile failed for %s: %s", user_id, exc)

        # ── 5. Load session (before NLU to pass accumulated_context) ────────
        session = session_store.get_or_create(session_id, user_id)
        accumulated = session.accumulated_context

        # ── 6. Profile-aware NLU ─────────────────────────────────────────────
        try:
            recent_queries = self._get_recent_queries(user_id, limit=5)
            new_ctx = self._llm.extract_user_context_with_profile(
                query=last_query,
                profile=profile,
                favorites_sample=favorites_titles,
                recent_queries=recent_queries,
                topological_type=topological_type,
                dominant_cluster_labels=dominant_cluster_labels,
                accumulated_context=accumulated,
                now=now,
            )
            new_ctx = replace(new_ctx, session_id=session_id)
        except Exception as exc:
            logger.warning("Profile-aware NLU failed: %s — bare context fallback", exc)
            new_ctx = UserContext(
                session_id=session_id,
                time_of_day=get_time_of_day(now),
                raw_query=last_query,
                confidence=0.3,
            )

        # ── 6b. Short-circuit if message is off-topic ────────────────────────
        if new_ctx.off_topic:
            try:
                greeting = self._llm.generate_greeting_response(
                    query=last_query,
                    is_cold_start=profile.is_cold_start,
                )
            except Exception:
                greeting = (
                    "Hello! I'm CineGraph. Tell me what kind of movie you're looking for "
                    "and I'll help you find the perfect one. For example: "
                    "'something funny for tonight' or 'intense action movie'."
                )
            return ChatResult(
                session_id=session_id,
                movies=[],
                explanation=greeting,
                strategy_used="off_topic",
                context=new_ctx,
                execution_ms=int((perf_counter() - start) * 1000),
                debug={"off_topic": True, "original_query": last_query},
            )

        # ── 7. Merge session context ─────────────────────────────────────────
        merged_ctx = merge_contexts(accumulated, new_ctx)

        # ── 8. Build SPARQL strategy with cluster IDs ────────────────────────
        # Exclude movies already shown in previous turns so the user always gets
        # fresh recommendations, not the same titles repeated.
        query_ctx = merged_ctx
        if session.recommended_titles:
            seen = {t.strip().lower() for t in session.recommended_titles if t.strip()}
            existing_excl = {e.strip().lower() for e in (merged_ctx.exclusions or []) if e.strip()}
            query_ctx = replace(merged_ctx, exclusions=list(existing_excl | seen))

        attempts = build_strategy(
            query_ctx,
            profile,
            dominant_cluster_ids=dominant_cluster_ids or None,
            adjacent_cluster_ids=adjacent_cluster_ids or None,
        )
        candidates, strategy_used, sparql_query = _run_strategy(attempts)

        # ── 9. Score and select with graph_affinity ──────────────────────────
        movies = score_and_select(
            candidates,
            merged_ctx,
            profile,
            n=5,
            dominant_cluster_ids=dominant_cluster_ids or None,
            adjacent_cluster_ids=adjacent_cluster_ids or None,
        )
        metrics = compute_metrics(movies, profile)

        # ── 10. Generate explanation with enriched context ───────────────────
        query_type = _query_type(merged_ctx, profile.is_cold_start)
        context_summary = _build_context_summary_with_graph(
            merged_ctx, topo_profile, favorites_titles[:3]
        )
        movies_payload = [m.to_response_dict() for m in movies]

        try:
            explanation = self._llm.generate_recommendation_explanation(
                query=last_query,
                context_summary=context_summary,
                movies_with_scores=movies_payload,
                semantic_hint=strategy_used,
                query_type=query_type,
            )
        except Exception as exc:
            logger.warning("Explanation generation failed: %s", exc)
            explanation = (
                f"Found {len(movies)} movie(s) based on your query."
                if movies
                else "No movies found matching your query. Try being more specific."
            )

        # ── 11. Update session ───────────────────────────────────────────────
        session.accumulated_context = merged_ctx
        session.add_turn(ConversationTurn(role="user", content=last_query, context=merged_ctx))
        if movies:
            assistant_msg = explanation[:200] + "..." if len(explanation) > 200 else explanation
            session.add_turn(ConversationTurn(role="assistant", content=assistant_msg))
            new_titles = [m.title for m in movies if m.title]
            session.recommended_titles.extend(new_titles)
        session_store.update(session)

        # ── 12. Archive context to Fuseki ────────────────────────────────────
        self._profile_svc.archive_context(user_id, merged_ctx)

        return ChatResult(
            session_id=session_id,
            movies=movies,
            explanation=explanation,
            strategy_used=strategy_used,
            sparql_query=sparql_query,
            context=merged_ctx,
            metrics=metrics,
            execution_ms=int((perf_counter() - start) * 1000),
            debug={
                "strategy_attempts": [n for n, _ in attempts],
                "candidates_found": len(candidates),
                "query_type": query_type,
                "is_cold_start": profile.is_cold_start,
                "graph_rag": {
                    "dominant_cluster_ids": dominant_cluster_ids,
                    "adjacent_cluster_ids": adjacent_cluster_ids,
                    "topological_type": topological_type,
                    "topo_profile_available": topo_profile is not None,
                },
                "metrics": {
                    "ild": metrics.ild,
                    "semantic_precision": metrics.semantic_precision,
                    "cold_start_threshold": metrics.cold_start_threshold,
                    "graph_diversity_score": metrics.graph_diversity_score,
                },
            },
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _get_favorites_raw(self, user_id: str, limit: int = 10) -> list:
        """Return the user's most recent FavoriteMovie objects. Never raises."""
        try:
            return self._favorites_repo.get_favorites(user_id)[:limit]
        except Exception as exc:
            logger.warning("_get_favorites_raw failed for %s: %s", user_id, exc)
            return []

    def _get_recent_queries(self, user_id: str, limit: int = 5) -> list[str]:
        """Return the raw query strings from recent history. Never raises."""
        try:
            entries = self._query_history_repo.find_by_user(user_id, limit=limit)
            return [e.query for e in entries if e.query]
        except Exception as exc:
            logger.warning("_get_recent_queries failed for %s: %s", user_id, exc)
            return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_context_summary(ctx: UserContext) -> str:
    parts: list[str] = []
    if ctx.mood:
        parts.append(f"Mood: {ctx.mood}")
    if ctx.companion:
        parts.append(f"Companion: {ctx.companion}")
    if ctx.genres:
        parts.append(f"Genres: {', '.join(ctx.genres)}")
    if ctx.runtime_max:
        parts.append(f"Max runtime: {ctx.runtime_max} min")
    if ctx.exclusions:
        parts.append(f"Exclude: {', '.join(ctx.exclusions)}")
    return "; ".join(parts) if parts else "general query"


def _build_context_summary_with_graph(
    ctx: UserContext,
    topo_profile,           # TopologicalProfileResponse | None
    favorites_sample: list[str],
) -> str:
    """Extended context summary including graph topology for the explanation LLM."""
    base = _build_context_summary(ctx)
    extras: list[str] = []
    if favorites_sample:
        extras.append(f"Recent favorites: {', '.join(favorites_sample)}")
    if topo_profile:
        if topo_profile.dominantClusters:
            top = topo_profile.dominantClusters[0]
            extras.append(f"Main cluster: {top.label} ({top.moviesSeen} movies)")
        extras.append(f"Profile: {topo_profile.userType}")
    return "; ".join([base] + extras) if extras else base
