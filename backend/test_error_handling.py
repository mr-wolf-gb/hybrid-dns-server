#!/usr/bin/env python3
"""
Test script to verify error handling improvements
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from pydantic import ValidationError
from app.schemas.dns import ZoneCreate, DNSRecordCreate, ForwarderCreate
from app.schemas.security import RPZRuleCreate
from app.core.validation_helpers import DNSValidationHelper
from app.core.exceptions import create_validation_error_response


def test_zone_validation():
    """Test zone validation with helpful error messages"""
    print("Testing Zone Validation...")
    
    # Test invalid zone data
    invalid_zone_data = {
        "name": "",  # Empty name
        "zone_type": "invalid_type",  # Invalid type
        "email": "admin@example.com",  # Wrong email format
        "refresh": 100,  # Too short
        "expire": 100  # Too short
    }
    
    try:
        zone = ZoneCreate(**invalid_zone_data)
        print("❌ Zone validation should have failed")
    except ValidationError as e:
        print("✅ Zone validation failed as expected")
        print("Validation errors:")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")
    
    # Test with validation helper
    is_valid, errors, suggestions = DNSValidationHelper.validate_zone_data(invalid_zone_data)
    print(f"\nValidation Helper Results:")
    print(f"Valid: {is_valid}")
    print(f"Errors: {errors}")
    print(f"Suggestions: {suggestions}")


def test_record_validation():
    """Test DNS record validation with helpful error messages"""
    print("\nTesting DNS Record Validation...")
    
    # Test invalid record data
    invalid_record_data = {
        "name": "",  # Empty name
        "record_type": "A",
        "value": "invalid_ip",  # Invalid IP
        "ttl": 30  # Too short
    }
    
    try:
        record = DNSRecordCreate(**invalid_record_data)
        print("❌ Record validation should have failed")
    except ValidationError as e:
        print("✅ Record validation failed as expected")
        print("Validation errors:")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")
    
    # Test SRV record without required fields
    srv_record_data = {
        "name": "_http._tcp",
        "record_type": "SRV",
        "value": "server.example.com"
        # Missing priority, weight, port
    }
    
    try:
        record = DNSRecordCreate(**srv_record_data)
        print("❌ SRV record validation should have failed")
    except ValidationError as e:
        print("✅ SRV record validation failed as expected")
        print("SRV validation errors:")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")


def test_forwarder_validation():
    """Test forwarder validation with helpful error messages"""
    print("\nTesting Forwarder Validation...")
    
    # Test invalid forwarder data
    invalid_forwarder_data = {
        "name": "",  # Empty name
        "domains": [],  # Empty domains
        "forwarder_type": "active_directory",
        "servers": []  # Empty servers
    }
    
    try:
        forwarder = ForwarderCreate(**invalid_forwarder_data)
        print("❌ Forwarder validation should have failed")
    except ValidationError as e:
        print("✅ Forwarder validation failed as expected")
        print("Validation errors:")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")


def test_rpz_validation():
    """Test RPZ rule validation with helpful error messages"""
    print("\nTesting RPZ Rule Validation...")
    
    # Test redirect rule without target
    invalid_rpz_data = {
        "domain": "malicious.com",
        "rpz_zone": "malware",
        "action": "redirect"
        # Missing redirect_target
    }
    
    try:
        rule = RPZRuleCreate(**invalid_rpz_data)
        print("❌ RPZ rule validation should have failed")
    except ValidationError as e:
        print("✅ RPZ rule validation failed as expected")
        print("Validation errors:")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")


def test_validation_helper():
    """Test the validation helper functions"""
    print("\nTesting Validation Helper Functions...")
    
    # Test zone validation helper
    zone_data = {
        "name": "example.com",
        "zone_type": "master",
        "email": "admin.example.com",
        "refresh": 3600
    }
    
    is_valid, errors, suggestions = DNSValidationHelper.validate_zone_data(zone_data)
    print(f"Valid zone data - Valid: {is_valid}, Errors: {len(errors)}, Suggestions: {len(suggestions)}")
    
    # Test record validation helper
    record_data = {
        "name": "www",
        "record_type": "A",
        "value": "192.168.1.1",
        "ttl": 3600
    }
    
    is_valid, errors, suggestions = DNSValidationHelper.validate_record_data(record_data)
    print(f"Valid record data - Valid: {is_valid}, Errors: {len(errors)}, Suggestions: {len(suggestions)}")


if __name__ == "__main__":
    print("🧪 Testing Error Handling Improvements")
    print("=" * 50)
    
    test_zone_validation()
    test_record_validation()
    test_forwarder_validation()
    test_rpz_validation()
    test_validation_helper()
    
    print("\n" + "=" * 50)
    print("✅ Error handling tests completed!")
    print("\nKey improvements implemented:")
    print("- Clear, contextual error messages")
    print("- Actionable suggestions for fixing errors")
    print("- Detailed validation information")
    print("- Consistent error response format")
    print("- Field-specific validation with helpful hints")