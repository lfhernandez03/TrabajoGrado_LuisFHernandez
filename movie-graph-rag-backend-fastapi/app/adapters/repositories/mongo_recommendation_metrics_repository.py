from datetime import datetime

from pymongo import DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from app.domain.entities.recommendation_metric import RecommendationMetric
from app.domain.ports.recommendation_metrics_repository import (
    RecommendationMetricsRepositoryPort,
)


class MongoRecommendationMetricsRepositoryAdapter(RecommendationMetricsRepositoryPort):
    def __init__(self, db: Database) -> None:
        self.collection: Collection = db["recommendation_metrics"]
        self.collection.create_index("createdAt")
        self.collection.create_index("source")
        self.collection.create_index("fallbackUsed")

    def _to_entity(self, document: dict) -> RecommendationMetric:
        return RecommendationMetric(
            id=str(document["_id"]),
            userId=document["userId"],
            query=document["query"],
            source=document.get("source", "unknown"),
            fallbackUsed=document.get("fallbackUsed", False),
            fusekiRows=document.get("fusekiRows", 0),
            errors=document.get("errors", []),
            timingsMs=document.get("timingsMs", {}),
            moviesFound=document.get("moviesFound", 0),
            executionTimeMs=document.get("executionTimeMs", 0),
            createdAt=document.get("createdAt"),
        )

    def _to_document(self, data: RecommendationMetric) -> dict:
        return {
            "userId": data.userId,
            "query": data.query,
            "source": data.source,
            "fallbackUsed": data.fallbackUsed,
            "fusekiRows": data.fusekiRows,
            "errors": data.errors,
            "timingsMs": data.timingsMs,
            "moviesFound": data.moviesFound,
            "executionTimeMs": data.executionTimeMs,
            "createdAt": data.createdAt or datetime.utcnow(),
        }

    def create_entry(self, data: RecommendationMetric) -> RecommendationMetric:
        document = self._to_document(data)
        result = self.collection.insert_one(document)
        created = self.collection.find_one({"_id": result.inserted_id})
        if not created:
            raise RuntimeError("Failed to create recommendation metric")
        return self._to_entity(created)

    def list_recent(self, limit: int = 50) -> list[RecommendationMetric]:
        cursor = self.collection.find({}).sort("createdAt", DESCENDING).limit(limit)
        return [self._to_entity(document) for document in cursor]

    def get_summary(self, limit: int = 200) -> dict:
        rows = list(
            self.collection.find({}).sort("createdAt", DESCENDING).limit(limit)
        )
        if not rows:
            return {
                "sampleSize": 0,
                "fallbackRate": 0.0,
                "errorRate": 0.0,
                "avgTotalMs": 0,
                "avgFusekiMs": 0,
                "sourceCounts": {"fuseki": 0, "favorites_fallback": 0, "unknown": 0},
            }

        sample_size = len(rows)
        fallback_count = sum(1 for row in rows if row.get("fallbackUsed"))
        error_count = sum(1 for row in rows if row.get("errors"))

        total_ms_values = []
        fuseki_ms_values = []
        source_counts = {"fuseki": 0, "favorites_fallback": 0, "unknown": 0}

        for row in rows:
            source = row.get("source", "unknown")
            if isinstance(source, str) and source.startswith("fuseki"):
                source_counts["fuseki"] += 1
            elif source not in source_counts:
                source_counts["unknown"] += 1
            else:
                source_counts[source] += 1

            timings = row.get("timingsMs") or {}
            total_value = timings.get("total") or row.get("executionTimeMs") or 0
            fuseki_value = timings.get("fusekiQuery") or 0
            total_ms_values.append(int(total_value))
            fuseki_ms_values.append(int(fuseki_value))

        avg_total = int(sum(total_ms_values) / sample_size)
        avg_fuseki = int(sum(fuseki_ms_values) / sample_size)

        return {
            "sampleSize": sample_size,
            "fallbackRate": round(fallback_count / sample_size, 4),
            "errorRate": round(error_count / sample_size, 4),
            "avgTotalMs": avg_total,
            "avgFusekiMs": avg_fuseki,
            "sourceCounts": source_counts,
        }
