from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.connections import router as connections_router
from app.api.v1.endpoints.clusters import router as clusters_router
from app.api.v1.endpoints.graph import router as graph_router
from app.api.v1.endpoints.history import router as history_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.movies import router as movies_router
from app.api.v1.endpoints.recommendation import router as recommendation_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(history_router)
api_router.include_router(movies_router)
api_router.include_router(recommendation_router)
api_router.include_router(connections_router)
api_router.include_router(graph_router)
api_router.include_router(clusters_router, prefix="/clusters")
api_router.include_router(users_router)
