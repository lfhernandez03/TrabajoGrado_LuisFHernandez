"""Phase 7 smoke test — Graph Diversity Score.

Runs without requiring Fuseki or Gemini.  Execute from the project root:

    python scripts/smoke_test_phase7.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Helpers
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
# Fixtures
# ---------------------------------------------------------------------------

from app.domain.entities.recommendation_models import Movie, UserProfile


def _movie(title: str, genre: str | None = "Drama", compat: float = 0.8) -> Movie:
    return Movie(
        uri=f"http://test/{title.replace(' ', '_')}",
        title=title,
        genre=genre,
        runtime=100,
        rating=7.0,
        poster_url=None,
        release_year="2020",
        compatibility_score=compat,
        semantic_scores={},
        kid_friendly=None,
    )


def _profile(genre_weights: dict[str, float] | None = None) -> UserProfile:
    return UserProfile(
        user_id="u1",
        genre_weights=genre_weights or {"Drama": 0.7, "Comedy": 0.5, "Action": 0.2},
        dominant_mood=None,
        dominant_companion=None,
        snapshot_count=0,
        is_cold_start=True,
        dominant_time_of_day=None,
        children_age_hint=None,
    )


# ---------------------------------------------------------------------------
# Mock explorer
# ---------------------------------------------------------------------------

class _MockExplorer:
    """Returns ConnectionPath(found=False) for every pair — simulates no path found."""

    def find_path(self, a: str, b: str):
        from app.core.connection_explorer import ConnectionPath
        return ConnectionPath(source=a, target=b, hops=[], found=False)


# ---------------------------------------------------------------------------
# Section 1 — Imports
# ---------------------------------------------------------------------------

section("1 - Imports")

try:
    from app.core.metrics import compute_graph_diversity, ListMetrics
    check("compute_graph_diversity and ListMetrics import successfully", True)
except ImportError as e:
    check("compute_graph_diversity and ListMetrics import successfully", False, str(e))
    print("\n[ABORT] Cannot continue without compute_graph_diversity.")
    sys.exit(1)

try:
    from app.api.schemas.recommendation import RecommendationMetricsResponse
    check("RecommendationMetricsResponse imports successfully", True)
except ImportError as e:
    check("RecommendationMetricsResponse imports successfully", False, str(e))
    sys.exit(1)

# ---------------------------------------------------------------------------
# Section 2 — graphDiversityScore field on schema
# ---------------------------------------------------------------------------

section("2 - RecommendationMetricsResponse has graphDiversityScore field")

check(
    "graphDiversityScore field exists on RecommendationMetricsResponse",
    "graphDiversityScore" in RecommendationMetricsResponse.model_fields,
)

field_info = RecommendationMetricsResponse.model_fields.get("graphDiversityScore")
check(
    "graphDiversityScore default is 0.0",
    field_info is not None and field_info.default == 0.0,
    f"default was {field_info.default if field_info else 'N/A'}",
)

# ---------------------------------------------------------------------------
# Section 3 — compute_graph_diversity: single movie returns 1.0
# ---------------------------------------------------------------------------

section("3 - compute_graph_diversity: single movie returns 1.0 (no pairs)")

single = [_movie("Inception")]
score_single = compute_graph_diversity(single, _MockExplorer())
check(
    "Single movie list returns 1.0",
    score_single == 1.0,
    f"got {score_single}",
)

# ---------------------------------------------------------------------------
# Section 4 — compute_graph_diversity: two movies, path not found → 1.0
# ---------------------------------------------------------------------------

section("4 - compute_graph_diversity: path not found treated as max distance")

two_movies = [_movie("Inception"), _movie("The Matrix")]
score_no_path = compute_graph_diversity(two_movies, _MockExplorer())
# _MockExplorer returns found=False → hops treated as _MAX_HOPS (3) → 3/3 = 1.0
check(
    "Two movies with no path found returns 1.0 (max distance = 3/3)",
    score_no_path == 1.0,
    f"got {score_no_path}",
)

# ---------------------------------------------------------------------------
# Section 5 — ListMetrics has graph_diversity_score field defaulting to 0.0
# ---------------------------------------------------------------------------

section("5 - ListMetrics.graph_diversity_score field")

m = ListMetrics(
    ild=0.8,
    semantic_precision=0.6,
    cold_start_threshold=3,
    semantic_threshold=0.7,
    movie_count=5,
)
check(
    "ListMetrics has graph_diversity_score field",
    hasattr(m, "graph_diversity_score"),
)
check(
    "graph_diversity_score defaults to 0.0",
    m.graph_diversity_score == 0.0,
    f"got {m.graph_diversity_score}",
)

# ---------------------------------------------------------------------------
# Section 6 — compute_metrics with explorer=None returns graph_diversity_score=0.0
# ---------------------------------------------------------------------------

section("6 - compute_metrics(explorer=None) returns graph_diversity_score=0.0")

from app.core.metrics import compute_metrics

movies_5 = [
    _movie("A", "Drama", compat=0.85),
    _movie("B", "Comedy", compat=0.9),
    _movie("C", "Action", compat=0.4),
    _movie("D", "Horror", compat=0.75),
    _movie("E", "Sci-Fi", compat=0.8),
]
profile = _profile()

result_no_explorer = compute_metrics(movies_5, profile, explorer=None)
check(
    "compute_metrics returns ListMetrics",
    isinstance(result_no_explorer, ListMetrics),
)
check(
    "graph_diversity_score is 0.0 when explorer=None",
    result_no_explorer.graph_diversity_score == 0.0,
    f"got {result_no_explorer.graph_diversity_score}",
)
check(
    "compute_metrics still computes ILD correctly without explorer",
    result_no_explorer.ild == 1.0,
    f"got {result_no_explorer.ild}",
)

# ---------------------------------------------------------------------------
# Section 7 — Schema serialization includes graphDiversityScore
# ---------------------------------------------------------------------------

section("7 - RecommendationMetricsResponse serialization")

schema = RecommendationMetricsResponse(
    ild=0.5,
    graphDiversityScore=0.7,
    semanticPrecision=0.8,
    coldStartThreshold=3,
    movieCount=5,
)
d = schema.model_dump()

check(
    "Serialized dict contains graphDiversityScore",
    "graphDiversityScore" in d,
    f"keys: {list(d.keys())}",
)
check(
    "graphDiversityScore serializes correctly",
    d["graphDiversityScore"] == 0.7,
    f"got {d.get('graphDiversityScore')}",
)
check(
    "All expected fields present in serialized dict",
    all(k in d for k in ("ild", "graphDiversityScore", "semanticPrecision", "coldStartThreshold", "movieCount")),
    f"missing: {[k for k in ('ild','graphDiversityScore','semanticPrecision','coldStartThreshold','movieCount') if k not in d]}",
)
check(
    "ild value correct",
    d["ild"] == 0.5,
    f"got {d.get('ild')}",
)
check(
    "semanticPrecision value correct",
    d["semanticPrecision"] == 0.8,
    f"got {d.get('semanticPrecision')}",
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in _results if ok)
total = len(_results)
if passed == total:
    print(f"  \033[92m[OK] All {total} checks passed -- Phase 7 smoke test OK\033[0m")
else:
    failed = [(label, detail) for label, ok, detail in _results if not ok]
    print(f"  \033[91m[FAIL] {passed}/{total} passed\033[0m")
    for label, detail in failed:
        print(f"         x {label}" + (f": {detail}" if detail else ""))
    sys.exit(1)
print("=" * 60)
