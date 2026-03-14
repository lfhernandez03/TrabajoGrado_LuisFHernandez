from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateQueryHistoryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    rdfGenerated: str | None = None
    sparqlExecuted: str | None = None
    contextExtracted: dict[str, Any] | None = None
    resultsFound: list[dict[str, Any]] | None = None
    explanation: str | None = None
    executionTimeMs: int | None = None
    wasSuccessful: bool = True


class QueryHistoryResponse(BaseModel):
    id: str
    userId: str
    query: str
    rdfGenerated: str | None = None
    sparqlExecuted: str | None = None
    contextExtracted: dict[str, Any] | None = None
    resultsFound: list[dict[str, Any]] | None = None
    explanation: str | None = None
    executionTimeMs: int | None = None
    wasSuccessful: bool
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
