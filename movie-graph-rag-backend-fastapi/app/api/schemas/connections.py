from __future__ import annotations

from pydantic import BaseModel

from app.api.schemas.recommendation import RecommendedMovieResponse


# ---------------------------------------------------------------------------
# Path finding — /movies/connections/path
# ---------------------------------------------------------------------------

class ConnectionHopResponse(BaseModel):
    """One hop on the shortest path between two movies."""
    from_title: str
    to_title: str
    relation: str   # "same_director" | "same_genre" | "same_mood_profile"


class ConnectionPathResponse(BaseModel):
    """Result of find_path(title_a, title_b)."""
    source: str
    target: str
    found: bool
    hops: list[ConnectionHopResponse]
    length: int


# ---------------------------------------------------------------------------
# Neighbourhood graph — /movies/connections/neighborhood
# ---------------------------------------------------------------------------

class NetworkNodeResponse(BaseModel):
    uri: str
    title: str
    genre: str | None = None
    rating: float | None = None
    poster_url: str | None = None
    description: str | None = None
    runtime: int | None = None


class NetworkEdgeResponse(BaseModel):
    source_uri: str
    target_uri: str
    relation: str   # "same_director" | "same_genre"


class NetworkGraphResponse(BaseModel):
    """Result of get_neighborhood(title, depth)."""
    center_title: str
    nodes: list[NetworkNodeResponse]
    edges: list[NetworkEdgeResponse]
    node_count: int
    edge_count: int


# ---------------------------------------------------------------------------
# Centrality ranking — /movies/connections/centrality
# ---------------------------------------------------------------------------

class CentralityResponse(BaseModel):
    """Result of get_centrality_ranking(genre, limit)."""
    genre: str | None = None
    movies: list[RecommendedMovieResponse]
    total: int
