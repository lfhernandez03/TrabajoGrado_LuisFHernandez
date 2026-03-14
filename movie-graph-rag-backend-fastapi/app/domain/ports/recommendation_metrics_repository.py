from app.domain.entities.recommendation_metric import RecommendationMetric


class RecommendationMetricsRepositoryPort:
    def create_entry(self, data: RecommendationMetric) -> RecommendationMetric:
        raise NotImplementedError

    def list_recent(self, limit: int = 50) -> list[RecommendationMetric]:
        raise NotImplementedError

    def get_summary(self, limit: int = 200) -> dict:
        raise NotImplementedError
