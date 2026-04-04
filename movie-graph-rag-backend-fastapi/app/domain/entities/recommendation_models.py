from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserContext:
    """Structured context extracted from a user query. confidence=0.9 when extracted by LLM, 0.5 when keyword fallback was used."""

    mood: str | None = None
    companion: str | None = None
    has_children: bool = False
    energy: str | None = None
    genres: list[str] = field(default_factory=list)
    runtime_max: int | None = None
    exclusions: list[str] = field(default_factory=list)
    confidence: float = 0.5
    time_of_day: str | None = None
    # Inferred automatically from server clock, never from LLM.
    # Values: "morning" (6-11), "afternoon" (12-17), "evening" (18-22), "night" (23-5)
    # Used for SPARQL filter: bridge:compatibleTimeOfDay
    children_age_hint: str | None = None
    # Extracted by LLM when social_context has children.
    # Values: "young" (<12), "teen" (12-17), "adult" (18+), None (unknown)
    # Controls whether isKidFriendly is applied as hard filter ("young") or soft signal (None/"teen")
    session_id: str | None = None
    # Identifies the conversation session. Set by the API layer, not the LLM.
    # Used to accumulate context across multiple turns of the same conversation.
    raw_query: str = ""


@dataclass
class UserProfile:
    """Persistent user preference profile built from favorites and search history with temporal decay."""

    user_id: str
    genre_weights: dict[str, float] = field(default_factory=dict)
    dominant_mood: str | None = None
    dominant_companion: str | None = None
    snapshot_count: int = 0
    dominant_time_of_day: str | None = None
    # Most frequent time_of_day from archived context snapshots.
    # Populated by ProfileService from Fuseki history.
    children_age_hint: str | None = None
    # Most recent children_age_hint from user history.
    # Preserved across sessions to avoid asking again.
    is_cold_start: bool = True

    @classmethod
    def cold_start(cls, user_id: str) -> UserProfile:
        return cls(user_id=user_id, is_cold_start=True)


@dataclass
class Movie:
    """A movie candidate with scoring metadata attached after ranking."""

    uri: str
    title: str
    genre: str | None = None
    runtime: int | None = None
    rating: float | None = None
    poster_url: str | None = None
    release_year: str | None = None
    compatibility_score: float = 0.0
    mood_match_score: float | None = None
    social_match_score: float | None = None
    energy_match_score: float | None = None
    time_match_score: float | None = None
    semantic_scores: dict[str, float] = field(default_factory=dict)
    kid_friendly: bool | None = None
    serendipity_score: float = 0.0
    description: str | None = None

    @classmethod
    def from_fuseki_row(cls, row: dict) -> Movie:
        uri = row.get("movie", "")
        title = row.get("title", "")
        genre = row.get("genreName")

        try:
            runtime = int(float(row["runtime"])) if row.get("runtime") is not None else None
        except Exception:
            runtime = None

        try:
            rating = float(row["rating"]) if row.get("rating") is not None else None
        except Exception:
            rating = None

        poster_url = row.get("posterUrl")
        release_year = str(row["releaseDate"])[:4] if row.get("releaseDate") else None

        try:
            compatibility_score = (
                float(row["compatibilityScore"])
                if row.get("compatibilityScore") is not None
                else 0.0
            )
        except Exception:
            compatibility_score = 0.0

        # Parse individual match scores from bridge data
        mood_match_score = None
        try:
            if row.get("moodMatchScore") is not None:
                mood_match_score = float(row["moodMatchScore"])
        except Exception:
            pass

        social_match_score = None
        try:
            if row.get("socialMatchScore") is not None:
                social_match_score = float(row["socialMatchScore"])
        except Exception:
            pass

        energy_match_score = None
        try:
            if row.get("energyMatchScore") is not None:
                energy_match_score = float(row["energyMatchScore"])
        except Exception:
            pass

        time_match_score = None
        try:
            if row.get("timeMatchScore") is not None:
                time_match_score = float(row["timeMatchScore"])
        except Exception:
            pass

        try:
            kid_friendly = bool(row["kidFriendly"]) if row.get("kidFriendly") is not None else None
        except Exception:
            kid_friendly = None

        # Build semantic scores dict for backward compatibility
        semantic_scores = {}
        score_mappings = {
            "overallCompatibility": "compatibilityScore",
            "moodMatchScore": "moodMatch",
            "socialMatchScore": "socialMatch",
            "energyMatchScore": "energyMatch",
            "timeMatchScore": "timeMatch",
        }
        for key, row_key in score_mappings.items():
            if row.get(row_key) is not None:
                try:
                    semantic_scores[key] = float(row[row_key])
                except Exception:
                    pass

        return cls(
            uri=uri,
            title=title,
            genre=genre,
            runtime=runtime,
            rating=rating,
            poster_url=poster_url,
            release_year=release_year,
            compatibility_score=compatibility_score,
            mood_match_score=mood_match_score,
            social_match_score=social_match_score,
            energy_match_score=energy_match_score,
            time_match_score=time_match_score,
            semantic_scores=semantic_scores,
            kid_friendly=kid_friendly,
            description=row.get("description"),
        )

    def to_response_dict(self) -> dict:
        return {
            "title": self.title,
            "posterUrl": self.poster_url,
            "runtime": self.runtime,
            "genreName": self.genre,
            "releaseDate": self.release_year,
            "averageRating": self.rating,
            "compatibilityScore": self.compatibility_score,
            "moodMatchScore": self.mood_match_score,
            "socialMatchScore": self.social_match_score,
            "energyMatchScore": self.energy_match_score,
            "timeMatchScore": self.time_match_score,
            "semanticScores": self.semantic_scores,
            "kidFriendly": self.kid_friendly,
            "serendipityScore": self.serendipity_score,
            "description": self.description,
        }


@dataclass
class RecommendationResult:
    """Complete output of a recommendation pipeline execution."""

    movies: list[Movie]
    strategy_used: str
    sparql_executed: str
    context: UserContext
    explanation: str = ""
    execution_ms: int = 0
    debug: dict = field(default_factory=dict)

    @property
    def movies_as_dicts(self) -> list[dict]:
        return [m.to_response_dict() for m in self.movies]

    @property
    def was_successful(self) -> bool:
        return len(self.movies) > 0


@dataclass
class ConversationTurn:
    """A single turn in a recommendation conversation."""

    role: str
    # "user" or "assistant"

    content: str
    # Raw text of the message

    context: UserContext | None = None
    # Extracted UserContext for user turns. None for assistant turns.

    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConversationSession:
    """Accumulated context across multiple turns of a recommendation conversation."""

    session_id: str
    user_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    accumulated_context: UserContext | None = None
    # Merged UserContext from all user turns so far.
    # None until at least one user turn has been processed.

    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def add_turn(self, turn: ConversationTurn) -> None:
        """Append a turn and update last_updated."""
        self.turns.append(turn)
        self.last_updated = datetime.utcnow()

    @property
    def user_turns(self) -> list[ConversationTurn]:
        """Return only user turns with extracted context."""
        return [t for t in self.turns if t.role == "user" and t.context is not None]

    @property
    def last_user_query(self) -> str | None:
        """Return the most recent user message content."""
        user_turns = [t for t in self.turns if t.role == "user"]
        return user_turns[-1].content if user_turns else None
