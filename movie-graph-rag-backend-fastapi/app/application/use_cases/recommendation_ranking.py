from __future__ import annotations

import hashlib
import math
from datetime import datetime


def _extract_genre_set(movie: dict) -> set[str]:
    genres: set[str] = set()

    primary = (movie.get("genreName") or "").strip().lower()
    if primary:
        genres.add(primary)

    raw_genres = movie.get("genres")
    if isinstance(raw_genres, list):
        for genre in raw_genres:
            normalized = str(genre).strip().lower()
            if normalized:
                genres.add(normalized)

    return genres


def _genre_similarity(a: dict, b: dict) -> float:
    ga = _extract_genre_set(a)
    gb = _extract_genre_set(b)
    if not ga and not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def mmr_select(
    candidates: list[dict],
    n: int = 5,
    lambda_: float = 0.7,
    relevance_key: str = "compatibilityScore",
) -> list[dict]:
    if not candidates:
        return []

    lambda_ = min(1.0, max(0.0, float(lambda_)))
    remaining = list(candidates)
    selected: list[dict] = []

    while remaining and len(selected) < n:
        if not selected:
            best = max(remaining, key=lambda movie: movie.get(relevance_key, 0.0))
        else:

            def mmr_score(movie: dict, selected_movies: list[dict] = selected) -> float:
                relevance = movie.get(relevance_key, 0.0)
                max_sim = max(_genre_similarity(movie, selected_movie) for selected_movie in selected_movies)
                return lambda_ * relevance - (1 - lambda_) * max_sim

            best = max(remaining, key=mmr_score)

        selected.append(best)
        remaining.remove(best)

    return selected


def normalized_rating(rating_value: float | None, default_value: float, min_floor: float) -> float:
    if rating_value is None:
        return default_value
    return min(1.0, max(min_floor, float(rating_value) / 10))


def freshness_score(release_year: str | None, current_year: int, horizon: float = 40.0) -> float:
    try:
        if not release_year:
            return 0.0
        age = current_year - int(str(release_year)[:4])
        return max(0.0, 1.0 - age / horizon)
    except Exception:
        return 0.0


def cosine_similarity_sparse(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0

    dot = sum(vec_a[key] * vec_b[key] for key in vec_a.keys() & vec_b.keys())
    norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vec_b.values()))

    if norm_a <= 0 or norm_b <= 0:
        return 0.0

    return dot / (norm_a * norm_b)


def novelty_score(movie: dict, user_genre_profile: dict[str, float]) -> float:
    if not user_genre_profile:
        return 0.5

    genre = (movie.get("genreName") or "").strip().lower()
    if not genre:
        return 0.5

    candidate_vector = {genre: 1.0}
    similarity = cosine_similarity_sparse(candidate_vector, user_genre_profile)
    novelty = 1.0 - similarity
    return min(1.0, max(0.0, novelty))


def is_runtime_match(runtime_value: int | None, runtime_max: int | None) -> bool:
    if runtime_max is None:
        return True
    if runtime_value is None:
        return True
    return runtime_value <= runtime_max


def is_genre_match(genre_name: str | None, preferred_genres: list[str]) -> bool:
    if not preferred_genres:
        return True
    if not genre_name:
        return False
    return genre_name in preferred_genres


def score_fuseki_candidate(
    *,
    movie: dict,
    rank_hint: int,
    current_year: int,
    preferred_genres: list[str],
    runtime_max: int | None,
    user_genre_profile: dict[str, float],
    scoring_weights: dict[str, float],
) -> float:
    normalized = normalized_rating(
        rating_value=movie.get("averageRating"),
        default_value=0.6,
        min_floor=0.45,
    )
    freshness = freshness_score(movie.get("releaseDate"), current_year)
    novelty = novelty_score(movie, user_genre_profile)

    genre_bonus = (
        scoring_weights.get("genre_bonus", 0.15)
        if is_genre_match(movie.get("genreName"), preferred_genres)
        else -scoring_weights.get("genre_mismatch_penalty", 0.03)
    )
    runtime_bonus = (
        scoring_weights.get("runtime_bonus", 0.10)
        if is_runtime_match(movie.get("runtime"), runtime_max)
        else -scoring_weights.get("runtime_mismatch_penalty", 0.08)
    )
    ranking_bonus = max(
        0.0,
        scoring_weights.get("ranking_bonus_base", 0.10)
        - rank_hint * scoring_weights.get("ranking_decay", 0.015),
    )

    final_score = (
        normalized
        + scoring_weights.get("freshness", 0.08) * freshness
        + scoring_weights.get("novelty", 0.0) * novelty
        + genre_bonus
        + runtime_bonus
        + ranking_bonus
    )
    return min(0.99, max(0.4, round(final_score, 2)))


