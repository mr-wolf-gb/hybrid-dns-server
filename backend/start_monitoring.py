#!/usr/bin/env python3
"""
Monitoring service startup script
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.monitoring_service import MonitoringService
from app.services.health_service import HealthService

async def main():
    """Main entry point for monitoring service"""
    try:
        monitor = MonitoringService()
        health = HealthService()
        
        # Start both services concurrently
        await asyncio.gather(
            monitor.start_monitoring(),
            health.start_health_checks()
        )
    except KeyboardInterrupt:
        print("Monitoring service stopped by user")
    except Exception as e:
        print(f"Error in monitoring service: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())