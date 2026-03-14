from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user, get_user_favorites_use_case
from app.api.schemas.favorites import (
    FavoriteMovieRequest,
    FavoriteMovieResponse,
    FavoritesResponse,
    RemoveFavoriteRequest,
)
from app.application.use_cases.user_favorites import UserFavoritesUseCase
from app.domain.entities.auth_user import AuthUser
from app.domain.entities.favorite_movie import FavoriteMovie

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/favorites", response_model=FavoritesResponse)
def get_my_favorites(
    current_user: AuthUser = Depends(get_current_user),
    use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case),
) -> FavoritesResponse:
    favorites = use_case.get_my_favorites(current_user.id)
    return FavoritesResponse(
        favorites=[FavoriteMovieResponse(**favorite.__dict__) for favorite in favorites]
    )


@router.post(
    "/me/favorites",
    response_model=FavoritesResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_my_favorite(
    payload: FavoriteMovieRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case),
) -> FavoritesResponse:
    movie = FavoriteMovie(
        uri=payload.uri,
        title=payload.title,
        posterUrl=payload.posterUrl,
        year=payload.year,
        runtime=payload.runtime,
        certification=payload.certification,
        director=payload.director,
        genres=payload.genres,
        description=payload.description,
        rating=payload.rating,
        relationReason=payload.relationReason,
    )

    favorites = use_case.add_my_favorite(current_user.id, movie)
    return FavoritesResponse(
        favorites=[FavoriteMovieResponse(**favorite.__dict__) for favorite in favorites]
    )


@router.delete("/me/favorites", response_model=FavoritesResponse)
def remove_my_favorite(
    payload: RemoveFavoriteRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case),
) -> FavoritesResponse:
    favorites = use_case.remove_my_favorite(current_user.id, payload.uri)
    return FavoritesResponse(
        favorites=[FavoriteMovieResponse(**favorite.__dict__) for favorite in favorites]
    )
