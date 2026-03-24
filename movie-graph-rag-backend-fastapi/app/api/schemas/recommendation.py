from typing import Any

from pydantic import BaseModel, Field


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
