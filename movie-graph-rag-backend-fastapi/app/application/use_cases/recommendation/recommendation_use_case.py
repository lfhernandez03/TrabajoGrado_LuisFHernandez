"""Simplified recommendation use case - clean pipeline architecture"""
import logging
import asyncio
import math
from time import perf_counter
from typing import Optional, Any
from uuid import uuid4

from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort
from app.domain.entities.query_context import QueryContext
from app.core.fuseki_client import execute_select_query, FusekiQueryError
from app.core.ontology_query_builder import (
    build_cross_ontology_sparql,
    inject_context_snapshot,
    delete_context_snapshot,
    build_context_triples_turtle,
)
from app.application.use_cases.history import QueryHistoryUseCase
from app.application.use_cases.users import UserFavoritesUseCase
from .models import RecommendationResult, MovieRecommendation, DebugInfo

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

# Scoring weights - mínimo, simple, orientado a result
SCORING_WEIGHTS = {
    "rating": 0.40,           # Calidad de película
    "degree": 0.45,           # Relevancia en grafo
    "genre_bonus": 0.15,      # Coincidencia de género
}

MMR_LAMBDA = 0.70             # Trade-off relevancia vs diversidad


# ============================================================================
# PIPELINE FUNCTIONS
# ============================================================================

def _extract_context(query: str, llm_client: RecommendationLlmClientPort) -> QueryContext:
    """Step 1: Extract context from query using LLM"""
    try:
        return llm_client.extract_query_context(query)
    except Exception as e:
        logger.warning(f"Context extraction failed: {e}, using default context")
        return QueryContext(intent="general")


def _build_rdf_context(context: QueryContext, user_id: str) -> str:
    """Step 2: Build RDF context from extracted context"""
    try:
        turtle_rdf = build_context_triples_turtle(context, user_id)
        return turtle_rdf
    except Exception as e:
        logger.warning(f"RDF context build failed: {e}")
        return ""


def _build_sparql_queries(context: QueryContext) -> list[str]:
    """Step 3: Build SPARQL queries from context"""
    try:
        queries = build_cross_ontology_sparql(context)
        return queries if queries else ["SELECT ?movie ?title ?score WHERE { ?movie ?p ?title . }"]
    except Exception as e:
        logger.warning(f"SPARQL build failed: {e}")
        return ["SELECT ?movie ?title ?score WHERE { ?movie ?p ?title . }"]


def _execute_sparql(
    queries: list[str],
    rdf_context: str,
    snapshot_id: Optional[str] = None,
) -> tuple[list[dict], str, bool]:
    """Step 4: Execute SPARQL queries with fallback strategy"""
    
    if rdf_context and snapshot_id:
        try:
            inject_context_snapshot(rdf_context, snapshot_id)
        except Exception as e:
            logger.warning(f"Failed to inject RDF context: {e}")

    results = []
    fallback_used = False
    executed_query = ""

    for idx, query in enumerate(queries):
        try:
            results = execute_select_query(query)
            executed_query = query
            logger.info(f"Query {idx} succeeded, got {len(results)} results")
            break
        except FusekiQueryError as e:
            logger.warning(f"Query {idx} failed: {e}")
            if idx == len(queries) - 1:
                fallback_used = True
                logger.info("All queries failed, returning empty results")
        except Exception as e:
            logger.error(f"Unexpected error in SPARQL execution: {e}")
            if idx == len(queries) - 1:
                fallback_used = True

    # Cleanup
    if snapshot_id:
        try:
            delete_context_snapshot(snapshot_id)
        except:
            pass

    return results, executed_query, fallback_used


