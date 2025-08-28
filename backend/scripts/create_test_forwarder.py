#!/usr/bin/env python3
"""
Script to create a test forwarder for health checking
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_database_session
from app.services.forwarder_service import ForwarderService


async def create_test_forwarder():
    """Create a test forwarder with health checking enabled"""
    print("Creating test forwarder...")
    
    async for db in get_database_session():
        try:
            forwarder_service = ForwarderService(db)
            
            # Create a test forwarder
            forwarder_data = {
                "name": "Test Forward First",
                "forwarder_type": "public",
                "domains": ["test.local", "example.local"],
                "servers": [
                    {"ip": "8.8.8.8", "port": 53},
                    {"ip": "1.1.1.1", "port": 53}
                ],
                "is_active": True,
                "health_check_enabled": True,
                "description": "Test forwarder for health checking"
            }
            
            forwarder = await forwarder_service.create_forwarder(forwarder_data)
            
            print(f"Created test forwarder: {forwarder.name} (ID: {forwarder.id})")
            print(f"  Health Check Enabled: {forwarder.health_check_enabled}")
            print(f"  Servers: {len(forwarder.servers)}")
            
            # Trigger an immediate health check
            print("Triggering initial health check...")
            result = await forwarder_service.perform_health_check(forwarder.id)
            
            print(f"Health check completed:")
            print(f"  Forwarder: {result.get('forwarder_name')}")
            print(f"  Servers tested: {len(result.get('results', []))}")
            
            for server_result in result.get('results', []):
                print(f"    {server_result['server_ip']}:{server_result['server_port']} - {server_result['status']}")
                if server_result.get('response_time'):
                    print(f"      Response time: {server_result['response_time']}ms")
                if server_result.get('error_message'):
                    print(f"      Error: {server_result['error_message']}")
            
            # Get current health status
            health_status = await forwarder_service.get_current_health_status(forwarder.id)
            print(f"  Overall Status: {health_status.get('overall_status', 'unknown')}")
            print(f"  Healthy Servers: {health_status.get('healthy_servers', 0)}/{health_status.get('total_servers', 0)}")
            
            break
            
        except Exception as e:
            print(f"Error creating test forwarder: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main function"""
    await create_test_forwarder()


if __name__ == "__main__":
    asyncio.run(main())