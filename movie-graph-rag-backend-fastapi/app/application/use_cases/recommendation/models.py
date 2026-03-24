"""Core models for recommendation system"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional


@dataclass
class MovieRecommendation:
    """Single movie recommendation with score"""
    movieUri: str
    title: str
    score: float
    genres: list[str] = field(default_factory=list)
    rating: Optional[float] = None
    year: Optional[int] = None
    runtime: Optional[int] = None
    posterUrl: Optional[str] = None
    moodMatchScore: Optional[float] = None
    socialMatchScore: Optional[float] = None
    energyMatchScore: Optional[float] = None
    timeMatchScore: Optional[float] = None


@dataclass
class DebugInfo:
    """Debug information for recommendations"""
    contextExtracted: dict[str, Any]
    rdfGenerated: str
    sparqlQuery: str
    fusekiResultsCount: int
    executionTimeMs: int
    fallbackUsed: bool = False
    strategy: str = "direct_sparql"


@dataclass
class RecommendationResult:
    """Complete recommendation result"""
    query: str
    moviesWithScores: list[MovieRecommendation]
    explanation: str
    totalMoviesFound: int
    executionTimeMs: int
    contextExtracted: dict[str, Any]
    rdfGenerated: str
    sparqlQuery: str
    debugInfo: Optional[DebugInfo] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response"""
        result = {
            "query": self.query,
            "moviesWithScores": [asdict(m) for m in self.moviesWithScores],
            "explanation": self.explanation,
            "moviesFound": self.totalMoviesFound,
            "executionTimeMs": self.executionTimeMs,
            "contextExtracted": self.contextExtracted,
            "rdfGenerated": self.rdfGenerated,
            "sparqlQuery": self.sparqlQuery,
        }
        if self.debugInfo:
            result["debugPayload"] = asdict(self.debugInfo)
        return result
