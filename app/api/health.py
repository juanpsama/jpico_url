
from fastapi import APIRouter


router = APIRouter(tags=["Health Check"])

@router.get("/")
async def health_check():
    return {"status": "ok"}