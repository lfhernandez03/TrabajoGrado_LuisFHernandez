"""Phase 9 smoke test -- Cluster-Based Recommendation.

Verifies:
  1. Pydantic schemas import and serialise correctly.
  2. Endpoint module imports, router tags/routes present.
  3. GET /clusters returns clusters from Fuseki (requires Phase 6 data).
  4. GET /movies/{title}/cluster returns valid intra/adjacent data.

Run with Fuseki active and Phase 6 metrics loaded:

    python scripts/smoke_test_phase9.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PASS = "\033[92mPASS\033[0m"
_FAIL = "\033[91mFAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    _results.append((label, condition, detail))
    status = _PASS if condition else _FAIL
    suffix = f" -- {detail}" if detail and not condition else ""
    print(f"  [{status}]  {label}{suffix}")


def section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


# ---------------------------------------------------------------------------
# Section 1 -- Schema imports and serialisation
# ---------------------------------------------------------------------------

section("1 - Schema imports")

try:
    from app.api.schemas.clusters import (
        AdjacentCluster,
        ClusterInfo,
        ClusterListItem,
        ClusterListResponse,
        ClusterMovie,
        MovieClusterResponse,
    )
    check("cluster schemas import", True)
except ImportError as e:
    check("cluster schemas import", False, str(e))
    sys.exit(1)

m = ClusterMovie(title="Interstellar", rating=4.5, genre="Sci-Fi", posterUrl=None)
ci = ClusterInfo(id="14", label="Sci-Fi Epico", size=312, dominantGenres=["Sci-Fi", "Drama"])
adj = AdjacentCluster(
    clusterId="7", label="Drama Historico", sharedGenres=["Drama"], bridgeMovies=[m]
)
resp = MovieClusterResponse(movie="Interstellar", cluster=ci, intraCluster=[m], adjacentClusters=[adj])
d = resp.model_dump()

check("MovieClusterResponse serialises", "cluster" in d and "intraCluster" in d)
check("cluster.dominantGenres serialises", d["cluster"]["dominantGenres"] == ["Sci-Fi", "Drama"])
check("adjacentClusters[0].bridgeMovies non-empty", len(d["adjacentClusters"][0]["bridgeMovies"]) == 1)

li = ClusterListItem(clusterId="14", label="Sci-Fi Epico", size=312, exampleMovies=["Interstellar"])
lr = ClusterListResponse(clusters=[li], total=1)
ld = lr.model_dump()
check("ClusterListResponse serialises", ld["total"] == 1)
check("exampleMovies serialises", ld["clusters"][0]["exampleMovies"] == ["Interstellar"])

# ---------------------------------------------------------------------------
# Section 2 -- Endpoint module imports
# ---------------------------------------------------------------------------

section("2 - Endpoint module imports")

try:
    from app.api.v1.endpoints.clusters import (
        router,
        get_movie_cluster,
        list_clusters,
        _cached_cluster_list,
        _get_movie_cluster,
        _escape,
    )
    check("clusters endpoint imports", True)
    check("router tags include 'clusters'", "clusters" in router.tags)

    routes = {r.path for r in router.routes}  # type: ignore[attr-defined]
    check("GET /movies/{title}/cluster route exists", "/movies/{title}/cluster" in routes)
    check("GET /clusters route exists", "/clusters" in routes)
except ImportError as e:
    check("clusters endpoint imports", False, str(e))

# _escape helper
check("_escape handles double-quote", _escape('He said "hi"') == 'He said \\"hi\\"')
check("_escape handles backslash", _escape("a\\b") == "a\\\\b")

# ---------------------------------------------------------------------------
# Section 3 -- Fuseki: cluster list
# ---------------------------------------------------------------------------

section("3 - Fuseki: GET /clusters (Phase 6 data required)")

try:
    result = _cached_cluster_list()
    check("_cached_cluster_list() returns ClusterListResponse", isinstance(result, ClusterListResponse))
    check("total >= 5 clusters", result.total >= 5, f"got {result.total}")
    check("clusters list non-empty", len(result.clusters) > 0)

    first = result.clusters[0]
    check("first cluster has non-empty label", len(first.label) > 0, f"got '{first.label}'")
    check("first cluster size > 0", first.size > 0, f"got {first.size}")
    check("first cluster has example movies", len(first.exampleMovies) > 0)
    check(
        "clusters ordered by size DESC",
        all(
            result.clusters[i].size >= result.clusters[i + 1].size
            for i in range(min(5, len(result.clusters) - 1))
        ),
    )
except Exception as e:
    check("Fuseki cluster list (skipped - Fuseki not available)", False, str(e))

# ---------------------------------------------------------------------------
# Section 4 -- Fuseki: GET /movies/{title}/cluster
# ---------------------------------------------------------------------------

section("4 - Fuseki: GET /movies/{title}/cluster (Phase 6 data required)")

# Use the first example movie from the largest cluster as the test subject
_test_title = ""
try:
    if result.clusters and result.clusters[0].exampleMovies:
        _test_title = result.clusters[0].exampleMovies[0]
except Exception:
    pass

if not _test_title:
    check("test movie available for cluster lookup", False, "no example movie found in cluster list")
else:
    check("test movie available for cluster lookup", True, f"using '{_test_title}'")
    try:
        movie_result = _get_movie_cluster(_test_title)
        check(
            "_get_movie_cluster() returns MovieClusterResponse",
            isinstance(movie_result, MovieClusterResponse),
        )
        check("movie field matches input title", movie_result.movie == _test_title)
        check("cluster.id non-empty", len(movie_result.cluster.id) > 0)
        check("cluster.label non-empty", len(movie_result.cluster.label) > 0)
        check("cluster.size > 1", movie_result.cluster.size > 1, f"got {movie_result.cluster.size}")
        check(
            "intraCluster has >= 3 movies",
            len(movie_result.intraCluster) >= 3,
            f"got {len(movie_result.intraCluster)}",
        )
        check(
            "intraCluster movies have titles",
            all(len(m.title) > 0 for m in movie_result.intraCluster),
        )
        check(
            "adjacentClusters >= 1",
            len(movie_result.adjacentClusters) >= 1,
            f"got {len(movie_result.adjacentClusters)}",
        )
        if movie_result.adjacentClusters:
            adj0 = movie_result.adjacentClusters[0]
            check("adjacentCluster.label non-empty", len(adj0.label) > 0)
            check("adjacentCluster.bridgeMovies non-empty", len(adj0.bridgeMovies) > 0)
    except Exception as e:
        check("_get_movie_cluster() executes without error", False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in _results if ok)
total = len(_results)
if passed == total:
    print(f"  \033[92m[OK] All {total} checks passed -- Phase 9 smoke test OK\033[0m")
else:
    failed = [(label, detail) for label, ok, detail in _results if not ok]
    print(f"  \033[91m[FAIL] {passed}/{total} passed\033[0m")
    for label, detail in failed:
        print(f"         x {label}" + (f": {detail}" if detail else ""))
    sys.exit(1)
print("=" * 60)
