"""Phase 6 smoke test — NetworkX offline metrics: degree, pageRank, clusters.

Verifies that compute_network_metrics.py wrote valid triples to Fuseki.
Run from the project root:

    python scripts/smoke_test_phase6.py

Requires Fuseki to be running and Phase 6 pipeline to have been executed first.
"""
from __future__ import annotations

import os
import sys
import urllib.error

# Make app.* importable from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Helpers (same style as smoke_test_phase5.py)
# ---------------------------------------------------------------------------

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
# Import Fuseki client (via app.*)
# ---------------------------------------------------------------------------

section("0 - Fuseki connectivity")

try:
    from app.core.fuseki_client import FusekiQueryError, execute_select_query  # type: ignore
    check("app.core.fuseki_client imported", True)
except ImportError as exc:
    check("app.core.fuseki_client imported", False, str(exc))
    print("\n[ABORT] Cannot import fuseki_client. Make sure you run from the project root.")
    sys.exit(1)

# Quick connectivity check
_PING_QUERY = """\
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
SELECT (COUNT(?m) AS ?cnt) WHERE {
  ?m movie:degreeCentrality ?v .
}
"""

try:
    _ping_rows = execute_select_query(_PING_QUERY)
    check("Fuseki is reachable", True)
except (FusekiQueryError, urllib.error.URLError, OSError) as exc:
    check("Fuseki is reachable", False, str(exc))
    print("\n[ABORT] Fuseki is not reachable. Start Fuseki and re-run the Phase 6 pipeline first.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Shared SPARQL helper
# ---------------------------------------------------------------------------

MOVIE_NS = "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#"


def _count(predicate: str) -> int:
    """Return the number of movies that have the given predicate."""
    sparql = f"""\
SELECT (COUNT(DISTINCT ?m) AS ?cnt) WHERE {{
  ?m <{MOVIE_NS}{predicate}> ?v .
}}
"""
    try:
        rows = execute_select_query(sparql)
        return int(rows[0].get("cnt", 0)) if rows else 0
    except Exception:  # noqa: BLE001
        return -1


def _distinct_values(predicate: str) -> list[str]:
    """Return all distinct object values for the given predicate."""
    sparql = f"""\
SELECT DISTINCT ?v WHERE {{
  ?m <{MOVIE_NS}{predicate}> ?v .
}}
LIMIT 5000
"""
    try:
        rows = execute_select_query(sparql)
        return [r.get("v", "") for r in rows]
    except Exception:  # noqa: BLE001
        return []


def _sample_values(predicate: str, limit: int = 200) -> list[str]:
    """Return a sample of object values for the given predicate."""
    sparql = f"""\
SELECT ?v WHERE {{
  ?m <{MOVIE_NS}{predicate}> ?v .
}}
LIMIT {limit}
"""
    try:
        rows = execute_select_query(sparql)
        return [r.get("v", "") for r in rows]
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Section 1 — degree centrality coverage and range
# ---------------------------------------------------------------------------

section("1 - movie:degreeCentrality")

deg_count = _count("degreeCentrality")
check(
    "At least 500 movies have degreeCentrality",
    deg_count >= 500,
    f"found {deg_count}",
)

deg_values = _sample_values("degreeCentrality", limit=500)
if deg_values:
    try:
        floats = [float(v) for v in deg_values]
        in_range = all(0.0 <= f <= 1.0 for f in floats)
        out_of_range = [f for f in floats if not (0.0 <= f <= 1.0)]
        check(
            "All sampled degreeCentrality values in [0.0, 1.0]",
            in_range,
            f"{len(out_of_range)} values out of range" if not in_range else "",
        )
    except ValueError as exc:
        check("All sampled degreeCentrality values in [0.0, 1.0]", False, str(exc))
else:
    check("All sampled degreeCentrality values in [0.0, 1.0]", False, "no values returned")

# ---------------------------------------------------------------------------
# Section 2 — cluster assignment coverage
# ---------------------------------------------------------------------------

section("2 - movie:belongsToCluster")

cluster_values = _distinct_values("belongsToCluster")
n_clusters = len(cluster_values)
check(
    "At least 5 distinct clusters detected",
    n_clusters >= 5,
    f"found {n_clusters} distinct cluster IDs",
)

# ---------------------------------------------------------------------------
# Section 3 — cluster labels
# ---------------------------------------------------------------------------

section("3 - movie:clusterLabel")

label_values = _distinct_values("clusterLabel")
n_labels = len(label_values)
check(
    "At least 5 distinct clusterLabel values exist",
    n_labels >= 5,
    f"found {n_labels} distinct labels",
)

empty_labels = [v for v in label_values if not v.strip()]
check(
    "No empty clusterLabel values",
    len(empty_labels) == 0,
    f"{len(empty_labels)} empty labels found" if empty_labels else "",
)

# ---------------------------------------------------------------------------
# Section 4 — pageRank coverage and positivity
# ---------------------------------------------------------------------------

section("4 - movie:pageRank")

pr_count = _count("pageRank")
check(
    "At least 500 movies have pageRank",
    pr_count >= 500,
    f"found {pr_count}",
)

pr_values = _sample_values("pageRank", limit=500)
if pr_values:
    try:
        pr_floats = [float(v) for v in pr_values]
        all_positive = all(f > 0.0 for f in pr_floats)
        non_positive = [f for f in pr_floats if f <= 0.0]
        check(
            "All sampled pageRank values are > 0.0",
            all_positive,
            f"{len(non_positive)} non-positive values found" if not all_positive else "",
        )
    except ValueError as exc:
        check("All sampled pageRank values are > 0.0", False, str(exc))
else:
    check("All sampled pageRank values are > 0.0", False, "no values returned")

# ---------------------------------------------------------------------------
# Section 5 — clustering coefficient and betweenness (optional presence check)
# ---------------------------------------------------------------------------

section("5 - movie:clusteringCoefficient and movie:betweennessCentrality")

cc_count = _count("clusteringCoefficient")
check(
    "At least 500 movies have clusteringCoefficient",
    cc_count >= 500,
    f"found {cc_count}",
)

bet_count = _count("betweennessCentrality")
check(
    "betweennessCentrality present for at least 1 movie (optional step)",
    bet_count >= 1,
    f"found {bet_count} (0 means betweenness step was skipped or failed)",
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in _results if ok)
total = len(_results)
if passed == total:
    print(f"  \033[92m[OK] All {total} checks passed -- Phase 6 smoke test OK\033[0m")
else:
    failed = [(label, detail) for label, ok, detail in _results if not ok]
    print(f"  \033[91m[FAIL] {passed}/{total} passed\033[0m")
    for label, detail in failed:
        print(f"         x {label}" + (f": {detail}" if detail else ""))
    sys.exit(1)
print("=" * 60)
