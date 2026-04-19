from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from groq import Groq

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.conversation_context import get_time_of_day, infer_children_age_hint
from app.domain.entities.query_context import QueryContext
from app.domain.entities.recommendation_models import UserContext
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort

if TYPE_CHECKING:
    from app.domain.entities.recommendation_models import UserProfile


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

_PROFILE_NLU_SYSTEM_PROMPT = (
    "Eres un analizador de intención para un sistema de recomendación de películas en español.\n"
    "El usuario tiene un perfil con historial de preferencias.\n\n"
    "COMPORTAMIENTO ESPECIAL:\n"
    "- Si la consulta es AMBIGUA (ej. 'algo bueno', 'no sé qué ver', 'sorpréndeme') y hay perfil disponible,\n"
    "  INFIERE la intención a partir del perfil en lugar de devolver campos vacíos.\n"
    "- Si el mensaje es claramente un SALUDO, SMALL TALK, o pregunta NO relacionada con películas\n"
    "  (ej. '¿cómo estás?', '¿quién eres?', '¿cuál es la capital de Francia?'), devuelve off_topic=true.\n"
    "- 'Hola, quiero algo bueno' → off_topic=false (hay intención de ver algo).\n"
    "- 'Hola' solo, '¿cómo estás?' → off_topic=true.\n\n"
    "EJEMPLOS:\n"
    'Consulta: "Hola, ¿cómo estás?"\n'
    'Respuesta: {"off_topic": true, "intent": "general", "mood": null, "social_context": null, "genres": [], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Consulta: "No sé qué ver" (usuario con perfil: Comedy 80%, Drama 40%, mood dominante: relaxed)\n'
    'Respuesta: {"off_topic": false, "intent": "comedy", "mood": "relaxed", "social_context": null, "genres": ["Comedy"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Consulta: "Algo de terror para esta noche"\n'
    'Respuesta: {"off_topic": false, "intent": "horror", "mood": "excited", "social_context": null, "genres": ["Horror"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    "REGLAS:\n"
    "- off_topic: true SOLO si el mensaje no tiene ninguna relación con películas/series/recomendaciones.\n"
    "- mood: elige el valor más cercano del enum. NUNCA devuelvas un valor fuera del enum. Si no hay señal emocional clara, usa null.\n"
    "- Si el usuario menciona un director o actor por nombre, extráelo en director_hint.\n"
    "- 'sin X', 'nada de X', 'que no sea X' → agregar X a exclusions.\n"
    "- year_range: solo si el usuario menciona explícitamente una época, década o rango de años.\n"
    "- runtime_max: solo para restricciones explícitas. 'algo corto' → 90. 'tengo una hora' → 60.\n"
    "- Si el usuario menciona un género en español, mapéalo al nombre en inglés del enum.\n"
    "- Responde SOLO con el JSON. Sin texto adicional, sin backticks, sin explicaciones.\n\n"
    "{\n"
    '  "off_topic": false | true,\n'
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

_GREETING_SYSTEM_PROMPT = (
    "Eres CineGraph, un asistente virtual de recomendación de películas. "
    "El usuario te ha enviado un mensaje que no es una consulta de película. "
    "Responde de forma amigable, muy breve (2-3 frases máximo) y en español. "
    "Invítalo a hacer una consulta de recomendación. "
    "Sugiere 1-2 ejemplos concretos de preguntas que puede hacerte. "
    "No te presentes en cada respuesta si parece una conversación continua."
)

_EXPLANATION_SYSTEM_PROMPT = (
    "Eres un experto asistente de recomendación de películas con profundo conocimiento de cine. "
    "Tu tarea es explicar por qué las películas recomendadas son perfectas para el usuario. "
    "Siempre responde en español. "
    "Sé apasionado, detallado y específico. "
    "Explica elementos de la trama, atmósfera, tono y por qué conectan con lo que el usuario busca. "
    "Evita ser genérico: haz que cada explicación sea personal y convincente."
)


class GroqRecommendationLlmAdapter(RecommendationLlmClientPort):

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
            "accion": "Action", "acción": "Action", "drama": "Drama",
            "comedia": "Comedy", "romantica": "Romance", "romántica": "Romance",
            "romance": "Romance", "terror": "Horror", "miedo": "Horror",
            "familia": "Family", "familiar": "Family", "animada": "Animation",
            "animacion": "Animation", "animación": "Animation",
            "ciencia": "Science Fiction", "ciencia ficcion": "Science Fiction",
            "ciencia ficción": "Science Fiction", "sci-fi": "Science Fiction",
            "thriller": "Thriller", "fantasia": "Fantasy", "fantasía": "Fantasy",
            "misterio": "Mystery", "aventura": "Adventure", "musical": "Musical",
            "western": "Western", "crimen": "Crime", "guerra": "War",
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

    def _call_nlu_with_system(self, system_prompt: str, user_message: str) -> dict:
        """Generic Groq NLU call with a custom system prompt and pre-built user message."""
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def _call_nlu(self, query: str) -> dict:
        print(f"[GROQ] _call_nlu called — model={settings.groq_model} key_len={len(settings.groq_api_key)}", flush=True)
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": _NLU_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def extract_query_context(self, query: str) -> QueryContext:
        try:
            data = self._call_nlu(query)
            return QueryContext.model_validate(data)
        except Exception as exc:
            import traceback
            print(f"[GROQ] NLU FAILED: {type(exc).__name__}: {exc}", flush=True)
            traceback.print_exc()
            return self._keyword_extract_context(query.lower())

    def extract_user_context(
        self,
        query: str,
        now: datetime | None = None,
        session_id: str | None = None,
    ) -> UserContext:
        llm_ok = False
        data: dict = {}
        try:
            data = self._call_nlu(query)
            llm_ok = True
        except Exception as exc:
            import traceback
            print(f"[GROQ] extract_user_context FAILED: {type(exc).__name__}: {exc}", flush=True)
            traceback.print_exc()

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

    def extract_user_context_with_profile(
        self,
        query: str,
        profile: "UserProfile",
        favorites_sample: list[str],
        recent_queries: list[str],
        topological_type: str,
        dominant_cluster_labels: list[str],
        accumulated_context: "UserContext | None",
        now: "datetime | None" = None,
    ) -> UserContext:
        # Build enriched user message with profile context
        genre_info = ", ".join(
            f"{g} ({w:.0%})"
            for g, w in sorted(
                (profile.genre_weights or {}).items(), key=lambda x: -x[1]
            )[:4]
        ) or "sin historial"

        acc_parts: list[str] = []
        if accumulated_context:
            if accumulated_context.mood:
                acc_parts.append(f"mood={accumulated_context.mood}")
            if accumulated_context.genres:
                acc_parts.append(f"genres={accumulated_context.genres}")
            if accumulated_context.companion:
                acc_parts.append(f"companion={accumulated_context.companion}")
        acc_summary = ", ".join(acc_parts) or "sin contexto previo"

        user_message = (
            f"CONTEXTO DEL USUARIO:\n"
            f"- Géneros favoritos: {genre_info}\n"
            f"- Estado de ánimo predominante: {profile.dominant_mood or 'desconocido'}\n"
            f"- Perfil de exploración: {topological_type}\n"
            f"- Comunidades temáticas frecuentes: {', '.join(dominant_cluster_labels[:3]) or 'ninguna'}\n"
            f"- Favoritos recientes: {', '.join(favorites_sample[:5]) or 'ninguno aún'}\n"
            f"- Búsquedas recientes: {'; '.join(recent_queries[:3]) or 'ninguna'}\n"
            f"- Contexto acumulado de sesión: {acc_summary}\n\n"
            f"QUERY ACTUAL: {query}\n\n"
            "INSTRUCCIÓN: Si el query es ambiguo, usa el perfil para inferir intención. "
            "Si no es una consulta de película, devuelve off_topic=true."
        )

        llm_ok = False
        data: dict = {}
        try:
            data = self._call_nlu_with_system(_PROFILE_NLU_SYSTEM_PROMPT, user_message)
            llm_ok = True
        except Exception as exc:
            logger.warning("extract_user_context_with_profile LLM failed: %s", exc)

        if llm_ok:
            social = data.get("social_context") or {}
            ctx = UserContext(
                mood=data.get("mood"),
                companion=social.get("companionType"),
                has_children=bool(social.get("hasChildren", False)),
                energy=None,
                genres=list(data.get("genres") or []),
                runtime_max=data.get("runtime_max"),
                exclusions=list(data.get("exclusions") or []),
                confidence=0.9,
                time_of_day=get_time_of_day(now),
                children_age_hint=infer_children_age_hint(query),
                raw_query=query,
                off_topic=bool(data.get("off_topic", False)),
            )
            # Profile fallback: if low signal but warm user, infer from history
            low_signal = not ctx.off_topic and not ctx.mood and not ctx.genres and not ctx.companion
            if low_signal and not profile.is_cold_start:
                ctx.mood = profile.dominant_mood
                ctx.genres = [
                    g for g, _ in sorted(
                        (profile.genre_weights or {}).items(), key=lambda x: -x[1]
                    )[:2]
                ]
                ctx.confidence = 0.65
            return ctx

        # Fallback: keyword extraction (no off_topic detection possible without LLM)
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
            raw_query=query,
        )

    def generate_greeting_response(
        self,
        query: str,
        user_name: str | None = None,
        is_cold_start: bool = True,
    ) -> str:
        try:
            user_msg = f"Mensaje del usuario: {query}"
            if not is_cold_start:
                user_msg += "\n(El usuario ya ha usado el sistema antes)"
            client = Groq(api_key=settings.groq_api_key)
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": _GREETING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                max_tokens=150,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("generate_greeting_response failed: %s", exc)
            return (
                "¡Hola! Soy CineGraph, tu asistente de recomendación de películas. "
                "Puedes preguntarme cosas como: '¿qué ver esta noche con mi pareja?' "
                "o 'algo de terror para el fin de semana'. ¿Qué te gustaría ver?"
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
            query_type, QUERY_TYPE_INSTRUCTIONS["general"]
        )
        semantic_section = (
            f"Contexto ontológico inferido: {semantic_hint}\n\n" if semantic_hint else ""
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
            mood_score = movie.get("moodMatchScore")
            if mood_score is not None:
                hints.append(f"afinidad_emocional={float(mood_score):.2f}")
            social_score = movie.get("socialMatchScore")
            if social_score is not None:
                hints.append(f"afinidad_social={float(social_score):.2f}")
            energy_score = movie.get("energyMatchScore")
            if energy_score is not None:
                hints.append(f"afinidad_energia={float(energy_score):.2f}")
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
                "o intenta con una búsqueda más general."
            )
        titles_with_genres = []
        for movie in movies_with_scores[:5]:
            title = movie.get("title", "Sin título")
            genre = movie.get("genreName", "")
            year = movie.get("releaseDate", "")
            titles_with_genres.append(f"{title} ({genre}, {year})" if genre else title)

        titles_str = ", ".join(titles_with_genres)
        return (
            f"Basándome en tu consulta '{query}', preparé estas recomendaciones: {titles_str}. "
            f"Estas películas se alinean con el contexto que detecté ({context_summary}). "
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
                query, context_summary, movies_with_scores, semantic_hint, query_type
            )
            client = Groq(api_key=settings.groq_api_key)
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": _EXPLANATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception as exc:
            import traceback
            print(f"[GROQ] explanation FAILED: {type(exc).__name__}: {exc}", flush=True)
            traceback.print_exc()
            return self._fallback_explanation(query, context_summary, movies_with_scores)
