from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1)


class SocialContext(BaseModel):
    companionType: str
    hasChildren: bool
    numberOfPeople: int | None = None


class EmotionalContext(BaseModel):
    moodDescription: str
    desiredEnergyLevel: str


class RequirementContext(BaseModel):
    availableTime: int | None = None
    excludedGenre: list[str] | None = None


class ContextExtractedResponse(BaseModel):
    snapshotID: str
    requestTimestamp: datetime
    userIntent: str
    hourOfDay: int
    dayOfWeek: str
    socialContext: SocialContext | None = None
    emotionalContext: EmotionalContext | None = None
    requirementContext: RequirementContext | None = None


class RecommendedMovieResponse(BaseModel):
    title: str
    posterUrl: str | None = None
    runtime: int | None = None
    genreName: str | None = None
    releaseDate: str | None = None
    averageRating: float | None = None
    compatibilityScore: float | None = None


class RecommendationResponse(BaseModel):
    query: str
    contextExtracted: ContextExtractedResponse
    rdfGenerated: str
    sparqlQuery: str
    moviesFound: int
    moviesWithScores: list[RecommendedMovieResponse]
    explanation: str
    executionTimeMs: int
    debugPayload: dict | None = None


class RecommendationDebugTimings(BaseModel):
    contextExtraction: int
    rdfAndSparqlBuild: int
    fusekiQuery: int
    scoring: int
    llmExplanation: int
    historyWrite: int
    total: int


class RecommendationDebugMeta(BaseModel):
    source: str
    fusekiRows: int
    fallbackUsed: bool
    contextGraphInjected: bool | None = None
    errors: list[str]
    timingsMs: RecommendationDebugTimings


class RecommendationDebugResponse(BaseModel):
    recommendation: RecommendationResponse
    debug: RecommendationDebugMeta
