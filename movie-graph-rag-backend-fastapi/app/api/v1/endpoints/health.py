from fastapi import APIRouter

from app.core.database import ping_mongo

router = APIRouter(prefix="/health")


@router.get("")
def health_check_v1() -> dict[str, str]:
    return {"status": "ok", "scope": "v1"}


@router.get("/db")
def health_check_db() -> dict[str, str]:
    if ping_mongo():
        return {"status": "ok", "scope": "v1", "database": "mongo"}
    return {"status": "error", "scope": "v1", "database": "mongo"}
