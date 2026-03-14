from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database


class MongoMovieCatalogRepositoryAdapter:
    def __init__(self, db: Database) -> None:
        self.users_collection: Collection = db["user"]
        self.history_collection: Collection = db["queryhistories"]

    def _normalize_movie(self, movie: dict[str, Any]) -> dict[str, Any] | None:
        title = movie.get("title")
        if not title:
            return None

        uri = movie.get("uri") or f"generated:{title.lower().replace(' ', '-')[:64]}"

        year = movie.get("year")
        if year is None and movie.get("releaseDate"):
            try:
                year = int(str(movie["releaseDate"])[:4])
            except Exception:
                year = None

        genres = movie.get("genres")
        if not isinstance(genres, list):
            genres = [movie["genreName"]] if movie.get("genreName") else []

        rating = movie.get("rating")
        if rating is None and movie.get("averageRating") is not None:
            try:
                rating = float(movie["averageRating"])
            except Exception:
                rating = None

        return {
            "uri": str(uri),
            "title": str(title),
            "posterUrl": movie.get("posterUrl"),
            "tmdbId": movie.get("tmdbId"),
            "year": year,
            "runtime": movie.get("runtime"),
            "certification": movie.get("certification"),
            "director": movie.get("director"),
            "genres": genres,
            "description": movie.get("description"),
            "rating": rating,
            "relationReason": movie.get("relationReason"),
            "_updatedAt": movie.get("addedAt") or movie.get("createdAt") or datetime.utcnow(),
        }

    def _merge_catalog(
        self,
        catalog: dict[str, dict[str, Any]],
        source_movies: list[dict[str, Any]],
    ) -> None:
        for movie in source_movies:
            normalized = self._normalize_movie(movie)
            if not normalized:
                continue

            existing = catalog.get(normalized["uri"])
            if not existing:
                catalog[normalized["uri"]] = normalized
                continue

            existing_genres = set(existing.get("genres", []))
            new_genres = set(normalized.get("genres", []))
            existing["genres"] = sorted(existing_genres.union(new_genres))

            for field in [
                "posterUrl",
                "tmdbId",
                "year",
                "runtime",
                "certification",
                "director",
                "description",
                "rating",
                "relationReason",
            ]:
                if existing.get(field) is None and normalized.get(field) is not None:
                    existing[field] = normalized[field]

            if normalized.get("_updatedAt") and normalized["_updatedAt"] > existing.get("_updatedAt", datetime.min):
                existing["_updatedAt"] = normalized["_updatedAt"]

    def _collect_from_favorites(self, user_id: str | None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if user_id:
            try:
                query["_id"] = ObjectId(user_id)
            except Exception:
                return []

        documents = self.users_collection.find(query, {"favoriteMovies": 1})
        movies: list[dict[str, Any]] = []
        for document in documents:
            favorites = document.get("favoriteMovies", [])
            movies.extend(favorites)
        return movies

    def _collect_from_history(self, user_id: str | None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if user_id:
            query["userId"] = user_id

        documents = self.history_collection.find(
            query,
            {"resultsFound": 1, "createdAt": 1},
        ).sort("createdAt", -1).limit(200)

        movies: list[dict[str, Any]] = []
        for document in documents:
            created_at = document.get("createdAt")
            raw_results = document.get("resultsFound")
            if not isinstance(raw_results, list):
                continue

            for result in raw_results:
                if not isinstance(result, dict):
                    continue
                result_copy = dict(result)
                if created_at and "createdAt" not in result_copy:
                    result_copy["createdAt"] = created_at
                movies.append(result_copy)
        return movies

    def get_catalog(self, user_id: str | None = None) -> list[dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}

        favorites = self._collect_from_favorites(user_id)
        history_movies = self._collect_from_history(user_id)

        self._merge_catalog(catalog, favorites)
        self._merge_catalog(catalog, history_movies)

        movies = list(catalog.values())
        movies.sort(
            key=lambda m: (
                m.get("rating") is not None,
                m.get("rating") or 0,
                m.get("_updatedAt") or datetime.min,
            ),
            reverse=True,
        )

        for movie in movies:
            movie.pop("_updatedAt", None)

        return movies
