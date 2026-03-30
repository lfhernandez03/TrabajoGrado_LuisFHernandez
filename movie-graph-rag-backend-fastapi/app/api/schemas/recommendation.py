from typing import Any

from pydantic import BaseModel, Field


class RecommendationMetricsResponse(BaseModel):
    """Quality metrics for a single recommendation list (Phase 5)."""

    ild: float
    """Intra-List Diversity (0–1). Higher = more genre variety."""
    graphDiversityScore: float = 0.0
    """Graph distance diversity — average BFS hops between recommended movies, normalized [0,1]."""
    semanticPrecision: float
    """Fraction of movies with compatibilityScore > 0.7."""
    coldStartThreshold: int
    """Adaptive minimum snapshots needed to exit cold-start mode."""
    movieCount: int


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Shared movie shape (used by both single-turn and chat endpoints)
# ---------------------------------------------------------------------------

class RecommendedMovieResponse(BaseModel):
    title: str
    posterUrl: str | None = None
    runtime: int | None = None
    genreName: str | None = None
    releaseDate: str | None = None
    averageRating: float | None = None
    compatibilityScore: float = 0.0
    moodMatchScore: float | None = None
    socialMatchScore: float | None = None
    energyMatchScore: float | None = None
    timeMatchScore: float | None = None
    kidFriendly: bool | None = None


# Alias so both endpoints share the same model class
ChatMovieResponse = RecommendedMovieResponse


# ---------------------------------------------------------------------------
# Single-turn recommendation
# ---------------------------------------------------------------------------

class RecommendationResponse(BaseModel):
    query: str
    contextExtracted: dict[str, Any]
    rdfGenerated: str = ""
    sparqlQuery: str
    moviesFound: int
    moviesWithScores: list[RecommendedMovieResponse]
    explanation: str
    executionTimeMs: int
    metrics: RecommendationMetricsResponse | None = None
    debugPayload: dict[str, Any] | None = None


class RecommendationDebugResponse(BaseModel):
    query: str
    contextExtracted: dict[str, Any]
    rdfGenerated: str = ""
    sparqlQuery: str
    moviesFound: int
    moviesWithScores: list[RecommendedMovieResponse]
    explanation: str
    executionTimeMs: int
    metrics: RecommendationMetricsResponse | None = None
    debugPayload: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Chat (Phase 2.5)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    messages: list[ChatMessage] = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    movies: list[ChatMovieResponse]
    explanation: str
    strategy_used: str
    context_extracted: dict[str, Any]
    execution_ms: int
    turn_count: int = 0
    metrics: RecommendationMetricsResponse | None = None
