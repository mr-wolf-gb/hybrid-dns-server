# Design Document - DNS Management Completion

## Overview

This design document outlines the architecture and implementation approach for completing the Hybrid DNS Server project. The design focuses on creating a robust, scalable, and maintainable system that transforms the existing foundation into a production-ready DNS management platform.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │ React Web Interface │    │     WebSocket Client            │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐ │
│  │ Nginx Proxy     │ │ Rate Limiting   │ │ SSL Termination     │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐ │
│  │ FastAPI Backend │ │ Authentication  │ │ WebSocket Server    │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐ │
│  │ BIND9 Config    │ │ Zone Manager    │ │ RPZ Manager         │ │
│  │ Manager         │ │                 │ │                     │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘ │
│  ┌─────────────────┐ ┌─────────────────┐                       │
│  │ Health Monitor  │ │ Threat Intel    │                       │
│  └─────────────────┘ └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐ │
│  │ SQLAlchemy ORM  │ │ PostgreSQL DB   │ │ BIND9 Config Files  │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│  ┌─────────────────┐ ┌─────────────────────────────────────────┐ │
│  │ BIND9 DNS       │ │ Threat Intelligence Feeds               │ │
│  │ Server          │ │                                         │ │
│  └─────────────────┘ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 1. System Components

### 1.1 Core Components

- **Frontend Layer**: React-based web interface with real-time updates
- **API Gateway**: Nginx with SSL termination and rate limiting
- **Application Layer**: FastAPI backend with WebSocket support
- **Service Layer**: Business logic services for DNS management
- **Data Layer**: PostgreSQL database with SQLAlchemy ORM
- **DNS Layer**: BIND9 server with dynamic configuration management

### 1.2 Integration Points

- **Database ↔ BIND9**: Automatic configuration file generation
- **Frontend ↔ Backend**: REST API and WebSocket connections
- **Backend ↔ BIND9**: Configuration file management and service control
- **Database ↔ Services**: Real-time data synchronization
- **External Feeds**: Automated threat intelligence updates

## 2. Database Models Implementation

### 2.1 SQLAlchemy Models Structure

```python
# backend/app/models/dns.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Zone(Base):
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    zone_type = Column(String(20), nullable=False)  # master, slave, forward
    file_path = Column(String(500), nullable=True)
    master_servers = Column(JSON, nullable=True)
    forwarders = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    serial = Column(Integer, nullable=True)
    refresh = Column(Integer, default=10800)
    retry = Column(Integer, default=3600)
    expire = Column(Integer, default=604800)
    minimum = Column(Integer, default=86400)
    email = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    records = relationship("DNSRecord", back_populates="zone", cascade="all, delete-orphan")

class DNSRecord(Base):
    __tablename__ = "dns_records"
    
    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    name = Column(String(255), nullable=False)
    record_type = Column(String(10), nullable=False)
    value = Column(String(500), nullable=False)
    ttl = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    port = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    zone = relationship("Zone", back_populates="records")

class Forwarder(Base):
    __tablename__ = "forwarders"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domains = Column(JSON, nullable=False)
    forwarder_type = Column(String(20), nullable=False)
    servers = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    health_check_enabled = Column(Boolean, default=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    health_checks = relationship("ForwarderHealth", back_populates="forwarder")

class ForwarderHealth(Base):
    __tablename__ = "forwarder_health"
    
    id = Column(Integer, primary_key=True, index=True)
    forwarder_id = Column(Integer, ForeignKey("forwarders.id"), nullable=False)
    server_ip = Column(String(45), nullable=False)
    status = Column(String(20), nullable=False)
    response_time = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    forwarder = relationship("Forwarder", back_populates="health_checks")

class RPZRule(Base):
    __tablename__ = "rpz_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True)
    rpz_zone = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    redirect_target = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    source = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```### 2.2
 Pydantic Schemas

```python
# backend/app/schemas/dns.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ZoneType(str, Enum):
    MASTER = "master"
    SLAVE = "slave"
    FORWARD = "forward"

class RecordType(str, Enum):
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    SRV = "SRV"
    PTR = "PTR"
    NS = "NS"
    SOA = "SOA"

class ForwarderType(str, Enum):
    ACTIVE_DIRECTORY = "active_directory"
    INTRANET = "intranet"
    PUBLIC = "public"

class RPZAction(str, Enum):
    BLOCK = "block"
    REDIRECT = "redirect"
    PASSTHRU = "passthru"

# Zone Schemas
class ZoneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    zone_type: ZoneType
    email: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    refresh: int = Field(default=10800, ge=300, le=86400)
    retry: int = Field(default=3600, ge=300, le=86400)
    expire: int = Field(default=604800, ge=86400, le=2419200)
    minimum: int = Field(default=86400, ge=300, le=86400)

class ZoneCreate(ZoneBase):
    master_servers: Optional[List[str]] = None
    forwarders: Optional[List[str]] = None

class ZoneUpdate(BaseModel):
    email: Optional[str] = None
    description: Optional[str] = None
    refresh: Optional[int] = Field(None, ge=300, le=86400)
    retry: Optional[int] = Field(None, ge=300, le=86400)
    expire: Optional[int] = Field(None, ge=86400, le=2419200)
    minimum: Optional[int] = Field(None, ge=300, le=86400)
    is_active: Optional[bool] = None

class Zone(ZoneBase):
    id: int
    serial: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    record_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# DNS Record Schemas
class DNSRecordBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    record_type: RecordType
    value: str = Field(..., min_length=1, max_length=500)
    ttl: Optional[int] = Field(None, ge=60, le=86400)
    priority: Optional[int] = Field(None, ge=0, le=65535)
    weight: Optional[int] = Field(None, ge=0, le=65535)
    port: Optional[int] = Field(None, ge=1, le=65535)

class DNSRecordCreate(DNSRecordBase):
    @validator('priority')
    def validate_priority(cls, v, values):
        if values.get('record_type') in ['MX', 'SRV'] and v is None:
            raise ValueError('Priority is required for MX and SRV records')
        return v

class DNSRecordUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[str] = Field(None, min_length=1, max_length=500)
    ttl: Optional[int] = Field(None, ge=60, le=86400)
    priority: Optional[int] = Field(None, ge=0, le=65535)
    weight: Optional[int] = Field(None, ge=0, le=65535)
    port: Optional[int] = Field(None, ge=1, le=65535)
    is_active: Optional[bool] = None

class DNSRecord(DNSRecordBase):
    id: int
    zone_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Forwarder Schemas
class ForwarderServer(BaseModel):
    ip: str = Field(..., regex=r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
    port: int = Field(default=53, ge=1, le=65535)
    priority: int = Field(default=1, ge=1, le=10)

class ForwarderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    domains: List[str] = Field(..., min_items=1)
    forwarder_type: ForwarderType
    servers: List[ForwarderServer] = Field(..., min_items=1)
    description: Optional[str] = None
    health_check_enabled: bool = True

class ForwarderCreate(ForwarderBase):
    pass

class ForwarderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domains: Optional[List[str]] = Field(None, min_items=1)
    servers: Optional[List[ForwarderServer]] = Field(None, min_items=1)
    description: Optional[str] = None
    health_check_enabled: Optional[bool] = None
    is_active: Optional[bool] = None

class Forwarder(ForwarderBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    health_status: Optional[str] = "unknown"
    
    class Config:
        from_attributes = True
```# R
PZ Rule Schemas
class RPZRuleBase(BaseModel):
    domain: str = Field(..., min_length=1, max_length=255)
    rpz_zone: str = Field(..., min_length=1, max_length=50)
    action: RPZAction
    redirect_target: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

