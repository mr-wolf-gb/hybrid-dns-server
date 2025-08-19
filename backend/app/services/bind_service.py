"""
BIND9 service management and configuration
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

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
                "zones_loaded": 0,  # TODO: Implement zone counting
                "cache_size": 0  # TODO: Implement cache size retrieval
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
            result = await self._run_command(["rndc", "reload"])
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
        """Validate BIND9 configuration"""
        logger = get_bind_logger()
        try:
            result = await self._run_command(["named-checkconf"])
            is_valid = result["returncode"] == 0
            
            if not is_valid:
                logger.error(f"BIND9 configuration validation failed: {result['stderr']}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to validate BIND9 configuration: {e}")
            return False
    
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
            result = await self._run_command(["rndc", "flush"])
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
        """Run system command asynchronously"""
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
    
    # Zone management methods
    async def create_zone_file(self, zone: Zone) -> bool:
        """Create zone file for a zone"""
        logger = get_bind_logger()
        logger.info(f"Creating zone file for zone: {zone.name}")
        
        try:
            # Ensure zones directory exists
            self.zones_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate zone file path if not set
            if not zone.file_path:
                zone.file_path = str(self.zones_dir / f"db.{zone.name}")
            
            zone_file_path = Path(zone.file_path)
            
            # Get zone records from database if available
            records = []
            if self.db:
                records = self.db.query(DNSRecord).filter(
                    DNSRecord.zone_id == zone.id,
                    DNSRecord.is_active == True
                ).all()
            
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
            
            # Set appropriate permissions (readable by BIND9)
            zone_file_path.chmod(0o644)
            
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
    
    async def reload_zone(self, zone_id: int) -> bool:
        """Reload specific zone"""
        logger = get_bind_logger()
        logger.info(f"Reloading zone ID: {zone_id}")
        
        try:
            if not self.db:
                logger.warning("No database connection, falling back to full reload")
                return await self.reload_service()
            
            # Get zone name from database
            zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
            if not zone:
                logger.error(f"Zone {zone_id} not found")
                return False
            
            # Reload specific zone using rndc
            result = await self._run_command(["rndc", "reload", zone.name])
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
        """Validate zone configuration"""
        logger = get_bind_logger()
        logger.info(f"Validating zone: {zone.name}")
        
        errors = []
        warnings = []
        
        try:
            # Check if zone file exists
            if zone.file_path:
                zone_file_path = Path(zone.file_path)
                if not zone_file_path.exists():
                    errors.append(f"Zone file does not exist: {zone_file_path}")
                else:
                    # Use named-checkzone to validate the zone file
                    result = await self._run_command([
                        "named-checkzone", 
                        zone.name, 
                        str(zone_file_path)
                    ])
                    
                    if result["returncode"] != 0:
                        errors.append(f"Zone validation failed: {result['stderr']}")
                    else:
                        logger.info(f"Zone {zone.name} validation passed")
            else:
                warnings.append("Zone file path not set")
            
            # Additional validation checks
            if zone.zone_type == "slave" and not zone.master_servers:
                warnings.append("Slave zone should have master servers configured")
            
            if zone.zone_type == "forward" and not zone.forwarders:
                warnings.append("Forward zone should have forwarders configured")
            
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
        """Update forwarder configuration (stub implementation)"""
        logger = get_bind_logger()
        logger.info("Updating forwarder configuration")
        # TODO: Implement forwarder configuration update
        return True
    
    async def update_rpz_zone_file(self, rpz_zone: str) -> bool:
        """Update RPZ zone file (stub implementation)"""
        logger = get_bind_logger()
        logger.info(f"Updating RPZ zone file: {rpz_zone}")
        # TODO: Implement RPZ zone file update
        return True
    
    # Helper methods for zone file generation
    async def _generate_master_zone_file(self, zone: Zone, records: List[DNSRecord]) -> str:
        """Generate master zone file content using Jinja2 template"""
        logger = get_bind_logger()
        
        try:
            # Determine if this is a reverse zone
            is_reverse_zone = (
                zone.name.endswith('.in-addr.arpa') or 
                zone.name.endswith('.ip6.arpa')
            )
            
            # Select appropriate template
            template_name = "reverse_zone.j2" if is_reverse_zone else "zone_file.j2"
            template = self.jinja_env.get_template(template_name)
            
            # Render the template
            content = template.render(
                zone=zone,
                records=records,
                generated_at=datetime.now()
            )
            
            logger.debug(f"Generated zone file content for {zone.name} using template {template_name}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate master zone file for {zone.name}: {e}")
            raise
    
    async def _generate_slave_zone_file(self, zone: Zone) -> str:
        """Generate slave zone file content (minimal placeholder)"""
        logger = get_bind_logger()
        
        try:
            template = self.jinja_env.get_template("slave_zone.j2")
            content = template.render(
                zone=zone,
                generated_at=datetime.now()
            )
            
            logger.debug(f"Generated slave zone file content for {zone.name}")
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
            
            # Set appropriate permissions
            self.zones_dir.chmod(0o755)
            self.rpz_dir.chmod(0o755)
            
            logger.debug("Zone directories ensured")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure zone directories: {e}")
            return False
    
    async def _backup_zone_file(self, zone_file_path: Path) -> bool:
        """Create a backup of existing zone file before modification"""
        logger = get_bind_logger()
        
        try:
            if zone_file_path.exists():
                backup_path = zone_file_path.with_suffix(f"{zone_file_path.suffix}.backup.{int(datetime.now().timestamp())}")
                zone_file_path.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")
                return True
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup zone file {zone_file_path}: {e}")
            return False
    
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
            raise ValueError("Invalid email address for SOA record")
        
        # Replace @ with . and ensure trailing dot
        formatted = email.replace('@', '.')
        if not formatted.endswith('.'):
            formatted += '.'
        
        return formatted
    
    def validate_soa_parameters(self, zone: Zone) -> Dict[str, Any]:
        """Validate SOA record parameters"""
        errors = []
        warnings = []
        
        # Validate email
        if not zone.email or '@' not in zone.email:
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
                "named-checkzone", 
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