def _score_movies(
    results: list[dict],
    context: QueryContext,
    user_favorites: set[str],
) -> list[MovieRecommendation]:
    """Step 5: Score and rank movies"""
    
    movies = []
    
    for row in results:
        try:
            movie_uri = row.get("movie", "")
            title = row.get("title", "Unknown")
            rating = float(row.get("rating", 0.0)) if row.get("rating") else 0.0
            degree = float(row.get("degree", 1.0)) if row.get("degree") else 1.0
            genres = row.get("genres", "").split("|") if row.get("genres") else []
            year = int(row.get("year", 0)) if row.get("year") else None
            runtime = int(row.get("runtime", 0)) if row.get("runtime") else None
            poster_url = row.get("posterUrl")

            # Simple scoring: rating * 0.40 + normalized_degree * 0.45 + genre_match * 0.15
            score = 0.0
            
            # Rating component (0-10 -> 0-1)
            rating_score = min(rating / 10.0, 1.0)
            score += rating_score * SCORING_WEIGHTS["rating"]
            
            # Degree component (normalized log scale)
            degree_normalized = min(math.log1p(degree) / math.log1p(100), 1.0)
            score += degree_normalized * SCORING_WEIGHTS["degree"]
            
            # Genre bonus if context has genre preferences
            if context.genres and genres:
                genre_match = len(set(context.genres) & set(genres)) / max(len(context.genres), 1)
                score += genre_match * SCORING_WEIGHTS["genre_bonus"]
            
            # Favorite bonus
            if movie_uri in user_favorites:
                score += 0.2

            movies.append(
                MovieRecommendation(
                    movieUri=movie_uri,
                    title=title,
                    score=score,
                    genres=genres,
                    rating=rating if rating > 0 else None,
                    year=year,
                    runtime=runtime,
                    posterUrl=poster_url,
                )
            )
        except Exception as e:
            logger.warning(f"Error scoring movie {row}: {e}")
            continue

    # Sort by score descending
    movies.sort(key=lambda x: x.score, reverse=True)
    
    # Apply MMR for diversity (simple implementation)
    selected = _apply_mmr(movies, int(len(movies) * 0.2) + 1)
    
    # Return top 5
    return selected[:5]


def _apply_mmr(
    movies: list[MovieRecommendation],
    num_results: int = 5,
) -> list[MovieRecommendation]:
    """Apply Maximum Marginal Relevance for diversity"""
    if len(movies) <= num_results:
        return movies

    selected = [movies[0]]
    candidates = movies[1:]

    while len(selected) < num_results and candidates:
        best_idx = 0
        best_score = -1.0

        for idx, candidate in enumerate(candidates):
            # Relevance term
            relevance = candidate.score
            
            # Diversity term: distance to already selected
            diversity = 1.0
            for sel_movie in selected:
                if _movies_similar(candidate, sel_movie):
                    diversity -= 0.5

            # MMR score
            mmr_score = MMR_LAMBDA * relevance + (1 - MMR_LAMBDA) * max(diversity, 0)
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(candidates.pop(best_idx))

    return selected


def _movies_similar(movie1: MovieRecommendation, movie2: MovieRecommendation) -> bool:
    """Check if two movies are similar (same genres)"""
    if not movie1.genres or not movie2.genres:
        return False
    return bool(set(movie1.genres) & set(movie2.genres))


def _generate_explanation(
    query: str,
    movies: list[MovieRecommendation],
    context: QueryContext,
    llm_client: RecommendationLlmClientPort,
) -> str:
    """Step 6: Generate natural language explanation"""
    
    try:
        movies_summary = ", ".join([f"{m.title} ({m.score:.2f})" for m in movies[:3]])
        context_summary = f"Intent: {context.intent}, Genres: {', '.join(context.genres) if context.genres else 'any'}"
        
        explanation = llm_client.generate_recommendation_explanation(
            query=query,
            context_summary=context_summary,
            movies_with_scores=[{"title": m.title, "score": m.score} for m in movies],
            semantic_hint=context.intent,
        )
        return explanation
    except Exception as e:
        logger.warning(f"Explanation generation failed: {e}")
        return f"Found {len(movies)} movies matching your criteria."


# ============================================================================
# MAIN USE CASE
# ============================================================================

