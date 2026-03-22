from app.domain.entities.favorite_movie import FavoriteMovie
from app.domain.ports.user_favorites_repository import UserFavoritesRepositoryPort


class UserFavoritesUseCase:
    def __init__(self, repository: UserFavoritesRepositoryPort) -> None:
        self.repository = repository

    def get_my_favorites(self, user_id: str) -> list[FavoriteMovie]:
        return self.repository.get_favorites(user_id)

    def add_my_favorite(self, user_id: str, movie: FavoriteMovie) -> list[FavoriteMovie]:
        return self.repository.add_favorite(user_id, movie)

    def remove_my_favorite(self, user_id: str, movie_uri: str) -> list[FavoriteMovie]:
        return self.repository.remove_favorite(user_id, movie_uri)
