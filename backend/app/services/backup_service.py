"""
Configuration backup and rollback service for BIND9 DNS server
"""

import asyncio
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.config import get_settings
from ..core.logging_config import get_bind_logger


class BackupType(str, Enum):
    """Types of backups supported"""
    ZONE_FILE = "zone_file"
    RPZ_FILE = "rpz_file"
    CONFIGURATION = "configuration"
    FULL_CONFIG = "full_config"


@dataclass
class BackupMetadata:
    """Metadata for backup operations"""
    backup_id: str
    backup_type: BackupType
    original_path: str
    backup_path: str
    timestamp: datetime
    description: str
    file_size: int
    checksum: Optional[str] = None
    related_files: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['backup_type'] = self.backup_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['backup_type'] = BackupType(data['backup_type'])
        return cls(**data)


class BackupService:
    """Service for managing configuration backups and rollbacks"""
    
    def __init__(self):
        settings = get_settings()
        self.config_dir = settings.config_dir
        self.zones_dir = settings.zones_dir
        self.rpz_dir = settings.rpz_dir
        
        # Backup configuration
        self.backup_root = Path(settings.config_dir) / "backups"
        self.metadata_file = self.backup_root / "backup_metadata.json"
        self.max_backups_per_type = 50  # Keep last 50 backups per type
        self.backup_retention_days = 30  # Keep backups for 30 days
        
        # Ensure backup directory exists with proper permissions
        try:
            self.backup_root.mkdir(parents=True, exist_ok=True)
            # Try to create common backup type directories
            for backup_type in BackupType:
                type_dir = self.backup_root / backup_type.value
                try:
                    type_dir.mkdir(exist_ok=True)
                except PermissionError:
                    self.logger.warning(f"Cannot create backup type directory {type_dir}, will use fallback")
        except PermissionError as e:
            self.logger.error(f"Cannot create backup root directory {self.backup_root}: {e}")
            # This is a critical error, but we'll continue and hope for the best
        
        self.logger = get_bind_logger()
    
    async def create_backup(
        self, 
        file_path: Path, 
        backup_type: BackupType, 
        description: str = ""
    ) -> Optional[BackupMetadata]:
        """Create a backup of a configuration file"""
        self.logger.info(f"Creating backup for {file_path} (type: {backup_type.value})")
        
        try:
            if not file_path.exists():
                self.logger.warning(f"File does not exist, skipping backup: {file_path}")
                return None
            
            # Generate backup ID and paths
            timestamp = datetime.now()
            backup_id = f"{backup_type.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # Create type-specific backup directory
            type_backup_dir = self.backup_root / backup_type.value
            try:
                type_backup_dir.mkdir(exist_ok=True)
            except PermissionError as e:
                self.logger.error(f"Failed to create backup directory {type_backup_dir}: {e}")
                # Fall back to using the main backup directory
                type_backup_dir = self.backup_root
                self.logger.info(f"Using fallback backup directory: {type_backup_dir}")
            
            # Generate backup filename
            backup_filename = f"{file_path.name}.{backup_id}"
            backup_path = type_backup_dir / backup_filename
            
            # Copy file to backup location
            shutil.copy2(file_path, backup_path)
            
            # Calculate file size and checksum
            file_size = backup_path.stat().st_size
            checksum = await self._calculate_checksum(backup_path)
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                original_path=str(file_path),
                backup_path=str(backup_path),
                timestamp=timestamp,
                description=description or f"Backup of {file_path.name}",
                file_size=file_size,
                checksum=checksum
            )
            
            # Save metadata
            await self._save_backup_metadata(metadata)
            
            # Clean up old backups
            await self._cleanup_old_backups(backup_type)
            
            self.logger.info(f"Successfully created backup: {backup_path}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    async def create_full_configuration_backup(self, description: str = "") -> Optional[str]:
        """Create a full backup of all BIND configuration"""
        self.logger.info("Creating full configuration backup")
        
        try:
            timestamp = datetime.now()
            backup_id = f"full_config_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # Create full backup directory
            full_backup_dir = self.backup_root / "full_config" / backup_id
            try:
                full_backup_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                self.logger.error(f"Failed to create full backup directory {full_backup_dir}: {e}")
                # Fall back to using a flat structure in the main backup directory
                full_backup_dir = self.backup_root / f"full_config_{backup_id}"
                try:
                    full_backup_dir.mkdir(exist_ok=True)
                except PermissionError:
                    self.logger.error(f"Cannot create backup directory at all, aborting backup")
                    return None
            
            backed_up_files = []
            
            # Backup main configuration files
            config_files = [
                self.config_dir / "named.conf.local",
                self.config_dir / "named.conf.options",
                self.config_dir / "forwarders.conf",
                self.config_dir / "rpz-policy.conf"
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    backup_file = full_backup_dir / config_file.name
                    shutil.copy2(config_file, backup_file)
                    backed_up_files.append(str(config_file))
            
            # Backup all zone files
            zones_backup_dir = full_backup_dir / "zones"
            if self.zones_dir.exists():
                shutil.copytree(self.zones_dir, zones_backup_dir, dirs_exist_ok=True)
                for zone_file in self.zones_dir.glob("*"):
                    if zone_file.is_file():
                        backed_up_files.append(str(zone_file))
            
            # Backup all RPZ files
            rpz_backup_dir = full_backup_dir / "rpz"
            if self.rpz_dir.exists():
                shutil.copytree(self.rpz_dir, rpz_backup_dir, dirs_exist_ok=True)
                for rpz_file in self.rpz_dir.glob("*"):
                    if rpz_file.is_file():
                        backed_up_files.append(str(rpz_file))
            
            # Create backup manifest
            manifest = {
                "backup_id": backup_id,
                "timestamp": timestamp.isoformat(),
                "description": description or f"Full configuration backup {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                "files": backed_up_files,
                "total_files": len(backed_up_files)
            }
            
            manifest_file = full_backup_dir / "backup_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create metadata entry
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=BackupType.FULL_CONFIG,
                original_path=str(self.config_dir),
                backup_path=str(full_backup_dir),
                timestamp=timestamp,
                description=manifest["description"],
                file_size=sum(f.stat().st_size for f in full_backup_dir.rglob("*") if f.is_file()),
                related_files=backed_up_files
            )
            
            await self._save_backup_metadata(metadata)
            
            self.logger.info(f"Successfully created full configuration backup: {backup_id}")
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create full configuration backup: {e}")
            return None
    
    async def restore_from_backup(self, backup_id: str) -> bool:
        """Restore configuration from a backup"""
        self.logger.info(f"Restoring from backup: {backup_id}")
        
        try:
            # Load backup metadata
            metadata = await self._get_backup_metadata(backup_id)
            if not metadata:
                self.logger.error(f"Backup metadata not found: {backup_id}")
                return False
            
            backup_path = Path(metadata.backup_path)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Verify backup integrity
            if not await self._verify_backup_integrity(metadata):
                self.logger.error(f"Backup integrity check failed: {backup_id}")
                return False
            
            # Create backup of current configuration before restore
            original_path = Path(metadata.original_path)
            if original_path.exists():
                await self.create_backup(
                    original_path, 
                    metadata.backup_type, 
                    f"Pre-restore backup before restoring {backup_id}"
                )
            
            # Restore based on backup type
            if metadata.backup_type == BackupType.FULL_CONFIG:
                success = await self._restore_full_configuration(backup_path)
            else:
                # Restore single file
                shutil.copy2(backup_path, original_path)
                success = True
            
            if success:
                self.logger.info(f"Successfully restored from backup: {backup_id}")
            else:
                self.logger.error(f"Failed to restore from backup: {backup_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup {backup_id}: {e}")
            return False
    
    async def list_backups(
        self, 
        backup_type: Optional[BackupType] = None,
        limit: int = 50
    ) -> List[BackupMetadata]:
        """List available backups"""
        try:
            all_metadata = await self._load_all_backup_metadata()
            
            # Filter by type if specified
            if backup_type:
                all_metadata = [m for m in all_metadata if m.backup_type == backup_type]
            
            # Sort by timestamp (newest first) and limit
            all_metadata.sort(key=lambda x: x.timestamp, reverse=True)
            return all_metadata[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
    
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a specific backup"""
        self.logger.info(f"Deleting backup: {backup_id}")
        
        try:
            metadata = await self._get_backup_metadata(backup_id)
            if not metadata:
                self.logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup_path = Path(metadata.backup_path)
            
            # Delete backup file or directory
            if backup_path.is_file():
                backup_path.unlink()
            elif backup_path.is_dir():
                shutil.rmtree(backup_path)
            
            # Remove from metadata
            await self._remove_backup_metadata(backup_id)
            
            self.logger.info(f"Successfully deleted backup: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    async def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a backup"""
        try:
            metadata = await self._get_backup_metadata(backup_id)
            if not metadata:
                return None
            
            backup_path = Path(metadata.backup_path)
            
            info = metadata.to_dict()
            info['exists'] = backup_path.exists()
            info['current_size'] = backup_path.stat().st_size if backup_path.exists() else 0
            info['integrity_valid'] = await self._verify_backup_integrity(metadata)
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get backup info for {backup_id}: {e}")
            return None
    
    async def cleanup_old_backups(self) -> int:
        """Clean up old backups based on retention policy"""
        self.logger.info("Cleaning up old backups")
        
        try:
            cleaned_count = 0
            
            for backup_type in BackupType:
                cleaned_count += await self._cleanup_old_backups(backup_type)
            
            self.logger.info(f"Cleaned up {cleaned_count} old backups")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
            return 0
    
    # Private methods
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        import hashlib
        
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""
    
    async def _verify_backup_integrity(self, metadata: BackupMetadata) -> bool:
        """Verify backup file integrity using checksum"""
        if not metadata.checksum:
            return True  # No checksum to verify
        
        try:
            backup_path = Path(metadata.backup_path)
            if not backup_path.exists():
                return False
            
            current_checksum = await self._calculate_checksum(backup_path)
            return current_checksum == metadata.checksum
            
        except Exception:
            return False
    
    async def _save_backup_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to file"""
        try:
            # Load existing metadata
            all_metadata = await self._load_all_backup_metadata()
            
            # Add new metadata
            all_metadata.append(metadata)
            
            # Save to file
            metadata_data = [m.to_dict() for m in all_metadata]
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {e}")
    
    async def _load_all_backup_metadata(self) -> List[BackupMetadata]:
        """Load all backup metadata from file"""
        try:
            if not self.metadata_file.exists():
                return []
            
            with open(self.metadata_file, 'r') as f:
                metadata_data = json.load(f)
            
            return [BackupMetadata.from_dict(data) for data in metadata_data]
            
        except Exception as e:
            self.logger.error(f"Failed to load backup metadata: {e}")
            return []
    
    async def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get metadata for a specific backup"""
        all_metadata = await self._load_all_backup_metadata()
        for metadata in all_metadata:
            if metadata.backup_id == backup_id:
                return metadata
        return None
    
    async def _remove_backup_metadata(self, backup_id: str) -> None:
        """Remove metadata for a specific backup"""
        try:
            all_metadata = await self._load_all_backup_metadata()
            all_metadata = [m for m in all_metadata if m.backup_id != backup_id]
            
            metadata_data = [m.to_dict() for m in all_metadata]
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to remove backup metadata: {e}")
    
    async def _cleanup_old_backups(self, backup_type: BackupType) -> int:
        """Clean up old backups for a specific type"""
        try:
            all_metadata = await self._load_all_backup_metadata()
            type_metadata = [m for m in all_metadata if m.backup_type == backup_type]
            
            # Sort by timestamp (newest first)
            type_metadata.sort(key=lambda x: x.timestamp, reverse=True)
            
            cleaned_count = 0
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)
            
            # Keep max_backups_per_type most recent, delete older ones
            for i, metadata in enumerate(type_metadata):
                should_delete = (
                    i >= self.max_backups_per_type or 
                    metadata.timestamp < cutoff_date
                )
                
                if should_delete:
                    if await self.delete_backup(metadata.backup_id):
                        cleaned_count += 1
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups for {backup_type}: {e}")
            return 0
    
    async def _restore_full_configuration(self, backup_dir: Path) -> bool:
        """Restore full configuration from backup directory"""
        try:
            # Load backup manifest
            manifest_file = backup_dir / "backup_manifest.json"
            if not manifest_file.exists():
                self.logger.error("Backup manifest not found")
                return False
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Restore configuration files
            for config_file in ["named.conf.local", "named.conf.options", "forwarders.conf", "rpz-policy.conf"]:
                backup_file = backup_dir / config_file
                if backup_file.exists():
                    target_file = self.config_dir / config_file
                    shutil.copy2(backup_file, target_file)
            
            # Restore zone files
            zones_backup_dir = backup_dir / "zones"
            if zones_backup_dir.exists():
                # Clear existing zones directory
                if self.zones_dir.exists():
                    shutil.rmtree(self.zones_dir)
                shutil.copytree(zones_backup_dir, self.zones_dir)
            
            # Restore RPZ files
            rpz_backup_dir = backup_dir / "rpz"
            if rpz_backup_dir.exists():
                # Clear existing RPZ directory
                if self.rpz_dir.exists():
                    shutil.rmtree(self.rpz_dir)
                shutil.copytree(rpz_backup_dir, self.rpz_dir)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore full configuration: {e}")
            return False    

    async def validate_backup_integrity(self, backup_id: str) -> Dict[str, Any]:
        """
        Validate the integrity of a backup by checking file existence and checksums.
        
        Args:
            backup_id: The ID of the backup to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Get backup metadata
            metadata = await self.get_backup_metadata(backup_id)
            if not metadata:
                return {
                    "valid": False,
                    "errors": [f"Backup {backup_id} not found"],
                    "warnings": []
                }
            
            errors = []
            warnings = []
            
            # Check if backup file exists
            backup_path = Path(metadata.backup_path)
            if not backup_path.exists():
                errors.append(f"Backup file not found: {backup_path}")
                return {
                    "valid": False,
                    "errors": errors,
                    "warnings": warnings
                }
            
            # Check file size
            actual_size = backup_path.stat().st_size
            if actual_size != metadata.file_size:
                errors.append(f"Backup file size mismatch: expected {metadata.file_size}, got {actual_size}")
            
            # Validate checksum if available
            if metadata.checksum:
                actual_checksum = await self._calculate_file_checksum(backup_path)
                if actual_checksum != metadata.checksum:
                    errors.append(f"Backup checksum mismatch: expected {metadata.checksum}, got {actual_checksum}")
            else:
                warnings.append("No checksum available for validation")
            
            # For full configuration backups, check internal structure
            if metadata.backup_type == BackupType.FULL_CONFIG:
                structure_validation = await self._validate_full_config_backup_structure(backup_path)
                if not structure_validation["valid"]:
                    errors.extend(structure_validation["errors"])
                warnings.extend(structure_validation.get("warnings", []))
            
            # Check if backup is too old (optional warning)
            backup_age = datetime.now() - metadata.timestamp
            if backup_age.days > 30:
                warnings.append(f"Backup is {backup_age.days} days old")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "backup_id": backup_id,
                "backup_age_days": backup_age.days,
                "file_size": actual_size
            }
            
        except Exception as e:
            self.logger.error(f"Failed to validate backup integrity: {e}")
            return {
                "valid": False,
                "errors": [f"Backup integrity validation failed: {str(e)}"],
                "warnings": []
            }
    
    async def _validate_full_config_backup_structure(self, backup_path: Path) -> Dict[str, Any]:
        """Validate the internal structure of a full configuration backup"""
        errors = []
        warnings = []
        
        try:
            import tarfile
            
            # Check if it's a valid tar file
            if not tarfile.is_tarfile(backup_path):
                errors.append("Backup file is not a valid tar archive")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check internal structure
            with tarfile.open(backup_path, 'r:gz') as tar:
                members = tar.getnames()
                
                # Check for required directories/files
                required_items = [
                    "named.conf.local",
                    "named.conf.options",
                    "zones/",
                    "rpz/"
                ]
                
                for required_item in required_items:
                    found = any(member.startswith(required_item) for member in members)
                    if not found:
                        warnings.append(f"Backup missing expected item: {required_item}")
                
                # Check for suspicious files
                for member in members:
                    if member.startswith('/') or '..' in member:
                        errors.append(f"Backup contains suspicious path: {member}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate backup structure: {str(e)}"],
                "warnings": warnings
            }
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def backup_contains_file(self, backup_id: str, filename: str) -> bool:
        """
        Check if a backup contains a specific file.
        This is a synchronous method for compatibility with existing code.
        """
        try:
            # Get backup metadata synchronously
            metadata_file = self.backup_dir / f"{backup_id}.json"
            if not metadata_file.exists():
                return False
            
            with open(metadata_file, 'r') as f:
                metadata_dict = json.load(f)
            
            metadata = BackupMetadata.from_dict(metadata_dict)
            backup_path = Path(metadata.backup_path)
            
            if not backup_path.exists():
                return False
            
            # For full config backups, check inside the tar file
            if metadata.backup_type == BackupType.FULL_CONFIG:
                import tarfile
                if tarfile.is_tarfile(backup_path):
                    with tarfile.open(backup_path, 'r:gz') as tar:
                        return filename in tar.getnames()
            
            # For single file backups, check if the filename matches
            return backup_path.name == filename or filename in str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to check if backup contains file: {e}")
            return False
    
    async def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a backup.
        
        Args:
            backup_id: The ID of the backup
            
        Returns:
            Dictionary with backup information or None if not found
        """
        try:
            metadata = await self.get_backup_metadata(backup_id)
            if not metadata:
                return None
            
            backup_path = Path(metadata.backup_path)
            
            # Get current file information
            file_exists = backup_path.exists()
            current_size = backup_path.stat().st_size if file_exists else 0
            
            # Validate integrity
            integrity_result = await self.validate_backup_integrity(backup_id)
            
            return {
                "id": backup_id,
                "type": metadata.backup_type.value,
                "description": metadata.description,
                "created_at": metadata.timestamp.isoformat(),
                "original_path": metadata.original_path,
                "backup_path": metadata.backup_path,
                "file_exists": file_exists,
                "size": current_size,
                "expected_size": metadata.file_size,
                "checksum": metadata.checksum,
                "integrity_valid": integrity_result["valid"],
                "integrity_errors": integrity_result.get("errors", []),
                "integrity_warnings": integrity_result.get("warnings", []),
                "related_files": metadata.related_files or []
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get backup info: {e}")
            return None  
  
    async def get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """
        Get backup metadata by backup ID.
        
        Args:
            backup_id: The ID of the backup
            
        Returns:
            BackupMetadata object or None if not found
        """
        try:
            metadata_file = self.backup_dir / f"{backup_id}.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r') as f:
                metadata_dict = json.load(f)
            
            return BackupMetadata.from_dict(metadata_dict)
            
        except Exception as e:
            self.logger.error(f"Failed to get backup metadata: {e}")
            return None
    
    async def list_backups(self, backup_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available backups, optionally filtered by type.
        
        Args:
            backup_type: Optional backup type to filter by
            
        Returns:
            List of backup information dictionaries
        """
        try:
            backups = []
            
            # Find all metadata files
            for metadata_file in self.backup_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata_dict = json.load(f)
                    
                    metadata = BackupMetadata.from_dict(metadata_dict)
                    
                    # Filter by type if specified
                    if backup_type and metadata.backup_type.value != backup_type:
                        continue
                    
                    # Get current file status
                    backup_path = Path(metadata.backup_path)
                    file_exists = backup_path.exists()
                    current_size = backup_path.stat().st_size if file_exists else 0
                    
                    backup_info = {
                        "id": metadata.backup_id,
                        "type": metadata.backup_type.value,
                        "description": metadata.description,
                        "created_at": metadata.timestamp.isoformat(),
                        "original_path": metadata.original_path,
                        "backup_path": metadata.backup_path,
                        "file_exists": file_exists,
                        "size": current_size,
                        "expected_size": metadata.file_size,
                        "checksum": metadata.checksum
                    }
                    
                    backups.append(backup_info)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to read backup metadata from {metadata_file}: {e}")
                    continue
            
            # Sort by creation date, newest first
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []