#!/usr/bin/env python3
"""
Script to test the health API endpoints
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_database_session
from app.services.health_service import get_health_service


async def test_health_api():
    """Test the health API endpoints"""
    print("Testing Health API endpoints...")
    
    async for db in get_database_session():
        try:
            health_service = get_health_service()
            
            print("\n1. Health Service Status:")
            print(f"   Running: {health_service.is_running()}")
            
            print("\n2. Forwarder Health Summary:")
            summary = await health_service.get_forwarder_health_summary(db)
            print(f"   Total Forwarders: {summary['total_forwarders']}")
            print(f"   Active Forwarders: {summary['active_forwarders']}")
            print(f"   Health Check Enabled: {summary['health_check_enabled']}")
            print(f"   Healthy: {summary['healthy_forwarders']}")
            print(f"   Unhealthy: {summary['unhealthy_forwarders']}")
            print(f"   Unknown: {summary['unknown_forwarders']}")
            
            print("\n3. Forwarder Details:")
            for forwarder in summary['forwarder_details']:
                print(f"   - {forwarder['name']} (ID: {forwarder['id']})")
                print(f"     Status: {forwarder['status']}")
                print(f"     Healthy Servers: {forwarder['healthy_servers']}/{forwarder['total_servers']}")
                print(f"     Last Checked: {forwarder['last_checked']}")
            
            print("\n4. Unhealthy Forwarders:")
            unhealthy = await health_service.get_unhealthy_forwarders(db)
            if unhealthy:
                for forwarder in unhealthy:
                    print(f"   - {forwarder['name']}: {forwarder['status']}")
                    print(f"     Servers: {forwarder['healthy_servers']}/{forwarder['total_servers']}")
            else:
                print("   No unhealthy forwarders")
            
            print("\n5. Triggering Manual Health Check:")
            result = await health_service.trigger_health_check_for_all(db)
            print(f"   Triggered: {result['triggered_count']} forwarders")
            print(f"   Eligible: {result['total_eligible']} forwarders")
            if result.get('errors'):
                print(f"   Errors: {len(result['errors'])}")
            
            # Wait a moment for the health check to complete
            await asyncio.sleep(2)
            
            print("\n6. Updated Health Summary:")
            summary = await health_service.get_forwarder_health_summary(db)
            for forwarder in summary['forwarder_details']:
                print(f"   - {forwarder['name']}: {forwarder['status']}")
                print(f"     Last Checked: {forwarder['last_checked']}")
            
            break
            
        except Exception as e:
            print(f"Error testing health API: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main function"""
    await test_health_api()


if __name__ == "__main__":
    asyncio.run(main())