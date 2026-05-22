from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    novelty: float = 0.5
    """Average genre novelty (0–1). Higher = recommendations from genres rare in user history."""
    ontoRecall: float = 1.0
    """Fraction of semantically-compatible candidates (bridge ontology) recovered in final list."""


# ---------------------------------------------------------------------------
# Metrics report (batch evaluation across multiple queries)
# ---------------------------------------------------------------------------

class MetricsReportRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "queries": [
                "I want an intense action movie for tonight",
                "A romantic comedy to watch with my partner",
                "Psychological horror, something disturbing and tense",
                "Epic science fiction, something like Interstellar",
                "An animated movie to watch with young children",
                "A historical drama from the 90s, something deep",
                "Something short and fun, under 90 minutes",
                "A suspense thriller to watch alone late at night",
                "Recommend me something different I haven't seen, surprise me",
                "An adventure movie for the whole family this weekend",
            ]
        }
    })

    queries: list[str] = Field(..., min_length=1, max_length=20)
    """Test queries to evaluate (1–20). Each runs through the full pipeline."""


class MetricsReportQueryResult(BaseModel):
    query: str
    ild: float
    graphDiversityScore: float
    semanticPrecision: float
    novelty: float
    ontoRecall: float
    coldStartThreshold: int
    movieCount: int
    strategy: str
    isColdStart: bool
    executionMs: int
    movies: list[str]
    """Titles of recommended movies for this query."""


class MetricsReportSummary(BaseModel):
    queriesEvaluated: int
    avgILD: float
    avgGraphDiversity: float
    avgSemanticPrecision: float
    avgNovelty: float
    avgOntoRecall: float
    minILD: float
    maxILD: float
    coldStartDetections: int


class MetricsReportResponse(BaseModel):
    summary: MetricsReportSummary
    perQuery: list[MetricsReportQueryResult]


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Shared movie shape (used by both single-turn and chat endpoints)
# ---------------------------------------------------------------------------

class RecommendedMovieResponse(BaseModel):
    uri: str | None = None
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
    serendipityScore: float = 0.0
    """Topological serendipity: compatibility x (1-clustering) x betweenness x (1-degree), scaled [0,1]."""
    description: str | None = None


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
    isColdStart: bool = False
    """True when the user has fewer context snapshots than the cold-start threshold."""
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
    sparql_query: str = ""
    context_extracted: dict[str, Any]
    execution_ms: int
    turn_count: int = 0
    metrics: RecommendationMetricsResponse | None = None
