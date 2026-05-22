from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from groq import Groq

logger = logging.getLogger(__name__)

from app.core.config import settings

_GROQ_NLU_TIMEOUT = 15  # seconds per NLU call


def ping_groq(timeout_seconds: int = 5) -> bool:
    """Return True if the Groq API is reachable and the API key is valid.

    Uses the Groq SDK to list models — zero token cost, same auth path as
    real calls.  Returns False on any network or auth error.
    """
    try:
        client = Groq(api_key=settings.groq_api_key, timeout=timeout_seconds)
        client.models.list()
        return True
    except Exception:
        return False
from app.core.conversation_context import get_time_of_day, infer_children_age_hint
from app.domain.entities.query_context import QueryContext
from app.domain.entities.recommendation_models import UserContext
from app.domain.ports.recommendation_llm_client import RecommendationLlmClientPort

if TYPE_CHECKING:
    from app.domain.entities.recommendation_models import UserProfile


_NLU_SYSTEM_PROMPT = (
    "You are an intent analyzer for an English movie recommendation system.\n\n"
    "EXAMPLES:\n"
    'Query: "I\'m exhausted from work, something short to relax"\n'
    'Response: {"intent": "general", "mood": "relaxed", "social_context": null, "genres": [], "director_hint": null, "year_range": null, "runtime_max": 90, "exclusions": []}\n\n'
    'Query: "We\'re 6 friends, Friday night, something fun"\n'
    'Response: {"intent": "comedy", "mood": "excited", "social_context": {"companionType": "friends", "hasChildren": false, "numberOfPeople": 6}, "genres": ["Comedy"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Query: "Something to watch with my young kids this afternoon"\n'
    'Response: {"intent": "family", "mood": "happy", "social_context": {"companionType": "family", "hasChildren": true, "numberOfPeople": 4}, "genres": ["Animation", "Family"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Query: "I want to cry, nothing with action"\n'
    'Response: {"intent": "drama", "mood": "sad", "social_context": null, "genres": ["Drama", "Romance"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": ["Action"]}\n\n'
    'Query: "Romantic movie for my partner, something from the 90s"\n'
    'Response: {"intent": "romance", "mood": "romantic", "social_context": {"companionType": "partner", "hasChildren": false, "numberOfPeople": 2}, "genres": ["Romance"], "director_hint": null, "year_range": [1990, 1999], "runtime_max": null, "exclusions": []}\n\n'
    'Query: "Something by Nolan, intense sci-fi"\n'
    'Response: {"intent": "scifi", "mood": "excited", "social_context": null, "genres": ["Science Fiction"], "director_hint": "Christopher Nolan", "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Query: "I have one hour, something light that doesn\'t make me think"\n'
    'Response: {"intent": "general", "mood": "relaxed", "social_context": null, "genres": ["Comedy"], "director_hint": null, "year_range": null, "runtime_max": 60, "exclusions": []}\n\n'
    'Query: "I want adventure, adrenaline, something epic"\n'
    'Response: {"intent": "action", "mood": "adventurous", "social_context": null, "genres": ["Action", "Adventure"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    "RULES:\n"
    "- mood: choose the closest enum value. NEVER return a value outside the enum. If no clear emotional signal, use null.\n"
    "- If user mentions a director or actor by name, extract it in director_hint.\n"
    "- \"without X\", \"no X\", \"nothing with X\" → add X to exclusions.\n"
    "- year_range: only if user explicitly mentions a time period, decade or year range.\n"
    "- numberOfPeople: infer from context (\"we're 6\" → 6, \"with my partner\" → 2, \"with my family\" → 4, \"with my kids\" → 4).\n"
    "- runtime_max: only for explicit restrictions. \"something short\" → 90. \"I have one hour\" → 60. \"I have 90 minutes\" → 90.\n"
    "- If user mentions a genre, map it to the English enum name.\n"
    "- Respond ONLY with JSON. No extra text, no backticks, no explanations.\n\n"
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
        "Explain in detail (5-7 sentences) why these movies match what the user is looking for. "
        "Be specific about tone, style and elements that make each movie especially relevant. "
        "Mention plot or atmosphere details that connect to the user's search."
    ),
    "activity": (
        "Write a 2-3 sentence pitch (max 90 words) that makes someone want to watch this movie right now. "
        "Hook with the premise or tone. Mention one concrete element: a plot beat, atmosphere, or standout performance. "
        "End with what kind of viewer or mood it suits. "
        "No filler phrases. No score data. No 'based on your preferences'."
    ),
    "cold_start": (
        "This is the user's first interaction with the system, so these recommendations are based on their query context. "
        "Explain in detail (5-7 sentences) why these movies are an excellent starting point. "
        "Emphasize the diversity in genres or styles to help them explore. "
        "Invite the user to mark favorites to improve future recommendations."
    ),
    "mood_driven": (
        "The user's emotional state was the main signal for this selection. "
        "Explain in detail (5-7 sentences) how the tone, pace, themes and atmosphere of these movies connect with that specific mood. "
        "Be concrete: describe scenes or elements from each movie that generate the desired emotion. "
        "Use empathetic and evocative language."
    ),
    "social": (
        "The social context was the determining factor in this selection. "
        "Explain in detail (5-7 sentences) why these movies are perfect for the described group or company. "
        "If there are children, explain the appropriate content in detail, safe themes and why it's entertaining for all ages. "
        "If it's a group of friends or couple, highlight social elements like humor, drama or romance that make the shared experience."
    ),
}

