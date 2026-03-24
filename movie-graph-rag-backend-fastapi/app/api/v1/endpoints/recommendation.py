from fastapi import APIRouter, Depends, Query

from app.api.di import get_current_user_di as get_current_user, get_recommendation_use_case_di as get_recommendation_use_case
from app.api.di.movies_di import get_chat_use_case_di
from app.api.schemas.recommendation import (
    ChatMovieResponse,
    ChatRequest,
    ChatResponse,
    RecommendationDebugResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.application.use_cases.recommendation import RecommendationUseCase
from app.application.use_cases.recommendation.chat_use_case import ChatUseCase
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


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: ChatUseCase = Depends(get_chat_use_case_di),
) -> ChatResponse:
    """Conversational recommendation endpoint.

    Accepts the full message history for a session and returns fresh
    recommendations based on the accumulated context across all turns.
    """
    result = use_case.execute(
        session_id=payload.session_id,
        messages=[m.model_dump() for m in payload.messages],
        user_id=current_user.id,
    )

    movies = [
        ChatMovieResponse(
            title=m.title,
            posterUrl=m.poster_url,
            runtime=m.runtime,
            genreName=m.genre,
            releaseDate=m.release_year,
            averageRating=m.rating,
            compatibilityScore=m.compatibility_score,
            moodMatchScore=m.mood_match_score,
            socialMatchScore=m.social_match_score,
            energyMatchScore=m.energy_match_score,
            timeMatchScore=m.time_match_score,
            kidFriendly=m.kid_friendly,
        )
        for m in result.movies
    ]

    ctx_dict = {
        "mood": result.context.mood,
        "companion": result.context.companion,
        "has_children": result.context.has_children,
        "energy": result.context.energy,
        "genres": result.context.genres,
        "runtime_max": result.context.runtime_max,
        "exclusions": result.context.exclusions,
        "confidence": result.context.confidence,
        "time_of_day": result.context.time_of_day,
        "children_age_hint": result.context.children_age_hint,
    }

    return ChatResponse(
        session_id=result.session_id,
        movies=movies,
        explanation=result.explanation,
        strategy_used=result.strategy_used,
        context_extracted=ctx_dict,
        execution_ms=result.execution_ms,
        turn_count=len([m for m in payload.messages if m.role == "user"]),
    )
