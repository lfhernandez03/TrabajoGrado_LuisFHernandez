from abc import ABC, abstractmethod

from app.domain.entities.favorite_movie import FavoriteMovie


class UserFavoritesRepositoryPort(ABC):
    @abstractmethod
    def get_favorites(self, user_id: str) -> list[FavoriteMovie]:
        raise NotImplementedError

    @abstractmethod
    def add_favorite(self, user_id: str, movie: FavoriteMovie) -> list[FavoriteMovie]:
        raise NotImplementedError

    @abstractmethod
    def remove_favorite(self, user_id: str, movie_uri: str) -> list[FavoriteMovie]:
        raise NotImplementedError
