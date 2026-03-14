from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.database import Database

from app.adapters.repositories.mongo_auth_user_repository import MongoAuthUserRepositoryAdapter
from app.adapters.repositories.mongo_movie_catalog_repository import (
    MongoMovieCatalogRepositoryAdapter,
)
from app.adapters.repositories.mongo_query_history_repository import (
    MongoQueryHistoryRepositoryAdapter,
)
from app.adapters.repositories.mongo_recommendation_metrics_repository import (
    MongoRecommendationMetricsRepositoryAdapter,
)
from app.adapters.repositories.mongo_user_favorites_repository import (
    MongoUserFavoritesRepositoryAdapter,
)
from app.application.use_cases.auth_user import AuthUserUseCase
from app.application.use_cases.movies import MoviesUseCase
from app.application.use_cases.query_history import QueryHistoryUseCase
from app.application.use_cases.recommendation import RecommendationUseCase
from app.application.use_cases.recommendation_metrics import RecommendationMetricsUseCase
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


def get_recommendation_metrics_repository(
    db: Database = Depends(get_database),
) -> MongoRecommendationMetricsRepositoryAdapter:
    return MongoRecommendationMetricsRepositoryAdapter(db=db)


def get_recommendation_metrics_use_case(
    repository: MongoRecommendationMetricsRepositoryAdapter = Depends(
        get_recommendation_metrics_repository
    ),
) -> RecommendationMetricsUseCase:
    return RecommendationMetricsUseCase(repository=repository)


def get_recommendation_use_case(
    favorites_use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case),
    history_use_case: QueryHistoryUseCase = Depends(get_query_history_use_case),
    metrics_use_case: RecommendationMetricsUseCase = Depends(
        get_recommendation_metrics_use_case
    ),
) -> RecommendationUseCase:
    return RecommendationUseCase(
        favorites_use_case=favorites_use_case,
        history_use_case=history_use_case,
        metrics_use_case=metrics_use_case,
    )


def get_movie_catalog_repository(
    db: Database = Depends(get_database),
) -> MongoMovieCatalogRepositoryAdapter:
    return MongoMovieCatalogRepositoryAdapter(db=db)


def get_movies_use_case(
    catalog_repository: MongoMovieCatalogRepositoryAdapter = Depends(
        get_movie_catalog_repository
    ),
    history_use_case: QueryHistoryUseCase = Depends(get_query_history_use_case),
) -> MoviesUseCase:
    return MoviesUseCase(
        catalog_repository=catalog_repository,
        history_use_case=history_use_case,
    )


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


def get_current_admin(
    current_user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
