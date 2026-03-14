from datetime import datetime

from pydantic import BaseModel, Field


class FavoriteMovieRequest(BaseModel):
    uri: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    posterUrl: str | None = None
    year: int | None = None
    runtime: int | None = None
    certification: str | None = None
    director: str | None = None
    genres: list[str] = Field(default_factory=list)
    description: str | None = None
    rating: float | None = None
    relationReason: str | None = None


class RemoveFavoriteRequest(BaseModel):
    uri: str = Field(..., min_length=1)


class FavoriteMovieResponse(BaseModel):
    uri: str
    title: str
    posterUrl: str | None = None
    year: int | None = None
    runtime: int | None = None
    certification: str | None = None
    director: str | None = None
    genres: list[str] = Field(default_factory=list)
    description: str | None = None
    rating: float | None = None
    relationReason: str | None = None
    addedAt: datetime | None = None


class FavoritesResponse(BaseModel):
    favorites: list[FavoriteMovieResponse]
