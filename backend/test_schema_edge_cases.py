#!/usr/bin/env python3
"""
Test script to validate edge cases in response schema serialization.
This script tests various edge cases and error conditions to ensure
robust serialization behavior.
"""

import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
import json

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from schemas import (
        # DNS schemas
        Zone, DNSRecord, Forwarder, ForwarderHealth,
        # Security schemas  
        ThreatFeed, RPZRule,
        # System schemas
        SystemConfig, SystemStatus, SystemMetrics, SystemInfo,
        # Monitoring schemas
        DNSLog, SystemStats, AuditLog,
        # Auth schemas
        UserInfo, SessionInfo, ApiKeyInfo,
        # Response schemas
        PaginatedResponse, HealthCheckResult, ZoneValidationResult,
        # Enums
        ZoneType, RecordType, ForwarderType, RPZAction,
        FeedType, FormatType, UpdateStatus,
        ValueType, ConfigCategory, SystemHealthStatus,
        MetricType, QueryType, ResourceType
    )
    print("✓ Successfully imported all schemas")
except ImportError as e:
    print(f"✗ Failed to import schemas: {e}")
    sys.exit(1)


def test_large_data_serialization():
    """Test serialization with large datasets"""
    print("\n=== Testing Large Data Serialization ===")
    
    try:
        # Create a large list of DNS records
        large_record_list = []
        for i in range(1000):
            record_data = {
                'id': i + 1,
                'zone_id': 1,
                'name': f'host{i:04d}',
                'record_type': RecordType.A,
                'value': f'192.168.{(i // 256) % 256}.{i % 256}',
                'ttl': 3600,
                'priority': None,
                'weight': None,
                'port': None,
                'is_active': True,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            large_record_list.append(DNSRecord(**record_data))
        
        # Test paginated response with large dataset
        paginated_data = {
            'items': large_record_list,
            'total': 10000,
            'page': 1,
            'per_page': 1000,
            'pages': 10
        }
        
        paginated = PaginatedResponse(**paginated_data)
        
        # Test JSON serialization (this should not crash)
        json_str = paginated.model_dump_json()
        parsed = json.loads(json_str)
        
        assert len(parsed['items']) == 1000
        assert parsed['total'] == 10000
        
        print("✓ Large data serialization successful")
        return True
        
    except Exception as e:
        print(f"✗ Large data serialization failed: {e}")
        return False


def test_unicode_content_serialization():
    """Test serialization with Unicode content"""
    print("\n=== Testing Unicode Content Serialization ===")
    
    try:
        # Test with various Unicode characters
        unicode_test_cases = [
            'café.example.com',  # Accented characters
            'тест.example.com',  # Cyrillic
            '测试.example.com',   # Chinese
            'テスト.example.com',  # Japanese
            '🌟.example.com',    # Emoji (though not valid DNS)
            'xn--nxasmq6b.example.com'  # Punycode
        ]
        
        for i, domain in enumerate(unicode_test_cases):
            try:
                zone_data = {
                    'id': i + 1,
                    'name': domain,
                    'zone_type': ZoneType.MASTER,
                    'email': 'admin.example.com',
                    'description': f'Unicode test zone: {domain}',
                    'refresh': 10800,
                    'retry': 3600,
                    'expire': 604800,
                    'minimum': 86400,
                    'serial': 2024011801,
                    'is_active': True,
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc),
                    'record_count': 1
                }
                
                # Some domains will fail validation, which is expected
                zone = Zone(**zone_data)
                json_str = zone.model_dump_json()
                parsed = json.loads(json_str)
                
                # Verify Unicode is properly handled in JSON
                assert isinstance(parsed['name'], str)
                assert isinstance(parsed['description'], str)
                
            except ValueError:
                # Expected for invalid domain names like emoji
                continue
        
        print("✓ Unicode content serialization successful")
        return True
        
    except Exception as e:
        print(f"✗ Unicode content serialization failed: {e}")
        return False


