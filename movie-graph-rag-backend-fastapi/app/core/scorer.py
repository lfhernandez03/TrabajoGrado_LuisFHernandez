from __future__ import annotations

from datetime import datetime

from app.domain.entities.recommendation_models import Movie, UserContext, UserProfile

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
_MMR_LAMBDA = 0.7          # trade-off relevance vs diversity (higher = more relevant)
_RATING_MAX = 10.0         # IMDB-style scale
_YEAR_BASELINE = 1990      # movies at/before this year get freshness ≈ 0
_CURRENT_YEAR = datetime.utcnow().year


# ---------------------------------------------------------------------------
# Individual scoring components
# ---------------------------------------------------------------------------

def _norm_rating(rating: float | None) -> float:
    """Normalise a 0–10 rating to 0–1."""
    if rating is None or rating <= 0:
        return 0.0
    return min(rating / _RATING_MAX, 1.0)


def _freshness(release_year: str | None) -> float:
    """Linear scale: _YEAR_BASELINE → 0.0, current year → 1.0.

    Unknown year returns a neutral 0.35 so missing data is not strongly
    penalised but fresh films are still rewarded.
    """
    if release_year is None:
        return 0.35
    try:
        year = int(str(release_year)[:4])
    except (ValueError, TypeError):
        return 0.35
    span = max(1, _CURRENT_YEAR - _YEAR_BASELINE)
    return max(0.0, min(1.0, (year - _YEAR_BASELINE) / span))


def _novelty(movie: Movie, profile: UserProfile) -> float:
    """Prefer genres underrepresented in the user's history.

    Returns 1 − genre_weight so a heavily-watched genre scores lower for
    novelty (nudging the system toward variety).  Returns neutral 0.5 when
    profile has no history or the movie has no genre.
    """
    if not profile.genre_weights or not movie.genre:
        return 0.5
    weight = profile.genre_weights.get(movie.genre, 0.0)
    return max(0.0, 1.0 - weight)


# ---------------------------------------------------------------------------
# Main scoring formula
# ---------------------------------------------------------------------------

def _compute_score(movie: Movie, ctx: UserContext, profile: UserProfile) -> float:  # noqa: ARG001
    """Composite relevance score for a single movie candidate.

    With semantic data (bridge ontology):
        score = 0.40·rating + 0.30·semantic + 0.15·freshness + 0.15·novelty

    Without semantic data (fallback strategies):
        score = 0.70·rating + 0.15·freshness + 0.15·novelty
    """
    rating = _norm_rating(movie.rating)
    fresh = _freshness(movie.release_year)
    novel = _novelty(movie, profile)

    # Prefer the direct compatibility_score field; fall back to the dict
    semantic = movie.compatibility_score or 0.0
    if not semantic and movie.semantic_scores:
        semantic = float(movie.semantic_scores.get("overallCompatibility", 0.0))

    if semantic > 0.0:
        return 0.40 * rating + 0.30 * semantic + 0.15 * fresh + 0.15 * novel
    return 0.70 * rating + 0.15 * fresh + 0.15 * novel


# ---------------------------------------------------------------------------
# MMR diversity selection
# ---------------------------------------------------------------------------

def _similarity(a: Movie, b: Movie) -> float:
    """Approximate genre-level similarity between two movies (0–1).

    Same genre → strong similarity (0.7).
    Different genres with close bridge scores → mild similarity.
    """
    if a.genre and b.genre and a.genre == b.genre:
        return 0.7
    score_diff = abs(a.compatibility_score - b.compatibility_score)
    return max(0.0, 0.3 - score_diff * 0.3)


def _mmr_select(scored: list[tuple[Movie, float]], n: int) -> list[Movie]:
    """Maximum Marginal Relevance selection.

    Iteratively picks the candidate that maximises:
        MMR = λ·relevance − (1−λ)·max_similarity_to_selected
    """
    if len(scored) <= n:
        return [m for m, _ in scored]

    selected: list[tuple[Movie, float]] = [scored[0]]
    remaining: list[tuple[Movie, float]] = list(scored[1:])

    while len(selected) < n and remaining:
        best_idx = 0
        best_mmr = float("-inf")

        for i, (cand, cand_score) in enumerate(remaining):
            max_sim = max(_similarity(cand, sel) for sel, _ in selected)
            mmr = _MMR_LAMBDA * cand_score - (1.0 - _MMR_LAMBDA) * max_sim
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i

        selected.append(remaining.pop(best_idx))

    return [m for m, _ in selected]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_and_select(
    candidates: list[dict],
    ctx: UserContext,
    profile: UserProfile,
    n: int = 5,
) -> list[Movie]:
    """Convert raw SPARQL rows → Movie objects, score, and select top-n with MMR.

    Args:
        candidates: Raw row dicts from Fuseki (as returned by execute_select_query).
        ctx:        UserContext for the current request.
        profile:    UserProfile for novelty computation.
        n:          How many movies to return.

    Returns:
        Up to ``n`` Movie objects, diverse and ranked.
    """
    if not candidates:
        return []

    scored: list[tuple[Movie, float]] = []
    for row in candidates:
        try:
            movie = Movie.from_fuseki_row(row)
            score = _compute_score(movie, ctx, profile)
            scored.append((movie, score))
        except Exception:  # never let a bad row crash the pipeline
            continue

    if not scored:
        return []

    scored.sort(key=lambda x: x[1], reverse=True)
    return _mmr_select(scored, n)
