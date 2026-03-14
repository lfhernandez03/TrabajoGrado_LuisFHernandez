from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import get_auth_use_case, get_current_user
from app.api.schemas.auth import (
    AuthResponse,
    AuthUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.application.use_cases.auth_user import AuthUserUseCase
from app.domain.entities.auth_user import AuthUser
from app.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    PasswordTooLongError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_http_from_auth_error(exc: Exception, default_status: int) -> None:
    if isinstance(exc, PasswordTooLongError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if isinstance(exc, EmailAlreadyRegisteredError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if isinstance(exc, InvalidCredentialsError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    raise HTTPException(status_code=default_status, detail=str(exc)) from exc


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    use_case: AuthUserUseCase = Depends(get_auth_use_case),
) -> AuthResponse:
    try:
        token, user = use_case.register(
            email=payload.email,
            name=payload.name,
            password=payload.password,
        )
        return AuthResponse(
            access_token=token,
            user=AuthUserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
            ),
        )
    except Exception as exc:
        _raise_http_from_auth_error(exc, status.HTTP_409_CONFLICT)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    use_case: AuthUserUseCase = Depends(get_auth_use_case),
) -> AuthResponse:
    try:
        token, user = use_case.login(email=payload.email, password=payload.password)
        return AuthResponse(
            access_token=token,
            user=AuthUserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
            ),
        )
    except Exception as exc:
        _raise_http_from_auth_error(exc, status.HTTP_401_UNAUTHORIZED)


@router.post("/token", response_model=TokenResponse)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    use_case: AuthUserUseCase = Depends(get_auth_use_case),
) -> TokenResponse:
    try:
        token_value, _ = use_case.login(
            email=form_data.username,
            password=form_data.password,
        )
        return TokenResponse(access_token=token_value)
    except Exception as exc:
        _raise_http_from_auth_error(exc, status.HTTP_401_UNAUTHORIZED)


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: AuthUser = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
    )
