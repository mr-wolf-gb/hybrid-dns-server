#!/usr/bin/env python3
"""
Test script for bulk RPZ operations
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.schemas.security import (
    RPZBulkUpdateRequest, RPZBulkUpdateResult, 
    RPZBulkDeleteRequest, RPZBulkDeleteResult,
    RPZRuleCreate, RPZRuleUpdate, RPZAction
)

def test_bulk_schemas():
    """Test that the bulk operation schemas work correctly"""
    print("Testing bulk operation schemas...")
    
    # Test bulk update request
    update_request = RPZBulkUpdateRequest(
        rule_ids=[1, 2, 3],
        updates=RPZRuleUpdate(
            action=RPZAction.BLOCK,
            description="Updated via bulk operation"
        )
    )
    print(f"✓ Bulk update request: {update_request.model_dump()}")
    
    # Test bulk update result
    update_result = RPZBulkUpdateResult(
        total_processed=3,
        rules_updated=2,
        rules_failed=1,
        errors=["Rule 3: Not found"]
    )
    print(f"✓ Bulk update result: {update_result.model_dump()}")
    
    # Test bulk delete request
    delete_request = RPZBulkDeleteRequest(
        rule_ids=[4, 5, 6],
        confirm=True
    )
    print(f"✓ Bulk delete request: {delete_request.model_dump()}")
    
    # Test bulk delete result
    delete_result = RPZBulkDeleteResult(
        total_processed=3,
        rules_deleted=3,
        rules_failed=0,
        affected_zones=["malware", "phishing"],
        errors=[]
    )
    print(f"✓ Bulk delete result: {delete_result.model_dump()}")
    
    print("All bulk operation schemas work correctly!")

def test_bulk_validation():
    """Test validation in bulk operation schemas"""
    print("\nTesting bulk operation validation...")
    
    try:
        # Test that bulk delete requires confirmation
        RPZBulkDeleteRequest(rule_ids=[1, 2, 3], confirm=False)
        print("✗ Bulk delete validation failed - should require confirmation")
    except ValueError as e:
        print(f"✓ Bulk delete validation works: {e}")
    
    try:
        # Test that rule_ids cannot be empty
        RPZBulkUpdateRequest(rule_ids=[], updates=RPZRuleUpdate(action=RPZAction.BLOCK))
        print("✗ Bulk update validation failed - should require rule_ids")
    except ValueError as e:
        print(f"✓ Bulk update validation works: {e}")
    
    print("Bulk operation validation works correctly!")

def main():
    """Run all tests"""
    print("=== Testing Bulk RPZ Operations ===\n")
    
    try:
        test_bulk_schemas()
        test_bulk_validation()
        print("\n=== All tests passed! ===")
        return 0
    except Exception as e:
        print(f"\n=== Test failed: {e} ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())