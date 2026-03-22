"""Authentication domain dependency injection"""
from typing import Optional
from functools import lru_cache

from app.core.config import settings
from app.core.database import get_database
from app.adapters.repositories.mongo_auth_user_repository import MongoAuthUserRepositoryAdapter
from app.application.use_cases.auth_user import AuthUserUseCase
from app.api.di.common_di import get_mongo_db_singleton

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer


@lru_cache(maxsize=1)
def get_auth_user_repository_singleton() -> MongoAuthUserRepositoryAdapter:
    """Get auth user repository (cached singleton)"""
    mongo = get_mongo_db_singleton()
    return MongoAuthUserRepositoryAdapter(mongo)


@lru_cache(maxsize=1)
def get_auth_use_case_singleton() -> AuthUserUseCase:
    """Get auth use case (cached singleton)"""
    repo = get_auth_user_repository_singleton()
    return AuthUserUseCase(repo, settings)


# FastAPI dependency injection functions
def get_auth_user_repository_di() -> MongoAuthUserRepositoryAdapter:
    """FastAPI dependency: get auth user repository"""
    return get_auth_user_repository_singleton()


def get_auth_use_case_di() -> AuthUserUseCase:
    """FastAPI dependency: get auth use case"""
    return get_auth_use_case_singleton()


# Security dependencies
http_bearer = HTTPBearer()


async def get_current_user_di(credentials = Depends(http_bearer)):
    """
    FastAPI dependency: get current authenticated user.
    Extracts and validates JWT token from Authorization header.
    """
    auth_use_case = get_auth_use_case_singleton()
    user = auth_use_case.verify_token(credentials.credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_admin_di(current_user=Depends(get_current_user_di)):
    """
    FastAPI dependency: get current admin user.
    Requires user to be authenticated AND have admin role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
