from fastapi import APIRouter, Depends, Query

from app.api.di import get_current_user_di as get_current_user, get_movies_use_case_di as get_movies_use_case
from app.api.schemas.movies import (
    ConnectionExplorerResponse,
    MovieResponse,
    MovieSuggestionResponse,
)
from app.application.use_cases.movies import MoviesUseCase
from app.domain.entities.auth_user import AuthUser

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/examples", response_model=list[MovieResponse])
def get_examples(
    limit: int = Query(default=3, ge=1, le=50),
    use_case: MoviesUseCase = Depends(get_movies_use_case),
) -> list[MovieResponse]:
    return [MovieResponse(**movie) for movie in use_case.get_examples(limit=limit)]


@router.get("/autocomplete", response_model=list[MovieSuggestionResponse])
def autocomplete_movies(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=8, ge=1, le=20),
    current_user: AuthUser = Depends(get_current_user),
    use_case: MoviesUseCase = Depends(get_movies_use_case),
) -> list[MovieSuggestionResponse]:
    results = use_case.autocomplete(user_id=current_user.id, term=q, limit=limit)
    return [MovieSuggestionResponse(**item) for item in results]


@router.get("/search", response_model=list[MovieResponse])
def search_movies(
    q: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    director: str | None = Query(default=None),
    yearFrom: int | None = Query(default=None),
    yearTo: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_user),
    use_case: MoviesUseCase = Depends(get_movies_use_case),
) -> list[MovieResponse]:
    results = use_case.search_movies(
        user_id=current_user.id,
        q=q,
        genre=genre,
        director=director,
        year_from=yearFrom,
        year_to=yearTo,
        limit=limit,
    )
    return [MovieResponse(**movie) for movie in results]


@router.get("/connections", response_model=ConnectionExplorerResponse)
def find_connections(
    from_: str = Query(..., alias="from", min_length=1),
    to: str = Query(..., min_length=1),
    maxDepth: int = Query(default=3, ge=1, le=6),
    current_user: AuthUser = Depends(get_current_user),
    use_case: MoviesUseCase = Depends(get_movies_use_case),
) -> ConnectionExplorerResponse:
    result = use_case.find_connections(
        user_id=current_user.id,
        from_term=from_,
        to_term=to,
        max_depth=maxDepth,
    )
    mapped_edges = [
        {
            "from_": edge["from"],
            "to": edge["to"],
            "label": edge["label"],
            "property": edge["property"],
        }
        for edge in result["edges"]
    ]
    result["edges"] = mapped_edges
    return ConnectionExplorerResponse(**result)
