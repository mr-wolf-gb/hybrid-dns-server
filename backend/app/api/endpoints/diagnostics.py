"""
DNS Diagnostic and Testing Tools API
"""

import asyncio
import socket
import subprocess
import time
import platform
import dns.resolver
import dns.query
import dns.message
import requests
import psutil
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
import ipaddress
import re
from urllib.parse import urlparse

from app.core.auth_context import get_current_user
from app.models.auth import User
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Request/Response Models
class DNSLookupRequest(BaseModel):
    hostname: str = Field(..., description="Hostname to resolve")
    record_type: str = Field(default="A", description="DNS record type (A, AAAA, CNAME, MX, TXT, etc.)")
    nameserver: Optional[str] = Field(None, description="Specific nameserver to query")
    timeout: int = Field(default=5, description="Query timeout in seconds")

class PingRequest(BaseModel):
    target: str = Field(..., description="Target hostname or IP address")
    count: int = Field(default=4, description="Number of ping packets")
    timeout: int = Field(default=5, description="Ping timeout in seconds")

class ZoneTestRequest(BaseModel):
    zone_name: str = Field(..., description="Zone name to test")
    nameserver: Optional[str] = Field(None, description="Nameserver to test against")

class ForwarderTestRequest(BaseModel):
    domain: str = Field(..., description="Domain to test forwarding")
    forwarder_ip: str = Field(..., description="Forwarder IP address")
    expected_result: Optional[str] = Field(None, description="Expected result for validation")

class ThreatTestRequest(BaseModel):
    domain: str = Field(..., description="Domain to test for threats")
    url: Optional[str] = Field(None, description="Full URL to test")

class DNSLookupResponse(BaseModel):
    hostname: str
    record_type: str
    nameserver: Optional[str]
    success: bool
    results: List[str]
    response_time: float
    error: Optional[str]
    additional_info: Dict[str, Any]

class PingResponse(BaseModel):
    target: str
    success: bool
    packets_sent: int
    packets_received: int
    packet_loss: float
    min_time: Optional[float]
    max_time: Optional[float]
    avg_time: Optional[float]
    error: Optional[str]
    raw_output: str

class ZoneTestResponse(BaseModel):
    zone_name: str
    nameserver: Optional[str]
    success: bool
    soa_record: Optional[Dict[str, Any]]
    ns_records: List[str]
    zone_transfer_allowed: bool
    dnssec_enabled: bool
    error: Optional[str]

class ForwarderTestResponse(BaseModel):
    domain: str
    forwarder_ip: str
    success: bool
    resolved_ip: Optional[str]
    response_time: float
    forwarding_working: bool
    error: Optional[str]

class ThreatTestResponse(BaseModel):
    domain: str
    url: Optional[str]
    is_blocked: bool
    threat_category: Optional[str]
    rpz_rule_matched: Optional[str]
    dns_response: Optional[str]
    reputation_score: Optional[float]
    error: Optional[str]

# Utility Functions
def validate_hostname(hostname: str) -> bool:
    """Validate hostname format"""
    if len(hostname) > 253:
        return False
    
    # Remove trailing dot if present
    if hostname.endswith('.'):
        hostname = hostname[:-1]
    
    # Check each label
    labels = hostname.split('.')
    for label in labels:
        if len(label) == 0 or len(label) > 63:
            return False
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
            return False
    
    return True

