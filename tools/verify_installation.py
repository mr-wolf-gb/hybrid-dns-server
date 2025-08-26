#!/usr/bin/env python3
"""
Installation verification script for Hybrid DNS Server
Run this after installation to verify all components are working
"""

import requests
import subprocess
import sys
import time
import json
from pathlib import Path

def check_service_status(service_name: str) -> bool:
    """Check if a systemd service is running"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0 and result.stdout.strip() == "active"
    except Exception:
        return False

def check_port_listening(port: int) -> bool:
    """Check if a port is listening"""
    try:
        result = subprocess.run(
            ["netstat", "-ln"],
            capture_output=True,
            text=True
        )
        return f":{port}" in result.stdout
    except Exception:
        return False

def check_api_health(base_url: str) -> bool:
    """Check if the API is responding"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def check_api_docs(base_url: str) -> bool:
    """Check if API documentation is accessible"""
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def check_bind9_installation() -> dict:
    """Check BIND9 installation and configuration"""
    results = {
        "bind9_service": False,
        "bind9_commands": {},
        "config_files": {},
        "rpz_policy_file": False,
        "dns_resolution": False
    }
    
    # Check BIND9 service
    results["bind9_service"] = check_service_status("bind9")
    
    # Check BIND9 commands
    commands = ["named", "rndc", "named-checkconf", "named-checkzone"]
    for cmd in commands:
        try:
            result = subprocess.run(["which", cmd], capture_output=True, text=True)
            results["bind9_commands"][cmd] = result.returncode == 0
        except Exception:
            results["bind9_commands"][cmd] = False
    
    # Check configuration files
    config_files = [
        "/etc/bind/named.conf",
        "/etc/bind/named.conf.options",
        "/etc/bind/named.conf.local",
        "/etc/bind/rpz-policy.conf"
    ]
    
    for config_file in config_files:
        results["config_files"][config_file] = Path(config_file).exists()
    
    # Check RPZ policy file specifically
    results["rpz_policy_file"] = Path("/etc/bind/rpz-policy.conf").exists()
    
    # Test DNS resolution
    try:
        result = subprocess.run(
            ["dig", "@localhost", "google.com", "+short"],
            capture_output=True,
            text=True,
            timeout=5
        )
        results["dns_resolution"] = result.returncode == 0 and result.stdout.strip()
    except Exception:
        results["dns_resolution"] = False
    
    return results

def print_bind9_status(bind9_results: dict):
    """Print BIND9 status in a readable format"""
    print("\n=== BIND9 Status ===")
    
    # Service status
    status = "✓ Running" if bind9_results["bind9_service"] else "✗ Not running"
    print(f"BIND9 Service: {status}")
    
    # Commands
    print("\nBIND9 Commands:")
    for cmd, available in bind9_results["bind9_commands"].items():
        status = "✓" if available else "✗"
        print(f"  {status} {cmd}")
    
    # Configuration files
    print("\nConfiguration Files:")
    for config_file, exists in bind9_results["config_files"].items():
        status = "✓" if exists else "✗"
        print(f"  {status} {config_file}")
    
    # DNS resolution test
    dns_status = "✓ Working" if bind9_results["dns_resolution"] else "✗ Failed"
    print(f"\nDNS Resolution Test: {dns_status}")
    
    # Overall assessment
    missing_commands = sum(1 for available in bind9_results["bind9_commands"].values() if not available)
    missing_configs = sum(1 for exists in bind9_results["config_files"].values() if not exists)
    
    if missing_commands > 0 or missing_configs > 0 or not bind9_results["bind9_service"]:
        print(f"\n⚠ BIND9 Issues Detected:")
        if missing_commands > 0:
            print(f"  - {missing_commands} BIND9 commands missing")
        if missing_configs > 0:
            print(f"  - {missing_configs} configuration files missing")
        if not bind9_results["bind9_service"]:
            print("  - BIND9 service not running")
        print("\n  Run: sudo apt install bind9 bind9utils bind9-doc dnsutils")
        print("  Then: sudo systemctl enable bind9 && sudo systemctl start bind9")
    else:
        print("\n✓ BIND9 is properly installed and configured")
    except Exception:
        return False

