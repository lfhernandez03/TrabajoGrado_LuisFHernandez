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
    raw_query: str = ""


@dataclass
class UserProfile:
    """Persistent user preference profile built from favorites and search history with temporal decay."""

    user_id: str
    genre_weights: dict[str, float] = field(default_factory=dict)
    dominant_mood: str | None = None
    dominant_companion: str | None = None
    snapshot_count: int = 0
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
    semantic_scores: dict[str, float] = field(default_factory=dict)
    kid_friendly: bool | None = None

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

        try:
            kid_friendly = bool(row["kidFriendly"]) if row.get("kidFriendly") is not None else None
        except Exception:
            kid_friendly = None

        semantic_scores = {}
        score_mappings = {
            "overallCompatibility": "compatibilityScore",
            "moodMatchScore": "moodMatch",
            "socialMatchScore": "socialMatch",
            "energyMatchScore": "energyMatch",
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
            semantic_scores=semantic_scores,
            kid_friendly=kid_friendly,
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
            "semanticScores": self.semantic_scores,
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
