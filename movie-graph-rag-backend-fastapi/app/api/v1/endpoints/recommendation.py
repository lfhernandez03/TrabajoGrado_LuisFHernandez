from dataclasses import replace
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from time import perf_counter

from app.api.di import (
    get_current_user_di as get_current_user,
    get_recommendation_use_case_di as get_recommendation_use_case,
    get_user_favorites_use_case_di,
)
from app.api.di.movies_di import get_chat_use_case_di
from app.api.schemas.recommendation import (
    ChatMovieResponse,
    ChatRequest,
    ChatResponse,
    MetricsReportRequest,
    MetricsReportQueryResult,
    MetricsReportResponse,
    MetricsReportSummary,
    RecommendationDebugResponse,
    RecommendationMetricsResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.application.use_cases.recommendation import RecommendationUseCase
from app.application.use_cases.recommendation.chat_use_case import ChatUseCase
from app.application.use_cases.users import UserFavoritesUseCase
from app.core.fuseki_client import ping_fuseki
from app.core.profile_service import ProfileService
from app.domain.entities.auth_user import AuthUser

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("", response_model=RecommendationResponse)
def get_recommendation_get(
    query: str = Query(..., min_length=1),
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
    favorites_use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case_di),
) -> RecommendationResponse:
    fav_titles = {f.title for f in favorites_use_case.get_my_favorites(current_user.id) if f.title}
    return RecommendationResponse(**use_case.get_recommendation(query, current_user.id, excluded_titles=fav_titles))


@router.post("", response_model=RecommendationResponse)
def get_recommendation_post(
    payload: RecommendationRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
    favorites_use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case_di),
) -> RecommendationResponse:
    fav_titles = {f.title for f in favorites_use_case.get_my_favorites(current_user.id) if f.title}
    return RecommendationResponse(
        **use_case.get_recommendation(payload.query, current_user.id, excluded_titles=fav_titles)
    )


@router.get("/activity", response_model=RecommendationResponse)
async def get_activity_recommendation(
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
    favorites_use_case: UserFavoritesUseCase = Depends(get_user_favorites_use_case_di),
) -> RecommendationResponse:
    """Inteligent activity recommendation based on user's profile, favorites, and topological exploration.
    
    Combines:
    - Time-of-day context (morning, afternoon, evening, night)
    - Favorite genres with weights
    - Dominant clusters and exploration index
    - Temporal trends (specializing vs diversifying)
    """
    profile_service = ProfileService()
    
    # Get user's favorites
    favorites = favorites_use_case.get_my_favorites(current_user.id)
    
    # Get topological profile
    topo_profile = profile_service.get_topological_profile(current_user.id, favorites)
    
    # Get basic user profile for genre weights and moods, then enrich with favorites
    basic_profile = profile_service.get(current_user.id)
    genre_weights = ProfileService.build_genre_weights(favorites)
    if genre_weights:
        basic_profile = replace(basic_profile, genre_weights=genre_weights)
    
    # Build time-of-day context
    hour = datetime.now().hour
    if 6 <= hour < 12:
        time_context = "morning"
    elif 12 <= hour < 18:
        time_context = "afternoon"
    else:
        time_context = "evening"

    # Build intelligent query components
    query_parts = [f"Recommend me a movie to watch in the {time_context}"]
    
    # 1. Add favorite genres if not cold start
    if basic_profile and basic_profile.genre_weights and not basic_profile.is_cold_start:
        top_genres = sorted(basic_profile.genre_weights.items(), key=lambda x: x[1], reverse=True)[:2]
        if top_genres:
            genre_names = [g[0] for g in top_genres]
            query_parts.append(f"that is {' or '.join(genre_names)}")
    
    # 2. Add dominant clusters context if available
    if topo_profile and getattr(topo_profile, 'dominantClusters', None):
        top_clusters = topo_profile.dominantClusters[:2]
        cluster_names = [c.label for c in top_clusters if hasattr(c, 'label')]
        if cluster_names:
            query_parts.append(f"type of {' or '.join(cluster_names)}")
    
    # 3. Add exploration insight
    if topo_profile:
        exploration_idx = getattr(topo_profile, 'explorationIndex', 0.5)
        if exploration_idx > 0.7:
            # Explorer: suggest new clusters
            query_parts.append("but from a new genre or cluster I haven't seen much of")
        elif exploration_idx < 0.3:
            # Specialist: deepen expertise
            temporal_trend = getattr(topo_profile, 'temporalTrend', None)
            if temporal_trend == "specializing":
                query_parts.append("that deepens my favorite genres")

        # Add temporal context if available
        temporal_trend = getattr(topo_profile, 'temporalTrend', None)
        if temporal_trend == "diversifying":
            query_parts.append("wanting to explore new areas")
    
    # 4. Add mood context if available
    if basic_profile and getattr(basic_profile, 'dominant_mood', None):
        query_parts.append(f"with a {basic_profile.dominant_mood} atmosphere")
    
    # 5. Add social context if the user prefers watching with others
    companion = getattr(basic_profile, 'dominant_companion', None) if basic_profile else None
    if companion and companion != "alone":
        query_parts.append(f"to watch with {companion}")
    
    # 6. If user has recent favorites, suggest similar movies
    try:
        if favorites:
            recent_favorite = max(favorites, key=lambda f: getattr(f, 'addedAt', datetime.min))
            recent_title = getattr(recent_favorite, 'title', '')
            if recent_title:
                query_parts.append(f"similar to '{recent_title}' that I liked recently")
    except Exception:
        # If there's any error getting favorites, just skip this part
        pass
    
    # Combine all components into final query
    query = " ".join(query_parts)

    # Exclude favorites so the hero card never shows something the user already saved
    fav_titles = {f.title for f in favorites if f.title}

    # Delegate to main recommendation pipeline — activity hero needs exactly 1 movie
    return RecommendationResponse(**use_case.get_recommendation(query, current_user.id, n=1, query_type_override="activity", excluded_titles=fav_titles))


