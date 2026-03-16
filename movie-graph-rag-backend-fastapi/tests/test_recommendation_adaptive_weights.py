"""
Sección: ¿Qué valida este archivo de tests?

Este módulo prueba el comportamiento adaptativo de pesos en recomendaciones.

Cobertura principal:
1) Umbral mínimo de datos:
    - Verifica que con menos de 20 métricas no se adapten los pesos.

2) Señales de fuentes ontológicas:
    - Comprueba que fuentes como "ontology_full" sí aporten ajustes
      efectivos en pesos relevantes (rating, genre_bonus y novelty).

3) Señal de navegación ontológica en engagement:
    - Valida que cuando ontologyNavigationUsed=True el engagement score
      sea mayor que el caso equivalente sin navegación ontológica.
"""

from app.application.use_cases.recommendation_adaptive_weights import (
    _engagement_score,
    adapt_scoring_weights,
)
from app.domain.entities.recommendation_metric import RecommendationMetric


def _make_metric(
    *,
    source: str,
    fallback_used: bool,
    movies_found: int,
    execution_time_ms: int,
    errors: list[str] | None = None,
    fuseki_rows: int = 1,
    ontology_navigation_used: bool = False,
) -> RecommendationMetric:
    metric = RecommendationMetric(
        userId="u1",
        query="test",
        source=source,
        fallbackUsed=fallback_used,
        fusekiRows=fuseki_rows,
        errors=errors or [],
        timingsMs={"total": execution_time_ms},
        moviesFound=movies_found,
        executionTimeMs=execution_time_ms,
    )
    metric.ontologyNavigationUsed = ontology_navigation_used
    return metric


def test_adapt_scoring_weights_requires_at_least_20_metrics() -> None:
    current_weights = {
        "rating": 0.58,
        "degree": 0.42,
        "freshness": 0.08,
        "novelty": 0.0,
        "genre_bonus": 0.15,
        "runtime_bonus": 0.10,
        "genre_mismatch_penalty": 0.03,
        "runtime_mismatch_penalty": 0.08,
        "ranking_bonus_base": 0.10,
        "ranking_decay": 0.015,
    }
    default_weights = dict(current_weights)
    metrics = [
        _make_metric(
            source="ontology_full",
            fallback_used=False,
            movies_found=5,
            execution_time_ms=100,
            ontology_navigation_used=True,
        )
        for _ in range(19)
    ]

    updated = adapt_scoring_weights(
        current_weights=current_weights,
        default_weights=default_weights,
        metrics=metrics,
    )

    assert updated == current_weights


def test_ontology_sources_contribute_to_adjustments() -> None:
    current_weights = {
        "rating": 0.58,
        "degree": 0.42,
        "freshness": 0.08,
        "novelty": 0.05,
        "genre_bonus": 0.15,
        "runtime_bonus": 0.10,
        "genre_mismatch_penalty": 0.03,
        "runtime_mismatch_penalty": 0.08,
        "ranking_bonus_base": 0.10,
        "ranking_decay": 0.015,
    }
    default_weights = dict(current_weights)

    def build_metrics(ontology_source: str) -> list[RecommendationMetric]:
        high = [
            _make_metric(
                source=ontology_source,
                fallback_used=False,
                movies_found=5,
                execution_time_ms=100,
                errors=[],
                fuseki_rows=10,
                ontology_navigation_used=True,
            )
            for _ in range(10)
        ]
        low = [
            _make_metric(
                source="safe_fallback",
                fallback_used=True,
                movies_found=0,
                execution_time_ms=5000,
                errors=["e"],
                fuseki_rows=10,
                ontology_navigation_used=False,
            )
            for _ in range(10)
        ]
        return high + low

    with_ontology = adapt_scoring_weights(
        current_weights=current_weights,
        default_weights=default_weights,
        metrics=build_metrics("ontology_full"),
    )
    without_ontology = adapt_scoring_weights(
        current_weights=current_weights,
        default_weights=default_weights,
        metrics=build_metrics("unknown_source"),
    )

    assert with_ontology["genre_bonus"] > without_ontology["genre_bonus"]
    assert with_ontology["rating"] > without_ontology["rating"]
    assert with_ontology["novelty"] > without_ontology["novelty"]


def test_engagement_score_rewards_ontology_navigation_usage() -> None:
    base_metric = _make_metric(
        source="ontology_mood_only",
        fallback_used=False,
        movies_found=4,
        execution_time_ms=1200,
        errors=[],
        fuseki_rows=5,
        ontology_navigation_used=False,
    )
    ontology_metric = _make_metric(
        source="ontology_mood_only",
        fallback_used=False,
        movies_found=4,
        execution_time_ms=1200,
        errors=[],
        fuseki_rows=5,
        ontology_navigation_used=True,
    )

    base_score = _engagement_score(base_metric)
    ontology_score = _engagement_score(ontology_metric)

    assert ontology_score > base_score


def test_missing_current_genre_bonus_still_gets_ontology_adjustment() -> None:
    current_weights = {
        "rating": 0.58,
        "degree": 0.42,
        "freshness": 0.08,
        "novelty": 0.05,
        "runtime_bonus": 0.10,
        "genre_mismatch_penalty": 0.03,
        "runtime_mismatch_penalty": 0.08,
        "ranking_bonus_base": 0.10,
        "ranking_decay": 0.015,
    }
    default_weights = {
        **current_weights,
        "genre_bonus": 0.15,
    }

    metrics = [
        _make_metric(
            source="ontology_full",
            fallback_used=False,
            movies_found=5,
            execution_time_ms=100,
            errors=[],
            fuseki_rows=10,
            ontology_navigation_used=True,
        )
        for _ in range(10)
    ] + [
        _make_metric(
            source="safe_fallback",
            fallback_used=True,
            movies_found=0,
            execution_time_ms=5000,
            errors=["e"],
            fuseki_rows=10,
            ontology_navigation_used=False,
        )
        for _ in range(10)
    ]

    updated = adapt_scoring_weights(
        current_weights=current_weights,
        default_weights=default_weights,
        metrics=metrics,
    )

    assert "genre_bonus" in updated
    assert updated["genre_bonus"] > default_weights["genre_bonus"]