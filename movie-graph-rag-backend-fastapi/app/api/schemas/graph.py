from __future__ import annotations

from pydantic import BaseModel


class GraphSummary(BaseModel):
    totalMovies: int
    totalEdges: int
    averageDegree: float
    averageClusteringCoefficient: float
    communityCount: int
    modularity: float
    isSmallWorld: bool


class CentralityEntry(BaseModel):
    title: str
    value: float
    genre: str | None = None


class ClusterEntry(BaseModel):
    clusterId: str
    label: str
    size: int


class GraphTopologyResponse(BaseModel):
    graphSummary: GraphSummary
    topByDegree: list[CentralityEntry]
    topByBetweenness: list[CentralityEntry]
    topByPageRank: list[CentralityEntry]
    clusterSummary: list[ClusterEntry]
