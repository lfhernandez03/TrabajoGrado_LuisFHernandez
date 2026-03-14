from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_admin, get_recommendation_metrics_use_case
from app.api.schemas.admin_metrics import (
    AdminRecommendationMetricsResponse,
    RecommendationMetricItemResponse,
    RecommendationMetricSummaryResponse,
)
from app.api.schemas.auth import AuthUserResponse
from app.application.use_cases.recommendation_metrics import RecommendationMetricsUseCase
from app.domain.entities.auth_user import AuthUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/whoami", response_model=AuthUserResponse)
def admin_whoami(current_admin: AuthUser = Depends(get_current_admin)) -> AuthUserResponse:
    return AuthUserResponse(
        id=current_admin.id,
        email=current_admin.email,
        name=current_admin.name,
        role=current_admin.role,
    )


@router.get("/metrics/recommendation", response_model=AdminRecommendationMetricsResponse)
def get_recommendation_metrics(
    recentLimit: int = Query(default=20, ge=1, le=200),
    summaryLimit: int = Query(default=200, ge=1, le=1000),
    _current_admin: AuthUser = Depends(get_current_admin),
    metrics_use_case: RecommendationMetricsUseCase = Depends(
        get_recommendation_metrics_use_case
    ),
) -> AdminRecommendationMetricsResponse:
    summary = metrics_use_case.get_summary(limit=summaryLimit)
    recent = metrics_use_case.list_recent(limit=recentLimit)

    return AdminRecommendationMetricsResponse(
        summary=RecommendationMetricSummaryResponse(**summary),
        recent=[
            RecommendationMetricItemResponse(
                id=item.id or "",
                userId=item.userId,
                query=item.query,
                source=item.source,
                fallbackUsed=item.fallbackUsed,
                fusekiRows=item.fusekiRows,
                errors=item.errors,
                timingsMs=item.timingsMs,
                moviesFound=item.moviesFound,
                executionTimeMs=item.executionTimeMs,
                createdAt=item.createdAt,
            )
            for item in recent
        ],
    )