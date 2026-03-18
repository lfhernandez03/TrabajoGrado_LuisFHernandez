from pydantic import BaseModel, Field


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
