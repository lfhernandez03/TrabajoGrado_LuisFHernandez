#!/usr/bin/env python3
"""Phase 6: NetworkX offline metrics pipeline for CineSemantico.

Run from project root:
    python scripts/compute_network_metrics.py

Required packages (install separately if not in venv):
    pip install networkx python-louvain scipy google-genai python-dotenv
"""
from __future__ import annotations

import base64
import collections
import itertools
import json
import os
import sys
import time
from datetime import datetime
from urllib import error, parse, request

# ---------------------------------------------------------------------------
# Load .env from the directory where the script is run (project root)
# ---------------------------------------------------------------------------

from dotenv import load_dotenv  # type: ignore

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

FUSEKI_URL: str = os.getenv("FUSEKI_URL", "http://localhost:3030")
FUSEKI_DATASET: str = os.getenv("FUSEKI_DATASET", "Cine")
FUSEKI_USER: str = os.getenv("FUSEKI_USER", "Admin")
FUSEKI_PASSWORD: str = os.getenv("FUSEKI_PASSWORD", "Admin")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

MOVIE_NS = "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"

# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Minimal Fuseki HTTP helpers (no app.* imports)
# ---------------------------------------------------------------------------


def _auth_header() -> dict[str, str]:
    user = FUSEKI_USER.strip()
    if not user:
        return {}
    token = base64.b64encode(f"{user}:{FUSEKI_PASSWORD}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _query_endpoint() -> str:
    return f"{FUSEKI_URL.rstrip('/')}/{FUSEKI_DATASET.strip('/')}/query"


def _update_endpoint() -> str:
    return f"{FUSEKI_URL.rstrip('/')}/{FUSEKI_DATASET.strip('/')}/update"


def fuseki_select(sparql: str, timeout: int = 120) -> list[dict[str, str]]:
    """Execute a SPARQL SELECT and return bindings as list of dicts."""
    payload = parse.urlencode({"query": sparql}).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json",
    }
    headers.update(_auth_header())
    req = request.Request(_query_endpoint(), data=payload, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    bindings = body.get("results", {}).get("bindings", [])
    result: list[dict[str, str]] = []
    for row in bindings:
        result.append({k: v["value"] for k, v in row.items() if "value" in v})
    return result


def fuseki_update(sparql: str, timeout: int = 120) -> None:
    """Execute a SPARQL UPDATE."""
    payload = sparql.encode("utf-8")
    headers = {"Content-Type": "application/sparql-update"}
    headers.update(_auth_header())
    req = request.Request(_update_endpoint(), data=payload, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        resp.read()


# ---------------------------------------------------------------------------
# Step 1: Fetch movie data from Fuseki
# ---------------------------------------------------------------------------

FETCH_QUERY = """\
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?movie ?title ?directorUri ?genreName WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         movie:hasTitle ?title .
  OPTIONAL { ?movie movie:hasDirector ?directorUri }
  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }
}
"""


def fetch_movie_data() -> list[dict[str, str]]:
    """Return raw bindings: each row has movie, title, optionally directorUri/genreName."""
    log("Step 1: Fetching movie data from Fuseki ...")
    rows = fuseki_select(FETCH_QUERY, timeout=180)
    log(f"  Fetched {len(rows)} rows from Fuseki.")
    return rows


# ---------------------------------------------------------------------------
# Step 2: Build NetworkX graph
# ---------------------------------------------------------------------------


def build_graph(
    rows: list[dict[str, str]],
) -> tuple["nx.Graph", dict[str, str], dict[str, str]]:
    """Build a weighted movie-movie projected graph.

    Returns:
        G: the NetworkX graph (nodes = movie URIs)
        uri_to_title: mapping from URI to title
        uri_to_genre: mapping from URI to primary genre name
    """
    import networkx as nx  # type: ignore  # noqa: PLC0415

    log("Step 2: Building movie-movie graph ...")

    uri_to_title: dict[str, str] = {}
    uri_to_genre: dict[str, str] = {}

    # Collect groupings
    director_movies: dict[str, list[str]] = collections.defaultdict(list)
    genre_movies: dict[str, list[str]] = collections.defaultdict(list)

    for row in rows:
        movie_uri = row.get("movie", "")
        if not movie_uri:
            continue
        title = row.get("title", movie_uri)
        uri_to_title[movie_uri] = title

        director_uri = row.get("directorUri", "")
        genre_name = row.get("genreName", "")

        if genre_name and movie_uri not in genre_movies[genre_name]:
            genre_movies[genre_name].append(movie_uri)
            # Store first genre seen as primary genre
            if movie_uri not in uri_to_genre:
                uri_to_genre[movie_uri] = genre_name

        if director_uri and movie_uri not in director_movies[director_uri]:
            director_movies[director_uri].append(movie_uri)

    G: nx.Graph = nx.Graph()

    # Add all known movies as nodes first
    for uri, title in uri_to_title.items():
        G.add_node(uri, title=title)

    # Director edges (weight=2); skip prolific directors
    MAX_DIRECTOR_MOVIES = 30
    director_edges = 0
    for director_uri, movies in director_movies.items():
        if len(movies) > MAX_DIRECTOR_MOVIES:
            continue
        for u, v in itertools.combinations(movies, 2):
            if G.has_edge(u, v):
                G[u][v]["weight"] = G[u][v].get("weight", 0) + 2
            else:
                G.add_edge(u, v, weight=2)
                director_edges += 1

    # Genre edges (weight=1); limit to top 100 per genre
    MAX_GENRE_MOVIES = 500
    GENRE_SAMPLE = 100
    genre_edges = 0
    for genre_name, movies in genre_movies.items():
        sample = movies[:GENRE_SAMPLE] if len(movies) > MAX_GENRE_MOVIES else movies[:GENRE_SAMPLE]
        for u, v in itertools.combinations(sample, 2):
            if G.has_edge(u, v):
                G[u][v]["weight"] = G[u][v].get("weight", 0) + 1
            else:
                G.add_edge(u, v, weight=1)
                genre_edges += 1

    log(
        f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges "
        f"({director_edges} director-based, {genre_edges} genre-based)."
    )
    return G, uri_to_title, uri_to_genre


# ---------------------------------------------------------------------------
# Step 3: Compute centrality metrics
# ---------------------------------------------------------------------------


def compute_centralities(G: "nx.Graph") -> dict[str, dict[str, float]]:
    """Return dict with keys: degree, betweenness, pagerank, clustering."""
    import networkx as nx  # type: ignore  # noqa: PLC0415

    metrics: dict[str, dict[str, float]] = {}

    log("Step 3a: Computing degree centrality ...")
    try:
        metrics["degree"] = nx.degree_centrality(G)
        log(f"  Degree centrality computed for {len(metrics['degree'])} nodes.")
    except Exception as exc:  # noqa: BLE001
        log(f"  [WARN] Degree centrality failed: {exc}")
        metrics["degree"] = {}

    log("Step 3b: Computing betweenness centrality (approximate, k=300) ...")
    log("  [NOTE] Betweenness centrality may take several minutes on large graphs.")
    try:
        k_val = min(300, len(G))
        metrics["betweenness"] = nx.betweenness_centrality(G, k=k_val, normalized=True)
        log(f"  Betweenness centrality computed for {len(metrics['betweenness'])} nodes.")
    except Exception as exc:  # noqa: BLE001
        log(f"  [WARN] Betweenness centrality failed (skipping): {exc}")
        metrics["betweenness"] = {}

    log("Step 3c: Computing PageRank ...")
    try:
        metrics["pagerank"] = nx.pagerank(G, alpha=0.85, max_iter=100)
        log(f"  PageRank computed for {len(metrics['pagerank'])} nodes.")
    except Exception as exc:  # noqa: BLE001
        log(f"  [WARN] PageRank failed: {exc}")
        metrics["pagerank"] = {}

    log("Step 3d: Computing clustering coefficients ...")
    try:
        metrics["clustering"] = nx.clustering(G)
        log(f"  Clustering coefficient computed for {len(metrics['clustering'])} nodes.")
    except Exception as exc:  # noqa: BLE001
        log(f"  [WARN] Clustering coefficient failed: {exc}")
        metrics["clustering"] = {}

    return metrics


# ---------------------------------------------------------------------------
# Step 4: Community detection (Louvain)
# ---------------------------------------------------------------------------


def detect_communities(G: "nx.Graph") -> tuple[dict[str, int], float]:
    """Run Louvain community detection.

    Returns:
        partition: {node_uri: cluster_id_int}
        modularity: float
    """
    log("Step 4: Running Louvain community detection ...")
    try:
        import community as community_louvain  # type: ignore  # noqa: PLC0415

        partition: dict[str, int] = community_louvain.best_partition(G)
        modularity: float = community_louvain.modularity(partition, G)
        n_clusters = len(set(partition.values()))
        log(f"  Detected {n_clusters} communities. Modularity = {modularity:.4f}")
        return partition, modularity
    except Exception as exc:  # noqa: BLE001
        log(f"  [WARN] Community detection failed (skipping): {exc}")
        return {}, 0.0


# ---------------------------------------------------------------------------
# Step 5: Generate cluster labels using Gemini
# ---------------------------------------------------------------------------


def generate_cluster_labels(
    partition: dict[str, int],
    uri_to_genre: dict[str, str],
) -> dict[int, str]:
    """Generate Spanish descriptive labels for each cluster via Gemini.

    Returns:
        labels: {cluster_id: label_str}
    """
    if not partition:
        return {}

    log("Step 5: Generating cluster labels with Gemini ...")

    # Build cluster -> dominant genres mapping
    cluster_genres: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    for uri, cluster_id in partition.items():
        genre = uri_to_genre.get(uri, "")
        if genre:
            cluster_genres[cluster_id][genre] += 1

    labels: dict[int, str] = {}

    if not GEMINI_API_KEY:
        log("  [WARN] GEMINI_API_KEY not set — using fallback labels.")
        for cluster_id in set(partition.values()):
            labels[cluster_id] = f"Cluster {cluster_id}"
        return labels

    try:
        from google import genai  # type: ignore  # noqa: PLC0415

        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:  # noqa: BLE001
        log(f"  [WARN] Could not initialise Gemini client: {exc}. Using fallback labels.")
        for cluster_id in set(partition.values()):
            labels[cluster_id] = f"Cluster {cluster_id}"
        return labels

    cluster_ids = sorted(set(partition.values()))
    log(f"  Generating labels for {len(cluster_ids)} clusters ...")

    for cluster_id in cluster_ids:
        try:
            top_genres = [g for g, _ in cluster_genres[cluster_id].most_common(5)]
            genres_str = ", ".join(top_genres) if top_genres else "desconocido"
            prompt = (
                f"Genera un nombre descriptivo en español (máximo 5 palabras) para un cluster "
                f"de películas con estas características: géneros dominantes: {genres_str}. "
                f"Solo responde con el nombre, sin explicación."
            )
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            label = response.text.strip().strip('"').strip("'")
            if not label:
                raise ValueError("Empty response from Gemini")
            labels[cluster_id] = label
        except Exception as exc:  # noqa: BLE001
            log(f"  [WARN] Gemini failed for cluster {cluster_id}: {exc}. Using fallback.")
            labels[cluster_id] = f"Cluster {cluster_id}"

    log(f"  Cluster labels generated: {len(labels)}")
    return labels


# ---------------------------------------------------------------------------
# Step 6: Delete old metrics and write new ones to Fuseki
# ---------------------------------------------------------------------------

_DELETE_QUERIES = [
    "DELETE WHERE { ?m <{ns}degreeCentrality> ?v }",
    "DELETE WHERE { ?m <{ns}betweennessCentrality> ?v }",
    "DELETE WHERE { ?m <{ns}pageRank> ?v }",
    "DELETE WHERE { ?m <{ns}clusteringCoefficient> ?v }",
    "DELETE WHERE { ?m <{ns}belongsToCluster> ?v }",
    "DELETE WHERE { ?m <{ns}clusterLabel> ?v }",
]

_PREFIXES = f"""\
PREFIX movie: <{MOVIE_NS}>
PREFIX xsd: <{XSD_NS}>
"""


def _delete_old_metrics() -> None:
    log("Step 6a: Deleting old metric triples from Fuseki ...")
    for tmpl in _DELETE_QUERIES:
        sparql = _PREFIXES + tmpl.format(ns=MOVIE_NS)
        try:
            fuseki_update(sparql, timeout=120)
        except Exception as exc:  # noqa: BLE001
            log(f"  [WARN] Delete failed ({tmpl[:40]}...): {exc}")
    log("  Old metric triples deleted.")


def _escape_string(s: str) -> str:
    """Escape backslashes and double quotes for SPARQL string literals."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_to_fuseki(
    G: "nx.Graph",
    metrics: dict[str, dict[str, float]],
    partition: dict[str, int],
    labels: dict[int, str],
    batch_size: int = 500,
) -> None:
    """Write all computed metrics to Fuseki in batches."""
    _delete_old_metrics()

    log("Step 6b: Writing new metric triples to Fuseki ...")

    degree = metrics.get("degree", {})
    betweenness = metrics.get("betweenness", {})
    pagerank = metrics.get("pagerank", {})
    clustering = metrics.get("clustering", {})

    nodes = list(G.nodes())
    triples: list[str] = []

    for uri in nodes:
        deg = degree.get(uri, 0.0)
        bet = betweenness.get(uri, 0.0)
        pr = pagerank.get(uri, 0.0)
        clust = clustering.get(uri, 0.0)
        cluster_id = partition.get(uri)
        label = labels.get(cluster_id, f"Cluster {cluster_id}") if cluster_id is not None else ""

        triple_lines: list[str] = [
            f'<{uri}> <{MOVIE_NS}degreeCentrality> "{deg:.6f}"^^xsd:float',
            f'<{uri}> <{MOVIE_NS}pageRank> "{pr:.8f}"^^xsd:float',
            f'<{uri}> <{MOVIE_NS}clusteringCoefficient> "{clust:.6f}"^^xsd:float',
        ]

        if betweenness:
            triple_lines.append(
                f'<{uri}> <{MOVIE_NS}betweennessCentrality> "{bet:.6f}"^^xsd:float'
            )

        if cluster_id is not None:
            triple_lines.append(
                f'<{uri}> <{MOVIE_NS}belongsToCluster> "{cluster_id}"^^xsd:string'
            )
            safe_label = _escape_string(label)
            triple_lines.append(
                f'<{uri}> <{MOVIE_NS}clusterLabel> "{safe_label}"^^xsd:string'
            )

        triples.extend(triple_lines)

    # Send in batches
    total = len(triples)
    sent = 0
    batch_num = 0
    while sent < total:
        batch = triples[sent : sent + batch_size]
        body = _PREFIXES + "INSERT DATA {\n  " + " .\n  ".join(batch) + " .\n}"
        try:
            fuseki_update(body, timeout=180)
        except Exception as exc:  # noqa: BLE001
            log(f"  [ERROR] Batch {batch_num} failed: {exc}")
        sent += len(batch)
        batch_num += 1
        log(f"  Written batch {batch_num} ({min(sent, total)}/{total} triples) ...")

    log(f"  All {total} triples written in {batch_num} batches.")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def main() -> None:
    log("=" * 60)
    log("CineSemantico — Phase 6: NetworkX Offline Metrics Pipeline")
    log("=" * 60)
    log(f"Fuseki: {FUSEKI_URL}/{FUSEKI_DATASET}")

    # Import NetworkX here so we can give a friendly error message
    try:
        import networkx as nx  # type: ignore  # noqa: F401, PLC0415
    except ImportError:
        print(
            "[ERROR] networkx is not installed. Run:\n"
            "  pip install networkx python-louvain scipy google-genai python-dotenv",
            file=sys.stderr,
        )
        sys.exit(1)

    # Step 1: Fetch
    try:
        rows = fetch_movie_data()
    except Exception as exc:
        log(f"[ERROR] Could not fetch data from Fuseki: {exc}")
        sys.exit(1)

    if not rows:
        log("[ERROR] No movie data returned from Fuseki. Is the dataset loaded?")
        sys.exit(1)

    # Step 2: Build graph
    try:
        G, uri_to_title, uri_to_genre = build_graph(rows)
    except Exception as exc:
        log(f"[ERROR] Graph construction failed: {exc}")
        sys.exit(1)

    if G.number_of_nodes() == 0:
        log("[ERROR] Graph has no nodes. Check Fuseki data.")
        sys.exit(1)

    # Step 3: Centralities
    try:
        metrics = compute_centralities(G)
    except Exception as exc:
        log(f"[ERROR] Centrality computation failed: {exc}")
        metrics = {"degree": {}, "betweenness": {}, "pagerank": {}, "clustering": {}}

    # Step 4: Communities
    try:
        partition, modularity = detect_communities(G)
    except Exception as exc:
        log(f"[WARN] Community detection error: {exc}")
        partition, modularity = {}, 0.0

    # Step 5: Cluster labels
    try:
        labels = generate_cluster_labels(partition, uri_to_genre)
    except Exception as exc:
        log(f"[WARN] Cluster label generation error: {exc}")
        labels = {cid: f"Cluster {cid}" for cid in set(partition.values())}

    # Step 6: Write to Fuseki
    try:
        write_to_fuseki(G, metrics, partition, labels)
    except Exception as exc:
        log(f"[ERROR] Writing to Fuseki failed: {exc}")
        sys.exit(1)

    log("=" * 60)
    log("Phase 6 pipeline completed successfully.")
    if modularity:
        log(f"  Louvain modularity: {modularity:.4f}")
    log(f"  Nodes processed: {G.number_of_nodes()}")
    log(f"  Clusters detected: {len(set(partition.values()))}")
    log("=" * 60)


if __name__ == "__main__":
    main()