_PROFILE_NLU_SYSTEM_PROMPT = (
    "You are an intent analyzer for an English movie recommendation system.\n"
    "The user has a profile with preference history.\n\n"
    "SPECIAL BEHAVIOR:\n"
    "- If the query is AMBIGUOUS (e.g. 'something good', 'I don't know what to watch', 'surprise me') and profile is available,\n"
    "  INFER the intent from the profile instead of returning empty fields.\n"
    "- If the message is clearly a GREETING, SMALL TALK, or question NOT related to movies\n"
    "  (e.g. 'how are you?', 'who are you?', 'what is the capital of France?'), return off_topic=true.\n"
    "- 'Hi, I want something good' → off_topic=false (there is intent to watch something).\n"
    "- 'Hi' alone, 'How are you?' → off_topic=true.\n\n"
    "EXAMPLES:\n"
    'Query: "Hi, how are you?"\n'
    'Response: {"off_topic": true, "intent": "general", "mood": null, "social_context": null, "genres": [], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Query: "I don\'t know what to watch" (user with profile: Comedy 80%, Drama 40%, dominant mood: relaxed)\n'
    'Response: {"off_topic": false, "intent": "comedy", "mood": "relaxed", "social_context": null, "genres": ["Comedy"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    'Query: "Something scary for tonight"\n'
    'Response: {"off_topic": false, "intent": "horror", "mood": "excited", "social_context": null, "genres": ["Horror"], "director_hint": null, "year_range": null, "runtime_max": null, "exclusions": []}\n\n'
    "RULES:\n"
    "- off_topic: true ONLY if the message has no relation to movies/series/recommendations.\n"
    "- mood: choose the closest enum value. NEVER return a value outside the enum. If no clear emotional signal, use null.\n"
    "- If user mentions a director or actor by name, extract it in director_hint.\n"
    "- 'without X', 'no X', 'nothing with X' → add X to exclusions.\n"
    "- year_range: only if user explicitly mentions a time period, decade or year range.\n"
    "- runtime_max: only for explicit restrictions. 'something short' → 90. 'I have one hour' → 60.\n"
    "- If user mentions a genre, map it to the English enum name.\n"
    "- Respond ONLY with JSON. No extra text, no backticks, no explanations.\n\n"
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
    "You are Moviq, a virtual movie recommendation assistant. "
    "The user has sent you a message that is not a movie query. "
    "Respond in a friendly, very brief manner (2-3 sentences maximum) and in English. "
    "Invite them to make a recommendation query. "
    "Suggest 1-2 concrete examples of questions they can ask you. "
    "Don't introduce yourself in each response if it seems like a continuous conversation."
)

