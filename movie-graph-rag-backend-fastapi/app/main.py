from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo


@asynccontextmanager
async def lifespan(_: FastAPI):
    connect_to_mongo()
    try:
        yield
    finally:
        close_mongo_connection()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")
