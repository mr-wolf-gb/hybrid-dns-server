"""
BIND9 service management and configuration
"""

import asyncio
import ipaddress
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.config import get_settings
from ..core.logging_config import get_bind_logger
from ..models.dns import Zone, DNSRecord


class BindService:
    """BIND9 service management"""
    
    def __init__(self, db: Optional[Session] = None):
        settings = get_settings()
        self.service_name = settings.BIND9_SERVICE_NAME
        self.config_dir = settings.config_dir
        self.zones_dir = settings.zones_dir
        self.rpz_dir = settings.rpz_dir
        self.db = db
        self.is_async = isinstance(db, AsyncSession) if db else False
        
        # Initialize Jinja2 environment for template rendering
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters for DNS zone file generation
        self.jinja_env.filters['format_email_for_soa'] = self._format_email_filter
        self.jinja_env.filters['ensure_trailing_dot'] = self._ensure_trailing_dot_filter
        self.jinja_env.filters['rpz_format_domain'] = self._rpz_format_domain_filter
        self.jinja_env.filters['format_ttl'] = self._format_ttl_filter
        self.jinja_env.filters['format_serial'] = self._format_serial_filter
        self.jinja_env.filters['format_duration'] = self._format_duration_filter
        self.jinja_env.filters['validate_ip'] = self._validate_ip_filter
        self.jinja_env.filters['reverse_ip'] = self._reverse_ip_filter
        self.jinja_env.filters['format_mx_priority'] = self._format_mx_priority_filter
        self.jinja_env.filters['format_srv_record'] = self._format_srv_record_filter
        self.jinja_env.filters['escape_txt_record'] = self._escape_txt_record_filter
        self.jinja_env.filters['normalize_domain'] = self._normalize_domain_filter
        self.jinja_env.filters['is_wildcard'] = self._is_wildcard_filter
        self.jinja_env.filters['format_comment'] = self._format_comment_filter
        
        # Add global functions for templates
        self.jinja_env.globals['now'] = datetime.now
        self.jinja_env.globals['utcnow'] = datetime.utcnow
        self.jinja_env.globals['generate_serial'] = self._generate_serial_number
        self.jinja_env.globals['default_ttl'] = self._get_default_ttl
        self.jinja_env.globals['format_timestamp'] = self._format_timestamp
        self.jinja_env.globals['get_zone_type_description'] = self._get_zone_type_description
        self.jinja_env.globals['get_record_type_description'] = self._get_record_type_description
    
    async def _execute_query(self, query):
        """Helper method to execute queries for both sync and async sessions"""
        if not self.db:
            return None
            
        if self.is_async:
            result = await self.db.execute(query)
            return result
        else:
            return query
    
    async def get_service_status(self) -> Dict:
        """Get BIND9 service status"""
        try:
            # Check if service is running
            result = await self._run_command(["systemctl", "is-active", self.service_name])
            is_active = result["stdout"].strip() == "active"
            
            # Get uptime if running
            uptime = "unknown"
            if is_active:
                uptime_result = await self._run_command([
                    "systemctl", "show", "-p", "ActiveEnterTimestamp", self.service_name
                ])
                if uptime_result["returncode"] == 0:
                    # Parse uptime from systemd output
                    uptime = uptime_result["stdout"].strip()
            
            # Check configuration validity
            config_valid = await self.validate_configuration()
            
            return {
                "status": "active" if is_active else "inactive",
                "uptime": uptime,
                "version": await self._get_bind_version(),
                "config_valid": config_valid,
                "zones_loaded": await self._get_zones_loaded_count(),
                "cache_size": await self._get_cache_size()
            }
            
        except Exception as e:
            logger = get_bind_logger()
            logger.error(f"Failed to get BIND service status: {e}")
            return {
                "status": "unknown",
                "uptime": "unknown",
                "version": "unknown",
                "config_valid": False,
                "zones_loaded": 0,
                "cache_size": 0
            }
    
    async def start_service(self) -> bool:
        """Start BIND9 service"""
        logger = get_bind_logger()
        try:
            result = await self._run_command(["systemctl", "start", self.service_name])
            success = result["returncode"] == 0
            
            if success:
                logger.info("BIND9 service started successfully")
            else:
                logger.error(f"Failed to start BIND9 service: {result['stderr']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to start BIND9 service: {e}")
            return False
    
    async def stop_service(self) -> bool:
        """Stop BIND9 service"""
        logger = get_bind_logger()
        try:
            result = await self._run_command(["systemctl", "stop", self.service_name])
            success = result["returncode"] == 0
            
            if success:
                logger.info("BIND9 service stopped successfully")
            else:
                logger.error(f"Failed to stop BIND9 service: {result['stderr']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to stop BIND9 service: {e}")
            return False
    
    async def reload_service(self) -> bool:
        """Reload BIND9 configuration"""
        logger = get_bind_logger()
        try:
            # First try rndc reload with full path
            result = await self._run_command(["/usr/sbin/rndc", "reload"])
            
            if result["returncode"] == 127:  # Command not found
                logger.warning("rndc command not found, trying systemctl restart")
                # Fallback to systemctl restart
                result = await self._run_command(["systemctl", "restart", self.service_name])
            
            success = result["returncode"] == 0
            
            if success:
                logger.info("BIND9 configuration reloaded successfully")
            else:
                logger.error(f"Failed to reload BIND9 configuration: {result['stderr']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to reload BIND9 configuration: {e}")
            return False
    
    async def validate_configuration(self) -> bool:
        """Validate BIND9 configuration (simple boolean result)"""
        validation_result = await self.validate_configuration_detailed()
        return validation_result["valid"]
    
    async def validate_configuration_detailed(self) -> Dict[str, Any]:
        """Comprehensive BIND9 configuration validation with detailed results"""
        logger = get_bind_logger()
        logger.info("Starting comprehensive BIND9 configuration validation")
        
        errors = []
        warnings = []
        validation_details = {}
        
        try:
            # 1. Validate main BIND9 configuration syntax
            logger.debug("Validating main BIND9 configuration syntax")
            main_config_result = await self._validate_main_configuration_syntax()
            validation_details["main_config"] = main_config_result
            errors.extend(main_config_result.get("errors", []))
            warnings.extend(main_config_result.get("warnings", []))
            
            # 2. Validate all zone files
            logger.debug("Validating zone files")
            zones_result = await self._validate_all_zone_files()
            validation_details["zones"] = zones_result
            errors.extend(zones_result.get("errors", []))
            warnings.extend(zones_result.get("warnings", []))
            
            # 3. Validate forwarder configuration
            logger.debug("Validating forwarder configuration")
            forwarders_result = await self._validate_forwarders_configuration()
            validation_details["forwarders"] = forwarders_result
            errors.extend(forwarders_result.get("errors", []))
            warnings.extend(forwarders_result.get("warnings", []))
            
            # 4. Validate RPZ configuration
            logger.debug("Validating RPZ configuration")
            rpz_result = await self._validate_rpz_configuration()
            validation_details["rpz"] = rpz_result
            errors.extend(rpz_result.get("errors", []))
            warnings.extend(rpz_result.get("warnings", []))
            
            # 5. Validate file permissions and ownership
            logger.debug("Validating file permissions")
            permissions_result = await self._validate_file_permissions()
            validation_details["permissions"] = permissions_result
            errors.extend(permissions_result.get("errors", []))
            warnings.extend(permissions_result.get("warnings", []))
            
            # 6. Validate configuration consistency
            logger.debug("Validating configuration consistency")
            consistency_result = await self._validate_configuration_consistency()
            validation_details["consistency"] = consistency_result
            errors.extend(consistency_result.get("errors", []))
            warnings.extend(consistency_result.get("warnings", []))
            
            # 7. Validate service dependencies
            logger.debug("Validating service dependencies")
            dependencies_result = await self._validate_service_dependencies()
            validation_details["dependencies"] = dependencies_result
            errors.extend(dependencies_result.get("errors", []))
            warnings.extend(dependencies_result.get("warnings", []))
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info("BIND9 configuration validation completed successfully")
            else:
                logger.error(f"BIND9 configuration validation failed with {len(errors)} errors")
                for error in errors[:5]:  # Log first 5 errors
                    logger.error(f"Validation error: {error}")
            
            if warnings:
                logger.warning(f"BIND9 configuration validation completed with {len(warnings)} warnings")
                for warning in warnings[:3]:  # Log first 3 warnings
                    logger.warning(f"Validation warning: {warning}")
            
            return {
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "details": validation_details,
                "summary": {
                    "total_errors": len(errors),
                    "total_warnings": len(warnings),
                    "components_validated": len(validation_details),
                    "validation_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to validate BIND9 configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Configuration validation failed: {str(e)}"],
                "warnings": warnings,
                "details": validation_details,
                "summary": {
                    "total_errors": 1,
                    "total_warnings": len(warnings),
                    "components_validated": len(validation_details),
                    "validation_timestamp": datetime.now().isoformat()
                }
            }
    
    async def validate_atomic_configuration_update(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that configuration changes can be applied atomically without breaking BIND9"""
        logger = get_bind_logger()
        logger.info("Validating atomic configuration update")
        
        errors = []
        warnings = []
        
        try:
            # 1. Create backup before validation
            backup_id = await self.create_full_configuration_backup("Pre-atomic-validation")
            if not backup_id:
                errors.append("Failed to create configuration backup - atomic update not safe")
                return {
                    "valid": False,
                    "errors": errors,
                    "warnings": warnings,
                    "backup_id": None
                }
            
            # 2. Validate current configuration state
            current_validation = await self.validate_configuration_detailed()
            if not current_validation["valid"]:
                errors.append("Current configuration is invalid - cannot perform atomic update")
                errors.extend(current_validation["errors"])
            
            # 3. Validate proposed changes
            change_validation = await self._validate_configuration_changes(changes)
            if not change_validation["valid"]:
                errors.extend(change_validation["errors"])
            warnings.extend(change_validation.get("warnings", []))
            
            # 4. Check for conflicting changes
            conflict_validation = await self._validate_change_conflicts(changes)
            if not conflict_validation["valid"]:
                errors.extend(conflict_validation["errors"])
            warnings.extend(conflict_validation.get("warnings", []))
            
            # 5. Validate rollback capability
            rollback_validation = await self._validate_rollback_capability(backup_id)
            if not rollback_validation["valid"]:
                errors.append("Rollback capability validation failed - atomic update not safe")
                errors.extend(rollback_validation["errors"])
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "backup_id": backup_id,
                "changes_validated": len(changes),
                "rollback_available": rollback_validation.get("valid", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to validate atomic configuration update: {e}")
            return {
                "valid": False,
                "errors": [f"Atomic validation failed: {str(e)}"],
                "warnings": warnings,
                "backup_id": backup_id if 'backup_id' in locals() else None
            }
    
    async def _validate_configuration_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Validate specific configuration changes"""
        errors = []
        warnings = []
        
        try:
            # Validate zone changes
            if "zones" in changes:
                for zone_change in changes["zones"]:
                    if zone_change.get("action") == "create":
                        zone_validation = await self._validate_zone_creation_change(zone_change)
                    elif zone_change.get("action") == "update":
                        zone_validation = await self._validate_zone_update_change(zone_change)
                    elif zone_change.get("action") == "delete":
                        zone_validation = await self._validate_zone_deletion_change(zone_change)
                    else:
                        errors.append(f"Unknown zone change action: {zone_change.get('action')}")
                        continue
                    
                    if not zone_validation["valid"]:
                        errors.extend(zone_validation["errors"])
                    warnings.extend(zone_validation.get("warnings", []))
            
            # Validate forwarder changes
            if "forwarders" in changes:
                for forwarder_change in changes["forwarders"]:
                    forwarder_validation = await self._validate_forwarder_change(forwarder_change)
                    if not forwarder_validation["valid"]:
                        errors.extend(forwarder_validation["errors"])
                    warnings.extend(forwarder_validation.get("warnings", []))
            
            # Validate RPZ changes
            if "rpz" in changes:
                for rpz_change in changes["rpz"]:
                    rpz_validation = await self._validate_rpz_change(rpz_change)
                    if not rpz_validation["valid"]:
                        errors.extend(rpz_validation["errors"])
                    warnings.extend(rpz_validation.get("warnings", []))
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate configuration changes: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_change_conflicts(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that changes don't conflict with each other"""
        errors = []
        warnings = []
        
        try:
            # Check for zone name conflicts
            zone_names = set()
            if "zones" in changes:
                for zone_change in changes["zones"]:
                    zone_name = zone_change.get("name")
                    if zone_name:
                        if zone_name in zone_names:
                            errors.append(f"Duplicate zone name in changes: {zone_name}")
                        zone_names.add(zone_name)
            
            # Check for forwarder domain conflicts
            forwarder_domains = set()
            if "forwarders" in changes:
                for forwarder_change in changes["forwarders"]:
                    domains = forwarder_change.get("domains", [])
                    for domain in domains:
                        if domain in forwarder_domains:
                            errors.append(f"Duplicate forwarder domain in changes: {domain}")
                        forwarder_domains.add(domain)
            
            # Check for RPZ rule conflicts
            rpz_domains = set()
            if "rpz" in changes:
                for rpz_change in changes["rpz"]:
                    domain = rpz_change.get("domain")
                    if domain:
                        if domain in rpz_domains:
                            warnings.append(f"Duplicate RPZ domain in changes: {domain}")
                        rpz_domains.add(domain)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate change conflicts: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_rollback_capability(self, backup_id: str) -> Dict[str, Any]:
        """Validate that rollback is possible from the given backup"""
        errors = []
        warnings = []
        
        try:
            from .backup_service import BackupService
            backup_service = BackupService()
            
            # Check if backup exists and is valid
            backup_info = await backup_service.get_backup_info(backup_id)
            if not backup_info:
                errors.append(f"Backup {backup_id} not found or invalid")
                return {
                    "valid": False,
                    "errors": errors,
                    "warnings": warnings
                }
            
            # Validate backup integrity
            integrity_check = await backup_service.validate_backup_integrity(backup_id)
            if not integrity_check["valid"]:
                errors.append("Backup integrity validation failed")
                errors.extend(integrity_check["errors"])
            
            # Check if backup contains all necessary files
            required_files = [
                "named.conf",
                "named.conf.options", 
                "named.conf.local"
            ]
            
            for required_file in required_files:
                if not backup_service.backup_contains_file(backup_id, required_file):
                    errors.append(f"Backup missing required file: {required_file}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "backup_info": backup_info
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate rollback capability: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_zone_creation_change(self, zone_change: Dict[str, Any]) -> Dict[str, Any]:
        """Validate zone creation change"""
        errors = []
        warnings = []
        
        try:
            zone_name = zone_change.get("name")
            if not zone_name:
                errors.append("Zone creation change missing name")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check if zone already exists
            if self.db:
                from ..models.dns import Zone
                existing_zone = self.db.query(Zone).filter(Zone.name == zone_name).first()
                if existing_zone:
                    errors.append(f"Zone {zone_name} already exists")
            
            # Validate zone configuration
            zone_type = zone_change.get("zone_type", "master")
            if zone_type not in ["master", "slave", "forward"]:
                errors.append(f"Invalid zone type: {zone_type}")
            
            # Validate required fields based on zone type
            if zone_type == "slave" and not zone_change.get("master_servers"):
                errors.append("Slave zone requires master servers")
            elif zone_type == "forward" and not zone_change.get("forwarders"):
                errors.append("Forward zone requires forwarders")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate zone creation change: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_zone_update_change(self, zone_change: Dict[str, Any]) -> Dict[str, Any]:
        """Validate zone update change"""
        errors = []
        warnings = []
        
        try:
            zone_id = zone_change.get("id")
            if not zone_id:
                errors.append("Zone update change missing ID")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check if zone exists
            if self.db:
                from ..models.dns import Zone
                existing_zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
                if not existing_zone:
                    errors.append(f"Zone with ID {zone_id} not found")
                    return {"valid": False, "errors": errors, "warnings": warnings}
                
                # Validate that critical fields aren't being changed inappropriately
                if "zone_type" in zone_change and zone_change["zone_type"] != existing_zone.zone_type:
                    warnings.append("Changing zone type may require manual intervention")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate zone update change: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_zone_deletion_change(self, zone_change: Dict[str, Any]) -> Dict[str, Any]:
        """Validate zone deletion change"""
        errors = []
        warnings = []
        
        try:
            zone_id = zone_change.get("id")
            if not zone_id:
                errors.append("Zone deletion change missing ID")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check if zone exists and has records
            if self.db:
                from ..models.dns import Zone, DNSRecord
                existing_zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
                if not existing_zone:
                    warnings.append(f"Zone with ID {zone_id} not found (already deleted?)")
                else:
                    record_count = self.db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id).count()
                    if record_count > 0:
                        warnings.append(f"Zone {existing_zone.name} has {record_count} records that will be deleted")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate zone deletion change: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_forwarder_change(self, forwarder_change: Dict[str, Any]) -> Dict[str, Any]:
        """Validate forwarder configuration change"""
        errors = []
        warnings = []
        
        try:
            # Validate server addresses
            servers = forwarder_change.get("servers", [])
            for server in servers:
                server_ip = server.get("ip") if isinstance(server, dict) else server
                try:
                    import ipaddress
                    ipaddress.ip_address(server_ip)
                except ValueError:
                    errors.append(f"Invalid server IP address: {server_ip}")
            
            # Validate domains
            domains = forwarder_change.get("domains", [])
            if not domains:
                errors.append("Forwarder change missing domains")
            
            for domain in domains:
                if not self._is_valid_domain_name(domain):
                    errors.append(f"Invalid domain name: {domain}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate forwarder change: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_rpz_change(self, rpz_change: Dict[str, Any]) -> Dict[str, Any]:
        """Validate RPZ rule change"""
        errors = []
        warnings = []
        
        try:
            domain = rpz_change.get("domain")
            if not domain:
                errors.append("RPZ change missing domain")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Validate domain format
            if not self._is_valid_rpz_domain(domain):
                errors.append(f"Invalid RPZ domain: {domain}")
            
            # Validate action
            action = rpz_change.get("action")
            if action not in ["block", "redirect", "passthru"]:
                errors.append(f"Invalid RPZ action: {action}")
            
            # Validate redirect target if action is redirect
            if action == "redirect":
                redirect_target = rpz_change.get("redirect_target")
                if not redirect_target:
                    errors.append("RPZ redirect action requires redirect_target")
                elif not self._is_valid_domain_name(redirect_target):
                    errors.append(f"Invalid RPZ redirect target: {redirect_target}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate RPZ change: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_main_configuration_syntax(self) -> Dict[str, Any]:
        """Validate main BIND9 configuration file syntax"""
        errors = []
        warnings = []
        
        try:
            # Use named-checkconf to validate main configuration
            result = await self._run_command(["/usr/sbin/named-checkconf"])
            
            if result["returncode"] != 0:
                error_msg = result["stderr"].strip()
                if error_msg:
                    errors.append(f"Main configuration syntax error: {error_msg}")
                else:
                    errors.append("Main configuration syntax validation failed")
            
            # Check if configuration files exist
            main_config_files = [
                "/etc/bind/named.conf",
                "/etc/bind/named.conf.options",
                "/etc/bind/named.conf.local"
            ]
            
            for config_file in main_config_files:
                config_path = Path(config_file)
                if not config_path.exists():
                    warnings.append(f"Configuration file not found: {config_file}")
                elif not config_path.is_file():
                    errors.append(f"Configuration path is not a file: {config_file}")
                elif not config_path.stat().st_size > 0:
                    warnings.append(f"Configuration file is empty: {config_file}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate main configuration: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_all_zone_files(self) -> Dict[str, Any]:
        """Validate all zone files referenced in configuration"""
        errors = []
        warnings = []
        validated_zones = 0
        
        try:
            # Get zones from database if available
            if self.db:
                from ..models.dns import Zone
                if isinstance(self.db, AsyncSession):
                    result = await self.db.execute(select(Zone).where(Zone.is_active == True))
                    zones = result.scalars().all()
                else:
                    zones = self.db.query(Zone).filter(Zone.is_active == True).all()
                
                for zone in zones:
                    try:
                        zone_validation = await self.validate_zone(zone)
                        validated_zones += 1
                        
                        if not zone_validation["valid"]:
                            errors.extend([f"Zone {zone.name}: {error}" for error in zone_validation["errors"]])
                        
                        if zone_validation.get("warnings"):
                            warnings.extend([f"Zone {zone.name}: {warning}" for warning in zone_validation["warnings"]])
                            
                    except Exception as e:
                        errors.append(f"Failed to validate zone {zone.name}: {str(e)}")
            else:
                warnings.append("No database connection available for zone validation")
            
            # Also validate zone files in the zones directory
            if self.zones_dir.exists():
                for zone_file in self.zones_dir.glob("db.*"):
                    if zone_file.is_file():
                        try:
                            # Extract zone name from filename
                            zone_name = zone_file.name.replace("db.", "")
                            
                            # Validate zone file syntax
                            result = await self._run_command([
                                "/usr/sbin/named-checkzone", zone_name, str(zone_file)
                            ])
                            
                            if result["returncode"] != 0:
                                errors.append(f"Zone file {zone_file.name} syntax error: {result['stderr'].strip()}")
                            
                        except Exception as e:
                            errors.append(f"Failed to validate zone file {zone_file.name}: {str(e)}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "zones_validated": validated_zones
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate zone files: {str(e)}"],
                "warnings": warnings,
                "zones_validated": validated_zones
            }
    
    async def _validate_forwarders_configuration(self) -> Dict[str, Any]:
        """Validate forwarder configuration"""
        errors = []
        warnings = []
        validated_forwarders = 0
        
        try:
            if self.db:
                from ..models.dns import Forwarder
                if isinstance(self.db, AsyncSession):
                    result = await self.db.execute(select(Forwarder).where(Forwarder.is_active == True))
                    forwarders = result.scalars().all()
                else:
                    forwarders = self.db.query(Forwarder).filter(Forwarder.is_active == True).all()
                
                for forwarder in forwarders:
                    try:
                        forwarder_validation = await self.validate_forwarder_configuration(forwarder)
                        validated_forwarders += 1
                        
                        if not forwarder_validation["valid"]:
                            errors.extend([f"Forwarder {forwarder.name}: {error}" for error in forwarder_validation["errors"]])
                        
                        if forwarder_validation.get("warnings"):
                            warnings.extend([f"Forwarder {forwarder.name}: {warning}" for warning in forwarder_validation["warnings"]])
                            
                    except Exception as e:
                        errors.append(f"Failed to validate forwarder {forwarder.name}: {str(e)}")
            else:
                warnings.append("No database connection available for forwarder validation")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "forwarders_validated": validated_forwarders
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate forwarders: {str(e)}"],
                "warnings": warnings,
                "forwarders_validated": validated_forwarders
            }
    
    async def _validate_rpz_configuration(self) -> Dict[str, Any]:
        """Validate RPZ configuration and zone files"""
        errors = []
        warnings = []
        validated_rpz_zones = 0
        
        try:
            # Validate RPZ policy configuration
            rpz_policy_validation = await self.validate_rpz_policy_configuration()
            if not rpz_policy_validation["valid"]:
                errors.extend(rpz_policy_validation["errors"])
            warnings.extend(rpz_policy_validation.get("warnings", []))
            
            # Validate RPZ zone files
            if self.rpz_dir.exists():
                for rpz_file in self.rpz_dir.glob("db.rpz.*"):
                    if rpz_file.is_file():
                        try:
                            # Extract RPZ zone name from filename
                            rpz_zone = rpz_file.name.replace("db.rpz.", "")
                            
                            # Validate RPZ zone file
                            rpz_validation = await self.validate_generated_rpz_zone_file(rpz_zone, rpz_file)
                            validated_rpz_zones += 1
                            
                            if not rpz_validation["valid"]:
                                errors.extend([f"RPZ zone {rpz_zone}: {error}" for error in rpz_validation["errors"]])
                            
                            if rpz_validation.get("warnings"):
                                warnings.extend([f"RPZ zone {rpz_zone}: {warning}" for warning in rpz_validation["warnings"]])
                                
                        except Exception as e:
                            errors.append(f"Failed to validate RPZ file {rpz_file.name}: {str(e)}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "rpz_zones_validated": validated_rpz_zones
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate RPZ configuration: {str(e)}"],
                "warnings": warnings,
                "rpz_zones_validated": validated_rpz_zones
            }
    
    async def _validate_file_permissions(self) -> Dict[str, Any]:
        """Validate file permissions and ownership for BIND9 files"""
        errors = []
        warnings = []
        
        try:
            import stat
            try:
                import pwd
                import grp
                has_unix_permissions = True
            except ImportError:
                # Windows doesn't have pwd/grp modules
                has_unix_permissions = False
            
            # Define expected permissions for different file types
            file_checks = [
                {
                    "path": "/etc/bind/named.conf",
                    "expected_mode": 0o644,
                    "expected_owner": "root",
                    "expected_group": "bind"
                },
                {
                    "path": "/etc/bind/named.conf.options",
                    "expected_mode": 0o644,
                    "expected_owner": "root",
                    "expected_group": "bind"
                },
                {
                    "path": "/etc/bind/named.conf.local",
                    "expected_mode": 0o644,
                    "expected_owner": "root",
                    "expected_group": "bind"
                }
            ]
            
            # Check zone files directory
            if self.zones_dir.exists():
                for zone_file in self.zones_dir.glob("db.*"):
                    file_checks.append({
                        "path": str(zone_file),
                        "expected_mode": 0o644,
                        "expected_owner": "root",
                        "expected_group": "bind"
                    })
            
            # Check RPZ files directory
            if self.rpz_dir.exists():
                for rpz_file in self.rpz_dir.glob("db.rpz.*"):
                    file_checks.append({
                        "path": str(rpz_file),
                        "expected_mode": 0o644,
                        "expected_owner": "root",
                        "expected_group": "bind"
                    })
            
            for check in file_checks:
                file_path = Path(check["path"])
                
                if not file_path.exists():
                    warnings.append(f"File does not exist: {check['path']}")
                    continue
                
                try:
                    file_stat = file_path.stat()
                    
                    # Check permissions
                    actual_mode = stat.S_IMODE(file_stat.st_mode)
                    if actual_mode != check["expected_mode"]:
                        warnings.append(
                            f"File {check['path']} has permissions {oct(actual_mode)}, "
                            f"expected {oct(check['expected_mode'])}"
                        )
                    
                    # Check ownership (if running as root)
                    try:
                        actual_owner = pwd.getpwuid(file_stat.st_uid).pw_name
                        actual_group = grp.getgrgid(file_stat.st_gid).gr_name
                        
                        if actual_owner != check["expected_owner"]:
                            warnings.append(
                                f"File {check['path']} owned by {actual_owner}, "
                                f"expected {check['expected_owner']}"
                            )
                        
                        if actual_group != check["expected_group"]:
                            warnings.append(
                                f"File {check['path']} group {actual_group}, "
                                f"expected {check['expected_group']}"
                            )
                    except (KeyError, PermissionError):
                        # Skip ownership check if we can't determine it
                        pass
                        
                except Exception as e:
                    warnings.append(f"Could not check permissions for {check['path']}: {str(e)}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "files_checked": len(file_checks)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate file permissions: {str(e)}"],
                "warnings": warnings,
                "files_checked": 0
            }
    
    async def _validate_configuration_consistency(self) -> Dict[str, Any]:
        """Validate consistency between database and configuration files"""
        errors = []
        warnings = []
        
        try:
            if not self.db:
                warnings.append("No database connection available for consistency validation")
                return {
                    "valid": True,
                    "errors": errors,
                    "warnings": warnings
                }
            
            # Check zone consistency
            from ..models.dns import Zone
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(select(Zone).where(Zone.is_active == True))
                db_zones = result.scalars().all()
            else:
                db_zones = self.db.query(Zone).filter(Zone.is_active == True).all()
            
            # Check if all active zones have corresponding zone files
            for zone in db_zones:
                if zone.zone_type == "master" and zone.file_path:
                    zone_file_path = Path(zone.file_path)
                    if not zone_file_path.exists():
                        errors.append(f"Zone {zone.name} references non-existent file: {zone.file_path}")
                    elif not zone_file_path.is_file():
                        errors.append(f"Zone {zone.name} file path is not a file: {zone.file_path}")
            
            # Check for orphaned zone files
            if self.zones_dir.exists():
                zone_files = set(f.name for f in self.zones_dir.glob("db.*") if f.is_file())
                db_zone_files = set()
                
                for zone in db_zones:
                    if zone.file_path:
                        zone_file_name = Path(zone.file_path).name
                        db_zone_files.add(zone_file_name)
                
                orphaned_files = zone_files - db_zone_files
                for orphaned_file in orphaned_files:
                    warnings.append(f"Zone file {orphaned_file} exists but is not referenced in database")
            
            # Check forwarder consistency
            from ..models.dns import Forwarder
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(select(Forwarder).where(Forwarder.is_active == True))
                db_forwarders = result.scalars().all()
            else:
                db_forwarders = self.db.query(Forwarder).filter(Forwarder.is_active == True).all()
            
            # Validate forwarder server configurations
            for forwarder in db_forwarders:
                if not forwarder.servers:
                    errors.append(f"Forwarder {forwarder.name} has no servers configured")
                elif not forwarder.domains:
                    errors.append(f"Forwarder {forwarder.name} has no domains configured")
            
            # Check RPZ consistency
            from ..models.security import RPZRule
            if isinstance(self.db, AsyncSession):
                result = await self.db.execute(select(RPZRule).where(RPZRule.is_active == True))
                rpz_rules = result.scalars().all()
            else:
                rpz_rules = self.db.query(RPZRule).filter(RPZRule.is_active == True).all()
            
            # Group rules by RPZ zone
            rpz_zones_in_db = set(rule.rpz_zone for rule in rpz_rules)
            
            # Check if RPZ zone files exist for all zones with rules
            for rpz_zone in rpz_zones_in_db:
                rpz_file_path = self.rpz_dir / f"db.rpz.{rpz_zone}"
                if not rpz_file_path.exists():
                    warnings.append(f"RPZ zone {rpz_zone} has rules but no zone file")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "zones_checked": len(db_zones),
                "forwarders_checked": len(db_forwarders),
                "rpz_zones_checked": len(rpz_zones_in_db)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate configuration consistency: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_service_dependencies(self) -> Dict[str, Any]:
        """Validate BIND9 service dependencies and system requirements"""
        errors = []
        warnings = []
        
        try:
            # Check if BIND9 service exists
            result = await self._run_command(["systemctl", "list-unit-files", self.service_name])
            if result["returncode"] != 0 or self.service_name not in result["stdout"]:
                errors.append(f"BIND9 service {self.service_name} is not installed or not found")
            
            # Check if rndc is available
            result = await self._run_command(["which", "rndc"])
            if result["returncode"] != 0:
                errors.append("rndc command not found - required for BIND9 management")
            
            # Check if named-checkconf is available
            result = await self._run_command(["which", "named-checkconf"])
            if result["returncode"] != 0:
                errors.append("named-checkconf command not found - required for configuration validation")
            
            # Check if named-checkzone is available
            result = await self._run_command(["which", "named-checkzone"])
            if result["returncode"] != 0:
                errors.append("named-checkzone command not found - required for zone validation")
            
            # Check directory permissions
            directories_to_check = [
                self.config_dir,
                self.zones_dir,
                self.rpz_dir
            ]
            
            for directory in directories_to_check:
                if not directory.exists():
                    warnings.append(f"Directory does not exist: {directory}")
                elif not directory.is_dir():
                    errors.append(f"Path is not a directory: {directory}")
                elif not os.access(directory, os.R_OK):
                    errors.append(f"Directory is not readable: {directory}")
                elif not os.access(directory, os.W_OK):
                    warnings.append(f"Directory is not writable: {directory}")
            
            # Check if BIND9 can bind to required ports
            import socket
            
            # Check if port 53 is available or in use by BIND9
            try:
                # Try to get the process using port 53
                result = await self._run_command(["lsof", "-i", ":53"])
                if result["returncode"] == 0:
                    if "named" not in result["stdout"]:
                        warnings.append("Port 53 is in use by a process other than BIND9")
                else:
                    # Port might be free, which is okay
                    pass
            except Exception:
                # lsof might not be available, skip this check
                pass
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "directories_checked": len(directories_to_check)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate service dependencies: {str(e)}"],
                "warnings": warnings
            }
    
    async def validate_production_environment(self) -> Dict[str, Any]:
        """Validate configuration for production environment compatibility (Ubuntu 24.04)"""
        logger = get_bind_logger()
        logger.info("Validating production environment compatibility")
        
        errors = []
        warnings = []
        
        try:
            # 1. Validate OS compatibility
            os_validation = await self._validate_os_compatibility()
            if not os_validation["valid"]:
                errors.extend(os_validation["errors"])
            warnings.extend(os_validation.get("warnings", []))
            
            # 2. Validate BIND9 version compatibility
            version_validation = await self._validate_bind_version_compatibility()
            if not version_validation["valid"]:
                errors.extend(version_validation["errors"])
            warnings.extend(version_validation.get("warnings", []))
            
            # 3. Validate system resources
            resource_validation = await self._validate_system_resources()
            if not resource_validation["valid"]:
                errors.extend(resource_validation["errors"])
            warnings.extend(resource_validation.get("warnings", []))
            
            # 4. Validate network configuration
            network_validation = await self._validate_network_configuration()
            if not network_validation["valid"]:
                errors.extend(network_validation["errors"])
            warnings.extend(network_validation.get("warnings", []))
            
            # 5. Validate security settings
            security_validation = await self._validate_security_settings()
            if not security_validation["valid"]:
                errors.extend(security_validation["errors"])
            warnings.extend(security_validation.get("warnings", []))
            
            # 6. Validate log configuration
            log_validation = await self._validate_log_configuration()
            if not log_validation["valid"]:
                errors.extend(log_validation["errors"])
            warnings.extend(log_validation.get("warnings", []))
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "environment": "production",
                "os_compatible": os_validation.get("valid", False),
                "bind_version_compatible": version_validation.get("valid", False),
                "resources_adequate": resource_validation.get("valid", False),
                "network_configured": network_validation.get("valid", False),
                "security_configured": security_validation.get("valid", False),
                "logging_configured": log_validation.get("valid", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to validate production environment: {e}")
            return {
                "valid": False,
                "errors": [f"Production environment validation failed: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_os_compatibility(self) -> Dict[str, Any]:
        """Validate operating system compatibility"""
        errors = []
        warnings = []
        
        try:
            # Check OS version
            result = await self._run_command(["lsb_release", "-a"])
            if result["returncode"] == 0:
                output = result["stdout"].lower()
                if "ubuntu" in output:
                    if "24.04" in output:
                        # Perfect match
                        pass
                    elif "22.04" in output or "20.04" in output:
                        warnings.append("Ubuntu version is supported but not the target version (24.04)")
                    else:
                        warnings.append("Ubuntu version may not be fully tested")
                else:
                    warnings.append("Non-Ubuntu OS detected - compatibility not guaranteed")
            else:
                warnings.append("Could not determine OS version")
            
            # Check systemd availability
            result = await self._run_command(["systemctl", "--version"])
            if result["returncode"] != 0:
                errors.append("systemd not available - required for service management")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate OS compatibility: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_bind_version_compatibility(self) -> Dict[str, Any]:
        """Validate BIND9 version compatibility"""
        errors = []
        warnings = []
        
        try:
            version = await self._get_bind_version()
            if version == "unknown":
                errors.append("Could not determine BIND9 version")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Extract version number
            import re
            version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
            if version_match:
                major, minor, patch = map(int, version_match.groups())
                
                # Check for minimum supported version (9.16+)
                if major < 9 or (major == 9 and minor < 16):
                    errors.append(f"BIND9 version {major}.{minor}.{patch} is too old - minimum 9.16 required")
                elif major == 9 and minor >= 18:
                    # Recommended version
                    pass
                elif major == 9 and minor >= 16:
                    warnings.append(f"BIND9 version {major}.{minor}.{patch} is supported but consider upgrading to 9.18+")
                elif major >= 10:
                    warnings.append(f"BIND9 version {major}.{minor}.{patch} is newer than tested - may have compatibility issues")
            else:
                warnings.append(f"Could not parse BIND9 version: {version}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "version": version
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate BIND9 version: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_system_resources(self) -> Dict[str, Any]:
        """Validate system resources for production use"""
        errors = []
        warnings = []
        
        try:
            # Check available memory
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    
                import re
                mem_total_match = re.search(r'MemTotal:\s+(\d+)\s+kB', meminfo)
                if mem_total_match:
                    mem_total_kb = int(mem_total_match.group(1))
                    mem_total_gb = mem_total_kb / (1024 * 1024)
                    
                    if mem_total_gb < 1:
                        errors.append(f"Insufficient memory: {mem_total_gb:.1f}GB - minimum 1GB required")
                    elif mem_total_gb < 2:
                        warnings.append(f"Low memory: {mem_total_gb:.1f}GB - consider upgrading to 2GB+")
            except Exception:
                warnings.append("Could not check system memory")
            
            # Check disk space
            try:
                import shutil
                total, used, free = shutil.disk_usage("/")
                free_gb = free / (1024**3)
                
                if free_gb < 1:
                    errors.append(f"Insufficient disk space: {free_gb:.1f}GB free - minimum 1GB required")
                elif free_gb < 5:
                    warnings.append(f"Low disk space: {free_gb:.1f}GB free - consider freeing up space")
            except Exception:
                warnings.append("Could not check disk space")
            
            # Check CPU cores
            try:
                import os
                cpu_count = os.cpu_count()
                if cpu_count and cpu_count < 1:
                    warnings.append("Single CPU core detected - performance may be limited")
            except Exception:
                warnings.append("Could not check CPU information")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate system resources: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_network_configuration(self) -> Dict[str, Any]:
        """Validate network configuration for DNS service"""
        errors = []
        warnings = []
        
        try:
            # Check if port 53 is available or used by BIND9
            result = await self._run_command(["ss", "-tulpn"])
            if result["returncode"] == 0:
                output = result["stdout"]
                port_53_lines = [line for line in output.split('\n') if ':53 ' in line]
                
                if port_53_lines:
                    bind_using_port = any('named' in line for line in port_53_lines)
                    if not bind_using_port:
                        errors.append("Port 53 is in use by another process - BIND9 cannot start")
                else:
                    # Port 53 is free, which is fine for initial setup
                    pass
            
            # Check network interfaces
            result = await self._run_command(["ip", "addr", "show"])
            if result["returncode"] == 0:
                output = result["stdout"]
                if "127.0.0.1" not in output:
                    warnings.append("Loopback interface not configured properly")
                
                # Check for at least one non-loopback interface
                interfaces = [line for line in output.split('\n') if 'inet ' in line and '127.0.0.1' not in line]
                if not interfaces:
                    warnings.append("No non-loopback network interfaces found")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate network configuration: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_security_settings(self) -> Dict[str, Any]:
        """Validate security settings for production environment"""
        errors = []
        warnings = []
        
        try:
            # Check if running as root (should not be in production)
            if os.geteuid() == 0:
                warnings.append("Running as root - consider using dedicated bind user for security")
            
            # Check firewall status
            result = await self._run_command(["ufw", "status"])
            if result["returncode"] == 0:
                if "Status: inactive" in result["stdout"]:
                    warnings.append("UFW firewall is inactive - consider enabling for security")
            
            # Check AppArmor/SELinux status
            result = await self._run_command(["aa-status"])
            if result["returncode"] == 0:
                if "apparmor module is loaded" not in result["stdout"].lower():
                    warnings.append("AppArmor not active - consider enabling for additional security")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate security settings: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_log_configuration(self) -> Dict[str, Any]:
        """Validate logging configuration for production environment"""
        errors = []
        warnings = []
        
        try:
            # Check if log directories exist and are writable
            log_dirs = [
                "/var/log/bind",
                "/var/log/hybrid-dns"
            ]
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if not log_path.exists():
                    warnings.append(f"Log directory does not exist: {log_dir}")
                elif not os.access(log_path, os.W_OK):
                    errors.append(f"Log directory is not writable: {log_dir}")
            
            # Check log rotation configuration
            logrotate_config = "/etc/logrotate.d/bind9"
            if not os.path.exists(logrotate_config):
                warnings.append("Log rotation not configured for BIND9 - logs may grow large")
            
            # Check syslog configuration
            result = await self._run_command(["systemctl", "is-active", "rsyslog"])
            if result["returncode"] != 0:
                warnings.append("rsyslog service not active - system logging may not work properly")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate log configuration: {str(e)}"],
                "warnings": warnings
            }

    async def get_statistics(self) -> Dict:
        """Get BIND9 statistics"""
        logger = get_bind_logger()
        try:
            # Try to get statistics from BIND's statistics channel
            import httpx
            settings = get_settings()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.BIND_STATS_URL}/json/v1/server")
                if response.status_code == 200:
                    return response.json()
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get BIND9 statistics: {e}")
            return {}
    
    async def flush_cache(self) -> bool:
        """Flush DNS cache"""
        logger = get_bind_logger()
        try:
            result = await self._run_command(["/usr/sbin/rndc", "flush"])
            success = result["returncode"] == 0
            
            if success:
                logger.info("DNS cache flushed successfully")
            else:
                logger.error(f"Failed to flush DNS cache: {result['stderr']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to flush DNS cache: {e}")
            return False
    
    async def _run_command(self, command: List[str], timeout: int = 30) -> Dict:
        """Run system command asynchronously, handling missing binaries gracefully"""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
            
        except asyncio.TimeoutError:
            logger = get_bind_logger()
            logger.error(f"Command timed out: {' '.join(command)}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out"
            }
        except FileNotFoundError as e:
            # Binary missing (e.g., named-checkconf, named-checkzone, rndc, systemctl) → don't spam stack traces
            logger = get_bind_logger()
            logger.error(f"Command not found: {' '.join(command)}")
            return {
                "returncode": 127,
                "stdout": "",
                "stderr": str(e)
            }
        except Exception as e:
            logger = get_bind_logger()
            logger.error(f"Command failed: {' '.join(command)}: {e}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    async def _get_bind_version(self) -> str:
        """Get BIND9 version"""
        try:
            result = await self._run_command(["named", "-v"])
            if result["returncode"] == 0:
                # Parse version from output
                version_line = result["stdout"].strip()
                return version_line
            
            return "unknown"
            
        except Exception:
            return "unknown"
    
    async def _get_zones_loaded_count(self) -> int:
        """Get count of zones currently loaded in BIND9"""
        try:
            # Try to get zone count from rndc status
            result = await self._run_command(["/usr/sbin/rndc", "status"])
            if result["returncode"] == 0:
                # Parse the output to find zone count
                lines = result["stdout"].split('\n')
                for line in lines:
                    if 'zones loaded' in line.lower():
                        # Extract number from line like "number of zones loaded: 123"
                        import re
                        match = re.search(r'(\d+)', line)
                        if match:
                            return int(match.group(1))
            
            # Fallback: count zones from database if available
            if self.db:
                from ..models.dns import Zone
                if isinstance(self.db, AsyncSession):
                    result = await self.db.execute(select(func.count(Zone.id)).where(Zone.is_active == True))
                    return int(result.scalar() or 0)
                else:
                    return self.db.query(Zone).filter(Zone.is_active == True).count()
            
            return 0
        except Exception as e:
            logger = get_bind_logger()
            logger.debug(f"Could not get zones loaded count: {e}")
            return 0
    
    async def _get_cache_size(self) -> int:
        """Get current DNS cache size in bytes"""
        try:
            # Try to get cache statistics from rndc
            result = await self._run_command(["/usr/sbin/rndc", "stats"])
            if result["returncode"] == 0:
                # Try to read the stats file
                stats_file = "/var/cache/bind/named.stats"
                if os.path.exists(stats_file):
                    with open(stats_file, 'r') as f:
                        content = f.read()
                        # Look for cache-related statistics
                        import re
                        # This is a simplified approach - actual parsing would be more complex
                        cache_match = re.search(r'cache.*?(\d+)', content, re.IGNORECASE)
                        if cache_match:
                            return int(cache_match.group(1))
            
            return 0
        except Exception as e:
            logger = get_bind_logger()
            logger.debug(f"Could not get cache size: {e}")
            return 0
    
    # Zone management methods
    async def create_zone_file(self, zone: Zone) -> bool:
        """Create zone file for a zone with comprehensive validation"""
        logger = get_bind_logger()
        logger.info(f"Creating zone file for zone: {zone.name}")
        
        try:
            # Ensure zones directory exists
            self.zones_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate zone file path if not set
            if not zone.file_path:
                zone.file_path = self._validate_zone_file_path(zone.name, zone.zone_type)
            
            zone_file_path = Path(zone.file_path)
            
            # Get zone records from database if available
            records = []
            if self.db:
                if isinstance(self.db, AsyncSession):
                    # Async session
                    result = await self.db.execute(
                        select(DNSRecord).filter(
                            DNSRecord.zone_id == zone.id,
                            DNSRecord.is_active == True
                        )
                    )
                    records = result.scalars().all()
                else:
                    # Sync session
                    records = self.db.query(DNSRecord).filter(
                        DNSRecord.zone_id == zone.id,
                        DNSRecord.is_active == True
                    ).all()
            
            # Pre-validate zone and records before generation
            if zone.zone_type == "master":
                pre_validation = await self.validate_zone_file_before_generation(zone, records)
                if not pre_validation["valid"]:
                    logger.error(f"Pre-validation failed for zone {zone.name}: {pre_validation['errors']}")
                    # Log warnings but don't fail
                    if pre_validation.get("warnings"):
                        logger.warning(f"Pre-validation warnings for zone {zone.name}: {pre_validation['warnings']}")
                    # Continue with generation despite validation errors for now
                    # In production, you might want to fail here
            
            # Backup existing zone file if it exists
            if zone_file_path.exists():
                await self._backup_zone_file(zone_file_path)
            
            # Generate zone file content based on zone type
            if zone.zone_type == "master":
                content = await self._generate_master_zone_file(zone, records)
            elif zone.zone_type == "slave":
                content = await self._generate_slave_zone_file(zone)
            else:
                logger.warning(f"Unsupported zone type for file generation: {zone.zone_type}")
                return False
            
            # Write zone file
            zone_file_path.write_text(content, encoding='utf-8')
            
            # Set appropriate permissions (readable by BIND9, group writable)
            zone_file_path.chmod(0o664)
            
            # Validate the generated zone file
            if zone.zone_type == "master":
                post_validation = await self.validate_generated_zone_file(zone, zone_file_path)
                if not post_validation["valid"]:
                    logger.error(f"Generated zone file validation failed for {zone.name}: {post_validation['errors']}")
                    # Don't fail the creation, but log the issues
                
                if post_validation.get("warnings"):
                    logger.warning(f"Generated zone file warnings for {zone.name}: {post_validation['warnings']}")
            
            logger.info(f"Successfully created zone file: {zone_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create zone file for {zone.name}: {e}")
            return False
    
    async def update_zone_file(self, zone: Zone) -> bool:
        """Update zone file for a zone"""
        logger = get_bind_logger()
        logger.info(f"Updating zone file for zone: {zone.name}")
        
        try:
            # For master zones, regenerate the zone file
            if zone.zone_type == "master":
                return await self.create_zone_file(zone)
            elif zone.zone_type == "slave":
                # For slave zones, just update the configuration
                # The actual zone data comes from master servers
                return await self._update_slave_zone_config(zone)
            else:
                logger.warning(f"Unsupported zone type for file update: {zone.zone_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update zone file for {zone.name}: {e}")
            return False
    
    async def delete_zone_file(self, zone_id: int) -> bool:
        """Delete zone file for a zone"""
        logger = get_bind_logger()
        logger.info(f"Deleting zone file for zone ID: {zone_id}")
        
        try:
            # Get zone information from database if available
            if self.db:
                if self.is_async:
                    result = await self.db.execute(select(Zone).filter(Zone.id == zone_id))
                    zone = result.scalar_one_or_none()
                else:
                    zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
                if zone and zone.file_path:
                    zone_file_path = Path(zone.file_path)
                    if zone_file_path.exists():
                        zone_file_path.unlink()
                        logger.info(f"Deleted zone file: {zone_file_path}")
                    else:
                        logger.warning(f"Zone file not found: {zone_file_path}")
                else:
                    logger.warning(f"Zone {zone_id} not found or has no file path")
            else:
                logger.warning("No database connection available for zone file deletion")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete zone file for zone ID {zone_id}: {e}")
            return False
    
    async def reload_configuration(self) -> bool:
        """Reload BIND9 configuration (alias for reload_service)"""
        return await self.reload_service()
    
    async def create_full_configuration_backup(self, description: str = "") -> Optional[str]:
        """Create a full backup of all BIND configuration before major changes"""
        from .backup_service import BackupService
        
        logger = get_bind_logger()
        logger.info("Creating full configuration backup before changes")
        
        try:
            backup_service = BackupService()
            backup_id = await backup_service.create_full_configuration_backup(
                description or f"Full configuration backup before changes at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if backup_id:
                logger.info(f"Successfully created full configuration backup: {backup_id}")
            else:
                logger.error("Failed to create full configuration backup")
            
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create full configuration backup: {e}")
            return None
    
    async def backup_before_zone_changes(self, zone_name: str, operation: str) -> bool:
        """Create backup before zone-related changes"""
        logger = get_bind_logger()
        logger.info(f"Creating backup before {operation} operation on zone: {zone_name}")
        
        try:
            # Create full configuration backup for major operations
            if operation in ['create', 'delete']:
                backup_id = await self.create_full_configuration_backup(
                    f"Before {operation} zone {zone_name}"
                )
                return backup_id is not None
            
            # For updates, just backup the specific zone file if it exists
            if self.db:
                from ..models.dns import Zone
                if self.is_async:
                    result = await self.db.execute(select(Zone).filter(Zone.name == zone_name))
                    zone = result.scalar_one_or_none()
                else:
                    zone = self.db.query(Zone).filter(Zone.name == zone_name).first()
                if zone and zone.file_path:
                    zone_file_path = Path(zone.file_path)
                    if zone_file_path.exists():
                        return await self._backup_zone_file(zone_file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup before {operation} on zone {zone_name}: {e}")
            return False
    
    async def backup_before_forwarder_changes(self, operation: str) -> bool:
        """Create backup before forwarder-related changes"""
        logger = get_bind_logger()
        logger.info(f"Creating backup before forwarder {operation} operation")
        
        try:
            # Always create full backup for forwarder changes as they affect main config
            backup_id = await self.create_full_configuration_backup(
                f"Before forwarder {operation} operation"
            )
            return backup_id is not None
            
        except Exception as e:
            logger.error(f"Failed to create backup before forwarder {operation}: {e}")
            return False
    
    async def backup_before_rpz_changes(self, rpz_zone: str, operation: str) -> bool:
        """Create backup before RPZ-related changes"""
        logger = get_bind_logger()
        logger.info(f"Creating backup before {operation} operation on RPZ zone: {rpz_zone}")
        
        try:
            # For bulk operations or policy changes, create full backup
            if operation in ['bulk_import', 'policy_update']:
                backup_id = await self.create_full_configuration_backup(
                    f"Before {operation} on RPZ zone {rpz_zone}"
                )
                return backup_id is not None
            
            # For individual rule changes, backup the specific RPZ file
            rpz_file_path = self.rpz_dir / f"db.rpz.{rpz_zone}"
            if rpz_file_path.exists():
                return await self._backup_rpz_file(rpz_file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup before {operation} on RPZ zone {rpz_zone}: {e}")
            return False
    
    async def reload_zone(self, zone_id: int) -> bool:
        """Reload specific zone"""
        logger = get_bind_logger()
        logger.info(f"Reloading zone ID: {zone_id}")
        
        try:
            if not self.db:
                logger.warning("No database connection, falling back to full reload")
                return await self.reload_service()
            
            # Get zone name from database
            if self.is_async:
                result = await self.db.execute(select(Zone).filter(Zone.id == zone_id))
                zone = result.scalar_one_or_none()
            else:
                zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
                
            if not zone:
                logger.error(f"Zone {zone_id} not found")
                return False
            
            # Reload specific zone using rndc with full path
            result = await self._run_command(["/usr/sbin/rndc", "reload", zone.name])
            
            if result["returncode"] == 127:  # Command not found
                logger.warning("rndc command not found, falling back to full reload")
                return await self.reload_service()
            
            success = result["returncode"] == 0
            
            if success:
                logger.info(f"Successfully reloaded zone {zone.name}")
            else:
                logger.error(f"Failed to reload zone {zone.name}: {result['stderr']}")
                # Fallback to full reload
                logger.info("Attempting full configuration reload")
                success = await self.reload_service()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to reload zone {zone_id}: {e}")
            return False
    
    async def validate_zone(self, zone: Zone) -> Dict:
        """Validate zone configuration and zone file"""
        logger = get_bind_logger()
        logger.info(f"Validating zone: {zone.name}")
        
        errors = []
        warnings = []
        
        try:
            # Validate zone configuration first
            config_validation = self._validate_zone_configuration(zone)
            errors.extend(config_validation["errors"])
            warnings.extend(config_validation["warnings"])
            
            # Validate zone file if it exists
            if zone.file_path:
                zone_file_path = Path(zone.file_path)
                if not zone_file_path.exists():
                    errors.append(f"Zone file does not exist: {zone_file_path}")
                else:
                    # Validate zone file syntax using named-checkzone
                    syntax_validation = await self._validate_zone_file_syntax(zone, zone_file_path)
                    errors.extend(syntax_validation["errors"])
                    warnings.extend(syntax_validation["warnings"])
                    
                    # Validate zone file content
                    content_validation = await self._validate_zone_file_content(zone, zone_file_path)
                    errors.extend(content_validation["errors"])
                    warnings.extend(content_validation["warnings"])
            else:
                if zone.zone_type == "master":
                    errors.append("Master zone must have a zone file path")
                else:
                    warnings.append("Zone file path not set")
            
            # Validate zone records if database is available
            if self.db and zone.zone_type == "master":
                records_validation = await self._validate_zone_records(zone)
                errors.extend(records_validation["errors"])
                warnings.extend(records_validation["warnings"])
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Failed to validate zone {zone.name}: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    async def update_zone_file_from_db(self, zone_id: int) -> bool:
        """Update zone file from database records"""
        logger = get_bind_logger()
        logger.info(f"Updating zone file from database for zone ID: {zone_id}")
        
        try:
            if not self.db:
                logger.error("No database connection available")
                return False
            
            # Get zone from database
            if self.is_async:
                result = await self.db.execute(select(Zone).filter(Zone.id == zone_id))
                zone = result.scalar_one_or_none()
            else:
                zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
            if not zone:
                logger.error(f"Zone {zone_id} not found in database")
                return False
            
            # Update the zone file
            return await self.update_zone_file(zone)
            
        except Exception as e:
            logger.error(f"Failed to update zone file from database for zone ID {zone_id}: {e}")
            return False
    
    async def update_forwarder_configuration(self) -> bool:
        """Update forwarder configuration from database"""
        logger = get_bind_logger()
        logger.info("Updating forwarder configuration")
        
        try:
            if not self.db:
                logger.error("No database connection available for forwarder configuration update")
                return False
            
            # Import here to avoid circular imports
            from ..models.dns import Forwarder
            
            # Get all active forwarders from database
            forwarders = self.db.query(Forwarder).filter(Forwarder.is_active == True).all()
            
            # Generate forwarder configuration
            success = await self.generate_forwarder_configuration(forwarders)
            
            if success:
                logger.info(f"Successfully updated forwarder configuration with {len(forwarders)} forwarders")
            else:
                logger.error("Failed to update forwarder configuration")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update forwarder configuration: {e}")
            return False
    
    async def update_rpz_zone_file(self, rpz_zone: str) -> bool:
        """Update RPZ zone file from database rules"""
        logger = get_bind_logger()
        logger.info(f"Updating RPZ zone file: {rpz_zone}")
        
        try:
            if not self.db:
                logger.error("No database connection available for RPZ zone file update")
                return False
            
            # Import here to avoid circular imports
            from ..models.security import RPZRule
            
            # Get all active rules for this RPZ zone
            rules = self.db.query(RPZRule).filter(
                RPZRule.rpz_zone == rpz_zone,
                RPZRule.is_active == True
            ).all()
            
            # Generate RPZ zone file
            success = await self.generate_rpz_zone_file(rpz_zone, rules)
            
            if success:
                logger.info(f"Successfully updated RPZ zone file for {rpz_zone} with {len(rules)} rules")
            else:
                logger.error(f"Failed to update RPZ zone file for {rpz_zone}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update RPZ zone file for {rpz_zone}: {e}")
            return False
    
    async def generate_rpz_zone_file(self, rpz_zone: str, rules: List) -> bool:
        """Generate RPZ zone file from rules"""
        logger = get_bind_logger()
        logger.info(f"Generating RPZ zone file for: {rpz_zone}")
        
        try:
            # Ensure RPZ directory exists
            self.rpz_dir.mkdir(parents=True, exist_ok=True)
            
            # Define RPZ zone file path
            rpz_file_path = self.rpz_dir / f"db.rpz.{rpz_zone}"
            
            # Backup existing RPZ file if it exists
            if rpz_file_path.exists():
                await self._backup_rpz_file(rpz_file_path)
            
            # Validate rules before generation
            validated_rules = []
            for rule in rules:
                validation = await self.validate_rpz_rule(rule)
                if validation["valid"]:
                    validated_rules.append(rule)
                else:
                    logger.warning(f"Skipping invalid RPZ rule {rule.id}: {validation['errors']}")
            
            # Get RPZ category information
            category_info = self.get_rpz_category_info(rpz_zone)
            
            # Calculate statistics
            active_rules_count = len(validated_rules)
            rules_by_action = self._group_rpz_rules_by_action(validated_rules)
            
            # Generate serial number (YYYYMMDDHH format)
            serial = datetime.now().strftime('%Y%m%d%H')
            
            # Determine which template to use
            template_name = "rpz_category.j2" if category_info else "rpz_zone.j2"
            
            # Use enhanced formatting method for better rule serialization
            try:
                content = self.format_rpz_zone_file_with_rules(rpz_zone, validated_rules, category_info)
                logger.debug(f"Generated RPZ zone file content for {rpz_zone} using enhanced serialization")
            except Exception as e:
                logger.warning(f"Enhanced serialization failed for {rpz_zone}, falling back to template: {e}")
                
                # Fallback to template-based generation
                template = self.jinja_env.get_template(template_name)
                content = template.render(
                    rpz_zone=rpz_zone,
                    category=rpz_zone,
                    category_info=category_info,
                    rules=validated_rules,
                    active_rules_count=active_rules_count,
                    rules_by_action=rules_by_action,
                    serial=serial,
                    generated_at=datetime.now(),
                    primary_ns=self._get_primary_ns(),
                    admin_email=self._get_admin_email(),
                    ttl=300,
                    refresh=3600,
                    retry=1800,
                    expire=604800,
                    minimum=300
                )
            
            # Write RPZ zone file
            rpz_file_path.write_text(content, encoding='utf-8')
            
            # Set appropriate permissions (readable by BIND9, group writable)
            rpz_file_path.chmod(0o664)
            
            # Validate the generated RPZ zone file
            validation_result = await self.validate_generated_rpz_zone_file(rpz_zone, rpz_file_path)
            if not validation_result["valid"]:
                logger.error(f"Generated RPZ zone file validation failed for {rpz_zone}: {validation_result['errors']}")
                # Don't fail the creation, but log the issues
            
            if validation_result.get("warnings"):
                logger.warning(f"Generated RPZ zone file warnings for {rpz_zone}: {validation_result['warnings']}")
            
            logger.info(f"Successfully generated RPZ zone file: {rpz_file_path} with {active_rules_count} rules")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate RPZ zone file for {rpz_zone}: {e}")
            return False
    
    async def validate_rpz_rule(self, rule) -> Dict[str, Any]:
        """Validate an RPZ rule before including in zone file"""
        errors = []
        warnings = []
        
        try:
            # Validate domain
            if not rule.domain:
                errors.append("Domain is required")
            elif not self._is_valid_rpz_domain(rule.domain):
                errors.append(f"Invalid domain format: {rule.domain}")
            
            # Validate action
            valid_actions = ['block', 'redirect', 'passthru']
            if rule.action not in valid_actions:
                errors.append(f"Invalid action: {rule.action}")
            
            # Validate redirect target for redirect actions
            if rule.action == 'redirect':
                if not rule.redirect_target:
                    errors.append("Redirect target is required for redirect action")
                elif not self._is_valid_domain_name(rule.redirect_target):
                    errors.append(f"Invalid redirect target: {rule.redirect_target}")
            
            # Validate RPZ zone
            valid_zones = ['malware', 'phishing', 'adult', 'social-media', 'gambling', 'custom']
            if rule.rpz_zone not in valid_zones:
                warnings.append(f"Unknown RPZ zone: {rule.rpz_zone}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger = get_bind_logger()
            logger.error(f"Failed to validate RPZ rule: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    def _is_valid_rpz_domain(self, domain: str) -> bool:
        """Validate domain for RPZ usage"""
        if not domain:
            return False
        
        # Remove protocol prefixes if present
        domain = domain.replace('http://', '').replace('https://', '')
        domain = domain.rstrip('/')
        
        # Handle wildcard domains
        if domain.startswith('*.'):
            domain = domain[2:]
        
        # Validate as domain name
        return self._is_valid_domain_name(domain)
    
    def get_rpz_category_info(self, rpz_zone: str) -> Dict[str, str]:
        """Get RPZ category information for template rendering"""
        category_info = {
            'malware': {
                'display_name': 'Malware Protection',
                'description': 'Blocks known malware and malicious domains'
            },
            'phishing': {
                'display_name': 'Phishing Protection',
                'description': 'Blocks phishing and fraudulent websites'
            },
            'adult': {
                'display_name': 'Adult Content Filter',
                'description': 'Blocks adult and inappropriate content'
            },
            'social-media': {
                'display_name': 'Social Media Filter',
                'description': 'Blocks social media platforms and services'
            },
            'gambling': {
                'display_name': 'Gambling Filter',
                'description': 'Blocks gambling and betting websites'
            },
            'custom': {
                'display_name': 'Custom Rules',
                'description': 'Custom block and allow rules'
            }
        }
        
        return category_info.get(rpz_zone, {
            'display_name': rpz_zone.title(),
            'description': f'Custom RPZ category: {rpz_zone}'
        })
    
    def _group_rpz_rules_by_action(self, rules: List) -> Dict[str, int]:
        """Group RPZ rules by action for statistics"""
        action_counts = {'block': 0, 'redirect': 0, 'passthru': 0}
        
        for rule in rules:
            if rule.is_active and rule.action in action_counts:
                action_counts[rule.action] += 1
        
        return action_counts
    
    def _get_primary_ns(self) -> str:
        """Get primary name server for RPZ zone files"""
        try:
            settings = get_settings()
            return getattr(settings, 'PRIMARY_NS', 'localhost.')
        except:
            return 'localhost.'
    
    def _get_admin_email(self) -> str:
        """Get admin email for RPZ zone files"""
        try:
            settings = get_settings()
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@localhost')
            # Convert email to DNS format (replace @ with .)
            return admin_email.replace('@', '.') + '.'
        except:
            return 'admin.localhost.'
    
    async def _backup_rpz_file(self, rpz_file_path: Path) -> bool:
        """Backup existing RPZ zone file using centralized backup service"""
        from .backup_service import BackupService, BackupType
        
        backup_service = BackupService()
        metadata = await backup_service.create_backup(
            rpz_file_path, 
            BackupType.RPZ_FILE, 
            f"RPZ file backup before update: {rpz_file_path.name}"
        )
        return metadata is not None
    
    async def validate_generated_rpz_zone_file(self, rpz_zone: str, rpz_file_path: Path) -> Dict:
        """Validate a generated RPZ zone file"""
        logger = get_bind_logger()
        logger.info(f"Validating generated RPZ zone file: {rpz_file_path}")
        
        errors = []
        warnings = []
        
        try:
            # Check if file exists and is readable
            if not rpz_file_path.exists():
                errors.append(f"RPZ zone file does not exist: {rpz_file_path}")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Validate file permissions
            if not rpz_file_path.stat().st_mode & 0o044:
                warnings.append("RPZ zone file may not be readable by BIND9 (check permissions)")
            
            # Use named-checkzone for RPZ zone validation
            rpz_zone_name = f"{rpz_zone}.rpz"
            result = await self._run_command([
                "/usr/sbin/named-checkzone",
                "-i", "local",  # Allow local addresses
                "-k", "warn",   # Warn on issues but don't fail
                rpz_zone_name,
                str(rpz_file_path)
            ])
            
            if result["returncode"] != 0:
                # Parse error output
                stderr_lines = result["stderr"].strip().split('\n')
                for line in stderr_lines:
                    if line.strip():
                        if "warning" in line.lower():
                            warnings.append(f"RPZ zone warning: {line.strip()}")
                        else:
                            errors.append(f"RPZ zone error: {line.strip()}")
            
            # Additional RPZ-specific validation
            content_validation = await self._validate_rpz_zone_content(rpz_file_path)
            errors.extend(content_validation["errors"])
            warnings.extend(content_validation["warnings"])
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Failed to validate RPZ zone file {rpz_file_path}: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_rpz_zone_content(self, rpz_file_path: Path) -> Dict:
        """Validate RPZ zone file content for RPZ-specific requirements"""
        errors = []
        warnings = []
        
        try:
            content = rpz_file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Check for required RPZ elements
            has_soa = False
            has_ns = False
            has_origin = False
            rule_count = 0
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Check for SOA record
                if 'SOA' in line.upper():
                    has_soa = True
                
                # Check for NS record
                if 'NS' in line.upper() and 'SOA' not in line.upper():
                    has_ns = True
                
                # Check for $ORIGIN directive
                if line.startswith('$ORIGIN') and '.rpz.' in line:
                    has_origin = True
                
                # Count RPZ rules (CNAME records)
                if 'CNAME' in line.upper():
                    rule_count += 1
            
            # Validate required elements
            if not has_soa:
                errors.append("RPZ zone file must contain an SOA record")
            
            if not has_ns:
                errors.append("RPZ zone file must contain an NS record")
            
            if not has_origin:
                warnings.append("RPZ zone file should include $ORIGIN directive with .rpz. suffix")
            
            # Check rule count
            if rule_count == 0:
                warnings.append("RPZ zone file contains no rules")
            elif rule_count > 10000:
                warnings.append(f"RPZ zone file contains many rules ({rule_count}), consider performance impact")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "rule_count": rule_count
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Content validation error: {str(e)}"],
                "warnings": warnings
            }
    
    async def generate_forwarder_configuration(self, forwarders: List) -> bool:
        """Generate forwarder configuration file from database forwarders"""
        logger = get_bind_logger()
        logger.info(f"Generating forwarder configuration for {len(forwarders)} forwarders")
        
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Define forwarder configuration file path
            forwarder_config_path = self.config_dir / "forwarders.conf"
            
            # Backup existing configuration if it exists
            if forwarder_config_path.exists():
                await self._backup_configuration_file(forwarder_config_path)
            
            # Validate forwarders before generation
            validated_forwarders = []
            for forwarder in forwarders:
                validation = await self.validate_forwarder_configuration(forwarder)
                if validation["valid"]:
                    validated_forwarders.append(forwarder)
                else:
                    logger.warning(f"Skipping invalid forwarder {forwarder.name}: {validation['errors']}")
            
            # Handle forwarder priority ordering
            prioritized_forwarders = await self.handle_forwarder_priority(validated_forwarders)
            
            # Generate configuration content using template
            template = self.jinja_env.get_template("config/forwarders.j2")
            content = template.render(
                forwarders=prioritized_forwarders,
                generated_at=datetime.now(),
                config_version="1.0"
            )
            
            # Write configuration file
            forwarder_config_path.write_text(content, encoding='utf-8')
            
            # Set appropriate permissions
            forwarder_config_path.chmod(0o644)
            
            # Update main configuration to include forwarders.conf
            await self._update_main_config_include(forwarder_config_path)
            
            logger.info(f"Successfully generated forwarder configuration: {forwarder_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate forwarder configuration: {e}")
            return False
    
    async def generate_acl_configuration(self, acls: List = None, **template_vars) -> bool:
        """Generate ACL configuration file from database ACLs"""
        logger = get_bind_logger()
        logger.info(f"Generating ACL configuration for {len(acls) if acls else 0} ACLs")
        
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Define ACL configuration file path
            acl_config_path = self.config_dir / "acl.conf"
            
            # Backup existing configuration if it exists
            if acl_config_path.exists():
                await self._backup_configuration_file(acl_config_path)
            
            # Validate ACLs before generation
            validated_acls = []
            if acls:
                for acl in acls:
                    validation = await self.validate_acl_configuration(acl)
                    if validation["valid"]:
                        validated_acls.append(acl)
                    else:
                        logger.warning(f"Skipping invalid ACL {acl.name}: {validation['errors']}")
            
            # Prepare template variables with defaults
            template_data = {
                "acls": validated_acls,
                "generated_at": datetime.now(),
                "config_version": "1.0",
                "include_predefined_acls": template_vars.get("include_predefined_acls", True),
                "include_security_acls": template_vars.get("include_security_acls", True),
                "include_dynamic_acls": template_vars.get("include_dynamic_acls", False),
                "trusted_networks": template_vars.get("trusted_networks", []),
                "management_networks": template_vars.get("management_networks", []),
                "dns_servers": template_vars.get("dns_servers", []),
                "monitoring_systems": template_vars.get("monitoring_systems", []),
                "blocked_networks": template_vars.get("blocked_networks", []),
                "rate_limited_networks": template_vars.get("rate_limited_networks", []),
                "dynamic_threats": template_vars.get("dynamic_threats", []),
                "dynamic_allow": template_vars.get("dynamic_allow", [])
            }
            
            # Generate configuration content using template
            template = self.jinja_env.get_template("config/acl.j2")
            content = template.render(**template_data)
            
            # Write configuration file
            acl_config_path.write_text(content, encoding='utf-8')
            
            # Set appropriate permissions
            acl_config_path.chmod(0o644)
            
            # Update main configuration to include acl.conf
            await self._update_main_config_include_acl(acl_config_path)
            
            logger.info(f"Successfully generated ACL configuration: {acl_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate ACL configuration: {e}")
            return False
    
    async def validate_acl_configuration(self, acl) -> Dict[str, Any]:
        """Validate ACL configuration before generation"""
        errors = []
        warnings = []
        
        try:
            # Validate ACL name
            if not acl.name or len(acl.name.strip()) == 0:
                errors.append("ACL name cannot be empty")
            elif not acl.name.replace('-', '').replace('_', '').isalnum():
                errors.append("ACL name must contain only alphanumeric characters, hyphens, and underscores")
            
            # Check for reserved BIND9 ACL names
            reserved_names = ['any', 'none', 'localhost', 'localnets']
            if acl.name.lower() in reserved_names:
                errors.append(f"ACL name '{acl.name}' is reserved by BIND9")
            
            # Validate ACL entries
            if not acl.entries or len(acl.entries) == 0:
                warnings.append(f"ACL '{acl.name}' has no entries")
            else:
                for entry in acl.entries:
                    if entry.is_active:
                        entry_validation = await self._validate_acl_entry(entry)
                        if not entry_validation["valid"]:
                            errors.extend(entry_validation["errors"])
                        warnings.extend(entry_validation.get("warnings", []))
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"ACL validation error: {str(e)}"],
                "warnings": warnings
            }
    
    async def _validate_acl_entry(self, entry) -> Dict[str, Any]:
        """Validate individual ACL entry"""
        errors = []
        warnings = []
        
        try:
            import ipaddress
            
            address = entry.address.strip()
            
            # Handle negation prefix
            if address.startswith('!'):
                address = address[1:].strip()
            
            # Try to validate as IP network
            try:
                ipaddress.ip_network(address, strict=False)
            except ValueError:
                # Check if it's a valid hostname
                import re
                hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
                if not re.match(hostname_pattern, address):
                    errors.append(f"Invalid address format: {entry.address}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Entry validation error: {str(e)}"],
                "warnings": warnings
            }
    
    async def _update_main_config_include_acl(self, acl_config_path: Path) -> bool:
        """Update main BIND configuration to include acl.conf"""
        logger = get_bind_logger()
        
        try:
            # Read main configuration file
            main_config_path = Path("/etc/bind/named.conf.local")
            if not main_config_path.exists():
                logger.warning(f"Main config file not found: {main_config_path}")
                return False
            
            content = main_config_path.read_text(encoding='utf-8')
            
            # Check if ACL include already exists
            include_line = f'include "{acl_config_path}";'
            if include_line in content:
                logger.debug("ACL configuration include already exists in main config")
                return True
            
            # Add include at the beginning of the file (after comments)
            lines = content.split('\n')
            insert_index = 0
            
            # Find the first non-comment, non-empty line
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith('//') and not stripped.startswith('#'):
                    insert_index = i
                    break
            
            # Insert the include line
            lines.insert(insert_index, include_line)
            lines.insert(insert_index + 1, "")  # Add empty line for readability
            
            # Write back to file
            main_config_path.write_text('\n'.join(lines), encoding='utf-8')
            
            logger.info(f"Added ACL configuration include to {main_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update main config with ACL include: {e}")
            return False

    async def validate_forwarder_configuration(self, forwarder) -> Dict[str, Any]:
        """Validate forwarder configuration before generation"""
        errors = []
        warnings = []
        
        try:
            # Validate forwarder name
            if not forwarder.name:
                errors.append("Forwarder name is required")
            
            # Validate domains
            if not forwarder.domains or len(forwarder.domains) == 0:
                errors.append("At least one domain is required")
            else:
                for domain in forwarder.domains:
                    if not self._is_valid_domain_name(domain):
                        errors.append(f"Invalid domain name: {domain}")
            
            # Validate servers
            if not forwarder.servers or len(forwarder.servers) == 0:
                errors.append("At least one server is required")
            else:
                for server in forwarder.servers:
                    # Validate IP address
                    if not server.get('ip'):
                        errors.append("Server IP address is required")
                    else:
                        try:
                            import ipaddress
                            ipaddress.ip_address(server['ip'])
                        except ValueError:
                            errors.append(f"Invalid IP address: {server['ip']}")
                    
                    # Validate port
                    port = server.get('port', 53)
                    if not isinstance(port, int) or port < 1 or port > 65535:
                        errors.append(f"Invalid port number: {port}")
                    
                    # Validate priority
                    priority = server.get('priority', 1)
                    if not isinstance(priority, int) or priority < 1 or priority > 10:
                        warnings.append(f"Priority should be between 1-10, got: {priority}")
            
            # Validate forwarder type
            valid_types = ['active_directory', 'intranet', 'public']
            if forwarder.forwarder_type not in valid_types:
                warnings.append(f"Unknown forwarder type: {forwarder.forwarder_type}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger = get_bind_logger()
            logger.error(f"Failed to validate forwarder configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    async def test_forwarder_connectivity(self, forwarder) -> Dict[str, Any]:
        """Test connectivity to forwarder servers"""
        logger = get_bind_logger()
        logger.info(f"Testing connectivity for forwarder: {forwarder.name}")
        
        results = []
        
        try:
            for server in forwarder.servers:
                server_ip = server.get('ip')
                server_port = server.get('port', 53)
                
                if not server_ip:
                    continue
                
                # Test DNS connectivity
                test_result = await self._test_dns_server_connectivity(server_ip, server_port)
                
                results.append({
                    'server_ip': server_ip,
                    'server_port': server_port,
                    'priority': server.get('priority', 1),
                    **test_result
                })
            
            # Calculate overall status
            successful_tests = sum(1 for r in results if r.get('status') == 'healthy')
            overall_status = 'healthy' if successful_tests > 0 else 'unhealthy'
            
            return {
                'forwarder_name': forwarder.name,
                'overall_status': overall_status,
                'successful_servers': successful_tests,
                'total_servers': len(results),
                'server_results': results,
                'tested_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to test forwarder connectivity: {e}")
            return {
                'forwarder_name': forwarder.name,
                'overall_status': 'error',
                'error_message': str(e),
                'tested_at': datetime.now()
            }
    
    async def _test_dns_server_connectivity(self, server_ip: str, server_port: int = 53) -> Dict[str, Any]:
        """Test connectivity to a single DNS server"""
        import socket
        import asyncio
        
        try:
            # Test basic TCP connectivity first
            start_time = datetime.now()
            
            # Create socket connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # 5 second timeout
            
            try:
                result = sock.connect_ex((server_ip, server_port))
                sock.close()
                
                end_time = datetime.now()
                response_time = int((end_time - start_time).total_seconds() * 1000)
                
                if result == 0:
                    return {
                        'status': 'healthy',
                        'response_time': response_time,
                        'test_type': 'tcp_connect'
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'error_message': f'TCP connection failed (error {result})',
                        'test_type': 'tcp_connect'
                    }
                    
            except socket.timeout:
                return {
                    'status': 'timeout',
                    'error_message': 'Connection timeout',
                    'test_type': 'tcp_connect'
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'error_message': f'Connection error: {str(e)}',
                    'test_type': 'tcp_connect'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error_message': f'Test error: {str(e)}',
                'test_type': 'tcp_connect'
            }
    
    async def _backup_configuration_file(self, config_file_path: Path) -> bool:
        """Create a backup of existing configuration file using centralized backup service"""
        from .backup_service import BackupService, BackupType
        
        backup_service = BackupService()
        metadata = await backup_service.create_backup(
            config_file_path, 
            BackupType.CONFIGURATION, 
            f"Configuration backup before update: {config_file_path.name}"
        )
        return metadata is not None
    
    async def _update_main_config_include(self, forwarder_config_path: Path) -> bool:
        """Update main BIND configuration to include forwarders.conf"""
        logger = get_bind_logger()
        
        try:
            # Path to main local configuration
            main_config_path = self.config_dir / "named.conf.local"
            
            if not main_config_path.exists():
                logger.warning(f"Main configuration file not found: {main_config_path}")
                return False
            
            # Backup existing configuration before modification
            await self._backup_configuration_file(main_config_path)
            
            # Read current configuration
            current_config = main_config_path.read_text(encoding='utf-8')
            
            # Check if forwarders.conf is already included
            include_line = f'include "{forwarder_config_path}";'
            
            if include_line not in current_config:
                # Add include at the beginning of the file
                lines = current_config.split('\n')
                
                # Find a good place to insert (after initial comments)
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('//'):
                        insert_index = i
                        break
                
                # Insert the include line
                lines.insert(insert_index, include_line)
                lines.insert(insert_index + 1, '')  # Add blank line
                
                # Write updated configuration
                updated_config = '\n'.join(lines)
                main_config_path.write_text(updated_config, encoding='utf-8')
                
                logger.info(f"Added forwarders.conf include to main configuration")
            else:
                logger.debug("Forwarders.conf already included in main configuration")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update main configuration include: {e}")
            return False
    
    def _is_valid_domain_name(self, domain: str) -> bool:
        """Validate domain name format"""
        import re
        
        if not domain or len(domain) > 253:
            return False
        
        # Remove trailing dot if present
        if domain.endswith('.'):
            domain = domain[:-1]
        
        # Check for valid domain name pattern
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        return bool(domain_pattern.match(domain))
    
    async def setup_conditional_forwarding(self, forwarder) -> bool:
        """Set up conditional forwarding for a specific forwarder"""
        logger = get_bind_logger()
        logger.info(f"Setting up conditional forwarding for: {forwarder.name}")
        
        try:
            # Validate forwarder configuration
            validation = await self.validate_forwarder_configuration(forwarder)
            if not validation["valid"]:
                logger.error(f"Invalid forwarder configuration: {validation['errors']}")
                return False
            
            # Test connectivity before setup
            connectivity_test = await self.test_forwarder_connectivity(forwarder)
            if connectivity_test["overall_status"] == "unhealthy":
                logger.warning(f"Forwarder {forwarder.name} has no healthy servers, but proceeding with setup")
            
            # Generate configuration for this specific forwarder
            success = await self.generate_forwarder_configuration([forwarder])
            
            if success:
                logger.info(f"Successfully set up conditional forwarding for {forwarder.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to set up conditional forwarding for {forwarder.name}: {e}")
            return False
    
    async def remove_conditional_forwarding(self, forwarder) -> bool:
        """Remove conditional forwarding for a specific forwarder"""
        logger = get_bind_logger()
        logger.info(f"Removing conditional forwarding for: {forwarder.name}")
        
        try:
            # Regenerate configuration without this forwarder
            if not self.db:
                logger.error("No database connection available")
                return False
            
            # Import here to avoid circular imports
            from ..models.dns import Forwarder
            
            # Get all other active forwarders (excluding the one being removed)
            other_forwarders = self.db.query(Forwarder).filter(
                Forwarder.is_active == True,
                Forwarder.id != forwarder.id
            ).all()
            
            # Regenerate configuration
            success = await self.generate_forwarder_configuration(other_forwarders)
            
            if success:
                logger.info(f"Successfully removed conditional forwarding for {forwarder.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove conditional forwarding for {forwarder.name}: {e}")
            return False
    
    async def add_forwarder_health_monitoring_integration(self, forwarder) -> bool:
        """Integrate forwarder with health monitoring system"""
        logger = get_bind_logger()
        logger.info(f"Integrating health monitoring for forwarder: {forwarder.name}")
        
        try:
            if not forwarder.health_check_enabled:
                logger.info(f"Health monitoring disabled for forwarder {forwarder.name}")
                return True
            
            # Test initial connectivity
            connectivity_test = await self.test_forwarder_connectivity(forwarder)
            
            # Log health status
            if connectivity_test["overall_status"] == "healthy":
                logger.info(f"Forwarder {forwarder.name} health check: {connectivity_test['successful_servers']}/{connectivity_test['total_servers']} servers healthy")
            else:
                logger.warning(f"Forwarder {forwarder.name} health check: {connectivity_test.get('error_message', 'No healthy servers')}")
            
            # Integration with health monitoring would happen here
            # This could include setting up periodic health checks, alerts, etc.
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to integrate health monitoring for {forwarder.name}: {e}")
            return False
    
    async def handle_forwarder_priority(self, forwarders: List) -> List:
        """Handle forwarder priority ordering for configuration generation"""
        logger = get_bind_logger()
        
        try:
            # Group forwarders by domain to handle priority within each domain
            domain_forwarders = {}
            
            for forwarder in forwarders:
                for domain in forwarder.domains:
                    if domain not in domain_forwarders:
                        domain_forwarders[domain] = []
                    domain_forwarders[domain].append(forwarder)
            
            # Sort servers within each forwarder by priority
            for forwarder in forwarders:
                if forwarder.servers:
                    forwarder.servers = sorted(
                        forwarder.servers, 
                        key=lambda x: x.get('priority', 1)
                    )
            
            # Log priority information
            for domain, domain_forwarder_list in domain_forwarders.items():
                if len(domain_forwarder_list) > 1:
                    logger.warning(f"Multiple forwarders configured for domain {domain}: {[f.name for f in domain_forwarder_list]}")
            
            return forwarders
            
        except Exception as e:
            logger.error(f"Failed to handle forwarder priority: {e}")
            return forwarders
    
    async def generate_statistics_configuration(self, statistics_config: Dict[str, Any] = None) -> bool:
        """Generate BIND9 statistics configuration file from settings"""
        logger = get_bind_logger()
        logger.info("Generating statistics configuration")
        
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Define statistics configuration file path
            stats_config_path = self.config_dir / "statistics.conf"
            
            # Backup existing configuration if it exists
            if stats_config_path.exists():
                await self._backup_configuration_file(stats_config_path)
            
            # Set default configuration if none provided
            if statistics_config is None:
                statistics_config = {
                    'enable_zone_statistics': True,
                    'enable_server_statistics': True,
                    'enable_mem_statistics': False,
                    'enable_network_stats': False,
                    'enable_monitoring_stats': False,
                    'local_stats_port': 8053,
                    'network_stats_port': 8053,
                    'monitoring_stats_port': 8053,
                    'trusted_networks': ['127.0.0.1', '192.168.0.0/16', '10.0.0.0/8', '172.16.0.0/12'],
                    'monitoring_ips': []
                }
            
            # Generate configuration content using template
            template = self.jinja_env.get_template("config/statistics.j2")
            content = template.render(
                generated_at=datetime.now(),
                config_version="1.0",
                **statistics_config
            )
            
            # Write configuration file
            stats_config_path.write_text(content, encoding='utf-8')
            
            # Set appropriate permissions
            stats_config_path.chmod(0o644)
            
            # Update main configuration to include statistics.conf
            await self._update_main_config_include_statistics(stats_config_path)
            
            logger.info(f"Successfully generated statistics configuration: {stats_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate statistics configuration: {e}")
            return False
    
    async def _update_main_config_include_statistics(self, stats_config_path: Path) -> bool:
        """Update main BIND configuration to include statistics.conf"""
        logger = get_bind_logger()
        
        try:
            # Path to main local configuration
            main_config_path = self.config_dir / "named.conf.local"
            
            if not main_config_path.exists():
                logger.warning(f"Main configuration file not found: {main_config_path}")
                return False
            
            # Backup existing configuration before modification
            await self._backup_configuration_file(main_config_path)
            
            # Read current configuration
            current_config = main_config_path.read_text(encoding='utf-8')
            
            # Check if statistics.conf is already included
            include_line = f'include "{stats_config_path}";'
            
            if include_line not in current_config:
                # Add include at the beginning of the file
                lines = current_config.split('\n')
                
                # Find a good place to insert (after initial comments)
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('//'):
                        insert_index = i
                        break
                
                # Insert the include line
                lines.insert(insert_index, include_line)
                lines.insert(insert_index + 1, '')  # Add blank line
                
                # Write updated configuration
                updated_config = '\n'.join(lines)
                main_config_path.write_text(updated_config, encoding='utf-8')
                
                logger.info(f"Added statistics.conf include to main configuration")
            else:
                logger.debug("Statistics.conf already included in main configuration")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update main configuration with statistics include: {e}")
            return False

    # Helper methods for zone file generation
    async def _generate_master_zone_file(self, zone: Zone, records: List[DNSRecord]) -> str:
        """Generate master zone file content using enhanced serialization"""
        logger = get_bind_logger()
        
        try:
            # Validate all records before generating zone file
            validation_errors = []
            for record in records:
                if record.is_active:
                    validation = self.validate_dns_record_for_zone(record)
                    if not validation['valid']:
                        validation_errors.extend([f"Record {record.name}: {error}" for error in validation['errors']])
            
            if validation_errors:
                logger.warning(f"Zone file generation for {zone.name} has validation errors: {validation_errors}")
            
            # Determine if this is a reverse zone
            is_reverse_zone = (
                zone.name.endswith('.in-addr.arpa') or 
                zone.name.endswith('.ip6.arpa')
            )
            
            # Use enhanced formatting method for better record serialization
            if hasattr(self, 'format_zone_file_with_records'):
                try:
                    content = self.format_zone_file_with_records(zone, records)
                    logger.debug(f"Generated zone file content for {zone.name} using enhanced serialization")
                    return content
                except Exception as e:
                    logger.warning(f"Enhanced serialization failed for {zone.name}, falling back to template: {e}")
            
            # Fallback to template-based generation
            if is_reverse_zone:
                template_name = "zones/reverse.j2"
            else:
                # Use the dedicated master zone template for better formatting and documentation
                template_name = "zones/master.j2"
            template = self.jinja_env.get_template(template_name)
            
            # Render the template with grouped records for better organization
            grouped_records = self.group_records_by_type(records)
            
            content = template.render(
                zone=zone,
                records=records,
                grouped_records=grouped_records,
                generated_at=datetime.now()
            )
            
            logger.debug(f"Generated zone file content for {zone.name} using template {template_name}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate master zone file for {zone.name}: {e}")
            raise
    
    async def _generate_slave_zone_file(self, zone: Zone) -> str:
        """Generate slave zone file content using the zones/slave.j2 template"""
        logger = get_bind_logger()
        
        try:
            template = self.jinja_env.get_template("zones/slave.j2")
            content = template.render(
                zone=zone,
                generated_at=datetime.now()
            )
            
            logger.debug(f"Generated slave zone file content for {zone.name} using zones/slave.j2 template")
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate slave zone file for {zone.name}: {e}")
            raise
    
    async def _update_slave_zone_config(self, zone: Zone) -> bool:
        """Update slave zone configuration (placeholder for now)"""
        logger = get_bind_logger()
        logger.info(f"Updating slave zone configuration for {zone.name}")
        
        # For slave zones, we mainly need to update the BIND9 configuration
        # The actual zone data is transferred from master servers
        # This would typically involve updating named.conf.local
        
        return True
    
    async def _ensure_zone_directories(self) -> bool:
        """Ensure all required directories exist"""
        logger = get_bind_logger()
        
        try:
            # Create zones directory
            self.zones_dir.mkdir(parents=True, exist_ok=True)
            
            # Create RPZ directory
            self.rpz_dir.mkdir(parents=True, exist_ok=True)
            
            # Set appropriate permissions (group writable for service user)
            self.zones_dir.chmod(0o775)
            self.rpz_dir.chmod(0o775)
            
            logger.debug("Zone directories ensured")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure zone directories: {e}")
            return False
    
    async def _backup_zone_file(self, zone_file_path: Path) -> bool:
        """Create a backup of existing zone file before modification using centralized backup service"""
        from .backup_service import BackupService, BackupType
        
        backup_service = BackupService()
        metadata = await backup_service.create_backup(
            zone_file_path, 
            BackupType.ZONE_FILE, 
            f"Zone file backup before update: {zone_file_path.name}"
        )
        return metadata is not None
    
    def _validate_zone_file_path(self, zone_name: str, zone_type: str) -> str:
        """Generate and validate zone file path"""
        # Generate standard zone file path
        if zone_type == "master":
            if zone_name.endswith('.in-addr.arpa') or zone_name.endswith('.ip6.arpa'):
                # Reverse zone
                filename = f"db.{zone_name}"
            else:
                # Forward zone
                filename = f"db.{zone_name}"
        else:
            # Slave zones
            filename = f"db.{zone_name}.slave"
        
        return str(self.zones_dir / filename)
    
    async def generate_soa_record(self, zone: Zone) -> str:
        """Generate SOA record for a zone with proper formatting"""
        return self.generate_soa_record_sync(zone)
    
    def generate_soa_record_sync(self, zone: Zone) -> str:
        """Generate SOA record for a zone with proper formatting (synchronous version)"""
        logger = get_bind_logger()
        
        try:
            # Format email address for DNS (replace @ with . and ensure trailing dot)
            email_formatted = zone.email.replace('@', '.')
            if not email_formatted.endswith('.'):
                email_formatted += '.'
            
            # Ensure zone name has trailing dot for primary nameserver
            primary_ns = zone.name
            if not primary_ns.endswith('.'):
                primary_ns += '.'
            
            # Generate SOA record with proper formatting and alignment
            soa_record = f"""@	IN	SOA	{primary_ns} {email_formatted} (
		{zone.serial}	; Serial number (YYYYMMDDNN)
		{zone.refresh}	; Refresh interval ({zone.refresh}s)
		{zone.retry}	; Retry interval ({zone.retry}s)
		{zone.expire}	; Expire time ({zone.expire}s)
		{zone.minimum}	; Minimum TTL ({zone.minimum}s)
		)"""
            
            logger.debug(f"Generated SOA record for zone {zone.name}")
            return soa_record
            
        except Exception as e:
            logger.error(f"Failed to generate SOA record for zone {zone.name}: {e}")
            raise ValueError(f"Invalid zone data for SOA record generation: {e}")
    
    def format_email_for_soa(self, email: str) -> str:
        """Format email address for SOA record (replace @ with . and ensure trailing dot)"""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")
        
        # Replace @ with . and ensure trailing dot
        formatted = email.replace('@', '.') + '.'
        return formatted
    
    def validate_soa_parameters(self, zone: Zone) -> Dict[str, Any]:
        """Validate SOA parameters for a zone"""
        errors = []
        warnings = []
        
        try:
            # Validate email format
            if not zone.email:
                errors.append("SOA email is required")
            elif '@' not in zone.email:
                errors.append("SOA email must contain @ symbol")
            
            # Validate timing parameters
            if zone.refresh < 300:
                warnings.append("Refresh interval is very low (<5 minutes)")
            elif zone.refresh > 86400:
                warnings.append("Refresh interval is very high (>24 hours)")
            
            if zone.retry < 300:
                warnings.append("Retry interval is very low (<5 minutes)")
            elif zone.retry > zone.refresh:
                warnings.append("Retry interval should be less than refresh interval")
            
            if zone.expire < zone.refresh:
                errors.append("Expire time must be greater than refresh interval")
            elif zone.expire < 604800:
                warnings.append("Expire time is less than 1 week")
            
            if zone.minimum < 60:
                warnings.append("Minimum TTL is very low (<1 minute)")
            elif zone.minimum > 86400:
                warnings.append("Minimum TTL is very high (>24 hours)")
            
            # Validate serial number
            if zone.serial is None:
                warnings.append("Serial number not set")
            elif zone.serial < 1:
                errors.append("Serial number must be positive")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"SOA validation error: {str(e)}"],
                "warnings": warnings
            }
    
    def serialize_rpz_rule_to_zone_format(self, rule) -> str:
        """Serialize an RPZ rule to zone file format"""
        logger = get_bind_logger()
        
        try:
            # Format the domain for RPZ
            domain = self._rpz_format_domain_filter(rule.domain)
            
            # Generate the appropriate RPZ record based on action
            if rule.action == 'block':
                # Block action - return NXDOMAIN
                return f"{domain}\tIN\tCNAME\t."
            
            elif rule.action == 'redirect':
                # Redirect action - redirect to specified target
                target = rule.redirect_target
                if target and not target.endswith('.'):
                    target += '.'
                return f"{domain}\tIN\tCNAME\t{target}"
            
            elif rule.action == 'passthru':
                # Passthrough action - explicitly allow (whitelist)
                return f"{domain}\tIN\tCNAME\trpz-passthru."
            
            else:
                logger.warning(f"Unknown RPZ action: {rule.action}")
                return f"; Unknown action for {domain}: {rule.action}"
                
        except Exception as e:
            logger.error(f"Failed to serialize RPZ rule {rule.id}: {e}")
            return f"; ERROR: Failed to serialize rule {rule.domain} ({rule.action})"
    
    def group_rpz_rules_by_action(self, rules: List) -> Dict[str, List]:
        """Group RPZ rules by action for organized zone file generation"""
        grouped = {
            'block': [],
            'redirect': [],
            'passthru': []
        }
        
        for rule in rules:
            if not rule.is_active:
                continue
                
            action = rule.action.lower()
            if action in grouped:
                grouped[action].append(rule)
            else:
                logger = get_bind_logger()
                logger.warning(f"Unknown RPZ action: {action}")
        
        return grouped
    
    def format_rpz_zone_file_with_rules(self, rpz_zone: str, rules: List, category_info: Dict = None) -> str:
        """Enhanced RPZ zone file formatting with comprehensive rule serialization"""
        logger = get_bind_logger()
        
        try:
            # Generate zone file header
            header = f"""; RPZ Zone file for {rpz_zone}
; Generated automatically by Hybrid DNS Server
; Category: {category_info.get('display_name', rpz_zone) if category_info else rpz_zone}
; Description: {category_info.get('description', 'Custom RPZ category') if category_info else 'Custom RPZ category'}
; Total Rules: {len(rules)}
; Active Rules: {len([r for r in rules if r.is_active])}
; Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

$TTL 300
$ORIGIN {rpz_zone}.rpz.

"""
            
            # Generate SOA record for RPZ zone
            serial = datetime.now().strftime('%Y%m%d%H')
            primary_ns = self._get_primary_ns()
            admin_email = self._get_admin_email()
            
            soa_record = f"""@\tIN\tSOA\t{primary_ns} {admin_email} (
\t\t{serial}\t; Serial number (YYYYMMDDHH)
\t\t3600\t\t; Refresh interval (1 hour)
\t\t1800\t\t; Retry interval (30 minutes)
\t\t604800\t\t; Expire time (1 week)
\t\t300\t\t; Minimum TTL (5 minutes)
\t\t)

; Name Server Record
@\tIN\tNS\t{primary_ns}

"""
            
            # Group and serialize rules
            grouped_rules = self.group_rpz_rules_by_action(rules)
            
            rule_sections = []
            
            # Add block rules
            if grouped_rules['block']:
                rule_sections.append(f"; ========================================")
                rule_sections.append(f"; BLOCK RULES ({len(grouped_rules['block'])} rules)")
                rule_sections.append(f"; These domains will return NXDOMAIN")
                rule_sections.append(f"; ========================================")
                
                # Sort rules by domain for better organization
                sorted_rules = sorted(grouped_rules['block'], key=lambda r: r.domain)
                for rule in sorted_rules:
                    if rule.description:
                        rule_sections.append(f"; {rule.description}")
                    rule_line = self.serialize_rpz_rule_to_zone_format(rule)
                    if rule.source:
                        rule_line += f" ; Source: {rule.source}"
                    rule_sections.append(rule_line)
                rule_sections.append("")
            
            # Add redirect rules
            if grouped_rules['redirect']:
                rule_sections.append(f"; ========================================")
                rule_sections.append(f"; REDIRECT RULES ({len(grouped_rules['redirect'])} rules)")
                rule_sections.append(f"; These domains will redirect to specified targets")
                rule_sections.append(f"; ========================================")
                
                sorted_rules = sorted(grouped_rules['redirect'], key=lambda r: r.domain)
                for rule in sorted_rules:
                    if rule.description:
                        rule_sections.append(f"; {rule.description}")
                    rule_line = self.serialize_rpz_rule_to_zone_format(rule)
                    if rule.source:
                        rule_line += f" ; Source: {rule.source}"
                    rule_sections.append(rule_line)
                rule_sections.append("")
            
            # Add passthrough rules
            if grouped_rules['passthru']:
                rule_sections.append(f"; ========================================")
                rule_sections.append(f"; PASSTHROUGH RULES ({len(grouped_rules['passthru'])} rules)")
                rule_sections.append(f"; These domains are explicitly allowed (whitelist)")
                rule_sections.append(f"; ========================================")
                
                sorted_rules = sorted(grouped_rules['passthru'], key=lambda r: r.domain)
                for rule in sorted_rules:
                    if rule.description:
                        rule_sections.append(f"; {rule.description}")
                    rule_line = self.serialize_rpz_rule_to_zone_format(rule)
                    if rule.source:
                        rule_line += f" ; Source: {rule.source}"
                    rule_sections.append(rule_line)
                rule_sections.append("")
            
            # Add statistics summary
            active_rules = [r for r in rules if r.is_active]
            rule_sections.append(f"; Statistics Summary:")
            rule_sections.append(f"; Total Rules: {len(rules)}")
            rule_sections.append(f"; Active Rules: {len(active_rules)}")
            rule_sections.append(f"; Block Rules: {len(grouped_rules['block'])}")
            rule_sections.append(f"; Redirect Rules: {len(grouped_rules['redirect'])}")
            rule_sections.append(f"; Passthrough Rules: {len(grouped_rules['passthru'])}")
            rule_sections.append("")
            rule_sections.append(f"; End of RPZ zone file for {rpz_zone}")
            
            # Combine all sections
            content = header + soa_record
            if rule_sections:
                content += "\n".join(rule_sections)
            else:
                content += "; No active RPZ rules defined for this category\n"
            
            logger.debug(f"Enhanced RPZ zone file formatting completed for {rpz_zone}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to format RPZ zone file with rules for {rpz_zone}: {e}")
            raise
    
    async def create_category_based_rpz_zones(self) -> bool:
        """Create category-based RPZ zones from database rules"""
        logger = get_bind_logger()
        logger.info("Creating category-based RPZ zones")
        
        try:
            if not self.db:
                logger.error("No database connection available for category-based RPZ zone creation")
                return False
            
            # Import here to avoid circular imports
            from ..models.security import RPZRule
            from sqlalchemy import select, distinct
            
            # Check if this is an async session
            is_async = hasattr(self.db, 'execute')
            
            if is_async:
                # Get all distinct RPZ zones (categories) from active rules using async syntax
                categories_query = select(distinct(RPZRule.rpz_zone)).filter(
                    RPZRule.is_active == True
                )
                categories_result = await self.db.execute(categories_query)
                categories = categories_result.scalars().all()
            else:
                # Use sync syntax for regular sessions
                categories = self.db.query(RPZRule.rpz_zone).filter(
                    RPZRule.is_active == True
                ).distinct().all()
                categories = [cat[0] for cat in categories]
            
            success_count = 0
            total_categories = len(categories)
            
            for category in categories:
                try:
                    if is_async:
                        # Get all rules for this category using async syntax
                        rules_query = select(RPZRule).filter(
                            RPZRule.rpz_zone == category,
                            RPZRule.is_active == True
                        )
                        rules_result = await self.db.execute(rules_query)
                        category_rules = rules_result.scalars().all()
                    else:
                        # Use sync syntax for regular sessions
                        category_rules = self.db.query(RPZRule).filter(
                            RPZRule.rpz_zone == category,
                            RPZRule.is_active == True
                        ).all()
                    
                    # Generate RPZ zone file for this category
                    success = await self.generate_rpz_zone_file(category, category_rules)
                    
                    if success:
                        success_count += 1
                        logger.info(f"Successfully created RPZ zone for category: {category} ({len(category_rules)} rules)")
                    else:
                        logger.error(f"Failed to create RPZ zone for category: {category}")
                        
                except Exception as e:
                    logger.error(f"Failed to process category {category}: {e}")
            
            logger.info(f"Created {success_count}/{total_categories} category-based RPZ zones")
            return success_count == total_categories
            
        except Exception as e:
            logger.error(f"Failed to create category-based RPZ zones: {e}")
            return False
    
    async def update_all_rpz_zones(self) -> bool:
        """Update all RPZ zones from database"""
        logger = get_bind_logger()
        logger.info("Updating all RPZ zones")
        
        try:
            # Create/update all category-based zones
            success = await self.create_category_based_rpz_zones()
            
            if success:
                # Reload BIND9 configuration to apply changes
                reload_success = await self.reload_configuration()
                if reload_success:
                    logger.info("Successfully updated all RPZ zones and reloaded BIND9")
                else:
                    logger.warning("RPZ zones updated but BIND9 reload failed")
                return reload_success
            else:
                logger.error("Failed to update some RPZ zones")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update all RPZ zones: {e}")
            return False
    
    def get_rpz_policy_configuration(self) -> Dict[str, Any]:
        """Get RPZ policy configuration for BIND9"""
        logger = get_bind_logger()
        
        try:
            # Define standard RPZ categories and their policies
            rpz_policies = {
                'malware': {
                    'zone_name': 'malware.rpz',
                    'policy': 'NXDOMAIN',
                    'priority': 1,
                    'description': 'Malware and malicious domains'
                },
                'phishing': {
                    'zone_name': 'phishing.rpz',
                    'policy': 'NXDOMAIN', 
                    'priority': 2,
                    'description': 'Phishing and fraudulent websites'
                },
                'adult': {
                    'zone_name': 'adult.rpz',
                    'policy': 'NXDOMAIN',
                    'priority': 3,
                    'description': 'Adult content filtering'
                },
                'social-media': {
                    'zone_name': 'social-media.rpz',
                    'policy': 'NXDOMAIN',
                    'priority': 4,
                    'description': 'Social media platforms'
                },
                'gambling': {
                    'zone_name': 'gambling.rpz',
                    'policy': 'NXDOMAIN',
                    'priority': 5,
                    'description': 'Gambling and betting sites'
                },
                'custom': {
                    'zone_name': 'custom.rpz',
                    'policy': 'GIVEN',
                    'priority': 10,
                    'description': 'Custom rules with mixed actions'
                }
            }
            
            # Add dynamic categories from database if available
            if self.db:
                try:
                    from ..models.security import RPZRule
                    
                    # Get all distinct categories from database
                    db_categories = self.db.query(RPZRule.rpz_zone).distinct().all()
                    
                    for (category,) in db_categories:
                        if category not in rpz_policies:
                            rpz_policies[category] = {
                                'zone_name': f'{category}.rpz',
                                'policy': 'GIVEN',
                                'priority': 20,
                                'description': f'Custom category: {category}'
                            }
                            
                except Exception as e:
                    logger.warning(f"Failed to get dynamic RPZ categories from database: {e}")
            
            return {
                'enabled': True,
                'categories': rpz_policies,
                'global_policy': 'GIVEN',
                'break_dnssec': True,
                'max_policy_ttl': 300,
                'min_update_interval': 60
            }
            
        except Exception as e:
            logger.error(f"Failed to get RPZ policy configuration: {e}")
            return {
                'enabled': False,
                'categories': {},
                'error': str(e)
            }
    
    async def generate_rpz_policy_configuration(self) -> bool:
        """Generate RPZ policy configuration for BIND9 using template"""
        logger = get_bind_logger()
        logger.info("Generating RPZ policy configuration")
        
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Define RPZ policy configuration file path
            rpz_config_path = self.config_dir / "rpz-policy.conf"
            
            # Backup existing configuration if it exists
            if rpz_config_path.exists():
                await self._backup_configuration_file(rpz_config_path)
            
            # Get RPZ policy configuration
            policy_config = self.get_rpz_policy_configuration()
            
            # Generate configuration content using template
            template = self.jinja_env.get_template("rpz_policy.j2")
            content = template.render(
                enabled=policy_config.get('enabled', True),
                categories=policy_config.get('categories', {}),
                break_dnssec=policy_config.get('break_dnssec', True),
                max_policy_ttl=policy_config.get('max_policy_ttl', 300),
                qname_wait_recurse=policy_config.get('qname_wait_recurse', False),
                min_update_interval=policy_config.get('min_update_interval', 60),
                generated_at=datetime.now()
            )
            
            # Write configuration file
            rpz_config_path.write_text(content, encoding='utf-8')
            
            # Set appropriate permissions
            rpz_config_path.chmod(0o644)
            
            # Update main configuration to include RPZ policy
            await self._update_main_config_rpz_include(rpz_config_path)
            
            logger.info(f"Successfully generated RPZ policy configuration: {rpz_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate RPZ policy configuration: {e}")
            return False
    
    async def _update_main_config_rpz_include(self, rpz_config_path: Path) -> bool:
        """Update main BIND configuration to include RPZ policy configuration"""
        logger = get_bind_logger()
        
        try:
            # Path to main options configuration
            main_config_path = self.config_dir / "named.conf.options"
            
            if not main_config_path.exists():
                logger.warning(f"Main options configuration file not found: {main_config_path}")
                return False
            
            # Backup existing configuration before modification
            await self._backup_configuration_file(main_config_path)
            
            # Read current configuration
            current_config = main_config_path.read_text(encoding='utf-8')
            
            # Check if RPZ policy is already included
            include_line = f'include "{rpz_config_path}";'
            
            if include_line not in current_config:
                # Find the options block and add RPZ configuration
                lines = current_config.split('\n')
                
                # Look for the options block
                in_options_block = False
                insert_index = -1
                
                for i, line in enumerate(lines):
                    if 'options' in line and '{' in line:
                        in_options_block = True
                    elif in_options_block and '};' in line:
                        insert_index = i
                        break
                
                if insert_index > 0:
                    # Insert the include line before the closing brace
                    lines.insert(insert_index, f'\t{include_line}')
                    lines.insert(insert_index + 1, '')  # Add blank line
                    
                    # Write updated configuration
                    updated_config = '\n'.join(lines)
                    main_config_path.write_text(updated_config, encoding='utf-8')
                    
                    logger.info(f"Added RPZ policy include to main configuration")
                else:
                    logger.warning("Could not find options block in main configuration")
                    return False
            else:
                logger.debug("RPZ policy already included in main configuration")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update main configuration RPZ include: {e}")
            return False
    
    async def enable_rpz_policy(self) -> bool:
        """Enable RPZ policy in BIND9 configuration"""
        logger = get_bind_logger()
        logger.info("Enabling RPZ policy")
        
        try:
            # Generate RPZ policy configuration with enabled=True
            success = await self.generate_rpz_policy_configuration()
            
            if success:
                # Reload BIND9 configuration to apply changes
                reload_success = await self.reload_configuration()
                if reload_success:
                    logger.info("Successfully enabled RPZ policy and reloaded BIND9")
                else:
                    logger.warning("RPZ policy enabled but BIND9 reload failed")
                return reload_success
            else:
                logger.error("Failed to generate RPZ policy configuration")
                return False
                
        except Exception as e:
            logger.error(f"Failed to enable RPZ policy: {e}")
            return False
    
    async def disable_rpz_policy(self) -> bool:
        """Disable RPZ policy in BIND9 configuration"""
        logger = get_bind_logger()
        logger.info("Disabling RPZ policy")
        
        try:
            # Generate RPZ policy configuration with enabled=False
            policy_config = self.get_rpz_policy_configuration()
            policy_config['enabled'] = False
            
            # Generate disabled configuration
            success = await self._generate_rpz_policy_configuration_with_settings(policy_config)
            
            if success:
                # Reload BIND9 configuration to apply changes
                reload_success = await self.reload_configuration()
                if reload_success:
                    logger.info("Successfully disabled RPZ policy and reloaded BIND9")
                else:
                    logger.warning("RPZ policy disabled but BIND9 reload failed")
                return reload_success
            else:
                logger.error("Failed to generate disabled RPZ policy configuration")
                return False
                
        except Exception as e:
            logger.error(f"Failed to disable RPZ policy: {e}")
            return False
    
    async def update_rpz_policy_settings(self, settings: Dict[str, Any]) -> bool:
        """Update RPZ policy settings dynamically"""
        logger = get_bind_logger()
        logger.info(f"Updating RPZ policy settings: {settings}")
        
        try:
            # Get current policy configuration
            current_config = self.get_rpz_policy_configuration()
            
            # Update settings
            for key, value in settings.items():
                if key in ['enabled', 'break_dnssec', 'max_policy_ttl', 'qname_wait_recurse', 'min_update_interval']:
                    current_config[key] = value
                    logger.debug(f"Updated RPZ policy setting: {key} = {value}")
                else:
                    logger.warning(f"Unknown RPZ policy setting: {key}")
            
            # Generate updated configuration
            success = await self._generate_rpz_policy_configuration_with_settings(current_config)
            
            if success:
                # Reload BIND9 configuration to apply changes
                reload_success = await self.reload_configuration()
                if reload_success:
                    logger.info("Successfully updated RPZ policy settings and reloaded BIND9")
                else:
                    logger.warning("RPZ policy settings updated but BIND9 reload failed")
                return reload_success
            else:
                logger.error("Failed to generate updated RPZ policy configuration")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update RPZ policy settings: {e}")
            return False
    
    async def _generate_rpz_policy_configuration_with_settings(self, policy_config: Dict[str, Any]) -> bool:
        """Generate RPZ policy configuration with specific settings"""
        logger = get_bind_logger()
        
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Define RPZ policy configuration file path
            rpz_config_path = self.config_dir / "rpz-policy.conf"
            
            # Backup existing configuration if it exists
            if rpz_config_path.exists():
                await self._backup_configuration_file(rpz_config_path)
            
            # Generate configuration content using template
            template = self.jinja_env.get_template("rpz_policy.j2")
            content = template.render(
                enabled=policy_config.get('enabled', True),
                categories=policy_config.get('categories', {}),
                break_dnssec=policy_config.get('break_dnssec', True),
                max_policy_ttl=policy_config.get('max_policy_ttl', 300),
                qname_wait_recurse=policy_config.get('qname_wait_recurse', False),
                min_update_interval=policy_config.get('min_update_interval', 60),
                generated_at=datetime.now()
            )
            
            # Write configuration file
            rpz_config_path.write_text(content, encoding='utf-8')
            
            # Set appropriate permissions
            rpz_config_path.chmod(0o644)
            
            # Update main configuration to include RPZ policy
            await self._update_main_config_rpz_include(rpz_config_path)
            
            logger.info(f"Successfully generated RPZ policy configuration with custom settings: {rpz_config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate RPZ policy configuration with settings: {e}")
            return False
    
    async def get_rpz_policy_status(self) -> Dict[str, Any]:
        """Get current RPZ policy status and configuration"""
        logger = get_bind_logger()
        
        try:
            # Check if RPZ policy configuration file exists
            rpz_config_path = self.config_dir / "rpz-policy.conf"
            config_exists = rpz_config_path.exists()
            
            # Get current policy configuration
            policy_config = self.get_rpz_policy_configuration()
            
            # Check if RPZ is included in main configuration
            main_config_path = self.config_dir / "named.conf.options"
            included_in_main = False
            
            if main_config_path.exists():
                main_config = main_config_path.read_text(encoding='utf-8')
                included_in_main = str(rpz_config_path) in main_config
            
            # Get RPZ zone statistics
            rpz_stats = await self._get_rpz_zone_statistics()
            
            return {
                "enabled": policy_config.get('enabled', False),
                "config_file_exists": config_exists,
                "included_in_main_config": included_in_main,
                "config_file_path": str(rpz_config_path),
                "categories": policy_config.get('categories', {}),
                "settings": {
                    "break_dnssec": policy_config.get('break_dnssec', True),
                    "max_policy_ttl": policy_config.get('max_policy_ttl', 300),
                    "qname_wait_recurse": policy_config.get('qname_wait_recurse', False),
                    "min_update_interval": policy_config.get('min_update_interval', 60)
                },
                "statistics": rpz_stats,
                "last_updated": datetime.fromtimestamp(rpz_config_path.stat().st_mtime) if config_exists else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get RPZ policy status: {e}")
            return {
                "enabled": False,
                "error": str(e),
                "config_file_exists": False,
                "included_in_main_config": False
            }
    
    async def _get_rpz_zone_statistics(self) -> Dict[str, Any]:
        """Get statistics for all RPZ zones"""
        try:
            stats = {
                "total_zones": 0,
                "total_rules": 0,
                "zones": {}
            }
            
            if not self.db:
                return stats
            
            # Import here to avoid circular imports
            from ..models.security import RPZRule
            
            # Get all distinct RPZ zones
            categories = self.db.query(RPZRule.rpz_zone).distinct().all()
            stats["total_zones"] = len(categories)
            
            for (category,) in categories:
                # Get rule count for this category
                rule_count = self.db.query(RPZRule).filter(
                    RPZRule.rpz_zone == category,
                    RPZRule.is_active == True
                ).count()
                
                stats["zones"][category] = {
                    "active_rules": rule_count,
                    "zone_file_exists": (self.rpz_dir / f"db.rpz.{category}").exists()
                }
                
                stats["total_rules"] += rule_count
            
            return stats
            
        except Exception as e:
            logger = get_bind_logger()
            logger.error(f"Failed to get RPZ zone statistics: {e}")
            return {"error": str(e)}
    
    async def validate_rpz_policy_configuration(self) -> Dict[str, Any]:
        """Validate the current RPZ policy configuration"""
        logger = get_bind_logger()
        logger.info("Validating RPZ policy configuration")
        
        errors = []
        warnings = []
        
        try:
            # Check if RPZ policy configuration file exists
            rpz_config_path = self.config_dir / "rpz-policy.conf"
            
            if not rpz_config_path.exists():
                errors.append(f"RPZ policy configuration file not found: {rpz_config_path}")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Validate file permissions
            if not rpz_config_path.stat().st_mode & 0o044:
                warnings.append("RPZ policy configuration file may not be readable by BIND9")
            
            # Read and validate configuration content
            content = rpz_config_path.read_text(encoding='utf-8')
            
            # Check for required RPZ policy elements
            if "response-policy" not in content:
                errors.append("RPZ policy configuration missing response-policy directive")
            
            # Validate that RPZ zones exist
            policy_config = self.get_rpz_policy_configuration()
            for category, config in policy_config.get('categories', {}).items():
                zone_file_path = self.rpz_dir / f"db.rpz.{category}"
                if not zone_file_path.exists():
                    warnings.append(f"RPZ zone file not found for category: {category}")
            
            # Check if included in main configuration
            main_config_path = self.config_dir / "named.conf.options"
            if main_config_path.exists():
                main_config = main_config_path.read_text(encoding='utf-8')
                if str(rpz_config_path) not in main_config:
                    errors.append("RPZ policy configuration not included in main BIND configuration")
            else:
                warnings.append("Main BIND configuration file not found")
            
            # Validate BIND9 configuration syntax (avoid circular dependency)
            config_syntax_result = await self._validate_main_configuration_syntax()
            config_valid = config_syntax_result["valid"]
            if not config_valid:
                errors.append("BIND9 configuration syntax validation failed - RPZ policy may have syntax errors")
                errors.extend(config_syntax_result["errors"])
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "config_file_path": str(rpz_config_path),
                "bind_config_valid": config_valid
            }
            
        except Exception as e:
            logger.error(f"Failed to validate RPZ policy configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    def validate_soa_parameters(self, zone: Zone) -> Dict[str, Any]:
        """Validate SOA record parameters"""
        errors = []
        warnings = []
        
        # Validate email (DNS format uses dots instead of @)
        if not zone.email or '.' not in zone.email:
            errors.append("Valid email address is required for SOA record")
        
        # Validate serial number
        if not zone.serial or zone.serial <= 0:
            errors.append("Valid serial number is required for SOA record")
        elif zone.serial > 4294967295:  # 2^32 - 1 (max 32-bit unsigned integer)
            errors.append("Serial number exceeds maximum value (4294967295)")
        
        # Validate timing parameters
        if zone.refresh < 300:
            warnings.append("Refresh interval is very low (< 5 minutes)")
        elif zone.refresh > 86400:
            warnings.append("Refresh interval is very high (> 24 hours)")
        
        if zone.retry < 300:
            warnings.append("Retry interval is very low (< 5 minutes)")
        elif zone.retry > zone.refresh:
            warnings.append("Retry interval should be less than refresh interval")
        
        if zone.expire < 86400:
            errors.append("Expire time must be at least 24 hours (86400 seconds)")
        elif zone.expire < zone.refresh * 2:
            warnings.append("Expire time should be at least twice the refresh interval")
        
        if zone.minimum < 300:
            warnings.append("Minimum TTL is very low (< 5 minutes)")
        elif zone.minimum > 86400:
            warnings.append("Minimum TTL is very high (> 24 hours)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _backup_configuration_file(self, config_file_path: Path) -> bool:
        """Create a backup of existing configuration file using centralized backup service"""
        from .backup_service import BackupService, BackupType
        
        backup_service = BackupService()
        metadata = await backup_service.create_backup(
            config_file_path, 
            BackupType.CONFIGURATION, 
            f"Configuration backup before update: {config_file_path.name}"
        )
        return metadata is not None
    
    async def handle_forwarder_priority(self, forwarders: List) -> List:
        """Handle forwarder priority ordering"""
        try:
            # Sort forwarders by priority (lower number = higher priority)
            sorted_forwarders = []
            for forwarder in forwarders:
                # Sort servers within each forwarder by priority
                if hasattr(forwarder, 'servers') and forwarder.servers:
                    sorted_servers = sorted(forwarder.servers, key=lambda s: s.get('priority', 1))
                    forwarder.servers = sorted_servers
                sorted_forwarders.append(forwarder)
            
            return sorted_forwarders
            
        except Exception as e:
            logger = get_bind_logger()
            logger.error(f"Failed to handle forwarder priority: {e}")
            return forwarders
    
    async def _update_main_config_include(self, config_file_path: Path) -> bool:
        """Update main BIND configuration to include the generated config file"""
        logger = get_bind_logger()
        
        try:
            # This is a placeholder for updating the main named.conf file
            # In a real implementation, you would parse and update the main config
            logger.info(f"Configuration file ready for inclusion: {config_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update main config include: {e}")
            return False
    
    def format_email_for_soa(self, email: str) -> str:
        """Format email address for SOA record (replace @ with .)"""
        if not email:
            raise ValueError("Email is required")
        
        if '@' not in email:
            raise ValueError("Invalid email format")
        
        # Replace @ with . and ensure trailing dot
        formatted = email.replace('@', '.') + '.'
        return formatted
    
    def _format_email_filter(self, email: str) -> str:
        """Jinja2 filter to format email for SOA record"""
        try:
            return self.format_email_for_soa(email)
        except ValueError:
            return "invalid.email."
    
    def _ensure_trailing_dot_filter(self, domain: str) -> str:
        """Jinja2 filter to ensure domain has trailing dot"""
        if not domain:
            return "."
        return domain if domain.endswith('.') else f"{domain}."
    
    def _rpz_format_domain_filter(self, domain: str) -> str:
        """Jinja2 filter to format domain for RPZ zone file"""
        if not domain:
            return ""
        
        # Remove protocol prefixes if present
        domain = domain.replace('http://', '').replace('https://', '')
        
        # Remove trailing slash if present
        domain = domain.rstrip('/')
        
        # Handle wildcard domains
        if domain.startswith('*.'):
            # For wildcard domains, use the RPZ wildcard format
            return f"*.{domain[2:]}"
        
        # For regular domains, just return as-is (RPZ will handle the formatting)
        return domain
    
    def _format_ttl_filter(self, ttl: Optional[int]) -> str:
        """Jinja2 filter to format TTL values with human-readable comments"""
        if ttl is None:
            return ""
        
        if ttl < 60:
            return f"{ttl}"
        elif ttl < 3600:
            minutes = ttl // 60
            return f"{ttl}  ; {minutes}m"
        elif ttl < 86400:
            hours = ttl // 3600
            return f"{ttl}  ; {hours}h"
        else:
            days = ttl // 86400
            return f"{ttl}  ; {days}d"
    
    def _format_serial_filter(self, serial: Optional[int]) -> str:
        """Jinja2 filter to format serial numbers with date information"""
        if serial is None:
            return str(self._generate_serial_number())
        
        serial_str = str(serial)
        if len(serial_str) == 10:
            # YYYYMMDDNN format
            year = serial_str[:4]
            month = serial_str[4:6]
            day = serial_str[6:8]
            revision = serial_str[8:10]
            return f"{serial}  ; {year}-{month}-{day} rev {revision}"
        else:
            return str(serial)
    
    def _format_duration_filter(self, seconds: int) -> str:
        """Jinja2 filter to format duration in seconds to human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds == 0:
                return f"{minutes}m"
            else:
                return f"{minutes}m{remaining_seconds}s"
        elif seconds < 86400:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h{remaining_minutes}m"
        else:
            days = seconds // 86400
            remaining_hours = (seconds % 86400) // 3600
            if remaining_hours == 0:
                return f"{days}d"
            else:
                return f"{days}d{remaining_hours}h"
    
    def _validate_ip_filter(self, ip_address: str) -> bool:
        """Jinja2 filter to validate IP addresses"""
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False
    
    def _reverse_ip_filter(self, ip_address: str) -> str:
        """Jinja2 filter to create reverse DNS format for IP addresses"""
        try:
            ip = ipaddress.ip_address(ip_address)
            if isinstance(ip, ipaddress.IPv4Address):
                # For IPv4: 192.168.1.10 -> 10.1.168.192.in-addr.arpa
                octets = str(ip).split('.')
                return '.'.join(reversed(octets)) + '.in-addr.arpa'
            elif isinstance(ip, ipaddress.IPv6Address):
                # For IPv6: create ip6.arpa format
                expanded = ip.exploded.replace(':', '')
                reversed_chars = '.'.join(reversed(expanded))
                return f"{reversed_chars}.ip6.arpa"
        except ValueError:
            return ip_address  # Return original if invalid
    
    def _format_mx_priority_filter(self, priority: Optional[int]) -> str:
        """Jinja2 filter to format MX record priority with validation"""
        if priority is None:
            return "10"  # Default MX priority
        
        if 0 <= priority <= 65535:
            return str(priority)
        else:
            return "10"  # Fallback to default if invalid
    
    def _format_srv_record_filter(self, record) -> str:
        """Jinja2 filter to format SRV record components"""
        priority = record.priority if record.priority is not None else 0
        weight = record.weight if record.weight is not None else 0
        port = record.port if record.port is not None else 0
        target = self._ensure_trailing_dot_filter(record.value)
        
        return f"{priority} {weight} {port} {target}"
    
    def _escape_txt_record_filter(self, text: str) -> str:
        """Jinja2 filter to properly escape TXT record content"""
        if not text:
            return '""'
        
        # Escape quotes and backslashes
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')
        
        # Handle long TXT records (split at 255 characters)
        if len(escaped) <= 255:
            return f'"{escaped}"'
        else:
            # Split into multiple quoted strings
            chunks = []
            for i in range(0, len(escaped), 255):
                chunk = escaped[i:i+255]
                chunks.append(f'"{chunk}"')
            return ' '.join(chunks)
    
    def _normalize_domain_filter(self, domain: str) -> str:
        """Jinja2 filter to normalize domain names"""
        if not domain:
            return ""
        
        # Convert to lowercase
        domain = domain.lower()
        
        # Remove protocol prefixes
        domain = domain.replace('http://', '').replace('https://', '')
        
        # Remove trailing slash
        domain = domain.rstrip('/')
        
        # Handle @ symbol (represents zone root)
        if domain == '@':
            return '@'
        
        return domain
    
    def _is_wildcard_filter(self, domain: str) -> bool:
        """Jinja2 filter to check if domain is a wildcard"""
        return domain.startswith('*.')
    
    def _format_comment_filter(self, text: str, max_length: int = 50) -> str:
        """Jinja2 filter to format comments in zone files"""
        if not text:
            return ""
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        
        # Ensure it starts with semicolon and space
        if not text.startswith(';'):
            text = f"; {text}"
        
        return text
    
    def _generate_serial_number(self) -> int:
        """Generate a serial number in YYYYMMDDNN format"""
        now = datetime.now()
        date_part = now.strftime('%Y%m%d')
        
        # For simplicity, use hour as revision number (00-23)
        revision = now.strftime('%H')
        
        return int(f"{date_part}{revision:0>2}")
    
    def _get_default_ttl(self) -> int:
        """Get default TTL value"""
        return 3600  # 1 hour default
    
    def _format_timestamp(self, dt: Optional[datetime] = None, format_str: str = '%Y-%m-%d %H:%M:%S UTC') -> str:
        """Format timestamp for zone file comments"""
        if dt is None:
            dt = datetime.utcnow()
        return dt.strftime(format_str)
    
    def _get_zone_type_description(self, zone_type: str) -> str:
        """Get human-readable description of zone type"""
        descriptions = {
            'master': 'Master (Authoritative)',
            'slave': 'Slave (Secondary)',
            'forward': 'Forward Only',
            'hint': 'Root Hints',
            'stub': 'Stub Zone'
        }
        return descriptions.get(zone_type.lower(), zone_type)
    
    def _get_record_type_description(self, record_type: str) -> str:
        """Get human-readable description of DNS record type"""
        descriptions = {
            'A': 'IPv4 Address Record',
            'AAAA': 'IPv6 Address Record',
            'CNAME': 'Canonical Name Record',
            'MX': 'Mail Exchange Record',
            'NS': 'Name Server Record',
            'PTR': 'Pointer Record',
            'SOA': 'Start of Authority Record',
            'SRV': 'Service Record',
            'TXT': 'Text Record',
            'CAA': 'Certification Authority Authorization',
            'DNAME': 'Delegation Name Record',
            'NAPTR': 'Naming Authority Pointer Record',
            'SSHFP': 'SSH Fingerprint Record',
            'TLSA': 'Transport Layer Security Authentication'
        }
        return descriptions.get(record_type.upper(), f'{record_type} Record')
    
    def _validate_zone_configuration(self, zone: Zone) -> Dict:
        """Validate zone configuration parameters"""
        errors = []
        warnings = []
        
        # Validate zone name
        if not zone.name:
            errors.append("Zone name is required")
        elif not self._is_valid_domain_name(zone.name):
            errors.append(f"Invalid zone name format: {zone.name}")
        
        # Validate zone type
        if zone.zone_type not in ["master", "slave", "forward"]:
            errors.append(f"Invalid zone type: {zone.zone_type}")
        
        # Validate SOA parameters for master zones
        if zone.zone_type == "master":
            soa_validation = self.validate_soa_parameters(zone)
            errors.extend(soa_validation["errors"])
            warnings.extend(soa_validation["warnings"])
        
        # Type-specific validations
        if zone.zone_type == "slave":
            if not zone.master_servers:
                errors.append("Slave zone must have master servers configured")
            else:
                for server in zone.master_servers:
                    if not self._is_valid_ip_address(server):
                        errors.append(f"Invalid master server IP address: {server}")
        
        if zone.zone_type == "forward":
            if not zone.forwarders:
                errors.append("Forward zone must have forwarders configured")
            else:
                for forwarder in zone.forwarders:
                    if not self._is_valid_ip_address(forwarder):
                        errors.append(f"Invalid forwarder IP address: {forwarder}")
        
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
    
    async def _validate_zone_file_syntax(self, zone: Zone, zone_file_path: Path) -> Dict:
        """Validate zone file syntax using named-checkzone"""
        errors = []
        warnings = []
        
        try:
            # Use named-checkzone to validate the zone file syntax
            result = await self._run_command([
                "/usr/sbin/named-checkzone", 
                "-q",  # Quiet mode - only show errors
                zone.name, 
                str(zone_file_path)
            ])
            
            if result["returncode"] != 0:
                # Parse named-checkzone output for specific errors
                stderr_lines = result["stderr"].strip().split('\n')
                for line in stderr_lines:
                    if line.strip():
                        errors.append(f"Zone file syntax error: {line.strip()}")
            else:
                # Check for warnings in stdout
                if result["stdout"].strip():
                    stdout_lines = result["stdout"].strip().split('\n')
                    for line in stdout_lines:
                        if "warning" in line.lower():
                            warnings.append(f"Zone file warning: {line.strip()}")
            
        except Exception as e:
            errors.append(f"Failed to validate zone file syntax: {str(e)}")
        
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
    
    async def _validate_zone_file_content(self, zone: Zone, zone_file_path: Path) -> Dict:
        """Validate zone file content for common issues"""
        errors = []
        warnings = []
        
        try:
            content = zone_file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Check for required SOA record
            has_soa = False
            soa_line_number = 0
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Check for SOA record
                if 'SOA' in line.upper():
                    has_soa = True
                    soa_line_number = i
                    break
            
            if not has_soa and zone.zone_type == "master":
                errors.append("Master zone file must contain an SOA record")
            
            # Validate $ORIGIN directive
            has_origin = False
            for line in lines:
                if line.strip().startswith('$ORIGIN'):
                    has_origin = True
                    origin_value = line.strip().split()[1] if len(line.strip().split()) > 1 else ""
                    if not origin_value.endswith('.'):
                        warnings.append("$ORIGIN directive should end with a dot")
                    break
            
            if not has_origin and zone.zone_type == "master":
                warnings.append("Zone file should include $ORIGIN directive")
            
            # Check for $TTL directive
            has_ttl = False
            for line in lines:
                if line.strip().startswith('$TTL'):
                    has_ttl = True
                    break
            
            if not has_ttl and zone.zone_type == "master":
                warnings.append("Zone file should include $TTL directive")
            
            # Validate record format consistency
            record_errors = self._validate_zone_file_records(lines)
            errors.extend(record_errors)
            
        except Exception as e:
            errors.append(f"Failed to read zone file content: {str(e)}")
        
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
    
    async def _validate_zone_records(self, zone: Zone) -> Dict:
        """Validate zone records from database"""
        errors = []
        warnings = []
        
        try:
            # Get all active records for the zone
            records = self.db.query(DNSRecord).filter(
                DNSRecord.zone_id == zone.id,
                DNSRecord.is_active == True
            ).all()
            
            # Check for required NS records
            ns_records = [r for r in records if r.record_type == 'NS']
            if not ns_records and zone.zone_type == "master":
                warnings.append("Master zone should have at least one NS record")
            
            # Validate each record
            for record in records:
                record_validation = self.validate_dns_record_for_zone(record)
                if not record_validation["valid"]:
                    for error in record_validation["errors"]:
                        errors.append(f"Record '{record.name}' ({record.record_type}): {error}")
                
                for warning in record_validation.get("warnings", []):
                    warnings.append(f"Record '{record.name}' ({record.record_type}): {warning}")
            
            # Check for conflicting records
            conflict_errors = self._check_record_conflicts(records)
            errors.extend(conflict_errors)
            
        except Exception as e:
            errors.append(f"Failed to validate zone records: {str(e)}")
        
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
    
    def _validate_zone_file_records(self, lines: List[str]) -> List[str]:
        """Validate individual records in zone file"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('$'):
                continue
            
            # Skip SOA record (multi-line)
            if 'SOA' in line.upper():
                continue
            
            # Parse record line
            parts = line.split()
            if len(parts) < 4:
                continue  # Skip incomplete lines
            
            try:
                # Basic record format validation
                record_type = None
                for part in parts:
                    if part.upper() in ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS']:
                        record_type = part.upper()
                        break
                
                if record_type:
                    # Type-specific validation
                    if record_type == 'A':
                        # Find the IP address (last part usually)
                        ip_part = parts[-1]
                        if not self._is_valid_ipv4_address(ip_part):
                            errors.append(f"Line {i}: Invalid IPv4 address '{ip_part}' in A record")
                    
                    elif record_type == 'AAAA':
                        ip_part = parts[-1]
                        if not self._is_valid_ipv6_address(ip_part):
                            errors.append(f"Line {i}: Invalid IPv6 address '{ip_part}' in AAAA record")
                    
                    elif record_type == 'MX':
                        # MX records should have priority and hostname
                        if len(parts) < 5:
                            errors.append(f"Line {i}: MX record missing priority or hostname")
                        else:
                            try:
                                priority = int(parts[-2])
                                if priority < 0 or priority > 65535:
                                    errors.append(f"Line {i}: MX priority must be between 0 and 65535")
                            except ValueError:
                                errors.append(f"Line {i}: MX priority must be a number")
            
            except Exception as e:
                errors.append(f"Line {i}: Error parsing record - {str(e)}")
        
        return errors
    
    def _check_record_conflicts(self, records: List[DNSRecord]) -> List[str]:
        """Check for conflicting DNS records"""
        errors = []
        
        # Group records by name
        records_by_name = {}
        for record in records:
            if record.name not in records_by_name:
                records_by_name[record.name] = []
            records_by_name[record.name].append(record)
        
        # Check for conflicts
        for name, name_records in records_by_name.items():
            # CNAME conflicts
            cname_records = [r for r in name_records if r.record_type == 'CNAME']
            other_records = [r for r in name_records if r.record_type != 'CNAME']
            
            if cname_records and other_records:
                errors.append(f"CNAME record for '{name}' conflicts with other record types")
            
            if len(cname_records) > 1:
                errors.append(f"Multiple CNAME records for '{name}' (only one allowed)")
        
        return errors
    
    def _is_valid_domain_name(self, domain: str) -> bool:
        """Validate domain name format"""
        if not domain:
            return False
        
        # Remove trailing dot for validation
        domain = domain.rstrip('.')
        
        # Check length
        if len(domain) > 253:
            return False
        
        # Check each label
        labels = domain.split('.')
        for label in labels:
            if not label:
                return False
            if len(label) > 63:
                return False
            if not label.replace('-', '').replace('_', '').isalnum():
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
        
        return True
    
    def _is_valid_ip_address(self, ip: str) -> bool:
        """Validate IP address (IPv4 or IPv6)"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def _is_valid_ipv4_address(self, ip: str) -> bool:
        """Validate IPv4 address"""
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ValueError:
            return False
    
    def _is_valid_ipv6_address(self, ip: str) -> bool:
        """Validate IPv6 address"""
        try:
            ipaddress.IPv6Address(ip)
            return True
        except ValueError:
            return False
    
    def serialize_dns_record_to_zone_format(self, record: DNSRecord) -> str:
        """Serialize a single DNS record to zone file format"""
        logger = get_bind_logger()
        
        try:
            # Format the record name (left-aligned, 20 characters)
            name_field = f"{record.name:<20}"
            
            # Format TTL field (empty if not specified)
            ttl_field = str(record.ttl) if record.ttl else ""
            
            # Format based on record type
            if record.record_type == 'A':
                return f"{name_field}\t{ttl_field}\tIN\tA\t{record.value}"
            
            elif record.record_type == 'AAAA':
                return f"{name_field}\t{ttl_field}\tIN\tAAAA\t{record.value}"
            
            elif record.record_type == 'CNAME':
                value = record.value if record.value.endswith('.') else f"{record.value}."
                return f"{name_field}\t{ttl_field}\tIN\tCNAME\t{value}"
            
            elif record.record_type == 'MX':
                priority = record.priority if record.priority is not None else 10
                value = record.value if record.value.endswith('.') else f"{record.value}."
                return f"{name_field}\t{ttl_field}\tIN\tMX\t{priority}\t{value}"
            
            elif record.record_type == 'TXT':
                # Escape quotes in TXT records
                escaped_value = record.value.replace('"', '\\"')
                return f"{name_field}\t{ttl_field}\tIN\tTXT\t\"{escaped_value}\""
            
            elif record.record_type == 'SRV':
                priority = record.priority if record.priority is not None else 0
                weight = record.weight if record.weight is not None else 0
                port = record.port if record.port is not None else 0
                value = record.value if record.value.endswith('.') else f"{record.value}."
                return f"{name_field}\t{ttl_field}\tIN\tSRV\t{priority}\t{weight}\t{port}\t{value}"
            
            elif record.record_type == 'PTR':
                value = record.value if record.value.endswith('.') else f"{record.value}."
                return f"{name_field}\t{ttl_field}\tIN\tPTR\t{value}"
            
            elif record.record_type == 'NS':
                value = record.value if record.value.endswith('.') else f"{record.value}."
                return f"{name_field}\t{ttl_field}\tIN\tNS\t{value}"
            
            else:
                # Generic format for other record types
                return f"{name_field}\t{ttl_field}\tIN\t{record.record_type}\t{record.value}"
            
        except Exception as e:
            logger.error(f"Failed to serialize DNS record {record.id}: {e}")
            return f"; ERROR: Failed to serialize record {record.name} ({record.record_type})"
    
    def validate_dns_record_for_zone(self, record: DNSRecord) -> Dict[str, Any]:
        """Validate a DNS record for zone file inclusion"""
        errors = []
        warnings = []
        
        try:
            # Validate record name
            if not record.name:
                errors.append("Record name is required")
            elif not self._is_valid_record_name(record.name):
                errors.append(f"Invalid record name format: {record.name}")
            
            # Validate record type
            valid_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS', 'SOA']
            if record.record_type not in valid_types:
                errors.append(f"Unsupported record type: {record.record_type}")
            
            # Validate record value based on type
            if record.record_type == 'A':
                if not self._is_valid_ipv4_address(record.value):
                    errors.append(f"Invalid IPv4 address: {record.value}")
            
            elif record.record_type == 'AAAA':
                if not self._is_valid_ipv6_address(record.value):
                    errors.append(f"Invalid IPv6 address: {record.value}")
            
            elif record.record_type == 'CNAME':
                if not self._is_valid_domain_name(record.value):
                    errors.append(f"Invalid CNAME target: {record.value}")
            
            elif record.record_type == 'MX':
                if not self._is_valid_domain_name(record.value):
                    errors.append(f"Invalid MX target: {record.value}")
                if record.priority is None:
                    errors.append("MX record requires priority")
                elif record.priority < 0 or record.priority > 65535:
                    errors.append("MX priority must be between 0 and 65535")
            
            elif record.record_type == 'SRV':
                if not self._is_valid_domain_name(record.value):
                    errors.append(f"Invalid SRV target: {record.value}")
                if record.priority is None:
                    errors.append("SRV record requires priority")
                elif record.priority < 0 or record.priority > 65535:
                    errors.append("SRV priority must be between 0 and 65535")
                if record.weight is None:
                    errors.append("SRV record requires weight")
                elif record.weight < 0 or record.weight > 65535:
                    errors.append("SRV weight must be between 0 and 65535")
                if record.port is None:
                    errors.append("SRV record requires port")
                elif record.port < 1 or record.port > 65535:
                    errors.append("SRV port must be between 1 and 65535")
            
            elif record.record_type == 'NS':
                if not self._is_valid_domain_name(record.value):
                    errors.append(f"Invalid NS target: {record.value}")
            
            elif record.record_type == 'PTR':
                if not self._is_valid_domain_name(record.value):
                    errors.append(f"Invalid PTR target: {record.value}")
            
            elif record.record_type == 'TXT':
                if len(record.value) > 255:
                    warnings.append("TXT record value is very long (>255 characters)")
                # Check for unescaped quotes
                if '"' in record.value and not record.value.startswith('"'):
                    warnings.append("TXT record contains unescaped quotes")
            
            # Validate TTL
            if record.ttl is not None:
                if record.ttl < 0 or record.ttl > 2147483647:  # Max 32-bit signed integer
                    errors.append("TTL must be between 0 and 2147483647")
                elif record.ttl < 60:
                    warnings.append("TTL is very low (<60 seconds)")
                elif record.ttl > 86400:
                    warnings.append("TTL is very high (>24 hours)")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    def _is_valid_record_name(self, name: str) -> bool:
        """Validate DNS record name"""
        if not name:
            return False
        
        # Allow @ for zone apex
        if name == '@':
            return True
        
        # Allow wildcard records
        if name.startswith('*.'):
            name = name[2:]
        
        # Validate as domain name
        return self._is_valid_domain_name(name)
    
    def group_records_by_type(self, records: List[DNSRecord]) -> Dict[str, List[DNSRecord]]:
        """Group DNS records by type for organized zone file generation"""
        grouped = {
            'NS': [],
            'A': [],
            'AAAA': [],
            'CNAME': [],
            'MX': [],
            'TXT': [],
            'SRV': [],
            'PTR': [],
            'OTHER': []
        }
        
        for record in records:
            if not record.is_active:
                continue
                
            record_type = record.record_type.upper()
            if record_type in grouped:
                grouped[record_type].append(record)
            else:
                grouped['OTHER'].append(record)
        
        return grouped
    
    def format_zone_file_with_records(self, zone: Zone, records: List[DNSRecord]) -> str:
        """Enhanced zone file formatting with comprehensive record serialization"""
        logger = get_bind_logger()
        
        try:
            # Generate zone file header
            header = f"""; Zone file for {zone.name}
; Generated automatically by Hybrid DNS Server
; Zone Type: {zone.zone_type}
; Serial: {zone.serial}
; Last Updated: {zone.updated_at.strftime('%Y-%m-%d %H:%M:%S') if zone.updated_at else 'Unknown'}

$TTL {zone.minimum}
$ORIGIN {zone.name if zone.name.endswith('.') else zone.name + '.'}

"""
            
            # Generate SOA record
            soa_record = self.generate_soa_record_sync(zone)
            
            # Group and serialize records
            grouped_records = self.group_records_by_type(records)
            
            record_sections = []
            
            # Add NS records first (after SOA)
            if grouped_records['NS']:
                record_sections.append("; Name Server Records")
                for record in grouped_records['NS']:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add A records
            if grouped_records['A']:
                record_sections.append("; A Records (IPv4 addresses)")
                for record in grouped_records['A']:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add AAAA records
            if grouped_records['AAAA']:
                record_sections.append("; AAAA Records (IPv6 addresses)")
                for record in grouped_records['AAAA']:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add CNAME records
            if grouped_records['CNAME']:
                record_sections.append("; CNAME Records (Canonical names)")
                for record in grouped_records['CNAME']:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add MX records (sorted by priority)
            if grouped_records['MX']:
                record_sections.append("; MX Records (Mail exchangers)")
                mx_records = sorted(grouped_records['MX'], key=lambda r: r.priority or 10)
                for record in mx_records:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add TXT records
            if grouped_records['TXT']:
                record_sections.append("; TXT Records (Text records)")
                for record in grouped_records['TXT']:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add SRV records (sorted by priority)
            if grouped_records['SRV']:
                record_sections.append("; SRV Records (Service records)")
                srv_records = sorted(grouped_records['SRV'], key=lambda r: r.priority or 0)
                for record in srv_records:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add PTR records
            if grouped_records['PTR']:
                record_sections.append("; PTR Records (Pointer records)")
                for record in grouped_records['PTR']:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Add other record types
            if grouped_records['OTHER']:
                record_sections.append("; Other Records")
                for record in grouped_records['OTHER']:
                    record_sections.append(self.serialize_dns_record_to_zone_format(record))
                record_sections.append("")
            
            # Combine all sections
            content = header + soa_record + "\n\n"
            if record_sections:
                content += "\n".join(record_sections)
            else:
                content += "; No DNS records defined for this zone\n"
            
            logger.debug(f"Enhanced zone file formatting completed for {zone.name}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to format zone file with records for {zone.name}: {e}")
            raise
    
    async def validate_zone_file_before_generation(self, zone: Zone, records: List[DNSRecord]) -> Dict:
        """Validate zone and records before generating zone file"""
        logger = get_bind_logger()
        logger.info(f"Pre-validating zone file generation for: {zone.name}")
        
        errors = []
        warnings = []
        
        try:
            # Validate zone configuration
            config_validation = self._validate_zone_configuration(zone)
            errors.extend(config_validation["errors"])
            warnings.extend(config_validation["warnings"])
            
            # Validate all records
            for record in records:
                if record.is_active:
                    record_validation = self.validate_dns_record_for_zone(record)
                    if not record_validation["valid"]:
                        for error in record_validation["errors"]:
                            errors.append(f"Record '{record.name}' ({record.record_type}): {error}")
                    
                    for warning in record_validation.get("warnings", []):
                        warnings.append(f"Record '{record.name}' ({record.record_type}): {warning}")
            
            # Check for record conflicts
            active_records = [r for r in records if r.is_active]
            conflict_errors = self._check_record_conflicts(active_records)
            errors.extend(conflict_errors)
            
            # Check for required records
            if zone.zone_type == "master":
                ns_records = [r for r in active_records if r.record_type == 'NS']
                if not ns_records:
                    warnings.append("Master zone should have at least one NS record")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "record_count": len(active_records),
                "zone_type": zone.zone_type
            }
            
        except Exception as e:
            logger.error(f"Failed to pre-validate zone file for {zone.name}: {e}")
            return {
                "valid": False,
                "errors": [f"Pre-validation error: {str(e)}"],
                "warnings": warnings,
                "record_count": 0,
                "zone_type": zone.zone_type
            }
    
    async def validate_generated_zone_file(self, zone: Zone, zone_file_path: Path) -> Dict:
        """Validate a generated zone file using BIND tools"""
        logger = get_bind_logger()
        logger.info(f"Validating generated zone file: {zone_file_path}")
        
        errors = []
        warnings = []
        
        try:
            # Check if file exists and is readable
            if not zone_file_path.exists():
                errors.append(f"Zone file does not exist: {zone_file_path}")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            if not zone_file_path.is_file():
                errors.append(f"Zone file path is not a file: {zone_file_path}")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Validate file permissions
            if not zone_file_path.stat().st_mode & 0o044:  # Check if readable by others
                warnings.append("Zone file may not be readable by BIND9 (check permissions)")
            
            # Use named-checkzone for basic validation
            result = await self._run_command([
                "/usr/bin/named-checkzone",
                zone.name,
                str(zone_file_path)
            ])
            
            if result["returncode"] != 0:
                # Parse detailed error output
                stderr_lines = result["stderr"].strip().split('\n')
                for line in stderr_lines:
                    if line.strip() and not line.startswith('zone'):
                        errors.append(f"Zone validation: {line.strip()}")
            
            # Check stdout for warnings even if validation passed
            if result["stdout"].strip():
                stdout_lines = result["stdout"].strip().split('\n')
                for line in stdout_lines:
                    if "warning" in line.lower():
                        warnings.append(f"Zone warning: {line.strip()}")
            
            # Additional content validation
            content_validation = await self._validate_zone_file_content(zone, zone_file_path)
            errors.extend(content_validation["errors"])
            warnings.extend(content_validation["warnings"])
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "file_size": zone_file_path.stat().st_size,
                "file_path": str(zone_file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to validate generated zone file {zone_file_path}: {e}")
            return {
                "valid": False,
                "errors": [f"Zone file validation error: {str(e)}"],
                "warnings": warnings,
                "file_size": 0,
                "file_path": str(zone_file_path)
            }
    
    # Reverse Zone Generation Utilities
    
    def generate_reverse_zone_name_from_network(self, network: str) -> str:
        """Generate reverse zone name from network CIDR notation"""
        logger = get_bind_logger()
        
        try:
            import ipaddress
            
            # Parse the network
            net = ipaddress.ip_network(network, strict=False)
            
            if isinstance(net, ipaddress.IPv4Network):
                return self._generate_ipv4_reverse_zone_name(net)
            elif isinstance(net, ipaddress.IPv6Network):
                return self._generate_ipv6_reverse_zone_name(net)
            else:
                raise ValueError(f"Unsupported network type: {type(net)}")
                
        except Exception as e:
            logger.error(f"Failed to generate reverse zone name from network {network}: {e}")
            raise ValueError(f"Invalid network format: {network}")
    
    def _generate_ipv4_reverse_zone_name(self, network: ipaddress.IPv4Network) -> str:
        """Generate IPv4 reverse zone name from network"""
        # Get the network address octets
        octets = str(network.network_address).split('.')
        prefix_len = network.prefixlen
        
        # Determine how many octets to include based on prefix length
        if prefix_len >= 24:
            # /24 or smaller - use 3 octets (e.g., 1.168.192.in-addr.arpa)
            return f"{octets[2]}.{octets[1]}.{octets[0]}.in-addr.arpa"
        elif prefix_len >= 16:
            # /16 to /23 - use 2 octets (e.g., 168.192.in-addr.arpa)
            return f"{octets[1]}.{octets[0]}.in-addr.arpa"
        elif prefix_len >= 8:
            # /8 to /15 - use 1 octet (e.g., 192.in-addr.arpa)
            return f"{octets[0]}.in-addr.arpa"
        else:
            # Less than /8 - not commonly used for reverse zones
            raise ValueError(f"Network prefix /{prefix_len} is too large for reverse zone generation")
    
    def _generate_ipv6_reverse_zone_name(self, network: ipaddress.IPv6Network) -> str:
        """Generate IPv6 reverse zone name from network"""
        # IPv6 reverse zones use nibble format
        # Each hex digit becomes a separate label in reverse order
        
        # Get the network address as hex string without colons
        hex_addr = format(int(network.network_address), '032x')
        prefix_len = network.prefixlen
        
        # Calculate how many nibbles to include (each nibble is 4 bits)
        nibbles_count = prefix_len // 4
        if prefix_len % 4 != 0:
            nibbles_count += 1
        
        # Take the required number of nibbles and reverse them
        nibbles = list(hex_addr[:nibbles_count])
        nibbles.reverse()
        
        # Join with dots and add .ip6.arpa
        return '.'.join(nibbles) + '.ip6.arpa'
    
    def generate_ptr_record_name_from_ip(self, ip_address: str, zone_name: str) -> str:
        """Generate PTR record name from IP address for a reverse zone"""
        logger = get_bind_logger()
        
        try:
            import ipaddress
            
            # Parse the IP address
            ip = ipaddress.ip_address(ip_address)
            
            if isinstance(ip, ipaddress.IPv4Address):
                return self._generate_ipv4_ptr_name(ip, zone_name)
            elif isinstance(ip, ipaddress.IPv6Address):
                return self._generate_ipv6_ptr_name(ip, zone_name)
            else:
                raise ValueError(f"Unsupported IP address type: {type(ip)}")
                
        except Exception as e:
            logger.error(f"Failed to generate PTR record name from IP {ip_address}: {e}")
            raise ValueError(f"Invalid IP address format: {ip_address}")
    
    def _generate_ipv4_ptr_name(self, ip: ipaddress.IPv4Address, zone_name: str) -> str:
        """Generate IPv4 PTR record name"""
        octets = str(ip).split('.')
        
        # Determine the PTR name based on the zone
        if zone_name.endswith('.in-addr.arpa'):
            # Extract the zone's network part
            zone_part = zone_name[:-13]  # Remove .in-addr.arpa
            zone_octets = zone_part.split('.')
            zone_octets.reverse()  # Reverse to get normal order
            
            # Determine which octets are covered by the zone
            if len(zone_octets) == 1:
                # /8 zone - use last 3 octets
                return f"{octets[3]}.{octets[2]}.{octets[1]}"
            elif len(zone_octets) == 2:
                # /16 zone - use last 2 octets
                return f"{octets[3]}.{octets[2]}"
            elif len(zone_octets) == 3:
                # /24 zone - use last octet
                return octets[3]
            else:
                # Full reverse - shouldn't happen in a zone context
                return f"{octets[3]}.{octets[2]}.{octets[1]}.{octets[0]}"
        else:
            raise ValueError(f"Zone {zone_name} is not a valid IPv4 reverse zone")
    
    def _generate_ipv6_ptr_name(self, ip: ipaddress.IPv6Address, zone_name: str) -> str:
        """Generate IPv6 PTR record name"""
        if not zone_name.endswith('.ip6.arpa'):
            raise ValueError(f"Zone {zone_name} is not a valid IPv6 reverse zone")
        
        # Get the full IPv6 address as hex string
        hex_addr = format(int(ip), '032x')
        
        # Convert to nibble format (each hex digit separated by dots, reversed)
        nibbles = list(hex_addr)
        nibbles.reverse()
        
        # Extract the zone's nibble part
        zone_part = zone_name[:-9]  # Remove .ip6.arpa
        zone_nibbles = zone_part.split('.') if zone_part else []
        
        # The PTR name should be the nibbles not covered by the zone
        ptr_nibbles = nibbles[len(zone_nibbles):]
        
        return '.'.join(ptr_nibbles)
    
    def create_reverse_zone_from_network(self, network: str, email: str, 
                                       nameservers: List[str] = None) -> Dict[str, Any]:
        """Create a complete reverse zone configuration from network CIDR"""
        logger = get_bind_logger()
        
        try:
            import ipaddress
            
            # Generate zone name
            zone_name = self.generate_reverse_zone_name_from_network(network)
            
            # Parse network for additional info
            net = ipaddress.ip_network(network, strict=False)
            
            # Create zone data
            zone_data = {
                'name': zone_name,
                'zone_type': 'master',
                'email': email,
                'description': f'Reverse zone for network {network}',
                'refresh': 10800,
                'retry': 3600,
                'expire': 604800,
                'minimum': 86400
            }
            
            # Generate sample PTR records for the network
            sample_records = []
            
            if nameservers:
                # Add NS records
                for ns in nameservers:
                    sample_records.append({
                        'name': '@',
                        'record_type': 'NS',
                        'value': ns if ns.endswith('.') else f"{ns}.",
                        'ttl': None
                    })
            
            # Add a few sample PTR records
            if isinstance(net, ipaddress.IPv4Network):
                # Add sample PTR records for first few IPs
                for i, ip in enumerate(net.hosts()):
                    if i >= 3:  # Only add first 3 as examples
                        break
                    
                    ptr_name = self.generate_ptr_record_name_from_ip(str(ip), zone_name)
                    sample_records.append({
                        'name': ptr_name,
                        'record_type': 'PTR',
                        'value': f'host{i+1}.example.com.',
                        'ttl': None
                    })
            
            return {
                'zone_data': zone_data,
                'sample_records': sample_records,
                'network_info': {
                    'network': str(net),
                    'network_address': str(net.network_address),
                    'broadcast_address': str(net.broadcast_address) if isinstance(net, ipaddress.IPv4Network) else None,
                    'num_addresses': net.num_addresses,
                    'prefix_length': net.prefixlen
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create reverse zone from network {network}: {e}")
            raise ValueError(f"Failed to create reverse zone: {str(e)}")
    
    def validate_reverse_zone_consistency(self, zone: Zone, records: List[DNSRecord]) -> Dict[str, Any]:
        """Validate that reverse zone records are consistent with the zone"""
        logger = get_bind_logger()
        errors = []
        warnings = []
        
        try:
            # Check if this is actually a reverse zone
            if not (zone.name.endswith('.in-addr.arpa') or zone.name.endswith('.ip6.arpa')):
                errors.append("Zone is not a reverse zone")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Validate PTR records
            for record in records:
                if not record.is_active:
                    continue
                    
                if record.record_type == 'PTR':
                    try:
                        # Try to reconstruct the full IP from the PTR record name and zone
                        full_ip = self._reconstruct_ip_from_ptr_record(record.name, zone.name)
                        if not full_ip:
                            warnings.append(f"Could not validate PTR record {record.name}")
                    except Exception as e:
                        errors.append(f"Invalid PTR record {record.name}: {str(e)}")
                
                elif record.record_type not in ['NS', 'SOA', 'TXT']:
                    warnings.append(f"Record type {record.record_type} is unusual in reverse zones")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Failed to validate reverse zone consistency: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    def _reconstruct_ip_from_ptr_record(self, ptr_name: str, zone_name: str) -> Optional[str]:
        """Reconstruct full IP address from PTR record name and zone"""
        try:
            import ipaddress
            
            if zone_name.endswith('.in-addr.arpa'):
                # IPv4 reverse zone
                zone_part = zone_name[:-13]  # Remove .in-addr.arpa
                zone_octets = zone_part.split('.')
                zone_octets.reverse()  # Get normal order
                
                # Combine zone octets with PTR name octets
                if ptr_name == '@':
                    # PTR for the zone itself
                    ip_octets = zone_octets + ['0'] * (4 - len(zone_octets))
                else:
                    ptr_octets = ptr_name.split('.')
                    ptr_octets.reverse()  # Reverse PTR octets
                    ip_octets = zone_octets + ptr_octets
                
                # Pad to 4 octets if needed
                while len(ip_octets) < 4:
                    ip_octets.append('0')
                
                ip_str = '.'.join(ip_octets[:4])
                # Validate the IP
                ipaddress.IPv4Address(ip_str)
                return ip_str
                
            elif zone_name.endswith('.ip6.arpa'):
                # IPv6 reverse zone - more complex reconstruction
                zone_part = zone_name[:-9]  # Remove .ip6.arpa
                zone_nibbles = zone_part.split('.') if zone_part else []
                
                if ptr_name == '@':
                    # PTR for the zone itself
                    all_nibbles = zone_nibbles
                else:
                    ptr_nibbles = ptr_name.split('.')
                    all_nibbles = zone_nibbles + ptr_nibbles
                
                # Reverse nibbles to get correct order
                all_nibbles.reverse()
                
                # Pad to 32 nibbles (128 bits / 4 bits per nibble)
                while len(all_nibbles) < 32:
                    all_nibbles.append('0')
                
                # Group into 4-nibble chunks and join with colons
                hex_groups = []
                for i in range(0, 32, 4):
                    group = ''.join(all_nibbles[i:i+4])
                    hex_groups.append(group)
                
                ip_str = ':'.join(hex_groups)
                # Validate and compress the IPv6 address
                ip_obj = ipaddress.IPv6Address(ip_str)
                return str(ip_obj)
            
            return None
            
        except Exception:
            return None
                
        except Exception as e:
            logger.error(f"Failed to serialize DNS record {record.id} to zone format: {e}")
            raise ValueError(f"Invalid DNS record data for serialization: {e}")
    
    def validate_dns_record_for_zone(self, record: DNSRecord) -> Dict[str, Any]:
        """Validate DNS record data for zone file generation"""
        logger = get_bind_logger()
        errors = []
        warnings = []
        
        try:
            # Basic field validation
            if record.name is None:
                errors.append("Record name cannot be None")
            elif record.name == "":
                # Empty name is allowed (represents zone apex @)
                pass
            elif not record.name.strip():
                errors.append("Record name cannot be empty or whitespace only")
            
            if not record.value or not record.value.strip():
                errors.append("Record value cannot be empty")
            
            if not record.record_type:
                errors.append("Record type cannot be empty")
            
            # TTL validation
            if record.ttl is not None:
                if record.ttl < 60:
                    warnings.append("TTL is very low (< 60 seconds)")
                elif record.ttl > 86400:
                    warnings.append("TTL is very high (> 24 hours)")
            
            # Record type-specific validation
            if record.record_type == 'A':
                # Validate IPv4 address format
                import ipaddress
                try:
                    ipaddress.IPv4Address(record.value)
                except ipaddress.AddressValueError:
                    errors.append(f"Invalid IPv4 address: {record.value}")
            
            elif record.record_type == 'AAAA':
                # Validate IPv6 address format
                import ipaddress
                try:
                    ipaddress.IPv6Address(record.value)
                except ipaddress.AddressValueError:
                    errors.append(f"Invalid IPv6 address: {record.value}")
            
            elif record.record_type == 'MX':
                if record.priority is None:
                    errors.append("MX records require a priority value")
                elif record.priority < 0 or record.priority > 65535:
                    errors.append("MX priority must be between 0 and 65535")
            
            elif record.record_type == 'SRV':
                if record.priority is None:
                    errors.append("SRV records require a priority value")
                if record.weight is None:
                    errors.append("SRV records require a weight value")
                if record.port is None:
                    errors.append("SRV records require a port value")
                
                if record.priority is not None and (record.priority < 0 or record.priority > 65535):
                    errors.append("SRV priority must be between 0 and 65535")
                if record.weight is not None and (record.weight < 0 or record.weight > 65535):
                    errors.append("SRV weight must be between 0 and 65535")
                if record.port is not None and (record.port < 1 or record.port > 65535):
                    errors.append("SRV port must be between 1 and 65535")
            
            elif record.record_type == 'CNAME':
                # CNAME records should not coexist with other record types for the same name
                # This validation would need database context to check properly
                if record.name == '@':
                    errors.append("CNAME records cannot be used for the zone apex (@)")
            
            elif record.record_type == 'TXT':
                # TXT records can contain almost anything, but check for extremely long values
                if len(record.value) > 255:
                    warnings.append("TXT record value is very long (> 255 characters)")
            
            # Domain name validation for records that should contain domain names
            domain_record_types = ['CNAME', 'MX', 'NS', 'PTR', 'SRV']
            if record.record_type in domain_record_types:
                # Basic domain name validation
                if not self._is_valid_domain_name(record.value):
                    warnings.append(f"Value may not be a valid domain name: {record.value}")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Failed to validate DNS record {record.id}: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }
    
    def _is_valid_domain_name(self, domain: str) -> bool:
        """Basic domain name validation"""
        if not domain:
            return False
        
        # Remove trailing dot for validation
        domain = domain.rstrip('.')
        
        # Check length
        if len(domain) > 253:
            return False
        
        # Check each label
        labels = domain.split('.')
        for label in labels:
            if not label:  # Empty label
                return False
            if len(label) > 63:  # Label too long
                return False
            if label.startswith('-') or label.endswith('-'):  # Invalid hyphens
                return False
            if not all(c.isalnum() or c == '-' for c in label):  # Invalid characters
                return False
        
        return True
    
    def group_records_by_type(self, records: List[DNSRecord]) -> Dict[str, List[DNSRecord]]:
        """Group DNS records by type for organized zone file output"""
        grouped = {
            'NS': [],
            'A': [],
            'AAAA': [],
            'CNAME': [],
            'MX': [],
            'TXT': [],
            'SRV': [],
            'PTR': [],
            'OTHER': []
        }
        
        for record in records:
            if not record.is_active:
                continue
                
            record_type = record.record_type.upper()
            if record_type in grouped:
                grouped[record_type].append(record)
            else:
                grouped['OTHER'].append(record)
        
        # Sort records within each group
        for record_type, record_list in grouped.items():
            if record_type in ['MX', 'SRV']:
                # Sort by priority for MX and SRV records
                record_list.sort(key=lambda r: (r.priority or 0, r.name))
            elif record_type == 'PTR':
                # Sort PTR records by name for reverse zones
                record_list.sort(key=lambda r: r.name)
            else:
                # Sort other records by name
                record_list.sort(key=lambda r: r.name)
        
        return grouped
    
    def format_zone_file_with_records(self, zone: Zone, records: List[DNSRecord]) -> str:
        """Format complete zone file with properly serialized DNS records"""
        logger = get_bind_logger()
        
        try:
            # Group and sort records
            grouped_records = self.group_records_by_type(records)
            
            # Start with zone header
            lines = [
                f"; Zone file for {zone.name}",
                f"; Generated automatically by Hybrid DNS Server",
                f"; Zone Type: {zone.zone_type}",
                f"; Serial: {zone.serial}",
                f"; Last Updated: {zone.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                f"$TTL {zone.minimum}",
                f"$ORIGIN {zone.name}.",
                "",
                "; SOA Record"
            ]
            
            # Add SOA record (synchronous version)
            soa_record = self.generate_soa_record_sync(zone)
            lines.append(soa_record)
            lines.append("")
            
            # Add records by type in proper order
            record_type_order = ['NS', 'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'OTHER']
            
            for record_type in record_type_order:
                if grouped_records[record_type]:
                    # Add section header
                    if record_type == 'NS':
                        lines.append("; Name Server Records")
                    elif record_type == 'A':
                        lines.append("; A Records (IPv4 addresses)")
                    elif record_type == 'AAAA':
                        lines.append("; AAAA Records (IPv6 addresses)")
                    elif record_type == 'CNAME':
                        lines.append("; CNAME Records (Canonical names)")
                    elif record_type == 'MX':
                        lines.append("; MX Records (Mail exchangers)")
                    elif record_type == 'TXT':
                        lines.append("; TXT Records (Text records)")
                    elif record_type == 'SRV':
                        lines.append("; SRV Records (Service records)")
                    elif record_type == 'PTR':
                        lines.append("; PTR Records (Pointer records)")
                    elif record_type == 'OTHER':
                        lines.append("; Other Records")
                    
                    # Add records
                    for record in grouped_records[record_type]:
                        try:
                            record_line = self.serialize_dns_record_to_zone_format(record)
                            lines.append(record_line)
                        except Exception as e:
                            logger.error(f"Failed to serialize record {record.id}: {e}")
                            lines.append(f"; ERROR: Failed to serialize record {record.name} {record.record_type}")
                    
                    lines.append("")  # Empty line after each section
            
            if not any(grouped_records.values()):
                lines.append("; No DNS records defined for this zone")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to format zone file for {zone.name}: {e}")
            raise
    
    async def increment_zone_serial(self, zone: Zone) -> int:
        """Increment zone serial number in YYYYMMDDNN format"""
        from datetime import datetime
        
        now = datetime.now()
        date_part = now.strftime("%Y%m%d")
        
        if zone.serial:
            current_serial_str = str(zone.serial)
            # Check if it's from today and in correct format
            if (current_serial_str.startswith(date_part) and 
                len(current_serial_str) == 10 and 
                current_serial_str.isdigit()):
                # Increment the sequence number
                sequence = int(current_serial_str[-2:]) + 1
                if sequence > 99:
                    sequence = 99  # Max sequences per day
            else:
                # Current serial is not in today's format, start fresh
                sequence = 1
        else:
            # No existing serial, start with 1
            sequence = 1
        
        new_serial = int(f"{date_part}{sequence:02d}")
        return new_serial
    
    async def validate_zone_file_syntax(self, zone_file_path: Path, zone_name: str) -> Dict:
        """Validate zone file syntax using named-checkzone"""
        logger = get_bind_logger()
        
        try:
            if not zone_file_path.exists():
                return {
                    "valid": False,
                    "errors": [f"Zone file does not exist: {zone_file_path}"],
                    "warnings": []
                }
            
            # Use named-checkzone to validate
            result = await self._run_command([
                "/usr/sbin/named-checkzone", 
                "-q",  # Quiet mode
                zone_name, 
                str(zone_file_path)
            ])
            
            errors = []
            warnings = []
            
            if result["returncode"] != 0:
                # Parse error output
                error_lines = result["stderr"].strip().split('\n')
                for line in error_lines:
                    if line.strip():
                        if 'warning' in line.lower():
                            warnings.append(line.strip())
                        else:
                            errors.append(line.strip())
            
            return {
                "valid": result["returncode"] == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Failed to validate zone file {zone_file_path}: {e}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": []
            }
    
    async def get_zone_file_info(self, zone: Zone) -> Dict:
        """Get information about a zone file"""
        logger = get_bind_logger()
        
        try:
            if not zone.file_path:
                return {
                    "exists": False,
                    "path": None,
                    "size": 0,
                    "modified": None,
                    "readable": False
                }
            
            zone_file_path = Path(zone.file_path)
            
            if not zone_file_path.exists():
                return {
                    "exists": False,
                    "path": str(zone_file_path),
                    "size": 0,
                    "modified": None,
                    "readable": False
                }
            
            stat = zone_file_path.stat()
            
            return {
                "exists": True,
                "path": str(zone_file_path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "readable": zone_file_path.is_file() and zone_file_path.stat().st_mode & 0o044
            }
            
        except Exception as e:
            logger.error(f"Failed to get zone file info for {zone.name}: {e}")
            return {
                "exists": False,
                "path": zone.file_path,
                "size": 0,
                "modified": None,
                "readable": False,
                "error": str(e)
            }
    
    def generate_reverse_zone_records_from_forward_zone(self, forward_zone: Zone, 
                                                       forward_records: List[DNSRecord],
                                                       reverse_zone_name: str) -> List[Dict[str, Any]]:
        """Generate PTR records for a reverse zone from forward zone A/AAAA records"""
        logger = get_bind_logger()
        ptr_records = []
        
        try:
            for record in forward_records:
                if not record.is_active:
                    continue
                
                if record.record_type in ['A', 'AAAA']:
                    try:
                        # Generate PTR record name from the IP address
                        ptr_name = self.generate_ptr_record_name_from_ip(record.value, reverse_zone_name)
                        
                        # Create PTR record pointing back to the forward record
                        fqdn = record.name
                        if record.name == '@':
                            fqdn = forward_zone.name
                        elif not record.name.endswith('.'):
                            fqdn = f"{record.name}.{forward_zone.name}"
                        
                        if not fqdn.endswith('.'):
                            fqdn += '.'
                        
                        ptr_records.append({
                            'name': ptr_name,
                            'record_type': 'PTR',
                            'value': fqdn,
                            'ttl': record.ttl,
                            'source_record_id': record.id,
                            'source_ip': record.value
                        })
                        
                    except Exception as e:
                        logger.warning(f"Could not generate PTR record for {record.name} -> {record.value}: {e}")
                        continue
            
            logger.info(f"Generated {len(ptr_records)} PTR records from forward zone {forward_zone.name}")
            return ptr_records
            
        except Exception as e:
            logger.error(f"Failed to generate reverse zone records: {e}")
            return []
    
    def suggest_reverse_zones_for_forward_zone(self, forward_zone: Zone, 
                                             forward_records: List[DNSRecord]) -> List[Dict[str, Any]]:
        """Suggest reverse zones that should be created based on forward zone records"""
        logger = get_bind_logger()
        suggestions = []
        networks = set()
        
        try:
            import ipaddress
            
            # Collect all IP addresses from A and AAAA records
            ip_addresses = []
            for record in forward_records:
                if record.is_active and record.record_type in ['A', 'AAAA']:
                    try:
                        ip = ipaddress.ip_address(record.value)
                        ip_addresses.append(ip)
                    except ValueError:
                        continue
            
            # Group IPs by common networks
            for ip in ip_addresses:
                if isinstance(ip, ipaddress.IPv4Address):
                    # Suggest /24 networks for IPv4
                    network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                    networks.add(str(network))
                elif isinstance(ip, ipaddress.IPv6Address):
                    # Suggest /64 networks for IPv6
                    network = ipaddress.IPv6Network(f"{ip}/64", strict=False)
                    networks.add(str(network))
            
            # Create suggestions for each network
            for network_str in networks:
                try:
                    zone_name = self.generate_reverse_zone_name_from_network(network_str)
                    
                    # Count how many IPs from this forward zone would be in this reverse zone
                    network = ipaddress.ip_network(network_str)
                    ip_count = sum(1 for ip in ip_addresses if ip in network)
                    
                    suggestions.append({
                        'network': network_str,
                        'reverse_zone_name': zone_name,
                        'ip_count': ip_count,
                        'priority': 'high' if ip_count >= 5 else 'medium' if ip_count >= 2 else 'low'
                    })
                    
                except Exception as e:
                    logger.warning(f"Could not create suggestion for network {network_str}: {e}")
                    continue
            
            # Sort by IP count (most IPs first)
            suggestions.sort(key=lambda x: x['ip_count'], reverse=True)
            
            logger.info(f"Generated {len(suggestions)} reverse zone suggestions for {forward_zone.name}")
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to suggest reverse zones: {e}")
            return []
    
    async def auto_generate_reverse_zone_file(self, zone: Zone, network: str = None) -> bool:
        """Auto-generate reverse zone file with intelligent PTR record creation"""
        logger = get_bind_logger()
        
        try:
            if not (zone.name.endswith('.in-addr.arpa') or zone.name.endswith('.ip6.arpa')):
                raise ValueError("Zone is not a reverse zone")
            
            # If network is not provided, try to derive it from zone name
            if not network:
                network = self._derive_network_from_reverse_zone_name(zone.name)
            
            if not network:
                logger.warning(f"Could not derive network from reverse zone {zone.name}")
                return await self.create_zone_file(zone)
            
            # Get existing records
            records = []
            if self.db:
                records = self.db.query(DNSRecord).filter(
                    DNSRecord.zone_id == zone.id,
                    DNSRecord.is_active == True
                ).all()
            
            # Look for corresponding forward zones to auto-generate PTR records
            if self.db:
                # Find A/AAAA records in other zones that have IPs in this network
                import ipaddress
                net = ipaddress.ip_network(network, strict=False)
                
                # Query for A/AAAA records with IPs in this network
                all_forward_records = self.db.query(DNSRecord).filter(
                    DNSRecord.record_type.in_(['A', 'AAAA']),
                    DNSRecord.is_active == True
                ).all()
                
                auto_ptr_records = []
                for record in all_forward_records:
                    try:
                        ip = ipaddress.ip_address(record.value)
                        if ip in net:
                            # This IP should have a PTR record in our reverse zone
                            ptr_name = self.generate_ptr_record_name_from_ip(record.value, zone.name)
                            
                            # Check if PTR record already exists
                            existing_ptr = next((r for r in records if r.name == ptr_name and r.record_type == 'PTR'), None)
                            if not existing_ptr:
                                # Get the forward zone to construct FQDN
                                forward_zone = self.db.query(Zone).filter(Zone.id == record.zone_id).first()
                                if forward_zone:
                                    fqdn = record.name
                                    if record.name == '@':
                                        fqdn = forward_zone.name
                                    elif not record.name.endswith('.'):
                                        fqdn = f"{record.name}.{forward_zone.name}"
                                    
                                    if not fqdn.endswith('.'):
                                        fqdn += '.'
                                    
                                    auto_ptr_records.append(DNSRecord(
                                        zone_id=zone.id,
                                        name=ptr_name,
                                        record_type='PTR',
                                        value=fqdn,
                                        ttl=record.ttl,
                                        is_active=True
                                    ))
                    except (ValueError, Exception) as e:
                        logger.debug(f"Skipping record {record.value}: {e}")
                        continue
                
                # Add auto-generated PTR records to the list
                records.extend(auto_ptr_records)
                logger.info(f"Auto-generated {len(auto_ptr_records)} PTR records for reverse zone {zone.name}")
            
            # Generate the zone file with all records (existing + auto-generated)
            return await self.create_zone_file(zone)
            
        except Exception as e:
            logger.error(f"Failed to auto-generate reverse zone file for {zone.name}: {e}")
            return False
    
    def _derive_network_from_reverse_zone_name(self, zone_name: str) -> Optional[str]:
        """Derive network CIDR from reverse zone name"""
        try:
            import ipaddress
            
            if zone_name.endswith('.in-addr.arpa'):
                # IPv4 reverse zone
                ip_part = zone_name[:-13]  # Remove .in-addr.arpa
                octets = ip_part.split('.')
                octets.reverse()  # Get normal order
                
                # Pad with zeros and determine network
                if len(octets) == 1:
                    # /8 network
                    return f"{octets[0]}.0.0.0/8"
                elif len(octets) == 2:
                    # /16 network
                    return f"{octets[0]}.{octets[1]}.0.0/16"
                elif len(octets) == 3:
                    # /24 network
                    return f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
                else:
                    return None
                    
            elif zone_name.endswith('.ip6.arpa'):
                # IPv6 reverse zone - more complex
                nibble_part = zone_name[:-9]  # Remove .ip6.arpa
                if not nibble_part:
                    return None
                
                nibbles = nibble_part.split('.')
                nibbles.reverse()  # Get correct order
                
                # Pad to full address and determine prefix
                prefix_len = len(nibbles) * 4  # Each nibble is 4 bits
                
                # Pad nibbles to 32 (full IPv6 address)
                while len(nibbles) < 32:
                    nibbles.append('0')
                
                # Group into 4-nibble chunks
                hex_groups = []
                for i in range(0, 32, 4):
                    group = ''.join(nibbles[i:i+4])
                    hex_groups.append(group)
                
                ip_str = ':'.join(hex_groups)
                ip_obj = ipaddress.IPv6Address(ip_str)
                
                return f"{ip_obj}/{prefix_len}"
            
            return None
            
        except Exception:
            return None  
  # Category-based RPZ Zone Management Methods
    
    async def create_category_based_rpz_zones_by_category(self, category: str) -> bool:
        """Create RPZ zone file for a specific category"""
        logger = get_bind_logger()
        logger.info(f"Creating category-based RPZ zone for: {category}")
        
        try:
            if not self.db:
                logger.error("No database connection available for category-based RPZ zone creation")
                return False
            
            # Import here to avoid circular imports
            from ..models.security import RPZRule
            
            # Get all active rules for this specific category
            category_rules = self.db.query(RPZRule).filter(
                RPZRule.rpz_zone == category,
                RPZRule.is_active == True
            ).all()
            
            if not category_rules:
                logger.warning(f"No active rules found for category: {category}")
                # Still create an empty zone file for consistency
                category_rules = []
            
            # Generate RPZ zone file for this category
            success = await self.generate_rpz_zone_file(category, category_rules)
            
            if success:
                logger.info(f"Successfully created category-based RPZ zone for {category} with {len(category_rules)} rules")
            else:
                logger.error(f"Failed to create category-based RPZ zone for {category}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create category-based RPZ zone for {category}: {e}")
            return False
    
    async def update_category_based_rpz_zone(self, category: str) -> bool:
        """Update a specific category-based RPZ zone"""
        logger = get_bind_logger()
        logger.info(f"Updating category-based RPZ zone: {category}")
        
        try:
            # Create/update the zone file for this category
            success = await self.create_category_based_rpz_zones_by_category(category)
            
            if success:
                # Reload only this specific RPZ zone if possible
                reload_success = await self._reload_specific_rpz_zone(category)
                if not reload_success:
                    # Fallback to full reload
                    logger.warning(f"Specific zone reload failed for {category}, performing full reload")
                    reload_success = await self.reload_configuration()
                
                return reload_success
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update category-based RPZ zone {category}: {e}")
            return False
    
    async def _reload_specific_rpz_zone(self, category: str) -> bool:
        """Reload a specific RPZ zone"""
        logger = get_bind_logger()
        
        try:
            zone_name = f"{category}.rpz"
            result = await self._run_command(["/usr/sbin/rndc", "reload", zone_name])
            success = result["returncode"] == 0
            
            if success:
                logger.info(f"Successfully reloaded RPZ zone: {zone_name}")
            else:
                logger.warning(f"Failed to reload RPZ zone {zone_name}: {result['stderr']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to reload specific RPZ zone {category}: {e}")
            return False
    
    def get_supported_rpz_categories(self) -> Dict[str, Dict[str, str]]:
        """Get list of supported RPZ categories with their configurations"""
        return {
            'malware': {
                'display_name': 'Malware Protection',
                'description': 'Blocks known malware and malicious domains',
                'default_action': 'block',
                'priority': 1,
                'color': '#dc2626'  # Red
            },
            'phishing': {
                'display_name': 'Phishing Protection', 
                'description': 'Blocks phishing and fraudulent websites',
                'default_action': 'block',
                'priority': 2,
                'color': '#ea580c'  # Orange
            },
            'adult': {
                'display_name': 'Adult Content Filter',
                'description': 'Blocks adult and inappropriate content',
                'default_action': 'block',
                'priority': 3,
                'color': '#7c2d12'  # Brown
            },
            'social-media': {
                'display_name': 'Social Media Filter',
                'description': 'Blocks social media platforms and services',
                'default_action': 'block',
                'priority': 4,
                'color': '#1d4ed8'  # Blue
            },
            'gambling': {
                'display_name': 'Gambling Filter',
                'description': 'Blocks gambling and betting websites',
                'default_action': 'block',
                'priority': 5,
                'color': '#7c3aed'  # Purple
            },
            'custom': {
                'display_name': 'Custom Rules',
                'description': 'Custom block, redirect, and allow rules',
                'default_action': 'block',
                'priority': 10,
                'color': '#059669'  # Green
            }
        }
    
    async def get_category_statistics(self, category: str) -> Dict[str, Any]:
        """Get statistics for a specific RPZ category"""
        logger = get_bind_logger()
        
        try:
            if not self.db:
                logger.warning("No database connection available for category statistics")
                return {}
            
            # Import here to avoid circular imports
            from ..models.security import RPZRule
            from sqlalchemy import func
            
            # Get rule counts by action for this category
            stats_query = self.db.query(
                RPZRule.action,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.rpz_zone == category,
                RPZRule.is_active == True
            ).group_by(RPZRule.action)
            
            action_stats = {row.action: row.count for row in stats_query.all()}
            
            # Get total counts
            total_active = sum(action_stats.values())
            total_inactive = self.db.query(RPZRule).filter(
                RPZRule.rpz_zone == category,
                RPZRule.is_active == False
            ).count()
            
            # Get source statistics
            source_stats = {}
            source_query = self.db.query(
                RPZRule.source,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.rpz_zone == category,
                RPZRule.is_active == True
            ).group_by(RPZRule.source)
            
            for row in source_query.all():
                source = row.source or 'manual'
                source_stats[source] = row.count
            
            # Get category info
            category_info = self.get_rpz_category_info(category)
            
            return {
                'category': category,
                'category_info': category_info,
                'total_active_rules': total_active,
                'total_inactive_rules': total_inactive,
                'total_rules': total_active + total_inactive,
                'rules_by_action': {
                    'block': action_stats.get('block', 0),
                    'redirect': action_stats.get('redirect', 0),
                    'passthru': action_stats.get('passthru', 0)
                },
                'rules_by_source': source_stats,
                'last_updated': datetime.now(),
                'zone_file_path': str(self.rpz_dir / f"db.rpz.{category}")
            }
            
        except Exception as e:
            logger.error(f"Failed to get category statistics for {category}: {e}")
            return {
                'category': category,
                'error': str(e),
                'total_rules': 0
            }
    
    async def get_all_categories_statistics(self) -> Dict[str, Any]:
        """Get statistics for all RPZ categories"""
        logger = get_bind_logger()
        
        try:
            if not self.db:
                logger.warning("No database connection available for categories statistics")
                return {}
            
            # Import here to avoid circular imports
            from ..models.security import RPZRule
            
            # Get all distinct categories
            categories = self.db.query(RPZRule.rpz_zone).distinct().all()
            categories = [cat[0] for cat in categories]
            
            # Get statistics for each category
            all_stats = {}
            total_rules = 0
            total_active = 0
            
            for category in categories:
                category_stats = await self.get_category_statistics(category)
                all_stats[category] = category_stats
                total_rules += category_stats.get('total_rules', 0)
                total_active += category_stats.get('total_active_rules', 0)
            
            # Add supported categories that might not have rules yet
            supported_categories = self.get_supported_rpz_categories()
            for category in supported_categories:
                if category not in all_stats:
                    all_stats[category] = await self.get_category_statistics(category)
            
            return {
                'categories': all_stats,
                'summary': {
                    'total_categories': len(all_stats),
                    'total_rules': total_rules,
                    'total_active_rules': total_active,
                    'categories_with_rules': len([c for c in all_stats.values() if c.get('total_rules', 0) > 0])
                },
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to get all categories statistics: {e}")
            return {
                'error': str(e),
                'categories': {},
                'summary': {'total_categories': 0, 'total_rules': 0}
            }
    
    async def create_all_category_based_rpz_zones(self) -> bool:
        """Create all category-based RPZ zones from supported categories"""
        logger = get_bind_logger()
        logger.info("Creating all category-based RPZ zones")
        
        try:
            supported_categories = self.get_supported_rpz_categories()
            success_count = 0
            total_categories = len(supported_categories)
            
            for category in supported_categories.keys():
                try:
                    success = await self.create_category_based_rpz_zones_by_category(category)
                    if success:
                        success_count += 1
                        logger.info(f"Successfully created RPZ zone for category: {category}")
                    else:
                        logger.error(f"Failed to create RPZ zone for category: {category}")
                        
                except Exception as e:
                    logger.error(f"Failed to process category {category}: {e}")
            
            logger.info(f"Created {success_count}/{total_categories} category-based RPZ zones")
            return success_count == total_categories
            
        except Exception as e:
            logger.error(f"Failed to create all category-based RPZ zones: {e}")
            return False
    
    async def update_all_category_based_rpz_zones(self) -> bool:
        """Update all category-based RPZ zones"""
        logger = get_bind_logger()
        logger.info("Updating all category-based RPZ zones")
        
        try:
            # Create/update all category-based zones
            success = await self.create_all_category_based_rpz_zones()
            
            if success:
                # Reload BIND9 configuration to apply changes
                reload_success = await self.reload_configuration()
                if reload_success:
                    logger.info("Successfully updated all category-based RPZ zones and reloaded BIND9")
                else:
                    logger.warning("Category-based RPZ zones updated but BIND9 reload failed")
                return reload_success
            else:
                logger.error("Failed to update some category-based RPZ zones")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update all category-based RPZ zones: {e}")
            return False
    
    async def delete_category_based_rpz_zone(self, category: str) -> bool:
        """Delete a category-based RPZ zone file"""
        logger = get_bind_logger()
        logger.info(f"Deleting category-based RPZ zone: {category}")
        
        try:
            # Define RPZ zone file path
            rpz_file_path = self.rpz_dir / f"db.rpz.{category}"
            
            if rpz_file_path.exists():
                # Backup before deletion
                await self._backup_rpz_file(rpz_file_path)
                
                # Delete the zone file
                rpz_file_path.unlink()
                logger.info(f"Deleted RPZ zone file: {rpz_file_path}")
            else:
                logger.warning(f"RPZ zone file not found: {rpz_file_path}")
            
            # Reload BIND9 configuration
            reload_success = await self.reload_configuration()
            if reload_success:
                logger.info(f"Successfully deleted category-based RPZ zone {category} and reloaded BIND9")
            else:
                logger.warning(f"Category-based RPZ zone {category} deleted but BIND9 reload failed")
            
            return reload_success
            
        except Exception as e:
            logger.error(f"Failed to delete category-based RPZ zone {category}: {e}")
            return False
    
    def validate_rpz_category(self, category: str) -> Dict[str, Any]:
        """Validate RPZ category name and configuration"""
        errors = []
        warnings = []
        
        try:
            # Check if category is supported
            supported_categories = self.get_supported_rpz_categories()
            
            if category not in supported_categories:
                warnings.append(f"Category '{category}' is not in the list of supported categories")
            
            # Validate category name format
            if not category:
                errors.append("Category name cannot be empty")
            elif not category.replace('-', '').replace('_', '').isalnum():
                errors.append("Category name can only contain letters, numbers, hyphens, and underscores")
            elif len(category) > 50:
                errors.append("Category name cannot exceed 50 characters")
            elif category.startswith('-') or category.endswith('-'):
                errors.append("Category name cannot start or end with a hyphen")
            
            # Check for reserved names
            reserved_names = ['localhost', 'local', 'rpz', 'bind', 'named']
            if category.lower() in reserved_names:
                errors.append(f"Category name '{category}' is reserved and cannot be used")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "is_supported": category in supported_categories,
                "category_info": supported_categories.get(category, {})
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Category validation error: {str(e)}"],
                "warnings": warnings,
                "is_supported": False
            }
    
    async def get_rpz_zone_file_content(self, category: str) -> Dict[str, Any]:
        """Get the content of an RPZ zone file for a category"""
        logger = get_bind_logger()
        
        try:
            rpz_file_path = self.rpz_dir / f"db.rpz.{category}"
            
            if not rpz_file_path.exists():
                return {
                    "exists": False,
                    "error": f"RPZ zone file not found: {rpz_file_path}",
                    "content": "",
                    "size": 0
                }
            
            # Read file content
            content = rpz_file_path.read_text(encoding='utf-8')
            file_size = rpz_file_path.stat().st_size
            file_mtime = rpz_file_path.stat().st_mtime
            
            # Parse basic statistics from content
            lines = content.split('\n')
            comment_lines = len([line for line in lines if line.strip().startswith(';')])
            rule_lines = len([line for line in lines if 'CNAME' in line and not line.strip().startswith(';')])
            
            return {
                "exists": True,
                "content": content,
                "size": file_size,
                "modified_time": datetime.fromtimestamp(file_mtime),
                "total_lines": len(lines),
                "comment_lines": comment_lines,
                "rule_lines": rule_lines,
                "file_path": str(rpz_file_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get RPZ zone file content for {category}: {e}")
            return {
                "exists": False,
                "error": str(e),
                "content": "",
                "size": 0
            }
    
    # Rollback functionality methods
    
    async def rollback_configuration(self, backup_id: str) -> bool:
        """Rollback BIND9 configuration to a previous backup"""
        logger = get_bind_logger()
        logger.info(f"Rolling back configuration to backup: {backup_id}")
        
        try:
            from .backup_service import BackupService
            
            backup_service = BackupService()
            
            # Verify backup exists and is valid
            backup_info = await backup_service.get_backup_info(backup_id)
            if not backup_info:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            if not backup_info.get('exists', False):
                logger.error(f"Backup file does not exist: {backup_id}")
                return False
            
            if not backup_info.get('integrity_valid', False):
                logger.error(f"Backup integrity check failed: {backup_id}")
                return False
            
            # Create a backup of current configuration before rollback
            pre_rollback_backup = await self.create_full_configuration_backup(
                f"Pre-rollback backup before restoring {backup_id}"
            )
            
            if not pre_rollback_backup:
                logger.warning("Failed to create pre-rollback backup, continuing anyway")
            
            # Perform the rollback
            success = await backup_service.restore_from_backup(backup_id)
            
            if success:
                # Validate the restored configuration
                config_valid = await self.validate_configuration()
                
                if config_valid:
                    # Reload BIND9 with restored configuration
                    reload_success = await self.reload_configuration()
                    
                    if reload_success:
                        logger.info(f"Successfully rolled back configuration to backup: {backup_id}")
                        return True
                    else:
                        logger.error("Configuration rollback succeeded but BIND9 reload failed")
                        # Try to rollback to pre-rollback state
                        if pre_rollback_backup:
                            logger.info("Attempting to restore pre-rollback state")
                            await backup_service.restore_from_backup(pre_rollback_backup)
                        return False
                else:
                    logger.error("Restored configuration is invalid")
                    # Try to rollback to pre-rollback state
                    if pre_rollback_backup:
                        logger.info("Attempting to restore pre-rollback state due to invalid configuration")
                        await backup_service.restore_from_backup(pre_rollback_backup)
                    return False
            else:
                logger.error(f"Failed to restore from backup: {backup_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to rollback configuration to backup {backup_id}: {e}")
            return False
    
    async def rollback_zone_changes(self, zone_name: str, backup_id: Optional[str] = None) -> bool:
        """Rollback zone changes to a previous backup"""
        logger = get_bind_logger()
        logger.info(f"Rolling back zone changes for: {zone_name}")
        
        try:
            from .backup_service import BackupService, BackupType
            
            backup_service = BackupService()
            
            # If no specific backup ID provided, find the most recent zone backup
            if not backup_id:
                backups = await backup_service.list_backups(BackupType.ZONE_FILE, limit=10)
                zone_backups = [b for b in backups if zone_name in b.original_path]
                
                if not zone_backups:
                    logger.error(f"No backups found for zone: {zone_name}")
                    return False
                
                backup_id = zone_backups[0].backup_id
                logger.info(f"Using most recent backup for zone {zone_name}: {backup_id}")
            
            # Verify backup exists and is valid
            backup_info = await backup_service.get_backup_info(backup_id)
            if not backup_info:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            if not backup_info.get('exists', False):
                logger.error(f"Backup file does not exist: {backup_id}")
                return False
            
            # Get zone from database if available
            zone = None
            if self.db:
                zone = self.db.query(Zone).filter(Zone.name == zone_name).first()
            
            # Create backup of current zone file before rollback
            if zone and zone.file_path:
                current_zone_path = Path(zone.file_path)
                if current_zone_path.exists():
                    await backup_service.create_backup(
                        current_zone_path,
                        BackupType.ZONE_FILE,
                        f"Pre-rollback backup of {zone_name} before restoring {backup_id}"
                    )
            
            # Perform the rollback
            success = await backup_service.restore_from_backup(backup_id)
            
            if success:
                # Validate the restored zone file
                if zone:
                    validation_result = await self.validate_zone(zone)
                    
                    if validation_result["valid"]:
                        # Reload the specific zone
                        reload_success = await self.reload_zone(zone.id)
                        
                        if reload_success:
                            logger.info(f"Successfully rolled back zone {zone_name} to backup: {backup_id}")
                            return True
                        else:
                            logger.error(f"Zone rollback succeeded but zone reload failed for: {zone_name}")
                            return False
                    else:
                        logger.error(f"Restored zone file is invalid for {zone_name}: {validation_result['errors']}")
                        return False
                else:
                    # No database connection, just reload configuration
                    reload_success = await self.reload_configuration()
                    if reload_success:
                        logger.info(f"Successfully rolled back zone {zone_name} to backup: {backup_id}")
                        return True
                    else:
                        logger.error("Zone rollback succeeded but configuration reload failed")
                        return False
            else:
                logger.error(f"Failed to restore zone {zone_name} from backup: {backup_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to rollback zone {zone_name} to backup {backup_id}: {e}")
            return False
    
    async def rollback_rpz_changes(self, rpz_zone: str, backup_id: Optional[str] = None) -> bool:
        """Rollback RPZ zone changes to a previous backup"""
        logger = get_bind_logger()
        logger.info(f"Rolling back RPZ zone changes for: {rpz_zone}")
        
        try:
            from .backup_service import BackupService, BackupType
            
            backup_service = BackupService()
            
            # If no specific backup ID provided, find the most recent RPZ backup
            if not backup_id:
                backups = await backup_service.list_backups(BackupType.RPZ_FILE, limit=10)
                rpz_backups = [b for b in backups if rpz_zone in b.original_path]
                
                if not rpz_backups:
                    logger.error(f"No backups found for RPZ zone: {rpz_zone}")
                    return False
                
                backup_id = rpz_backups[0].backup_id
                logger.info(f"Using most recent backup for RPZ zone {rpz_zone}: {backup_id}")
            
            # Verify backup exists and is valid
            backup_info = await backup_service.get_backup_info(backup_id)
            if not backup_info:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            if not backup_info.get('exists', False):
                logger.error(f"Backup file does not exist: {backup_id}")
                return False
            
            # Create backup of current RPZ file before rollback
            rpz_file_path = self.rpz_dir / f"db.rpz.{rpz_zone}"
            if rpz_file_path.exists():
                await backup_service.create_backup(
                    rpz_file_path,
                    BackupType.RPZ_FILE,
                    f"Pre-rollback backup of RPZ {rpz_zone} before restoring {backup_id}"
                )
            
            # Perform the rollback
            success = await backup_service.restore_from_backup(backup_id)
            
            if success:
                # Validate the restored RPZ zone file
                validation_result = await self.validate_generated_rpz_zone_file(rpz_zone, rpz_file_path)
                
                if validation_result["valid"]:
                    # Reload BIND9 configuration to pick up RPZ changes
                    reload_success = await self.reload_configuration()
                    
                    if reload_success:
                        logger.info(f"Successfully rolled back RPZ zone {rpz_zone} to backup: {backup_id}")
                        return True
                    else:
                        logger.error(f"RPZ rollback succeeded but configuration reload failed for: {rpz_zone}")
                        return False
                else:
                    logger.error(f"Restored RPZ zone file is invalid for {rpz_zone}: {validation_result['errors']}")
                    return False
            else:
                logger.error(f"Failed to restore RPZ zone {rpz_zone} from backup: {backup_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to rollback RPZ zone {rpz_zone} to backup {backup_id}: {e}")
            return False
    
    async def rollback_forwarder_changes(self, backup_id: Optional[str] = None) -> bool:
        """Rollback forwarder configuration changes to a previous backup"""
        logger = get_bind_logger()
        logger.info("Rolling back forwarder configuration changes")
        
        try:
            from .backup_service import BackupService, BackupType
            
            backup_service = BackupService()
            
            # If no specific backup ID provided, find the most recent configuration backup
            if not backup_id:
                backups = await backup_service.list_backups(BackupType.CONFIGURATION, limit=10)
                forwarder_backups = [b for b in backups if "forwarders.conf" in b.original_path]
                
                if not forwarder_backups:
                    logger.error("No forwarder configuration backups found")
                    return False
                
                backup_id = forwarder_backups[0].backup_id
                logger.info(f"Using most recent forwarder configuration backup: {backup_id}")
            
            # Verify backup exists and is valid
            backup_info = await backup_service.get_backup_info(backup_id)
            if not backup_info:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            if not backup_info.get('exists', False):
                logger.error(f"Backup file does not exist: {backup_id}")
                return False
            
            # Create backup of current forwarder configuration before rollback
            forwarder_config_path = self.config_dir / "forwarders.conf"
            if forwarder_config_path.exists():
                await backup_service.create_backup(
                    forwarder_config_path,
                    BackupType.CONFIGURATION,
                    f"Pre-rollback backup of forwarders.conf before restoring {backup_id}"
                )
            
            # Perform the rollback
            success = await backup_service.restore_from_backup(backup_id)
            
            if success:
                # Validate the overall configuration
                config_valid = await self.validate_configuration()
                
                if config_valid:
                    # Reload BIND9 configuration
                    reload_success = await self.reload_configuration()
                    
                    if reload_success:
                        logger.info(f"Successfully rolled back forwarder configuration to backup: {backup_id}")
                        return True
                    else:
                        logger.error("Forwarder rollback succeeded but configuration reload failed")
                        return False
                else:
                    logger.error("Restored forwarder configuration is invalid")
                    return False
            else:
                logger.error(f"Failed to restore forwarder configuration from backup: {backup_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to rollback forwarder configuration to backup {backup_id}: {e}")
            return False
    
    async def get_rollback_candidates(self, rollback_type: str = "all") -> List[Dict[str, Any]]:
        """Get list of available backups that can be used for rollback"""
        logger = get_bind_logger()
        logger.info(f"Getting rollback candidates for type: {rollback_type}")
        
        try:
            from .backup_service import BackupService, BackupType
            
            backup_service = BackupService()
            candidates = []
            
            if rollback_type in ["all", "full"]:
                full_backups = await backup_service.list_backups(BackupType.FULL_CONFIG, limit=20)
                for backup in full_backups:
                    candidates.append({
                        "backup_id": backup.backup_id,
                        "type": "full_configuration",
                        "description": backup.description,
                        "timestamp": backup.timestamp.isoformat(),
                        "size": backup.file_size,
                        "rollback_method": "rollback_configuration"
                    })
            
            if rollback_type in ["all", "zone"]:
                zone_backups = await backup_service.list_backups(BackupType.ZONE_FILE, limit=20)
                for backup in zone_backups:
                    zone_name = Path(backup.original_path).stem.replace("db.", "")
                    candidates.append({
                        "backup_id": backup.backup_id,
                        "type": "zone_file",
                        "zone_name": zone_name,
                        "description": backup.description,
                        "timestamp": backup.timestamp.isoformat(),
                        "size": backup.file_size,
                        "rollback_method": "rollback_zone_changes"
                    })
            
            if rollback_type in ["all", "rpz"]:
                rpz_backups = await backup_service.list_backups(BackupType.RPZ_FILE, limit=20)
                for backup in rpz_backups:
                    rpz_zone = Path(backup.original_path).stem.replace("db.rpz.", "")
                    candidates.append({
                        "backup_id": backup.backup_id,
                        "type": "rpz_file",
                        "rpz_zone": rpz_zone,
                        "description": backup.description,
                        "timestamp": backup.timestamp.isoformat(),
                        "size": backup.file_size,
                        "rollback_method": "rollback_rpz_changes"
                    })
            
            if rollback_type in ["all", "forwarder"]:
                config_backups = await backup_service.list_backups(BackupType.CONFIGURATION, limit=20)
                forwarder_backups = [b for b in config_backups if "forwarders.conf" in b.original_path]
                for backup in forwarder_backups:
                    candidates.append({
                        "backup_id": backup.backup_id,
                        "type": "forwarder_configuration",
                        "description": backup.description,
                        "timestamp": backup.timestamp.isoformat(),
                        "size": backup.file_size,
                        "rollback_method": "rollback_forwarder_changes"
                    })
            
            # Sort by timestamp (newest first)
            candidates.sort(key=lambda x: x["timestamp"], reverse=True)
            
            logger.info(f"Found {len(candidates)} rollback candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to get rollback candidates: {e}")
            return []
    
    async def test_rollback_safety(self, backup_id: str) -> Dict[str, Any]:
        """Test if a rollback would be safe without actually performing it"""
        logger = get_bind_logger()
        logger.info(f"Testing rollback safety for backup: {backup_id}")
        
        try:
            from .backup_service import BackupService
            
            backup_service = BackupService()
            
            # Get backup information
            backup_info = await backup_service.get_backup_info(backup_id)
            if not backup_info:
                return {
                    "safe": False,
                    "errors": ["Backup not found"],
                    "warnings": []
                }
            
            errors = []
            warnings = []
            
            # Check if backup exists and is valid
            if not backup_info.get('exists', False):
                errors.append("Backup file does not exist")
            
            if not backup_info.get('integrity_valid', False):
                errors.append("Backup integrity check failed")
            
            # Check backup age
            backup_timestamp = datetime.fromisoformat(backup_info['timestamp'])
            age_days = (datetime.now() - backup_timestamp).days
            
            if age_days > 30:
                warnings.append(f"Backup is {age_days} days old")
            
            # Check if current configuration is valid before rollback
            current_config_valid = await self.validate_configuration()
            if not current_config_valid:
                warnings.append("Current configuration is already invalid")
            
            # Check available disk space
            backup_path = Path(backup_info['backup_path'])
            if backup_path.exists():
                try:
                    import shutil
                    free_space = shutil.disk_usage(backup_path.parent).free
                    required_space = backup_info['current_size'] * 2  # Need space for backup + restore
                    
                    if free_space < required_space:
                        errors.append(f"Insufficient disk space for rollback (need {required_space}, have {free_space})")
                except Exception:
                    warnings.append("Could not check disk space")
            
            # Check if BIND9 service is running
            service_status = await self.get_service_status()
            if service_status.get("status") != "active":
                warnings.append("BIND9 service is not currently running")
            
            return {
                "safe": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "backup_info": backup_info,
                "estimated_downtime": "30-60 seconds" if len(errors) == 0 else "unknown"
            }
            
        except Exception as e:
            logger.error(f"Failed to test rollback safety for backup {backup_id}: {e}")
            return {
                "safe": False,
                "errors": [f"Safety test failed: {str(e)}"],
                "warnings": []
            }
    
    async def apply_atomic_configuration_update(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Apply configuration changes atomically with automatic rollback on failure"""
        logger = get_bind_logger()
        logger.info("Starting atomic configuration update")
        
        # Track the update process
        update_id = f"atomic_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_id = None
        applied_changes = []
        
        try:
            # Phase 1: Validation
            logger.info("Phase 1: Validating atomic configuration update")
            validation_result = await self.validate_atomic_configuration_update(changes)
            
            if not validation_result["valid"]:
                logger.error("Atomic configuration update validation failed")
                return {
                    "success": False,
                    "phase": "validation",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", []),
                    "update_id": update_id,
                    "backup_id": None,
                    "applied_changes": []
                }
            
            backup_id = validation_result.get("backup_id")
            logger.info(f"Validation passed, backup created: {backup_id}")
            
            # Phase 2: Apply changes atomically
            logger.info("Phase 2: Applying configuration changes")
            
            # Apply zone changes
            if "zones" in changes:
                zone_results = await self._apply_zone_changes_atomic(changes["zones"])
                if not zone_results["success"]:
                    raise Exception(f"Zone changes failed: {zone_results['error']}")
                applied_changes.extend(zone_results["applied"])
            
            # Apply forwarder changes
            if "forwarders" in changes:
                forwarder_results = await self._apply_forwarder_changes_atomic(changes["forwarders"])
                if not forwarder_results["success"]:
                    raise Exception(f"Forwarder changes failed: {forwarder_results['error']}")
                applied_changes.extend(forwarder_results["applied"])
            
            # Apply RPZ changes
            if "rpz" in changes:
                rpz_results = await self._apply_rpz_changes_atomic(changes["rpz"])
                if not rpz_results["success"]:
                    raise Exception(f"RPZ changes failed: {rpz_results['error']}")
                applied_changes.extend(rpz_results["applied"])
            
            # Phase 3: Validate and reload configuration
            logger.info("Phase 3: Validating and reloading configuration")
            
            # Validate the complete configuration
            validation_result = await self.validate_configuration_detailed()
            if not validation_result["valid"]:
                raise Exception(f"Configuration validation failed after changes: {validation_result['errors']}")
            
            # Reload BIND9 configuration
            reload_success = await self.reload_service()
            if not reload_success:
                raise Exception("Failed to reload BIND9 configuration")
            
            # Phase 4: Verify changes are working
            logger.info("Phase 4: Verifying changes are working")
            
            # Test that BIND9 is responding correctly
            service_status = await self.get_service_status()
            if service_status["status"] != "active":
                raise Exception("BIND9 service is not active after configuration update")
            
            logger.info(f"Atomic configuration update completed successfully: {update_id}")
            
            return {
                "success": True,
                "phase": "completed",
                "errors": [],
                "warnings": validation_result.get("warnings", []),
                "update_id": update_id,
                "backup_id": backup_id,
                "applied_changes": applied_changes,
                "changes_count": len(applied_changes)
            }
            
        except Exception as e:
            logger.error(f"Atomic configuration update failed: {e}")
            
            # Attempt rollback
            rollback_success = False
            rollback_errors = []
            
            if backup_id:
                logger.info(f"Attempting rollback to backup: {backup_id}")
                try:
                    rollback_result = await self.rollback_configuration(backup_id)
                    rollback_success = rollback_result["success"]
                    if not rollback_success:
                        rollback_errors = rollback_result.get("errors", [])
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    rollback_errors.append(f"Rollback failed: {str(rollback_error)}")
            
            return {
                "success": False,
                "phase": "failed",
                "errors": [str(e)],
                "warnings": [],
                "update_id": update_id,
                "backup_id": backup_id,
                "applied_changes": applied_changes,
                "rollback_attempted": backup_id is not None,
                "rollback_success": rollback_success,
                "rollback_errors": rollback_errors
            }
    
    async def _apply_zone_changes_atomic(self, zone_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply zone changes atomically"""
        logger = get_bind_logger()
        applied_changes = []
        
        try:
            for zone_change in zone_changes:
                action = zone_change.get("action")
                
                if action == "create":
                    result = await self._apply_zone_creation(zone_change)
                elif action == "update":
                    result = await self._apply_zone_update(zone_change)
                elif action == "delete":
                    result = await self._apply_zone_deletion(zone_change)
                else:
                    raise Exception(f"Unknown zone action: {action}")
                
                if not result["success"]:
                    raise Exception(result["error"])
                
                applied_changes.append({
                    "type": "zone",
                    "action": action,
                    "details": result["details"]
                })
            
            return {
                "success": True,
                "applied": applied_changes,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Zone changes failed: {e}")
            return {
                "success": False,
                "applied": applied_changes,
                "error": str(e)
            }
    
    async def _apply_forwarder_changes_atomic(self, forwarder_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply forwarder changes atomically"""
        logger = get_bind_logger()
        applied_changes = []
        
        try:
            for forwarder_change in forwarder_changes:
                action = forwarder_change.get("action")
                
                if action == "create":
                    result = await self._apply_forwarder_creation(forwarder_change)
                elif action == "update":
                    result = await self._apply_forwarder_update(forwarder_change)
                elif action == "delete":
                    result = await self._apply_forwarder_deletion(forwarder_change)
                else:
                    raise Exception(f"Unknown forwarder action: {action}")
                
                if not result["success"]:
                    raise Exception(result["error"])
                
                applied_changes.append({
                    "type": "forwarder",
                    "action": action,
                    "details": result["details"]
                })
            
            # Regenerate forwarder configuration after all changes
            await self.update_forwarder_configuration()
            
            return {
                "success": True,
                "applied": applied_changes,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Forwarder changes failed: {e}")
            return {
                "success": False,
                "applied": applied_changes,
                "error": str(e)
            }
    
    async def _apply_rpz_changes_atomic(self, rpz_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply RPZ changes atomically"""
        logger = get_bind_logger()
        applied_changes = []
        
        try:
            for rpz_change in rpz_changes:
                action = rpz_change.get("action")
                
                if action == "create":
                    result = await self._apply_rpz_rule_creation(rpz_change)
                elif action == "update":
                    result = await self._apply_rpz_rule_update(rpz_change)
                elif action == "delete":
                    result = await self._apply_rpz_rule_deletion(rpz_change)
                else:
                    raise Exception(f"Unknown RPZ action: {action}")
                
                if not result["success"]:
                    raise Exception(result["error"])
                
                applied_changes.append({
                    "type": "rpz",
                    "action": action,
                    "details": result["details"]
                })
            
            # Regenerate RPZ zone files after all changes
            affected_zones = set()
            for change in applied_changes:
                if "rpz_zone" in change["details"]:
                    affected_zones.add(change["details"]["rpz_zone"])
            
            for rpz_zone in affected_zones:
                await self.update_rpz_zone_file(rpz_zone)
            
            return {
                "success": True,
                "applied": applied_changes,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"RPZ changes failed: {e}")
            return {
                "success": False,
                "applied": applied_changes,
                "error": str(e)
            }
    
    async def _apply_zone_creation(self, zone_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply zone creation change"""
        try:
            if not self.db:
                raise Exception("Database connection required for zone creation")
            
            from ..models.dns import Zone
            from ..schemas.dns import ZoneCreate
            
            # Create zone data from change
            zone_data = ZoneCreate(
                name=zone_change["name"],
                zone_type=zone_change.get("zone_type", "master"),
                email=zone_change.get("email", "admin@localhost"),
                description=zone_change.get("description", ""),
                master_servers=zone_change.get("master_servers"),
                forwarders=zone_change.get("forwarders")
            )
            
            # Create zone in database
            zone = Zone(
                name=zone_data.name,
                zone_type=zone_data.zone_type,
                email=zone_data.email,
                description=zone_data.description,
                master_servers=zone_data.master_servers,
                forwarders=zone_data.forwarders,
                serial=1
            )
            
            self.db.add(zone)
            self.db.commit()
            self.db.refresh(zone)
            
            # Create zone file
            await self.create_zone_file(zone)
            
            return {
                "success": True,
                "details": {
                    "zone_id": zone.id,
                    "zone_name": zone.name,
                    "zone_type": zone.zone_type
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_zone_update(self, zone_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply zone update change"""
        try:
            if not self.db:
                raise Exception("Database connection required for zone update")
            
            from ..models.dns import Zone
            
            zone_id = zone_change.get("id")
            zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
            
            if not zone:
                raise Exception(f"Zone with ID {zone_id} not found")
            
            # Update zone fields
            for field, value in zone_change.items():
                if field != "id" and field != "action" and hasattr(zone, field):
                    setattr(zone, field, value)
            
            # Increment serial number
            zone.serial = (zone.serial or 0) + 1
            
            self.db.commit()
            self.db.refresh(zone)
            
            # Update zone file
            await self.update_zone_file_from_db(zone.id)
            
            return {
                "success": True,
                "details": {
                    "zone_id": zone.id,
                    "zone_name": zone.name,
                    "new_serial": zone.serial
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_zone_deletion(self, zone_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply zone deletion change"""
        try:
            if not self.db:
                raise Exception("Database connection required for zone deletion")
            
            from ..models.dns import Zone
            
            zone_id = zone_change.get("id")
            zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
            
            if not zone:
                # Zone already deleted, consider it successful
                return {
                    "success": True,
                    "details": {
                        "zone_id": zone_id,
                        "note": "Zone already deleted"
                    },
                    "error": None
                }
            
            zone_name = zone.name
            
            # Delete zone file
            await self.delete_zone_file(zone_id)
            
            # Delete zone from database (cascade will handle records)
            self.db.delete(zone)
            self.db.commit()
            
            return {
                "success": True,
                "details": {
                    "zone_id": zone_id,
                    "zone_name": zone_name
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_forwarder_creation(self, forwarder_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply forwarder creation change"""
        try:
            if not self.db:
                raise Exception("Database connection required for forwarder creation")
            
            from ..models.dns import Forwarder
            
            # Create forwarder in database
            forwarder = Forwarder(
                name=forwarder_change["name"],
                domains=forwarder_change["domains"],
                forwarder_type=forwarder_change.get("forwarder_type", "public"),
                servers=forwarder_change["servers"],
                description=forwarder_change.get("description", ""),
                health_check_enabled=forwarder_change.get("health_check_enabled", True)
            )
            
            self.db.add(forwarder)
            self.db.commit()
            self.db.refresh(forwarder)
            
            return {
                "success": True,
                "details": {
                    "forwarder_id": forwarder.id,
                    "forwarder_name": forwarder.name,
                    "domains": forwarder.domains
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_forwarder_update(self, forwarder_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply forwarder update change"""
        try:
            if not self.db:
                raise Exception("Database connection required for forwarder update")
            
            from ..models.dns import Forwarder
            
            forwarder_id = forwarder_change.get("id")
            forwarder = self.db.query(Forwarder).filter(Forwarder.id == forwarder_id).first()
            
            if not forwarder:
                raise Exception(f"Forwarder with ID {forwarder_id} not found")
            
            # Update forwarder fields
            for field, value in forwarder_change.items():
                if field != "id" and field != "action" and hasattr(forwarder, field):
                    setattr(forwarder, field, value)
            
            self.db.commit()
            self.db.refresh(forwarder)
            
            return {
                "success": True,
                "details": {
                    "forwarder_id": forwarder.id,
                    "forwarder_name": forwarder.name,
                    "domains": forwarder.domains
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_forwarder_deletion(self, forwarder_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply forwarder deletion change"""
        try:
            if not self.db:
                raise Exception("Database connection required for forwarder deletion")
            
            from ..models.dns import Forwarder
            
            forwarder_id = forwarder_change.get("id")
            forwarder = self.db.query(Forwarder).filter(Forwarder.id == forwarder_id).first()
            
            if not forwarder:
                # Forwarder already deleted, consider it successful
                return {
                    "success": True,
                    "details": {
                        "forwarder_id": forwarder_id,
                        "note": "Forwarder already deleted"
                    },
                    "error": None
                }
            
            forwarder_name = forwarder.name
            domains = forwarder.domains
            
            # Delete forwarder from database
            self.db.delete(forwarder)
            self.db.commit()
            
            return {
                "success": True,
                "details": {
                    "forwarder_id": forwarder_id,
                    "forwarder_name": forwarder_name,
                    "domains": domains
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_rpz_rule_creation(self, rpz_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply RPZ rule creation change"""
        try:
            if not self.db:
                raise Exception("Database connection required for RPZ rule creation")
            
            from ..models.security import RPZRule
            
            # Create RPZ rule in database
            rpz_rule = RPZRule(
                domain=rpz_change["domain"],
                rpz_zone=rpz_change.get("rpz_zone", "malware"),
                action=rpz_change["action"],
                redirect_target=rpz_change.get("redirect_target"),
                description=rpz_change.get("description", ""),
                source=rpz_change.get("source", "manual")
            )
            
            self.db.add(rpz_rule)
            self.db.commit()
            self.db.refresh(rpz_rule)
            
            return {
                "success": True,
                "details": {
                    "rpz_rule_id": rpz_rule.id,
                    "domain": rpz_rule.domain,
                    "rpz_zone": rpz_rule.rpz_zone,
                    "action": rpz_rule.action
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_rpz_rule_update(self, rpz_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply RPZ rule update change"""
        try:
            if not self.db:
                raise Exception("Database connection required for RPZ rule update")
            
            from ..models.security import RPZRule
            
            rpz_rule_id = rpz_change.get("id")
            rpz_rule = self.db.query(RPZRule).filter(RPZRule.id == rpz_rule_id).first()
            
            if not rpz_rule:
                raise Exception(f"RPZ rule with ID {rpz_rule_id} not found")
            
            # Update RPZ rule fields
            for field, value in rpz_change.items():
                if field != "id" and field != "action" and hasattr(rpz_rule, field):
                    setattr(rpz_rule, field, value)
            
            self.db.commit()
            self.db.refresh(rpz_rule)
            
            return {
                "success": True,
                "details": {
                    "rpz_rule_id": rpz_rule.id,
                    "domain": rpz_rule.domain,
                    "rpz_zone": rpz_rule.rpz_zone,
                    "action": rpz_rule.action
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            }
    
    async def _apply_rpz_rule_deletion(self, rpz_change: Dict[str, Any]) -> Dict[str, Any]:
        """Apply RPZ rule deletion change"""
        try:
            if not self.db:
                raise Exception("Database connection required for RPZ rule deletion")
            
            from ..models.security import RPZRule
            
            rpz_rule_id = rpz_change.get("id")
            rpz_rule = self.db.query(RPZRule).filter(RPZRule.id == rpz_rule_id).first()
            
            if not rpz_rule:
                # RPZ rule already deleted, consider it successful
                return {
                    "success": True,
                    "details": {
                        "rpz_rule_id": rpz_rule_id,
                        "note": "RPZ rule already deleted"
                    },
                    "error": None
                }
            
            domain = rpz_rule.domain
            rpz_zone = rpz_rule.rpz_zone
            
            # Delete RPZ rule from database
            self.db.delete(rpz_rule)
            self.db.commit()
            
            return {
                "success": True,
                "details": {
                    "rpz_rule_id": rpz_rule_id,
                    "domain": domain,
                    "rpz_zone": rpz_zone
                },
                "error": None
            }
            
        except Exception as e:
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "details": {},
                "error": str(e)
            } 
   
    async def execute_atomic_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complete atomic transaction with multiple configuration changes.
        This is the main entry point for atomic configuration updates.
        
        Args:
            transaction_data: Dictionary containing:
                - description: Human-readable description of the transaction
                - changes: Dictionary with zones, forwarders, rpz changes
                - dry_run: If True, only validate without applying changes
                - force_backup: If True, create backup even if no changes
        
        Returns:
            Dictionary with transaction results including success status, 
            backup information, and detailed change results
        """
        logger = get_bind_logger()
        transaction_id = f"transaction_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"Starting atomic transaction: {transaction_id}")
        logger.info(f"Description: {transaction_data.get('description', 'No description provided')}")
        
        try:
            # Extract transaction parameters
            changes = transaction_data.get("changes", {})
            dry_run = transaction_data.get("dry_run", False)
            force_backup = transaction_data.get("force_backup", False)
            description = transaction_data.get("description", f"Atomic transaction {transaction_id}")
            
            # Validate transaction data structure
            validation_result = await self._validate_transaction_structure(transaction_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "transaction_id": transaction_id,
                    "phase": "structure_validation",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                }
            
            # If dry run, only perform validation
            if dry_run:
                logger.info("Performing dry run - validation only")
                
                validation_result = await self.validate_atomic_configuration_update(changes)
                
                return {
                    "success": validation_result["valid"],
                    "transaction_id": transaction_id,
                    "phase": "dry_run_validation",
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", []),
                    "dry_run": True,
                    "changes_validated": validation_result.get("changes_validated", 0),
                    "backup_would_be_created": len(changes) > 0 or force_backup
                }
            
            # Create backup if changes exist or forced
            backup_id = None
            if len(changes) > 0 or force_backup:
                backup_id = await self.create_full_configuration_backup(description)
                if not backup_id:
                    return {
                        "success": False,
                        "transaction_id": transaction_id,
                        "phase": "backup_creation",
                        "errors": ["Failed to create configuration backup"],
                        "warnings": []
                    }
                logger.info(f"Created backup: {backup_id}")
            
            # If no changes, return success
            if len(changes) == 0:
                logger.info("No changes to apply")
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "phase": "completed",
                    "errors": [],
                    "warnings": [],
                    "backup_id": backup_id,
                    "changes_applied": 0,
                    "message": "No changes to apply"
                }
            
            # Apply changes atomically
            result = await self.apply_atomic_configuration_update(changes)
            
            # Enhance result with transaction information
            result["transaction_id"] = transaction_id
            result["description"] = description
            
            if result["success"]:
                logger.info(f"Atomic transaction completed successfully: {transaction_id}")
            else:
                logger.error(f"Atomic transaction failed: {transaction_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Atomic transaction failed with exception: {e}")
            return {
                "success": False,
                "transaction_id": transaction_id,
                "phase": "exception",
                "errors": [f"Transaction failed: {str(e)}"],
                "warnings": [],
                "backup_id": backup_id if 'backup_id' in locals() else None
            }
    
    async def _validate_transaction_structure(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the structure of transaction data"""
        errors = []
        warnings = []
        
        try:
            # Check required fields
            if not isinstance(transaction_data, dict):
                errors.append("Transaction data must be a dictionary")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Validate changes structure
            changes = transaction_data.get("changes", {})
            if not isinstance(changes, dict):
                errors.append("Changes must be a dictionary")
            else:
                # Validate each change type
                for change_type in ["zones", "forwarders", "rpz"]:
                    if change_type in changes:
                        change_list = changes[change_type]
                        if not isinstance(change_list, list):
                            errors.append(f"{change_type} changes must be a list")
                        else:
                            # Validate each change item
                            for i, change_item in enumerate(change_list):
                                if not isinstance(change_item, dict):
                                    errors.append(f"{change_type}[{i}] must be a dictionary")
                                elif "action" not in change_item:
                                    errors.append(f"{change_type}[{i}] missing required 'action' field")
                                elif change_item["action"] not in ["create", "update", "delete"]:
                                    errors.append(f"{change_type}[{i}] has invalid action: {change_item['action']}")
            
            # Validate optional fields
            dry_run = transaction_data.get("dry_run")
            if dry_run is not None and not isinstance(dry_run, bool):
                warnings.append("dry_run should be a boolean value")
            
            force_backup = transaction_data.get("force_backup")
            if force_backup is not None and not isinstance(force_backup, bool):
                warnings.append("force_backup should be a boolean value")
            
            description = transaction_data.get("description")
            if description is not None and not isinstance(description, str):
                warnings.append("description should be a string")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to validate transaction structure: {str(e)}"],
                "warnings": warnings
            }
    
    async def get_atomic_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get the status of an atomic transaction.
        This method can be used to check the status of ongoing or completed transactions.
        """
        logger = get_bind_logger()
        
        try:
            # For now, we don't persist transaction status, but this could be enhanced
            # to store transaction history in the database for audit purposes
            
            return {
                "transaction_id": transaction_id,
                "status": "unknown",
                "message": "Transaction status tracking not yet implemented",
                "note": "This feature can be enhanced to track transaction history"
            }
            
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return {
                "transaction_id": transaction_id,
                "status": "error",
                "message": f"Failed to get transaction status: {str(e)}"
            }
    
    async def list_available_backups_for_rollback(self) -> Dict[str, Any]:
        """
        List all available configuration backups that can be used for rollback.
        This provides a convenient way to see rollback options.
        """
        logger = get_bind_logger()
        
        try:
            from .backup_service import BackupService
            backup_service = BackupService()
            
            # Get all configuration backups
            backups = await backup_service.list_backups(backup_type="configuration")
            
            # Filter and format for rollback use
            rollback_candidates = []
            for backup in backups:
                # Validate that backup is suitable for rollback
                validation = await self._validate_rollback_capability(backup["id"])
                
                rollback_candidates.append({
                    "backup_id": backup["id"],
                    "description": backup.get("description", ""),
                    "created_at": backup.get("created_at"),
                    "size": backup.get("size", 0),
                    "rollback_ready": validation["valid"],
                    "rollback_issues": validation.get("errors", [])
                })
            
            # Sort by creation date, newest first
            rollback_candidates.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return {
                "success": True,
                "backups": rollback_candidates,
                "total_backups": len(rollback_candidates),
                "rollback_ready_count": len([b for b in rollback_candidates if b["rollback_ready"]])
            }
            
        except Exception as e:
            logger.error(f"Failed to list rollback backups: {e}")
            return {
                "success": False,
                "error": str(e),
                "backups": []
            }
    
    async def create_atomic_configuration_checkpoint(self, checkpoint_name: str) -> Dict[str, Any]:
        """
        Create a named checkpoint of the current configuration.
        This is useful before making major changes to have a known good state to return to.
        """
        logger = get_bind_logger()
        
        try:
            # Validate current configuration before creating checkpoint
            validation_result = await self.validate_configuration_detailed()
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Cannot create checkpoint - current configuration is invalid",
                    "validation_errors": validation_result["errors"]
                }
            
            # Create backup with checkpoint description
            description = f"Configuration checkpoint: {checkpoint_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            backup_id = await self.create_full_configuration_backup(description)
            
            if not backup_id:
                return {
                    "success": False,
                    "error": "Failed to create configuration backup for checkpoint"
                }
            
            logger.info(f"Created configuration checkpoint '{checkpoint_name}' with backup ID: {backup_id}")
            
            return {
                "success": True,
                "checkpoint_name": checkpoint_name,
                "backup_id": backup_id,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "configuration_valid": True
            }
            
        except Exception as e:
            logger.error(f"Failed to create configuration checkpoint: {e}")
            return {
                "success": False,
                "error": str(e)
            }