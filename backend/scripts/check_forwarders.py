#!/usr/bin/env python3
"""
Script to check forwarder configuration and health settings
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_database_session
from app.services.forwarder_service import ForwarderService


async def check_forwarders():
    """Check all forwarders and their health settings"""
    print("Checking forwarder configuration...")
    
    async for db in get_database_session():
        try:
            forwarder_service = ForwarderService(db)
            
            # Get all forwarders
            result = await forwarder_service.get_forwarders(limit=100)
            forwarders = result["items"]
            
            print(f"Found {len(forwarders)} forwarders:")
            print()
            
            for forwarder in forwarders:
                print(f"Forwarder: {forwarder.name}")
                print(f"  ID: {forwarder.id}")
                print(f"  Type: {forwarder.forwarder_type}")
                print(f"  Active: {forwarder.is_active}")
                print(f"  Health Check Enabled: {forwarder.health_check_enabled}")
                print(f"  Servers: {len(forwarder.servers) if forwarder.servers else 0}")
                
                if forwarder.servers:
                    for i, server in enumerate(forwarder.servers):
                        print(f"    Server {i+1}: {server.get('ip', 'N/A')}:{server.get('port', 53)}")
                
                print(f"  Domains: {len(forwarder.domains) if forwarder.domains else 0}")
                if forwarder.domains:
                    print(f"    {', '.join(forwarder.domains[:3])}{'...' if len(forwarder.domains) > 3 else ''}")
                
                # Get current health status
                if forwarder.health_check_enabled:
                    health_status = await forwarder_service.get_current_health_status(forwarder.id)
                    print(f"  Current Health Status: {health_status.get('overall_status', 'unknown')}")
                    print(f"  Last Checked: {health_status.get('last_checked', 'Never')}")
                    print(f"  Healthy Servers: {health_status.get('healthy_servers', 0)}/{health_status.get('total_servers', 0)}")
                else:
                    print(f"  Health Checking: Disabled")
                
                print()
            
            break
            
        except Exception as e:
            print(f"Error checking forwarders: {e}")


async def enable_health_check_for_all():
    """Enable health checking for all forwarders"""
    print("Enabling health checking for all forwarders...")
    
    async for db in get_database_session():
        try:
            forwarder_service = ForwarderService(db)
            
            # Get all forwarders
            result = await forwarder_service.get_forwarders(limit=100)
            forwarders = result["items"]
            
            updated_count = 0
            
            for forwarder in forwarders:
                if not forwarder.health_check_enabled:
                    # Enable health checking
                    await forwarder_service.update_forwarder(forwarder.id, {
                        "health_check_enabled": True
                    })
                    print(f"Enabled health checking for: {forwarder.name}")
                    updated_count += 1
            
            print(f"Updated {updated_count} forwarders")
            break
            
        except Exception as e:
            print(f"Error enabling health checks: {e}")


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "list":
            await check_forwarders()
        elif command == "enable":
            await enable_health_check_for_all()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python check_forwarders.py [list|enable]")
    else:
        print("Forwarder Configuration Script")
        print("Usage: python check_forwarders.py [command]")
        print("")
        print("Commands:")
        print("  list   - List all forwarders and their health settings")
        print("  enable - Enable health checking for all forwarders")
        print("")
        
        # Default: list forwarders
        await check_forwarders()


if __name__ == "__main__":
    asyncio.run(main())