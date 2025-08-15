"""
BIND9 service management and configuration
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ..core.config import get_settings
from ..core.logging_config import get_bind_logger


class BindService:
    """BIND9 service management"""
    
    def __init__(self):
        settings = get_settings()
        self.service_name = settings.BIND9_SERVICE_NAME
        self.config_dir = settings.config_dir
        self.zones_dir = settings.zones_dir
        self.rpz_dir = settings.rpz_dir
    
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