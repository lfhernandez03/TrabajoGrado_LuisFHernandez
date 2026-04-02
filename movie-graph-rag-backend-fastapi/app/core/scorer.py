from __future__ import annotations

import logging
from datetime import datetime

from app.domain.entities.recommendation_models import Movie, UserContext, UserProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
_MMR_LAMBDA = 0.7          # trade-off relevance vs diversity (higher = more relevant)
_RATING_MAX = 10.0         # IMDB-style scale
_YEAR_BASELINE = 1990      # movies at/before this year get freshness ≈ 0
_CURRENT_YEAR = datetime.utcnow().year

_MOVIE_NS = "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#"

# ---------------------------------------------------------------------------
# Network metrics cache (populated once per batch of candidates)
# ---------------------------------------------------------------------------

# {movie_uri: {"betweenness": float, "clustering": float, "degree": float}}
_NETWORK_CACHE: dict[str, dict[str, float]] = {}


def _bulk_fetch_network_scores(uris: list[str]) -> None:
    """Fetch Phase 6 network metrics for all uncached URIs in one SPARQL query.

    Results are stored in ``_NETWORK_CACHE``.  URIs with no metrics in Fuseki
    are cached as empty dicts so they are not re-queried on the next request.
    """
    missing = [u for u in uris if u not in _NETWORK_CACHE]
    if not missing:
        return

    try:
        from app.core.fuseki_client import execute_select_query  # local import avoids circular dep at startup

        values_clause = " ".join(f"<{u}>" for u in missing)
        rows = execute_select_query(
            f"PREFIX movie: <{_MOVIE_NS}>\n"
            "SELECT ?movie ?betweenness ?clustering ?degree WHERE {\n"
            f"  VALUES ?movie {{ {values_clause} }}\n"
            "  OPTIONAL { ?movie movie:betweennessCentrality ?betweenness }\n"
            "  OPTIONAL { ?movie movie:clusteringCoefficient ?clustering }\n"
            "  OPTIONAL { ?movie movie:degreeCentrality ?degree }\n"
            "}"
        )
        uri_scores: dict[str, dict[str, float]] = {}
        for row in rows:
            uri = row.get("movie", "")
            if not uri:
                continue
            try:
                uri_scores[uri] = {
                    "betweenness": float(row.get("betweenness") or 0.0),
                    "clustering": float(row.get("clustering") or 0.0),
                    "degree": float(row.get("degree") or 0.0),
                }
            except (ValueError, TypeError):
                uri_scores[uri] = {}
        for uri in missing:
            _NETWORK_CACHE[uri] = uri_scores.get(uri, {})
    except Exception as exc:
        logger.debug("Network scores fetch skipped: %s", exc)
        for uri in missing:
            _NETWORK_CACHE[uri] = {}


def _compute_serendipity(movie: Movie, network: dict[str, float]) -> float:
    """Topological serendipity score for a single movie.

    Formula (from the architecture plan):
        serendipity = compatibility
                      x (1 - clustering)    # low clustering = bridge node
                      x betweenness         # connects different communities
                      x (1 - degree)        # anti-popularity bias

    The raw product is tiny (three sub-unit values multiplied), so it is
    scaled up by 3x and clamped to [0, 1].

    Returns 0.0 when network metrics are unavailable.
    """
    if not network:
        return 0.0
    betweenness = network.get("betweenness", 0.0)
    clustering = network.get("clustering", 0.0)
    degree = network.get("degree", 0.0)
    if betweenness == 0.0:
        return 0.0
    compatibility = movie.compatibility_score or 0.0
    raw = compatibility * (1.0 - clustering) * betweenness * (1.0 - degree)
    return min(raw * 3.0, 1.0)


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


_GENRE_ALIASES: dict[str, str] = {
    "family": "children",
    "science fiction": "sci-fi",
    "sci fi": "sci-fi",
    "scifi": "sci-fi",
    "kids": "children",
    "children's": "children",
}