@router.post("/debug", response_model=RecommendationDebugResponse)
def get_recommendation_debug(
    payload: RecommendationRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
) -> RecommendationDebugResponse:
    return RecommendationDebugResponse(
        **use_case.get_recommendation_debug(payload.query, current_user.id)
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: ChatUseCase = Depends(get_chat_use_case_di),
) -> ChatResponse:
    """Conversational recommendation endpoint.

    Accepts the full message history for a session and returns fresh
    recommendations based on the accumulated context across all turns.
    """
    result = use_case.execute(
        session_id=payload.session_id,
        messages=[m.model_dump() for m in payload.messages],
        user_id=current_user.id,
    )

    movies = [
        ChatMovieResponse(
            title=m.title,
            posterUrl=m.poster_url,
            runtime=m.runtime,
            genreName=m.genre,
            releaseDate=m.release_year,
            averageRating=m.rating,
            compatibilityScore=m.compatibility_score,
            moodMatchScore=m.mood_match_score,
            socialMatchScore=m.social_match_score,
            energyMatchScore=m.energy_match_score,
            timeMatchScore=m.time_match_score,
            kidFriendly=m.kid_friendly,
        )
        for m in result.movies
    ]

    ctx_dict = {
        "mood": result.context.mood,
        "companion": result.context.companion,
        "has_children": result.context.has_children,
        "energy": result.context.energy,
        "genres": result.context.genres,
        "runtime_max": result.context.runtime_max,
        "exclusions": result.context.exclusions,
        "confidence": result.context.confidence,
        "time_of_day": result.context.time_of_day,
        "children_age_hint": result.context.children_age_hint,
    }

    metrics_response = None
    if result.metrics is not None:
        metrics_response = RecommendationMetricsResponse(
            ild=result.metrics.ild,
            graphDiversityScore=result.metrics.graph_diversity_score,
            semanticPrecision=result.metrics.semantic_precision,
            coldStartThreshold=result.metrics.cold_start_threshold,
            movieCount=result.metrics.movie_count,
            novelty=result.metrics.novelty,
            ontoRecall=result.metrics.onto_recall,
        )

    return ChatResponse(
        session_id=result.session_id,
        movies=movies,
        explanation=result.explanation,
        strategy_used=result.strategy_used,
        sparql_query=result.sparql_query,
        context_extracted=ctx_dict,
        execution_ms=result.execution_ms,
        turn_count=len([m for m in payload.messages if m.role == "user"]),
        metrics=metrics_response,
    )


@router.post("/metrics-report", response_model=MetricsReportResponse)
def get_metrics_report(
    payload: MetricsReportRequest,
    current_user: AuthUser = Depends(get_current_user),
    use_case: RecommendationUseCase = Depends(get_recommendation_use_case),
) -> MetricsReportResponse:
    """Batch evaluation endpoint for thesis quality metrics.

    Runs each query through the full recommendation pipeline using a neutral
    cold-start profile so results are reproducible regardless of who calls it.
    Returns 503 if Fuseki is unreachable.
    """
    if not ping_fuseki():
        raise HTTPException(
            status_code=503,
            detail="Fuseki is not reachable. Start Apache Jena Fuseki and load the dataset before running the metrics report.",
        )

    results: list[MetricsReportQueryResult] = []

    for query in payload.queries:
        t0 = perf_counter()
        try:
            raw = use_case.get_recommendation(query, "__metrics_eval__")
            m = raw.get("metrics", {})
            results.append(MetricsReportQueryResult(
                query=query,
                ild=m.get("ild", 0.0),
                graphDiversityScore=m.get("graphDiversityScore", 0.0),
                semanticPrecision=m.get("semanticPrecision", 0.0),
                novelty=m.get("novelty", 0.5),
                ontoRecall=m.get("ontoRecall", 1.0),
                coldStartThreshold=m.get("coldStartThreshold", 5),
                movieCount=m.get("movieCount", 0),
                strategy=raw.get("strategyUsed", ""),
                isColdStart=raw.get("isColdStart", False),
                executionMs=int((perf_counter() - t0) * 1000),
                movies=[mv["title"] for mv in raw.get("moviesWithScores", []) if mv.get("title")],
            ))
        except Exception:
            results.append(MetricsReportQueryResult(
                query=query,
                ild=0.0, graphDiversityScore=0.0, semanticPrecision=0.0,
                novelty=0.0, ontoRecall=0.0, coldStartThreshold=5, movieCount=0,
                strategy="error", isColdStart=False,
                executionMs=int((perf_counter() - t0) * 1000),
                movies=[],
            ))

    valid = [r for r in results if r.strategy != "error"]
    count = len(valid) or 1

    summary = MetricsReportSummary(
        queriesEvaluated=len(results),
        avgILD=round(sum(r.ild for r in valid) / count, 4),
        avgGraphDiversity=round(sum(r.graphDiversityScore for r in valid) / count, 4),
        avgSemanticPrecision=round(sum(r.semanticPrecision for r in valid) / count, 4),
        avgNovelty=round(sum(r.novelty for r in valid) / count, 4),
        avgOntoRecall=round(sum(r.ontoRecall for r in valid) / count, 4),
        minILD=round(min((r.ild for r in valid), default=0.0), 4),
        maxILD=round(max((r.ild for r in valid), default=0.0), 4),
        coldStartDetections=sum(1 for r in valid if r.isColdStart),
    )

    return MetricsReportResponse(summary=summary, perQuery=results)
