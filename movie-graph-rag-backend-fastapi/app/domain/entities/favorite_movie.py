from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FavoriteMovie:
    uri: str
    title: str
    posterUrl: str | None = None
    year: int | None = None
    runtime: int | None = None
    certification: str | None = None
    director: str | None = None
    genres: list[str] = field(default_factory=list)
    description: str | None = None
    rating: float | None = None
    relationReason: str | None = None
    addedAt: datetime | None = None
