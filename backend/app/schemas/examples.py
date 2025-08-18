"""
Example usage of the PaginatedResponse generic schema
"""

from typing import List
from .dns import PaginatedResponse, Zone, DNSRecord, Forwarder

# Example usage of PaginatedResponse with different types

def create_paginated_zones_response(zones: List[Zone], total: int, page: int, per_page: int) -> PaginatedResponse[Zone]:
    """Create a paginated response for zones"""
    return PaginatedResponse[Zone](
        items=zones,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page  # This will be recalculated by the validator
    )

def create_paginated_records_response(records: List[DNSRecord], total: int, page: int, per_page: int) -> PaginatedResponse[DNSRecord]:
    """Create a paginated response for DNS records"""
    return PaginatedResponse[DNSRecord](
        items=records,
        total=total,
        page=page,
        per_page=per_page,
        pages=0  # Will be automatically calculated
    )

def create_paginated_forwarders_response(forwarders: List[Forwarder], total: int, page: int, per_page: int) -> PaginatedResponse[Forwarder]:
    """Create a paginated response for forwarders"""
    return PaginatedResponse[Forwarder](
        items=forwarders,
        total=total,
        page=page,
        per_page=per_page,
        pages=0  # Will be automatically calculated
    )

# Example of how to use in API endpoints:
"""
from fastapi import APIRouter, Query
from typing import List
from ..schemas.dns import Zone, PaginatedResponse

router = APIRouter()

@router.get("/zones", response_model=PaginatedResponse[Zone])
async def list_zones(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
) -> PaginatedResponse[Zone]:
    # Get zones from database
    zones = get_zones_from_db(page, per_page)
    total = get_total_zones_count()
    
    return PaginatedResponse[Zone](
        items=zones,
        total=total,
        page=page,
        per_page=per_page,
        pages=0  # Automatically calculated
    )
"""