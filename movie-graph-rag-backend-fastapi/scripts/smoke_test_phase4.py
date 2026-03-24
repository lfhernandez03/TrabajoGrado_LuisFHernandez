"""Smoke test — Phase 4: Connection Explorer + REST endpoints.

Runs without Fuseki or Gemini. Uses monkeypatching to stub
execute_select_query and tests every layer from dataclass to
Pydantic schema to API router registration.

Usage (from repo root):
    cd movie-graph-rag-backend-fastapi
    python scripts/smoke_test_phase4.py
"""
from __future__ import annotations

import sys
import traceback
from typing import Any
from unittest.mock import patch

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
        results.append((name, True, ""))
        print(f"  {PASS}  {name}")
    except Exception as exc:
        tb = traceback.format_exc()
        results.append((name, False, tb))
        print(f"  {FAIL}  {name}\n        {exc}")


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


# ===========================================================================
# 1. Imports
# ===========================================================================

section("1 · Imports")


def _import_dataclasses():
    from app.core.connection_explorer import (
        ConnectionExplorer,
        ConnectionHop,
        ConnectionPath,
        NetworkEdge,
        NetworkGraph,
        NetworkNode,
        _esc,
    )


def _import_schemas():
    from app.api.schemas.connections import (
        CentralityResponse,
        ConnectionHopResponse,
        ConnectionPathResponse,
        NetworkEdgeResponse,
        NetworkGraphResponse,
        NetworkNodeResponse,
    )


def _import_endpoint():
    from app.api.v1.endpoints.connections import router


def _import_router_registered():
    from app.api.v1.router import api_router
    routes = [r.path for r in api_router.routes]
    # The connections prefix must appear somewhere after include_router
    # FastAPI merges routes, so we check the individual endpoint module
    from app.api.v1.endpoints.connections import router as conn_router
    assert conn_router.prefix == "/movies/connections", (
        f"unexpected prefix: {conn_router.prefix!r}"
    )


check("connection_explorer module imports", _import_dataclasses)
check("connections schemas import", _import_schemas)
check("connections endpoint module imports", _import_endpoint)
check("connections router has correct prefix", _import_router_registered)


# ===========================================================================
# 2. Dataclass correctness
# ===========================================================================

section("2 · Dataclass correctness")


def _hop_dataclass():
    from app.core.connection_explorer import ConnectionHop
    h = ConnectionHop(from_title="A", to_title="B", relation="same_genre")
    assert h.from_title == "A"
    assert h.relation == "same_genre"


def _path_length_property():
    from app.core.connection_explorer import ConnectionHop, ConnectionPath
    p = ConnectionPath(source="A", target="B", hops=[], found=False)
    assert p.length == 0
    p.hops.append(ConnectionHop("A", "B", "same_director"))
    assert p.length == 1


def _network_graph_defaults():
    from app.core.connection_explorer import NetworkGraph
    g = NetworkGraph(center_title="Inception")
    assert g.center_title == "Inception"
    assert g.nodes == []
    assert g.edges == []


def _esc_escapes():
    from app.core.connection_explorer import _esc
    assert _esc('hello "world"') == 'hello \\"world\\"'
    assert _esc("line\nnewline") == "line newline"
    assert _esc("back\\slash") == "back\\\\slash"


check("ConnectionHop fields", _hop_dataclass)
check("ConnectionPath.length property", _path_length_property)
check("NetworkGraph default factory fields", _network_graph_defaults)
check("_esc escapes quotes/newlines/backslashes", _esc_escapes)


# ===========================================================================
# 3. Pydantic schema serialisation
# ===========================================================================

section("3 · Pydantic schema serialisation")


def _connection_hop_response():
    from app.api.schemas.connections import ConnectionHopResponse
    obj = ConnectionHopResponse(from_title="X", to_title="Y", relation="same_genre")
    d = obj.model_dump()
    assert d == {"from_title": "X", "to_title": "Y", "relation": "same_genre"}