def test_nested_object_serialization():
    """Test serialization of deeply nested objects"""
    print("\n=== Testing Nested Object Serialization ===")
    
    try:
        from schemas.system import ServiceStatus, DatabaseStatus, BindStatus
        
        # Create deeply nested system status
        services = []
        for i in range(10):
            service = ServiceStatus(
                name=f'service-{i}',
                status=SystemHealthStatus.HEALTHY,
                uptime=86400 + i * 1000,
                last_check=datetime.now(timezone.utc),
                error_message=None,
                details={
                    'version': f'1.{i}.0',
                    'config': {
                        'nested': {
                            'deeply': {
                                'nested': {
                                    'value': f'test-{i}'
                                }
                            }
                        }
                    },
                    'metrics': [
                        {'name': 'cpu', 'value': i * 10.5},
                        {'name': 'memory', 'value': i * 20.3}
                    ]
                }
            )
            services.append(service)
        
        system_status_data = {
            'overall_status': SystemHealthStatus.HEALTHY,
            'bind9': BindStatus(
                running=True,
                config_valid=True,
                zones_loaded=100,
                queries_per_second=50.5,
                uptime=86400,
                version='9.16.1',
                last_reload=datetime.now(timezone.utc),
                error_message=None
            ),
            'database': DatabaseStatus(
                connected=True,
                connection_pool_size=20,
                active_connections=5,
                response_time=2.5,
                last_check=datetime.now(timezone.utc),
                error_message=None
            ),
            'services': services,
            'system_info': {
                'hostname': 'dns-server-01',
                'os': 'Ubuntu 24.04 LTS',
                'python_version': '3.10.12',
                'nested_config': {
                    'level1': {
                        'level2': {
                            'level3': {
                                'deep_value': 'success'
                            }
                        }
                    }
                }
            },
            'last_updated': datetime.now(timezone.utc)
        }
        
        system_status = SystemStatus(**system_status_data)
        json_str = system_status.model_dump_json()
        parsed = json.loads(json_str)
        
        # Verify nested structures are preserved
        assert len(parsed['services']) == 10
        assert parsed['services'][0]['details']['config']['nested']['deeply']['nested']['value'] == 'test-0'
        assert parsed['system_info']['nested_config']['level1']['level2']['level3']['deep_value'] == 'success'
        
        print("✓ Nested object serialization successful")
        return True
        
    except Exception as e:
        print(f"✗ Nested object serialization failed: {e}")
        return False


def test_empty_collections_serialization():
    """Test serialization with empty collections"""
    print("\n=== Testing Empty Collections Serialization ===")
    
    try:
        # Test empty paginated response
        empty_paginated = PaginatedResponse(
            items=[],
            total=0,
            page=1,
            per_page=10,
            pages=0
        )
        
        serialized = empty_paginated.model_dump()
        assert serialized['items'] == []
        assert serialized['total'] == 0
        
        # Test forwarder with empty domains list (should fail validation)
        try:
            forwarder_data = {
                'id': 1,
                'name': 'Empty Forwarder',
                'domains': [],  # This should fail validation
                'forwarder_type': ForwarderType.PUBLIC,
                'servers': [{'ip': '8.8.8.8', 'port': 53, 'priority': 1}],
                'description': 'Test forwarder',
                'health_check_enabled': True,
                'is_active': True,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'health_status': 'healthy'
            }
            
            forwarder = Forwarder(**forwarder_data)
            # This should not reach here due to validation
            assert False, "Empty domains list should fail validation"
            
        except ValueError:
            # Expected - empty domains should fail validation
            pass
        
        # Test validation result with empty errors/warnings
        validation = ZoneValidationResult(
            valid=True,
            errors=[],
            warnings=[]
        )
        
        serialized = validation.model_dump()
        assert serialized['errors'] == []
        assert serialized['warnings'] == []
        assert serialized['valid'] is True
        
        print("✓ Empty collections serialization successful")
        return True
        
    except Exception as e:
        print(f"✗ Empty collections serialization failed: {e}")
        return False


