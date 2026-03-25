"""Unit tests for the recommendation API endpoints.

Covers:
    - Authentication barrier (401 without token)
    - Input validation (422 on bad payloads)
    - Happy-path response shape for every endpoint
    - Phase 5 metrics field presence and structure
    - Response content correctness

All tests run without Fuseki, Gemini, or MongoDB.
See conftest.py for fixture setup and mock strategy.
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Endpoint paths
# ---------------------------------------------------------------------------

GET_REC = "/api/v1/recommendation"
POST_REC = "/api/v1/recommendation"
POST_DEBUG = "/api/v1/recommendation/debug"
GET_ACTIVITY = "/api/v1/recommendation/activity"
POST_CHAT = "/api/v1/recommendation/chat"


# ===========================================================================
# 1. Authentication barrier
# ===========================================================================

class TestAuthBarrier:
    """Every recommendation endpoint must return 401 without a valid token."""

    def test_get_recommendation_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.get(GET_REC, params={"query": "action"})
        assert resp.status_code == 401

    def test_post_recommendation_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.post(POST_REC, json={"query": "action"})
        assert resp.status_code == 401

    def test_post_debug_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.post(POST_DEBUG, json={"query": "action"})
        assert resp.status_code == 401

    def test_post_chat_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.post(
            POST_CHAT,
            json={
                "session_id": "s1",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert resp.status_code == 401

    def test_get_activity_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.get(GET_ACTIVITY)
        assert resp.status_code == 401


# ===========================================================================
# 2. Input validation (422 Unprocessable Entity)
# ===========================================================================

class TestInputValidation:
    """FastAPI / Pydantic must reject invalid inputs before they reach the use case."""

    def test_get_recommendation_empty_query_string(self, client):
        # query param with min_length=1 — an empty string should be rejected
        resp = client.get(GET_REC, params={"query": ""})
        assert resp.status_code == 422

    def test_post_recommendation_empty_query(self, client):
        resp = client.post(POST_REC, json={"query": ""})
        assert resp.status_code == 422

    def test_post_recommendation_missing_query(self, client):
        resp = client.post(POST_REC, json={})
        assert resp.status_code == 422

    def test_post_debug_empty_query(self, client):
        resp = client.post(POST_DEBUG, json={"query": ""})
        assert resp.status_code == 422

    def test_post_chat_missing_messages(self, client):
        resp = client.post(POST_CHAT, json={"session_id": "s1"})
        assert resp.status_code == 422

    def test_post_chat_empty_messages_list(self, client):
        resp = client.post(POST_CHAT, json={"session_id": "s1", "messages": []})
        assert resp.status_code == 422

    def test_post_chat_invalid_role(self, client):
        resp = client.post(
            POST_CHAT,
            json={
                "session_id": "s1",
                "messages": [{"role": "admin", "content": "hello"}],
            },
        )
        assert resp.status_code == 422

    def test_post_chat_empty_session_id(self, client):
        resp = client.post(
            POST_CHAT,
            json={
                "session_id": "",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert resp.status_code == 422

    def test_post_chat_empty_message_content(self, client):
        resp = client.post(
            POST_CHAT,
            json={
                "session_id": "s1",
                "messages": [{"role": "user", "content": ""}],
            },
        )
        assert resp.status_code == 422


# ===========================================================================
# 3. Happy-path HTTP status and response shape
# ===========================================================================

class TestHappyPath:
    """Authenticated requests with valid payloads must return 200 with the expected schema."""

    def test_get_recommendation_returns_200(self, client):
        resp = client.get(GET_REC, params={"query": "something relaxing"})
        assert resp.status_code == 200

    def test_post_recommendation_returns_200(self, client):
        resp = client.post(POST_REC, json={"query": "horror for tonight"})
        assert resp.status_code == 200

    def test_post_debug_returns_200(self, client):
        resp = client.post(POST_DEBUG, json={"query": "something relaxing"})
        assert resp.status_code == 200

    def test_post_chat_returns_200(self, client):
        resp = client.post(
            POST_CHAT,
            json={
                "session_id": "sess_abc123",
                "messages": [{"role": "user", "content": "algo de terror"}],
            },
        )
        assert resp.status_code == 200

    # --- GET /recommendation schema ---

    def test_get_recommendation_top_level_fields(self, client):
        data = client.get(GET_REC, params={"query": "action"}).json()
        required = {"query", "contextExtracted", "sparqlQuery", "moviesFound",
                    "moviesWithScores", "explanation", "executionTimeMs"}
        assert required.issubset(data.keys())

    def test_post_recommendation_top_level_fields(self, client):
        data = client.post(POST_REC, json={"query": "comedy"}).json()
        required = {"query", "contextExtracted", "sparqlQuery", "moviesFound",
                    "moviesWithScores", "explanation", "executionTimeMs"}
        assert required.issubset(data.keys())

    def test_post_debug_has_debug_payload(self, client):
        data = client.post(POST_DEBUG, json={"query": "drama"}).json()
        # debugPayload may be populated in the mock — key must exist
        assert "debugPayload" in data

    # --- POST /recommendation/chat schema ---

    def test_chat_top_level_fields(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "sess_abc123",
                "messages": [{"role": "user", "content": "recomiendame algo"}],
            },
        ).json()
        required = {"session_id", "movies", "explanation", "strategy_used",
                    "context_extracted", "execution_ms", "turn_count"}
        assert required.issubset(data.keys())


# ===========================================================================
# 4. Response content correctness
# ===========================================================================

class TestResponseContent:
    """Verify that specific values in the mock are correctly propagated to the response."""

    def test_get_recommendation_query_echoed(self, client):
        resp = client.get(GET_REC, params={"query": "action movies"})
        assert resp.json()["query"] == "action movies"

    def test_post_recommendation_query_echoed(self, client):
        resp = client.post(POST_REC, json={"query": "romantic films"})
        assert resp.json()["query"] == "romantic films"

    def test_recommendation_movies_list_not_empty(self, client):
        data = client.get(GET_REC, params={"query": "thriller"}).json()
        assert isinstance(data["moviesWithScores"], list)
        assert len(data["moviesWithScores"]) > 0

    def test_recommendation_movie_has_expected_fields(self, client):
        data = client.get(GET_REC, params={"query": "thriller"}).json()
        movie = data["moviesWithScores"][0]
        expected = {"title", "compatibilityScore", "averageRating", "genreName", "runtime"}
        assert expected.issubset(movie.keys())

    def test_recommendation_movie_title(self, client):
        data = client.get(GET_REC, params={"query": "thriller"}).json()
        assert data["moviesWithScores"][0]["title"] == "Inception"

    def test_recommendation_explanation_not_empty(self, client):
        data = client.get(GET_REC, params={"query": "something"}).json()
        assert data["explanation"] != ""

    def test_recommendation_context_extracted_has_mood(self, client):
        data = client.get(GET_REC, params={"query": "happy films"}).json()
        ctx = data["contextExtracted"]
        assert "mood" in ctx
        assert "genres" in ctx
        assert "confidence" in ctx

    def test_chat_session_id_matches_request(self, client):
        """The session_id in the response must equal the one sent in the request."""
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "sess_abc123",
                "messages": [{"role": "user", "content": "algo de terror"}],
            },
        ).json()
        assert data["session_id"] == "sess_abc123"

    def test_chat_turn_count_equals_user_message_count(self, client):
        """turn_count must reflect the number of 'user' messages sent."""
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "sess_xyz",
                "messages": [
                    {"role": "user", "content": "first message"},
                    {"role": "assistant", "content": "here are some films"},
                    {"role": "user", "content": "shorter please"},
                ],
            },
        ).json()
        # 2 user messages in the payload
        assert data["turn_count"] == 2

    def test_chat_movies_list_returned(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "s1",
                "messages": [{"role": "user", "content": "something fun"}],
            },
        ).json()
        assert isinstance(data["movies"], list)
        assert len(data["movies"]) == 2  # mock returns 2 movies

    def test_chat_movie_has_required_fields(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "s1",
                "messages": [{"role": "user", "content": "something fun"}],
            },
        ).json()
        movie = data["movies"][0]
        assert "title" in movie
        assert "compatibilityScore" in movie
        assert "averageRating" in movie

    def test_chat_explanation_not_empty(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "s1",
                "messages": [{"role": "user", "content": "something fun"}],
            },
        ).json()
        assert data["explanation"] != ""

    def test_chat_strategy_used_present(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "s1",
                "messages": [{"role": "user", "content": "something fun"}],
            },
        ).json()
        assert data["strategy_used"] == "ontology_mood_only"


# ===========================================================================
# 5. Phase 5 — metrics field
# ===========================================================================

class TestMetrics:
    """Every recommendation response must include the 'metrics' block from Phase 5."""

    def test_get_recommendation_has_metrics(self, client):
        data = client.get(GET_REC, params={"query": "drama"}).json()
        assert "metrics" in data

    def test_post_recommendation_has_metrics(self, client):
        data = client.post(POST_REC, json={"query": "drama"}).json()
        assert "metrics" in data

    def test_recommendation_metrics_structure(self, client):
        data = client.get(GET_REC, params={"query": "drama"}).json()
        m = data["metrics"]
        assert "ild" in m
        assert "semanticPrecision" in m
        assert "coldStartThreshold" in m
        assert "movieCount" in m

    def test_recommendation_metrics_ild_is_float(self, client):
        data = client.get(GET_REC, params={"query": "drama"}).json()
        assert isinstance(data["metrics"]["ild"], float)

    def test_recommendation_metrics_precision_between_0_and_1(self, client):
        data = client.get(GET_REC, params={"query": "drama"}).json()
        p = data["metrics"]["semanticPrecision"]
        assert 0.0 <= p <= 1.0

    def test_recommendation_metrics_cold_start_threshold_is_int(self, client):
        data = client.get(GET_REC, params={"query": "drama"}).json()
        assert isinstance(data["metrics"]["coldStartThreshold"], int)

    def test_chat_has_metrics(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "s_metrics",
                "messages": [{"role": "user", "content": "test"}],
            },
        ).json()
        assert "metrics" in data

    def test_chat_metrics_structure(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "s_metrics",
                "messages": [{"role": "user", "content": "test"}],
            },
        ).json()
        m = data["metrics"]
        assert "ild" in m
        assert "semanticPrecision" in m
        assert "coldStartThreshold" in m
        assert "movieCount" in m

    def test_chat_metrics_ild_range(self, client):
        data = client.post(
            POST_CHAT,
            json={
                "session_id": "s_metrics",
                "messages": [{"role": "user", "content": "test"}],
            },
        ).json()
        assert 0.0 <= data["metrics"]["ild"] <= 1.0

    def test_debug_endpoint_has_metrics(self, client):
        data = client.post(POST_DEBUG, json={"query": "comedy"}).json()
        assert "metrics" in data


# ===========================================================================
# 6. Use case interaction — verifying the mock was called correctly
# ===========================================================================

class TestUseCaseInteraction:
    """Verify that endpoints delegate to the use case with the correct arguments."""

    def test_get_recommendation_calls_use_case_with_query(self, client):
        client.get(GET_REC, params={"query": "my test query"})
        client.mock_rec_uc.get_recommendation.assert_called_once()
        call_args = client.mock_rec_uc.get_recommendation.call_args
        assert "my test query" in call_args.args or call_args.kwargs.get("query") == "my test query"

    def test_post_recommendation_calls_use_case_with_query(self, client):
        client.post(POST_REC, json={"query": "posted query"})
        client.mock_rec_uc.get_recommendation.assert_called_once()

    def test_post_debug_calls_debug_method(self, client):
        client.post(POST_DEBUG, json={"query": "debug query"})
        client.mock_rec_uc.get_recommendation_debug.assert_called_once()

    def test_post_chat_calls_execute_with_session_id(self, client):
        client.post(
            POST_CHAT,
            json={
                "session_id": "sess_verify",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        client.mock_chat_uc.execute.assert_called_once()
        call_kwargs = client.mock_chat_uc.execute.call_args.kwargs
        assert call_kwargs.get("session_id") == "sess_verify"

    def test_post_chat_passes_user_id_from_token(self, client):
        """user_id injected from the (mocked) JWT must be forwarded to ChatUseCase."""
        client.post(
            POST_CHAT,
            json={
                "session_id": "sess_verify",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        call_kwargs = client.mock_chat_uc.execute.call_args.kwargs
        assert call_kwargs.get("user_id") == "u_test_001"  # FAKE_USER.id
