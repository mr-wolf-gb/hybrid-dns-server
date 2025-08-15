"""
DNS records management endpoints (stub)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_records():
    return {"message": "DNS records management endpoints - TODO"}