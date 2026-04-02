from __future__ import annotations

from pydantic import BaseModel


class ClusterMovie(BaseModel):
    title: str
    rating: float | None = None
    genre: str | None = None
    posterUrl: str | None = None


class ClusterInfo(BaseModel):
    id: str
    label: str
    size: int
    dominantGenres: list[str]


class AdjacentCluster(BaseModel):
    clusterId: str
    label: str
    sharedGenres: list[str]
    bridgeMovies: list[ClusterMovie]


class MovieClusterResponse(BaseModel):
    movie: str
    cluster: ClusterInfo
    intraCluster: list[ClusterMovie]
    adjacentClusters: list[AdjacentCluster]


class ClusterListItem(BaseModel):
    clusterId: str
    label: str
    size: int
    exampleMovies: list[str]


class ClusterListResponse(BaseModel):
    clusters: list[ClusterListItem]
    total: int
