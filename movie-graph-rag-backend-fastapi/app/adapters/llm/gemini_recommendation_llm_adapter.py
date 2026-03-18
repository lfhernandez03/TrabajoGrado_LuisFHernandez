from __future__ import annotations

import json
import logging
import re

try:
    from google import genai
except ImportError:
    genai = None

from app.core.config import settings
from app.domain.entities.query_context import QueryContext


_NLU_SYSTEM_PROMPT = (
    "Eres un analizador de intención para un sistema de recomendación de películas en español.\n\n"
    "EJEMPLOS:\n"
    'Consulta: "estoy agotado del trabajo, algo cortito para relajarme"\n'
    'Respuesta: {"intent": "general", "mood": "relaxed", "social_context": null, "genres": [], "director_hint": null, "year_range": null, "runtime_max": 90, "exclusions": []}\n\n'
    'Consulta: "somos 6 amigos, viernes por la noche, algo divertido"\n'
    'Respuesta: {"intent": "comedy", "mood": "excited", "social_context": {"companionType": "friends", "hasChildren": false, "numberOfPeople": 6}, "genres": ["Comedy"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Consulta: "algo para ver con mis hijos pequeños esta tarde"\n'
    'Respuesta: {"intent": "family", "mood": "happy", "social_context": {"companionType": "family", "hasChildren": true, "numberOfPeople": 4}, "genres": ["Animation", "Family"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Consulta: "quiero llorar con algo, nada de acción"\n'
    'Respuesta: {"intent": "drama", "mood": "sad", "social_context": null, "genres": ["Drama", "Romance"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": ["Action"]}\n\n'
    'Consulta: "película romántica para ver con mi pareja, algo de los 90"\n'
    'Respuesta: {"intent": "romance", "mood": "romantic", "social_context": {"companionType": "partner", "hasChildren": false, "numberOfPeople": 2}, "genres": ["Romance"], "director_hint": null, "year_range": [1990, 1999], "runtime_max": null, "exclusions": []}\n\n'
    'Consulta: "algo de Nolan, ciencia ficción intensa"\n'
    'Respuesta: {"intent": "scifi", "mood": "excited", "social_context": null, "genres": ["Science Fiction"], "director_hint": "Christopher Nolan", "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Consulta: "tengo una hora, algo ligero que no me haga pensar"\n'
    'Respuesta: {"intent": "general", "mood": "relaxed", "social_context": null, "genres": ["Comedy"], "director_hint": null, "year_range": null, "runtime_max": 60, "exclusions": []}\n\n'
    'Consulta: "quiero aventura, adrenalina, algo épico"\n'
    'Respuesta: {"intent": "action", "mood": "adventurous", "social_context": null, "genres": ["Action", "Adventure"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    "REGLAS:\n"
    "- mood: elige el valor más cercano del enum. NUNCA devuelvas un valor fuera del enum. Si no hay señal emocional clara, usa null.\n"
    "- Si el usuario menciona un director o actor por nombre, extráelo en director_hint.\n"
    "- \"sin X\", \"nada de X\", \"que no sea X\" → agregar X a exclusions.\n"
    "- year_range: solo si el usuario menciona explícitamente una época, década o rango de años.\n"
    "- numberOfPeople: infiere del contexto (\"somos 6\" → 6, \"en pareja\" → 2, \"con mi familia\" → 4, \"con mis hijos\" → 4).\n"
    "- runtime_max: solo para restricciones explícitas. \"algo corto\" → 90. \"tengo una hora\" → 60. \"tengo 90 minutos\" → 90.\n"
    "- Si el usuario menciona un género en español, mapéalo al nombre en inglés del enum.\n"
    "- Responde SOLO con el JSON. Sin texto adicional, sin backticks, sin explicaciones.\n\n"
    "{\n"
    '  "intent": "general|action|romance|horror|comedy|family|scifi|thriller|drama",\n'
    '  "mood": null | "relaxed|excited|sad|happy|neutral|stressed|anxious|bored|curious|romantic|nostalgic|adventurous|nervous",\n'
    '  "social_context": null | {"companionType": "solo|partner|friends|family", '
    '"hasChildren": bool, "numberOfPeople": int},\n'
    '  "genres": ["Action","Drama","Comedy","Romance","Horror","Family",'
    '"Animation","Science Fiction","Thriller"],\n'
    '  "director_hint": null | "string",\n'
    '  "year_range": null | [min_year_int, max_year_int],\n'
    '  "runtime_max": null | int,\n'
    '  "exclusions": []\n'
    "}"
)


