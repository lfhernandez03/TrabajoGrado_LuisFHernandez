"""Phase 10 smoke test -- Serendipity Engine.

Verifies:
  1. serendipity_score field exists on Movie dataclass.
  2. serendipityScore field exists on RecommendedMovieResponse.
  3. _compute_serendipity returns values in [0, 1].
  4. _compute_score uses serendipity formula when network data present.
  5. score_and_select populates serendipity_score on returned Movie objects.
  6. Backward compatibility: base formula unchanged when no network data.

Run (Fuseki optional -- sections 1-5 are pure unit tests):

    python scripts/smoke_test_phase10.py
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
# Section 1 -- Domain entity
# ---------------------------------------------------------------------------

section("1 - Movie dataclass has serendipity_score")

from app.domain.entities.recommendation_models import Movie, UserContext, UserProfile

m = Movie(uri="http://example.org/m1", title="Test Movie")
check("serendipity_score field exists with default 0.0", m.serendipity_score == 0.0)

d = m.to_response_dict()
check("to_response_dict includes serendipityScore", "serendipityScore" in d)
check("to_response_dict serendipityScore default is 0.0", d["serendipityScore"] == 0.0)

m2 = Movie(uri="http://example.org/m2", title="Bridge Movie", serendipity_score=0.42)
d2 = m2.to_response_dict()
check("to_response_dict propagates serendipity_score", d2["serendipityScore"] == 0.42)

# ---------------------------------------------------------------------------
# Section 2 -- Response schema
# ---------------------------------------------------------------------------

section("2 - RecommendedMovieResponse schema")

from app.api.schemas.recommendation import RecommendedMovieResponse

r = RecommendedMovieResponse(title="Test", serendipityScore=0.31)
check("serendipityScore field exists", r.serendipityScore == 0.31)

r_default = RecommendedMovieResponse(title="Test")
check("serendipityScore defaults to 0.0", r_default.serendipityScore == 0.0)

rd = r.model_dump()
check("serendipityScore serialises in model_dump", rd["serendipityScore"] == 0.31)

# ---------------------------------------------------------------------------
# Section 3 -- _compute_serendipity formula
# ---------------------------------------------------------------------------

section("3 - _compute_serendipity formula")

from app.core.scorer import _compute_serendipity

# Bridge movie: high betweenness, low clustering, low degree, high compatibility
bridge = Movie(uri="u1", title="Bridge Film", compatibility_score=0.9)
bridge_network = {"betweenness": 0.8, "clustering": 0.1, "degree": 0.1}
s_bridge = _compute_serendipity(bridge, bridge_network)
check("bridge movie serendipity > 0", s_bridge > 0.0, f"got {s_bridge:.4f}")
check("bridge movie serendipity in [0, 1]", 0.0 <= s_bridge <= 1.0, f"got {s_bridge:.4f}")

# Mainstream movie: high degree, high clustering, low betweenness
mainstream = Movie(uri="u2", title="Mainstream Film", compatibility_score=0.8)
mainstream_network = {"betweenness": 0.02, "clustering": 0.85, "degree": 0.95}
s_mainstream = _compute_serendipity(mainstream, mainstream_network)
check("mainstream movie serendipity < bridge movie", s_mainstream < s_bridge,
      f"mainstream={s_mainstream:.4f} bridge={s_bridge:.4f}")

# No network data -> 0.0
s_none = _compute_serendipity(bridge, {})
check("empty network returns 0.0", s_none == 0.0)

# Betweenness = 0 -> 0.0 (no bridge role)
s_no_between = _compute_serendipity(bridge, {"betweenness": 0.0, "clustering": 0.1, "degree": 0.1})
check("betweenness=0 returns 0.0", s_no_between == 0.0)

# Result always clamped to [0, 1]
extreme = Movie(uri="u3", title="Extreme", compatibility_score=1.0)
s_extreme = _compute_serendipity(extreme, {"betweenness": 1.0, "clustering": 0.0, "degree": 0.0})
check("result clamped to <= 1.0", s_extreme <= 1.0, f"got {s_extreme:.4f}")

# ---------------------------------------------------------------------------
# Section 4 -- _compute_score uses serendipity when network present
# ---------------------------------------------------------------------------

section("4 - _compute_score formula selection")

from app.core.scorer import _compute_score

ctx = UserContext()
profile = UserProfile(user_id="test")

movie_with_semantic = Movie(
    uri="u4", title="Semantic Film",
    compatibility_score=0.8, rating=7.5, release_year="2015", genre="Drama"
)
movie_no_semantic = Movie(
    uri="u5", title="No-Semantic Film",
    compatibility_score=0.0, rating=8.0, release_year="2018", genre="Action"
)

# Base formula (no network)
score_base = _compute_score(movie_with_semantic, ctx, profile, network=None)
check("base formula computes score > 0", score_base > 0.0, f"got {score_base:.4f}")

# Serendipity formula (with network, bridge movie)
score_serendipity = _compute_score(
    Movie(uri="u6", title="Bridge", compatibility_score=0.8, rating=7.5, release_year="2015"),
    ctx, profile,
    network={"betweenness": 0.7, "clustering": 0.15, "degree": 0.2},
)
check("serendipity formula computes score > 0", score_serendipity > 0.0, f"got {score_serendipity:.4f}")

# No network -> serendipity_score stays 0.0
m_no_net = Movie(uri="u7", title="No net", compatibility_score=0.7, rating=7.0)
_compute_score(m_no_net, ctx, profile, network=None)
check("no network -> serendipity_score stays 0.0", m_no_net.serendipity_score == 0.0)

# With empty network (metrics not in Fuseki) -> serendipity_score stays 0.0
m_empty_net = Movie(uri="u8", title="Empty net", compatibility_score=0.7, rating=7.0)
_compute_score(m_empty_net, ctx, profile, network={})
check("empty network -> serendipity_score stays 0.0", m_empty_net.serendipity_score == 0.0)

# Backward compat: fallback formula when no semantic data
score_fallback = _compute_score(movie_no_semantic, ctx, profile, network=None)
check("fallback (no semantic) formula computes score > 0", score_fallback > 0.0, f"got {score_fallback:.4f}")

# ---------------------------------------------------------------------------
# Section 5 -- score_and_select populates serendipity_score
# ---------------------------------------------------------------------------

section("5 - score_and_select populates serendipity_score (Fuseki optional)")

from app.core.scorer import score_and_select, _NETWORK_CACHE

# Manually pre-populate cache so the test doesn't need Fuseki
_NETWORK_CACHE["http://example.org/pulp"] = {"betweenness": 0.6, "clustering": 0.2, "degree": 0.15}
_NETWORK_CACHE["http://example.org/kill"] = {"betweenness": 0.01, "clustering": 0.9, "degree": 0.85}

fake_candidates = [
    {
        "movie": "http://example.org/pulp",
        "title": "Pulp Fiction",
        "genreName": "Crime",
        "rating": "8.9",
        "compatibilityScore": "0.85",
        "releaseDate": "1994",
    },
    {
        "movie": "http://example.org/kill",
        "title": "Kill Bill",
        "genreName": "Action",
        "rating": "8.1",
        "compatibilityScore": "0.72",
        "releaseDate": "2003",
    },
]

results = score_and_select(fake_candidates, ctx, profile, n=5)
check("score_and_select returns movies", len(results) >= 1)

pulp = next((m for m in results if m.title == "Pulp Fiction"), None)
kill = next((m for m in results if m.title == "Kill Bill"), None)

if pulp:
    check("Pulp Fiction (bridge) has serendipity_score > 0", pulp.serendipity_score > 0.0,
          f"got {pulp.serendipity_score:.4f}")
else:
    check("Pulp Fiction present in results", False, "not returned")

if kill:
    check("Kill Bill (mainstream) has lower serendipity than Pulp Fiction",
          (kill.serendipity_score < pulp.serendipity_score) if pulp else True,
          f"kill={kill.serendipity_score:.4f} pulp={pulp.serendipity_score if pulp else 'N/A':.4f}" if pulp else "")
else:
    check("Kill Bill present in results", False, "not returned")

# ---------------------------------------------------------------------------
# Section 6 -- Fuseki live round-trip (optional)
# ---------------------------------------------------------------------------

section("6 - Fuseki live: real network scores (Phase 6 data required)")

try:
    from app.core.scorer import _bulk_fetch_network_scores, _NETWORK_CACHE as NC
    from app.core.fuseki_client import execute_select_query

    # Pick a real movie URI that should have metrics from Phase 6
    uri_rows = execute_select_query(
        f"PREFIX movie: <{_compute_serendipity.__module__}>\n"
        "PREFIX movie2: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "SELECT ?m WHERE { ?m movie2:betweennessCentrality ?b } LIMIT 1"
    )
    if not uri_rows:
        check("Phase 6 data present in Fuseki", False, "no betweennessCentrality triples found")
    else:
        test_uri = uri_rows[0].get("m", "")
        # Remove from cache to force a real fetch
        NC.pop(test_uri, None)
        _bulk_fetch_network_scores([test_uri])
        scores = NC.get(test_uri, {})
        check("bulk fetch populates cache for real URI", bool(scores), f"got {scores}")
        check("betweenness in [0, 1]", 0.0 <= scores.get("betweenness", -1) <= 1.0)
        check("clustering in [0, 1]", 0.0 <= scores.get("clustering", -1) <= 1.0)
        check("degree in [0, 1]", 0.0 <= scores.get("degree", -1) <= 1.0)
except Exception as e:
    check("Fuseki round-trip (skipped - not available)", False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in _results if ok)
total = len(_results)
if passed == total:
    print(f"  \033[92m[OK] All {total} checks passed -- Phase 10 smoke test OK\033[0m")
else:
    failed = [(label, detail) for label, ok, detail in _results if not ok]
    print(f"  \033[91m[FAIL] {passed}/{total} passed\033[0m")
    for label, detail in failed:
        print(f"         x {label}" + (f": {detail}" if detail else ""))
    sys.exit(1)
print("=" * 60)
