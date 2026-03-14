from app.domain.entities.query_history import QueryHistory


class QueryHistoryRepositoryPort:
    def create_entry(self, data: QueryHistory) -> QueryHistory:
        raise NotImplementedError

    def find_by_user(self, user_id: str, limit: int = 10) -> list[QueryHistory]:
        raise NotImplementedError

    def find_one(self, history_id: str) -> QueryHistory | None:
        raise NotImplementedError
