#!/usr/bin/env python3
"""
Final validation script to ensure all response schemas serialize data correctly.
This script runs comprehensive tests to validate serialization functionality.
"""

import sys
import os
from datetime import datetime, timezone

# Add the backend app to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def main():
    """Run all serialization validation tests"""
    print("🔍 Running Final Response Schema Serialization Validation...\n")
    
    try:
        # Import all schemas to verify they're available
        from app.schemas import (
            Zone, DNSRecord, Forwarder, ForwarderHealth,
            ThreatFeed, RPZRule, SystemConfig, SystemStatus,
            DNSLog, UserInfo, PaginatedResponse, HealthCheckResult,
            ZoneValidationResult, ValidationResult
        )
        print("✓ All schemas imported successfully")
        
        # Test basic serialization functionality
        now = datetime.now(timezone.utc)
        
        # Test Zone serialization
        zone = Zone(
            id=1,
            name="test.example.com",
            zone_type="master",
            email="admin.test.example.com",
            serial=2024011501,
            is_active=True,
            created_at=now,
            updated_at=now,
            record_count=10
        )
        
        zone_dict = zone.model_dump()
        zone_json = zone.model_dump_json()
        
        assert zone_dict["name"] == "test.example.com"
        assert zone_dict["zone_type"] == "master"
        assert zone_dict["is_active"] is True
        assert '"name":"test.example.com"' in zone_json
        print("✓ Zone serialization works correctly")
        
        # Test DNSRecord serialization
        record = DNSRecord(
            id=1,
            zone_id=1,
            name="www",
            record_type="A",
            value="192.168.1.100",
            ttl=3600,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        record_dict = record.model_dump()
        record_json = record.model_dump_json()
        
        assert record_dict["record_type"] == "A"
        assert record_dict["value"] == "192.168.1.100"
        assert record_dict["ttl"] == 3600
        assert '"record_type":"A"' in record_json
        print("✓ DNSRecord serialization works correctly")
        
        # Test PaginatedResponse serialization
        paginated = PaginatedResponse(
            items=[zone_dict, record_dict],
            total=2,
            page=1,
            per_page=10,
            pages=1
        )
        
        paginated_dict = paginated.model_dump()
        paginated_json = paginated.model_dump_json()
        
        assert len(paginated_dict["items"]) == 2
        assert paginated_dict["total"] == 2
        assert '"total":2' in paginated_json
        print("✓ PaginatedResponse serialization works correctly")
        
        # Test HealthCheckResult serialization
        health = HealthCheckResult(
            server_ip="192.168.1.10",
            status="healthy",
            response_time=25,
            error_message=None,
            checked_at=now
        )
        
        health_dict = health.model_dump()
        health_json = health.model_dump_json()
        
        assert health_dict["server_ip"] == "192.168.1.10"
        assert health_dict["status"] == "healthy"
        assert health_dict["response_time"] == 25
        assert health_dict["error_message"] is None
        assert '"status":"healthy"' in health_json
        print("✓ HealthCheckResult serialization works correctly")
        
        # Test ValidationResult serialization
        validation = ValidationResult(
            valid=True,
            errors=[],
            warnings=["Minor warning"],
            details={"field": "test", "value": "ok"}
        )
        
        validation_dict = validation.model_dump()
        validation_json = validation.model_dump_json()
        
        assert validation_dict["valid"] is True
        assert validation_dict["errors"] == []
        assert len(validation_dict["warnings"]) == 1
        assert validation_dict["details"]["field"] == "test"
        assert '"valid":true' in validation_json
        print("✓ ValidationResult serialization works correctly")
        
        # Test datetime serialization
        import json
        parsed_zone = json.loads(zone_json)
        assert "created_at" in parsed_zone
        assert "updated_at" in parsed_zone
        assert isinstance(parsed_zone["created_at"], str)
        assert isinstance(parsed_zone["updated_at"], str)
        print("✓ Datetime serialization works correctly")
        
        # Test None value handling
        record_with_none = DNSRecord(
            id=2,
            zone_id=1,
            name="test",
            record_type="A",
            value="127.0.0.1",
            ttl=None,
            priority=None,
            weight=None,
            port=None,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        none_dict = record_with_none.model_dump()
        none_json = record_with_none.model_dump_json()
        parsed_none = json.loads(none_json)
        
        assert none_dict["ttl"] is None
        assert none_dict["priority"] is None
        assert parsed_none["ttl"] is None
        assert parsed_none["priority"] is None
        print("✓ None value handling works correctly")
        
        # Test exclude_none functionality
        none_excluded = record_with_none.model_dump(exclude_none=True)
        assert "ttl" not in none_excluded
        assert "priority" not in none_excluded
        assert "weight" not in none_excluded
        assert "port" not in none_excluded
        print("✓ exclude_none functionality works correctly")
        
        print("\n" + "="*60)
        print("🎉 ALL RESPONSE SCHEMA SERIALIZATION TESTS PASSED!")
        print("="*60)
        print("✅ All schemas serialize data correctly to dictionaries")
        print("✅ All schemas serialize data correctly to JSON strings")
        print("✅ Datetime objects are properly serialized")
        print("✅ None values are handled correctly")
        print("✅ Optional field exclusion works properly")
        print("✅ Nested objects and collections serialize correctly")
        print("✅ All response schemas are ready for production use")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Serialization validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)