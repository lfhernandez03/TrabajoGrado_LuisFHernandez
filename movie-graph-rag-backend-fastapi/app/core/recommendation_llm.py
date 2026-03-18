from app.adapters.llm.gemini_recommendation_llm_adapter import GeminiRecommendationLlmAdapter
from app.domain.entities.query_context import QueryContext


_default_llm_adapter = GeminiRecommendationLlmAdapter()


def extract_query_context(query: str) -> QueryContext:
    return _default_llm_adapter.extract_query_context(query)


def generate_recommendation_explanation(
    query: str,
    context_summary: str,
    movies_with_scores: list[dict],
    semantic_hint: str = "",
    query_type: str = "general",
) -> str:
    return _default_llm_adapter.generate_recommendation_explanation(
        query=query,
        context_summary=context_summary,
        movies_with_scores=movies_with_scores,
        semantic_hint=semantic_hint,
        query_type=query_type,
    )