def _path_response_empty_path():
    from app.api.schemas.connections import ConnectionPathResponse
    obj = ConnectionPathResponse(
        source="The Matrix",
        target="Inception",
        found=False,
        hops=[],
        length=0,
    )
    assert obj.found is False
    assert obj.hops == []


def _network_node_optional_fields():
    from app.api.schemas.connections import NetworkNodeResponse
    # All optional fields absent -> default None
    obj = NetworkNodeResponse(uri="http://example.org/m1", title="Movie 1")
    assert obj.genre is None
    assert obj.rating is None
    assert obj.poster_url is None


def _network_graph_response_counts():
    from app.api.schemas.connections import (
        NetworkEdgeResponse,
        NetworkGraphResponse,
        NetworkNodeResponse,
    )
    nodes = [NetworkNodeResponse(uri="u1", title="T1")]
    edges = [NetworkEdgeResponse(source_uri="u1", target_uri="u2", relation="same_genre")]
    g = NetworkGraphResponse(
        center_title="T1",
        nodes=nodes,
        edges=edges,
        node_count=1,
        edge_count=1,
    )
    assert g.node_count == 1
    assert g.edge_count == 1


def _centrality_response_empty():
    from app.api.schemas.connections import CentralityResponse
    obj = CentralityResponse(genre=None, movies=[], total=0)
    assert obj.genre is None
    assert obj.total == 0


check("ConnectionHopResponse serialisation", _connection_hop_response)
check("ConnectionPathResponse empty path", _path_response_empty_path)
check("NetworkNodeResponse optional fields default None", _network_node_optional_fields)
check("NetworkGraphResponse node/edge counts", _network_graph_response_counts)
check("CentralityResponse empty genre", _centrality_response_empty)


# ===========================================================================
# 4. ConnectionExplorer — mocked Fuseki
# ===========================================================================

section("4 · ConnectionExplorer (Fuseki mocked)")

# Shared fake movie rows
_FAKE_INFO_A: list[dict] = [{
    "movie": "http://ont/movieA",
    "title": "Movie A",
    "genreName": "Action",
    "directorUri": "http://ont/dir1",
}]
_FAKE_INFO_B: list[dict] = [{
    "movie": "http://ont/movieB",
    "title": "Movie B",
    "genreName": "Action",
    "directorUri": "http://ont/dir1",
}]
_FAKE_NEIGHBORS: list[dict] = [{
    "movie": "http://ont/movieB",
    "title": "Movie B",
    "genreName": "Action",
    "rating": "8.0",
    "posterUrl": None,
}]
_FAKE_CENTRALITY: list[dict] = [
    {
        "movie": f"http://ont/movie{i}",
        "title": f"Movie {i}",
        "genreName": "Drama",
        "runtime": "120",
        "rating": str(9.0 - i * 0.1),
        "posterUrl": None,
        "releaseDate": "2020-01-01",
        "compatibilityScore": "0.9",
        "moodMatchScore": "0.8",
        "socialMatchScore": "0.7",
        "energyMatchScore": "0.6",
        "timeMatchScore": "0.5",
        "kidFriendly": None,
    }
    for i in range(5)
]


def _side_effect_path(query: str) -> list[dict]:
    """Return different data depending on which SPARQL query is called."""
    if "Movie A" in query or 'LCASE("movie a")' in query.lower():
        return _FAKE_INFO_A
    if "Movie B" in query or 'LCASE("movie b")' in query.lower():
        return _FAKE_INFO_B
    if "hasDirector" in query:
        return _FAKE_NEIGHBORS
    if "hasMainGenre" in query and "Action" in query:
        return _FAKE_NEIGHBORS
    return []


def _test_find_path_same_movie():
    """find_path(X, X) -> found=True, 0 hops."""
    with patch("app.core.connection_explorer.execute_select_query",
               side_effect=lambda q: _FAKE_INFO_A):
        from app.core.connection_explorer import ConnectionExplorer
        ex = ConnectionExplorer()
        result = ex.find_path("Movie A", "Movie A")
        assert result.found is True
        assert result.length == 0