def _genre_match(movie: Movie, ctx: UserContext) -> float:
    """1.0 if the movie's genre matches any genre in the user's request, 0.0 otherwise.

    Applies the same NLU→ontology normalisation used in query_strategy so that
    ctx.genres = ["Family"] correctly matches movie.genre = "Children".
    """
    if not ctx.genres or not movie.genre:
        return 0.0
    movie_genre_lower = movie.genre.strip().lower()
    for g in ctx.genres:
        # Normalise the requested genre the same way query_strategy does
        g_lower = g.strip().lower()
        normalised = _GENRE_ALIASES.get(g_lower, g_lower)
        if normalised == movie_genre_lower or g_lower == movie_genre_lower:
            return 1.0
    return 0.0


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

def _compute_score(
    movie: Movie,
    ctx: UserContext,
    profile: UserProfile,
    network: dict[str, float] | None = None,
) -> float:
    """Composite relevance score for a single movie candidate.

    With semantic + network data (Phases 5 + 6):
        score = 0.35·rating + 0.25·semantic + 0.20·serendipity + 0.10·freshness + 0.10·novelty

    With semantic data only (bridge ontology, Phase 5):
        score = 0.30·rating + 0.25·semantic + 0.25·genre_match + 0.10·freshness + 0.10·novelty

    Without semantic data (fallback strategies):
        score = 0.55·rating + 0.25·genre_match + 0.10·freshness + 0.10·novelty

    Genre match is 1.0 when the movie's genre aligns with the user's explicit request.
    Serendipity replaces genre_match when network metrics are available — the bridge
    ontology's compatibility_score already encodes semantic genre compatibility.
    """
    rating = _norm_rating(movie.rating)
    fresh = _freshness(movie.release_year)
    novel = _novelty(movie, profile)
    genre = _genre_match(movie, ctx)

    # Prefer the direct compatibility_score field; fall back to the dict
    semantic = movie.compatibility_score or 0.0
    if not semantic and movie.semantic_scores:
        semantic = float(movie.semantic_scores.get("overallCompatibility", 0.0))

    if semantic > 0.0 and network:
        serendipity = _compute_serendipity(movie, network)
        movie.serendipity_score = round(serendipity, 4)
        if serendipity > 0.0:
            return 0.35 * rating + 0.25 * semantic + 0.20 * serendipity + 0.10 * fresh + 0.10 * novel

    if semantic > 0.0:
        return 0.30 * rating + 0.25 * semantic + 0.25 * genre + 0.10 * fresh + 0.10 * novel
    return 0.55 * rating + 0.25 * genre + 0.10 * fresh + 0.10 * novel


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

    # Deduplicate by URI before scoring.  SPARQL DISTINCT does not prevent
    # the same movie appearing multiple times when it has several genre
    # assignments (each genreName produces a separate row).
    #
    # Strategy: keep the row whose genreName best matches the requested genres.
    # If the user asked for "Animation" and a movie appears as both "Action"
    # and "Animation", we prefer the "Animation" row so _genre_match() gives
    # it a proper boost rather than scoring it as an Action film.

    # Parse all candidates first so we have their URIs for the bulk fetch.
    parsed: list[Movie] = []
    for row in candidates:
        try:
            parsed.append(Movie.from_fuseki_row(row))
        except Exception:
            continue

    # Bulk-fetch Phase 6 network metrics (one SPARQL query for all candidates).
    all_uris = [m.uri for m in parsed if m.uri]
    _bulk_fetch_network_scores(all_uris)

    uri_to_entry: dict[str, tuple[Movie, float]] = {}
    for movie in parsed:
        try:
            network = _NETWORK_CACHE.get(movie.uri) if movie.uri else None
            score = _compute_score(movie, ctx, profile, network=network)
            if movie.uri not in uri_to_entry:
                uri_to_entry[movie.uri] = (movie, score)
            else:
                # Upgrade to this row if it scores higher (better genre match)
                _, existing_score = uri_to_entry[movie.uri]
                if score > existing_score:
                    uri_to_entry[movie.uri] = (movie, score)
        except Exception:  # never let a bad row crash the pipeline
            continue

    scored: list[tuple[Movie, float]] = list(uri_to_entry.values())

    if not scored:
        return []

    scored.sort(key=lambda x: x[1], reverse=True)
    return _mmr_select(scored, n)
