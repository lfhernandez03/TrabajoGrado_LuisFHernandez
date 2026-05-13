from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from app.domain.entities.query_context import QueryContext

if TYPE_CHECKING:
    from app.domain.entities.recommendation_models import UserContext, UserProfile


class RecommendationLlmClientPort(Protocol):
    def extract_query_context(self, query: str) -> QueryContext:
        """Legacy: extract context as QueryContext. Kept for backward compat."""
        ...

    def extract_user_context(
        self,
        query: str,
        now: datetime | None = None,
        session_id: str | None = None,
    ) -> "UserContext":
        """Extract context from a user query and return a fully populated UserContext.

        ``now`` is used for server-clock time_of_day injection.
        ``session_id`` is attached as-is (set by the API layer, not the LLM).
        Never raises — falls back to keyword extraction on any LLM failure.
        """
        ...

    def extract_user_context_with_profile(
        self,
        query: str,
        profile: "UserProfile",
        favorites_sample: list[str],
        recent_queries: list[str],
        topological_type: str,
        dominant_cluster_labels: list[str],
        accumulated_context: "UserContext | None",
        now: datetime | None = None,
        conversation_history: list[dict] | None = None,
    ) -> "UserContext":
        """Profile-aware NLU: infer intent from query enriched with user history.

        ``conversation_history`` is the full message list from the client
        (excluding the current user message). Used as a fallback when
        ``accumulated_context`` is None (e.g. after a server restart).

        Sets off_topic=True when the message is clearly not a movie query.
        Never raises — falls back to keyword extraction on any LLM failure.
        time_of_day is always injected from server clock, never from the LLM.
        """
        ...

    def generate_recommendation_explanation(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
        semantic_hint: str = "",
        query_type: str = "general",
    ) -> str:
        ...

    def generate_greeting_response(
        self,
        query: str,
        user_name: str | None = None,
        is_cold_start: bool = True,
    ) -> str:
        """Generate a friendly invitation response when the message is off-topic.

        Returns a short, warm reply in Spanish inviting the user to ask for a movie.
        Never raises — returns a hardcoded fallback on any LLM failure.
        """
        ...
