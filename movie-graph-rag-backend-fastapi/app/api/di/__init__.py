"""Dependency Injection module exports"""
from .common_di import (
    get_settings_di,
    get_mongo_db_di,
    get_recommendation_llm_client_di,
)
from .auth_di import (
    get_auth_user_repository_di,
    get_auth_use_case_di,
    get_current_user_di,
    get_current_admin_di,
)
from .movies_di import (
    get_favorite_repository_di,
    get_query_history_repository_di,
    get_user_favorites_use_case_di,
    get_query_history_use_case_di,
    get_recommendation_use_case_di,
    get_recommendation_metrics_repository_di,
    get_recommendation_metrics_use_case_di,
)
from .recommendation_di import (
    get_movies_repository_di,
    get_movies_use_case_di,
)
from .di_container import get_di_container, initialize_di_container

__all__ = [
    # Common
    "get_settings_di",
    "get_mongo_db_di",
    "get_recommendation_llm_client_di",
    # Auth
    "get_auth_user_repository_di",
    "get_auth_use_case_di",
    "get_current_user_di",
    "get_current_admin_di",
    # Recommendation domain (favorites, history, recommendations, metrics)
    "get_favorite_repository_di",
    "get_query_history_repository_di",
    "get_user_favorites_use_case_di",
    "get_query_history_use_case_di",
    "get_recommendation_use_case_di",
    "get_recommendation_metrics_repository_di",
    "get_recommendation_metrics_use_case_di",
    # Movies domain
    "get_movies_repository_di",
    "get_movies_use_case_di",
    # Container
    "get_di_container",
    "initialize_di_container",
]
