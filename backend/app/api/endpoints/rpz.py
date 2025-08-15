"""
RPZ management endpoints (stub)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_rpz_rules():
    return {"message": "RPZ management endpoints - TODO"}