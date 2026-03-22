from app.domain.entities.recommendation_metric import RecommendationMetric
from app.domain.ports.recommendation_metrics_repository import (
    RecommendationMetricsRepositoryPort,
)


class RecommendationMetricsUseCase:
    def __init__(self, repository: RecommendationMetricsRepositoryPort) -> None:
        self.repository = repository

    def create_entry(self, data: RecommendationMetric) -> RecommendationMetric:
        return self.repository.create_entry(data)

    def list_recent(self, limit: int = 50) -> list[RecommendationMetric]:
        return self.repository.list_recent(limit=limit)

    def get_summary(self, limit: int = 200) -> dict:
        return self.repository.get_summary(limit=limit)
