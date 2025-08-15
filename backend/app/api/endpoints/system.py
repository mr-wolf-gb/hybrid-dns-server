"""
System administration endpoints (stub)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def system_info():
    return {"message": "System administration endpoints - TODO"}