from pydantic import BaseModel


class MovieResponse(BaseModel):
    uri: str
    title: str
    posterUrl: str | None = None
    tmdbId: str | None = None
    year: int | None = None
    runtime: int | None = None
    certification: str | None = None
    director: str | None = None
    genres: list[str] | None = None
    description: str | None = None
    rating: float | None = None
    imdbRating: float | None = None
    relationReason: str | None = None


class MovieSuggestionResponse(BaseModel):
    uri: str
    title: str
    director: str | None = None


class ConnectionNodeResponse(BaseModel):
    uri: str
    label: str
    type: str


class ConnectionEdgeResponse(BaseModel):
    from_: str
    to: str
    label: str
    property: str

    class Config:
        populate_by_name = True


class ConnectionPathStepResponse(BaseModel):
    step: int
    description: str
    node: ConnectionNodeResponse


class ConnectionExplorerResponse(BaseModel):
    found: bool
    nodes: list[ConnectionNodeResponse]
    edges: list[ConnectionEdgeResponse]
    pathSteps: list[ConnectionPathStepResponse]
    distance: int
    sparqlQuery: str
    executionTimeMs: int
    fromTitle: str | None = None
    toTitle: str | None = None
