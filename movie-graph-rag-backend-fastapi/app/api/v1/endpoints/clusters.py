from __future__ import annotations

import collections
import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.di import get_current_user_di as get_current_user
from app.api.schemas.clusters import (
    AdjacentCluster,
    ClusterInfo,
    ClusterListItem,
    ClusterListResponse,
    ClusterMovie,
    ClusterMovieListResponse,
    MovieClusterResponse,
)
from app.core.fuseki_client import execute_select_query
from app.domain.entities.auth_user import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["clusters"])

_NS_MOVIE = "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#"
_NS_SCHEMA = "http://schema.org/"

_PREFIXES = (
    f"PREFIX movie: <{_NS_MOVIE}>\n"
    f"PREFIX schema1: <{_NS_SCHEMA}>\n"
)


# ---------------------------------------------------------------------------
# SPARQL helpers
# ---------------------------------------------------------------------------

def _escape(s: str) -> str:
    """Escape a string value for use in a SPARQL double-quoted literal."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _row_to_cluster_movie(row: dict) -> ClusterMovie:
    rating = None
    try:
        if row.get("rating"):
            rating = round(float(row["rating"]), 2)
    except (ValueError, TypeError):
        pass
    imdb_rating = None
    try:
        if row.get("imdbRating"):
            imdb_rating = round(float(row["imdbRating"]), 2)
    except (ValueError, TypeError):
        pass
    runtime = None
    try:
        if row.get("runtime"):
            runtime = int(row["runtime"])
    except (ValueError, TypeError):
        pass
    genres_str = row.get("genres") or ""
    genres = [g.strip() for g in genres_str.split(",") if g.strip()] if genres_str else []
    return ClusterMovie(
        uri=row.get("uri") or None,
        title=row.get("title", ""),
        rating=rating,
        imdbRating=imdb_rating,
        genres=genres,
        posterUrl=row.get("posterUrl") or None,
        runtime=runtime,
        description=row.get("description") or None,
        director=row.get("directorName") or None,
    )


# ---------------------------------------------------------------------------
# Cluster list (cached — doesn't change between pipeline runs)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _cached_cluster_list() -> ClusterListResponse:
    # Query 1: clusters with size and label
    size_rows = execute_select_query(
        _PREFIXES
        + "SELECT ?clusterId ?label (COUNT(DISTINCT ?m) AS ?size) WHERE {\n"
        "  ?m movie:belongsToCluster ?clusterId .\n"
        "  OPTIONAL { ?m movie:clusterLabel ?label }\n"
        "} GROUP BY ?clusterId ?label ORDER BY DESC(?size)"
    )

    # Build cluster size map (deduplicate: same clusterId may appear with different labels due to OPTIONAL)
    cluster_sizes: dict[str, int] = {}
    cluster_labels: dict[str, str] = {}
    for row in size_rows:
        cid = str(row.get("clusterId", "")).strip()
        if not cid:
            continue
        try:
            sz = int(row.get("size", 0))
        except (ValueError, TypeError):
            sz = 0
        if cid not in cluster_sizes or sz > cluster_sizes[cid]:
            cluster_sizes[cid] = sz
        if cid not in cluster_labels:
            label = str(row.get("label", "")).strip()
            cluster_labels[cid] = label if label else f"Cluster {cid}"

    # Query 2: top-rated movies per cluster (single batch, group in Python)
    example_rows = execute_select_query(
        _PREFIXES
        + "SELECT ?clusterId ?title ?rating WHERE {\n"
        "  ?m movie:belongsToCluster ?clusterId ;\n"
        "     movie:hasTitle ?title .\n"
        "  OPTIONAL { ?m movie:hasRating ?rating }\n"
        "} ORDER BY ?clusterId DESC(?rating)\n"
        "LIMIT 3000"
    )

    cluster_examples: dict[str, list[str]] = collections.defaultdict(list)
    for row in example_rows:
        cid = str(row.get("clusterId", "")).strip()
        title = str(row.get("title", "")).strip()
        if cid and title and len(cluster_examples[cid]) < 3:
            cluster_examples[cid].append(title)

    clusters = [
        ClusterListItem(
            clusterId=cid,
            label=cluster_labels.get(cid, f"Cluster {cid}"),
            size=cluster_sizes[cid],
            exampleMovies=cluster_examples.get(cid, []),
        )
        for cid in sorted(cluster_sizes, key=lambda c: -cluster_sizes[c])
    ]
    return ClusterListResponse(clusters=clusters, total=len(clusters))


# ---------------------------------------------------------------------------
# Movie cluster lookup
# ---------------------------------------------------------------------------

def _get_movie_cluster(title: str) -> MovieClusterResponse:
    safe_title = _escape(title)

    # Step 1: find seed movie's cluster
    seed_rows = execute_select_query(
        _PREFIXES
        + "SELECT ?clusterId ?clusterLabel ?rating ?genreName WHERE {\n"
        f'  ?m movie:hasTitle "{safe_title}" ;\n'
        "     movie:belongsToCluster ?clusterId .\n"
        "  OPTIONAL { ?m movie:clusterLabel ?clusterLabel }\n"
        "  OPTIONAL { ?m movie:hasRating ?rating }\n"
        "  OPTIONAL { ?m movie:hasMainGenre/movie:genreName ?genreName }\n"
        "} LIMIT 5"
    )

    if not seed_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie '{title}' not found or has no cluster assigned. "
                   "Run scripts/compute_network_metrics.py to assign clusters.",
        )

    cluster_id = str(seed_rows[0].get("clusterId", "")).strip()
    cluster_label = str(seed_rows[0].get("clusterLabel", "")).strip() or f"Cluster {cluster_id}"

    if not cluster_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie '{title}' has no cluster assigned.",
        )

    safe_cid = _escape(cluster_id)

    # Step 2: cluster size
    size_rows = execute_select_query(
        _PREFIXES
        + f'SELECT (COUNT(DISTINCT ?m) AS ?size) WHERE {{ ?m movie:belongsToCluster "{safe_cid}" }}'
    )
    cluster_size = int(size_rows[0].get("size", 0)) if size_rows else 0

    # Step 3: dominant genres in this cluster
    genre_rows = execute_select_query(
        _PREFIXES
        + "SELECT ?genreName (COUNT(?m) AS ?cnt) WHERE {\n"
        f'  ?m movie:belongsToCluster "{safe_cid}" ;\n'
        "     movie:hasMainGenre/movie:genreName ?genreName .\n"
        "} GROUP BY ?genreName ORDER BY DESC(?cnt) LIMIT 5"
    )
    dominant_genres = [r["genreName"] for r in genre_rows if r.get("genreName")]

    # Step 4: intra-cluster movies (exclude seed, ordered by rating)
    intra_rows = execute_select_query(
        _PREFIXES
        + "SELECT DISTINCT ?title ?rating ?imdbRating ?genreName ?posterUrl ?runtime ?description ?directorName WHERE {\n"
        f'  ?m movie:belongsToCluster "{safe_cid}" ;\n'
        "     movie:hasTitle ?title .\n"
        "  OPTIONAL { ?m movie:hasRating ?rating }\n"
        "  OPTIONAL { ?m movie:hasIMDbRating ?imdbRating }\n"
        "  OPTIONAL { ?m movie:hasMainGenre/movie:genreName ?genreName }\n"
        "  OPTIONAL { ?m schema1:image ?posterUrl }\n"
        "  OPTIONAL { ?m movie:runtime ?runtime }\n"
        "  OPTIONAL { ?m movie:hasPlotSummary ?description }\n"
        "  OPTIONAL { ?m movie:hasDirector/movie:hasName ?directorName }\n"
        f'  FILTER(?title != "{safe_title}")\n'
        "} ORDER BY DESC(?rating) LIMIT 50"
    )
    # Deduplicate by title (OPTIONAL genre can produce multiple rows)
    seen: set[str] = set()
    intra_movies: list[ClusterMovie] = []
    for row in intra_rows:
        t = row.get("title", "")
        if t and t not in seen:
            seen.add(t)
            intra_movies.append(_row_to_cluster_movie(row))
        if len(intra_movies) >= 10:
            break

    # Step 5: adjacent clusters (clusters sharing the most genre overlap)
    if dominant_genres:
        genre_values = " ".join(f'"{_escape(g)}"' for g in dominant_genres)
        adj_rows = execute_select_query(
            _PREFIXES
            + "SELECT ?otherClusterId ?otherLabel (COUNT(DISTINCT ?neighbor) AS ?overlap) WHERE {\n"
            f"  VALUES ?sharedGenre {{ {genre_values} }}\n"
            "  ?neighbor movie:hasMainGenre/movie:genreName ?sharedGenre ;\n"
            "            movie:belongsToCluster ?otherClusterId .\n"
            "  OPTIONAL { ?neighbor movie:clusterLabel ?otherLabel }\n"
            f'  FILTER(?otherClusterId != "{safe_cid}")\n'
            "} GROUP BY ?otherClusterId ?otherLabel ORDER BY DESC(?overlap) LIMIT 10"
        )
    else:
        adj_rows = []

    # Deduplicate adjacent clusters
    seen_adj: set[str] = set()
    adjacent: list[AdjacentCluster] = []
    for row in adj_rows:
        adj_cid = str(row.get("otherClusterId", "")).strip()
        if not adj_cid or adj_cid in seen_adj:
            continue
        seen_adj.add(adj_cid)
        adj_label = str(row.get("otherLabel", "")).strip() or f"Cluster {adj_cid}"

        # Fetch bridge movies (top 3 high-rated from this adjacent cluster sharing genres)
        if dominant_genres:
            safe_adj = _escape(adj_cid)
            bridge_rows = execute_select_query(
                _PREFIXES
                + "SELECT DISTINCT ?title ?rating ?imdbRating ?genreName ?posterUrl ?runtime ?description ?directorName WHERE {\n"
                f"  VALUES ?sharedGenre {{ {genre_values} }}\n"
                "  ?m movie:hasMainGenre/movie:genreName ?sharedGenre ;\n"
                f'     movie:belongsToCluster "{safe_adj}" ;\n'
                "     movie:hasTitle ?title .\n"
                "  OPTIONAL { ?m movie:hasRating ?rating }\n"
                "  OPTIONAL { ?m movie:hasIMDbRating ?imdbRating }\n"
                "  OPTIONAL { ?m schema1:image ?posterUrl }\n"
                "  OPTIONAL { ?m movie:runtime ?runtime }\n"
                "  OPTIONAL { ?m movie:hasPlotSummary ?description }\n"
                "  OPTIONAL { ?m movie:hasDirector/movie:hasName ?directorName }\n"
                "  BIND(?sharedGenre AS ?genreName)\n"
                "} ORDER BY DESC(?rating) LIMIT 15"
            )
            seen_b: set[str] = set()
            bridge: list[ClusterMovie] = []
            for br in bridge_rows:
                bt = br.get("title", "")
                if bt and bt not in seen_b:
                    seen_b.add(bt)
                    bridge.append(_row_to_cluster_movie(br))
                if len(bridge) >= 3:
                    break
        else:
            bridge = []

        adjacent.append(AdjacentCluster(
            clusterId=adj_cid,
            label=adj_label,
            sharedGenres=dominant_genres[:3],
            bridgeMovies=bridge,
        ))
        if len(adjacent) >= 3:
            break

    return MovieClusterResponse(
        movie=title,
        cluster=ClusterInfo(
            id=cluster_id,
            label=cluster_label,
            size=cluster_size,
            dominantGenres=dominant_genres,
        ),
        intraCluster=intra_movies,
        adjacentClusters=adjacent,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/movies/{title}/cluster", response_model=MovieClusterResponse)
def get_movie_cluster(
    title: str,
    current_user: AuthUser = Depends(get_current_user),
) -> MovieClusterResponse:
    """Devuelve la comunidad Louvain de una película y sus vecinas.

    Incluye:
    - Información del cluster (id, etiqueta generada por LLM, tamaño, géneros dominantes)
    - Top 10 películas del mismo cluster ordenadas por rating (**intra-cluster**)
    - Hasta 3 clusters adyacentes con películas puente (**inter-cluster**)

    Requiere que ``scripts/compute_network_metrics.py`` haya sido ejecutado previamente.
    """
    return _get_movie_cluster(title)


@router.get("", response_model=ClusterListResponse)
def list_clusters(
    current_user: AuthUser = Depends(get_current_user),
) -> ClusterListResponse:
    """Lista todas las comunidades detectadas por Louvain, ordenadas por tamaño.

    Incluye nombre generado por LLM, número de películas y hasta 3 ejemplos
    representativos por cluster.

    El resultado se cachea en memoria (los clusters no cambian entre ejecuciones
    del pipeline).
    """
    return _cached_cluster_list()


@router.get("/{cluster_id}/movies", response_model=ClusterMovieListResponse)
def get_cluster_movies(
    cluster_id: str = Path(..., description="ID del cluster Louvain (e.g., '0', '1', ...)"),
    limit: int = Query(default=12, ge=1, le=50, description="Número de películas (1-50)"),
    current_user: AuthUser = Depends(get_current_user),
) -> ClusterMovieListResponse:
    """Devuelve las películas de un cluster ordenadas por rating.

    Útil para exploración de géneros inexplorados - permite cargar películas
    de clusters específicos que el usuario aún no ha descubierto.
    """
    safe_cid = _escape(cluster_id)
    query = (
        _PREFIXES
        + "SELECT ?m ?title ?rating ?imdbRating ?posterUrl ?runtime ?description ?directorName (GROUP_CONCAT(DISTINCT ?genreName; separator=\", \") AS ?genres) WHERE {\n"
        f'  ?m movie:belongsToCluster "{safe_cid}" ;\n'
        "     movie:hasTitle ?title .\n"
        "  OPTIONAL { ?m movie:hasRating ?rating }\n"
        "  OPTIONAL { ?m movie:hasIMDbRating ?imdbRating }\n"
        "  OPTIONAL { ?m movie:hasMainGenre/movie:genreName ?genreName }\n"
        "  OPTIONAL { ?m schema1:image ?posterUrl }\n"
        "  OPTIONAL { ?m movie:runtime ?runtime }\n"
        "  OPTIONAL { ?m movie:hasPlotSummary ?description }\n"
        "  OPTIONAL { ?m movie:hasDirector/movie:hasName ?directorName }\n"
        f"}} GROUP BY ?m ?title ?rating ?imdbRating ?posterUrl ?runtime ?description ?directorName ORDER BY DESC(?rating) LIMIT {limit}"
    )
    try:
        rows = execute_select_query(query)
        movies = [_row_to_cluster_movie(row) for row in rows]
        return ClusterMovieListResponse(cluster_id=cluster_id, movies=movies)
    except Exception as exc:
        logger.error("get_cluster_movies failed for cluster '%s': %s", cluster_id, exc)
        return ClusterMovieListResponse(cluster_id=cluster_id, movies=[])
