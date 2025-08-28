#!/usr/bin/env python3
"""
Script to check and restart the health monitoring service
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_database_session
from app.services.health_service import get_health_service
from app.services.background_tasks import get_background_task_service


async def check_health_service_status():
    """Check the status of the health monitoring service"""
    print("Checking health service status...")
    
    health_service = get_health_service()
    background_service = get_background_task_service()
    
    # Check if services are running
    health_running = health_service.is_running()
    background_running = background_service.is_running()
    
    print(f"Health Service Running: {health_running}")
    print(f"Background Service Running: {background_running}")
    
    # Get detailed status
    status = await background_service.get_service_status()
    print(f"Background Service Status: {status}")
    
    return health_running, background_running


async def restart_health_service():
    """Restart the health monitoring service"""
    print("Restarting health monitoring service...")
    
    health_service = get_health_service()
    background_service = get_background_task_service()
    
    # Stop services if running
    if health_service.is_running():
        print("Stopping health service...")
        await health_service.stop()
    
    if background_service.is_running():
        print("Stopping background service...")
        await background_service.stop()
    
    # Start services
    print("Starting background service...")
    await background_service.start()
    
    print("Services restarted successfully!")
    
    # Verify they're running
    await asyncio.sleep(2)
    health_running, background_running = await check_health_service_status()
    
    if health_running and background_running:
        print("✅ Health monitoring service is now running properly")
    else:
        print("❌ Failed to start health monitoring service")


async def trigger_immediate_health_check():
    """Trigger an immediate health check for all forwarders"""
    print("Triggering immediate health check...")
    
    async for db in get_database_session():
        try:
            health_service = get_health_service()
            result = await health_service.trigger_health_check_for_all(db)
            
            print(f"Health check results:")
            print(f"  - Triggered: {result.get('triggered_count', 0)} forwarders")
            print(f"  - Eligible: {result.get('total_eligible', 0)} forwarders")
            
            if result.get('errors'):
                print(f"  - Errors: {len(result['errors'])}")
                for error in result['errors']:
                    print(f"    * {error}")
            
            break
            
        except Exception as e:
            print(f"Error triggering health check: {e}")


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            await check_health_service_status()
        elif command == "restart":
            await restart_health_service()
        elif command == "check":
            await trigger_immediate_health_check()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python check_health_service.py [status|restart|check]")
    else:
        print("Health Service Management Script")
        print("Usage: python check_health_service.py [command]")
        print("")
        print("Commands:")
        print("  status  - Check current service status")
        print("  restart - Restart health monitoring service")
        print("  check   - Trigger immediate health check")
        print("")
        
        # Default: show status
        await check_health_service_status()


if __name__ == "__main__":
    asyncio.run(main())