from __future__ import annotations

from datetime import datetime
from typing import Any

from app.adapters.repositories.mongo_movie_catalog_repository import (
    MongoMovieCatalogRepositoryAdapter,
)
from app.application.use_cases.history import QueryHistoryUseCase
from app.domain.entities.query_history import QueryHistory


class MoviesUseCase:
    def __init__(
        self,
        catalog_repository: MongoMovieCatalogRepositoryAdapter,
        history_use_case: QueryHistoryUseCase,
    ) -> None:
        self.catalog_repository = catalog_repository
        self.history_use_case = history_use_case

    def get_examples(self, limit: int = 3) -> list[dict[str, Any]]:
        return self.catalog_repository.search_global_catalog(
            q=None,
            genre=None,
            director=None,
            year_from=None,
            year_to=None,
            limit=max(1, limit),
        )

    def autocomplete(
        self,
        user_id: str,
        term: str,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        _ = user_id
        return self.catalog_repository.autocomplete_global(
            term=term,
            limit=max(1, limit),
        )

    def search_movies(
        self,
        user_id: str,
        q: str | None,
        genre: str | None,
        director: str | None,
        year_from: int | None,
        year_to: int | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        start = datetime.utcnow()
        results = self.catalog_repository.search_global_catalog(
            q=q,
            genre=genre,
            director=director,
            year_from=year_from,
            year_to=year_to,
            limit=max(1, limit),
        )

        execution_time_ms = max(1, int((datetime.utcnow() - start).total_seconds() * 1000))
        self.history_use_case.create_entry(
            QueryHistory(
                userId=user_id,
                query=q or "Busqueda de peliculas",
                sparqlExecuted="# pending-graph-rag-migration-movies-search",
                resultsFound=results,
                executionTimeMs=execution_time_ms,
                wasSuccessful=len(results) > 0,
                contextExtracted={
                    "q": q,
                    "genre": genre,
                    "director": director,
                    "yearFrom": year_from,
                    "yearTo": year_to,
                    "limit": limit,
                },
            )
        )

        return results

    def find_connections(
        self,
        user_id: str,
        from_term: str,
        to_term: str,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        start = datetime.utcnow()
        from_results = self.catalog_repository.search_global_catalog(
            q=from_term,
            genre=None,
            director=None,
            year_from=None,
            year_to=None,
            limit=25,
        )
        to_results = self.catalog_repository.search_global_catalog(
            q=to_term,
            genre=None,
            director=None,
            year_from=None,
            year_to=None,
            limit=25,
        )

        def find_movie(term: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
            term_norm = term.lower().strip()
            exact = next((m for m in candidates if m.get("title", "").strip().lower() == term_norm), None)
            if exact:
                return exact
            contains = next((m for m in candidates if term_norm in m.get("title", "").lower()), None)
            return contains

        from_movie = find_movie(from_term, from_results)
        to_movie = find_movie(to_term, to_results)

        if not from_movie or not to_movie:
            response = {
                "found": False,
                "nodes": [],
                "edges": [],
                "pathSteps": [],
                "distance": 0,
                "sparqlQuery": "# pending-graph-rag-migration-movies-connections",
                "executionTimeMs": max(
                    1, int((datetime.utcnow() - start).total_seconds() * 1000)
                ),
                "fromTitle": from_movie["title"] if from_movie else None,
                "toTitle": to_movie["title"] if to_movie else None,
            }
            return response

        if from_movie["uri"] == to_movie["uri"]:
            node = {"uri": from_movie["uri"], "label": from_movie["title"], "type": "movie"}
            return {
                "found": True,
                "nodes": [node],
                "edges": [],
                "pathSteps": [
                    {
                        "step": 1,
                        "description": f"{from_movie['title']} es la misma pelicula",
                        "node": node,
                    }
                ],
                "distance": 0,
                "sparqlQuery": "# pending-graph-rag-migration-movies-connections",
                "executionTimeMs": max(
                    1, int((datetime.utcnow() - start).total_seconds() * 1000)
                ),
                "fromTitle": from_movie["title"],
                "toTitle": to_movie["title"],
            }

        from_genres = set(from_movie.get("genres", []))
        to_genres = set(to_movie.get("genres", []))
        shared_genres = list(from_genres.intersection(to_genres))

        shared_director = None
        if from_movie.get("director") and to_movie.get("director"):
            if from_movie["director"].strip().lower() == to_movie["director"].strip().lower():
                shared_director = from_movie["director"]

        if shared_director:
            shared_node = {
                "uri": f"person:{shared_director.lower().replace(' ', '-')}",
                "label": shared_director,
                "type": "person",
            }
            edges = [
                {
                    "from": from_movie["uri"],
                    "to": shared_node["uri"],
                    "label": "dirigida por",
                    "property": "movie:hasDirector",
                },
                {
                    "from": shared_node["uri"],
                    "to": to_movie["uri"],
                    "label": "tambien dirigio",
                    "property": "movie:hasDirector",
                },
            ]
            path_steps = [
                {"step": 1, "description": from_movie["title"], "node": {"uri": from_movie["uri"], "label": from_movie["title"], "type": "movie"}},
                {"step": 2, "description": f"Conectan por director {shared_director}", "node": shared_node},
                {"step": 3, "description": to_movie["title"], "node": {"uri": to_movie["uri"], "label": to_movie["title"], "type": "movie"}},
            ]
            found = True
        elif shared_genres:
            genre = shared_genres[0]
            shared_node = {
                "uri": f"genre:{genre.lower().replace(' ', '-')}",
                "label": genre,
                "type": "genre",
            }
            edges = [
                {
                    "from": from_movie["uri"],
                    "to": shared_node["uri"],
                    "label": "mismo genero",
                    "property": "movie:hasMainGenre",
                },
                {
                    "from": shared_node["uri"],
                    "to": to_movie["uri"],
                    "label": "mismo genero",
                    "property": "movie:hasMainGenre",
                },
            ]
            path_steps = [
                {"step": 1, "description": from_movie["title"], "node": {"uri": from_movie["uri"], "label": from_movie["title"], "type": "movie"}},
                {"step": 2, "description": f"Conectan por genero {genre}", "node": shared_node},
                {"step": 3, "description": to_movie["title"], "node": {"uri": to_movie["uri"], "label": to_movie["title"], "type": "movie"}},
            ]
            found = True
        else:
            edges = []
            path_steps = []
            found = False

        response = {
            "found": found,
            "nodes": [
                {"uri": from_movie["uri"], "label": from_movie["title"], "type": "movie"},
                *([path_steps[1]["node"]] if path_steps else []),
                {"uri": to_movie["uri"], "label": to_movie["title"], "type": "movie"},
            ],
            "edges": edges,
            "pathSteps": path_steps,
            "distance": 2 if found else -1,
            "sparqlQuery": "# pending-graph-rag-migration-movies-connections",
            "executionTimeMs": max(1, int((datetime.utcnow() - start).total_seconds() * 1000)),
            "fromTitle": from_movie["title"],
            "toTitle": to_movie["title"],
        }

        if max_depth >= 1:
            self.history_use_case.create_entry(
                QueryHistory(
                    userId=user_id,
                    query=f"connection {from_term} -> {to_term}",
                    sparqlExecuted=response["sparqlQuery"],
                    resultsFound=[response],
                    executionTimeMs=response["executionTimeMs"],
                    wasSuccessful=response["found"],
                    contextExtracted={
                        "from": from_term,
                        "to": to_term,
                        "maxDepth": max_depth,
                    },
                )
            )

        return response