class RecommendationUseCase:
    """Simplified recommendation use case with clean pipeline"""

    def __init__(
        self,
        favorites_use_case: UserFavoritesUseCase,
        history_use_case: QueryHistoryUseCase,
        llm_client: RecommendationLlmClientPort,
    ) -> None:
        self.favorites_use_case = favorites_use_case
        self.history_use_case = history_use_case
        self.llm_client = llm_client

    def get_recommendation(self, query: str, user_id: str) -> dict[str, Any]:
        """Get recommendation without debug info"""
        result = self._build_recommendation(query, user_id)
        return result.to_dict()

    def get_recommendation_debug(self, query: str, user_id: str) -> dict[str, Any]:
        """Get recommendation with full debug info"""
        result = self._build_recommendation(query, user_id, debug=True)
        debug_dict = result.to_dict()
        if result.debugInfo:
            debug_dict["debugPayload"] = {
                "contextExtracted": result.debugInfo.contextExtracted,
                "rdfGenerated": result.debugInfo.rdfGenerated,
                "sparqlQuery": result.debugInfo.sparqlQuery,
                "fusekiResultsCount": result.debugInfo.fusekiResultsCount,
                "executionTimeMs": result.debugInfo.executionTimeMs,
                "fallbackUsed": result.debugInfo.fallbackUsed,
                "strategy": result.debugInfo.strategy,
            }
        return debug_dict

    async def get_activity_recommendation(self, user_id: str) -> dict[str, Any]:
        """Get recommendation based on recent user activity"""
        try:
            # Get recent history
            history = await asyncio.to_thread(
                self.history_use_case.find_by_user,
                user_id,
                5,
            )
            
            if not history:
                # Fallback to generic recommendation
                return self.get_recommendation("Quiero una película interesante", user_id)
            
            # Build query from recent history
            recent_queries = [h.query for h in history[-3:]]
            combined_query = f"Basándome en mi historial: {', '.join(recent_queries)}, recomiéndame algo similar"
            
            return self.get_recommendation(combined_query, user_id)
        except Exception as e:
            logger.error(f"Activity recommendation failed: {e}")
            return self.get_recommendation("Quiero una película interesante", user_id)

    def _build_recommendation(
        self,
        query: str,
        user_id: str,
        debug: bool = False,
    ) -> RecommendationResult:
        """Internal pipeline: query -> context -> sparql -> score -> response"""
        
        start_time = perf_counter()
        snapshot_id = str(uuid4())[:8]

        try:
            # Step 1: Extract context
            context = _extract_context(query, self.llm_client)

            # Step 2: Build RDF
            rdf_context = _build_rdf_context(context, user_id)

            # Step 3: Build SPARQL
            sparql_queries = _build_sparql_queries(context)

            # Step 4: Execute SPARQL
            fuseki_results, executed_query, fallback_used = _execute_sparql(
                sparql_queries,
                rdf_context,
                snapshot_id,
            )

            # Step 5: Get user favorites
            try:
                favorites = self.favorites_use_case.get_favorites(user_id)
                favorite_uris = {f.movieUri for f in favorites}
            except:
                favorite_uris = set()

            # Step 6: Score movies
            scored_movies = _score_movies(fuseki_results, context, favorite_uris)

            # Step 7: Generate explanation
            explanation = _generate_explanation(
                query,
                scored_movies,
                context,
                self.llm_client,
            )

            # Step 8: Save to history
            try:
                self.history_use_case.create_entry(
                    query=query,
                    user_id=user_id,
                    context_extracted=context.dict() if hasattr(context, 'dict') else {},
                    rdf_generated=rdf_context,
                    sparql_executed=executed_query,
                    results_found=[
                        {
                            "title": m.title,
                            "score": m.score,
                            "genres": m.genres,
                        }
                        for m in scored_movies
                    ],
                    explanation=explanation,
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                    was_successful=True,
                )
            except Exception as e:
                logger.warning(f"Failed to save history: {e}")

            # Build result
            context_dict = context.dict() if hasattr(context, 'dict') else {}
            
            result = RecommendationResult(
                query=query,
                moviesWithScores=scored_movies,
                explanation=explanation,
                totalMoviesFound=len(fuseki_results),
                executionTimeMs=int((perf_counter() - start_time) * 1000),
                contextExtracted=context_dict,
                rdfGenerated=rdf_context,
                sparqlQuery=executed_query,
            )

            if debug:
                result.debugInfo = DebugInfo(
                    contextExtracted=context_dict,
                    rdfGenerated=rdf_context,
                    sparqlQuery=executed_query,
                    fusekiResultsCount=len(fuseki_results),
                    executionTimeMs=int((perf_counter() - start_time) * 1000),
                    fallbackUsed=fallback_used,
                )

            return result

        except Exception as e:
            logger.error(f"Recommendation pipeline failed: {e}", exc_info=True)
            
            # Minimal fallback response
            return RecommendationResult(
                query=query,
                moviesWithScores=[],
                explanation=f"Error generating recommendation: {str(e)}",
                totalMoviesFound=0,
                executionTimeMs=int((perf_counter() - start_time) * 1000),
                contextExtracted={},
                rdfGenerated="",
                sparqlQuery="",
            )
