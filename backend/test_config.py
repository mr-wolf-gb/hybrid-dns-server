#!/usr/bin/env python3
"""
Test script to verify configuration loading works without early import issues
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up a minimal environment for testing
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

def test_config_loading():
    """Test that configuration can be loaded without import errors"""
    try:
        # This should not fail now
        from app.core.config import get_settings
        
        settings = get_settings()
        print(f"✅ Configuration loaded successfully!")
        print(f"   SECRET_KEY: {'*' * len(settings.SECRET_KEY)}")
        print(f"   DATABASE_URL: {settings.DATABASE_URL}")
        print(f"   DEBUG: {settings.DEBUG}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_logging_config():
    """Test that logging configuration can be loaded"""
    try:
        from app.core.logging_config import setup_logging, get_logger
        
        setup_logging()
        logger = get_logger(__name__)
        logger.info("Test log message")
        
        print("✅ Logging configuration loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Logging configuration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_config():
    """Test that database configuration can be loaded"""
    try:
        from app.core.database import _initialize_database_engine
        
        _initialize_database_engine()
        print("✅ Database configuration loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database configuration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing configuration loading fixes...")
    print("=" * 50)
    
    success = True
    success &= test_config_loading()
    success &= test_logging_config()
    success &= test_database_config()
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! The configuration loading fix should work.")
    else:
        print("❌ Some tests failed. There may still be issues.")
    
    sys.exit(0 if success else 1)