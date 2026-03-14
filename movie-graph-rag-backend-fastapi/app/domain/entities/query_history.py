from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class QueryHistory:
    userId: str
    query: str
    rdfGenerated: str | None = None
    sparqlExecuted: str | None = None
    contextExtracted: dict[str, Any] | None = None
    resultsFound: list[dict[str, Any]] | None = None
    explanation: str | None = None
    executionTimeMs: int | None = None
    wasSuccessful: bool = True
    id: str | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
