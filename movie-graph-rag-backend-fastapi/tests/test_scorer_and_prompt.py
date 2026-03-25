"""Regression tests for two bugs fixed in this session.

Bug 1 — Duplicate movies in recommendations
    Root cause: SPARQL returns the same movie URI multiple times when a film
    has several genre assignments (each ?genreName produces a distinct row).
    SELECT DISTINCT does not collapse them because ?genreName differs.
    Fix: score_and_select() now deduplicates by URI before scoring.

Bug 2 — Inaccurate LLM explanation
    Root cause: _build_prompt() read moodMatchScore / socialMatchScore from
    movie["semanticScores"], but those keys live at the top level of
    to_response_dict() (not nested).  Gemini never received mood/social hints.
    Fix: read individual match scores from top-level fields; keep
    overallCompatibility from semanticScores.
"""
from __future__ import annotations

from app.core.scorer import score_and_select
from app.domain.entities.recommendation_models import Movie, UserContext, UserProfile
from app.adapters.llm.gemini_recommendation_llm_adapter import GeminiRecommendationLlmAdapter


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _profile() -> UserProfile:
    return UserProfile(user_id="u1", genre_weights={}, is_cold_start=False)


def _ctx() -> UserContext:
    return UserContext(mood="happy", raw_query="test")


def _row(uri: str, title: str, genre: str) -> dict:
    """Minimal Fuseki row dict — only fields Movie.from_fuseki_row reads."""
    return {
        "movie": uri,
        "title": title,
        "genreName": genre,
        "runtime": "120",
        "rating": "7.5",
        "posterUrl": None,
        "releaseDate": "2020-01-01",
        "compatibilityScore": "0.8",
        "moodMatchScore": "0.85",
        "socialMatchScore": "0.7",
        "energyMatchScore": "0.75",
        "timeMatchScore": "0.6",
        "kidFriendly": "false",
    }


# ===========================================================================
# Bug 1 — Deduplication by URI
# ===========================================================================

class TestScorerDeduplication:
    """score_and_select must never return the same movie URI more than once."""

    def test_duplicate_rows_produce_single_movie(self):
        """Two rows with the same URI (different genres) → one movie in result."""
        rows = [
            _row("http://ont/m1", "Inception", "Sci-Fi"),
            _row("http://ont/m1", "Inception", "Action"),  # same URI, different genre
        ]
        movies = score_and_select(rows, _ctx(), _profile(), n=5)
        uris = [m.uri for m in movies]
        assert len(uris) == len(set(uris)), "Duplicate URIs found in result"
        assert len(movies) == 1

    def test_five_same_uri_rows_become_one_movie(self):
        """Five rows for the same URI → exactly one movie returned."""
        rows = [_row("http://ont/m1", "Inception", f"Genre{i}") for i in range(5)]
        movies = score_and_select(rows, _ctx(), _profile(), n=5)
        assert len(movies) == 1
        assert movies[0].uri == "http://ont/m1"

    def test_mixed_duplicates_and_uniques(self):
        """3 unique URIs + 2 duplicate rows → 3 movies, no duplicate URIs."""
        rows = [
            _row("http://ont/m1", "Movie A", "Action"),
            _row("http://ont/m2", "Movie B", "Drama"),
            _row("http://ont/m1", "Movie A", "Thriller"),  # duplicate of m1
            _row("http://ont/m3", "Movie C", "Comedy"),
            _row("http://ont/m2", "Movie B", "Romance"),   # duplicate of m2
        ]
        movies = score_and_select(rows, _ctx(), _profile(), n=5)
        uris = [m.uri for m in movies]
        assert len(uris) == len(set(uris))
        assert len(movies) == 3

    def test_no_duplicates_in_normal_case(self):
        """Five rows with distinct URIs → all five returned (below MMR threshold)."""
        rows = [
            _row(f"http://ont/m{i}", f"Movie {i}", "Drama")
            for i in range(5)
        ]
        movies = score_and_select(rows, _ctx(), _profile(), n=5)
        uris = [m.uri for m in movies]
        assert len(uris) == len(set(uris))
        assert len(movies) == 5

    def test_first_occurrence_wins(self):
        """When a URI appears twice, the first row (Fuseki ORDER BY rank) is kept."""
        rows = [
            {**_row("http://ont/m1", "Inception", "Sci-Fi"), "rating": "9.0"},  # first
            {**_row("http://ont/m1", "Inception", "Action"), "rating": "7.0"},  # duplicate
        ]
        movies = score_and_select(rows, _ctx(), _profile(), n=5)
        assert len(movies) == 1
        assert movies[0].rating == 9.0


