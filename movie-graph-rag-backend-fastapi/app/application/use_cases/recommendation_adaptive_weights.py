from __future__ import annotations

import math

from app.domain.entities.recommendation_metric import RecommendationMetric


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _engagement_score(metric: RecommendationMetric) -> float:
    movies_component = _clamp((metric.moviesFound or 0) / 5.0, 0.0, 1.0)
    fallback_component = 0.0 if metric.fallbackUsed else 1.0
    latency_component = 1.0 - _clamp((metric.executionTimeMs or 0) / 5000.0, 0.0, 1.0)
    errors_component = 0.0 if (metric.errors or []) else 1.0
    ontology_component = 1.0 if getattr(metric, "ontologyNavigationUsed", False) else 0.0
    score = (
        0.45 * movies_component
        + 0.20 * fallback_component
        + 0.15 * latency_component
        + 0.10 * errors_component
        + 0.10 * ontology_component
    )
    return _clamp(score, 0.0, 1.0)


def _pearson_corr(xs: list[float], ys: list[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0

    x = xs[:n]
    y = ys[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

    if den_x <= 0 or den_y <= 0:
        return 0.0
    return num / (den_x * den_y)


def adapt_scoring_weights(
    *,
    current_weights: dict[str, float],
    default_weights: dict[str, float],
    metrics: list[RecommendationMetric],
) -> dict[str, float]:
    if len(metrics) < 20:
        return dict(current_weights)

    scored_metrics = [(metric, _engagement_score(metric)) for metric in metrics]
    engagement_values = [score for _, score in scored_metrics]
    baseline_engagement = sum(engagement_values) / len(engagement_values)

    source_to_signals: dict[str, dict[str, float]] = {
        "fuseki_strict": {"rating": 0.30, "degree": 0.20, "freshness": 0.10, "novelty": -0.05},
        "fuseki_relaxed_runtime": {"runtime_bonus": 0.35, "rating": 0.20, "novelty": 0.05},
        "fuseki_relaxed_genre": {"genre_bonus": 0.35, "novelty": 0.20, "degree": 0.10},
        "fuseki_broad": {"novelty": 0.35, "freshness": 0.10, "rating": 0.10},
        "favorites_fallback": {"rating": 0.20, "degree": -0.15, "novelty": -0.10},
        "safe_fallback": {"rating": 0.10, "novelty": 0.10},
        "ontology_full": {
            "rating": 0.20,
            "novelty": 0.15,
            "genre_bonus": 0.25,
        },
        "ontology_mood_companion": {
            "rating": 0.25,
            "novelty": 0.10,
            "genre_bonus": 0.20,
        },
        "ontology_mood_only": {
            "rating": 0.30,
            "genre_bonus": 0.15,
            "novelty": 0.08,
        },
        "ontology_companion_only": {
            "rating": 0.30,
            "genre_bonus": 0.15,
            "novelty": 0.05,
        },
    }

    updated_weights = dict(current_weights)
    all_keys = set(current_weights.keys()) | set(default_weights.keys())
    adjustments: dict[str, float] = {key: 0.0 for key in all_keys}

    source_scores: dict[str, list[float]] = {}
    for metric, score in scored_metrics:
        source_scores.setdefault(metric.source, []).append(score)

    for source, scores in source_scores.items():
        if not scores:
            continue
        lift = (sum(scores) / len(scores)) - baseline_engagement
        signal_weights = source_to_signals.get(source)
        if not signal_weights:
            continue
        for weight_key, source_signal in signal_weights.items():
            if weight_key in adjustments:
                adjustments[weight_key] += source_signal * lift

    rows_values = [float(metric.fusekiRows or 0) for metric, _ in scored_metrics]
    latency_values = [float(metric.executionTimeMs or 0) for metric, _ in scored_metrics]
    movies_values = [float(metric.moviesFound or 0) for metric, _ in scored_metrics]

    corr_rows = _pearson_corr(rows_values, engagement_values)
    corr_latency = _pearson_corr(latency_values, engagement_values)
    corr_movies = _pearson_corr(movies_values, engagement_values)

    adjustments["degree"] += 0.06 * corr_rows
    adjustments["novelty"] += 0.04 * corr_rows
    adjustments["rating"] += 0.05 * corr_movies
    adjustments["freshness"] += 0.03 * corr_movies
    adjustments["novelty"] += -0.05 * corr_latency

    learning_rate = 0.08
    for weight_key, delta in adjustments.items():
        current = updated_weights.get(weight_key, default_weights.get(weight_key, 0.0))
        updated = current + learning_rate * delta
        default = default_weights.get(weight_key, updated)
        updated_weights[weight_key] = 0.90 * updated + 0.10 * default

    updated_weights["rating"] = _clamp(updated_weights.get("rating", 0.58), 0.35, 0.85)
    updated_weights["degree"] = _clamp(updated_weights.get("degree", 0.42), 0.15, 0.65)
    updated_weights["freshness"] = _clamp(updated_weights.get("freshness", 0.08), 0.0, 0.20)
    updated_weights["novelty"] = _clamp(updated_weights.get("novelty", 0.0), 0.0, 0.20)

    updated_weights["genre_bonus"] = _clamp(updated_weights.get("genre_bonus", 0.15), 0.05, 0.40)
    updated_weights["runtime_bonus"] = _clamp(updated_weights.get("runtime_bonus", 0.10), 0.03, 0.35)
    updated_weights["genre_mismatch_penalty"] = _clamp(
        updated_weights.get("genre_mismatch_penalty", 0.03),
        0.0,
        0.20,
    )
    updated_weights["runtime_mismatch_penalty"] = _clamp(
        updated_weights.get("runtime_mismatch_penalty", 0.08),
        0.0,
        0.30,
    )
    updated_weights["ranking_bonus_base"] = _clamp(
        updated_weights.get("ranking_bonus_base", 0.10),
        0.02,
        0.20,
    )
    updated_weights["ranking_decay"] = _clamp(
        updated_weights.get("ranking_decay", 0.015),
        0.005,
        0.05,
    )

    return updated_weights