def test_boundary_values_serialization():
    """Test serialization with boundary values"""
    print("\n=== Testing Boundary Values Serialization ===")
    
    try:
        # Test with maximum valid values (within schema constraints)
        long_domain = 'a' * 60 + '.' + 'b' * 60 + '.com'  # Long but valid domain
        zone_data = {
            'id': 2147483647,  # Max 32-bit int
            'name': long_domain,  # Long valid domain
            'zone_type': ZoneType.MASTER,
            'email': 'admin.example.com',
            'description': 'x' * 500,  # Max description length
            'refresh': 86400,    # Max allowed refresh
            'retry': 86400,     # Max allowed retry
            'expire': 2419200,  # Max allowed expire
            'minimum': 86400,   # Max allowed minimum
            'serial': 4294967295,  # Max 32-bit unsigned int
            'is_active': True,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'record_count': 2147483647
        }
        
        zone = Zone(**zone_data)
        serialized = zone.model_dump()
        
        # Verify boundary values are preserved
        assert serialized['id'] == 2147483647
        assert serialized['refresh'] == 86400
        assert serialized['serial'] == 4294967295
        
        # Test with minimum values
        zone_data_min = {
            'id': 1,
            'name': 'ab.cd',  # Minimum valid domain (2 char labels)
            'zone_type': ZoneType.MASTER,
            'email': 'admin.example.com',  # Valid email
            'description': None,
            'refresh': 300,    # Min refresh (5 minutes)
            'retry': 300,     # Min retry
            'expire': 86400,  # Min expire (1 day)
            'minimum': 300,   # Min minimum
            'serial': 1,
            'is_active': False,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'record_count': 0
        }
        
        zone_min = Zone(**zone_data_min)
        serialized_min = zone_min.model_dump()
        
        assert serialized_min['refresh'] == 300
        assert serialized_min['record_count'] == 0
        
        print("✓ Boundary values serialization successful")
        return True
        
    except Exception as e:
        print(f"✗ Boundary values serialization failed: {e}")
        return False


def test_datetime_edge_cases():
    """Test datetime serialization edge cases"""
    print("\n=== Testing DateTime Edge Cases ===")
    
    try:
        # Test with various datetime formats
        test_datetimes = [
            datetime.min.replace(tzinfo=timezone.utc),  # Minimum datetime
            datetime.max.replace(tzinfo=timezone.utc),  # Maximum datetime
            datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc),  # Y2K
            datetime(2038, 1, 19, 3, 14, 7, tzinfo=timezone.utc),  # Unix timestamp limit
            datetime.now(timezone.utc),  # Current time
        ]
        
        for i, test_dt in enumerate(test_datetimes):
            try:
                zone_data = {
                    'id': i + 1,
                    'name': f'test{i}.com',
                    'zone_type': ZoneType.MASTER,
                    'email': 'admin.example.com',
                    'description': f'Test zone {i}',
                    'refresh': 10800,
                    'retry': 3600,
                    'expire': 604800,
                    'minimum': 86400,
                    'serial': 2024011801,
                    'is_active': True,
                    'created_at': test_dt,
                    'updated_at': test_dt,
                    'record_count': 1
                }
                
                zone = Zone(**zone_data)
                json_str = zone.model_dump_json()
                parsed = json.loads(json_str)
                
                # Verify datetime is properly serialized
                assert 'created_at' in parsed
                assert isinstance(parsed['created_at'], str)
                
            except (ValueError, OverflowError):
                # Some extreme datetimes might not be serializable
                continue
        
        print("✓ DateTime edge cases serialization successful")
        return True
        
    except Exception as e:
        print(f"✗ DateTime edge cases serialization failed: {e}")
        return False


def test_json_serialization_consistency():
    """Test that model_dump() and model_dump_json() are consistent"""
    print("\n=== Testing JSON Serialization Consistency ===")
    
    try:
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
        
        # Get both serialization formats
        dict_dump = zone.model_dump()
        json_str = zone.model_dump_json()
        json_parsed = json.loads(json_str)
        
        # Compare all fields except datetime (which has different formats)
        for key, value in dict_dump.items():
            if key in ['created_at', 'updated_at']:
                # Skip datetime comparison as formats differ
                continue
            
            assert key in json_parsed, f"Key {key} missing from JSON serialization"
            assert json_parsed[key] == value, f"Value mismatch for {key}: {json_parsed[key]} != {value}"
        
        # Verify datetime fields are present in JSON
        assert 'created_at' in json_parsed
        assert 'updated_at' in json_parsed
        assert isinstance(json_parsed['created_at'], str)
        assert isinstance(json_parsed['updated_at'], str)
        
        print("✓ JSON serialization consistency successful")
        return True
        
    except Exception as e:
        print(f"✗ JSON serialization consistency failed: {e}")
        return False


def main():
    """Run all edge case tests"""
    print("Starting Response Schema Edge Case Tests")
    print("=" * 50)
    
    tests = [
        test_large_data_serialization,
        test_unicode_content_serialization,
        test_nested_object_serialization,
        test_empty_collections_serialization,
        test_boundary_values_serialization,
        test_datetime_edge_cases,
        test_json_serialization_consistency
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Edge Case Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All edge case tests passed!")
        return 0
    else:
        print("❌ Some edge case tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())