def _test_find_path_not_found_missing_movie():
    """find_path returns found=False when source movie not in Fuseki."""
    with patch("app.core.connection_explorer.execute_select_query",
               return_value=[]):
        from app.core.connection_explorer import ConnectionExplorer
        ex = ConnectionExplorer()
        result = ex.find_path("Ghost Movie", "Another Ghost")
        assert result.found is False
        assert result.hops == []


def _test_find_path_one_hop_director():
    """find_path finds 1-hop via same director."""
    call_count = {"n": 0}

    def mock_query(q: str) -> list[dict]:
        call_count["n"] += 1
        # First two calls: _get_movie_info for A and B
        if call_count["n"] == 1:
            return _FAKE_INFO_A
        if call_count["n"] == 2:
            return _FAKE_INFO_B
        # Subsequent: director neighbours include B
        return _FAKE_NEIGHBORS

    with patch("app.core.connection_explorer.execute_select_query", side_effect=mock_query):
        from app.core.connection_explorer import ConnectionExplorer
        ex = ConnectionExplorer()
        result = ex.find_path("Movie A", "Movie B")
        assert result.found is True
        assert result.length >= 1


def _test_get_neighborhood_empty_when_no_movie():
    with patch("app.core.connection_explorer.execute_select_query",
               return_value=[]):
        from app.core.connection_explorer import ConnectionExplorer
        ex = ConnectionExplorer()
        g = ex.get_neighborhood("Nonexistent Movie", depth=1)
        assert g.center_title == "Nonexistent Movie"
        assert g.nodes == []
        assert g.edges == []


def _test_get_neighborhood_returns_nodes():
    call_count = {"n": 0}

    def mock_query(q: str) -> list[dict]:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FAKE_INFO_A  # _get_movie_info
        return _FAKE_NEIGHBORS   # genre/director expansions

    with patch("app.core.connection_explorer.execute_select_query", side_effect=mock_query):
        from app.core.connection_explorer import ConnectionExplorer
        ex = ConnectionExplorer()
        g = ex.get_neighborhood("Movie A", depth=1)
        # Center node always added
        assert len(g.nodes) >= 1
        assert g.nodes[0].title in ("Movie A", "Movie B")


def _test_get_centrality_ranking_rows():
    with patch("app.core.connection_explorer.execute_select_query",
               return_value=_FAKE_CENTRALITY):
        from app.core.connection_explorer import ConnectionExplorer
        ex = ConnectionExplorer()
        rows = ex.get_centrality_ranking(genre=None, limit=5)
        assert len(rows) == 5
        assert rows[0]["title"] == "Movie 0"


def _test_get_centrality_ranking_empty_on_fuseki_error():
    with patch("app.core.connection_explorer.execute_select_query",
               side_effect=Exception("Fuseki down")):
        from app.core.connection_explorer import ConnectionExplorer
        ex = ConnectionExplorer()
        rows = ex.get_centrality_ranking()
        assert rows == []


check("find_path same movie -> found=True 0 hops", _test_find_path_same_movie)
check("find_path missing movie -> found=False", _test_find_path_not_found_missing_movie)
check("find_path 1 hop via director", _test_find_path_one_hop_director)
check("get_neighborhood no movie -> empty graph", _test_get_neighborhood_empty_when_no_movie)
check("get_neighborhood returns center + neighbour nodes", _test_get_neighborhood_returns_nodes)
check("get_centrality_ranking returns rows from Fuseki", _test_get_centrality_ranking_rows)
check("get_centrality_ranking returns [] on Fuseki error", _test_get_centrality_ranking_empty_on_fuseki_error)


# ===========================================================================
# 5. Endpoint helpers (_movie_to_response)
# ===========================================================================

section("5 · Endpoint helpers")