def validate_ip_address(ip: str) -> bool:
    """Validate IP address format"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

async def run_command(command: List[str], timeout: int = 10) -> tuple[bool, str, str]:
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
        
        return (
            process.returncode == 0,
            stdout.decode('utf-8', errors='ignore'),
            stderr.decode('utf-8', errors='ignore')
        )
    except asyncio.TimeoutError:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

# API Endpoints
@router.post("/dns-lookup", response_model=DNSLookupResponse)
async def dns_lookup(
    request: DNSLookupRequest,
    current_user: User = Depends(get_current_user)
):
    """Perform DNS lookup with detailed results"""
    start_time = time.time()
    
    try:
        # Validate hostname
        if not validate_hostname(request.hostname):
            raise HTTPException(status_code=400, detail="Invalid hostname format")
        
        # Create resolver
        resolver = dns.resolver.Resolver()
        if request.nameserver:
            if not validate_ip_address(request.nameserver):
                raise HTTPException(status_code=400, detail="Invalid nameserver IP address")
            resolver.nameservers = [request.nameserver]
        
        resolver.timeout = request.timeout
        resolver.lifetime = request.timeout
        
        # Perform lookup
        try:
            answers = resolver.resolve(request.hostname, request.record_type)
            results = [str(answer) for answer in answers]
            
            # Additional info
            additional_info = {
                "ttl": answers.rrset.ttl,
                "canonical_name": str(answers.canonical_name),
                "nameserver_used": resolver.nameservers[0] if resolver.nameservers else "system_default"
            }
            
            response_time = time.time() - start_time
            
            return DNSLookupResponse(
                hostname=request.hostname,
                record_type=request.record_type,
                nameserver=request.nameserver,
                success=True,
                results=results,
                response_time=response_time,
                error=None,
                additional_info=additional_info
            )
            
        except dns.resolver.NXDOMAIN:
            return DNSLookupResponse(
                hostname=request.hostname,
                record_type=request.record_type,
                nameserver=request.nameserver,
                success=False,
                results=[],
                response_time=time.time() - start_time,
                error="Domain does not exist (NXDOMAIN)",
                additional_info={}
            )
        except dns.resolver.NoAnswer:
            return DNSLookupResponse(
                hostname=request.hostname,
                record_type=request.record_type,
                nameserver=request.nameserver,
                success=False,
                results=[],
                response_time=time.time() - start_time,
                error=f"No {request.record_type} record found",
                additional_info={}
            )
        except dns.resolver.Timeout:
            return DNSLookupResponse(
                hostname=request.hostname,
                record_type=request.record_type,
                nameserver=request.nameserver,
                success=False,
                results=[],
                response_time=time.time() - start_time,
                error="DNS query timed out",
                additional_info={}
            )
            
    except Exception as e:
        logger.error(f"DNS lookup error: {str(e)}")
        return DNSLookupResponse(
            hostname=request.hostname,
            record_type=request.record_type,
            nameserver=request.nameserver,
            success=False,
            results=[],
            response_time=time.time() - start_time,
            error=str(e),
            additional_info={}
        )

@router.post("/ping", response_model=PingResponse)
async def ping_test(
    request: PingRequest,
    current_user: User = Depends(get_current_user)
):
    """Perform ping test"""
    try:
        # Validate target
        if not (validate_hostname(request.target) or validate_ip_address(request.target)):
            raise HTTPException(status_code=400, detail="Invalid target hostname or IP address")
        
        # Build ping command based on OS
        import platform
        system = platform.system().lower()
        
        if system == "windows":
            command = ["ping", "-n", str(request.count), "-w", str(request.timeout * 1000), request.target]
        else:
            command = ["ping", "-c", str(request.count), "-W", str(request.timeout), request.target]
        
        success, stdout, stderr = await run_command(command, timeout=request.timeout + 10)
        
        # Parse ping results
        packets_sent = request.count
        packets_received = 0
        min_time = None
        max_time = None
        avg_time = None
        
        if success and stdout:
            # Parse output for statistics
            lines = stdout.split('\n')
            
            for line in lines:
                # Windows format
                if "Packets: Sent =" in line:
                    parts = line.split(',')
                    for part in parts:
                        if "Received =" in part:
                            packets_received = int(part.split('=')[1].strip().split()[0])
                
                # Linux format
                if "packets transmitted" in line:
                    parts = line.split(',')
                    packets_received = int(parts[1].strip().split()[0])
                
                # Time statistics
                if "min/avg/max" in line or "Minimum/Maximum/Average" in line:
                    if "=" in line:
                        times = line.split('=')[1].strip().replace('ms', '').split('/')
                        if len(times) >= 3:
                            min_time = float(times[0])
                            avg_time = float(times[1])
                            max_time = float(times[2])
        
        packet_loss = ((packets_sent - packets_received) / packets_sent) * 100 if packets_sent > 0 else 100
        
        return PingResponse(
            target=request.target,
            success=success and packets_received > 0,
            packets_sent=packets_sent,
            packets_received=packets_received,
            packet_loss=packet_loss,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            error=stderr if stderr else None,
            raw_output=stdout
        )
        
    except Exception as e:
        logger.error(f"Ping test error: {str(e)}")
        return PingResponse(
            target=request.target,
            success=False,
            packets_sent=0,
            packets_received=0,
            packet_loss=100.0,
            min_time=None,
            max_time=None,
            avg_time=None,
            error=str(e),
            raw_output=""
        )

@router.post("/zone-test", response_model=ZoneTestResponse)
async def zone_test(
    request: ZoneTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Test DNS zone configuration and health"""
    try:
        # Validate zone name
        if not validate_hostname(request.zone_name):
            raise HTTPException(status_code=400, detail="Invalid zone name format")
        
        # Create resolver
        resolver = dns.resolver.Resolver()
        if request.nameserver:
            if not validate_ip_address(request.nameserver):
                raise HTTPException(status_code=400, detail="Invalid nameserver IP address")
            resolver.nameservers = [request.nameserver]
        
        soa_record = None
        ns_records = []
        zone_transfer_allowed = False
        dnssec_enabled = False
        error = None
        success = True
        
        try:
            # Test SOA record
            try:
                soa_answers = resolver.resolve(request.zone_name, 'SOA')
                if soa_answers:
                    soa = soa_answers[0]
                    soa_record = {
                        "primary_ns": str(soa.mname),
                        "admin_email": str(soa.rname),
                        "serial": soa.serial,
                        "refresh": soa.refresh,
                        "retry": soa.retry,
                        "expire": soa.expire,
                        "minimum": soa.minimum
                    }
            except Exception as e:
                error = f"SOA lookup failed: {str(e)}"
                success = False
            
            # Test NS records
            try:
                ns_answers = resolver.resolve(request.zone_name, 'NS')
                ns_records = [str(ns) for ns in ns_answers]
            except Exception as e:
                if not error:
                    error = f"NS lookup failed: {str(e)}"
                success = False
            
            # Test zone transfer (AXFR)
            if request.nameserver:
                try:
                    zone_transfer_query = dns.query.xfr(request.nameserver, request.zone_name)
                    zone_transfer_allowed = True
                except Exception:
                    zone_transfer_allowed = False
            
            # Test DNSSEC
            try:
                dnskey_answers = resolver.resolve(request.zone_name, 'DNSKEY')
                dnssec_enabled = len(dnskey_answers) > 0
            except Exception:
                dnssec_enabled = False
                
        except Exception as e:
            error = str(e)
            success = False
        
        return ZoneTestResponse(
            zone_name=request.zone_name,
            nameserver=request.nameserver,
            success=success,
            soa_record=soa_record,
            ns_records=ns_records,
            zone_transfer_allowed=zone_transfer_allowed,
            dnssec_enabled=dnssec_enabled,
            error=error
        )
        
    except Exception as e:
        logger.error(f"Zone test error: {str(e)}")
        return ZoneTestResponse(
            zone_name=request.zone_name,
            nameserver=request.nameserver,
            success=False,
            soa_record=None,
            ns_records=[],
            zone_transfer_allowed=False,
            dnssec_enabled=False,
            error=str(e)
        )

