"""Dependency Injection Container - Central orchestrator for all dependencies"""
from typing import Optional

from app.api.di import (
    common_di,
    auth_di,
)


class DIContainer:
    """
    Central DI container that orchestrates all domain dependencies.
    
    This container provides access to all dependency factories across the application.
    It serves as the single source of truth for dependency resolution and initialization.
    
    Usage:
        container = DIContainer()
        llm_client = container.get_recommendation_llm_client()
    """
    
    def __init__(self):
        """Initialize the DI container"""
        # Future: Initialize all modules when they are ready
        pass
    
    # Common infrastructure
    def get_settings(self):
        return common_di.get_settings_di()
    
    def get_mongo_db(self):
        return common_di.get_mongo_db_di()
    
    def get_recommendation_llm_client(self):
        return common_di.get_recommendation_llm_client_di()
    
    # Auth domain
    def get_auth_user_repository(self):
        return auth_di.get_auth_user_repository_di()
    
    def get_auth_use_case(self):
        return auth_di.get_auth_use_case_di()


# Global singleton instance
_container: Optional[DIContainer] = None


def get_di_container() -> DIContainer:
    """Get or create the global DI container instance"""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def initialize_di_container() -> DIContainer:
    """Initialize and return the DI container (call once during app startup)"""
    global _container
    _container = DIContainer()
    return _container
