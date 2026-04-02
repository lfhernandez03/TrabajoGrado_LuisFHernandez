"""Phase 11 smoke test -- Topological User Profile.

Verifies:
  1. Pydantic schemas import and serialise correctly.
  2. _entropy_index formula is correct.
  3. _compute_temporal_trend logic.
  4. ProfileService.get_topological_profile with mocked favorites.
  5. Endpoint imports and route present.
  6. Live Fuseki round-trip with real favorites (requires Phase 6 data).

Run with Fuseki active:

    python scripts/smoke_test_phase11.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

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
# Section 1 -- Schema
# ---------------------------------------------------------------------------

section("1 - Schema imports and serialisation")

from app.api.schemas.topology_profile import (
    ClusterWeight,
    TopologicalProfileResponse,
    UnexploredCluster,
)

check("topology_profile schemas import", True)

cw = ClusterWeight(clusterId="14", label="Sci-Fi Epico", weight=0.6, moviesSeen=6)
uc = UnexploredCluster(clusterId="7", label="Drama Historico", distanceToDominant=1)
resp = TopologicalProfileResponse(
    userId="user1",
    explorationIndex=0.35,
    userType="equilibrado",
    dominantClusters=[cw],
    unexploredAdjacent=[uc],
    temporalTrend="stable",
    trendExplanation="Patron estable.",
    totalFavorites=10,
    clusteredFavorites=8,
)
d = resp.model_dump()

check("TopologicalProfileResponse serialises", "explorationIndex" in d)
check("explorationIndex value correct", d["explorationIndex"] == 0.35)
check("userType correct", d["userType"] == "equilibrado")
check("dominantClusters non-empty", len(d["dominantClusters"]) == 1)
check("ClusterWeight.weight serialises", d["dominantClusters"][0]["weight"] == 0.6)
check("UnexploredCluster serialises", d["unexploredAdjacent"][0]["clusterId"] == "7")
check("clusteredFavorites serialises", d["clusteredFavorites"] == 8)

# ---------------------------------------------------------------------------
# Section 2 -- _entropy_index formula
# ---------------------------------------------------------------------------

section("2 - _entropy_index formula")

from app.core.profile_service import _entropy_index

# Perfect specialist: all weight on one cluster
check("specialist entropy = 0.0", _entropy_index([1.0]) == 0.0)

# Perfect explorer: uniform distribution over 4 clusters
uniform = [0.25, 0.25, 0.25, 0.25]
check("explorer entropy = 1.0", _entropy_index(uniform) == 1.0)

# Intermediate
mixed = [0.6, 0.3, 0.1]
idx = _entropy_index(mixed)
check("mixed entropy in (0, 1)", 0.0 < idx < 1.0, f"got {idx:.4f}")

# Empty list -> 0.5 (neutral)
check("empty weights -> 0.5", _entropy_index([]) == 0.5)

# Zero values are ignored
check("zero weights ignored", _entropy_index([1.0, 0.0, 0.0]) == 0.0)

# ---------------------------------------------------------------------------
# Section 3 -- _compute_temporal_trend
# ---------------------------------------------------------------------------

section("3 - _compute_temporal_trend logic")

from app.core.profile_service import _compute_temporal_trend
from app.domain.entities.favorite_movie import FavoriteMovie

now = datetime.utcnow()

def _make_fav(uri: str, days_ago: int) -> FavoriteMovie:
    return FavoriteMovie(uri=uri, title=uri, addedAt=now - timedelta(days=days_ago))

# Specializing: older favorites spread across 4 clusters, recent all in one
cluster_map_spec = {
    "a": "1", "b": "2", "c": "3", "d": "4",   # older (60-30 days ago)
    "e": "1", "f": "1", "g": "1", "h": "1",   # recent (10-1 days ago)
}
favs_spec = [
    _make_fav("a", 60), _make_fav("b", 50), _make_fav("c", 40), _make_fav("d", 30),
    _make_fav("e", 10), _make_fav("f", 8),  _make_fav("g", 5),  _make_fav("h", 1),
]
trend_s, _ = _compute_temporal_trend(favs_spec, cluster_map_spec, 8)
check("specializing trend detected", trend_s == "specializing", f"got '{trend_s}'")

# Diversifying: recent favorites spread across more clusters than older
cluster_map_div = {
    "a": "1", "b": "1", "c": "1", "d": "1",   # older — all cluster 1
    "e": "1", "f": "2", "g": "3", "h": "4",   # recent — spread out
}
favs_div = [
    _make_fav("a", 60), _make_fav("b", 50), _make_fav("c", 40), _make_fav("d", 30),
    _make_fav("e", 10), _make_fav("f", 8),  _make_fav("g", 5),  _make_fav("h", 1),
]
trend_d, _ = _compute_temporal_trend(favs_div, cluster_map_div, 8)
check("diversifying trend detected", trend_d == "diversifying", f"got '{trend_d}'")

# Insufficient data -> stable
check("insufficient data -> stable",
      _compute_temporal_trend(favs_spec[:2], cluster_map_spec, 2)[0] == "stable")

# ---------------------------------------------------------------------------
# Section 4 -- ProfileService.get_topological_profile (mocked cache)
# ---------------------------------------------------------------------------

section("4 - ProfileService.get_topological_profile with injected cache")

from app.core.profile_service import ProfileService
from app.core.fuseki_client import execute_select_query

# Use real movie URIs from Fuseki that have cluster assignments
try:
    uri_rows = execute_select_query(
        "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "SELECT DISTINCT ?m ?title WHERE { ?m movie:belongsToCluster ?c ; movie:hasTitle ?title } LIMIT 12"
    )
    real_uris = [(r.get("m", ""), r.get("title", "")) for r in uri_rows if r.get("m")]
    if not real_uris:
        raise RuntimeError("No clustered movies found in Fuseki")

    fake_favs = [
        FavoriteMovie(
            uri=uri,
            title=title,
            addedAt=now - timedelta(days=i * 5),
        )
        for i, (uri, title) in enumerate(real_uris)
    ]

    ps = ProfileService()
    result = ps.get_topological_profile("test_user", fake_favs)

    check("returns TopologicalProfileResponse", isinstance(result, TopologicalProfileResponse))
    check("userId correct", result.userId == "test_user")
    check("totalFavorites correct", result.totalFavorites == len(fake_favs))
    check("clusteredFavorites > 0", result.clusteredFavorites > 0,
          f"got {result.clusteredFavorites}")
    check("explorationIndex in [0, 1]", 0.0 <= result.explorationIndex <= 1.0,
          f"got {result.explorationIndex}")
    check("userType valid", result.userType in ("especialista", "equilibrado", "explorador"),
          f"got '{result.userType}'")
    check("dominantClusters non-empty", len(result.dominantClusters) > 0)
    check("dominant cluster weights each in [0, 1]",
          all(0.0 <= c.weight <= 1.0 for c in result.dominantClusters),
          f"weights={[c.weight for c in result.dominantClusters]}")
    check("temporalTrend valid",
          result.temporalTrend in ("specializing", "diversifying", "stable"),
          f"got '{result.temporalTrend}'")

    # Cold start: empty favorites
    empty_result = ps.get_topological_profile("empty_user", [])
    check("empty favorites: explorationIndex = 0.5", empty_result.explorationIndex == 0.5)
    check("empty favorites: totalFavorites = 0", empty_result.totalFavorites == 0)
    check("empty favorites: dominantClusters empty", len(empty_result.dominantClusters) == 0)

except Exception as e:
    check("Fuseki available for profile test", False, str(e))

# ---------------------------------------------------------------------------
# Section 5 -- Endpoint imports and route
# ---------------------------------------------------------------------------

section("5 - Endpoint imports and route")

try:
    from app.api.v1.endpoints.users import router, get_my_topology
    check("users endpoint imports", True)
    routes = {r.path for r in router.routes}  # type: ignore[attr-defined]
    check("GET /users/me/topology route exists", "/users/me/topology" in routes)
    check("get_my_topology callable", callable(get_my_topology))
except ImportError as e:
    check("users endpoint imports", False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in _results if ok)
total = len(_results)
if passed == total:
    print(f"  \033[92m[OK] All {total} checks passed -- Phase 11 smoke test OK\033[0m")
else:
    failed = [(label, detail) for label, ok, detail in _results if not ok]
    print(f"  \033[91m[FAIL] {passed}/{total} passed\033[0m")
    for label, detail in failed:
        print(f"         x {label}" + (f": {detail}" if detail else ""))
    sys.exit(1)
print("=" * 60)
