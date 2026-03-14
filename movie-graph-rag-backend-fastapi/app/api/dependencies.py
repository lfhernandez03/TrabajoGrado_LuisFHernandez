from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.database import Database

from app.adapters.repositories.mongo_auth_user_repository import MongoAuthUserRepositoryAdapter
from app.adapters.repositories.mongo_query_history_repository import (
    MongoQueryHistoryRepositoryAdapter,
)
from app.adapters.repositories.mongo_user_favorites_repository import (
    MongoUserFavoritesRepositoryAdapter,
)
from app.application.use_cases.auth_user import AuthUserUseCase
from app.application.use_cases.query_history import QueryHistoryUseCase
from app.application.use_cases.user_favorites import UserFavoritesUseCase
from app.core.database import get_database
from app.core.security import decode_access_token
from app.domain.entities.auth_user import AuthUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_auth_user_repository(
    db: Database = Depends(get_database),
) -> MongoAuthUserRepositoryAdapter:
    return MongoAuthUserRepositoryAdapter(db=db)


def get_auth_use_case(
    repository: MongoAuthUserRepositoryAdapter = Depends(get_auth_user_repository),
) -> AuthUserUseCase:
    return AuthUserUseCase(repository=repository)


def get_user_favorites_repository(
    db: Database = Depends(get_database),
) -> MongoUserFavoritesRepositoryAdapter:
    return MongoUserFavoritesRepositoryAdapter(db=db)


def get_user_favorites_use_case(
    repository: MongoUserFavoritesRepositoryAdapter = Depends(
        get_user_favorites_repository
    ),
) -> UserFavoritesUseCase:
    return UserFavoritesUseCase(repository=repository)


def get_query_history_repository(
    db: Database = Depends(get_database),
) -> MongoQueryHistoryRepositoryAdapter:
    return MongoQueryHistoryRepositoryAdapter(db=db)


def get_query_history_use_case(
    repository: MongoQueryHistoryRepositoryAdapter = Depends(
        get_query_history_repository
    ),
) -> QueryHistoryUseCase:
    return QueryHistoryUseCase(repository=repository)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    use_case: AuthUserUseCase = Depends(get_auth_use_case),
) -> AuthUser:
    try:
        payload = decode_access_token(token)
        user_id = payload["sub"]
        return use_case.get_me(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc
