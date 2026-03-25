"""Regression tests for query_strategy fixes.

Fix 1 — Genre name normalisation
    Root cause: NLU (Gemini) returns genre names like "Family" or "Science Fiction"
    that differ from the exact literals stored in the movie ontology ("Children",
    "Sci-Fi"). The SPARQL FILTER would never match, returning zero results.
    Fix: _normalize_genre() maps known mismatches; applied in _genre_filter_sparql()
    and in the centrality_ranking cold-start path inside build_strategy().

Fix 2 — _run_strategy counts unique URIs, not raw rows
    Root cause: A movie with multiple genre assignments produces several SPARQL rows.
    len(rows) >= 5 could pass with 30 rows for a single movie, wrongly signalling
    a successful strategy. Fixed in chat_use_case and recommendation_use_case by
    counting distinct ?movie URIs via _unique_movie_count().
"""
from __future__ import annotations

import pytest

from app.core.query_strategy import (
    _normalize_genre,
    _genre_filter_sparql,
    build_strategy,
)
from app.domain.entities.recommendation_models import UserContext, UserProfile


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _cold_profile() -> UserProfile:
    return UserProfile(user_id="u1", genre_weights={}, is_cold_start=True)


def _warm_profile() -> UserProfile:
    return UserProfile(user_id="u1", genre_weights={}, is_cold_start=False)


def _ctx(**kwargs) -> UserContext:
    return UserContext(**kwargs)


# ===========================================================================
# Fix 1 — Genre normalisation: _normalize_genre()
# ===========================================================================

class TestNormalizeGenre:
    """_normalize_genre must map NLU names to exact ontology literals."""

    @pytest.mark.parametrize("nlu_name, expected", [
        ("Family",          "Children"),
        ("family",          "Children"),
        ("FAMILY",          "Children"),
        ("Science Fiction", "Sci-Fi"),
        ("science fiction", "Sci-Fi"),
        ("Sci Fi",          "Sci-Fi"),
        ("sci fi",          "Sci-Fi"),
        ("scifi",           "Sci-Fi"),
        ("SciFi",           "Sci-Fi"),
        ("Kids",            "Children"),
        ("kids",            "Children"),
        ("Children's",      "Children"),
        ("children's",      "Children"),
        # Pass-through: unknown names stay as-is
        ("Action",          "Action"),
        ("Drama",           "Drama"),
        ("Thriller",        "Thriller"),
        ("",                ""),
    ])
    def test_normalise(self, nlu_name: str, expected: str):
        assert _normalize_genre(nlu_name) == expected

    def test_leading_trailing_whitespace_stripped(self):
        assert _normalize_genre("  family  ") == "Children"

    def test_unknown_genre_returned_unchanged(self):
        assert _normalize_genre("Horror") == "Horror"


# ===========================================================================
# Fix 1 — Genre filter SPARQL uses normalised names
# ===========================================================================

class TestGenreFilterSparql:
    """_genre_filter_sparql must produce SPARQL with normalised genre literals."""

    def test_family_normalised_to_children_in_filter(self):
        sparql = _genre_filter_sparql(
            genres=["Family"],
            excluded=set(),
            hard_kid_filter=False,
            runtime_max=None,
        )
        assert '"Children"' in sparql
        assert '"Family"' not in sparql

    def test_science_fiction_normalised_to_sci_fi(self):
        sparql = _genre_filter_sparql(
            genres=["Science Fiction"],
            excluded=set(),
            hard_kid_filter=False,
            runtime_max=None,
        )
        assert '"Sci-Fi"' in sparql
        assert '"Science Fiction"' not in sparql

    def test_mixed_genres_all_normalised(self):
        sparql = _genre_filter_sparql(
            genres=["Family", "Action", "Science Fiction"],
            excluded=set(),
            hard_kid_filter=False,
            runtime_max=None,
        )
        assert '"Children"' in sparql
        assert '"Action"' in sparql
        assert '"Sci-Fi"' in sparql
        assert '"Family"' not in sparql
        assert '"Science Fiction"' not in sparql

    def test_already_correct_genre_unchanged(self):
        sparql = _genre_filter_sparql(
            genres=["Drama"],
            excluded=set(),
            hard_kid_filter=False,
            runtime_max=None,
        )
        assert '"Drama"' in sparql

    def test_empty_genres_produces_no_filter_clause(self):
        sparql = _genre_filter_sparql(
            genres=[],
            excluded=set(),
            hard_kid_filter=False,
            runtime_max=None,
        )
        assert "FILTER(?genreName IN" not in sparql


# ===========================================================================
# Fix 1 — build_strategy normalises genres in genre_filter and centrality
# ===========================================================================

class TestBuildStrategyGenreNormalisation:
    """build_strategy must normalise genre names when building all genre-based strategies."""

    def test_warm_user_genre_filter_uses_normalised_name(self):
        ctx = _ctx(genres=["Family"], session_id="s1")
        attempts = build_strategy(ctx, _warm_profile())
        genre_filter_sparqls = [sparql for name, sparql in attempts if name == "genre_filter"]
        assert genre_filter_sparqls, "genre_filter strategy should be present"
        assert '"Children"' in genre_filter_sparqls[0]
        assert '"Family"' not in genre_filter_sparqls[0]

    def test_cold_start_centrality_uses_normalised_genre(self):
        ctx = _ctx(genres=["Science Fiction"], session_id="s1")
        attempts = build_strategy(ctx, _cold_profile())
        centrality_sparqls = [sparql for name, sparql in attempts if name == "centrality_ranking"]
        assert centrality_sparqls, "centrality_ranking strategy should be present for cold-start with genre"
        assert '"Sci-Fi"' in centrality_sparqls[0]
        assert '"Science Fiction"' not in centrality_sparqls[0]

    def test_no_signal_cold_start_skips_genre_filter(self):
        ctx = _ctx(session_id="s1")  # no genres, no mood, no companion
        attempts = build_strategy(ctx, _cold_profile())
        names = [name for name, _ in attempts]
        assert "genre_filter" not in names
        assert "centrality_ranking" in names  # broad cold-start path

    def test_ontology_full_includes_genre_filter_when_genres_present(self):
        """ontology_full strategy must include a genre FILTER when ctx.genres is set."""
        ctx = _ctx(
            mood="happy",
            companion="family",
            genres=["Animation"],
            session_id="s1",
        )
        attempts = build_strategy(ctx, _warm_profile())
        ontology_full = next(
            (sparql for name, sparql in attempts if name == "ontology_full"), None
        )
        assert ontology_full is not None, "ontology_full strategy not found"
        assert '"Animation"' in ontology_full, (
            "ontology_full SPARQL must filter by genre when genres are specified"
        )
        assert "FILTER(?genreName IN" in ontology_full

    def test_ontology_full_no_genre_filter_when_no_genres(self):
        """ontology_full must NOT add genre FILTER when ctx.genres is empty."""
        ctx = _ctx(mood="happy", companion="friends", session_id="s1")
        attempts = build_strategy(ctx, _warm_profile())
        ontology_full = next(
            (sparql for name, sparql in attempts if name == "ontology_full"), None
        )
        assert ontology_full is not None
        assert "FILTER(?genreName IN" not in ontology_full

    def test_strategies_are_deduplicated(self):
        """No two entries in the returned list should have identical SPARQL."""
        ctx = _ctx(mood="happy", companion="friends", genres=["Action"], session_id="s1")
        attempts = build_strategy(ctx, _warm_profile())
        sparqls = [sparql for _, sparql in attempts]
        assert len(sparqls) == len(set(sparqls)), "Duplicate SPARQL strings found in strategy list"
