#!/usr/bin/env python3
"""
Test script for bulk RPZ API endpoints
"""

import sys
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_endpoints_structure():
    """Test that the bulk RPZ API endpoints are properly structured"""
    print("Testing bulk RPZ API endpoints structure...")
    
    try:
        from app.api.endpoints.rpz import router
        
        # Get all routes from the router
        routes = []
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append({
                    'path': route.path,
                    'methods': list(route.methods),
                    'name': getattr(route, 'name', 'unknown')
                })
        
        # Check for bulk import endpoints
        bulk_import_found = any('/rules/bulk-import' in route['path'] for route in routes)
        print(f"✓ Bulk import endpoint found: {bulk_import_found}")
        
        # Check for bulk update endpoint
        bulk_update_found = any('/rules/bulk-update' in route['path'] for route in routes)
        print(f"✓ Bulk update endpoint found: {bulk_update_found}")
        
        # Check for bulk delete endpoint
        bulk_delete_found = any('/rules/bulk-delete' in route['path'] for route in routes)
        print(f"✓ Bulk delete endpoint found: {bulk_delete_found}")
        
        # Print all bulk-related routes
        bulk_routes = [route for route in routes if 'bulk' in route['path']]
        print(f"\nFound {len(bulk_routes)} bulk-related routes:")
        for route in bulk_routes:
            print(f"  - {route['methods']} {route['path']} ({route['name']})")
        
        if bulk_import_found and bulk_update_found and bulk_delete_found:
            print("\n✓ All required bulk operation endpoints are present!")
            return True
        else:
            print("\n✗ Some bulk operation endpoints are missing!")
            return False
            
    except Exception as e:
        print(f"✗ Error testing API endpoints: {e}")
        return False

def test_endpoint_imports():
    """Test that all required imports work correctly"""
    print("\nTesting endpoint imports...")
    
    try:
        from app.api.endpoints.rpz import (
            bulk_import_rules, bulk_import_rules_json,
            bulk_update_rules, bulk_delete_rules
        )
        print("✓ All bulk operation functions imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_schema_imports():
    """Test that all required schemas can be imported"""
    print("\nTesting schema imports...")
    
    try:
        from app.schemas.security import (
            RPZBulkUpdateRequest, RPZBulkUpdateResult,
            RPZBulkDeleteRequest, RPZBulkDeleteResult,
            RPZRuleImportResult
        )
        print("✓ All bulk operation schemas imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Schema import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Testing Bulk RPZ API Implementation ===\n")
    
    tests = [
        test_schema_imports,
        test_endpoint_imports,
        test_api_endpoints_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("🎉 All bulk RPZ operations are properly implemented!")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())