class RPZRuleCreate(RPZRuleBase):
    @validator('redirect_target')
    def validate_redirect_target(cls, v, values):
        if values.get('action') == RPZAction.REDIRECT and not v:
            raise ValueError('Redirect target is required for redirect action')
        return v

class RPZRuleUpdate(BaseModel):
    domain: Optional[str] = Field(None, min_length=1, max_length=255)
    action: Optional[RPZAction] = None
    redirect_target: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class RPZRule(RPZRuleBase):
    id: int
    is_active: bool
    source: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Response Schemas
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int

class HealthCheckResult(BaseModel):
    server_ip: str
    status: str
    response_time: Optional[int]
    error_message: Optional[str]
    checked_at: datetime

class ZoneValidationResult(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []

class SystemStatus(BaseModel):
    bind9_running: bool
    bind9_config_valid: bool
    database_connected: bool
    zones_loaded: int
    active_forwarders: int
    rpz_rules_active: int
```

## 3. API Endpoints Implementation

### 3.1 DNS Zones API

```python
# backend/app/api/endpoints/zones.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...models.dns import Zone, DNSRecord
from ...schemas.dns import ZoneCreate, ZoneUpdate, Zone as ZoneSchema, PaginatedResponse
from ...services.zone_service import ZoneService
from ...services.bind_service import BindService

router = APIRouter()

@router.get("/", response_model=List[ZoneSchema])
async def list_zones(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    zone_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all DNS zones with optional filtering"""
    zone_service = ZoneService(db)
    zones = await zone_service.get_zones(
        skip=skip, 
        limit=limit, 
        zone_type=zone_type, 
        active_only=active_only
    )
    return zones

@router.post("/", response_model=ZoneSchema)
async def create_zone(
    zone_data: ZoneCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new DNS zone"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    # Create zone in database
    zone = await zone_service.create_zone(zone_data)
    
    # Generate BIND9 configuration
    await bind_service.create_zone_file(zone)
    await bind_service.reload_configuration()
    
    return zone

@router.get("/{zone_id}", response_model=ZoneSchema)
async def get_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific DNS zone"""
    zone_service = ZoneService(db)
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone

@router.put("/{zone_id}", response_model=ZoneSchema)
async def update_zone(
    zone_id: int,
    zone_data: ZoneUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a DNS zone"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    zone = await zone_service.update_zone(zone_id, zone_data)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Update BIND9 configuration
    await bind_service.update_zone_file(zone)
    await bind_service.reload_configuration()
    
    return zone

@router.delete("/{zone_id}")
async def delete_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a DNS zone"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    success = await zone_service.delete_zone(zone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Remove from BIND9 configuration
    await bind_service.delete_zone_file(zone_id)
    await bind_service.reload_configuration()
    
    return {"message": "Zone deleted successfully"}

@router.post("/{zone_id}/validate")
async def validate_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate zone configuration"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    validation_result = await bind_service.validate_zone(zone)
    return validation_result
```

### 3.2 DNS Records API

```python
# backend/app/api/endpoints/dns_records.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...schemas.dns import DNSRecordCreate, DNSRecordUpdate, DNSRecord as DNSRecordSchema
from ...services.record_service import RecordService
from ...services.bind_service import BindService

router = APIRouter()

@router.get("/zones/{zone_id}/records", response_model=List[DNSRecordSchema])
async def list_records(
    zone_id: int,
    record_type: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List DNS records for a zone"""
    record_service = RecordService(db)
    records = await record_service.get_records(
        zone_id=zone_id,
        record_type=record_type,
        name=name,
        active_only=active_only
    )
    return records

@router.post("/zones/{zone_id}/records", response_model=DNSRecordSchema)
async def create_record(
    zone_id: int,
    record_data: DNSRecordCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new DNS record"""
    record_service = RecordService(db)
    bind_service = BindService()
    
    # Create record in database
    record = await record_service.create_record(zone_id, record_data)
    
    # Update zone file
    await bind_service.update_zone_file_from_db(zone_id)
    await bind_service.reload_zone(zone_id)
    
    return record

@router.put("/records/{record_id}", response_model=DNSRecordSchema)
async def update_record(
    record_id: int,
    record_data: DNSRecordUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a DNS record"""
    record_service = RecordService(db)
    bind_service = BindService()
    
    record = await record_service.update_record(record_id, record_data)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Update zone file
    await bind_service.update_zone_file_from_db(record.zone_id)
    await bind_service.reload_zone(record.zone_id)
    
    return record

@router.delete("/records/{record_id}")
async def delete_record(
    record_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a DNS record"""
    record_service = RecordService(db)
    bind_service = BindService()
    
    zone_id = await record_service.get_record_zone_id(record_id)
    success = await record_service.delete_record(record_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Update zone file
    if zone_id:
        await bind_service.update_zone_file_from_db(zone_id)
        await bind_service.reload_zone(zone_id)
    
    return {"message": "Record deleted successfully"}

@router.post("/records/{record_id}/toggle")
async def toggle_record(
    record_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle record active status"""
    record_service = RecordService(db)
    bind_service = BindService()
    
    record = await record_service.toggle_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Update zone file
    await bind_service.update_zone_file_from_db(record.zone_id)
    await bind_service.reload_zone(record.zone_id)
    
    return record
```### 
3.3 Forwarders API

```python
# backend/app/api/endpoints/forwarders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...schemas.dns import ForwarderCreate, ForwarderUpdate, Forwarder as ForwarderSchema
from ...services.forwarder_service import ForwarderService
from ...services.bind_service import BindService

router = APIRouter()

@router.get("/", response_model=List[ForwarderSchema])
async def list_forwarders(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all DNS forwarders"""
    forwarder_service = ForwarderService(db)
    forwarders = await forwarder_service.get_forwarders()
    return forwarders

@router.post("/", response_model=ForwarderSchema)
async def create_forwarder(
    forwarder_data: ForwarderCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new DNS forwarder"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService()
    
    # Create forwarder in database
    forwarder = await forwarder_service.create_forwarder(forwarder_data)
    
    # Update BIND9 configuration
    await bind_service.update_forwarder_configuration()
    await bind_service.reload_configuration()
    
    return forwarder

@router.put("/{forwarder_id}", response_model=ForwarderSchema)
async def update_forwarder(
    forwarder_id: int,
    forwarder_data: ForwarderUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a DNS forwarder"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService()
    
    forwarder = await forwarder_service.update_forwarder(forwarder_id, forwarder_data)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    # Update BIND9 configuration
    await bind_service.update_forwarder_configuration()
    await bind_service.reload_configuration()
    
    return forwarder

@router.delete("/{forwarder_id}")
async def delete_forwarder(
    forwarder_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a DNS forwarder"""
    forwarder_service = ForwarderService(db)
    bind_service = BindService()
    
    success = await forwarder_service.delete_forwarder(forwarder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    # Update BIND9 configuration
    await bind_service.update_forwarder_configuration()
    await bind_service.reload_configuration()
    
    return {"message": "Forwarder deleted successfully"}

@router.post("/{forwarder_id}/test")
async def test_forwarder(
    forwarder_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Test forwarder connectivity"""
    forwarder_service = ForwarderService(db)
    
    forwarder = await forwarder_service.get_forwarder(forwarder_id)
    if not forwarder:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    
    test_results = await forwarder_service.test_forwarder(forwarder)
    return {"results": test_results}

@router.get("/{forwarder_id}/health")
async def get_forwarder_health(
    forwarder_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get forwarder health status"""
    forwarder_service = ForwarderService(db)
    health_status = await forwarder_service.get_health_status(forwarder_id)
    return health_status
```### 
3.4 RPZ Security API

```python
# backend/app/api/endpoints/rpz.py
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...schemas.dns import RPZRuleCreate, RPZRuleUpdate, RPZRule as RPZRuleSchema
from ...services.rpz_service import RPZService
from ...services.bind_service import BindService
from ...services.threat_feed_service import ThreatFeedService

router = APIRouter()

@router.get("/rules", response_model=List[RPZRuleSchema])
async def list_rpz_rules(
    category: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List RPZ rules with filtering"""
    rpz_service = RPZService(db)
    rules = await rpz_service.get_rules(
        category=category,
        action=action,
        search=search,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return rules

@router.post("/rules", response_model=RPZRuleSchema)
async def create_rpz_rule(
    rule_data: RPZRuleCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new RPZ rule"""
    rpz_service = RPZService(db)
    bind_service = BindService()
    
    # Create rule in database
    rule = await rpz_service.create_rule(rule_data)
    
    # Update RPZ zone files
    await bind_service.update_rpz_zone_file(rule.rpz_zone)
    await bind_service.reload_configuration()
    
    return rule

@router.put("/rules/{rule_id}", response_model=RPZRuleSchema)
async def update_rpz_rule(
    rule_id: int,
    rule_data: RPZRuleUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update an RPZ rule"""
    rpz_service = RPZService(db)
    bind_service = BindService()
    
    rule = await rpz_service.update_rule(rule_id, rule_data)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update RPZ zone files
    await bind_service.update_rpz_zone_file(rule.rpz_zone)
    await bind_service.reload_configuration()
    
    return rule

@router.delete("/rules/{rule_id}")
async def delete_rpz_rule(
    rule_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete an RPZ rule"""
    rpz_service = RPZService(db)
    bind_service = BindService()
    
    rpz_zone = await rpz_service.get_rule_zone(rule_id)
    success = await rpz_service.delete_rule(rule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update RPZ zone files
    if rpz_zone:
        await bind_service.update_rpz_zone_file(rpz_zone)
        await bind_service.reload_configuration()
    
    return {"message": "Rule deleted successfully"}

@router.post("/rules/bulk-import")
async def bulk_import_rules(
    category: str,
    domains: List[str],
    action: str = "block",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Bulk import RPZ rules"""
    rpz_service = RPZService(db)
    
    # Start background task for bulk import
    background_tasks.add_task(
        rpz_service.bulk_import_rules,
        category=category,
        domains=domains,
        action=action
    )
    
    return {"message": f"Bulk import started for {len(domains)} domains"}

@router.post("/threat-feeds/update")
async def update_threat_feeds(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update threat intelligence feeds"""
    threat_feed_service = ThreatFeedService(db)
    
    # Start background task for threat feed update
    background_tasks.add_task(threat_feed_service.update_all_feeds)
    
    return {"message": "Threat feed update started"}

@router.get("/categories")
async def get_rpz_categories(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get available RPZ categories"""
    rpz_service = RPZService(db)
    categories = await rpz_service.get_categories()
    return {"categories": categories}

@router.get("/statistics")
async def get_rpz_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get RPZ statistics"""
    rpz_service = RPZService(db)
    stats = await rpz_service.get_statistics()
    return stats
```

## 4. Service Layer Implementation

### 4.1 Zone Service

```python
# backend/app/services/zone_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime

from ..models.dns import Zone, DNSRecord
from ..schemas.dns import ZoneCreate, ZoneUpdate
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class ZoneService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_zones(
        self, 
        skip: int = 0, 
        limit: int = 100,
        zone_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Zone]:
        """Get zones with optional filtering"""
        query = self.db.query(Zone)
        
        if active_only:
            query = query.filter(Zone.is_active == True)
        
        if zone_type:
            query = query.filter(Zone.zone_type == zone_type)
        
        zones = query.offset(skip).limit(limit).all()
        
        # Add record count for each zone
        for zone in zones:
            zone.record_count = self.db.query(DNSRecord).filter(
                DNSRecord.zone_id == zone.id,
                DNSRecord.is_active == True
            ).count()
        
        return zones
    
    async def get_zone(self, zone_id: int) -> Optional[Zone]:
        """Get a specific zone by ID"""
        zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
        if zone:
            zone.record_count = self.db.query(DNSRecord).filter(
                DNSRecord.zone_id == zone.id,
                DNSRecord.is_active == True
            ).count()
        return zone
    
    async def create_zone(self, zone_data: ZoneCreate) -> Zone:
        """Create a new DNS zone"""
        # Generate initial serial number
        serial = int(datetime.now().strftime("%Y%m%d01"))
        
        zone = Zone(
            name=zone_data.name,
            zone_type=zone_data.zone_type,
            email=zone_data.email,
            description=zone_data.description,
            refresh=zone_data.refresh,
            retry=zone_data.retry,
            expire=zone_data.expire,
            minimum=zone_data.minimum,
            serial=serial,
            master_servers=zone_data.master_servers,
            forwarders=zone_data.forwarders,
            is_active=True
        )
        
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        
        logger.info(f"Created zone: {zone.name} (ID: {zone.id})")
        return zone
    
    async def update_zone(self, zone_id: int, zone_data: ZoneUpdate) -> Optional[Zone]:
        """Update an existing zone"""
        zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return None
        
        # Update fields if provided
        update_data = zone_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(zone, field, value)
        
        # Increment serial number if zone content changed
        if any(field in update_data for field in ['refresh', 'retry', 'expire', 'minimum']):
            zone.serial = self._increment_serial(zone.serial)
        
        zone.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(zone)
        
        logger.info(f"Updated zone: {zone.name} (ID: {zone.id})")
        return zone
    
    async def delete_zone(self, zone_id: int) -> bool:
        """Delete a zone and all its records"""
        zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return False
        
        # Delete all records first (cascade should handle this)
        self.db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id).delete()
        
        # Delete the zone
        self.db.delete(zone)
        self.db.commit()
        
        logger.info(f"Deleted zone: {zone.name} (ID: {zone.id})")
        return True
    
    def _increment_serial(self, current_serial: int) -> int:
        """Increment zone serial number"""
        today = datetime.now().strftime("%Y%m%d")
        current_date = str(current_serial)[:8]
        
        if current_date == today:
            # Same day, increment sequence
            sequence = int(str(current_serial)[8:]) + 1
            return int(f"{today}{sequence:02d}")
        else:
            # New day, start with 01
            return int(f"{today}01")
```### 4.
2 Enhanced BIND Service

```python
# backend/app/services/bind_service.py (Enhanced)
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from jinja2 import Template

from ..core.config import get_settings
from ..core.logging_config import get_bind_logger
from ..models.dns import Zone, DNSRecord, Forwarder, RPZRule

logger = get_bind_logger()

class BindService:
    """Enhanced BIND9 service management with configuration generation"""
    
    def __init__(self):
        settings = get_settings()
        self.service_name = settings.BIND9_SERVICE_NAME
        self.config_dir = settings.config_dir
        self.zones_dir = settings.zones_dir
        self.rpz_dir = settings.rpz_dir
    
    async def create_zone_file(self, zone: Zone) -> bool:
        """Generate and create BIND9 zone file from database"""
        try:
            if zone.zone_type == "master":
                await self._create_master_zone_file(zone)
            elif zone.zone_type == "forward":
                await self._update_forwarder_configuration()
            
            return True
        except Exception as e:
            logger.error(f"Failed to create zone file for {zone.name}: {e}")
            return False
    
    async def _create_master_zone_file(self, zone: Zone):
        """Create master zone file with SOA and records"""
        zone_file_path = self.zones_dir / f"db.{zone.name}"
        
        # Zone file template
        zone_template = Template("""$TTL {{ zone.minimum }}
@       IN  SOA {{ zone.name }}. {{ zone.email.replace('@', '.') }}. (
            {{ zone.serial }}  ; serial
            {{ zone.refresh }}        ; refresh
            {{ zone.retry }}        ; retry
            {{ zone.expire }}      ; expire
            {{ zone.minimum }} )       ; minimum

; Name servers
{% for ns_record in ns_records %}
@       IN  NS  {{ ns_record.value }}
{% endfor %}

; DNS Records
{% for record in records %}
{% if record.is_active %}
{{ record.name }}{% if record.ttl %}    {{ record.ttl }}{% endif %}    IN  {{ record.record_type }}{% if record.priority %}  {{ record.priority }}{% endif %}{% if record.weight %}  {{ record.weight }}{% endif %}{% if record.port %}  {{ record.port }}{% endif %}  {{ record.value }}
{% endif %}
{% endfor %}
""")
        
        # Get records from database
        from ..core.database import database
        records = await database.fetch_all(
            "SELECT * FROM dns_records WHERE zone_id = :zone_id ORDER BY record_type, name",
            {"zone_id": zone.id}
        )
        
        # Separate NS records for SOA section
        ns_records = [r for r in records if r['record_type'] == 'NS']
        other_records = [r for r in records if r['record_type'] != 'NS']
        
        # Generate zone file content
        zone_content = zone_template.render(
            zone=zone,
            ns_records=ns_records,
            records=other_records
        )
        
        # Write zone file
        zone_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(zone_file_path, 'w') as f:
            f.write(zone_content)
        
        # Set proper permissions
        zone_file_path.chmod(0o644)
        
        logger.info(f"Created zone file: {zone_file_path}")
    
    async def update_zone_file_from_db(self, zone_id: int) -> bool:
        """Update zone file from database records"""
        try:
            from ..core.database import database
            
            # Get zone information
            zone_data = await database.fetch_one(
                "SELECT * FROM zones WHERE id = :zone_id",
                {"zone_id": zone_id}
            )
            
            if not zone_data:
                return False
            
            # Create zone object
            zone = type('Zone', (), zone_data)()
            zone.id = zone_data['id']
            
            await self._create_master_zone_file(zone)
            return True
            
        except Exception as e:
            logger.error(f"Failed to update zone file for zone {zone_id}: {e}")
            return False
    
    async def update_forwarder_configuration(self) -> bool:
        """Update BIND9 forwarder configuration from database"""
        try:
            from ..core.database import database
            
            # Get all active forwarders
            forwarders = await database.fetch_all(
                "SELECT * FROM forwarders WHERE is_active = true"
            )
            
            # Generate forwarder configuration
            forwarder_config = self._generate_forwarder_config(forwarders)
            
            # Write to zones.conf
            zones_conf_path = self.config_dir / "zones.conf"
            with open(zones_conf_path, 'w') as f:
                f.write(forwarder_config)
            
            logger.info("Updated forwarder configuration")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update forwarder configuration: {e}")
            return False
    
    def _generate_forwarder_config(self, forwarders: List[Dict]) -> str:
        """Generate BIND9 forwarder configuration"""
        config_lines = [
            "//",
            "// Dynamic Forwarder Configuration",
            "// Generated automatically - do not edit manually",
            "//",
            ""
        ]
        
        for forwarder in forwarders:
            domains = json.loads(forwarder['domains']) if isinstance(forwarder['domains'], str) else forwarder['domains']
            servers = json.loads(forwarder['servers']) if isinstance(forwarder['servers'], str) else forwarder['servers']
            
            for domain in domains:
                config_lines.extend([
                    f"// {forwarder['name']} - {forwarder['forwarder_type']}",
                    f'zone "{domain}" {{',
                    "    type forward;",
                    "    forward first;",
                    "    forwarders {"
                ])
                
                # Add server IPs
                for server in servers:
                    if isinstance(server, dict):
                        ip = server.get('ip')
                        port = server.get('port', 53)
                        if port != 53:
                            config_lines.append(f"        {ip} port {port};")
                        else:
                            config_lines.append(f"        {ip};")
                    else:
                        config_lines.append(f"        {server};")
                
                config_lines.extend([
                    "    };",
                    "};",
                    ""
                ])
        
        return "\n".join(config_lines)
    
    async def update_rpz_zone_file(self, rpz_zone: str) -> bool:
        """Update RPZ zone file from database rules"""
        try:
            from ..core.database import database
            
            # Get all active rules for this RPZ zone
            rules = await database.fetch_all(
                "SELECT * FROM rpz_rules WHERE rpz_zone = :rpz_zone AND is_active = true",
                {"rpz_zone": rpz_zone}
            )
            
            # Generate RPZ zone file
            rpz_content = self._generate_rpz_zone_content(rpz_zone, rules)
            
            # Write RPZ zone file
            rpz_file_path = self.rpz_dir / f"db.rpz.{rpz_zone}"
            rpz_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(rpz_file_path, 'w') as f:
                f.write(rpz_content)
            
            rpz_file_path.chmod(0o644)
            
            logger.info(f"Updated RPZ zone file: {rpz_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update RPZ zone {rpz_zone}: {e}")
            return False
    
    def _generate_rpz_zone_content(self, rpz_zone: str, rules: List[Dict]) -> str:
        """Generate RPZ zone file content"""
        from datetime import datetime
        
        serial = int(datetime.now().strftime("%Y%m%d%H"))
        
        lines = [
            "$TTL 300",
            f"@   IN  SOA localhost. admin.localhost. (",
            f"    {serial}  ; serial",
            "    3600        ; refresh",
            "    1800        ; retry",
            "    604800      ; expire",
            "    300 )       ; minimum",
            "    IN  NS  localhost.",
            "",
            f"; RPZ rules for {rpz_zone}",
            ""
        ]
        
        for rule in rules:
            domain = rule['domain']
            action = rule['action']
            redirect_target = rule.get('redirect_target')
            
            if action == "block":
                lines.append(f"{domain}         CNAME   .")
                lines.append(f"*.{domain}       CNAME   .")
            elif action == "redirect" and redirect_target:
                lines.append(f"{domain}         CNAME   {redirect_target}")
                lines.append(f"*.{domain}       CNAME   {redirect_target}")
            elif action == "passthru":
                lines.append(f"{domain}         CNAME   rpz-passthru.")
                lines.append(f"*.{domain}       CNAME   rpz-passthru.")
        
        return "\n".join(lines)
    
    async def reload_zone(self, zone_id: int) -> bool:
        """Reload a specific zone"""
        try:
            from ..core.database import database
            
            zone_data = await database.fetch_one(
                "SELECT name FROM zones WHERE id = :zone_id",
                {"zone_id": zone_id}
            )
            
            if not zone_data:
                return False
            
            result = await self._run_command(["rndc", "reload", zone_data['name']])
            return result["returncode"] == 0
            
        except Exception as e:
            logger.error(f"Failed to reload zone {zone_id}: {e}")
            return False
    
    async def validate_zone(self, zone: Zone) -> Dict:
        """Validate zone configuration"""
        try:
            zone_file_path = self.zones_dir / f"db.{zone.name}"
            
            if not zone_file_path.exists():
                return {
                    "valid": False,
                    "errors": ["Zone file does not exist"],
                    "warnings": []
                }
            
            # Run named-checkzone
            result = await self._run_command([
                "named-checkzone", zone.name, str(zone_file_path)
            ])
            
            return {
                "valid": result["returncode"] == 0,
                "errors": result["stderr"].split("\n") if result["stderr"] else [],
                "warnings": []
            }
            
        except Exception as e:
            logger.error(f"Failed to validate zone {zone.name}: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
```

## 5. Frontend Implementation

### 5.1 DNS Zones Management Page

```typescript
// frontend/src/pages/DNSZones.tsx
import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PlusIcon, PencilIcon, TrashIcon, EyeIcon } from '@heroicons/react/24/outline'
import { zonesService } from '@/services/api'
import { Zone, ZoneFormData } from '@/types'
import { Card, Button, Table, Modal, Loading, Badge } from '@/components/ui'
import ZoneModal from '@/components/zones/ZoneModal'
import RecordsView from '@/components/zones/RecordsView'
import { toast } from 'react-toastify'

const DNSZones: React.FC = () => {
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null)
  const [showZoneModal, setShowZoneModal] = useState(false)
  const [showRecordsModal, setShowRecordsModal] = useState(false)
  const [editingZone, setEditingZone] = useState<Zone | null>(null)
  
  const queryClient = useQueryClient()
  
  const { data: zones, isLoading, error } = useQuery({
    queryKey: ['zones'],
    queryFn: () => zonesService.getZones(),
  })
  
  const createZoneMutation = useMutation({
    mutationFn: (zoneData: ZoneFormData) => zonesService.createZone(zoneData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      setShowZoneModal(false)
      toast.success('Zone created successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to create zone')
    }
  })
  
  const updateZoneMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ZoneFormData> }) =>
      zonesService.updateZone(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      setShowZoneModal(false)
      setEditingZone(null)
      toast.success('Zone updated successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to update zone')
    }
  })
  
  const deleteZoneMutation = useMutation({
    mutationFn: (zoneId: number) => zonesService.deleteZone(zoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      toast.success('Zone deleted successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to delete zone')
    }
  })
  
  const handleCreateZone = () => {
    setEditingZone(null)
    setShowZoneModal(true)
  }
  
  const handleEditZone = (zone: Zone) => {
    setEditingZone(zone)
    setShowZoneModal(true)
  }
  
  const handleDeleteZone = async (zone: Zone) => {
    if (window.confirm(`Are you sure you want to delete zone "${zone.name}"? This will also delete all DNS records in this zone.`)) {
      deleteZoneMutation.mutate(zone.id)
    }
  }
  
  const handleViewRecords = (zone: Zone) => {
    setSelectedZone(zone)
    setShowRecordsModal(true)
  }
  
  const handleZoneSubmit = (zoneData: ZoneFormData) => {
    if (editingZone) {
      updateZoneMutation.mutate({ id: editingZone.id, data: zoneData })
    } else {
      createZoneMutation.mutate(zoneData)
    }
  }
  
  const columns = [
    {
      header: 'Zone Name',
      accessor: 'name' as keyof Zone,
      cell: (zone: Zone) => (
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {zone.name}
          </div>
          {zone.description && (
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {zone.description}
            </div>
          )}
        </div>
      )
    },
    {
      header: 'Type',
      accessor: 'zone_type' as keyof Zone,
      cell: (zone: Zone) => (
        <Badge 
          variant={zone.zone_type === 'master' ? 'success' : 'info'}
          className="capitalize"
        >
          {zone.zone_type}
        </Badge>
      )
    },
    {
      header: 'Records',
      accessor: 'record_count' as keyof Zone,
      cell: (zone: Zone) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {zone.record_count || 0} records
        </span>
      )
    },
    {
      header: 'Status',
      accessor: 'is_active' as keyof Zone,
      cell: (zone: Zone) => (
        <Badge variant={zone.is_active ? 'success' : 'danger'}>
          {zone.is_active ? 'Active' : 'Inactive'}
        </Badge>
      )
    },
    {
      header: 'Serial',
      accessor: 'serial' as keyof Zone,
      cell: (zone: Zone) => (
        <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
          {zone.serial}
        </span>
      )
    },
    {
      header: 'Actions',
      accessor: 'id' as keyof Zone,
      cell: (zone: Zone) => (
        <div className="flex space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleViewRecords(zone)}
            title="View Records"
          >
            <EyeIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEditZone(zone)}
            title="Edit Zone"
          >
            <PencilIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteZone(zone)}
            className="text-red-600 hover:text-red-700"
            title="Delete Zone"
          >
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      )
    }
  ]
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text="Loading DNS zones..." />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 dark:text-red-400">
          Failed to load DNS zones. Please try again.
        </p>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            DNS Zones
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Manage authoritative DNS zones and their records
          </p>
        </div>
        <Button onClick={handleCreateZone} className="flex items-center space-x-2">
          <PlusIcon className="h-4 w-4" />
          <span>Add Zone</span>
        </Button>
      </div>
      
      {/* Zones table */}
      <Card>
        <Table
          data={zones?.data || []}
          columns={columns}
          emptyMessage="No DNS zones found. Create your first zone to get started."
        />
      </Card>
      
      {/* Zone modal */}
      <Modal
        isOpen={showZoneModal}
        onClose={() => {
          setShowZoneModal(false)
          setEditingZone(null)
        }}
        title={editingZone ? 'Edit DNS Zone' : 'Create DNS Zone'}
        size="lg"
      >
        <ZoneModal
          zone={editingZone}
          onSubmit={handleZoneSubmit}
          onCancel={() => {
            setShowZoneModal(false)
            setEditingZone(null)
          }}
          isLoading={createZoneMutation.isPending || updateZoneMutation.isPending}
        />
      </Modal>
      
      {/* Records modal */}
      <Modal
        isOpen={showRecordsModal}
        onClose={() => {
          setShowRecordsModal(false)
          setSelectedZone(null)
        }}
        title={`DNS Records - ${selectedZone?.name}`}
        size="xl"
      >
        {selectedZone && (
          <RecordsView
            zone={selectedZone}
            onClose={() => {
              setShowRecordsModal(false)
              setSelectedZone(null)
            }}
          />
        )}
      </Modal>
    </div>
  )
}

export default DNSZones
```### 5.2 
Zone Modal Component

```typescript
// frontend/src/components/zones/ZoneModal.tsx
import React from 'react'
import { useForm } from 'react-hook-form'
import { Zone, ZoneFormData } from '@/types'
import { Button, Input, Select, Card } from '@/components/ui'

interface ZoneModalProps {
  zone?: Zone | null
  onSubmit: (data: ZoneFormData) => void
  onCancel: () => void
  isLoading: boolean
}

const ZoneModal: React.FC<ZoneModalProps> = ({
  zone,
  onSubmit,
  onCancel,
  isLoading
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch
  } = useForm<ZoneFormData>({
    defaultValues: zone ? {
      name: zone.name,
      zone_type: zone.zone_type,
      email: zone.email,
      description: zone.description || '',
      refresh: zone.refresh,
      retry: zone.retry,
      expire: zone.expire,
      minimum: zone.minimum
    } : {
      zone_type: 'master',
      refresh: 10800,
      retry: 3600,
      expire: 604800,
      minimum: 86400
    }
  })
  
  const zoneType = watch('zone_type')
  
  const zoneTypeOptions = [
    { value: 'master', label: 'Master (Authoritative)' },
    { value: 'slave', label: 'Slave (Secondary)' },
    { value: 'forward', label: 'Forward Only' }
  ]
  
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Basic Information */}
      <Card title="Basic Information" className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="Zone Name"
            {...register('name', {
              required: 'Zone name is required',
              pattern: {
                value: /^[a-zA-Z0-9.-]+$/,
                message: 'Invalid zone name format'
              }
            })}
            error={errors.name?.message}
            placeholder="example.local"
            disabled={!!zone} // Don't allow editing zone name
          />
          
          <Select
            label="Zone Type"
            {...register('zone_type', { required: 'Zone type is required' })}
            options={zoneTypeOptions}
            error={errors.zone_type?.message}
          />
          
          <Input
            label="Administrator Email"
            type="email"
            {...register('email', {
              required: 'Administrator email is required',
              pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: 'Invalid email format'
              }
            })}
            error={errors.email?.message}
            placeholder="admin@example.local"
            className="md:col-span-2"
          />
          
          <Input
            label="Description"
            {...register('description')}
            placeholder="Optional description"
            className="md:col-span-2"
          />
        </div>
      </Card>
      
      {/* SOA Settings (for master zones) */}
      {zoneType === 'master' && (
        <Card title="SOA Settings" className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Refresh Interval (seconds)"
              type="number"
              {...register('refresh', {
                required: 'Refresh interval is required',
                min: { value: 300, message: 'Minimum 300 seconds' },
                max: { value: 86400, message: 'Maximum 86400 seconds' }
              })}
              error={errors.refresh?.message}
              placeholder="10800"
            />
            
            <Input
              label="Retry Interval (seconds)"
              type="number"
              {...register('retry', {
                required: 'Retry interval is required',
                min: { value: 300, message: 'Minimum 300 seconds' },
                max: { value: 86400, message: 'Maximum 86400 seconds' }
              })}
              error={errors.retry?.message}
              placeholder="3600"
            />
            
            <Input
              label="Expire Time (seconds)"
              type="number"
              {...register('expire', {
                required: 'Expire time is required',
                min: { value: 86400, message: 'Minimum 86400 seconds' },
                max: { value: 2419200, message: 'Maximum 2419200 seconds' }
              })}
              error={errors.expire?.message}
              placeholder="604800"
            />
            
            <Input
              label="Minimum TTL (seconds)"
              type="number"
              {...register('minimum', {
                required: 'Minimum TTL is required',
                min: { value: 300, message: 'Minimum 300 seconds' },
                max: { value: 86400, message: 'Maximum 86400 seconds' }
              })}
              error={errors.minimum?.message}
              placeholder="86400"
            />
          </div>
          
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
              SOA Settings Guide
            </h4>
            <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
              <li><strong>Refresh:</strong> How often secondary servers check for updates</li>
              <li><strong>Retry:</strong> How long to wait before retrying failed zone transfers</li>
              <li><strong>Expire:</strong> When secondary servers stop answering queries</li>
              <li><strong>Minimum:</strong> Default TTL for records without explicit TTL</li>
            </ul>
          </div>
        </Card>
      )}
      
      {/* Action buttons */}
      <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={isLoading}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          isLoading={isLoading}
          loadingText={zone ? 'Updating...' : 'Creating...'}
        >
          {zone ? 'Update Zone' : 'Create Zone'}
        </Button>
      </div>
    </form>
  )
}

export default ZoneModal
```

## 6. Implementation Tasks

### Phase 1: Database Models and Core Services (Week 1-2)

#### Task 1.1: Database Models
- [ ] Create SQLAlchemy models for all entities
- [ ] Set up proper relationships and constraints
- [ ] Create database migration scripts
- [ ] Add indexes for performance optimization

#### Task 1.2: Pydantic Schemas
- [ ] Create request/response schemas for all endpoints
- [ ] Add comprehensive validation rules
- [ ] Implement custom validators for DNS-specific data
- [ ] Add serialization configurations

#### Task 1.3: Core Services
- [ ] Implement ZoneService with CRUD operations
- [ ] Implement RecordService with validation
- [ ] Implement ForwarderService with health checking
- [ ] Implement RPZService with rule management

### Phase 2: Enhanced BIND Integration (Week 3-4)

#### Task 2.1: BIND Configuration Management
- [ ] Enhance BindService with zone file generation
- [ ] Implement forwarder configuration updates
- [ ] Add RPZ zone file management
- [ ] Create configuration validation methods

#### Task 2.2: File Template System
- [ ] Create Jinja2 templates for zone files
- [ ] Implement RPZ zone file templates
- [ ] Add forwarder configuration templates
- [ ] Create backup and rollback mechanisms

#### Task 2.3: Service Integration
- [ ] Integrate database changes with BIND updates
- [ ] Implement atomic operations for consistency
- [ ] Add error handling and rollback procedures
- [ ] Create configuration testing utilities

### Phase 3: API Endpoints Implementation (Week 5-6)

#### Task 3.1: DNS Zones API
- [ ] Complete zones CRUD endpoints
- [ ] Add zone validation endpoints
- [ ] Implement zone import/export functionality
- [ ] Add bulk operations support

#### Task 3.2: DNS Records API
- [ ] Complete records CRUD endpoints
- [ ] Add record type-specific validation
- [ ] Implement bulk record operations
- [ ] Add record search and filtering

#### Task 3.3: Forwarders API
- [ ] Complete forwarders CRUD endpoints
- [ ] Add forwarder testing functionality
- [ ] Implement health monitoring endpoints
- [ ] Add forwarder statistics

#### Task 3.4: RPZ Security API
- [ ] Complete RPZ rules CRUD endpoints
- [ ] Add threat feed integration
- [ ] Implement bulk import functionality
- [ ] Add RPZ statistics and reporting

### Phase 4: Frontend Implementation (Week 7-8)

#### Task 4.1: DNS Zones Management
- [ ] Complete DNSZones page implementation
- [ ] Create ZoneModal component
- [ ] Add zone validation UI
- [ ] Implement zone import/export UI

#### Task 4.2: DNS Records Management
- [ ] Create RecordsView component
- [ ] Implement RecordModal component
- [ ] Add record type-specific forms
- [ ] Create bulk operations UI

#### Task 4.3: Forwarders Management
- [ ] Complete Forwarders page
- [ ] Create ForwarderModal component
- [ ] Add health monitoring UI
- [ ] Implement forwarder testing interface

#### Task 4.4: Security Management
- [ ] Complete Security/RPZ page
- [ ] Create RPZRuleModal component
- [ ] Add threat feed management UI
- [ ] Implement bulk import interface

### Phase 5: Advanced Features (Week 9-10)

#### Task 5.1: Real-time Monitoring
- [ ] Implement WebSocket connections
- [ ] Add real-time query monitoring
- [ ] Create live dashboard updates
- [ ] Add system health monitoring

#### Task 5.2: Analytics and Reporting
- [ ] Enhance monitoring service
- [ ] Add query analytics
- [ ] Implement performance monitoring
- [ ] Create automated reports

#### Task 5.3: Backup and Recovery
- [ ] Implement configuration backup
- [ ] Add automated backup scheduling
- [ ] Create restore functionality
- [ ] Add disaster recovery procedures

#### Task 5.4: Threat Intelligence
- [ ] Implement threat feed service
- [ ] Add automatic feed updates
- [ ] Create custom threat lists
- [ ] Add threat intelligence reporting

### Phase 6: Testing and Documentation (Week 11-12)

#### Task 6.1: Testing
- [ ] Create unit tests for all services
- [ ] Add integration tests for API endpoints
- [ ] Implement end-to-end tests for UI
- [ ] Add performance testing

#### Task 6.2: Documentation
- [ ] Update API documentation
- [ ] Create user guides
- [ ] Add troubleshooting guides
- [ ] Create deployment documentation

#### Task 6.3: Performance Optimization
- [ ] Optimize database queries
- [ ] Add caching where appropriate
- [ ] Optimize frontend performance
- [ ] Add monitoring and alerting

## 7. Success Criteria

### Functional Requirements
- [ ] Complete DNS zone management (CRUD operations)
- [ ] Full DNS record management with all record types
- [ ] Conditional forwarding configuration and management
- [ ] RPZ security policy management
- [ ] Real-time monitoring and analytics
- [ ] Automated BIND9 configuration updates
- [ ] Threat intelligence integration
- [ ] Backup and recovery functionality

### Technical Requirements
- [ ] All API endpoints implemented and tested
- [ ] Frontend components fully functional
- [ ] Database models with proper relationships
- [ ] BIND9 integration working correctly
- [ ] Real-time updates via WebSocket
- [ ] Comprehensive error handling
- [ ] Security best practices implemented
- [ ] Performance optimization completed

### Quality Requirements
- [ ] 90%+ test coverage for backend code
- [ ] All UI components responsive and accessible
- [ ] API response times under 200ms
- [ ] Zero data loss during operations
- [ ] Comprehensive logging and monitoring
- [ ] Security vulnerabilities addressed
- [ ] Documentation complete and accurate
- [ ] User acceptance testing passed

This specification provides a comprehensive roadmap for implementing all missing and partially implemented components of the Hybrid DNS Server. The phased approach ensures systematic development while maintaining system stability and allowing for iterative testing and refinement.