# ===========================================================================
# Bug 2 — LLM explanation prompt uses correct score fields
# ===========================================================================

class TestBuildPromptScoreKeys:
    """_build_prompt must surface moodMatchScore and socialMatchScore from the
    top-level movie dict fields, not from the nested semanticScores dict."""

    def _make_movie_dict(
        self,
        mood: float | None = 0.9,
        social: float | None = 0.8,
        energy: float | None = 0.7,
        overall: float | None = 0.85,
    ) -> dict:
        """Matches the structure of Movie.to_response_dict()."""
        return {
            "title": "Inception",
            "posterUrl": None,
            "runtime": 148,
            "genreName": "Sci-Fi",
            "releaseDate": "2010",
            "averageRating": 8.8,
            "compatibilityScore": overall or 0.0,
            "moodMatchScore": mood,         # top-level
            "socialMatchScore": social,     # top-level
            "energyMatchScore": energy,     # top-level
            "timeMatchScore": 0.6,
            "semanticScores": {"overallCompatibility": overall} if overall else {},
            "kidFriendly": False,
        }

    def test_mood_hint_present_in_prompt(self):
        adapter = GeminiRecommendationLlmAdapter()
        movie = self._make_movie_dict(mood=0.92)
        prompt = adapter._build_prompt(
            query="happy films",
            context_summary="mood=happy",
            movies_with_scores=[movie],
        )
        assert "afinidad_emocional" in prompt, (
            "moodMatchScore must appear in prompt as 'afinidad_emocional'"
        )
        assert "0.92" in prompt

    def test_social_hint_present_in_prompt(self):
        adapter = GeminiRecommendationLlmAdapter()
        movie = self._make_movie_dict(social=0.75)
        prompt = adapter._build_prompt(
            query="with friends",
            context_summary="companion=friends",
            movies_with_scores=[movie],
        )
        assert "afinidad_social" in prompt, (
            "socialMatchScore must appear in prompt as 'afinidad_social'"
        )
        assert "0.75" in prompt

    def test_energy_hint_present_in_prompt(self):
        adapter = GeminiRecommendationLlmAdapter()
        movie = self._make_movie_dict(energy=0.65)
        prompt = adapter._build_prompt(
            query="energetic movie",
            context_summary="energy=high",
            movies_with_scores=[movie],
        )
        assert "afinidad_energia" in prompt
        assert "0.65" in prompt

    def test_overall_compatibility_present_in_prompt(self):
        adapter = GeminiRecommendationLlmAdapter()
        movie = self._make_movie_dict(overall=0.88)
        prompt = adapter._build_prompt(
            query="test",
            context_summary="general",
            movies_with_scores=[movie],
        )
        assert "compatibilidad_general" in prompt
        assert "0.88" in prompt

    def test_none_scores_not_included(self):
        adapter = GeminiRecommendationLlmAdapter()
        movie = self._make_movie_dict(mood=None, social=None, energy=None, overall=None)
        prompt = adapter._build_prompt(
            query="test",
            context_summary="general",
            movies_with_scores=[movie],
        )
        # None values must not produce hint lines
        assert "afinidad_emocional" not in prompt
        assert "afinidad_social" not in prompt
        assert "afinidad_energia" not in prompt
        assert "compatibilidad_general" not in prompt

    def test_all_hints_included_for_full_movie(self):
        adapter = GeminiRecommendationLlmAdapter()
        movie = self._make_movie_dict(mood=0.9, social=0.8, energy=0.7, overall=0.85)
        prompt = adapter._build_prompt(
            query="family movie",
            context_summary="mood=happy, companion=family",
            movies_with_scores=[movie],
        )
        assert "afinidad_emocional" in prompt
        assert "afinidad_social" in prompt
        assert "afinidad_energia" in prompt
        assert "compatibilidad_general" in prompt

    def test_prompt_includes_title_and_genre(self):
        """Core movie info must always appear regardless of score values."""
        adapter = GeminiRecommendationLlmAdapter()
        movie = self._make_movie_dict()
        prompt = adapter._build_prompt(
            query="sci-fi",
            context_summary="genres=Sci-Fi",
            movies_with_scores=[movie],
        )
        assert "Inception" in prompt
        assert "Sci-Fi" in prompt

    def test_empty_movies_list_returns_fallback_prompt(self):
        adapter = GeminiRecommendationLlmAdapter()
        prompt = adapter._build_prompt(
            query="something",
            context_summary="general",
            movies_with_scores=[],
        )
        # Empty list → fallback prompt explaining no results
        assert "no hay recomendaciones" in prompt.lower() or "no" in prompt.lower()


