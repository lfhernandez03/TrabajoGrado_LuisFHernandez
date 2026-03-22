"""Use cases - organized by module"""
from .auth import AuthUserUseCase
from .movies import MoviesUseCase
from .history import QueryHistoryUseCase
from .users import UserFavoritesUseCase
from .recommendation import (
    RecommendationUseCase,
    RecommendationMetricsUseCase,
)

__all__ = [
    "AuthUserUseCase",
    "MoviesUseCase",
    "QueryHistoryUseCase",
    "UserFavoritesUseCase",
    "RecommendationUseCase",
    "RecommendationMetricsUseCase",
]
