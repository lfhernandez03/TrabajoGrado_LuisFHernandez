from dataclasses import dataclass
from datetime import datetime


@dataclass
class RecommendationMetric:
    userId: str
    query: str
    source: str
    fallbackUsed: bool
    fusekiRows: int
    errors: list[str]
    timingsMs: dict[str, int]
    moviesFound: int
    executionTimeMs: int
    id: str | None = None
    createdAt: datetime | None = None
