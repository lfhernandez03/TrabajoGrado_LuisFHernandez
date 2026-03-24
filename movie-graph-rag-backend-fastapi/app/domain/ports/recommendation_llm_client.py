from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from app.domain.entities.query_context import QueryContext

if TYPE_CHECKING:
    from app.domain.entities.recommendation_models import UserContext


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

    def generate_recommendation_explanation(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
        semantic_hint: str = "",
        query_type: str = "general",
    ) -> str:
        ...
