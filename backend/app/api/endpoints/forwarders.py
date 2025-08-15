"""
Forwarders management endpoints (stub)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_forwarders():
    return {"message": "Forwarders management endpoints - TODO"}