QUERY_TYPE_INSTRUCTIONS: dict[str, str] = {
    "general": (
        "Explica en máximo 4 frases por qué estas películas encajan con lo que el usuario busca. "
        "Sé específico sobre el tono y estilo de cada recomendación."
    ),
    "activity": (
        "El usuario recibió estas recomendaciones basadas en su actividad reciente. "
        "Explica en 3 frases qué preferencias de sus búsquedas anteriores se reflejan en estas sugerencias. "
        "Menciona géneros o estilos que el usuario ha explorado."
    ),
    "cold_start": (
        "Es la primera vez que el usuario interactúa con el sistema. "
        "Explica en 2 frases por qué estas películas son un buen punto de partida. "
        "Al final, invita al usuario a marcar favoritos para mejorar las próximas recomendaciones."
    ),
    "mood_driven": (
        "El estado emocional del usuario fue la señal principal para esta selección. "
        "Explica en 3 frases cómo el tono, ritmo o temática de estas películas conecta con ese estado de ánimo. "
        "Usa lenguaje empático y directo."
    ),
    "social": (
        "El contexto social fue el factor determinante. "
        "Explica en 3 frases por qué estas películas son adecuadas para el grupo o compañía descrita. "
        "Si hay niños presentes, menciona por qué el contenido es apropiado para ellos."
    ),
}


