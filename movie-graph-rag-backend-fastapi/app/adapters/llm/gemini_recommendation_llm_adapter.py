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
        "The user received this recommendation based on their recent activity and historical preferences. "
        "Explain in 3-4 sentences why THIS specific movie is the perfect pick for them right now. "
        "Mention the genre, tone, or style elements that align with their profile and the time of day. "
        "Be direct and personal — speak as if you chose this one film just for them tonight."
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


class GeminiRecommendationLlmAdapter(RecommendationLlmClientPort):
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
            "action": "Action",
            "drama": "Drama",
            "comedy": "Comedy",
            "romantic": "Romance",
            "romance": "Romance",
            "horror": "Horror",
            "scary": "Horror",
            "family": "Family",
            "animation": "Animation",
            "animated": "Animation",
            "sci-fi": "Science Fiction",
            "scifi": "Science Fiction",
            "science fiction": "Science Fiction",
            "thriller": "Thriller",
            "fantasy": "Fantasy",
            "mystery": "Mystery",
            "adventure": "Adventure",
            "musical": "Musical",
            "western": "Western",
            "crime": "Crime",
            "war": "War",
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
            f"Inferred ontological context: {semantic_hint}\n\n"
            if semantic_hint
            else ""
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
        for movie in movies_with_scores:
            hints: list[str] = []
            # Individual semantic scores are top-level fields in to_response_dict()
            mood_score = movie.get("moodMatchScore")
            if mood_score is not None:
                hints.append(f"emotional_affinity={float(mood_score):.2f}")
            social_score = movie.get("socialMatchScore")
            if social_score is not None:
                hints.append(f"social_affinity={float(social_score):.2f}")
            energy_score = movie.get("energyMatchScore")
            if energy_score is not None:
                hints.append(f"energy_affinity={float(energy_score):.2f}")
            # overallCompatibility lives inside semanticScores
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
                "or try a more general search. "
                "Try again after adding favorites to get more personalized recommendations."
            )

        titles_with_genres = []
        for movie in movies_with_scores:
            title = movie.get("title", "No title")
            genre = movie.get("genreName", "")
            year = movie.get("releaseDate", "")
            if genre:
                titles_with_genres.append(f"{title} ({genre}, {year})")
            else:
                titles_with_genres.append(f"{title}")
        
        titles_str = ", ".join(titles_with_genres)
        return (
            f"Based on your query '{query}', here are my recommendations: {titles_str}. "
            f"These movies align with the context I detected ({context_summary}). "
            "Each one offers a unique experience: some are more relaxing, others more exciting, "
            "and all have been selected because they match what you're looking for. "
            "If you like any of them, mark it as favorite to improve future recommendations."
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
                        "You are an expert movie recommendation assistant with deep knowledge of cinema. "
                        "Your task is to explain why the recommended movies are perfect for the user. "
                        "Always respond in English. "
                        "Be passionate, detailed, and specific. "
                        "Explain plot elements, atmosphere, tone, and why they connect with what the user is looking for. "
                        "Avoid being generic: make each explanation personal and convincing."
                    ),
                    temperature=0.5,
                    max_output_tokens=600,
                ),
            )
            return response.text
        except Exception:
            return self._fallback_explanation(query, context_summary, movies_with_scores)

    def extract_user_context_with_profile(
        self,
        query: str,
        profile,
        favorites_sample: list[str],
        recent_queries: list[str],
        topological_type: str,
        dominant_cluster_labels: list[str],
        accumulated_context,
        now=None,
    ):
        """Stub: delegates to extract_user_context ignoring profile context."""
        return self.extract_user_context(query, now=now)

    def generate_greeting_response(
        self,
        query: str,
        user_name=None,
        is_cold_start: bool = True,
    ) -> str:
        """Stub: returns a hardcoded invitation message."""
        return (
            "Hello! I'm your movie recommendation assistant. "
            "Tell me what kind of movie you're looking for and I'll help you find the perfect one. "
            "For example: 'something funny for tonight?' or 'intense action movie'."
        )
