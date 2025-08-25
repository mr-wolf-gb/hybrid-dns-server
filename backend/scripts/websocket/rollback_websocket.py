#!/usr/bin/env python3
"""
Emergency WebSocket System Rollback Script

This script provides emergency rollback capabilities for the WebSocket system
when the admin interface is not accessible or when immediate rollback is needed.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.core.feature_flags import get_websocket_feature_flags
from app.websocket.router import get_websocket_router

logger = get_logger(__name__)


class WebSocketRollbackManager:
    """Manages WebSocket system rollback operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.feature_flags = get_websocket_feature_flags()
        self.router = get_websocket_router()
    
    async def emergency_rollback(self, reason: str = "Emergency rollback"):
        """
        Perform emergency rollback to legacy WebSocket system
        
        Args:
            reason: Reason for the rollback
        """
        print(f"🚨 EMERGENCY ROLLBACK INITIATED: {reason}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("-" * 60)
        
        try:
            # Get current stats before rollback
            stats_before = self.router.get_connection_stats()
            unified_connections = stats_before.get("unified_stats", {}).get("total_connections", 0)
            legacy_connections = stats_before.get("legacy_stats", {}).get("total_connections", 0)
            
            print(f"Current connections:")
            print(f"  - Unified system: {unified_connections}")
            print(f"  - Legacy system: {legacy_connections}")
            print()
            
            # Step 1: Set migration mode to disabled
            print("Step 1: Setting migration mode to 'disabled'...")
            self.settings.WEBSOCKET_MIGRATION_MODE = "disabled"
            print("✅ Migration mode set to disabled")
            
            # Step 2: Clear user assignment cache
            print("Step 2: Clearing user assignment cache...")
            self.feature_flags.clear_user_assignment_cache()
            print("✅ User assignment cache cleared")
            
            # Step 3: Update environment file if it exists
            print("Step 3: Updating environment configuration...")
            await self._update_env_file()
            print("✅ Environment configuration updated")
            
            # Step 4: Log the rollback
            logger.critical(f"EMERGENCY ROLLBACK COMPLETED: {reason}")
            
            print()
            print("🎯 ROLLBACK COMPLETED SUCCESSFULLY")
            print("Next steps:")
            print("  1. All new WebSocket connections will use the legacy system")
            print("  2. Existing unified connections will be disconnected on next reconnection")
            print("  3. Monitor system logs for stability")
            print("  4. Restart the backend service to ensure all changes take effect")
            print("  5. Review logs to determine the cause of the rollback")
            
            return True
            
        except Exception as e:
            print(f"❌ ROLLBACK FAILED: {e}")
            logger.error(f"Emergency rollback failed: {e}")
            return False
    
    async def _update_env_file(self):
        """Update the .env file with rollback settings"""
        env_file = Path(".env")
        
        if not env_file.exists():
            print("  - No .env file found, skipping environment update")
            return
        
        try:
            # Read current .env file
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update WebSocket settings
            updated_lines = []
            websocket_settings_updated = set()
            
            for line in lines:
                line = line.strip()
                if line.startswith('WEBSOCKET_MIGRATION_MODE='):
                    updated_lines.append('WEBSOCKET_MIGRATION_MODE=disabled\n')
                    websocket_settings_updated.add('WEBSOCKET_MIGRATION_MODE')
                elif line.startswith('WEBSOCKET_ROLLOUT_PERCENTAGE='):
                    updated_lines.append('WEBSOCKET_ROLLOUT_PERCENTAGE=0\n')
                    websocket_settings_updated.add('WEBSOCKET_ROLLOUT_PERCENTAGE')
                elif line.startswith('WEBSOCKET_GRADUAL_ROLLOUT_ENABLED='):
                    updated_lines.append('WEBSOCKET_GRADUAL_ROLLOUT_ENABLED=false\n')
                    websocket_settings_updated.add('WEBSOCKET_GRADUAL_ROLLOUT_ENABLED')
                elif line.startswith('WEBSOCKET_UNIFIED_ENABLED='):
                    updated_lines.append('WEBSOCKET_UNIFIED_ENABLED=false\n')
                    websocket_settings_updated.add('WEBSOCKET_UNIFIED_ENABLED')
                else:
                    updated_lines.append(line + '\n' if not line.endswith('\n') else line)
            
            # Add missing settings if they weren't in the file
            missing_settings = {
                'WEBSOCKET_MIGRATION_MODE': 'disabled',
                'WEBSOCKET_ROLLOUT_PERCENTAGE': '0',
                'WEBSOCKET_GRADUAL_ROLLOUT_ENABLED': 'false',
                'WEBSOCKET_UNIFIED_ENABLED': 'false'
            }
            
            for setting, value in missing_settings.items():
                if setting not in websocket_settings_updated:
                    updated_lines.append(f'{setting}={value}\n')
            
            # Write updated .env file
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            print("  - .env file updated with rollback settings")
            
        except Exception as e:
            print(f"  - Warning: Could not update .env file: {e}")
    
    async def gradual_rollback(self, percentage_step: int = 10):
        """
        Perform gradual rollback by reducing rollout percentage
        
        Args:
            percentage_step: How much to reduce the percentage by each step
        """
        current_percentage = self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE
        
        if current_percentage == 0:
            print("Already at 0% rollout - no rollback needed")
            return True
        
        new_percentage = max(0, current_percentage - percentage_step)
        
        print(f"🔄 GRADUAL ROLLBACK: {current_percentage}% → {new_percentage}%")
        
        try:
            # Update rollout percentage
            self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE = new_percentage
            
            # Clear cache to apply new percentage
            self.feature_flags.clear_user_assignment_cache()
            
            # Update environment file
            await self._update_env_file()
            
            print(f"✅ Rollout percentage reduced to {new_percentage}%")
            
            if new_percentage == 0:
                print("🎯 Gradual rollback complete - all users on legacy system")
            else:
                print(f"📊 {new_percentage}% of users still on unified system")
            
            return True
            
        except Exception as e:
            print(f"❌ Gradual rollback failed: {e}")
            logger.error(f"Gradual rollback failed: {e}")
            return False
    
    async def status_check(self):
        """Check current WebSocket system status"""
        print("📊 WEBSOCKET SYSTEM STATUS")
        print("=" * 50)
        
        try:
            # Get rollout statistics
            rollout_stats = self.feature_flags.get_rollout_statistics()
            print(f"Migration Mode: {rollout_stats['migration_mode']}")
            print(f"Unified Enabled: {rollout_stats['unified_enabled']}")
            print(f"Gradual Rollout: {rollout_stats['gradual_rollout_enabled']}")
            print(f"Rollout Percentage: {rollout_stats['rollout_percentage']}%")
            print(f"Explicit Rollout Users: {rollout_stats['explicit_rollout_users']}")
            print(f"Forced Legacy Users: {rollout_stats['forced_legacy_users']}")
            print(f"Fallback Enabled: {rollout_stats['fallback_enabled']}")
            print()
            
            # Get connection statistics
            connection_stats = self.router.get_connection_stats()
            router_stats = connection_stats.get("router_stats", {})
            
            print("Connection Statistics:")
            print(f"  Legacy Connections: {router_stats.get('legacy_connections', 0)}")
            print(f"  Unified Connections: {router_stats.get('unified_connections', 0)}")
            print(f"  Routing Errors: {router_stats.get('routing_errors', 0)}")
            print(f"  Fallback Activations: {router_stats.get('fallback_activations', 0)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return False


async def main():
    """Main function for the rollback script"""
    parser = argparse.ArgumentParser(description="WebSocket System Rollback Tool")
    parser.add_argument(
        "action",
        choices=["emergency", "gradual", "status"],
        help="Action to perform"
    )
    parser.add_argument(
        "--reason",
        default="Manual rollback via script",
        help="Reason for the rollback"
    )
    parser.add_argument(
        "--step",
        type=int,
        default=10,
        help="Percentage step for gradual rollback (default: 10)"
    )
    
    args = parser.parse_args()
    
    rollback_manager = WebSocketRollbackManager()
    
    if args.action == "emergency":
        success = await rollback_manager.emergency_rollback(args.reason)
        sys.exit(0 if success else 1)
    
    elif args.action == "gradual":
        success = await rollback_manager.gradual_rollback(args.step)
        sys.exit(0 if success else 1)
    
    elif args.action == "status":
        success = await rollback_manager.status_check()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())