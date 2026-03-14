from datetime import datetime

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database

from app.domain.entities.favorite_movie import FavoriteMovie
from app.domain.ports.user_favorites_repository import UserFavoritesRepositoryPort


class MongoUserFavoritesRepositoryAdapter(UserFavoritesRepositoryPort):
    def __init__(self, db: Database) -> None:
        self.collection: Collection = db["user"]

    def _to_entity(self, document: dict) -> FavoriteMovie:
        return FavoriteMovie(
            uri=document["uri"],
            title=document["title"],
            posterUrl=document.get("posterUrl"),
            year=document.get("year"),
            runtime=document.get("runtime"),
            certification=document.get("certification"),
            director=document.get("director"),
            genres=document.get("genres", []),
            description=document.get("description"),
            rating=document.get("rating"),
            relationReason=document.get("relationReason"),
            addedAt=document.get("addedAt"),
        )

    def _to_document(self, movie: FavoriteMovie) -> dict:
        return {
            "uri": movie.uri,
            "title": movie.title,
            "posterUrl": movie.posterUrl,
            "year": movie.year,
            "runtime": movie.runtime,
            "certification": movie.certification,
            "director": movie.director,
            "genres": movie.genres,
            "description": movie.description,
            "rating": movie.rating,
            "relationReason": movie.relationReason,
            "addedAt": movie.addedAt,
        }

    def _parse_user_id(self, user_id: str) -> ObjectId:
        try:
            return ObjectId(user_id)
        except Exception as exc:
            raise ValueError("Invalid user id") from exc

    def get_favorites(self, user_id: str) -> list[FavoriteMovie]:
        object_id = self._parse_user_id(user_id)
        user = self.collection.find_one({"_id": object_id}, {"favoriteMovies": 1})

        if not user:
            return []

        favorite_movies = user.get("favoriteMovies", [])
        return [self._to_entity(movie) for movie in favorite_movies]

    def add_favorite(self, user_id: str, movie: FavoriteMovie) -> list[FavoriteMovie]:
        object_id = self._parse_user_id(user_id)

        self.collection.update_one(
            {"_id": object_id},
            {"$pull": {"favoriteMovies": {"uri": movie.uri}}},
        )

        movie_to_store = self._to_document(
            FavoriteMovie(
                uri=movie.uri,
                title=movie.title,
                posterUrl=movie.posterUrl,
                year=movie.year,
                runtime=movie.runtime,
                certification=movie.certification,
                director=movie.director,
                genres=movie.genres,
                description=movie.description,
                rating=movie.rating,
                relationReason=movie.relationReason,
                addedAt=datetime.utcnow(),
            )
        )

        self.collection.update_one(
            {"_id": object_id},
            {
                "$push": {
                    "favoriteMovies": {
                        "$each": [movie_to_store],
                        "$position": 0,
                    }
                }
            },
        )

        return self.get_favorites(user_id)

    def remove_favorite(self, user_id: str, movie_uri: str) -> list[FavoriteMovie]:
        object_id = self._parse_user_id(user_id)
        self.collection.update_one(
            {"_id": object_id},
            {"$pull": {"favoriteMovies": {"uri": movie_uri}}},
        )
        return self.get_favorites(user_id)
