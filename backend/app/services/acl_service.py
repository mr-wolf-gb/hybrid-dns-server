"""
ACL (Access Control List) service for managing BIND9 ACL configurations
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.logging_config import get_logger
from ..models.system import ACL, ACLEntry
from ..schemas.system import (
    ACLCreate, ACLUpdate, ACLEntryCreate, ACLEntryUpdate,
    BulkACLEntryUpdate, ACLValidationResult, ACLConfigurationTemplate
)
from .base_service import BaseService


class ACLService(BaseService):
    """Service for managing Access Control Lists"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.logger = get_logger("acl_service")
    
    async def get_acls(
        self,
        skip: int = 0,
        limit: int = 100,
        acl_type: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None
    ) -> List[ACL]:
        """Get ACLs with optional filtering"""
        try:
            query = self.db.query(ACL)
            
            # Apply filters
            if active_only:
                query = query.filter(ACL.is_active == True)
            
            if acl_type:
                query = query.filter(ACL.acl_type == acl_type)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        ACL.name.ilike(search_term),
                        ACL.description.ilike(search_term)
                    )
                )
            
            # Apply pagination and ordering
            acls = query.order_by(ACL.name).offset(skip).limit(limit).all()
            
            self.logger.info(f"Retrieved {len(acls)} ACLs")
            return acls
            
        except Exception as e:
            self.logger.error(f"Failed to get ACLs: {e}")
            raise
    
    async def get_acl(self, acl_id: int) -> Optional[ACL]:
        """Get a specific ACL by ID"""
        try:
            acl = self.db.query(ACL).filter(ACL.id == acl_id).first()
            if acl:
                self.logger.debug(f"Retrieved ACL: {acl.name}")
            else:
                self.logger.warning(f"ACL not found: {acl_id}")
            return acl
            
        except Exception as e:
            self.logger.error(f"Failed to get ACL {acl_id}: {e}")
            raise
    
    async def get_acl_by_name(self, name: str) -> Optional[ACL]:
        """Get a specific ACL by name"""
        try:
            acl = self.db.query(ACL).filter(ACL.name == name).first()
            if acl:
                self.logger.debug(f"Retrieved ACL by name: {name}")
            else:
                self.logger.warning(f"ACL not found by name: {name}")
            return acl
            
        except Exception as e:
            self.logger.error(f"Failed to get ACL by name {name}: {e}")
            raise
    
    async def create_acl(self, acl_data: ACLCreate, user_id: Optional[int] = None) -> ACL:
        """Create a new ACL"""
        try:
            # Check if ACL name already exists
            existing = await self.get_acl_by_name(acl_data.name)
            if existing:
                raise ValueError(f"ACL with name '{acl_data.name}' already exists")
            
            # Create ACL
            acl = ACL(
                name=acl_data.name,
                acl_type=acl_data.acl_type,
                description=acl_data.description,
                is_active=acl_data.is_active,
                created_by=user_id,
                updated_by=user_id
            )
            
            self.db.add(acl)
            self.db.flush()  # Get the ID
            
            # Create ACL entries
            for entry_data in acl_data.entries:
                entry = ACLEntry(
                    acl_id=acl.id,
                    address=entry_data.address,
                    comment=entry_data.comment,
                    is_active=entry_data.is_active,
                    created_by=user_id,
                    updated_by=user_id
                )
                self.db.add(entry)
            
            self.db.commit()
            self.db.refresh(acl)
            
            self.logger.info(f"Created ACL: {acl.name} with {len(acl_data.entries)} entries")
            return acl
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create ACL: {e}")
            raise
    
    async def update_acl(
        self, 
        acl_id: int, 
        acl_data: ACLUpdate, 
        user_id: Optional[int] = None
    ) -> Optional[ACL]:
        """Update an existing ACL"""
        try:
            acl = await self.get_acl(acl_id)
            if not acl:
                return None
            
            # Check if new name conflicts with existing ACL
            if acl_data.name and acl_data.name != acl.name:
                existing = await self.get_acl_by_name(acl_data.name)
                if existing:
                    raise ValueError(f"ACL with name '{acl_data.name}' already exists")
            
            # Update fields
            if acl_data.name is not None:
                acl.name = acl_data.name
            if acl_data.acl_type is not None:
                acl.acl_type = acl_data.acl_type
            if acl_data.description is not None:
                acl.description = acl_data.description
            if acl_data.is_active is not None:
                acl.is_active = acl_data.is_active
            
            acl.updated_by = user_id
            acl.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(acl)
            
            self.logger.info(f"Updated ACL: {acl.name}")
            return acl
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update ACL {acl_id}: {e}")
            raise
    
    async def delete_acl(self, acl_id: int) -> bool:
        """Delete an ACL"""
        try:
            acl = await self.get_acl(acl_id)
            if not acl:
                return False
            
            acl_name = acl.name
            self.db.delete(acl)
            self.db.commit()
            
            self.logger.info(f"Deleted ACL: {acl_name}")
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to delete ACL {acl_id}: {e}")
            raise
    
    async def toggle_acl(self, acl_id: int, user_id: Optional[int] = None) -> Optional[ACL]:
        """Toggle ACL active status"""
        try:
            acl = await self.get_acl(acl_id)
            if not acl:
                return None
            
            acl.is_active = not acl.is_active
            acl.updated_by = user_id
            acl.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(acl)
            
            status = "activated" if acl.is_active else "deactivated"
            self.logger.info(f"ACL {acl.name} {status}")
            return acl
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to toggle ACL {acl_id}: {e}")
            raise
    
    # ACL Entry methods
    async def get_acl_entries(self, acl_id: int, active_only: bool = True) -> List[ACLEntry]:
        """Get entries for a specific ACL"""
        try:
            query = self.db.query(ACLEntry).filter(ACLEntry.acl_id == acl_id)
            
            if active_only:
                query = query.filter(ACLEntry.is_active == True)
            
            entries = query.order_by(ACLEntry.address).all()
            
            self.logger.debug(f"Retrieved {len(entries)} entries for ACL {acl_id}")
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to get ACL entries for {acl_id}: {e}")
            raise
    
    async def add_acl_entry(
        self, 
        acl_id: int, 
        entry_data: ACLEntryCreate, 
        user_id: Optional[int] = None
    ) -> Optional[ACLEntry]:
        """Add an entry to an ACL"""
        try:
            # Check if ACL exists
            acl = await self.get_acl(acl_id)
            if not acl:
                return None
            
            # Check if entry already exists
            existing = self.db.query(ACLEntry).filter(
                and_(
                    ACLEntry.acl_id == acl_id,
                    ACLEntry.address == entry_data.address
                )
            ).first()
            
            if existing:
                raise ValueError(f"Entry with address '{entry_data.address}' already exists in ACL")
            
            # Create entry
            entry = ACLEntry(
                acl_id=acl_id,
                address=entry_data.address,
                comment=entry_data.comment,
                is_active=entry_data.is_active,
                created_by=user_id,
                updated_by=user_id
            )
            
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            
            self.logger.info(f"Added entry {entry_data.address} to ACL {acl.name}")
            return entry
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to add entry to ACL {acl_id}: {e}")
            raise
    
    async def update_acl_entry(
        self, 
        entry_id: int, 
        entry_data: ACLEntryUpdate, 
        user_id: Optional[int] = None
    ) -> Optional[ACLEntry]:
        """Update an ACL entry"""
        try:
            entry = self.db.query(ACLEntry).filter(ACLEntry.id == entry_id).first()
            if not entry:
                return None
            
            # Check for address conflicts if address is being changed
            if entry_data.address and entry_data.address != entry.address:
                existing = self.db.query(ACLEntry).filter(
                    and_(
                        ACLEntry.acl_id == entry.acl_id,
                        ACLEntry.address == entry_data.address,
                        ACLEntry.id != entry_id
                    )
                ).first()
                
                if existing:
                    raise ValueError(f"Entry with address '{entry_data.address}' already exists in ACL")
            
            # Update fields
            if entry_data.address is not None:
                entry.address = entry_data.address
            if entry_data.comment is not None:
                entry.comment = entry_data.comment
            if entry_data.is_active is not None:
                entry.is_active = entry_data.is_active
            
            entry.updated_by = user_id
            entry.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(entry)
            
            self.logger.info(f"Updated ACL entry: {entry.address}")
            return entry
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update ACL entry {entry_id}: {e}")
            raise
    
    async def delete_acl_entry(self, entry_id: int) -> bool:
        """Delete an ACL entry"""
        try:
            entry = self.db.query(ACLEntry).filter(ACLEntry.id == entry_id).first()
            if not entry:
                return False
            
            entry_address = entry.address
            self.db.delete(entry)
            self.db.commit()
            
            self.logger.info(f"Deleted ACL entry: {entry_address}")
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to delete ACL entry {entry_id}: {e}")
            raise
    
    async def bulk_update_acl_entries(
        self, 
        acl_id: int, 
        bulk_data: BulkACLEntryUpdate, 
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Bulk update ACL entries"""
        try:
            # Check if ACL exists
            acl = await self.get_acl(acl_id)
            if not acl:
                raise ValueError(f"ACL with ID {acl_id} not found")
            
            results = {
                "total_processed": len(bulk_data.entries),
                "successful_updates": 0,
                "failed_updates": 0,
                "errors": []
            }
            
            # If replace_all is True, delete existing entries first
            if bulk_data.replace_all:
                existing_entries = await self.get_acl_entries(acl_id, active_only=False)
                for entry in existing_entries:
                    self.db.delete(entry)
            
            # Add new entries
            for entry_data in bulk_data.entries:
                try:
                    # Check for duplicates if not replacing all
                    if not bulk_data.replace_all:
                        existing = self.db.query(ACLEntry).filter(
                            and_(
                                ACLEntry.acl_id == acl_id,
                                ACLEntry.address == entry_data.address
                            )
                        ).first()
                        
                        if existing:
                            results["errors"].append(f"Entry {entry_data.address} already exists")
                            results["failed_updates"] += 1
                            continue
                    
                    # Create entry
                    entry = ACLEntry(
                        acl_id=acl_id,
                        address=entry_data.address,
                        comment=entry_data.comment,
                        is_active=entry_data.is_active,
                        created_by=user_id,
                        updated_by=user_id
                    )
                    
                    self.db.add(entry)
                    results["successful_updates"] += 1
                    
                except Exception as e:
                    results["errors"].append(f"Failed to add {entry_data.address}: {str(e)}")
                    results["failed_updates"] += 1
            
            self.db.commit()
            
            self.logger.info(f"Bulk updated ACL {acl.name}: {results['successful_updates']} successful, {results['failed_updates']} failed")
            return results
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to bulk update ACL entries for {acl_id}: {e}")
            raise
    
    async def validate_acl(self, acl_id: int) -> ACLValidationResult:
        """Validate an ACL configuration"""
        try:
            acl = await self.get_acl(acl_id)
            if not acl:
                return ACLValidationResult(
                    valid=False,
                    errors=[f"ACL with ID {acl_id} not found"],
                    warnings=[],
                    entry_count=0
                )
            
            errors = []
            warnings = []
            
            # Validate ACL name
            if not acl.name or len(acl.name.strip()) == 0:
                errors.append("ACL name cannot be empty")
            
            # Check for reserved names
            reserved_names = ['any', 'none', 'localhost', 'localnets']
            if acl.name.lower() in reserved_names:
                errors.append(f"ACL name '{acl.name}' is reserved by BIND9")
            
            # Validate entries
            entries = await self.get_acl_entries(acl_id, active_only=False)
            active_entries = [e for e in entries if e.is_active]
            
            if len(active_entries) == 0:
                warnings.append("ACL has no active entries")
            
            # Validate each entry
            for entry in entries:
                if entry.is_active:
                    entry_validation = await self._validate_entry_address(entry.address)
                    if not entry_validation["valid"]:
                        errors.extend(entry_validation["errors"])
                    warnings.extend(entry_validation.get("warnings", []))
            
            return ACLValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                entry_count=len(active_entries)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to validate ACL {acl_id}: {e}")
            return ACLValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                entry_count=0
            )
    
    async def _validate_entry_address(self, address: str) -> Dict[str, Any]:
        """Validate an ACL entry address"""
        errors = []
        warnings = []
        
        try:
            import ipaddress
            import re
            
            addr = address.strip()
            
            # Handle negation
            if addr.startswith('!'):
                addr = addr[1:].strip()
            
            # Try to validate as IP network
            try:
                ipaddress.ip_network(addr, strict=False)
            except ValueError:
                # Check if it's a valid hostname
                hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
                if not re.match(hostname_pattern, addr):
                    errors.append(f"Invalid address format: {address}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Address validation error: {str(e)}"],
                "warnings": warnings
            }
    
    async def get_acl_statistics(self) -> Dict[str, Any]:
        """Get ACL statistics"""
        try:
            total_acls = self.db.query(ACL).count()
            active_acls = self.db.query(ACL).filter(ACL.is_active == True).count()
            
            # Count by type
            type_counts = {}
            for acl_type in ['trusted', 'blocked', 'management', 'dns-servers', 'monitoring', 'custom']:
                count = self.db.query(ACL).filter(
                    and_(ACL.acl_type == acl_type, ACL.is_active == True)
                ).count()
                type_counts[acl_type] = count
            
            # Count entries
            total_entries = self.db.query(ACLEntry).count()
            active_entries = self.db.query(ACLEntry).filter(ACLEntry.is_active == True).count()
            
            return {
                "total_acls": total_acls,
                "active_acls": active_acls,
                "inactive_acls": total_acls - active_acls,
                "type_counts": type_counts,
                "total_entries": total_entries,
                "active_entries": active_entries,
                "inactive_entries": total_entries - active_entries
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get ACL statistics: {e}")
            raise