def _test_movie_to_response_mapping():
    from app.core.connection_explorer import ConnectionExplorer
    from app.domain.entities.recommendation_models import Movie

    movie = Movie(
        uri="http://ont/m1",
        title="Inception",
        genre="Sci-Fi",
        runtime=148,
        rating=8.8,
        poster_url="http://img.example/poster.jpg",
        release_year="2010",
        compatibility_score=0.92,
        mood_match_score=0.85,
        social_match_score=0.70,
        energy_match_score=0.75,
        time_match_score=0.80,
        kid_friendly=False,
    )

    # Import the private helper
    from app.api.v1.endpoints.connections import _movie_to_response
    resp = _movie_to_response(movie)

    assert resp.title == "Inception"
    assert resp.posterUrl == "http://img.example/poster.jpg"
    assert resp.runtime == 148
    assert resp.genreName == "Sci-Fi"
    assert resp.releaseDate == "2010"
    assert abs(resp.averageRating - 8.8) < 0.001
    assert abs(resp.compatibilityScore - 0.92) < 0.001
    assert resp.kidFriendly is False


def _test_movie_to_response_none_fields():
    """Movie with all optional fields None maps gracefully."""
    from app.domain.entities.recommendation_models import Movie
    from app.api.v1.endpoints.connections import _movie_to_response

    movie = Movie(uri="http://ont/m0", title="Unknown")
    resp = _movie_to_response(movie)
    assert resp.title == "Unknown"
    assert resp.posterUrl is None
    assert resp.averageRating is None


check("_movie_to_response maps all fields", _test_movie_to_response_mapping)
check("_movie_to_response handles None optional fields", _test_movie_to_response_none_fields)


# ===========================================================================
# 6. Movie.from_fuseki_row — centrality integration
# ===========================================================================

section("6 · Movie.from_fuseki_row with centrality data")


def _test_from_fuseki_row_full():
    from app.domain.entities.recommendation_models import Movie

    row = {
        "movie": "http://ont/m1",
        "title": "The Dark Knight",
        "genreName": "Action",
        "runtime": "152",
        "rating": "9.0",
        "posterUrl": "http://img.example/tdk.jpg",
        "releaseDate": "2008-07-18",
        "compatibilityScore": "0.95",
        "moodMatchScore": "0.88",
        "socialMatchScore": "0.72",
        "energyMatchScore": "0.80",
        "timeMatchScore": "0.65",
        "kidFriendly": None,
    }
    m = Movie.from_fuseki_row(row)
    assert m.title == "The Dark Knight"
    assert m.runtime == 152
    assert abs(m.rating - 9.0) < 0.001
    assert m.release_year == "2008"
    assert abs(m.compatibility_score - 0.95) < 0.001
    assert abs(m.mood_match_score - 0.88) < 0.001
    assert m.kid_friendly is None


def _test_from_fuseki_row_minimal():
    """Row with only required fields doesn't crash."""
    from app.domain.entities.recommendation_models import Movie
    m = Movie.from_fuseki_row({"movie": "http://ont/m0", "title": "Minimal"})
    assert m.title == "Minimal"
    assert m.rating is None
    assert m.compatibility_score == 0.0


check("Movie.from_fuseki_row full centrality row", _test_from_fuseki_row_full)
check("Movie.from_fuseki_row minimal row (no crash)", _test_from_fuseki_row_minimal)


# ===========================================================================
# 7. Router registration sanity
# ===========================================================================

section("7 · Router registration in api_router")


def _test_connections_routes_in_api_router():
    from app.api.v1.router import api_router
    # Collect all paths from all mounted sub-routers
    all_paths = set()
    for route in api_router.routes:
        all_paths.add(getattr(route, "path", ""))
    expected = {
        "/movies/connections/path",
        "/movies/connections/neighborhood",
        "/movies/connections/centrality",
    }
    missing = expected - all_paths
    assert not missing, f"Missing routes in api_router: {missing}"


check("api_router exposes /path, /neighborhood, /centrality", _test_connections_routes_in_api_router)


# ===========================================================================
# Summary
# ===========================================================================

print(f"\n{'=' * 60}")
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed

if failed == 0:
    print(f"  [OK] All {total} checks passed -- Phase 4 smoke test OK")
else:
    print(f"  [FAIL] {failed}/{total} checks FAILED")
    print("\nFailed details:")
    for name, ok, tb in results:
        if not ok:
            print(f"\n  * {name}\n{tb}")

print(f"{'=' * 60}\n")
sys.exit(0 if failed == 0 else 1)
