from typing import Protocol

from app.domain.entities.query_context import QueryContext


class RecommendationLlmClientPort(Protocol):
    def extract_query_context(self, query: str) -> QueryContext:
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
