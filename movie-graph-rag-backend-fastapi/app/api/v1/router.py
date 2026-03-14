from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.history import router as history_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.movies import router as movies_router
from app.api.v1.endpoints.recommendation import router as recommendation_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(history_router)
api_router.include_router(movies_router)
api_router.include_router(recommendation_router)
api_router.include_router(users_router)
