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
        description=movie.description,
    )


# ---------------------------------------------------------------------------
# GET /movies/connections/path
# ---------------------------------------------------------------------------

@router.get("/path", response_model=ConnectionPathResponse)
def find_path(
    source: str = Query(..., min_length=1, description="Source movie title"),
    target: str = Query(..., min_length=1, description="Target movie title"),
    current_user: AuthUser = Depends(get_current_user),
    explorer: ConnectionExplorer = Depends(get_connection_explorer),
) -> ConnectionPathResponse:
    """Find the shortest path between two movies in the knowledge graph.

    Traverses up to 3 hops using shared director, shared genre,
    and compatible mood profile (bridge-ontology) relationships.

    Returns hops with the relationship type at each step.
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
    title: str = Query(..., min_length=1, description="Center movie title"),
    depth: int = Query(default=2, ge=1, le=3, description="Expansion depth (1–3)"),
    current_user: AuthUser = Depends(get_current_user),
    explorer: ConnectionExplorer = Depends(get_connection_explorer),
) -> NetworkGraphResponse:
    """Return the neighborhood graph around a movie up to N hops.

    Nodes represent connected movies; edges indicate the relationship type
    (shared director or shared genre).

    The center node (input) is excluded from the result.

    Limited to 60 nodes to keep responses manageable.
    """
    graph = explorer.get_neighborhood(title, depth=depth)

    # Exclude the center node (first node) — return only the real neighborhood
    neighborhood_nodes = graph.nodes[1:] if graph.nodes else []

    nodes = [
        NetworkNodeResponse(
            uri=n.uri,
            title=n.title,
            genre=n.genre,
            rating=n.rating,
            posterUrl=n.poster_url,
            description=n.description,
            runtime=getattr(n, "runtime", None),
            director=getattr(n, "director", None),
            year=getattr(n, "year", None),
        )
        for n in neighborhood_nodes
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
    """Return the most central movies in the graph, ordered by rating and compatibility.

    When ``genre`` is specified, the ranking is restricted to that genre.
    Useful for showing reference movies in cold start and for thematic catalog exploration.
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
