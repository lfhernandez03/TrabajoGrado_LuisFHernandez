from datetime import datetime
from time import perf_counter
from uuid import uuid4

from app.application.use_cases.query_history import QueryHistoryUseCase
from app.application.use_cases.recommendation_metrics import RecommendationMetricsUseCase
from app.application.use_cases.user_favorites import UserFavoritesUseCase
from app.core.fuseki_client import FusekiQueryError, execute_select_query
from app.core.recommendation_llm import generate_recommendation_explanation
from app.domain.entities.query_history import QueryHistory
from app.domain.entities.recommendation_metric import RecommendationMetric


class RecommendationUseCase:
    def __init__(
        self,
        favorites_use_case: UserFavoritesUseCase,
        history_use_case: QueryHistoryUseCase,
        metrics_use_case: RecommendationMetricsUseCase,
    ) -> None:
        self.favorites_use_case = favorites_use_case
        self.history_use_case = history_use_case
        self.metrics_use_case = metrics_use_case

    def get_recommendation(self, query: str, user_id: str) -> dict:
        response, _ = self._build_recommendation(query, user_id)
        return response

    def get_recommendation_debug(self, query: str, user_id: str) -> dict:
        response, debug = self._build_recommendation(query, user_id)
        return {
            "recommendation": response,
            "debug": debug,
        }

    def _build_recommendation(self, query: str, user_id: str) -> tuple[dict, dict]:
        total_start = perf_counter()
        query_lower = query.lower()
        timings: dict[str, int] = {}
        debug_errors: list[str] = []

        def elapsed_ms(start_time: float) -> int:
            return max(0, int((perf_counter() - start_time) * 1000))

        context_start = perf_counter()

        social_context = None
        if any(token in query_lower for token in ["amigos", "friends", "grupo"]):
            social_context = {
                "companionType": "friends",
                "hasChildren": False,
                "numberOfPeople": 3,
            }
        elif any(token in query_lower for token in ["pareja", "novia", "novio"]):
            social_context = {
                "companionType": "partner",
                "hasChildren": False,
                "numberOfPeople": 2,
            }
        elif any(token in query_lower for token in ["familia", "ninos", "niños", "hijos"]):
            social_context = {
                "companionType": "family",
                "hasChildren": True,
                "numberOfPeople": 4,
            }

        emotional_context = None
        if any(token in query_lower for token in ["relaj", "tranquil", "liger", "calm"]):
            emotional_context = {
                "moodDescription": "relaxed",
                "desiredEnergyLevel": "low",
            }
        elif any(token in query_lower for token in ["accion", "acción", "emocion", "intensa"]):
            emotional_context = {
                "moodDescription": "excited",
                "desiredEnergyLevel": "high",
            }

        requirement_context = None
        detected_time = None
        for minutes in [60, 75, 90, 100, 120, 150]:
            if str(minutes) in query_lower:
                detected_time = minutes
                break
        if detected_time is not None:
            requirement_context = {
                "availableTime": detected_time,
                "excludedGenre": None,
            }

        genre_aliases = {
            "accion": "Action",
            "acción": "Action",
            "drama": "Drama",
            "comedia": "Comedy",
            "romantica": "Romance",
            "romántica": "Romance",
            "romance": "Romance",
            "terror": "Horror",
            "miedo": "Horror",
            "familia": "Family",
            "familiar": "Family",
            "animada": "Animation",
            "animacion": "Animation",
            "animación": "Animation",
            "ciencia ficcion": "Science Fiction",
            "ciencia ficción": "Science Fiction",
            "sci-fi": "Science Fiction",
            "thriller": "Thriller",
        }

        preferred_genres: list[str] = []
        for keyword, genre_name in genre_aliases.items():
            if keyword in query_lower and genre_name not in preferred_genres:
                preferred_genres.append(genre_name)

        timings["contextExtraction"] = elapsed_ms(context_start)

        def build_rdf_context(snapshot_id: str) -> str:
            social_companion = social_context["companionType"] if social_context else "unknown"
            mood = emotional_context["moodDescription"] if emotional_context else "neutral"
            energy = emotional_context["desiredEnergyLevel"] if emotional_context else "medium"
            available_time = (
                str(requirement_context["availableTime"])
                if requirement_context and requirement_context.get("availableTime")
                else "unknown"
            )
            genres_literal = ", ".join(preferred_genres) if preferred_genres else "none"
            return (
                "@prefix ctx: <http://www.semanticweb.org/movierecommendation/context/> .\n"
                f"ctx:{snapshot_id} ctx:userIntent \"{query}\" ;\n"
                f"    ctx:companionType \"{social_companion}\" ;\n"
                f"    ctx:mood \"{mood}\" ;\n"
                f"    ctx:energy \"{energy}\" ;\n"
                f"    ctx:availableTime \"{available_time}\" ;\n"
                f"    ctx:preferredGenres \"{genres_literal}\" ."
            )

        def build_sparql_query() -> str:
            genre_filter = ""
            if preferred_genres:
                genre_values = " ".join(f'\"{genre}\"' for genre in preferred_genres)
                genre_filter = (
                    "FILTER(?genreName IN (" + genre_values + "))"
                )

            runtime_filter = ""
            if requirement_context and requirement_context.get("availableTime"):
                available_time = requirement_context["availableTime"]
                runtime_filter = f"FILTER(!BOUND(?runtime) || ?runtime <= {available_time})"

            return (
                "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
                "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
                "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl ?releaseDate\n"
                "WHERE {\n"
                "  ?movie rdf:type movie:FeatureFilm ;\n"
                "         movie:hasTitle ?title .\n"
                "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
                "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
                "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
                "  OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }\n"
                "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
                f"  {genre_filter}\n"
                f"  {runtime_filter}\n"
                "}\n"
                "ORDER BY DESC(?rating)\n"
                "LIMIT 20"
            )

        build_query_start = perf_counter()
        context_snapshot_id = str(uuid4())
        rdf_generated = build_rdf_context(context_snapshot_id)
        sparql_query = build_sparql_query()
        timings["rdfAndSparqlBuild"] = elapsed_ms(build_query_start)

        favorites = self.favorites_use_case.get_my_favorites(user_id)
        top_candidates = favorites[:5]

        fuseki_candidates: list[dict] = []
        fuseki_rows_count = 0
        fuseki_start = perf_counter()
        try:
            raw_rows = execute_select_query(sparql_query)
            fuseki_rows_count = len(raw_rows)
            for row in raw_rows:
                title = row.get("title")
                if not title:
                    continue
                rating_value = None
                if row.get("rating") is not None:
                    try:
                        rating_value = float(row["rating"])
                    except ValueError:
                        rating_value = None

                runtime_value = None
                if row.get("runtime") is not None:
                    try:
                        runtime_value = int(float(row["runtime"]))
                    except ValueError:
                        runtime_value = None

                release_date = row.get("releaseDate")
                release_year = None
                if release_date:
                    release_year = str(release_date)[:4]

                fuseki_candidates.append(
                    {
                        "title": title,
                        "posterUrl": row.get("posterUrl"),
                        "runtime": runtime_value,
                        "genreName": row.get("genreName"),
                        "releaseDate": release_year,
                        "averageRating": rating_value,
                    }
                )
        except FusekiQueryError as exc:
            fuseki_candidates = []
            debug_errors.append(f"fuseki_query_error: {exc}")
        timings["fusekiQuery"] = elapsed_ms(fuseki_start)

        movies_with_scores: list[dict] = []
        scoring_start = perf_counter()
        recommendation_source = "fuseki"
        if fuseki_candidates:
            for index, movie in enumerate(fuseki_candidates[:5]):
                base_score = 0.5
                if movie.get("averageRating") is not None:
                    base_score = min(1.0, max(0.5, float(movie["averageRating"]) / 10))
                score = min(0.99, round(base_score + max(0, 0.12 - index * 0.02), 2))
                movies_with_scores.append(
                    {
                        **movie,
                        "compatibilityScore": score,
                    }
                )
        else:
            recommendation_source = "favorites_fallback"
            for index, movie in enumerate(top_candidates):
                score = max(0.5, 0.95 - (index * 0.08))
                movies_with_scores.append(
                    {
                        "title": movie.title,
                        "posterUrl": movie.posterUrl,
                        "runtime": movie.runtime,
                        "genreName": movie.genres[0] if movie.genres else None,
                        "releaseDate": str(movie.year) if movie.year else None,
                        "averageRating": movie.rating,
                        "compatibilityScore": round(score, 2),
                    }
                )
        timings["scoring"] = elapsed_ms(scoring_start)

        now = datetime.utcnow()

        context_summary_parts = []
        if social_context:
            context_summary_parts.append(
                f"social={social_context['companionType']}"
            )
        if emotional_context:
            context_summary_parts.append(
                f"mood={emotional_context['moodDescription']}"
            )
        if requirement_context and requirement_context.get("availableTime"):
            context_summary_parts.append(
                f"availableTime={requirement_context['availableTime']}"
            )
        context_summary = ", ".join(context_summary_parts) if context_summary_parts else "general"

        context_extracted = {
            "snapshotID": context_snapshot_id,
            "requestTimestamp": now,
            "userIntent": query,
            "hourOfDay": now.hour,
            "dayOfWeek": now.strftime("%A"),
            "socialContext": social_context,
            "emotionalContext": emotional_context,
            "requirementContext": requirement_context,
        }

        llm_start = perf_counter()
        explanation = generate_recommendation_explanation(
            query=query,
            context_summary=context_summary,
            movies_with_scores=movies_with_scores,
        )
        timings["llmExplanation"] = elapsed_ms(llm_start)

        execution_time_ms = max(1, elapsed_ms(total_start))

        response = {
            "query": query,
            "contextExtracted": context_extracted,
            "rdfGenerated": rdf_generated,
            "sparqlQuery": sparql_query,
            "moviesFound": len(movies_with_scores),
            "moviesWithScores": movies_with_scores,
            "explanation": explanation,
            "executionTimeMs": execution_time_ms,
        }

        history_start = perf_counter()
        self.history_use_case.create_entry(
            QueryHistory(
                userId=user_id,
                query=query,
                rdfGenerated=response["rdfGenerated"],
                sparqlExecuted=response["sparqlQuery"],
                contextExtracted=context_extracted,
                resultsFound=movies_with_scores,
                explanation=explanation,
                executionTimeMs=execution_time_ms,
                wasSuccessful=len(movies_with_scores) > 0,
            )
        )
        timings["historyWrite"] = elapsed_ms(history_start)
        timings["total"] = max(1, elapsed_ms(total_start))

        try:
            self.metrics_use_case.create_entry(
                RecommendationMetric(
                    userId=user_id,
                    query=query,
                    source=recommendation_source,
                    fallbackUsed=recommendation_source != "fuseki",
                    fusekiRows=fuseki_rows_count,
                    errors=debug_errors,
                    timingsMs=timings,
                    moviesFound=len(movies_with_scores),
                    executionTimeMs=execution_time_ms,
                    createdAt=now,
                )
            )
        except Exception as exc:
            debug_errors.append(f"metrics_write_error: {exc}")

        debug_payload = {
            "source": recommendation_source,
            "fusekiRows": fuseki_rows_count,
            "fallbackUsed": recommendation_source != "fuseki",
            "errors": debug_errors,
            "timingsMs": timings,
        }

        return response, debug_payload
