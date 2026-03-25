"""Shared fixtures for the recommendation API test suite.

All fixtures are designed to run without requiring Fuseki, Gemini, or MongoDB.
External dependencies (database, LLM, DI container) are patched at the module
boundary so the FastAPI lifespan does not attempt real connections.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.di import get_current_user_di, get_recommendation_use_case_di
from app.api.di.movies_di import get_chat_use_case_di
from app.application.use_cases.recommendation.chat_use_case import ChatResult
from app.core.metrics import ListMetrics
from app.domain.entities.auth_user import AuthUser
from app.domain.entities.recommendation_models import Movie, UserContext
from app.main import app


# ---------------------------------------------------------------------------
# Shared domain objects
# ---------------------------------------------------------------------------

FAKE_USER = AuthUser(
    id="u_test_001",
    email="tester@example.com",
    name="Test User",
    password_hash="not_a_real_hash",
    role="user",
)


def _fake_movie(
    title: str = "Inception",
    genre: str = "Sci-Fi",
    compat: float = 0.9,
) -> Movie:
    return Movie(
        uri=f"http://ont/{title.lower().replace(' ', '_')}",
        title=title,
        genre=genre,
        runtime=148,
        rating=8.8,
        poster_url=None,
        release_year="2010",
        compatibility_score=compat,
        mood_match_score=0.85,
        social_match_score=None,
        energy_match_score=0.9,
        time_match_score=0.7,
        semantic_scores={"overallCompatibility": compat},
        kid_friendly=False,
    )


def _recommendation_payload(query: str = "action movies") -> dict:
    """Simulates the dict returned by RecommendationUseCase.get_recommendation()."""
    movie = _fake_movie()
    return {
        "query": query,
        "contextExtracted": {
            "mood": "happy",
            "companion": None,
            "has_children": False,
            "energy": "high",
            "genres": ["Sci-Fi"],
            "runtime_max": None,
            "exclusions": [],
            "confidence": 0.9,
            "time_of_day": "evening",
        },
        "rdfGenerated": "",
        "sparqlQuery": "SELECT * WHERE { ?m a movie:FeatureFilm }",
        "moviesFound": 5,
        "moviesWithScores": [movie.to_response_dict()],
        "explanation": "I recommend Inception because it matches your mood perfectly.",
        "executionTimeMs": 450,
        "metrics": {
            "ild": 0.8,
            "semanticPrecision": 0.8,
            "coldStartThreshold": 3,
            "movieCount": 1,
        },
    }


def _chat_result(session_id: str = "sess_abc123") -> ChatResult:
    """Simulates what ChatUseCase.execute() returns."""
    return ChatResult(
        session_id=session_id,
        movies=[_fake_movie(), _fake_movie("The Dark Knight", "Action", 0.85)],
        explanation="Based on your anxious mood, I recommend these films.",
        strategy_used="ontology_mood_only",
        context=UserContext(
            mood="anxious",
            companion=None,
            genres=["Thriller"],
            session_id=session_id,
        ),
        metrics=ListMetrics(
            ild=1.0,
            semantic_precision=1.0,
            cold_start_threshold=3,
            semantic_threshold=0.7,
            movie_count=2,
        ),
        execution_ms=320,
    )


# ---------------------------------------------------------------------------
# Mock use cases
# ---------------------------------------------------------------------------

def _mock_recommendation_use_case() -> MagicMock:
    uc = MagicMock()
    # Use side_effect so the returned dict echoes the actual query arg
    uc.get_recommendation.side_effect = lambda query, user_id: _recommendation_payload(query)
    uc.get_recommendation_debug.side_effect = lambda query, user_id: {
        **_recommendation_payload(query),
        "debugPayload": {
            "strategy_used": "ontology_full",
            "strategy_attempts": ["ontology_full"],
            "candidates_found": 5,
            "query_type": "mood_driven",
            "is_cold_start": False,
        },
    }
    uc.get_activity_recommendation = AsyncMock(
        return_value=_recommendation_payload("activity-based query")
    )
    return uc


def _mock_chat_use_case() -> MagicMock:
    uc = MagicMock()
    uc.execute.return_value = _chat_result()
    return uc


# ---------------------------------------------------------------------------
# TestClient fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """FastAPI TestClient with all external dependencies mocked.

    Patches:
    - ``connect_to_mongo`` / ``close_mongo_connection`` — avoids real DB.
    - ``initialize_di_container`` — avoids singleton initialisation.
    - ``get_current_user_di`` → returns FAKE_USER (no JWT required).
    - ``get_recommendation_use_case_di`` → returns a MagicMock use case.
    - ``get_chat_use_case_di`` → returns a MagicMock chat use case.
    """
    mock_rec_uc = _mock_recommendation_use_case()
    mock_chat_uc = _mock_chat_use_case()

    app.dependency_overrides[get_current_user_di] = lambda: FAKE_USER
    app.dependency_overrides[get_recommendation_use_case_di] = lambda: mock_rec_uc
    app.dependency_overrides[get_chat_use_case_di] = lambda: mock_chat_uc

    with (
        patch("app.main.connect_to_mongo"),
        patch("app.main.close_mongo_connection"),
        patch("app.main.initialize_di_container"),
    ):
        with TestClient(app, raise_server_exceptions=True) as c:
            # Attach mocks so individual tests can inspect / reconfigure them
            c.mock_rec_uc = mock_rec_uc
            c.mock_chat_uc = mock_chat_uc
            yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client():
    """TestClient with NO user override — used to test 401 behaviour."""
    with (
        patch("app.main.connect_to_mongo"),
        patch("app.main.close_mongo_connection"),
        patch("app.main.initialize_di_container"),
    ):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
