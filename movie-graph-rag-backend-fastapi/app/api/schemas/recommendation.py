from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Chat (Phase 2.5)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    messages: list[ChatMessage] = Field(..., min_length=1)


class ChatMovieResponse(BaseModel):
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


class ChatResponse(BaseModel):
    session_id: str
    movies: list[ChatMovieResponse]
    explanation: str
    strategy_used: str
    context_extracted: dict[str, Any]
    execution_ms: int
    turn_count: int = 0


class RecommendedMovieResponse(BaseModel):
    movieUri: str
    title: str
    score: float
    genres: list[str] = []
    rating: float | None = None
    year: int | None = None
    runtime: int | None = None
    posterUrl: str | None = None


class RecommendationResponse(BaseModel):
    query: str
    contextExtracted: dict[str, Any]
    rdfGenerated: str
    sparqlQuery: str
    moviesFound: int
    moviesWithScores: list[RecommendedMovieResponse]
    explanation: str
    executionTimeMs: int
    debugPayload: dict[str, Any] | None = None


class RecommendationDebugResponse(BaseModel):
    query: str
    contextExtracted: dict[str, Any]
    rdfGenerated: str
    sparqlQuery: str
    moviesFound: int
    moviesWithScores: list[RecommendedMovieResponse]
    explanation: str
    executionTimeMs: int
    debugPayload: dict[str, Any] | None = None