@router.post("/forwarder-test", response_model=ForwarderTestResponse)
async def forwarder_test(
    request: ForwarderTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Test DNS forwarder configuration"""
    start_time = time.time()
    
    try:
        # Validate inputs
        if not validate_hostname(request.domain):
            raise HTTPException(status_code=400, detail="Invalid domain format")
        
        if not validate_ip_address(request.forwarder_ip):
            raise HTTPException(status_code=400, detail="Invalid forwarder IP address")
        
        # Create resolver with specific forwarder
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [request.forwarder_ip]
        resolver.timeout = 5
        resolver.lifetime = 5
        
        try:
            # Perform lookup through forwarder
            answers = resolver.resolve(request.domain, 'A')
            resolved_ip = str(answers[0]) if answers else None
            response_time = time.time() - start_time
            
            # Check if forwarding is working
            forwarding_working = resolved_ip is not None
            if request.expected_result:
                forwarding_working = forwarding_working and (resolved_ip == request.expected_result)
            
            return ForwarderTestResponse(
                domain=request.domain,
                forwarder_ip=request.forwarder_ip,
                success=True,
                resolved_ip=resolved_ip,
                response_time=response_time,
                forwarding_working=forwarding_working,
                error=None
            )
            
        except Exception as e:
            return ForwarderTestResponse(
                domain=request.domain,
                forwarder_ip=request.forwarder_ip,
                success=False,
                resolved_ip=None,
                response_time=time.time() - start_time,
                forwarding_working=False,
                error=str(e)
            )
            
    except Exception as e:
        logger.error(f"Forwarder test error: {str(e)}")
        return ForwarderTestResponse(
            domain=request.domain,
            forwarder_ip=request.forwarder_ip,
            success=False,
            resolved_ip=None,
            response_time=time.time() - start_time,
            forwarding_working=False,
            error=str(e)
        )

@router.post("/threat-test", response_model=ThreatTestResponse)
async def threat_test(
    request: ThreatTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Test domain/URL for threats and RPZ blocking"""
    try:
        # Validate domain
        if not validate_hostname(request.domain):
            raise HTTPException(status_code=400, detail="Invalid domain format")
        
        is_blocked = False
        threat_category = None
        rpz_rule_matched = None
        dns_response = None
        reputation_score = None
        error = None
        
        try:
            # Test DNS resolution to check for RPZ blocking
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5
            
            try:
                answers = resolver.resolve(request.domain, 'A')
                dns_response = str(answers[0]) if answers else None
                
                # Check if response indicates blocking (common RPZ responses)
                blocked_ips = ['127.0.0.1', '0.0.0.0', '::1']
                if dns_response in blocked_ips:
                    is_blocked = True
                    threat_category = "RPZ_BLOCKED"
                    
            except dns.resolver.NXDOMAIN:
                # Domain doesn't exist - could be blocked or genuinely non-existent
                dns_response = "NXDOMAIN"
                # Additional check needed to determine if it's blocked
                
            except Exception as dns_error:
                dns_response = f"DNS_ERROR: {str(dns_error)}"
            
            # If URL is provided, do additional URL-based checks
            if request.url:
                try:
                    parsed_url = urlparse(request.url)
                    if not parsed_url.scheme:
                        request.url = f"http://{request.url}"
                    
                    # Simple reputation check (in production, integrate with threat intelligence APIs)
                    # This is a placeholder - integrate with actual threat intelligence services
                    reputation_score = 0.5  # Neutral score
                    
                except Exception as url_error:
                    error = f"URL parsing error: {str(url_error)}"
            
            # Check against local RPZ rules (this would integrate with your RPZ service)
            # For now, this is a placeholder
            if is_blocked:
                rpz_rule_matched = f"rpz.{request.domain}"
                
        except Exception as e:
            error = str(e)
        
        return ThreatTestResponse(
            domain=request.domain,
            url=request.url,
            is_blocked=is_blocked,
            threat_category=threat_category,
            rpz_rule_matched=rpz_rule_matched,
            dns_response=dns_response,
            reputation_score=reputation_score,
            error=error
        )
        
    except Exception as e:
        logger.error(f"Threat test error: {str(e)}")
        return ThreatTestResponse(
            domain=request.domain,
            url=request.url,
            is_blocked=False,
            threat_category=None,
            rpz_rule_matched=None,
            dns_response=None,
            reputation_score=None,
            error=str(e)
        )

@router.get("/network-info")
async def get_network_info(current_user: User = Depends(get_current_user)):
    """Get network configuration information"""
    try:
        info = {}
        
        # Get system DNS servers
        try:
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                success, stdout, stderr = await run_command(["nslookup", "localhost"])
                if success and stdout:
                    lines = stdout.split('\n')
                    for line in lines:
                        if "Address:" in line and "#53" in line:
                            dns_server = line.split("Address:")[1].strip().replace("#53", "")
                            info["system_dns"] = dns_server
                            break
            else:
                # Linux/Unix
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        content = f.read()
                        dns_servers = []
                        for line in content.split('\n'):
                            if line.strip().startswith('nameserver'):
                                dns_servers.append(line.split()[1])
                        info["system_dns_servers"] = dns_servers
                except Exception:
                    pass
                    
        except Exception as e:
            info["dns_error"] = str(e)
        
        # Get network interfaces
        try:
            import psutil
            interfaces = {}
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info = []
                for addr in addrs:
                    if addr.family == socket.AF_INET:  # IPv4
                        interface_info.append({
                            "type": "IPv4",
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
                    elif addr.family == socket.AF_INET6:  # IPv6
                        interface_info.append({
                            "type": "IPv6",
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
                if interface_info:
                    interfaces[interface] = interface_info
            info["network_interfaces"] = interfaces
            
        except Exception as e:
            info["interface_error"] = str(e)
        
        return {"success": True, "network_info": info}
        
    except Exception as e:
        logger.error(f"Network info error: {str(e)}")
        return {"success": False, "error": str(e)}