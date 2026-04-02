from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.di import get_current_user_di as get_current_user
from app.api.schemas.connections import (
    CentralityResponse,
    ConnectionHopResponse,
    ConnectionPathResponse,
    NetworkEdgeResponse,
    NetworkGraphResponse,
    NetworkNodeResponse,
)
from app.api.schemas.recommendation import RecommendedMovieResponse
from app.core.connection_explorer import ConnectionExplorer
from app.domain.entities.auth_user import AuthUser
from app.domain.entities.recommendation_models import Movie

router = APIRouter(prefix="/movies/connections", tags=["connections"])


# ---------------------------------------------------------------------------
# Dependency — ConnectionExplorer is stateless, singleton is fine
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _explorer_singleton() -> ConnectionExplorer:
    return ConnectionExplorer()


def get_connection_explorer() -> ConnectionExplorer:
    return _explorer_singleton()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _movie_to_response(movie: Movie) -> RecommendedMovieResponse:
    return RecommendedMovieResponse(
        title=movie.title,
        posterUrl=movie.poster_url,
        runtime=movie.runtime,
        genreName=movie.genre,
        releaseDate=movie.release_year,
        averageRating=movie.rating,
        compatibilityScore=movie.compatibility_score,
        moodMatchScore=movie.mood_match_score,
        socialMatchScore=movie.social_match_score,
        energyMatchScore=movie.energy_match_score,
        timeMatchScore=movie.time_match_score,
        kidFriendly=movie.kid_friendly,
        serendipityScore=movie.serendipity_score,
    )


# ---------------------------------------------------------------------------
# GET /movies/connections/path
# ---------------------------------------------------------------------------

@router.get("/path", response_model=ConnectionPathResponse)
def find_path(
    source: str = Query(..., min_length=1, description="Título de la película origen"),
    target: str = Query(..., min_length=1, description="Título de la película destino"),
    current_user: AuthUser = Depends(get_current_user),
    explorer: ConnectionExplorer = Depends(get_connection_explorer),
) -> ConnectionPathResponse:
    """Encuentra el camino más corto entre dos películas en el grafo de conocimiento.

    Traversa hasta 3 saltos usando relaciones de director compartido, género
    compartido, y perfil de mood compatible (bridge-ontology).

    Devuelve los hops con el tipo de relación en cada paso.
    """
    path = explorer.find_path(source, target)
    hops = [
        ConnectionHopResponse(
            from_title=h.from_title,
            to_title=h.to_title,
            relation=h.relation,
        )
        for h in path.hops
    ]
    return ConnectionPathResponse(
        source=path.source,
        target=path.target,
        found=path.found,
        hops=hops,
        length=path.length,
    )


# ---------------------------------------------------------------------------
# GET /movies/connections/neighborhood
# ---------------------------------------------------------------------------

@router.get("/neighborhood", response_model=NetworkGraphResponse)
def get_neighborhood(
    title: str = Query(..., min_length=1, description="Título de la película centro"),
    depth: int = Query(default=2, ge=1, le=3, description="Profundidad de expansión (1–3)"),
    current_user: AuthUser = Depends(get_current_user),
    explorer: ConnectionExplorer = Depends(get_connection_explorer),
) -> NetworkGraphResponse:
    """Devuelve el grafo de vecindad alrededor de una película hasta N saltos.

    Los nodos representan películas conectadas; las aristas indican el tipo de
    relación (director compartido o género compartido).

    Limitado a 60 nodos para mantener respuestas manejables.
    """
    graph = explorer.get_neighborhood(title, depth=depth)

    nodes = [
        NetworkNodeResponse(
            uri=n.uri,
            title=n.title,
            genre=n.genre,
            rating=n.rating,
            poster_url=n.poster_url,
        )
        for n in graph.nodes
    ]
    edges = [
        NetworkEdgeResponse(
            source_uri=e.source_uri,
            target_uri=e.target_uri,
            relation=e.relation,
        )
        for e in graph.edges
    ]
    return NetworkGraphResponse(
        center_title=graph.center_title,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


# ---------------------------------------------------------------------------
# GET /movies/connections/centrality
# ---------------------------------------------------------------------------

@router.get("/centrality", response_model=CentralityResponse)
def get_centrality(
    genre: str | None = Query(default=None, description="Filtrar por género (opcional)"),
    limit: int = Query(default=20, ge=1, le=100, description="Número máximo de películas"),
    current_user: AuthUser = Depends(get_current_user),
    explorer: ConnectionExplorer = Depends(get_connection_explorer),
) -> CentralityResponse:
    """Devuelve las películas más centrales del grafo, ordenadas por rating y compatibilidad.

    Cuando se especifica ``genre``, el ranking se restringe a ese género.
    Útil para mostrar películas de referencia en cold start y para exploración
    temática del catálogo.
    """
    rows = explorer.get_centrality_ranking(genre=genre, limit=limit)

    movies = []
    for row in rows:
        try:
            movie = Movie.from_fuseki_row(row)
            movies.append(_movie_to_response(movie))
        except Exception:
            continue

    return CentralityResponse(
        genre=genre,
        movies=movies,
        total=len(movies),
    )
