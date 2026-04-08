from datetime import datetime

from pydantic import BaseModel


class RecommendationMetricItemResponse(BaseModel):
    id: str
    userId: str
    query: str
    source: str
    fallbackUsed: bool
    fusekiRows: int
    errors: list[str]
    timingsMs: dict[str, int]
    moviesFound: int
    executionTimeMs: int
    createdAt: datetime | None = None


class RecommendationMetricSummaryResponse(BaseModel):
    sampleSize: int
    fallbackRate: float
    errorRate: float
    avgTotalMs: int
    avgFusekiMs: int
    sourceCounts: dict[str, int]


class AdminRecommendationMetricsResponse(BaseModel):
    summary: RecommendationMetricSummaryResponse
    recent: list[RecommendationMetricItemResponse]


class PipelineStatusResponse(BaseModel):
    status: str
    step: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    ontologies_loaded: int
    ontologies_total: int
    skipped_load: bool


class PipelineLoadResponse(BaseModel):
    accepted: bool
    message: str
    status: str