def check_bind9_config() -> bool:
    """Check BIND9 configuration"""
    try:
        result = subprocess.run(
            ["named-checkconf"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_database_connection(base_url: str) -> bool:
    """Check database connection through API"""
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def main():
    print("🔍 Hybrid DNS Server Installation Verification")
    print("=" * 60)
    
    base_url = "http://localhost:8000/api"
    
    # Check services
    print("\n📋 Service Status:")
    services = [
        "hybrid-dns-backend",
        "bind9",
        "nginx"  # If using nginx
    ]
    
    for service in services:
        status = check_service_status(service)
        icon = "✅" if status else "❌"
        print(f"  {icon} {service}: {'Running' if status else 'Not running'}")
    
    # Check ports
    print("\n🔌 Port Status:")
    ports = [
        (8000, "FastAPI Backend"),
        (53, "BIND9 DNS"),
        (80, "HTTP (nginx)"),
        (443, "HTTPS (nginx)")
    ]
    
    for port, description in ports:
        status = check_port_listening(port)
        icon = "✅" if status else "❌"
        print(f"  {icon} Port {port} ({description}): {'Listening' if status else 'Not listening'}")
    
    # Check BIND9 installation
    bind9_results = check_bind9_installation()
    print_bind9_status(bind9_results)
    
    # Check API health
    print("\n🏥 API Health:")
    
    # Basic health check
    health_status = check_api_health(base_url)
    icon = "✅" if health_status else "❌"
    print(f"  {icon} API Health Endpoint: {'Responding' if health_status else 'Not responding'}")
    
    # Database connection
    db_status = check_database_connection(base_url)
    icon = "✅" if db_status else "❌"
    print(f"  {icon} Database Connection: {'Connected' if db_status else 'Not connected'}")
    
    # API documentation
    docs_status = check_api_docs(base_url)
    icon = "✅" if docs_status else "❌"
    print(f"  {icon} API Documentation: {'Accessible' if docs_status else 'Not accessible'}")
    
    # Check BIND9 configuration
    print("\n🔧 BIND9 Configuration:")
    bind_config_status = check_bind9_config()
    icon = "✅" if bind_config_status else "❌"
    print(f"  {icon} BIND9 Config: {'Valid' if bind_config_status else 'Invalid'}")
    
    # Check file permissions
    print("\n📁 File Permissions:")
    important_paths = [
        "/etc/bind/",
        "/var/log/bind/",
        "/opt/hybrid-dns-server/",
        "/var/log/hybrid-dns/"
    ]
    
    for path in important_paths:
        if Path(path).exists():
            print(f"  ✅ {path}: Exists")
        else:
            print(f"  ❌ {path}: Missing")
    
    # Overall status
    print("\n" + "=" * 60)
    
    all_checks = [
        check_service_status("hybrid-dns-backend"),
        check_service_status("bind9"),
        check_port_listening(8000),
        check_port_listening(53),
        health_status,
        db_status,
        bind_config_status
    ]
    
    if all(all_checks):
        print("🎉 Installation verification PASSED! All components are working correctly.")
        print("\n📝 Next steps:")
        print("  1. Access the web interface at http://your-server-ip")
        print("  2. Login with your admin credentials")
        print("  3. Create your first DNS zone")
        print("  4. Run the API test: python3 test_zone_records_api.py")
    else:
        print("❌ Installation verification FAILED! Some components need attention.")
        print("\n🔧 Troubleshooting:")
        print("  1. Check service logs: journalctl -u hybrid-dns-backend -f")
        print("  2. Check BIND9 logs: tail -f /var/log/bind/bind.log")
        print("  3. Verify configuration files")
        print("  4. Check firewall settings")
    
    return 0 if all(all_checks) else 1

if __name__ == "__main__":
    sys.exit(main())