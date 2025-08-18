#!/usr/bin/env python3
"""
Test script to verify that response schemas serialize data correctly.
This tests the Pydantic schemas to ensure they properly serialize database models
and other data structures into JSON responses.
"""

import sys
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

# Test if we can import the required modules
try:
    from pydantic import BaseModel, Field
    print("✓ Pydantic is available")
except ImportError:
    print("❌ Pydantic is not installed. Please install it first.")
    print("Run: pip install pydantic==2.9.2")
    sys.exit(1)

# Add the backend app to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    # Import all schemas
    from app.schemas import (
        # DNS schemas
        Zone, DNSRecord, Forwarder, ForwarderHealth,
        # Security schemas
        ThreatFeed, RPZRule,
        # System schemas
        SystemConfig, SystemStatus, SystemMetrics,
        # Monitoring schemas
        DNSLog, SystemStats, AuditLog,
        # Auth schemas
        UserInfo, SessionInfo, ApiKeyInfo,
        # Response schemas
        PaginatedResponse, HealthCheckResult, ZoneValidationResult,
        # Enums
        ZoneType, RecordType, ForwarderType, RPZAction,
        SystemHealthStatus, MetricType, QueryType, ResourceType
    )
    print("✓ All schemas imported successfully")
except ImportError as e:
    print(f"❌ Failed to import schemas: {e}")
    print("This might be due to missing dependencies or import issues.")
    sys.exit(1)


def test_zone_serialization():
    """Test Zone schema serialization"""
    print("Testing Zone schema serialization...")
    
    # Create test data that mimics SQLAlchemy model
    zone_data = {
        'id': 1,
        'name': 'example.com',
        'zone_type': ZoneType.MASTER,
        'email': 'admin.example.com',
        'description': 'Test zone',
        'refresh': 10800,
        'retry': 3600,
        'expire': 604800,
        'minimum': 86400,
        'serial': 2024011801,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'record_count': 5
    }
    
    # Test serialization
    zone = Zone(**zone_data)
    serialized = zone.model_dump()
    
    # Verify serialization
    assert serialized['id'] == 1
    assert serialized['name'] == 'example.com'
    assert serialized['zone_type'] == 'master'
    assert serialized['is_active'] is True
    assert 'created_at' in serialized
    assert 'updated_at' in serialized
    
    # Test JSON serialization
    json_str = zone.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed['name'] == 'example.com'
    
    print("✓ Zone serialization test passed")


