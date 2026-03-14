from __future__ import annotations

import json
import re
from urllib import error, request

from pydantic import BaseModel, Field

from app.core.config import settings


# ---------------------------------------------------------------------------
# Structured NLU context model
# ---------------------------------------------------------------------------


class QueryContext(BaseModel):
    """Typed context extracted from a user query, produced by LLM or keyword fallback."""

    intent: str = "general"
    mood: str | None = None
    social_context: dict | None = None
    """e.g. {"companionType": "friends", "hasChildren": False, "numberOfPeople": 3}"""
    genres: list[str] = Field(default_factory=list)
    director_hint: str | None = None
    year_range: list[int] | None = None  # [min_year, max_year]
    runtime_max: int | None = None
    exclusions: list[str] = Field(default_factory=list)


def _keyword_extract_context(query_lower: str) -> QueryContext:
    """Synchronous keyword-based parser — identical to the original if/else logic."""
    social_context = None
    if any(token in query_lower for token in ["amigos", "friends", "grupo"]):
        social_context = {"companionType": "friends", "hasChildren": False, "numberOfPeople": 3}
    elif any(token in query_lower for token in ["pareja", "novia", "novio"]):
        social_context = {"companionType": "partner", "hasChildren": False, "numberOfPeople": 2}
    elif any(token in query_lower for token in ["familia", "ninos", "niños", "hijos"]):
        social_context = {"companionType": "family", "hasChildren": True, "numberOfPeople": 4}

    mood = None
    if any(token in query_lower for token in ["relaj", "tranquil", "liger", "calm"]):
        mood = "relaxed"
    elif any(token in query_lower for token in ["accion", "acción", "emocion", "intensa"]):
        mood = "excited"
    elif any(token in query_lower for token in ["triste", "sad"]):
        mood = "sad"
    elif any(token in query_lower for token in ["feliz", "happy", "alegre"]):
        mood = "happy"

    runtime_max = None
    for minutes in [60, 75, 90, 100, 120, 150]:
        if str(minutes) in query_lower:
            runtime_max = minutes
            break

    range_match = re.search(r"(19\d{2}|20\d{2})\D+(19\d{2}|20\d{2})", query_lower)
    year_range = None
    if range_match:
        start_year = int(range_match.group(1))
        end_year = int(range_match.group(2))
        year_range = [min(start_year, end_year), max(start_year, end_year)]

    exclusions: list[str] = []
    for marker in ["sin ", "excepto ", "excluding "]:
        if marker in query_lower:
            tail = query_lower.split(marker, 1)[1].split(".", 1)[0].strip()
            if tail:
                exclusions.append(tail)

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

    return QueryContext(
        intent="general",
        mood=mood,
        social_context=social_context,
        genres=preferred_genres,
        year_range=year_range,
        runtime_max=runtime_max,
        exclusions=exclusions,
    )


_NLU_SYSTEM_PROMPT = (
    "Eres un analizador de intención para un sistema de recomendación de películas. "
    "Analiza la consulta del usuario y devuelve SOLO un objeto JSON con esta estructura exacta:\n"
    "{\n"
    '  "intent": "general|action|romance|horror|comedy|family|scifi|thriller|drama",\n'
    '  "mood": null | "relaxed|excited|sad|happy|neutral",\n'
    '  "social_context": null | {"companionType": "solo|partner|friends|family", '
    '"hasChildren": bool, "numberOfPeople": int},\n'
    '  "genres": ["Action","Drama","Comedy","Romance","Horror","Family",'
    '"Animation","Science Fiction","Thriller"],\n'
    '  "director_hint": null | "string",\n'
    '  "year_range": null | [min_year_int, max_year_int],\n'
    '  "runtime_max": null | int,\n'
    '  "exclusions": []\n'
    "}\n"
    "Responde SOLO con el JSON, sin texto adicional."
)


def extract_query_context(query: str) -> QueryContext:
    """Extract structured NLU context from a query using the LLM.

    Falls back to :func:`_keyword_extract_context` if the API key is missing,
    the request times out, or the response cannot be parsed.
    """
    api_key = settings.groq_api_key
    query_lower = query.lower()

    if not api_key:
        return _keyword_extract_context(query_lower)

    payload = {
        "model": settings.groq_model,
        "temperature": 0.1,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _NLU_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
    }

    req = request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
            choices = body.get("choices", [])
            if not choices:
                return _keyword_extract_context(query_lower)
            content = choices[0].get("message", {}).get("content", "").strip()
            if not content:
                return _keyword_extract_context(query_lower)
            if content.startswith("```"):
                content = content.strip("`")
                if content.lower().startswith("json"):
                    content = content[4:].strip()
            data = json.loads(content)
            return QueryContext.model_validate(data)
    except Exception:
        return _keyword_extract_context(query_lower)


def _build_prompt(
    query: str,
    context_summary: str,
    movies_with_scores: list[dict],
) -> str:
    if not movies_with_scores:
        return (
            "Eres un asistente de recomendacion de peliculas. "
            "Responde en espanol en 2-3 frases, explica por que no hay recomendaciones "
            "y sugiere agregar favoritos o hacer una consulta mas especifica.\n\n"
            f"Consulta: {query}\n"
            f"Contexto inferido: {context_summary}"
        )

    top = [
        f"- {movie.get('title')} (score={movie.get('compatibilityScore')}, genero={movie.get('genreName')})"
        for movie in movies_with_scores[:5]
    ]
    top_text = "\n".join(top)
    return (
        "Eres un asistente de recomendacion de peliculas. "
        "Responde en espanol en maximo 4 frases. "
        "Explica por que estas opciones son relevantes para la consulta y el contexto.\n\n"
        f"Consulta: {query}\n"
        f"Contexto inferido: {context_summary}\n"
        f"Top recomendaciones:\n{top_text}"
    )


def _fallback_explanation(query: str, context_summary: str, movies_with_scores: list[dict]) -> str:
    if not movies_with_scores:
        return (
            "Aun no tengo suficientes senales para recomendarte peliculas. "
            "Agrega favoritos y vuelve a intentar. "
            f"Consulta recibida: '{query}'."
        )

    titles = ", ".join(movie.get("title", "") for movie in movies_with_scores[:3])
    return (
        "Prepare recomendaciones basadas en tu consulta y tus senales actuales. "
        f"Las opciones mas fuertes son: {titles}. "
        f"Contexto detectado: {context_summary}."
    )


def generate_recommendation_explanation(
    query: str,
    context_summary: str,
    movies_with_scores: list[dict],
) -> str:
    api_key = settings.groq_api_key
    if not api_key:
        return _fallback_explanation(query, context_summary, movies_with_scores)

    prompt = _build_prompt(query, context_summary, movies_with_scores)
    payload = {
        "model": settings.groq_model,
        "temperature": 0.4,
        "max_tokens": 220,
        "messages": [
            {
                "role": "system",
                "content": "Eres un recomendador de peliculas claro, util y breve.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    req = request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
            choices = body.get("choices", [])
            if not choices:
                return _fallback_explanation(query, context_summary, movies_with_scores)
            content = choices[0].get("message", {}).get("content", "").strip()
            return content or _fallback_explanation(query, context_summary, movies_with_scores)
    except (error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
        return _fallback_explanation(query, context_summary, movies_with_scores)
