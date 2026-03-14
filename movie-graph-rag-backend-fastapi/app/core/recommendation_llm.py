from __future__ import annotations

import json
from urllib import error, request

from app.core.config import settings


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
