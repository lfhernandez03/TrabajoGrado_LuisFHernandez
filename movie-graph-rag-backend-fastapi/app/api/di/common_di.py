"""Common infrastructure dependencies shared across modules"""
from typing import Callable
from functools import lru_cache

from app.core.config import settings
from app.core.database import get_database
from app.adapters.llm.groq_recommendation_llm_adapter import GroqRecommendationLlmAdapter
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort


@lru_cache(maxsize=1)
def get_settings_singleton():
    """Get app settings (cached singleton)"""
    return settings


def get_mongo_db_singleton():
    """Get MongoDB database instance"""
    return get_database()


@lru_cache(maxsize=1)
def get_recommendation_llm_client_singleton() -> RecommendationLlmClientPort:
    """Get recommendation LLM client (cached singleton)"""
    return GroqRecommendationLlmAdapter()

# FastAPI dependency injection functions
def get_settings_di():
    """FastAPI dependency: get settings"""
    return get_settings_singleton()


def get_mongo_db_di():
    """FastAPI dependency: get MongoDB"""
    return get_mongo_db_singleton()


def get_recommendation_llm_client_di() -> RecommendationLlmClientPort:
    """FastAPI dependency: get recommendation LLM client"""
    return get_recommendation_llm_client_singleton()
