from fastapi import APIRouter

router = APIRouter(prefix="/health")


@router.get("")
def health_check_v1() -> dict[str, str]:
    return {"status": "ok", "scope": "v1"}
