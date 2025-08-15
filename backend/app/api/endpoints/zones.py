"""
DNS zones management endpoints (stub)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_zones():
    return {"message": "Zone management endpoints - TODO"}