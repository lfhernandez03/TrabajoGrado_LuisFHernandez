from __future__ import annotations

from datetime import datetime


def build_context_summary(
    *,
    social_context: dict | None,
    emotional_context: dict | None,
    requirement_context: dict | None,
) -> str:
    context_summary_parts: list[str] = []
    if social_context:
        context_summary_parts.append(f"social={social_context['companionType']}")
    if emotional_context:
        context_summary_parts.append(f"mood={emotional_context['moodDescription']}")
    if requirement_context and requirement_context.get("availableTime"):
        context_summary_parts.append(f"availableTime={requirement_context['availableTime']}")
    return ", ".join(context_summary_parts) if context_summary_parts else "general"


def build_context_extracted(
    *,
    snapshot_id: str,
    request_timestamp: datetime,
    user_intent: str,
    social_context: dict | None,
    emotional_context: dict | None,
    requirement_context: dict | None,
) -> dict:
    return {
        "snapshotID": snapshot_id,
        "requestTimestamp": request_timestamp,
        "userIntent": user_intent,
        "hourOfDay": request_timestamp.hour,
        "dayOfWeek": request_timestamp.strftime("%A"),
        "socialContext": social_context,
        "emotionalContext": emotional_context,
        "requirementContext": requirement_context,
    }


def build_recommendation_response(
    *,
    query: str,
    context_extracted: dict,
    rdf_generated: str,
    sparql_query: str,
    movies_with_scores: list[dict],
    explanation: str,
    execution_time_ms: int,
    semantic_explanation: str = "",
) -> dict:
    return {
        "query": query,
        "contextExtracted": context_extracted,
        "rdfGenerated": rdf_generated,
        "sparqlQuery": sparql_query,
        "moviesFound": len(movies_with_scores),
        "moviesWithScores": movies_with_scores,
        "explanation": explanation,
        "semanticExplanation": semantic_explanation,
        "executionTimeMs": execution_time_ms,
    }


def build_debug_payload(
    *,
    recommendation_source: str,
    fuseki_rows_count: int,
    debug_errors: list[str],
    timings: dict[str, int],
    ontology_navigation_used: bool = False,
    context_graph_injected: bool = False,
) -> dict:
    _non_fallback_prefixes = ("fuseki", "ontology")
    return {
        "source": recommendation_source,
        "fusekiRows": fuseki_rows_count,
        "fallbackUsed": not any(
            recommendation_source.startswith(p) for p in _non_fallback_prefixes
        ),
        "errors": debug_errors,
        "timingsMs": timings,
        "ontologyNavigationUsed": ontology_navigation_used,
        "contextGraphInjected": context_graph_injected,
    }
