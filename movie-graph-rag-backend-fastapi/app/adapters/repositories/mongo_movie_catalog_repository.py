from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.fuseki_client import FusekiQueryError, execute_select_query


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

    def _safe_sparql_literal(self, value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", " ")
            .replace("\r", " ")
        )

    def _parse_year(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(str(value)[:4])
        except Exception:
            return None

    def _parse_runtime(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(float(str(value)))
        except Exception:
            return None

    def _parse_rating(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value))
        except Exception:
            return None

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

    def search_global_catalog(
        self,
        q: str | None,
        genre: str | None,
        director: str | None,
        year_from: int | None,
        year_to: int | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        safe_q = self._safe_sparql_literal((q or "").strip().lower())
        safe_genre = self._safe_sparql_literal((genre or "").strip().lower())
        safe_director = self._safe_sparql_literal((director or "").strip().lower())

        filters: list[str] = []
        if safe_q:
            filters.append(f'FILTER(CONTAINS(LCASE(?title), "{safe_q}"))')
        if safe_genre:
            filters.append(f'FILTER(CONTAINS(LCASE(COALESCE(?genreName, "")), "{safe_genre}"))')
        if safe_director:
            filters.append(
                f'FILTER(CONTAINS(LCASE(COALESCE(?directorName, "")), "{safe_director}"))'
            )

        filters_block = "\n  ".join(filters)
        sparql_query = (
            "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "SELECT DISTINCT ?movie ?title ?posterUrl ?runtime ?releaseDate ?rating ?directorName ?genreName ?description\n"
            "WHERE {\n"
            "  ?movie rdf:type movie:FeatureFilm ;\n"
            "         movie:hasTitle ?title .\n"
            "  OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }\n"
            "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
            "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
            "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
            "  OPTIONAL { ?movie movie:hasPlotSummary ?description }\n"
            "  OPTIONAL { ?movie movie:hasDirector/movie:personName ?directorName }\n"
            "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
            f"  {filters_block}\n"
            "}\n"
            "ORDER BY DESC(?rating) DESC(?releaseDate)\n"
            f"LIMIT {max(50, limit * 12)}"
        )

        try:
            rows = execute_select_query(sparql_query)
        except FusekiQueryError:
            return []

        catalog: dict[str, dict[str, Any]] = {}
        for row in rows:
            uri = row.get("movie")
            title = row.get("title")
            if not uri or not title:
                continue

            year = self._parse_year(row.get("releaseDate"))
            if year_from is not None and year is not None and year < year_from:
                continue
            if year_to is not None and year is not None and year > year_to:
                continue

            runtime = self._parse_runtime(row.get("runtime"))
            rating = self._parse_rating(row.get("rating"))
            genre_name = row.get("genreName")

            movie = {
                "uri": uri,
                "title": title,
                "posterUrl": row.get("posterUrl"),
                "tmdbId": None,
                "year": year,
                "runtime": runtime,
                "certification": None,
                "director": row.get("directorName"),
                "genres": [genre_name] if genre_name else [],
                "description": row.get("description"),
                "rating": rating,
                "relationReason": None,
                "createdAt": datetime.utcnow(),
            }

            existing = catalog.get(uri)
            if not existing:
                catalog[uri] = movie
                continue

            existing_genres = set(existing.get("genres", []))
            if genre_name:
                existing_genres.add(genre_name)
            existing["genres"] = sorted(existing_genres)

            for field in [
                "posterUrl",
                "year",
                "runtime",
                "director",
                "description",
                "rating",
            ]:
                if existing.get(field) is None and movie.get(field) is not None:
                    existing[field] = movie[field]

        movies = list(catalog.values())
        movies.sort(
            key=lambda m: (
                m.get("rating") is not None,
                m.get("rating") or 0,
                m.get("year") or 0,
            ),
            reverse=True,
        )
        return movies[: max(1, limit)]

    def autocomplete_global(self, term: str, limit: int = 8) -> list[dict[str, Any]]:
        query = term.lower().strip()
        if len(query) < 2:
            return []

        safe_term = self._safe_sparql_literal(query)
        sparql_query = (
            "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "SELECT DISTINCT ?movie ?title ?directorName\n"
            "WHERE {\n"
            "  ?movie rdf:type movie:FeatureFilm ;\n"
            "         movie:hasTitle ?title .\n"
            "  OPTIONAL { ?movie movie:hasDirector/movie:personName ?directorName }\n"
            f'  FILTER(CONTAINS(LCASE(?title), "{safe_term}"))\n'
            "}\n"
            "ORDER BY ?title\n"
            f"LIMIT {max(10, limit * 3)}"
        )

        try:
            rows = execute_select_query(sparql_query)
        except FusekiQueryError:
            return []

        results: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for row in rows:
            title = row.get("title")
            uri = row.get("movie")
            if not title or not uri:
                continue

            normalized = title.strip().lower()
            if normalized in seen_titles:
                continue
            seen_titles.add(normalized)

            results.append(
                {
                    "uri": uri,
                    "title": title,
                    "director": row.get("directorName"),
                }
            )

            if len(results) >= max(1, limit):
                break

        return results