class GeminiRecommendationLlmAdapter:
    def __init__(self) -> None:
        self._gemini_connection_logged_ok = False

    def _log_gemini_connection_ok(self, operation: str) -> None:
        if self._gemini_connection_logged_ok:
            return
        logging.getLogger("gemini_health").info(
            "[GEMINI CONNECTION] status=ok | operation=%s | model=%s",
            operation,
            settings.gemini_model,
        )
        self._gemini_connection_logged_ok = True

    def _log_gemini_connection_error(self, operation: str, exc: Exception) -> None:
        self._gemini_connection_logged_ok = False
        logging.getLogger("gemini_health").warning(
            "[GEMINI CONNECTION] status=error | operation=%s | model=%s | reason=%s",
            operation,
            settings.gemini_model,
            str(exc)[:200],
        )

    def _get_client(self):
        if genai is None:
            return None
        api_key = settings.gemini_api_key
        if not api_key:
            return None
        return genai.Client(api_key=api_key)

    def _extract_response_text(self, response: object) -> str | None:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None
        first_candidate = candidates[0]
        content = getattr(first_candidate, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if not parts:
            return None
        first_part = parts[0]
        part_text = getattr(first_part, "text", None)
        if isinstance(part_text, str) and part_text.strip():
            return part_text.strip()
        return None

    def _keyword_extract_context(self, query_lower: str) -> QueryContext:
        social_context = None
        if any(token in query_lower for token in ["solo", "sola", "yo solo", "yo sola"]):
            social_context = {"companionType": "alone", "hasChildren": False, "numberOfPeople": 1}
        elif any(token in query_lower for token in ["compañeros", "colegas", "del trabajo"]):
            social_context = {"companionType": "friends", "hasChildren": False, "numberOfPeople": 4}
        elif any(token in query_lower for token in ["amigos", "friends", "grupo"]):
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
        elif any(token in query_lower for token in ["estres", "stress", "agobia", "agotad"]):
            mood = "stressed"
        elif any(token in query_lower for token in ["ansios", "nervios", "angustia"]):
            mood = "anxious"
        elif any(token in query_lower for token in ["aburrid", "bored", "hastio"]):
            mood = "bored"
        elif any(token in query_lower for token in ["nostalgic", "nostálgic", "recuerdo", "añoran"]):
            mood = "nostalgic"
        elif any(token in query_lower for token in ["romantic", "romántic", "amor", "enamorad"]):
            mood = "romantic"
        elif any(token in query_lower for token in ["curiosi", "interesant", "descubr", "explorar"]):
            mood = "curious"
        elif any(token in query_lower for token in ["aventur", "adrenali", "epico", "épico", "accion pura"]):
            mood = "adventurous"
        elif any(token in query_lower for token in ["concentr", "enfoc", "productiv"]):
            mood = "neutral"

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
            "ciencia": "Science Fiction",
            "ciencia ficcion": "Science Fiction",
            "ciencia ficción": "Science Fiction",
            "sci-fi": "Science Fiction",
            "thriller": "Thriller",
            "fantasia": "Fantasy",
            "fantasía": "Fantasy",
            "misterio": "Mystery",
            "aventura": "Adventure",
            "musical": "Musical",
            "western": "Western",
            "crimen": "Crime",
            "guerra": "War",
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

    def extract_query_context(self, query: str) -> QueryContext:
        client = self._get_client()
        query_lower = query.lower()

        if client is None:
            if genai is None:
                logging.getLogger("nlu_debug").debug("[NLU SOURCE] keyword_fallback | reason='google-genai missing'")
            return self._keyword_extract_context(query_lower)

        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=query,
                config=genai.types.GenerateContentConfig(
                    system_instruction=_NLU_SYSTEM_PROMPT,
                    temperature=0.1,
                    max_output_tokens=300,
                    response_mime_type="application/json",
                ),
            )
            self._log_gemini_connection_ok("extract_query_context")
            content = self._extract_response_text(response)
            if not content:
                return self._keyword_extract_context(query_lower)
            if content.startswith("```"):
                content = content.strip("`")
                if content.lower().startswith("json"):
                    content = content[4:].strip()
            data = json.loads(content)
            result = QueryContext.model_validate(data)
            nlu_logger = logging.getLogger("nlu_debug")
            nlu_logger.debug("[NLU SOURCE] gemini_flash_sdk | mood=%r | raw=%r", result.mood, content[:120])
            return result
        except Exception as exc:
            self._log_gemini_connection_error("extract_query_context", exc)
            nlu_logger = logging.getLogger("nlu_debug")
            nlu_logger.debug("[NLU SOURCE] keyword_fallback | reason=%r", str(exc)[:80])
            return self._keyword_extract_context(query_lower)

    def _build_prompt(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
        semantic_hint: str = "",
        query_type: str = "general",
    ) -> str:
        query_type_instruction = QUERY_TYPE_INSTRUCTIONS.get(
            query_type,
            QUERY_TYPE_INSTRUCTIONS["general"],
        )
        semantic_section = (
            f"Contexto ontológico inferido: {semantic_hint}\n\n"
            if semantic_hint
            else ""
        )
        if not movies_with_scores:
            return (
                "Eres un asistente de recomendacion de peliculas. "
                "Responde en espanol en 2-3 frases, explica por que no hay recomendaciones "
                "y sugiere agregar favoritos o hacer una consulta mas especifica.\n\n"
                f"{query_type_instruction}\n\n"
                f"{semantic_section}"
                f"Consulta: {query}\n"
                f"Contexto inferido: {context_summary}"
            )

        top: list[str] = []
        for movie in movies_with_scores[:5]:
            raw_scores = movie.get("semanticScores")
            scores = raw_scores if isinstance(raw_scores, dict) else {}
            hints: list[str] = []
            if scores.get("moodMatchScore") is not None:
                hints.append(f"afinidad_emocional={scores['moodMatchScore']:.1f}")
            if scores.get("socialMatchScore") is not None:
                hints.append(f"afinidad_social={scores['socialMatchScore']:.1f}")
            if scores.get("overallCompatibility") is not None:
                hints.append(f"compatibilidad={scores['overallCompatibility']:.1f}")
            score_detail = ", ".join(hints)
            line = (
                f"- {movie.get('title')} (score={movie.get('compatibilityScore')}, "
                f"genero={movie.get('genreName')}"
            )
            if score_detail:
                line += f", {score_detail}"
            line += ")"
            top.append(line)

        top_text = "\n".join(top)
        return (
            f"{query_type_instruction}\n\n"
            f"{semantic_section}"
            f"Consulta: {query}\n"
            f"Contexto inferido: {context_summary}\n"
            f"Top recomendaciones:\n{top_text}"
        )

    def _fallback_explanation(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
    ) -> str:
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
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
        semantic_hint: str = "",
        query_type: str = "general",
    ) -> str:
        client = self._get_client()
        if client is None:
            if genai is None:
                logging.getLogger("nlu_debug").debug("[LLM SOURCE] fallback_explanation | reason='google-genai missing'")
            return self._fallback_explanation(query, context_summary, movies_with_scores)

        prompt = self._build_prompt(
            query,
            context_summary,
            movies_with_scores,
            semantic_hint,
            query_type,
        )
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=(
                        "Eres un asistente de recomendación de películas. "
                        "Responde siempre en español. "
                        "Sigue exactamente las instrucciones de formato y longitud que recibirás en el mensaje del usuario."
                    ),
                    temperature=0.4,
                    max_output_tokens=220,
                ),
            )
            self._log_gemini_connection_ok("generate_recommendation_explanation")
            content = self._extract_response_text(response)
            if not content:
                return self._fallback_explanation(query, context_summary, movies_with_scores)
            return content or self._fallback_explanation(query, context_summary, movies_with_scores)
        except Exception as exc:
            self._log_gemini_connection_error("generate_recommendation_explanation", exc)
            return self._fallback_explanation(query, context_summary, movies_with_scores)
