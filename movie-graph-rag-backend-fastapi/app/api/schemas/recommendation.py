from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1)


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

