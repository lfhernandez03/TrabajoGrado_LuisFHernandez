from datetime import datetime

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from app.domain.entities.query_history import QueryHistory
from app.domain.ports.query_history_repository import QueryHistoryRepositoryPort


class MongoQueryHistoryRepositoryAdapter(QueryHistoryRepositoryPort):
    def __init__(self, db: Database) -> None:
        self.collection: Collection = db["queryhistories"]
        self.collection.create_index("userId")
        self.collection.create_index("createdAt")

    def _to_entity(self, document: dict) -> QueryHistory:
        return QueryHistory(
            id=str(document["_id"]),
            userId=document["userId"],
            query=document["query"],
            rdfGenerated=document.get("rdfGenerated"),
            sparqlExecuted=document.get("sparqlExecuted"),
            contextExtracted=document.get("contextExtracted"),
            resultsFound=document.get("resultsFound"),
            explanation=document.get("explanation"),
            executionTimeMs=document.get("executionTimeMs"),
            wasSuccessful=document.get("wasSuccessful", True),
            createdAt=document.get("createdAt"),
            updatedAt=document.get("updatedAt"),
        )

    def _to_document(self, data: QueryHistory) -> dict:
        now = datetime.utcnow()
        return {
            "userId": data.userId,
            "query": data.query,
            "rdfGenerated": data.rdfGenerated,
            "sparqlExecuted": data.sparqlExecuted,
            "contextExtracted": data.contextExtracted,
            "resultsFound": data.resultsFound,
            "explanation": data.explanation,
            "executionTimeMs": data.executionTimeMs,
            "wasSuccessful": data.wasSuccessful,
            "createdAt": data.createdAt or now,
            "updatedAt": data.updatedAt or now,
        }

    def create_entry(self, data: QueryHistory) -> QueryHistory:
        document = self._to_document(data)
        result = self.collection.insert_one(document)
        created = self.collection.find_one({"_id": result.inserted_id})
        if not created:
            raise RuntimeError("Failed to create history entry")
        return self._to_entity(created)

    def find_by_user(self, user_id: str, limit: int = 10) -> list[QueryHistory]:
        cursor = (
            self.collection.find({"userId": user_id})
            .sort("createdAt", DESCENDING)
            .limit(limit)
        )
        return [self._to_entity(document) for document in cursor]

    def find_one(self, history_id: str) -> QueryHistory | None:
        try:
            object_id = ObjectId(history_id)
        except Exception:
            return None

        document = self.collection.find_one({"_id": object_id})
        if not document:
            return None

        return self._to_entity(document)