# ===========================================================================
# Bug 3 — Genre match boosts correct movies; non-matching genres score lower
# ===========================================================================

class TestScorerGenreMatch:
    """score_and_select must rank genre-matching movies above non-matching ones
    when the user explicitly requested a genre."""

    def _animation_row(self, uri: str, title: str, rating: str = "7.5") -> dict:
        return {**_row(uri, title, "Animation"), "rating": rating}

    def _crime_row(self, uri: str, title: str, rating: str = "9.0") -> dict:
        """Crime drama — very high rating but wrong genre for an animation request."""
        return {**_row(uri, title, "Crime"), "rating": rating}

    def test_animation_beats_high_rated_crime_when_animation_requested(self):
        """A lower-rated Animation movie should rank above a higher-rated Crime movie
        when the user explicitly asked for Animation."""
        ctx = UserContext(mood="happy", genres=["Animation"], raw_query="animated movie")
        profile = UserProfile(user_id="u1", genre_weights={}, is_cold_start=False)
        rows = [
            self._crime_row("http://ont/crime1", "Fight Club", rating="9.5"),
            self._animation_row("http://ont/anim1", "Toy Story", rating="7.0"),
        ]
        movies = score_and_select(rows, ctx, profile, n=5)
        assert len(movies) == 2
        # The animation movie should come first despite lower rating
        assert movies[0].uri == "http://ont/anim1", (
            f"Expected Toy Story (Animation) first, got {movies[0].title}"
        )

    def test_family_genre_maps_to_children_for_genre_match(self):
        """ctx.genres=['Family'] should match a movie with genreName='Children'."""
        ctx = UserContext(genres=["Family"], raw_query="family movie")
        profile = UserProfile(user_id="u1", genre_weights={}, is_cold_start=False)
        rows = [
            {**_row("http://ont/crime1", "The Godfather", "Crime"), "rating": "9.5"},
            {**_row("http://ont/kids1", "Bambi", "Children"), "rating": "7.0"},
        ]
        movies = score_and_select(rows, ctx, profile, n=5)
        assert movies[0].uri == "http://ont/kids1", (
            "Children movie should rank first when user requested Family genre"
        )

    def test_no_genre_request_leaves_rating_dominant(self):
        """When ctx has no genres, rating should remain the dominant signal."""
        ctx = UserContext(raw_query="good movie")  # no genres
        profile = UserProfile(user_id="u1", genre_weights={}, is_cold_start=False)
        rows = [
            {**_row("http://ont/m1", "High Rated Drama", "Drama"), "rating": "9.5",
             "compatibilityScore": "0.0"},
            {**_row("http://ont/m2", "Low Rated Comedy", "Comedy"), "rating": "5.0",
             "compatibilityScore": "0.0"},
        ]
        movies = score_and_select(rows, ctx, profile, n=5)
        assert movies[0].uri == "http://ont/m1"

    def test_multiple_requested_genres_any_match_counts(self):
        """Any genre in ctx.genres should match (OR logic)."""
        ctx = UserContext(genres=["Animation", "Family"], raw_query="animated family")
        profile = UserProfile(user_id="u1", genre_weights={}, is_cold_start=False)
        rows = [
            {**_row("http://ont/action1", "Die Hard", "Action"), "rating": "8.5",
             "compatibilityScore": "0.0"},
            {**_row("http://ont/anim1", "Moana", "Animation"), "rating": "7.0",
             "compatibilityScore": "0.0"},
        ]
        movies = score_and_select(rows, ctx, profile, n=5)
        assert movies[0].uri == "http://ont/anim1"