def test_dns_record_serialization():
    """Test DNSRecord schema serialization"""
    print("Testing DNSRecord schema serialization...")
    
    record_data = {
        'id': 1,
        'zone_id': 1,
        'name': 'www',
        'record_type': RecordType.A,
        'value': '192.168.1.100',
        'ttl': 3600,
        'priority': None,
        'weight': None,
        'port': None,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    record = DNSRecord(**record_data)
    serialized = record.model_dump()
    
    assert serialized['record_type'] == 'A'
    assert serialized['value'] == '192.168.1.100'
    assert serialized['ttl'] == 3600
    assert serialized['priority'] is None
    
    # Test with MX record (has priority)
    mx_data = record_data.copy()
    mx_data.update({
        'id': 2,
        'record_type': RecordType.MX,
        'value': 'mail.example.com',
        'priority': 10
    })
    
    mx_record = DNSRecord(**mx_data)
    mx_serialized = mx_record.model_dump()
    assert mx_serialized['priority'] == 10
    
    print("✓ DNSRecord serialization test passed")


def test_forwarder_serialization():
    """Test Forwarder schema serialization"""
    print("Testing Forwarder schema serialization...")
    
    forwarder_data = {
        'id': 1,
        'name': 'AD Forwarder',
        'domains': ['ad.company.com', 'company.local'],
        'forwarder_type': ForwarderType.ACTIVE_DIRECTORY,
        'servers': [
            {'ip': '192.168.1.10', 'port': 53, 'priority': 1},
            {'ip': '192.168.1.11', 'port': 53, 'priority': 2}
        ],
        'description': 'Active Directory DNS forwarder',
        'health_check_enabled': True,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'health_status': 'healthy'
    }
    
    forwarder = Forwarder(**forwarder_data)
    serialized = forwarder.model_dump()
    
    assert serialized['forwarder_type'] == 'active_directory'
    assert len(serialized['domains']) == 2
    assert len(serialized['servers']) == 2
    assert serialized['servers'][0]['ip'] == '192.168.1.10'
    assert serialized['health_status'] == 'healthy'
    
    print("✓ Forwarder serialization test passed")


def test_rpz_rule_serialization():
    """Test RPZRule schema serialization"""
    print("Testing RPZRule schema serialization...")
    
    rule_data = {
        'id': 1,
        'domain': 'malicious.example.com',
        'rpz_zone': 'malware',
        'action': RPZAction.BLOCK,
        'redirect_target': None,
        'description': 'Known malware domain',
        'is_active': True,
        'source': 'threat_feed',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    rule = RPZRule(**rule_data)
    serialized = rule.model_dump()
    
    assert serialized['action'] == 'block'
    assert serialized['domain'] == 'malicious.example.com'
    assert serialized['redirect_target'] is None
    
    # Test redirect rule
    redirect_data = rule_data.copy()
    redirect_data.update({
        'id': 2,
        'action': RPZAction.REDIRECT,
        'redirect_target': 'blocked.company.com'
    })
    
    redirect_rule = RPZRule(**redirect_data)
    redirect_serialized = redirect_rule.model_dump()
    assert redirect_serialized['action'] == 'redirect'
    assert redirect_serialized['redirect_target'] == 'blocked.company.com'
    
    print("✓ RPZRule serialization test passed")


def test_system_status_serialization():
    """Test SystemStatus schema serialization"""
    print("Testing SystemStatus schema serialization...")
    
    status_data = {
        'overall_status': SystemHealthStatus.HEALTHY,
        'bind9': {
            'running': True,
            'config_valid': True,
            'zones_loaded': 5,
            'queries_per_second': 10.5,
            'uptime': 86400,
            'version': '9.16.1',
            'last_reload': datetime.now(timezone.utc),
            'error_message': None
        },
        'database': {
            'connected': True,
            'connection_pool_size': 10,
            'active_connections': 3,
            'response_time': 5.2,
            'last_check': datetime.now(timezone.utc),
            'error_message': None
        },
        'services': [
            {
                'name': 'backend',
                'status': SystemHealthStatus.HEALTHY,
                'uptime': 86400,
                'last_check': datetime.now(timezone.utc),
                'error_message': None,
                'details': {'version': '1.0.0'}
            }
        ],
        'system_info': {
            'hostname': 'dns-server',
            'os': 'Ubuntu 24.04',
            'python_version': '3.10.0'
        },
        'last_updated': datetime.now(timezone.utc)
    }
    
    status = SystemStatus(**status_data)
    serialized = status.model_dump()
    
    assert serialized['overall_status'] == 'healthy'
    assert serialized['bind9']['running'] is True
    assert serialized['database']['connected'] is True
    assert len(serialized['services']) == 1
    assert serialized['services'][0]['status'] == 'healthy'
    
    print("✓ SystemStatus serialization test passed")


def test_paginated_response_serialization():
    """Test PaginatedResponse schema serialization"""
    print("Testing PaginatedResponse schema serialization...")
    
    # Create sample zone data for pagination
    zones = []
    for i in range(3):
        zone_data = {
            'id': i + 1,
            'name': f'example{i + 1}.com',
            'zone_type': ZoneType.MASTER,
            'email': f'admin.example{i + 1}.com',
            'description': f'Test zone {i + 1}',
            'refresh': 10800,
            'retry': 3600,
            'expire': 604800,
            'minimum': 86400,
            'serial': 2024011801 + i,
            'is_active': True,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'record_count': 5 + i
        }
        zones.append(Zone(**zone_data))
    
    # Create paginated response
    paginated_data = {
        'items': [zone.model_dump() for zone in zones],
        'total': 25,
        'page': 1,
        'per_page': 3,
        'pages': 9
    }
    
    paginated = PaginatedResponse(**paginated_data)
    serialized = paginated.model_dump()
    
    assert len(serialized['items']) == 3
    assert serialized['total'] == 25
    assert serialized['page'] == 1
    assert serialized['per_page'] == 3
    assert serialized['pages'] == 9
    assert serialized['items'][0]['name'] == 'example1.com'
    
    print("✓ PaginatedResponse serialization test passed")


def test_dns_log_serialization():
    """Test DNSLog schema serialization"""
    print("Testing DNSLog schema serialization...")
    
    log_data = {
        'id': 1,
        'timestamp': datetime.now(timezone.utc),
        'client_ip': '192.168.1.100',
        'query_domain': 'example.com',
        'query_type': QueryType.A,
        'response_code': 'NOERROR',
        'response_time': 15,
        'blocked': False,
        'rpz_zone': None,
        'forwarder_used': None
    }
    
    log = DNSLog(**log_data)
    serialized = log.model_dump()
    
    assert serialized['query_type'] == 'A'
    assert serialized['client_ip'] == '192.168.1.100'
    assert serialized['blocked'] is False
    assert serialized['response_time'] == 15
    
    # Test blocked query
    blocked_data = log_data.copy()
    blocked_data.update({
        'id': 2,
        'blocked': True,
        'rpz_zone': 'malware'
    })
    
    blocked_log = DNSLog(**blocked_data)
    blocked_serialized = blocked_log.model_dump()
    assert blocked_serialized['blocked'] is True
    assert blocked_serialized['rpz_zone'] == 'malware'
    
    print("✓ DNSLog serialization test passed")


def test_user_info_serialization():
    """Test UserInfo schema serialization"""
    print("Testing UserInfo schema serialization...")
    
    user_data = {
        'id': 1,
        'username': 'admin',
        'email': 'admin@example.com',
        'is_active': True,
        'is_superuser': True,
        'two_factor_enabled': True,
        'last_login': datetime.now(timezone.utc),
        'created_at': datetime.now(timezone.utc)
    }
    
    user = UserInfo(**user_data)
    serialized = user.model_dump()
    
    assert serialized['username'] == 'admin'
    assert serialized['email'] == 'admin@example.com'
    assert serialized['is_superuser'] is True
    assert serialized['two_factor_enabled'] is True
    assert 'last_login' in serialized
    
    print("✓ UserInfo serialization test passed")


def test_health_check_result_serialization():
    """Test HealthCheckResult schema serialization"""
    print("Testing HealthCheckResult schema serialization...")
    
    health_data = {
        'server_ip': '192.168.1.10',
        'status': 'healthy',
        'response_time': 25,
        'error_message': None,
        'checked_at': datetime.now(timezone.utc)
    }
    
    health = HealthCheckResult(**health_data)
    serialized = health.model_dump()
    
    assert serialized['server_ip'] == '192.168.1.10'
    assert serialized['status'] == 'healthy'
    assert serialized['response_time'] == 25
    assert serialized['error_message'] is None
    
    # Test failed health check
    failed_data = health_data.copy()
    failed_data.update({
        'status': 'failed',
        'response_time': None,
        'error_message': 'Connection timeout'
    })
    
    failed_health = HealthCheckResult(**failed_data)
    failed_serialized = failed_health.model_dump()
    assert failed_serialized['status'] == 'failed'
    assert failed_serialized['error_message'] == 'Connection timeout'
    
    print("✓ HealthCheckResult serialization test passed")


def test_zone_validation_result_serialization():
    """Test ZoneValidationResult schema serialization"""
    print("Testing ZoneValidationResult schema serialization...")
    
    validation_data = {
        'valid': True,
        'errors': [],
        'warnings': ['Zone has no NS records']
    }
    
    validation = ZoneValidationResult(**validation_data)
    serialized = validation.model_dump()
    
    assert serialized['valid'] is True
    assert len(serialized['errors']) == 0
    assert len(serialized['warnings']) == 1
    assert serialized['warnings'][0] == 'Zone has no NS records'
    
    # Test invalid zone
    invalid_data = {
        'valid': False,
        'errors': ['Invalid SOA record', 'Missing required NS record'],
        'warnings': []
    }
    
    invalid_validation = ZoneValidationResult(**invalid_data)
    invalid_serialized = invalid_validation.model_dump()
    assert invalid_serialized['valid'] is False
    assert len(invalid_serialized['errors']) == 2
    
    print("✓ ZoneValidationResult serialization test passed")


def test_json_serialization_with_datetime():
    """Test JSON serialization handles datetime objects correctly"""
    print("Testing JSON serialization with datetime objects...")
    
    zone_data = {
        'id': 1,
        'name': 'example.com',
        'zone_type': ZoneType.MASTER,
        'email': 'admin.example.com',
        'description': 'Test zone',
        'refresh': 10800,
        'retry': 3600,
        'expire': 604800,
        'minimum': 86400,
        'serial': 2024011801,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'record_count': 5
    }
    
    zone = Zone(**zone_data)
    
    # Test JSON serialization
    json_str = zone.model_dump_json()
    parsed = json.loads(json_str)
    
    # Verify datetime fields are properly serialized as ISO strings
    assert 'created_at' in parsed
    assert 'updated_at' in parsed
    assert isinstance(parsed['created_at'], str)
    assert isinstance(parsed['updated_at'], str)
    
    # Verify ISO format
    datetime.fromisoformat(parsed['created_at'].replace('Z', '+00:00'))
    datetime.fromisoformat(parsed['updated_at'].replace('Z', '+00:00'))
    
    print("✓ JSON datetime serialization test passed")


def test_enum_serialization():
    """Test that enums serialize to their string values"""
    print("Testing enum serialization...")
    
    # Test various enums
    zone_data = {
        'id': 1,
        'name': 'example.com',
        'zone_type': ZoneType.MASTER,
        'email': 'admin.example.com',
        'description': 'Test zone',
        'refresh': 10800,
        'retry': 3600,
        'expire': 604800,
        'minimum': 86400,
        'serial': 2024011801,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'record_count': 5
    }
    
    zone = Zone(**zone_data)
    serialized = zone.model_dump()
    
    # Verify enum serializes to string value
    assert serialized['zone_type'] == 'master'
    assert isinstance(serialized['zone_type'], str)
    
    # Test record type enum
    record_data = {
        'id': 1,
        'zone_id': 1,
        'name': 'www',
        'record_type': RecordType.AAAA,
        'value': '2001:db8::1',
        'ttl': 3600,
        'priority': None,
        'weight': None,
        'port': None,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    record = DNSRecord(**record_data)
    record_serialized = record.model_dump()
    assert record_serialized['record_type'] == 'AAAA'
    
    print("✓ Enum serialization test passed")


def test_optional_fields_serialization():
    """Test serialization of optional fields (None values)"""
    print("Testing optional fields serialization...")
    
    # Test record with optional fields as None
    record_data = {
        'id': 1,
        'zone_id': 1,
        'name': 'www',
        'record_type': RecordType.A,
        'value': '192.168.1.100',
        'ttl': None,  # Optional field
        'priority': None,  # Optional field
        'weight': None,  # Optional field
        'port': None,  # Optional field
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    record = DNSRecord(**record_data)
    serialized = record.model_dump()
    
    # Verify None values are preserved
    assert serialized['ttl'] is None
    assert serialized['priority'] is None
    assert serialized['weight'] is None
    assert serialized['port'] is None
    
    # Test with exclude_none option
    serialized_no_none = record.model_dump(exclude_none=True)
    assert 'ttl' not in serialized_no_none
    assert 'priority' not in serialized_no_none
    assert 'weight' not in serialized_no_none
    assert 'port' not in serialized_no_none
    
    print("✓ Optional fields serialization test passed")


def test_nested_object_serialization():
    """Test serialization of nested objects"""
    print("Testing nested object serialization...")
    
    # Test forwarder with nested server objects
    forwarder_data = {
        'id': 1,
        'name': 'Test Forwarder',
        'domains': ['test.com'],
        'forwarder_type': ForwarderType.PUBLIC,
        'servers': [
            {'ip': '8.8.8.8', 'port': 53, 'priority': 1},
            {'ip': '8.8.4.4', 'port': 53, 'priority': 2}
        ],
        'description': 'Public DNS forwarder',
        'health_check_enabled': True,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'health_status': 'healthy'
    }
    
    forwarder = Forwarder(**forwarder_data)
    serialized = forwarder.model_dump()
    
    # Verify nested objects are properly serialized
    assert len(serialized['servers']) == 2
    assert serialized['servers'][0]['ip'] == '8.8.8.8'
    assert serialized['servers'][0]['port'] == 53
    assert serialized['servers'][0]['priority'] == 1
    assert serialized['servers'][1]['ip'] == '8.8.4.4'
    
    print("✓ Nested object serialization test passed")


def run_all_tests():
    """Run all serialization tests"""
    print("Running response schema serialization tests...\n")
    
    try:
        test_zone_serialization()
        test_dns_record_serialization()
        test_forwarder_serialization()
        test_rpz_rule_serialization()
        test_system_status_serialization()
        test_paginated_response_serialization()
        test_dns_log_serialization()
        test_user_info_serialization()
        test_health_check_result_serialization()
        test_zone_validation_result_serialization()
        test_json_serialization_with_datetime()
        test_enum_serialization()
        test_optional_fields_serialization()
        test_nested_object_serialization()
        
        print("\n" + "="*50)
        print("✅ ALL RESPONSE SCHEMA SERIALIZATION TESTS PASSED!")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)