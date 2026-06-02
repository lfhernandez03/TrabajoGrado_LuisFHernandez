from fastapi import APIRouter, Depends, status

from app.api.di import get_current_user_di as get_current_user, get_user_favorites_use_case_di as get_user_favorites_use_case
from app.api.schemas.favorites import (
    FavoriteMovieRequest,
    FavoriteMovieResponse,
    FavoritesResponse,
    RemoveFavoriteRequest,
)
from app.api.schemas.topology_profile import TopologicalProfileResponse
from app.application.use_cases.users import UserFavoritesUseCase
from app.core.profile_service import ProfileService
from app.core.fuseki_client import execute_select_query, FusekiQueryError
from app.domain.entities.auth_user import AuthUser
from app.domain.entities.favorite_movie import FavoriteMovie

router = APIRouter(prefix="/users", tags=["users"])

_profile_service = ProfileService()

_RATING_QUERY = """\
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
SELECT ?m ?rating WHERE {{
  VALUES ?m {{ {uris} }}
  OPTIONAL {{ ?m movie:hasRating ?rating }}
}}
"""


def _enrich_ratings(favorites: list[FavoriteMovie]) -> list[FavoriteMovie]:
    """Back-fill rating for favorites that were saved before the SPARQL fix."""
    missing = [f for f in favorites if f.rating is None and f.uri]
    if not missing:
        return favorites

    uri_values = " ".join(f"<{f.uri}>" for f in missing)
    try:
        rows = execute_select_query(_RATING_QUERY.format(uris=uri_values))
    except FusekiQueryError:
        return favorites

    rating_map: dict[str, float] = {}
    for row in rows:
        uri = row.get("m")
        raw = row.get("rating")
        if uri and raw is not None:
            try:
                rating_map[uri] = float(raw)
            except (ValueError, TypeError):
                pass

    for fav in missing:
        if fav.uri in rating_map:
            fav.rating = rating_map[fav.uri]

    return favorites


@router.get("/me/favorites", response_model=FavoritesResponse)
def get_my_favorites(
    current_user: AuthUser = Depends(get_current_user),
    use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case),
) -> FavoritesResponse:
    favorites = _enrich_ratings(use_case.get_my_favorites(current_user.id))
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


@router.get("/me/topology", response_model=TopologicalProfileResponse)
def get_my_topology(
    current_user: AuthUser = Depends(get_current_user),
    use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case),
) -> TopologicalProfileResponse:
    """Devuelve el perfil topologico del usuario basado en sus favoritos.

    Mapea cada pelicula favorita a su comunidad Louvain (Fase 6) y calcula:
    - **explorationIndex**: entropia de Shannon normalizada [0,1] sobre la
      distribucion de clusters — 0 = especialista, 1 = explorador.
    - **dominantClusters**: top 5 comunidades por peso.
    - **unexploredAdjacent**: clusters adjacentes al dominante aun no explorados.
    - **temporalTrend**: si el usuario se esta especializando o diversificando,
      calculado comparando la mitad mas antigua vs. la mas reciente de sus favoritos.

    Requiere que ``scripts/compute_network_metrics.py`` haya asignado clusters a
    las peliculas en Fuseki (Fase 6).
    """
    favorites = use_case.get_my_favorites(current_user.id)
    return _profile_service.get_topological_profile(current_user.id, favorites)
