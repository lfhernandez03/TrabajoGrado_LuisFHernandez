from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user, get_recommendation_use_case
from app.api.schemas.recommendation import (
    RecommendationDebugResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.application.use_cases.recommendation import RecommendationUseCase
from app.domain.entities.auth_user import AuthUser

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("", response_model=RecommendationResponse)
def get_recommendation_get(
    query: str = Query(..., min_length=1),
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
) -> RecommendationResponse:
    return RecommendationResponse(**use_case.get_recommendation(query, current_user.id))


@router.post("", response_model=RecommendationResponse)
def get_recommendation_post(
    payload: RecommendationRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
) -> RecommendationResponse:
    return RecommendationResponse(
        **use_case.get_recommendation(payload.query, current_user.id)
    )


@router.get("/activity", response_model=RecommendationResponse)
async def get_activity_recommendation(
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
) -> RecommendationResponse:
    return RecommendationResponse(**await use_case.get_activity_recommendation(current_user.id))


@router.post("/debug", response_model=RecommendationDebugResponse)
def get_recommendation_debug(
    payload: RecommendationRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
) -> RecommendationDebugResponse:
    return RecommendationDebugResponse(
        **use_case.get_recommendation_debug(payload.query, current_user.id)
    )
