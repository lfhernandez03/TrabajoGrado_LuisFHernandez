from app.domain.entities.query_history import QueryHistory
from app.domain.ports.query_history_repository import QueryHistoryRepositoryPort


class QueryHistoryUseCase:
    def __init__(self, repository: QueryHistoryRepositoryPort) -> None:
        self.repository = repository

    def create_entry(self, data: QueryHistory) -> QueryHistory:
        return self.repository.create_entry(data)

    def find_by_user(self, user_id: str, limit: int = 10) -> list[QueryHistory]:
        return self.repository.find_by_user(user_id=user_id, limit=limit)

    def find_one(self, history_id: str) -> QueryHistory | None:
        return self.repository.find_one(history_id)
