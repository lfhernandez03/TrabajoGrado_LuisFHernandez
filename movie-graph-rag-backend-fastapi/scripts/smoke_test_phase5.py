"""Phase 5 smoke test — Metrics: ILD, semantic precision, cold-start threshold.

Runs without requiring Fuseki or Gemini.  Execute from the project root:

    python scripts/smoke_test_phase5.py
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


def _movie(title: str, genre: str | None, compat: float = 0.0) -> Movie:
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


def _profile(genre_weights: dict[str, float]) -> UserProfile:
    return UserProfile(
        user_id="u1",
        genre_weights=genre_weights,
        dominant_mood=None,
        dominant_companion=None,
        snapshot_count=0,
        is_cold_start=True,
        dominant_time_of_day=None,
        children_age_hint=None,
    )


# ---------------------------------------------------------------------------
# Section 1 — Module imports
# ---------------------------------------------------------------------------

section("1 - Imports")

try:
    from app.core.metrics import (
        ListMetrics,
        compute_cold_start_threshold,
        compute_ild,
        compute_metrics,
        compute_semantic_precision,
    )
    check("metrics module imports", True)
except ImportError as e:
    check("metrics module imports", False, str(e))
    print("\n[ABORT] Cannot continue without the metrics module.")
    sys.exit(1)

try:
    from app.api.schemas.recommendation import RecommendationMetricsResponse
    check("RecommendationMetricsResponse schema imports", True)
except ImportError as e:
    check("RecommendationMetricsResponse schema imports", False, str(e))

try:
    from app.api.schemas.recommendation import RecommendationResponse, ChatResponse
    check("RecommendationResponse and ChatResponse have metrics field",
          hasattr(RecommendationResponse.model_fields, "metrics") or
          "metrics" in RecommendationResponse.model_fields)
except Exception as e:
    check("RecommendationResponse and ChatResponse have metrics field", False, str(e))

try:
    from app.application.use_cases.recommendation.chat_use_case import ChatResult
    check("ChatResult has metrics field", "metrics" in ChatResult.__dataclass_fields__)
except Exception as e:
    check("ChatResult has metrics field", False, str(e))

# ---------------------------------------------------------------------------
# Section 2 — ListMetrics dataclass
# ---------------------------------------------------------------------------

section("2 - ListMetrics dataclass")

m = ListMetrics(ild=0.8, semantic_precision=0.6, cold_start_threshold=3,
                semantic_threshold=0.7, movie_count=5)
check("ListMetrics fields accessible", m.ild == 0.8 and m.semantic_precision == 0.6)
check("ListMetrics cold_start_threshold", m.cold_start_threshold == 3)
check("ListMetrics movie_count", m.movie_count == 5)

# ---------------------------------------------------------------------------
# Section 3 — compute_ild
# ---------------------------------------------------------------------------

section("3 - compute_ild (Intra-List Diversity)")

# Empty list
check("ILD empty list returns 0.0", compute_ild([]) == 0.0)

# Single movie
single = [_movie("A", "Comedy")]
check("ILD single movie returns 0.0", compute_ild(single) == 0.0)

# All same genre -> diversity = 0
same = [_movie("A", "Drama"), _movie("B", "Drama"), _movie("C", "Drama")]
check("ILD all same genre = 0.0", compute_ild(same) == 0.0)

# All different genres -> diversity = 1
diff = [_movie("A", "Drama"), _movie("B", "Comedy"), _movie("C", "Action")]
ild_diff = compute_ild(diff)
check("ILD all different genres = 1.0", ild_diff == 1.0, f"got {ild_diff}")

# Mixed: 3 movies, 2 Drama + 1 Comedy -> 2 of 3 pairs are different
mixed = [_movie("A", "Drama"), _movie("B", "Drama"), _movie("C", "Comedy")]
# Pairs: (A,B)=0, (A,C)=1, (B,C)=1  -> avg = 2/3
ild_mixed = compute_ild(mixed)
expected_mixed = round(2 / 3, 10)
check("ILD mixed genres ~= 2/3", abs(ild_mixed - expected_mixed) < 1e-9, f"got {ild_mixed}")

# None genre treated as different
none_genre = [_movie("A", "Drama"), _movie("B", None)]
ild_none = compute_ild(none_genre)
check("ILD None genre treated as different (distance=1)", ild_none == 1.0, f"got {ild_none}")

# ---------------------------------------------------------------------------
# Section 4 — compute_semantic_precision
# ---------------------------------------------------------------------------

section("4 - compute_semantic_precision")

check("Precision empty list = 0.0", compute_semantic_precision([]) == 0.0)

all_high = [_movie("A", "Drama", compat=0.8), _movie("B", "Comedy", compat=0.9)]
check("Precision all above threshold = 1.0", compute_semantic_precision(all_high) == 1.0)

none_high = [_movie("A", "Drama", compat=0.3), _movie("B", "Comedy", compat=0.5)]
check("Precision none above threshold = 0.0", compute_semantic_precision(none_high) == 0.0)

half_high = [
    _movie("A", "Drama", compat=0.8),
    _movie("B", "Comedy", compat=0.8),
    _movie("C", "Action", compat=0.5),
    _movie("D", "Horror", compat=0.3),
]
prec_half = compute_semantic_precision(half_high)
check("Precision 2/4 above threshold = 0.5", prec_half == 0.5, f"got {prec_half}")

# Custom threshold — strict >, so compat==0.5 is NOT counted; only 0.8+0.8 above = 2/4
check("Precision with threshold=0.5 (strict >): 2/4 = 0.5",
      compute_semantic_precision(half_high, threshold=0.5) == 0.5)

# Boundary: score exactly at threshold is NOT above (strict >)
at_threshold = [_movie("A", "Drama", compat=0.7)]
check("Precision score == threshold not counted (strict >)",
      compute_semantic_precision(at_threshold, threshold=0.7) == 0.0)

# ---------------------------------------------------------------------------
# Section 5 — compute_cold_start_threshold
# ---------------------------------------------------------------------------

section("5 - compute_cold_start_threshold (adaptive)")

# No genre data -> threshold = 5
p_none = _profile({})
check("No genres -> threshold = 5", compute_cold_start_threshold(p_none) == 5)

# 1 genre -> diversity = 1/5 = 0.2 -> threshold = 3
p_one = _profile({"Drama": 0.9})
check("1 genre (diversity=0.2) -> threshold = 3", compute_cold_start_threshold(p_one) == 3)

# 2 genres -> diversity = 2/5 = 0.4 -> threshold = 3
p_two = _profile({"Drama": 0.9, "Comedy": 0.5})
check("2 genres (diversity=0.4) -> threshold = 3", compute_cold_start_threshold(p_two) == 3)

# 3 genres -> diversity = 3/5 = 0.6 -> threshold = 2
p_three = _profile({"Drama": 0.9, "Comedy": 0.5, "Action": 0.3})
check("3 genres (diversity=0.6) -> threshold = 2", compute_cold_start_threshold(p_three) == 2)

# 5+ genres -> capped at _MAX_GENRES_COUNTED, diversity = 1.0 -> threshold = 2
p_many = _profile({"Drama": 0.9, "Comedy": 0.5, "Action": 0.3, "Horror": 0.2, "Sci-Fi": 0.1, "Romance": 0.05})
check("5+ genres -> threshold = 2", compute_cold_start_threshold(p_many) == 2)

# ---------------------------------------------------------------------------
# Section 6 — compute_metrics (integration)
# ---------------------------------------------------------------------------

section("6 - compute_metrics (all together)")

movies_5 = [
    _movie("A", "Drama", compat=0.85),
    _movie("B", "Comedy", compat=0.9),
    _movie("C", "Action", compat=0.4),
    _movie("D", "Horror", compat=0.75),
    _movie("E", "Sci-Fi", compat=0.8),
]
profile = _profile({"Drama": 0.7, "Comedy": 0.5, "Action": 0.2})

result = compute_metrics(movies_5, profile)
check("compute_metrics returns ListMetrics", isinstance(result, ListMetrics))
check("compute_metrics movie_count = 5", result.movie_count == 5)
check("compute_metrics ILD > 0 (diverse genres)", result.ild > 0)
check("compute_metrics ILD = 1.0 (all different)", result.ild == 1.0)
check("compute_metrics semantic_precision > 0", result.semantic_precision > 0)
# Movies with compat > 0.7: A(0.85), B(0.9), D(0.75), E(0.8) = 4/5 = 0.8
check("compute_metrics semantic_precision = 0.8", result.semantic_precision == 0.8,
      f"got {result.semantic_precision}")
# 3 genres in profile -> threshold = 2
check("compute_metrics cold_start_threshold = 2", result.cold_start_threshold == 2)
check("compute_metrics semantic_threshold stored", result.semantic_threshold == 0.7)

# ---------------------------------------------------------------------------
# Section 7 — Pydantic schema serialisation
# ---------------------------------------------------------------------------

section("7 - Pydantic schema serialisation")

from app.api.schemas.recommendation import RecommendationMetricsResponse

schema = RecommendationMetricsResponse(
    ild=0.8,
    semanticPrecision=0.6,
    coldStartThreshold=3,
    movieCount=5,
)
d = schema.model_dump()
check("RecommendationMetricsResponse serialises all fields",
      all(k in d for k in ("ild", "semanticPrecision", "coldStartThreshold", "movieCount")))
check("RecommendationMetricsResponse values correct",
      d["ild"] == 0.8 and d["semanticPrecision"] == 0.6 and d["coldStartThreshold"] == 3)

# RecommendationResponse accepts metrics=None
from app.api.schemas.recommendation import RecommendationResponse
rec = RecommendationResponse(
    query="test",
    contextExtracted={},
    sparqlQuery="SELECT ...",
    moviesFound=0,
    moviesWithScores=[],
    explanation="",
    executionTimeMs=100,
    metrics=None,
)
check("RecommendationResponse metrics=None is valid", rec.metrics is None)

rec_with = RecommendationResponse(
    query="test",
    contextExtracted={},
    sparqlQuery="SELECT ...",
    moviesFound=5,
    moviesWithScores=[],
    explanation="test explanation",
    executionTimeMs=200,
    metrics=RecommendationMetricsResponse(ild=1.0, semanticPrecision=0.8, coldStartThreshold=2, movieCount=5),
)
check("RecommendationResponse metrics populated correctly",
      rec_with.metrics is not None and rec_with.metrics.ild == 1.0)

# ChatResponse accepts metrics
from app.api.schemas.recommendation import ChatResponse
chat_resp = ChatResponse(
    session_id="sess_1",
    movies=[],
    explanation="",
    strategy_used="broad",
    context_extracted={},
    execution_ms=150,
    turn_count=1,
    metrics=RecommendationMetricsResponse(ild=0.5, semanticPrecision=0.4, coldStartThreshold=3, movieCount=3),
)
check("ChatResponse metrics field works",
      chat_resp.metrics is not None and chat_resp.metrics.coldStartThreshold == 3)

# ---------------------------------------------------------------------------
# Section 8 — Integration with use case _Result.to_api_dict()
# ---------------------------------------------------------------------------

section("8 - RecommendationUseCase._Result.to_api_dict() includes metrics")

from app.application.use_cases.recommendation.recommendation_use_case import _Result

fake_metrics = ListMetrics(ild=0.6, semantic_precision=0.8, cold_start_threshold=3,
                           semantic_threshold=0.7, movie_count=4)
fake_ctx_cls = __import__(
    "app.domain.entities.recommendation_models", fromlist=["UserContext"]
).UserContext

result_obj = _Result(
    query="test query",
    movies=[],
    explanation="ok",
    strategy_used="broad",
    sparql_executed="SELECT ...",
    candidates_found=0,
    context=fake_ctx_cls(session_id=None),
    metrics=fake_metrics,
    execution_ms=50,
    debug={},
)
api_dict = result_obj.to_api_dict()
check("to_api_dict includes 'metrics' key", "metrics" in api_dict)
check("metrics.ild in to_api_dict", api_dict["metrics"]["ild"] == 0.6)
check("metrics.semanticPrecision in to_api_dict", api_dict["metrics"]["semanticPrecision"] == 0.8)
check("metrics.coldStartThreshold in to_api_dict", api_dict["metrics"]["coldStartThreshold"] == 3)
check("metrics.movieCount in to_api_dict", api_dict["metrics"]["movieCount"] == 4)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in _results if ok)
total = len(_results)
if passed == total:
    print(f"  \033[92m[OK] All {total} checks passed -- Phase 5 smoke test OK\033[0m")
else:
    failed = [(label, detail) for label, ok, detail in _results if not ok]
    print(f"  \033[91m[FAIL] {passed}/{total} passed\033[0m")
    for label, detail in failed:
        print(f"         ✗ {label}" + (f": {detail}" if detail else ""))
    sys.exit(1)
print("=" * 60)
