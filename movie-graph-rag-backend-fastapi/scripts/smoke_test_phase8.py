"""Phase 8 smoke test — Topological Dashboard.

Verifies that:
  1. The Pydantic schemas import and serialise correctly.
  2. The endpoint module imports without errors.
  3. SPARQL queries return plausible data from Fuseki (requires Phase 6 data).

Run from the project root (with Fuseki active and Phase 6 metrics loaded):

    python scripts/smoke_test_phase8.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PASS = "\033[92mPASS\033[0m"
_FAIL = "\033[91mFAIL\033[0m"

_results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    _results.append((label, condition, detail))
    status = _PASS if condition else _FAIL
    print(f"  [{status}]  {label}" + (f" — {detail}" if detail and not condition else ""))


def section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


# ---------------------------------------------------------------------------
# Section 1 — Schema imports
# ---------------------------------------------------------------------------

section("1 - Schema imports")

try:
    from app.api.schemas.graph import (
        CentralityEntry,
        ClusterEntry,
        GraphSummary,
        GraphTopologyResponse,
    )
    check("graph schemas import", True)
except ImportError as e:
    check("graph schemas import", False, str(e))
    sys.exit(1)

# Instantiate manually
summary = GraphSummary(
    totalMovies=1000,
    totalEdges=50000,
    averageDegree=100.0,
    averageClusteringCoefficient=0.42,
    communityCount=15,
    modularity=0.61,
    isSmallWorld=True,
)
entry = CentralityEntry(title="Pulp Fiction", value=0.0812, genre="Crime")
cluster = ClusterEntry(clusterId="5", label="Thriller Psicológico", size=312)

resp = GraphTopologyResponse(
    graphSummary=summary,
    topByDegree=[entry],
    topByBetweenness=[entry],
    topByPageRank=[entry],
    clusterSummary=[cluster],
)
d = resp.model_dump()

check("GraphTopologyResponse serialises", "graphSummary" in d and "topByDegree" in d)
check("graphSummary.isSmallWorld correct", d["graphSummary"]["isSmallWorld"] is True)
check("CentralityEntry.value serialises", d["topByDegree"][0]["value"] == 0.0812)
check("ClusterEntry.size serialises", d["clusterSummary"][0]["size"] == 312)

# ---------------------------------------------------------------------------
# Section 2 — Endpoint module imports
# ---------------------------------------------------------------------------

section("2 - Endpoint module imports")

try:
    from app.api.v1.endpoints.graph import router, get_graph_topology
    check("graph endpoint imports", True)
    check("router prefix correct", router.prefix == "/graph")
    check("get_graph_topology is callable", callable(get_graph_topology))
except ImportError as e:
    check("graph endpoint imports", False, str(e))

# ---------------------------------------------------------------------------
# Section 3 — Fuseki queries (requires Phase 6 data)
# ---------------------------------------------------------------------------

section("3 - Fuseki queries (Phase 6 data required)")

try:
    from app.core.fuseki_client import execute_select_query

    _PREFIXES = (
        "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
    )

    # 3.1 At least 500 movies with degreeCentrality
    count_rows = execute_select_query(
        _PREFIXES + "SELECT (COUNT(DISTINCT ?m) AS ?c) WHERE { ?m movie:degreeCentrality ?d }"
    )
    count = int(count_rows[0].get("c", 0)) if count_rows else 0
    check("degreeCentrality -- >=500 movies", count >= 500, f"got {count}")

    # 3.2 Top-10 by degree returns 10 entries
    top_degree = execute_select_query(
        _PREFIXES
        + "SELECT ?title ?value WHERE { ?m movie:hasTitle ?title ; movie:degreeCentrality ?value } "
        "ORDER BY DESC(?value) LIMIT 10"
    )
    check("top-10 by degree returns 10 rows", len(top_degree) == 10, f"got {len(top_degree)}")

    # 3.3 Values in [0, 1]
    values = []
    for row in top_degree:
        try:
            values.append(float(row.get("value", 0)))
        except (ValueError, TypeError):
            pass
    check(
        "degree values in [0, 1]",
        all(0.0 <= v <= 1.0 for v in values),
        f"out-of-range: {[v for v in values if not 0.0 <= v <= 1.0]}",
    )

    # 3.4 betweennessCentrality present
    btw_rows = execute_select_query(
        _PREFIXES + "SELECT (COUNT(?m) AS ?c) WHERE { ?m movie:betweennessCentrality ?b }"
    )
    btw_count = int(btw_rows[0].get("c", 0)) if btw_rows else 0
    check("betweennessCentrality -- >=500 movies", btw_count >= 500, f"got {btw_count}")

    # 3.5 pageRank present
    pr_rows = execute_select_query(
        _PREFIXES + "SELECT (COUNT(?m) AS ?c) WHERE { ?m movie:pageRank ?pr }"
    )
    pr_count = int(pr_rows[0].get("c", 0)) if pr_rows else 0
    check("pageRank -- >=500 movies", pr_count >= 500, f"got {pr_count}")

    # 3.6 At least 5 clusters
    cluster_rows = execute_select_query(
        _PREFIXES + "SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?m movie:belongsToCluster ?c }"
    )
    cluster_count = int(cluster_rows[0].get("n", 0)) if cluster_rows else 0
    check("clusters -- >=5 distinct", cluster_count >= 5, f"got {cluster_count}")

    # 3.7 clusterLabel non-empty for at least one cluster
    label_rows = execute_select_query(
        _PREFIXES + "SELECT ?label WHERE { ?m movie:clusterLabel ?label } LIMIT 5"
    )
    labels = [r.get("label", "") for r in label_rows]
    check(
        "clusterLabel non-empty for >=1 entry",
        any(len(str(l)) > 0 for l in labels),
        f"labels={labels}",
    )

    # 3.8 Full _build_topology() executes without error
    from app.api.v1.endpoints.graph import _build_topology
    topo = _build_topology()
    check("_build_topology() returns GraphTopologyResponse", isinstance(topo, GraphTopologyResponse))
    check(
        "graphSummary.totalMovies >=500",
        topo.graphSummary.totalMovies >= 500,
        f"got {topo.graphSummary.totalMovies}",
    )
    check(
        "communityCount >=5",
        topo.graphSummary.communityCount >= 5,
        f"got {topo.graphSummary.communityCount}",
    )
    check(
        "topByDegree has 10 entries",
        len(topo.topByDegree) == 10,
        f"got {len(topo.topByDegree)}",
    )
    check(
        "clusterSummary non-empty",
        len(topo.clusterSummary) > 0,
        f"got {len(topo.clusterSummary)}",
    )
    check(
        "modularity in [0, 1]",
        0.0 <= topo.graphSummary.modularity <= 1.0,
        f"got {topo.graphSummary.modularity}",
    )

except Exception as e:
    check("Fuseki queries (skipped - Fuseki not available)", False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in _results if ok)
total = len(_results)
if passed == total:
    print(f"  \033[92m[OK] All {total} checks passed -- Phase 8 smoke test OK\033[0m")
else:
    failed = [(label, detail) for label, ok, detail in _results if not ok]
    print(f"  \033[91m[FAIL] {passed}/{total} passed\033[0m")
    for label, detail in failed:
        print(f"         x {label}" + (f": {detail}" if detail else ""))
    sys.exit(1)
print("=" * 60)
