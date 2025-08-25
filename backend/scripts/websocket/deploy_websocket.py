#!/usr/bin/env python3
"""
WebSocket System Deployment Script

This script manages the gradual rollout of the unified WebSocket system
with monitoring and automatic rollback capabilities.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.core.feature_flags import get_websocket_feature_flags, WebSocketMigrationMode
from app.websocket.router import get_websocket_router
from monitor_websocket_deployment import WebSocketDeploymentMonitor, MonitoringThresholds

logger = get_logger(__name__)


class WebSocketDeploymentManager:
    """Manages the deployment and rollout of the unified WebSocket system"""
    
    def __init__(self):
        self.settings = get_settings()
        self.feature_flags = get_websocket_feature_flags()
        self.router = get_websocket_router()
    
    async def deploy_testing_mode(self, test_users: List[str]):
        """
        Deploy in testing mode for specific users
        
        Args:
            test_users: List of user IDs to include in testing
        """
        print(f"🧪 DEPLOYING WEBSOCKET SYSTEM IN TESTING MODE")
        print(f"Test users: {len(test_users)}")
        print("-" * 60)
        
        try:
            # Update configuration
            self.settings.WEBSOCKET_MIGRATION_MODE = "testing"
            self.settings.WEBSOCKET_ROLLOUT_USER_LIST = ",".join(test_users)
            self.settings.WEBSOCKET_UNIFIED_ENABLED = True
            
            # Clear cache to apply changes
            self.feature_flags.clear_user_assignment_cache()
            
            # Update environment file
            await self._update_env_file({
                'WEBSOCKET_MIGRATION_MODE': 'testing',
                'WEBSOCKET_ROLLOUT_USER_LIST': ",".join(test_users),
                'WEBSOCKET_UNIFIED_ENABLED': 'true'
            })
            
            print("✅ Testing mode deployment completed")
            print(f"   - {len(test_users)} users will use the unified system")
            print(f"   - All other users will use the legacy system")
            print(f"   - Monitor the system and verify functionality before proceeding")
            
            logger.info(f"WebSocket system deployed in testing mode for {len(test_users)} users")
            return True
            
        except Exception as e:
            print(f"❌ Testing mode deployment failed: {e}")
            logger.error(f"Testing mode deployment failed: {e}")
            return False
    
    async def deploy_gradual_rollout(
        self, 
        initial_percentage: int = 5,
        max_percentage: int = 100,
        step_size: int = 5,
        step_duration_minutes: int = 30,
        monitor_deployment: bool = True
    ):
        """
        Deploy with gradual rollout
        
        Args:
            initial_percentage: Starting rollout percentage
            max_percentage: Maximum rollout percentage
            step_size: Percentage increase per step
            step_duration_minutes: Duration of each step
            monitor_deployment: Whether to monitor during deployment
        """
        print(f"🚀 STARTING GRADUAL WEBSOCKET DEPLOYMENT")
        print(f"Initial: {initial_percentage}% → Max: {max_percentage}%")
        print(f"Step size: {step_size}%, Duration: {step_duration_minutes} minutes")
        print("-" * 60)
        
        try:
            # Set initial configuration
            self.settings.WEBSOCKET_MIGRATION_MODE = "gradual"
            self.settings.WEBSOCKET_GRADUAL_ROLLOUT_ENABLED = True
            self.settings.WEBSOCKET_UNIFIED_ENABLED = True
            self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE = initial_percentage
            
            # Clear cache
            self.feature_flags.clear_user_assignment_cache()
            
            # Update environment file
            await self._update_env_file({
                'WEBSOCKET_MIGRATION_MODE': 'gradual',
                'WEBSOCKET_GRADUAL_ROLLOUT_ENABLED': 'true',
                'WEBSOCKET_UNIFIED_ENABLED': 'true',
                'WEBSOCKET_ROLLOUT_PERCENTAGE': str(initial_percentage)
            })
            
            current_percentage = initial_percentage
            
            while current_percentage <= max_percentage:
                print(f"\n📊 ROLLOUT STEP: {current_percentage}%")
                print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                # Update rollout percentage
                self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE = current_percentage
                self.feature_flags.clear_user_assignment_cache()
                
                # Update environment file
                await self._update_env_file({
                    'WEBSOCKET_ROLLOUT_PERCENTAGE': str(current_percentage)
                })
                
                print(f"✅ Rollout percentage set to {current_percentage}%")
                
                # Monitor this step if requested
                if monitor_deployment and current_percentage < max_percentage:
                    print(f"🔍 Monitoring for {step_duration_minutes} minutes...")
                    
                    # Create monitoring thresholds for deployment
                    thresholds = MonitoringThresholds(
                        max_error_rate=3.0,  # Stricter during deployment
                        max_routing_errors=20,
                        max_fallback_rate=5.0,
                        min_success_rate=97.0,
                        consecutive_failures_threshold=2  # Faster rollback during deployment
                    )
                    
                    monitor = WebSocketDeploymentMonitor(thresholds)
                    
                    # Monitor for the step duration
                    monitoring_task = asyncio.create_task(
                        monitor.start_monitoring(step_duration_minutes)
                    )
                    
                    try:
                        await monitoring_task
                        
                        if monitor.rollback_triggered:
                            print("🚨 Automatic rollback triggered during monitoring!")
                            print("Deployment stopped.")
                            return False
                        
                        print(f"✅ Step monitoring completed successfully")
                        
                    except Exception as e:
                        print(f"⚠️  Monitoring error: {e}")
                        print("Continuing deployment...")
                
                # Move to next step
                if current_percentage >= max_percentage:
                    break
                
                current_percentage = min(current_percentage + step_size, max_percentage)
            
            print(f"\n🎯 GRADUAL DEPLOYMENT COMPLETED!")
            print(f"Final rollout percentage: {max_percentage}%")
            
            if max_percentage == 100:
                # Switch to full mode
                await self.deploy_full_mode()
            
            logger.info(f"Gradual WebSocket deployment completed at {max_percentage}%")
            return True
            
        except Exception as e:
            print(f"❌ Gradual deployment failed: {e}")
            logger.error(f"Gradual deployment failed: {e}")
            return False
    
    async def deploy_full_mode(self):
        """Deploy in full mode (all users use unified system)"""
        print(f"🌟 DEPLOYING WEBSOCKET SYSTEM IN FULL MODE")
        print("-" * 60)
        
        try:
            # Update configuration
            self.settings.WEBSOCKET_MIGRATION_MODE = "full"
            self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE = 100
            self.settings.WEBSOCKET_UNIFIED_ENABLED = True
            
            # Clear cache
            self.feature_flags.clear_user_assignment_cache()
            
            # Update environment file
            await self._update_env_file({
                'WEBSOCKET_MIGRATION_MODE': 'full',
                'WEBSOCKET_ROLLOUT_PERCENTAGE': '100',
                'WEBSOCKET_UNIFIED_ENABLED': 'true'
            })
            
            print("✅ Full mode deployment completed")
            print("   - All users will use the unified WebSocket system")
            print("   - Legacy system is still available as fallback")
            
            logger.info("WebSocket system deployed in full mode")
            return True
            
        except Exception as e:
            print(f"❌ Full mode deployment failed: {e}")
            logger.error(f"Full mode deployment failed: {e}")
            return False
    
    async def _update_env_file(self, updates: dict):
        """Update the .env file with new settings"""
        env_file = Path(".env")
        
        if not env_file.exists():
            print("  - No .env file found, creating one...")
            with open(env_file, 'w') as f:
                for key, value in updates.items():
                    f.write(f"{key}={value}\n")
            return
        
        try:
            # Read current .env file
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update existing settings or add new ones
            updated_lines = []
            updated_keys = set()
            
            for line in lines:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key = line.split('=')[0]
                    if key in updates:
                        updated_lines.append(f'{key}={updates[key]}\n')
                        updated_keys.add(key)
                    else:
                        updated_lines.append(line + '\n' if not line.endswith('\n') else line)
                else:
                    updated_lines.append(line + '\n' if not line.endswith('\n') else line)
            
            # Add new settings that weren't in the file
            for key, value in updates.items():
                if key not in updated_keys:
                    updated_lines.append(f'{key}={value}\n')
            
            # Write updated .env file
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            print(f"  - Updated .env file with {len(updates)} settings")
            
        except Exception as e:
            print(f"  - Warning: Could not update .env file: {e}")
    
    async def status_check(self):
        """Check current deployment status"""
        print("📊 WEBSOCKET DEPLOYMENT STATUS")
        print("=" * 50)
        
        try:
            # Get rollout statistics
            rollout_stats = self.feature_flags.get_rollout_statistics()
            connection_stats = self.router.get_connection_stats()
            router_stats = connection_stats.get("router_stats", {})
            
            print(f"Migration Mode: {rollout_stats['migration_mode']}")
            print(f"Unified Enabled: {rollout_stats['unified_enabled']}")
            print(f"Rollout Percentage: {rollout_stats['rollout_percentage']}%")
            print(f"Explicit Users: {rollout_stats['explicit_rollout_users']}")
            print(f"Forced Legacy: {rollout_stats['forced_legacy_users']}")
            print()
            
            print("Current Connections:")
            print(f"  Legacy: {router_stats.get('legacy_connections', 0)}")
            print(f"  Unified: {router_stats.get('unified_connections', 0)}")
            print(f"  Total: {router_stats.get('legacy_connections', 0) + router_stats.get('unified_connections', 0)}")
            print()
            
            print("Error Statistics:")
            print(f"  Routing Errors: {router_stats.get('routing_errors', 0)}")
            print(f"  Fallback Activations: {router_stats.get('fallback_activations', 0)}")
            
            # Determine deployment phase
            mode = rollout_stats['migration_mode']
            percentage = rollout_stats['rollout_percentage']
            
            if mode == "disabled":
                phase = "Not deployed (legacy only)"
            elif mode == "testing":
                phase = f"Testing phase ({rollout_stats['explicit_rollout_users']} users)"
            elif mode == "gradual":
                phase = f"Gradual rollout ({percentage}%)"
            elif mode == "full":
                phase = "Full deployment (100%)"
            else:
                phase = f"Unknown ({mode})"
            
            print(f"\nDeployment Phase: {phase}")
            
            return True
            
        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return False


async def main():
    """Main function for the deployment script"""
    parser = argparse.ArgumentParser(description="WebSocket System Deployment Manager")
    parser.add_argument(
        "action",
        choices=["testing", "gradual", "full", "status"],
        help="Deployment action to perform"
    )
    parser.add_argument(
        "--test-users",
        nargs="+",
        help="User IDs for testing mode"
    )
    parser.add_argument(
        "--initial-percentage",
        type=int,
        default=5,
        help="Initial rollout percentage for gradual deployment"
    )
    parser.add_argument(
        "--max-percentage",
        type=int,
        default=100,
        help="Maximum rollout percentage for gradual deployment"
    )
    parser.add_argument(
        "--step-size",
        type=int,
        default=5,
        help="Percentage increase per step in gradual deployment"
    )
    parser.add_argument(
        "--step-duration",
        type=int,
        default=30,
        help="Duration of each step in minutes"
    )
    parser.add_argument(
        "--no-monitoring",
        action="store_true",
        help="Disable monitoring during gradual deployment"
    )
    
    args = parser.parse_args()
    
    deployment_manager = WebSocketDeploymentManager()
    
    if args.action == "testing":
        if not args.test_users:
            print("❌ Test users required for testing mode")
            sys.exit(1)
        
        success = await deployment_manager.deploy_testing_mode(args.test_users)
        sys.exit(0 if success else 1)
    
    elif args.action == "gradual":
        success = await deployment_manager.deploy_gradual_rollout(
            initial_percentage=args.initial_percentage,
            max_percentage=args.max_percentage,
            step_size=args.step_size,
            step_duration_minutes=args.step_duration,
            monitor_deployment=not args.no_monitoring
        )
        sys.exit(0 if success else 1)
    
    elif args.action == "full":
        success = await deployment_manager.deploy_full_mode()
        sys.exit(0 if success else 1)
    
    elif args.action == "status":
        success = await deployment_manager.status_check()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())