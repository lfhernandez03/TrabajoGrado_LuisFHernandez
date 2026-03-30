from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends

from app.api.di import get_current_user_di as get_current_user
from app.api.schemas.graph import (
    CentralityEntry,
    ClusterEntry,
    GraphSummary,
    GraphTopologyResponse,
)
from app.core.fuseki_client import execute_select_query
from app.domain.entities.auth_user import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])

_PREFIXES = (
    "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
)


# ---------------------------------------------------------------------------
# Cached topology (graph metrics don't change between pipeline runs)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _cached_topology() -> GraphTopologyResponse:
    return _build_topology()


def _build_topology() -> GraphTopologyResponse:
    summary = _fetch_summary()
    top_degree = _fetch_top("degreeCentrality", 10)
    top_betweenness = _fetch_top("betweennessCentrality", 10)
    top_pagerank = _fetch_top("pageRank", 10)
    clusters = _fetch_clusters()

    is_small_world = (
        summary.averageClusteringCoefficient > 0.3
        and summary.communityCount >= 5
    )

    return GraphTopologyResponse(
        graphSummary=GraphSummary(
            totalMovies=summary.totalMovies,
            totalEdges=summary.totalEdges,
            averageDegree=summary.averageDegree,
            averageClusteringCoefficient=summary.averageClusteringCoefficient,
            communityCount=summary.communityCount,
            modularity=summary.modularity,
            isSmallWorld=is_small_world,
        ),
        topByDegree=top_degree,
        topByBetweenness=top_betweenness,
        topByPageRank=top_pagerank,
        clusterSummary=clusters,
    )


# ---------------------------------------------------------------------------
# SPARQL helpers
# ---------------------------------------------------------------------------

def _fetch_summary() -> GraphSummary:
    """Aggregate statistics from the Phase 6 triples."""

    # Total movies with degree assigned
    count_rows = execute_select_query(
        _PREFIXES
        + "SELECT (COUNT(DISTINCT ?m) AS ?c) WHERE { ?m movie:degreeCentrality ?d }"
    )
    total_movies = int(count_rows[0].get("c", 0)) if count_rows else 0

    # Average degree (normalised [0,1] → multiply by (N-1) to approximate absolute degree)
    avg_degree_rows = execute_select_query(
        _PREFIXES
        + "SELECT (AVG(?d) AS ?avg) WHERE { ?m movie:degreeCentrality ?d }"
    )
    avg_degree_norm = float(avg_degree_rows[0].get("avg", 0.0)) if avg_degree_rows else 0.0
    avg_degree = round(avg_degree_norm * max(total_movies - 1, 1), 2)

    # Estimated edges: avg_degree * N / 2
    total_edges = int(avg_degree * total_movies / 2)

    # Average clustering coefficient
    avg_clustering_rows = execute_select_query(
        _PREFIXES
        + "SELECT (AVG(?c) AS ?avg) WHERE { ?m movie:clusteringCoefficient ?c }"
    )
    avg_clustering = float(avg_clustering_rows[0].get("avg", 0.0)) if avg_clustering_rows else 0.0

    # Community count
    cluster_count_rows = execute_select_query(
        _PREFIXES
        + "SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?m movie:belongsToCluster ?c }"
    )
    community_count = int(cluster_count_rows[0].get("n", 0)) if cluster_count_rows else 0

    # Modularity — stored on the first movie that has it (written uniformly by pipeline)
    modularity_rows = execute_select_query(
        _PREFIXES
        + "SELECT ?mod WHERE { ?m movie:communityModularity ?mod } LIMIT 1"
    )
    modularity = float(modularity_rows[0].get("mod", 0.0)) if modularity_rows else 0.0

    return GraphSummary(
        totalMovies=total_movies,
        totalEdges=total_edges,
        averageDegree=avg_degree,
        averageClusteringCoefficient=round(avg_clustering, 4),
        communityCount=community_count,
        modularity=round(modularity, 4),
        isSmallWorld=False,  # overridden by caller
    )


def _fetch_top(metric: str, limit: int) -> list[CentralityEntry]:
    # Fetch extra rows because the OPTIONAL genre join can produce multiple
    # rows per movie.  Deduplicate by title and keep the first `limit` unique.
    fetch_limit = limit * 10
    rows = execute_select_query(
        _PREFIXES
        + f"SELECT ?title ?value ?genre WHERE {{\n"
        f"  ?m movie:hasTitle ?title ;\n"
        f"     movie:{metric} ?value .\n"
        f"  OPTIONAL {{ ?m movie:hasMainGenre/movie:genreName ?genre }}\n"
        f"}} ORDER BY DESC(?value) LIMIT {fetch_limit}"
    )
    entries: list[CentralityEntry] = []
    seen: set[str] = set()
    for row in rows:
        if len(entries) >= limit:
            break
        title = row.get("title", "")
        if not title or title in seen:
            continue
        seen.add(title)
        try:
            value = round(float(row.get("value", 0.0)), 6)
        except (ValueError, TypeError):
            value = 0.0
        entries.append(CentralityEntry(
            title=title,
            value=value,
            genre=row.get("genre") or None,
        ))
    return entries


def _fetch_clusters() -> list[ClusterEntry]:
    rows = execute_select_query(
        _PREFIXES
        + "SELECT ?clusterId ?label (COUNT(?m) AS ?size) WHERE {\n"
        "  ?m movie:belongsToCluster ?clusterId .\n"
        "  OPTIONAL { ?m movie:clusterLabel ?label }\n"
        "} GROUP BY ?clusterId ?label ORDER BY DESC(?size)"
    )
    clusters: list[ClusterEntry] = []
    seen_ids: set[str] = set()
    for row in rows:
        cid = str(row.get("clusterId", "")).strip()
        if not cid or cid in seen_ids:
            continue
        seen_ids.add(cid)
        try:
            size = int(row.get("size", 0))
        except (ValueError, TypeError):
            size = 0
        clusters.append(ClusterEntry(
            clusterId=cid,
            label=str(row.get("label", "")).strip() or f"Cluster {cid}",
            size=size,
        ))
    return clusters


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/topology", response_model=GraphTopologyResponse)
def get_graph_topology(
    current_user: AuthUser = Depends(get_current_user),
) -> GraphTopologyResponse:
    """Devuelve métricas topológicas globales del grafo de películas.

    Los datos son calculados offline por ``scripts/compute_network_metrics.py``
    y persistidos como tripletas RDF en Fuseki. Este endpoint los agrega y los
    devuelve en un formato listo para visualización.

    El resultado se cachea en memoria (las métricas no cambian entre ejecuciones
    del pipeline).
    """
    return _cached_topology()
