"""
Feature flag management for WebSocket system rollout
"""

import hashlib
import random
from enum import Enum
from typing import Optional, Dict, Any
from functools import lru_cache

from .config import get_settings
from .logging_config import get_logger

logger = get_logger(__name__)


class WebSocketMigrationMode(Enum):
    """WebSocket migration modes"""
    DISABLED = "disabled"  # Use legacy system only
    TESTING = "testing"    # Use unified system for specific test users only
    GRADUAL = "gradual"    # Gradual rollout based on percentage and user lists
    FULL = "full"         # Use unified system for all users


class WebSocketFeatureFlags:
    """Feature flag manager for WebSocket system rollout"""
    
    def __init__(self):
        self.settings = get_settings()
        self._user_assignments: Dict[str, bool] = {}  # Cache user assignments
    
    def should_use_unified_websocket(self, user_id: str) -> bool:
        """
        Determine if a user should use the unified WebSocket system
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user should use unified WebSocket, False for legacy
        """
        try:
            # Check if user is forced to use legacy system
            if user_id in self.settings.websocket_force_legacy_users_parsed:
                logger.debug(f"User {user_id} forced to use legacy WebSocket")
                return False
            
            # Get migration mode
            migration_mode = WebSocketMigrationMode(self.settings.WEBSOCKET_MIGRATION_MODE.lower())
            
            if migration_mode == WebSocketMigrationMode.DISABLED:
                return False
            
            if migration_mode == WebSocketMigrationMode.FULL:
                return True
            
            if migration_mode == WebSocketMigrationMode.TESTING:
                # Only specific users in the rollout list
                result = user_id in self.settings.websocket_rollout_user_list_parsed
                logger.debug(f"Testing mode: User {user_id} unified WebSocket = {result}")
                return result
            
            if migration_mode == WebSocketMigrationMode.GRADUAL:
                return self._should_use_unified_gradual(user_id)
            
            # Default to legacy
            return False
            
        except Exception as e:
            logger.error(f"Error determining WebSocket system for user {user_id}: {e}")
            return False  # Default to legacy on error
    
    def _should_use_unified_gradual(self, user_id: str) -> bool:
        """
        Determine if user should use unified WebSocket in gradual rollout mode
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user should use unified WebSocket
        """
        # Check if user is explicitly in the rollout list
        if user_id in self.settings.websocket_rollout_user_list_parsed:
            logger.debug(f"User {user_id} in explicit rollout list")
            return True
        
        # Check cached assignment
        if user_id in self._user_assignments:
            return self._user_assignments[user_id]
        
        # Use deterministic hash-based assignment for consistent user experience
        rollout_percentage = max(0, min(100, self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE))
        
        if rollout_percentage == 0:
            self._user_assignments[user_id] = False
            return False
        
        if rollout_percentage == 100:
            self._user_assignments[user_id] = True
            return True
        
        # Create deterministic hash of user ID
        user_hash = hashlib.md5(f"websocket_rollout_{user_id}".encode()).hexdigest()
        hash_int = int(user_hash[:8], 16)  # Use first 8 hex chars
        user_percentage = hash_int % 100
        
        should_use_unified = user_percentage < rollout_percentage
        self._user_assignments[user_id] = should_use_unified
        
        logger.debug(f"Gradual rollout: User {user_id} hash={user_percentage}, "
                    f"threshold={rollout_percentage}, unified={should_use_unified}")
        
        return should_use_unified
    
    def get_websocket_system_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get information about which WebSocket system a user should use
        
        Args:
            user_id: The user ID to check
            
        Returns:
            Dictionary with WebSocket system information
        """
        should_use_unified = self.should_use_unified_websocket(user_id)
        migration_mode = WebSocketMigrationMode(self.settings.WEBSOCKET_MIGRATION_MODE.lower())
        
        return {
            "user_id": user_id,
            "use_unified": should_use_unified,
            "system": "unified" if should_use_unified else "legacy",
            "migration_mode": migration_mode.value,
            "rollout_percentage": self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE,
            "in_explicit_list": user_id in self.settings.websocket_rollout_user_list_parsed,
            "forced_legacy": user_id in self.settings.websocket_force_legacy_users_parsed,
            "fallback_enabled": self.settings.WEBSOCKET_LEGACY_FALLBACK
        }
    
    def get_rollout_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current rollout configuration
        
        Returns:
            Dictionary with rollout statistics
        """
        migration_mode = WebSocketMigrationMode(self.settings.WEBSOCKET_MIGRATION_MODE.lower())
        
        return {
            "migration_mode": migration_mode.value,
            "unified_enabled": self.settings.WEBSOCKET_UNIFIED_ENABLED,
            "gradual_rollout_enabled": self.settings.WEBSOCKET_GRADUAL_ROLLOUT_ENABLED,
            "rollout_percentage": self.settings.WEBSOCKET_ROLLOUT_PERCENTAGE,
            "explicit_rollout_users": len(self.settings.websocket_rollout_user_list_parsed),
            "forced_legacy_users": len(self.settings.websocket_force_legacy_users_parsed),
            "fallback_enabled": self.settings.WEBSOCKET_LEGACY_FALLBACK,
            "cached_assignments": len(self._user_assignments)
        }
    
    def clear_user_assignment_cache(self, user_id: Optional[str] = None):
        """
        Clear cached user assignments
        
        Args:
            user_id: Specific user ID to clear, or None to clear all
        """
        if user_id:
            self._user_assignments.pop(user_id, None)
            logger.info(f"Cleared WebSocket assignment cache for user {user_id}")
        else:
            self._user_assignments.clear()
            logger.info("Cleared all WebSocket assignment cache")
    
    def force_user_to_system(self, user_id: str, use_unified: bool) -> bool:
        """
        Force a user to use a specific WebSocket system (for testing/debugging)
        
        Args:
            user_id: The user ID
            use_unified: True for unified, False for legacy
            
        Returns:
            True if assignment was successful
        """
        try:
            self._user_assignments[user_id] = use_unified
            system = "unified" if use_unified else "legacy"
            logger.info(f"Forced user {user_id} to use {system} WebSocket system")
            return True
        except Exception as e:
            logger.error(f"Error forcing user {user_id} to WebSocket system: {e}")
            return False


# Global feature flags instance
_websocket_feature_flags = None


@lru_cache()
def get_websocket_feature_flags() -> WebSocketFeatureFlags:
    """Get the global WebSocket feature flags instance"""
    global _websocket_feature_flags
    if _websocket_feature_flags is None:
        _websocket_feature_flags = WebSocketFeatureFlags()
    return _websocket_feature_flags


def should_use_unified_websocket(user_id: str) -> bool:
    """
    Convenience function to check if user should use unified WebSocket
    
    Args:
        user_id: The user ID to check
        
    Returns:
        True if user should use unified WebSocket, False for legacy
    """
    return get_websocket_feature_flags().should_use_unified_websocket(user_id)