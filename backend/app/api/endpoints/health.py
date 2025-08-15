"""
Health monitoring endpoints (stub)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_status():
    return {"message": "Health monitoring endpoints - TODO"}