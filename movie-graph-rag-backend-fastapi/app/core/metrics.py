from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.recommendation_models import Movie, UserProfile

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

_SEMANTIC_PRECISION_THRESHOLD = 0.7   # min compatibilityScore to be "semantically precise"
_MIN_COLD_START_THRESHOLD = 2          # never require fewer than 2 snapshots
_MAX_COLD_START_THRESHOLD = 5          # never require more than 5 snapshots
_GENRE_DIVERSITY_HIGH = 0.6            # genre diversity ratio → threshold = 2
_GENRE_DIVERSITY_MED = 0.2             # genre diversity ratio → threshold = 3
_MAX_GENRES_COUNTED = 5                # cap for normalising genre diversity (0–1)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ListMetrics:
    """Quality metrics for a single recommendation list.

    Attributes:
        ild:                  Intra-List Diversity — average pairwise genre
                              distance in [0, 1].  1.0 means every movie is a
                              different genre; 0.0 means all the same genre.
        semantic_precision:   Fraction of movies whose ``compatibility_score``
                              exceeds *semantic_threshold*.  1.0 means every
                              recommendation is a strong ontological match.
        cold_start_threshold: Adaptive minimum snapshot count needed to exit
                              cold-start mode for this user profile.
        semantic_threshold:   The cutoff used to compute *semantic_precision*
                              (stored here for transparency).
        movie_count:          Number of movies in the list (≤ n).
    """

    ild: float
    semantic_precision: float
    cold_start_threshold: int
    semantic_threshold: float
    movie_count: int


# ---------------------------------------------------------------------------
# ILD — Intra-List Diversity
# ---------------------------------------------------------------------------

def compute_ild(movies: list[Movie]) -> float:
    """Average pairwise genre distance across the recommendation list.

    Genre distance is binary: 0 if both movies share the same genre, 1
    otherwise.  The result is the mean over all C(n, 2) unique pairs.

    Returns 0.0 for lists with fewer than 2 movies.
    """
    n = len(movies)
    if n < 2:
        return 0.0

    total = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            g_i = movies[i].genre
            g_j = movies[j].genre
            # Distance = 0 when both genres are the same known string; 1 otherwise.
            dist = 0.0 if (g_i and g_j and g_i == g_j) else 1.0
            total += dist
            pairs += 1

    return total / pairs if pairs else 0.0


# ---------------------------------------------------------------------------
# Semantic precision
# ---------------------------------------------------------------------------

def compute_semantic_precision(
    movies: list[Movie],
    threshold: float = _SEMANTIC_PRECISION_THRESHOLD,
) -> float:
    """Fraction of movies with ``compatibility_score`` above *threshold*.

    A high value means most recommendations are strong ontological matches
    for the user's current context.  Returns 0.0 for empty lists.
    """
    if not movies:
        return 0.0
    above = sum(1 for m in movies if m.compatibility_score > threshold)
    return above / len(movies)


# ---------------------------------------------------------------------------
# Adaptive cold-start threshold
# ---------------------------------------------------------------------------

def compute_cold_start_threshold(profile: UserProfile) -> int:
    """Return the minimum snapshot count needed to exit cold-start mode.

    The threshold is adaptive: users whose genre history already covers a
    wide variety of preferences need fewer interactions to build a reliable
    profile.  Users with narrow or empty history require more data.

    Mapping (``genre_diversity`` = distinct genres / ``_MAX_GENRES_COUNTED``):
        ≥ 0.6  (3+ distinct genres)  →  threshold = 2
        ≥ 0.2  (1–2 distinct genres) →  threshold = 3
        < 0.2  (no genre data)        →  threshold = 5
    """
    distinct_genres = len(profile.genre_weights)
    diversity = min(distinct_genres, _MAX_GENRES_COUNTED) / _MAX_GENRES_COUNTED

    if diversity >= _GENRE_DIVERSITY_HIGH:
        return _MIN_COLD_START_THRESHOLD      # 2
    if diversity >= _GENRE_DIVERSITY_MED:
        return 3
    return _MAX_COLD_START_THRESHOLD          # 5


# ---------------------------------------------------------------------------
# Convenience: compute all metrics at once
# ---------------------------------------------------------------------------

def compute_metrics(
    movies: list[Movie],
    profile: UserProfile,
    semantic_threshold: float = _SEMANTIC_PRECISION_THRESHOLD,
) -> ListMetrics:
    """Compute ILD, semantic precision, and adaptive cold-start threshold.

    Args:
        movies:             Final recommendation list from the scorer.
        profile:            User profile (used for cold-start threshold).
        semantic_threshold: Minimum compatibility_score for a "precise" hit.

    Returns:
        A :class:`ListMetrics` with all three quality signals populated.
    """
    return ListMetrics(
        ild=compute_ild(movies),
        semantic_precision=compute_semantic_precision(movies, semantic_threshold),
        cold_start_threshold=compute_cold_start_threshold(profile),
        semantic_threshold=semantic_threshold,
        movie_count=len(movies),
    )
