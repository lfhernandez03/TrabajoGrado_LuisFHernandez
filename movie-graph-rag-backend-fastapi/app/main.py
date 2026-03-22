from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.api.di import initialize_di_container
from app.infrastructure.logging import set_trace_id, generate_trace_id


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    print("🚀 Initializing application...")
    connect_to_mongo()
    print("✅ MongoDB connected")
    
    # Initialize dependency injection container
    initialize_di_container()
    print("✅ Dependency injection container initialized")
    
    try:
        yield
    finally:
        # Shutdown
        print("🛑 Shutting down application...")
        close_mongo_connection()
        print("✅ MongoDB closed")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next: Callable):
    """
    Middleware that injects trace IDs into each request for correlation.
    
    If client provides X-Trace-ID header, use that. Otherwise generate a new one.
    This enables end-to-end tracing across all logs.
    """
    trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
    set_trace_id(trace_id)
    
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")