_EXPLANATION_SYSTEM_PROMPT = (
    "You are an expert movie recommendation assistant with deep knowledge of cinema. "
    "Your task is to explain why the recommended movies are perfect for the user. "
    "Always respond in English. "
    "Be passionate, detailed and specific. "
    "Explain elements of the plot, atmosphere, tone and why they connect with what the user is looking for. "
    "Avoid being generic: make each explanation personal and convincing."
)


class GroqRecommendationLlmAdapter(RecommendationLlmClientPort):

    def _keyword_extract_context(self, query_lower: str) -> QueryContext:
        social_context = None
        if any(token in query_lower for token in ["alone", "by myself", "solo", "myself"]):
            social_context = {"companionType": "alone", "hasChildren": False, "numberOfPeople": 1}
        elif any(token in query_lower for token in ["colleagues", "coworkers", "work friends"]):
            social_context = {"companionType": "friends", "hasChildren": False, "numberOfPeople": 4}
        elif any(token in query_lower for token in ["friends", "group", "buddy"]):
            social_context = {"companionType": "friends", "hasChildren": False, "numberOfPeople": 3}
        elif any(token in query_lower for token in ["partner", "girlfriend", "boyfriend", "spouse"]):
            social_context = {"companionType": "partner", "hasChildren": False, "numberOfPeople": 2}
        elif any(token in query_lower for token in ["family", "kids", "children", "children"]):
            social_context = {"companionType": "family", "hasChildren": True, "numberOfPeople": 4}

        mood = None
        if any(token in query_lower for token in ["relax", "tranquil", "light", "calm", "chill"]):
            mood = "relaxed"
        elif any(token in query_lower for token in ["action", "emotion", "intense", "adrenaline"]):
            mood = "excited"
        elif any(token in query_lower for token in ["sad", "cry", "emotional"]):
            mood = "sad"
        elif any(token in query_lower for token in ["happy", "joy", "fun", "funny"]):
            mood = "happy"
        elif any(token in query_lower for token in ["stress", "anxious", "overwhelm", "tired"]):
            mood = "stressed"
        elif any(token in query_lower for token in ["anxious", "nervous", "worried", "panic"]):
            mood = "anxious"
        elif any(token in query_lower for token in ["boring", "bored", "dull"]):
            mood = "bored"
        elif any(token in query_lower for token in ["nostalgic", "memory", "remember", "throwback"]):
            mood = "nostalgic"
        elif any(token in query_lower for token in ["romantic", "love", "romantic", "in love"]):
            mood = "romantic"
        elif any(token in query_lower for token in ["curious", "interesting", "discover", "explore"]):
            mood = "curious"
        elif any(token in query_lower for token in ["adventure", "adrenaline", "epic", "epic", "pure action"]):
            mood = "adventurous"
        elif any(token in query_lower for token in ["focus", "concentrate", "productive"]):
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
        for marker in ["without ", "except ", "excluding "]:
            if marker in query_lower:
                tail = query_lower.split(marker, 1)[1].split(".", 1)[0].strip()
                if tail:
                    exclusions.append(tail)

        genre_aliases = {
            "action": "Action", "drama": "Drama",
            "comedy": "Comedy", "romantic": "Romance", "romance": "Romance",
            "horror": "Horror", "scary": "Horror",
            "family": "Family", "animation": "Animation",
            "sci-fi": "Science Fiction", "scifi": "Science Fiction", "science fiction": "Science Fiction",
            "thriller": "Thriller", "fantasy": "Fantasy",
            "mystery": "Mystery", "adventure": "Adventure", "musical": "Musical",
            "western": "Western", "crime": "Crime", "war": "War",
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
        client = Groq(api_key=settings.groq_api_key, timeout=_GROQ_NLU_TIMEOUT)
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
        client = Groq(api_key=settings.groq_api_key, timeout=_GROQ_NLU_TIMEOUT)
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
        conversation_history: list[dict] | None = None,
    ) -> UserContext:
        # Build enriched user message with profile context
        genre_info = ", ".join(
            f"{g} ({w:.0%})"
            for g, w in sorted(
                (profile.genre_weights or {}).items(), key=lambda x: -x[1]
            )[:4]
        ) or "no history"

        acc_parts: list[str] = []
        if accumulated_context:
            if accumulated_context.mood:
                acc_parts.append(f"mood={accumulated_context.mood}")
            if accumulated_context.genres:
                acc_parts.append(f"genres={accumulated_context.genres}")
            if accumulated_context.companion:
                acc_parts.append(f"companion={accumulated_context.companion}")
            if accumulated_context.runtime_max:
                acc_parts.append(f"max_runtime={accumulated_context.runtime_max}")
            if accumulated_context.exclusions:
                acc_parts.append(f"excluded={accumulated_context.exclusions}")
        acc_summary = ", ".join(acc_parts) or "no previous context"

        # Fallback: if no accumulated context but we have the raw message history,
        # summarize the last 3 user turns so the LLM has some prior context.
        if not acc_parts and conversation_history:
            prior_user = [
                m["content"]
                for m in conversation_history
                if m.get("role") == "user"
            ][-3:]
            if prior_user:
                acc_summary = "prior messages: " + " | ".join(prior_user)

        user_message = (
            f"USER CONTEXT:\n"
            f"- Favorite genres: {genre_info}\n"
            f"- Predominant mood: {profile.dominant_mood or 'unknown'}\n"
            f"- Exploration profile: {topological_type}\n"
            f"- Frequent thematic communities: {', '.join(dominant_cluster_labels[:3]) or 'none'}\n"
            f"- Recent favorites: {', '.join(favorites_sample[:5]) or 'none yet'}\n"
            f"- Recent searches: {'; '.join(recent_queries[:3]) or 'none'}\n"
            f"- Accumulated session context: {acc_summary}\n\n"
            f"CURRENT QUERY: {query}\n\n"
            "INSTRUCTION: If the query is ambiguous, use the profile to infer intent. "
            "If it's not a movie query, return off_topic=true."
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
            user_msg = f"User message: {query}"
            if not is_cold_start:
                user_msg += "\n(The user has already used the system before)"
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
                "Hello! I'm Moviq, your movie recommendation assistant. "
                "You can ask me things like: 'What to watch tonight with my partner?' "
                "or 'Something horror for the weekend'. What would you like to watch?"
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
            f"Inferred ontological context: {semantic_hint}\n\n" if semantic_hint else ""
        )
        if not movies_with_scores:
            return (
                "You are a movie recommendation assistant. "
                "Respond in English in 2-3 sentences, explain why there are no recommendations "
                "and suggest adding favorites or making a more specific query.\n\n"
                f"{query_type_instruction}\n\n"
                f"{semantic_section}"
                f"Query: {query}\n"
                f"Inferred context: {context_summary}"
            )

        top: list[str] = []
        for movie in movies_with_scores[:5]:
            hints: list[str] = []
            mood_score = movie.get("moodMatchScore")
            if mood_score is not None:
                hints.append(f"emotional_affinity={float(mood_score):.2f}")
            social_score = movie.get("socialMatchScore")
            if social_score is not None:
                hints.append(f"social_affinity={float(social_score):.2f}")
            energy_score = movie.get("energyMatchScore")
            if energy_score is not None:
                hints.append(f"energy_affinity={float(energy_score):.2f}")
            overall = (movie.get("semanticScores") or {}).get("overallCompatibility")
            if overall is not None:
                hints.append(f"overall_compatibility={float(overall):.2f}")
            score_detail = ", ".join(hints)
            line = (
                f"- {movie.get('title')} (score={movie.get('compatibilityScore')}, "
                f"genre={movie.get('genreName')}"
            )
            if score_detail:
                line += f", {score_detail}"
            line += ")"
            top.append(line)

        top_text = "\n".join(top)
        return (
            f"{query_type_instruction}\n\n"
            f"{semantic_section}"
            f"Query: {query}\n"
            f"Inferred context: {context_summary}\n"
            f"Top recommendations:\n{top_text}"
        )

    def _fallback_explanation(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
    ) -> str:
        if not movies_with_scores:
            return (
                "Unfortunately, I couldn't find movies that exactly match your search at this time. "
                f"Your query was: '{query}'. "
                "I suggest marking some movies as favorites so the system can better learn your preferences, "
                "or try a more general search."
            )
        titles_with_genres = []
        for movie in movies_with_scores[:5]:
            title = movie.get("title", "No title")
            genre = movie.get("genreName", "")
            year = movie.get("releaseDate", "")
            titles_with_genres.append(f"{title} ({genre}, {year})" if genre else title)

        titles_str = ", ".join(titles_with_genres)
        return (
            f"Based on your query '{query}', here are my recommendations: {titles_str}. "
            f"These movies align with the context I detected ({context_summary}). "
            "If you like any of them, mark it as favorite to improve future recommendations."
        )

    def _generate_explanation_once(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
        semantic_hint: str,
        query_type: str,
        extra_hint: str = "",
    ) -> str | None:
        max_tokens = 200 if query_type == "activity" else 600
        try:
            base_prompt = self._build_prompt(
                query, context_summary, movies_with_scores, semantic_hint, query_type
            )
            prompt = base_prompt + extra_hint if extra_hint else base_prompt
            client = Groq(api_key=settings.groq_api_key)
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": _EXPLANATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("Groq _generate_explanation_once failed: %s", exc)
            return None

    def _call_judge(
        self, explanation: str, title: str, context_summary: str, query_type: str
    ) -> float:
        from app.adapters.llm.explanation_evaluator import build_judge_prompt, parse_judge_score

        prompt = build_judge_prompt(explanation, title, context_summary, query_type)
        try:
            client = Groq(api_key=settings.groq_api_key)
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a movie explanation quality judge. Respond only with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            return parse_judge_score(response.choices[0].message.content)
        except Exception as exc:
            logger.warning("Groq judge call failed: %s", exc)
            return 1.0

    def generate_recommendation_explanation(
        self,
        query: str,
        context_summary: str,
        movies_with_scores: list[dict],
        semantic_hint: str = "",
        query_type: str = "general",
    ) -> str:
        from app.adapters.llm.explanation_evaluator import (
            validate_text, build_retry_hint, JUDGE_THRESHOLD,
        )

        title = movies_with_scores[0].get("title", "") if movies_with_scores else ""

        # --- Initial generation ---
        text = self._generate_explanation_once(
            query, context_summary, movies_with_scores, semantic_hint, query_type
        )
        if not text:
            return self._fallback_explanation(query, context_summary, movies_with_scores)

        # --- Static validation (word count, title presence, forbidden phrases) ---
        eval_result = validate_text(text, title, query_type)
        if eval_result.issues:
            retry = self._generate_explanation_once(
                query, context_summary, movies_with_scores, semantic_hint, query_type,
                extra_hint=build_retry_hint(eval_result.issues),
            )
            if retry:
                text = retry

        # --- LLM-as-a-judge ---
        judge_score = self._call_judge(text, title, context_summary, query_type)
        if judge_score < JUDGE_THRESHOLD:
            retry = self._generate_explanation_once(
                query, context_summary, movies_with_scores, semantic_hint, query_type,
                extra_hint=build_retry_hint(["low_quality"]),
            )
            if retry:
                text = retry

        return text
