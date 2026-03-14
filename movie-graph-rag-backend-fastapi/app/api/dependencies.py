from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.database import Database

from app.adapters.repositories.mongo_auth_user_repository import MongoAuthUserRepositoryAdapter
from app.application.use_cases.auth_user import AuthUserUseCase
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
