from __future__ import annotations

from pydantic import BaseModel


class ClusterWeight(BaseModel):
    clusterId: str
    label: str
    weight: float
    """Fraction of the user's favorites that belong to this cluster [0, 1]."""
    moviesSeen: int
    """Number of favorites in this cluster."""


class UnexploredCluster(BaseModel):
    clusterId: str
    label: str
    distanceToDominant: int = 1
    """Graph distance to the user's most dominant cluster (always 1 — genre-adjacent)."""


class TopologicalProfileResponse(BaseModel):
    userId: str
    explorationIndex: float
    """Shannon entropy of cluster distribution, normalized to [0, 1].
    0 = pure specialist (all favorites in one cluster).
    1 = pure explorer (favorites uniformly spread across all clusters).
    """
    userType: str
    """'especialista' (< 0.3) | 'equilibrado' (0.3–0.7) | 'explorador' (> 0.7)."""
    dominantClusters: list[ClusterWeight]
    """Top clusters by weight, descending."""
    unexploredAdjacent: list[UnexploredCluster]
    """Clusters adjacent to the dominant cluster that the user has not yet visited."""
    temporalTrend: str
    """'specializing' | 'diversifying' | 'stable'."""
    trendExplanation: str
    totalFavorites: int
    clusteredFavorites: int
    """Favorites that had a cluster assignment in Phase 6 data."""
