from __future__ import annotations

import json
import re
from datetime import datetime

from google import genai

from app.core.config import settings
from app.core.conversation_context import get_time_of_day, infer_children_age_hint
from app.domain.entities.query_context import QueryContext
from app.domain.entities.recommendation_models import UserContext
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort


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
        "Explica detalladamente (5-7 frases) por qué estas películas encajan con lo que el usuario busca. "
        "Sé específico sobre el tono, estilo y elementos que hacen cada película especialmente relevante. "
        "Menciona detalles de la trama o atmósfera que conectan con la búsqueda del usuario."
    ),
    "activity": (
        "El usuario recibió estas recomendaciones basadas en su actividad reciente y preferencias históricas. "
        "Explica detalladamente (5-7 frases) qué patrones en sus búsquedas anteriores se reflejan en estas sugerencias. "
        "Menciona géneros, directores o estilos que el usuario ha explorado y cómo se conectan con estas películas. "
        "Destaca qué hace estas recomendaciones especialmente alineadas con su perfil."
    ),
    "cold_start": (
        "Es la primera vez que el usuario interactúa con el sistema, así que estas recomendaciones están basadas en el contexto de su consulta. "
        "Explica detalladamente (5-7 frases) por qué estas películas son un excelente punto de partida. "
        "Destaca la diversidad en géneros o estilos para ayudarle a explorar. "
        "Invita al usuario a marcar favoritos para mejorar las próximas recomendaciones."
    ),
    "mood_driven": (
        "El estado emocional del usuario fue la señal principal para esta selección. "
        "Explica detalladamente (5-7 frases) cómo el tono, ritmo, temática y atmósfera de estas películas conecta con ese específico estado de ánimo. "
        "Sé concreto: describe escenas o elementos de cada película que generan la emoción deseada. "
        "Usa lenguaje empático y evocador."
    ),
    "social": (
        "El contexto social fue el factor determinante en esta selección. "
        "Explica detalladamente (5-7 frases) por qué estas películas son perfectas para el grupo o compañía descrita. "
        "Si hay niños, explica en detalle el contenido apropiado, temas seguros y por qué es entretenido para todas las edades. "
        "Si es un grupo de amigos o pareja, destaca elementos sociales como humor, drama o romance que hacen la experience compartida."
    ),
}


class GeminiRecommendationLlmAdapter(RecommendationLlmClientPort):
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
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
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
            data = json.loads(response.text)
            return QueryContext.model_validate(data)
        except Exception:
            return self._keyword_extract_context(query.lower())

    def extract_user_context(
        self,
        query: str,
        now: datetime | None = None,
        session_id: str | None = None,
    ) -> UserContext:
        """Call the NLU pipeline and return a UserContext directly.

        Uses the same Gemini prompt as extract_query_context but builds
        UserContext instead of QueryContext, injecting server-clock time_of_day
        and detecting children_age_hint from the raw query text.
        """
        llm_ok = False
        data: dict = {}
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
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
            data = json.loads(response.text)
            llm_ok = True
        except Exception:
            pass

        if llm_ok:
            social = data.get("social_context") or {}
            companion = social.get("companionType")
            has_children = bool(social.get("hasChildren", False))
            return UserContext(
                mood=data.get("mood"),
                companion=companion,
                has_children=has_children,
                energy=None,
                genres=list(data.get("genres") or []),
                runtime_max=data.get("runtime_max"),
                exclusions=list(data.get("exclusions") or []),
                confidence=0.9,
                time_of_day=get_time_of_day(now),
                children_age_hint=infer_children_age_hint(query),
                session_id=session_id,
                raw_query=query,
            )

        # Keyword fallback — build UserContext from keyword extraction
        qctx = self._keyword_extract_context(query.lower())
        social = qctx.social_context or {}
        return UserContext(
            mood=qctx.mood,
            companion=social.get("companionType"),
            has_children=bool(social.get("hasChildren", False)),
            energy=None,
            genres=list(qctx.genres or []),
            runtime_max=qctx.runtime_max,
            exclusions=list(qctx.exclusions or []),
            confidence=0.5,
            time_of_day=get_time_of_day(now),
            children_age_hint=infer_children_age_hint(query),
            session_id=session_id,
            raw_query=query,
        )

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
            hints: list[str] = []
            # Individual semantic scores are top-level fields in to_response_dict()
            mood_score = movie.get("moodMatchScore")
            if mood_score is not None:
                hints.append(f"afinidad_emocional={float(mood_score):.2f}")
            social_score = movie.get("socialMatchScore")
            if social_score is not None:
                hints.append(f"afinidad_social={float(social_score):.2f}")
            energy_score = movie.get("energyMatchScore")
            if energy_score is not None:
                hints.append(f"afinidad_energia={float(energy_score):.2f}")
            # overallCompatibility lives inside semanticScores
            overall = (movie.get("semanticScores") or {}).get("overallCompatibility")
            if overall is not None:
                hints.append(f"compatibilidad_general={float(overall):.2f}")
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
                "Lamentablemente, no encontré películas que coincidan exactamente con tu búsqueda en este momento. "
                f"Tu consulta fue: '{query}'. "
                "Te sugiero marcar algunas películas como favoritas para que el sistema aprenda mejor tus preferencias, "
                "o intenta con una búsqueda más general. "
                "Vuelve a intentar después de agregar favoritos para obtener recomendaciones más personalizadas."
            )

        titles_with_genres = []
        for movie in movies_with_scores[:5]:
            title = movie.get("title", "Sin título")
            genre = movie.get("genreName", "")
            year = movie.get("releaseDate", "")
            if genre:
                titles_with_genres.append(f"{title} ({genre}, {year})")
            else:
                titles_with_genres.append(f"{title}")
        
        titles_str = ", ".join(titles_with_genres)
        return (
            f"Basándome en tu consulta '{query}', preparé estas recomendaciones: {titles_str}. "
            f"Estas películas se alinean con el contexto que detecté ({context_summary}). "
            "Cada una ofrece una experiencia única: unas son más relajantes, otras más emocionantes, "
            "y todas han sido seleccionadas porque encajan con lo que buscas. "
            "Si alguna te gusta, márcala como favorita para mejorar futuras recomendaciones."
        )

    def generate_recommendation_explanation(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
        semantic_hint: str = "",
        query_type: str = "general",
    ) -> str:
        try:
            prompt = self._build_prompt(
                query,
                context_summary,
                movies_with_scores,
                semantic_hint,
                query_type,
            )
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=(
                        "Eres un experto asistente de recomendación de películas con profundo conocimiento de cine. "
                        "Tu tarea es explicar por qué las películas recomendadas son perfectas para el usuario. "
                        "Siempre responde en español. "
                        "Sé apasionado, detallado y específico. "
                        "Explica elementos de la trama, atmósfera, tono y por qué conectan con lo que el usuario busca. "
                        "Evita ser genérico: haz que cada explicación sea personal y convincente."
                    ),
                    temperature=0.5,
                    max_output_tokens=600,
                ),
            )
            return response.text
        except Exception:
            return self._fallback_explanation(query, context_summary, movies_with_scores)
