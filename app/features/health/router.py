from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/health")
async def get_health():
    return {"status": "ok"}
