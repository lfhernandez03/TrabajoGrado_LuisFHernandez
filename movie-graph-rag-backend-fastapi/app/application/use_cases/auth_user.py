from app.core.security import create_access_token, hash_password, verify_password
from app.domain.entities.auth_user import AuthUser
from app.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    PasswordTooLongError,
    UserNotFoundError,
)
from app.domain.ports.auth_user_repository import AuthUserRepositoryPort


def _ensure_bcrypt_password_limit(password: str) -> None:
    if len(password.encode("utf-8")) > 72:
        raise PasswordTooLongError()


class AuthUserUseCase:
    def __init__(self, repository: AuthUserRepositoryPort) -> None:
        self.repository = repository

    def register(self, email: str, name: str, password: str) -> tuple[str, AuthUser]:
        _ensure_bcrypt_password_limit(password)

        if self.repository.find_by_email(email):
            raise EmailAlreadyRegisteredError()

        user = self.repository.create(
            email=email,
            name=name,
            password_hash=hash_password(password),
        )
        token = create_access_token(subject=user.id, email=user.email)
        return token, user

    def login(self, email: str, password: str) -> tuple[str, AuthUser]:
        _ensure_bcrypt_password_limit(password)

        user = self.repository.find_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        token = create_access_token(subject=user.id, email=user.email)
        return token, user

    def get_me(self, user_id: str) -> AuthUser:
        user = self.repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user
