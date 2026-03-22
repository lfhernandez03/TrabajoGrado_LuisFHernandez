from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.di import get_current_user_di as get_current_user, get_query_history_use_case_di as get_query_history_use_case
from app.api.schemas.history import CreateQueryHistoryRequest, QueryHistoryResponse
from app.application.use_cases.history import QueryHistoryUseCase
from app.domain.entities.auth_user import AuthUser
from app.domain.entities.query_history import QueryHistory

router = APIRouter(prefix="/history", tags=["history"])


@router.post("/me", response_model=QueryHistoryResponse, status_code=status.HTTP_201_CREATED)
def create_my_history_entry(
    payload: CreateQueryHistoryRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: QueryHistoryUseCase = Depends(get_query_history_use_case),
) -> QueryHistoryResponse:
    created = use_case.create_entry(
        QueryHistory(
            userId=current_user.id,
            query=payload.query,
            rdfGenerated=payload.rdfGenerated,
            sparqlExecuted=payload.sparqlExecuted,
            contextExtracted=payload.contextExtracted,
            resultsFound=payload.resultsFound,
            explanation=payload.explanation,
            executionTimeMs=payload.executionTimeMs,
            wasSuccessful=payload.wasSuccessful,
        )
    )

    return QueryHistoryResponse(
        id=created.id or "",
        userId=created.userId,
        query=created.query,
        rdfGenerated=created.rdfGenerated,
        sparqlExecuted=created.sparqlExecuted,
        contextExtracted=created.contextExtracted,
        resultsFound=created.resultsFound,
        explanation=created.explanation,
        executionTimeMs=created.executionTimeMs,
        wasSuccessful=created.wasSuccessful,
        createdAt=created.createdAt,
        updatedAt=created.updatedAt,
    )


@router.get("/me", response_model=list[QueryHistoryResponse])
def get_my_history(
    limit: int = Query(default=10, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_user),
    use_case: QueryHistoryUseCase = Depends(get_query_history_use_case),
) -> list[QueryHistoryResponse]:
    entries = use_case.find_by_user(user_id=current_user.id, limit=limit)
    return [
        QueryHistoryResponse(
            id=entry.id or "",
            userId=entry.userId,
            query=entry.query,
            rdfGenerated=entry.rdfGenerated,
            sparqlExecuted=entry.sparqlExecuted,
            contextExtracted=entry.contextExtracted,
            resultsFound=entry.resultsFound,
            explanation=entry.explanation,
            executionTimeMs=entry.executionTimeMs,
            wasSuccessful=entry.wasSuccessful,
            createdAt=entry.createdAt,
            updatedAt=entry.updatedAt,
        )
        for entry in entries
    ]


@router.get("/{history_id}", response_model=QueryHistoryResponse)
def get_history_detail(
    history_id: str,
    _current_user: AuthUser = Depends(get_current_user),
    use_case: QueryHistoryUseCase = Depends(get_query_history_use_case),
) -> QueryHistoryResponse:
    entry = use_case.find_one(history_id)
    if not entry or not entry.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History entry not found",
        )

    return QueryHistoryResponse(
        id=entry.id,
        userId=entry.userId,
        query=entry.query,
        rdfGenerated=entry.rdfGenerated,
        sparqlExecuted=entry.sparqlExecuted,
        contextExtracted=entry.contextExtracted,
        resultsFound=entry.resultsFound,
        explanation=entry.explanation,
        executionTimeMs=entry.executionTimeMs,
        wasSuccessful=entry.wasSuccessful,
        createdAt=entry.createdAt,
        updatedAt=entry.updatedAt,
    )