def rank_fuseki_movies(
    *,
    fuseki_candidates: list[dict],
    preferred_genres: list[str],
    runtime_max: int | None,
    current_year: int,
    user_genre_profile: dict[str, float],
    scoring_weights: dict[str, float],
    mmr_lambda: float = 0.7,
    limit: int = 5,
) -> list[dict]:
    if not fuseki_candidates:
        return []

    sorted_candidates = sorted(
        fuseki_candidates,
        key=lambda movie: (
            is_genre_match(movie.get("genreName"), preferred_genres),
            is_runtime_match(movie.get("runtime"), runtime_max),
            (movie.get("averageRating") or 0),
        ),
        reverse=True,
    )

    pre_scored: list[dict] = []
    for index, movie in enumerate(sorted_candidates):
        scored_movie = dict(movie)
        scored_movie["compatibilityScore"] = score_fuseki_candidate(
            movie=movie,
            rank_hint=index,
            current_year=current_year,
            preferred_genres=preferred_genres,
            runtime_max=runtime_max,
            user_genre_profile=user_genre_profile,
            scoring_weights=scoring_weights,
        )
        pre_scored.append(scored_movie)

    return [
        {
            "title": movie.get("title"),
            "posterUrl": movie.get("posterUrl"),
            "runtime": movie.get("runtime"),
            "genreName": movie.get("genreName"),
            "releaseDate": movie.get("releaseDate"),
            "averageRating": movie.get("averageRating"),
            "compatibilityScore": movie["compatibilityScore"],
        }
        for movie in mmr_select(pre_scored, n=limit, lambda_=mmr_lambda)
    ]


def score_network_cold_start_movies(
    *,
    candidates: list[dict],
    scoring_weights: dict[str, float],
    user_genre_profile: dict[str, float],
    user_id: str,
    limit: int = 5,
    pool_size: int = 40,
) -> list[dict]:
    if not candidates:
        return []

    max_degree = max((int(movie.get("degree") or 0) for movie in candidates), default=1)
    max_degree = max(1, max_degree)

    current_year = datetime.utcnow().year
    scored: list[dict] = []
    for movie in candidates:
        rating_norm = normalized_rating(
            rating_value=movie.get("averageRating"),
            default_value=0.55,
            min_floor=0.35,
        )

        degree_norm = math.log1p(max(0, int(movie.get("degree") or 0))) / math.log1p(max_degree)
        freshness = freshness_score(movie.get("releaseDate"), current_year)
        novelty = novelty_score(movie, user_genre_profile)

        score = (
            scoring_weights.get("rating", 0.58) * rating_norm
            + scoring_weights.get("degree", 0.42) * degree_norm
            + scoring_weights.get("freshness", 0.08) * freshness
            + scoring_weights.get("novelty", 0.0) * novelty
        )

        movie_with_score = dict(movie)
        movie_with_score["compatibilityScore"] = round(min(0.99, max(0.4, score)), 2)
        scored.append(movie_with_score)

    scored.sort(
        key=lambda item: (
            item.get("compatibilityScore", 0),
            item.get("averageRating") or 0,
            int(item.get("degree") or 0),
        ),
        reverse=True,
    )

    pool = scored[:pool_size]
    if pool:
        day_key = datetime.utcnow().strftime("%Y-%m-%d")
        hash_source = f"{user_id}:{day_key}".encode("utf-8")
        rotation_seed = int(hashlib.sha256(hash_source).hexdigest()[:8], 16)
        offset = rotation_seed % len(pool)
        pool = pool[offset:] + pool[:offset]

    return mmr_select(pool, n=limit)
