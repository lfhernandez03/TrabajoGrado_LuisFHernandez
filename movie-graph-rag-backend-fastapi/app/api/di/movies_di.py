"""Recommendation domain dependency injection"""
from functools import lru_cache

from app.core.database import get_database
from app.core.profile_service import ProfileService
from app.application.events import get_event_bus, RecommendationEventHandler
from app.adapters.repositories.mongo_user_favorites_repository import MongoUserFavoritesRepositoryAdapter
from app.adapters.repositories.mongo_query_history_repository import MongoQueryHistoryRepositoryAdapter
from app.adapters.repositories.mongo_movie_catalog_repository import MongoMovieCatalogRepositoryAdapter
from app.adapters.repositories.mongo_recommendation_metrics_repository import MongoRecommendationMetricsRepositoryAdapter
from app.application.use_cases.users import UserFavoritesUseCase
from app.application.use_cases.history import QueryHistoryUseCase
from app.application.use_cases.recommendation.recommendation_use_case import (
    RecommendationUseCase,
)
from app.application.use_cases.recommendation.chat_use_case import ChatUseCase
from app.application.use_cases.recommendation import RecommendationMetricsUseCase
from app.api.di.common_di import (
    get_mongo_db_singleton,
    get_recommendation_llm_client_singleton,
)


@lru_cache(maxsize=1)
def get_favorite_repository_singleton() -> MongoUserFavoritesRepositoryAdapter:
    """Get favorite movie repository (cached singleton)"""
    mongo = get_mongo_db_singleton()
    return MongoUserFavoritesRepositoryAdapter(mongo)


@lru_cache(maxsize=1)
def get_query_history_repository_singleton() -> MongoQueryHistoryRepositoryAdapter:
    """Get query history repository (cached singleton)"""
    mongo = get_mongo_db_singleton()
    return MongoQueryHistoryRepositoryAdapter(mongo)


@lru_cache(maxsize=1)
def get_recommendation_metrics_repository_singleton() -> MongoRecommendationMetricsRepositoryAdapter:
    """Get recommendation metrics repository (cached singleton)"""
    mongo = get_mongo_db_singleton()
    return MongoRecommendationMetricsRepositoryAdapter(db=mongo)


@lru_cache(maxsize=1)
def get_recommendation_metrics_use_case_singleton() -> RecommendationMetricsUseCase:
    """Get recommendation metrics use case (cached singleton)"""
    repo = get_recommendation_metrics_repository_singleton()
    return RecommendationMetricsUseCase(repository=repo)


@lru_cache(maxsize=1)
def get_user_favorites_use_case_singleton() -> UserFavoritesUseCase:
    """Get user favorites use case (cached singleton)"""
    repo = get_favorite_repository_singleton()
    return UserFavoritesUseCase(repo)


@lru_cache(maxsize=1)
def get_query_history_use_case_singleton() -> QueryHistoryUseCase:
    """Get query history use case (cached singleton)"""
    repo = get_query_history_repository_singleton()
    return QueryHistoryUseCase(repo)


@lru_cache(maxsize=1)
def get_recommendation_use_case_singleton() -> RecommendationUseCase:
    """Get recommendation use case (cached singleton)"""
    llm_client = get_recommendation_llm_client_singleton()
    favorites_use_case = get_user_favorites_use_case_singleton()
    history_use_case = get_query_history_use_case_singleton()
    
    return RecommendationUseCase(
        favorites_use_case=favorites_use_case,
        history_use_case=history_use_case,
        llm_client=llm_client,
    )


def _setup_recommendation_event_handlers():
    """Setup event handlers for recommendation events"""
    event_bus = get_event_bus()
    handler = RecommendationEventHandler()
    
    from app.domain.events.recommendation_events import (
        RecommendationCreatedEvent,
        RecommendationCacheHitEvent,
        RecommendationCacheMissEvent,
    )
    
    event_bus.subscribe(RecommendationCreatedEvent, handler.on_recommendation_created)
    event_bus.subscribe(RecommendationCacheHitEvent, handler.on_cache_hit)
    event_bus.subscribe(RecommendationCacheMissEvent, handler.on_cache_miss)


@lru_cache(maxsize=1)
def get_profile_service_singleton() -> ProfileService:
    """Get ProfileService singleton (in-process cache, no external deps)."""
    return ProfileService()


@lru_cache(maxsize=1)
def get_chat_use_case_singleton() -> ChatUseCase:
    """Get ChatUseCase singleton."""
    llm_client = get_recommendation_llm_client_singleton()
    profile_service = get_profile_service_singleton()
    return ChatUseCase(llm_client=llm_client, profile_service=profile_service)


# FastAPI dependency injection functions
def get_favorite_repository_di() -> MongoUserFavoritesRepositoryAdapter:
    """FastAPI dependency: get favorite repository"""
    return get_favorite_repository_singleton()


def get_query_history_repository_di() -> MongoQueryHistoryRepositoryAdapter:
    """FastAPI dependency: get query history repository"""
    return get_query_history_repository_singleton()


def get_user_favorites_use_case_di() -> UserFavoritesUseCase:
    """FastAPI dependency: get user favorites use case"""
    return get_user_favorites_use_case_singleton()


def get_query_history_use_case_di() -> QueryHistoryUseCase:
    """FastAPI dependency: get query history use case"""
    return get_query_history_use_case_singleton()


def get_recommendation_use_case_di() -> RecommendationUseCase:
    """FastAPI dependency: get recommendation use case"""
    return get_recommendation_use_case_singleton()


def get_recommendation_metrics_repository_di() -> MongoRecommendationMetricsRepositoryAdapter:
    """FastAPI dependency: get recommendation metrics repository"""
    return get_recommendation_metrics_repository_singleton()


def get_recommendation_metrics_use_case_di() -> RecommendationMetricsUseCase:
    """FastAPI dependency: get recommendation metrics use case"""
    return get_recommendation_metrics_use_case_singleton()


def get_chat_use_case_di() -> ChatUseCase:
    """FastAPI dependency: get chat use case"""
    return get_chat_use_case_singleton()


def initialize_recommendation_module():
    """Initialize recommendation module - setup event handlers"""
    _setup_recommendation_event_handlers()
