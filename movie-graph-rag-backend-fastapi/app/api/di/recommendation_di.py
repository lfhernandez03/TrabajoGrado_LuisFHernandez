"""Movies domain dependency injection"""
from functools import lru_cache

from app.core.database import get_database
from app.adapters.repositories.mongo_movie_catalog_repository import MongoMovieCatalogRepositoryAdapter
from app.application.use_cases.movies import MoviesUseCase
from app.api.di.common_di import get_mongo_db_singleton


@lru_cache(maxsize=1)
def get_movies_repository_singleton() -> MongoMovieCatalogRepositoryAdapter:
    """Get movies repository (cached singleton)"""
    mongo = get_mongo_db_singleton()
    return MongoMovieCatalogRepositoryAdapter(mongo)


@lru_cache(maxsize=1)
def get_movies_use_case_singleton() -> MoviesUseCase:
    """Get movies use case (cached singleton)"""
    repo = get_movies_repository_singleton()
    return MoviesUseCase(repo)


# FastAPI dependency injection functions
def get_movies_repository_di() -> MongoMovieCatalogRepositoryAdapter:
    """FastAPI dependency: get movies repository"""
    return get_movies_repository_singleton()


def get_movies_use_case_di() -> MoviesUseCase:
    """FastAPI dependency: get movies use case"""
    return get_movies_use_case_singleton()
