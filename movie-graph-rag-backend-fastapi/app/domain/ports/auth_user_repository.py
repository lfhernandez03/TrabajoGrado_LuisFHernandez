from abc import ABC, abstractmethod

from app.domain.entities.auth_user import AuthUser


class AuthUserRepositoryPort(ABC):
    @abstractmethod
    def find_by_email(self, email: str) -> AuthUser | None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, user_id: str) -> AuthUser | None:
        raise NotImplementedError

    @abstractmethod
    def create(
        self,
        email: str,
        name: str,
        password_hash: str,
        role: str = "user",
    ) -> AuthUser:
        raise NotImplementedError
