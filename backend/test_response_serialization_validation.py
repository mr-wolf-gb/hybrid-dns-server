#!/usr/bin/env python3
"""
Test script to validate that response schemas serialize data correctly.
This script tests all response schemas to ensure they properly serialize
database model data and handle edge cases.
"""

import sys
import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

# Test if we can import the schemas
try:
    # Add the backend directory to the Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
    
    # Try importing pydantic first
    import pydantic
    print(f"Using Pydantic version: {pydantic.VERSION}")
    
    # Import all schemas
    from app.schemas import (
        # DNS schemas
        Zone, DNSRecord, Forwarder, ForwarderHealth,
        PaginatedResponse, HealthCheckResult, ZoneValidationResult, ValidationResult,
        # Security schemas
        ThreatFeed, RPZRule, ThreatFeedStatus, ThreatFeedUpdateResult,
        BulkThreatFeedUpdateResult, RPZRuleImportResult,
        # System schemas
        SystemConfig, SystemConfigPublic, ServiceStatus, DatabaseStatus,
        BindStatus, SystemStatus, SystemMetrics, SystemInfo, BackupStatus,
        MaintenanceStatus, SystemSummary, ConfigValidationResult,
        BulkConfigUpdate, BulkConfigUpdateResult,
        # Monitoring schemas
        DNSLog, SystemStats, AuditLog, DNSQueryStats, SystemMetricsSummary,
        AuditSummary, MonitoringDashboard,
        # Auth schemas
        LoginResponse, TokenResponse, TwoFactorSetupResponse, UserInfo,
        SessionInfo, ApiKeyInfo,
        # Enums
        ZoneType, RecordType, ForwarderType, RPZAction, FeedType, FormatType,
        UpdateStatus, ValueType, ConfigCategory, SystemHealthStatus,
        MetricType, QueryType, ResourceType
    )
    
    SCHEMAS_AVAILABLE = True
    
except ImportError as e:
    print(f"Warning: Could not import schemas: {e}")
    print("This test will validate schema structure instead of runtime serialization.")
    SCHEMAS_AVAILABLE = False


class MockModel:
    """Mock database model for testing serialization"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_zone_serialization():
    """Test Zone schema serialization"""
    print("Testing Zone schema serialization...")
    
    # Create mock zone data
    mock_zone = MockModel(
        id=1,
        name="example.com",
        zone_type="master",
        email="admin.example.com",
        description="Test zone",
        refresh=10800,
        retry=3600,
        expire=604800,
        minimum=86400,
        serial=2024011801,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        record_count=5
    )
    
    try:
        zone_schema = Zone.model_validate(mock_zone)
        serialized = zone_schema.model_dump()
        
        # Verify required fields are present
        assert 'id' in serialized
        assert 'name' in serialized
        assert 'zone_type' in serialized
        assert 'email' in serialized
        assert 'created_at' in serialized
        assert 'updated_at' in serialized
        
        # Verify data types
        assert isinstance(serialized['id'], int)
        assert isinstance(serialized['name'], str)
        assert isinstance(serialized['is_active'], bool)
        
        # Test JSON serialization
        json_str = zone_schema.model_dump_json()
        json_data = json.loads(json_str)
        assert json_data['name'] == "example.com"
        
        print("✓ Zone schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ Zone schema serialization failed: {e}")
        return False


def test_dns_record_serialization():
    """Test DNSRecord schema serialization"""
    print("Testing DNSRecord schema serialization...")
    
    mock_record = MockModel(
        id=1,
        zone_id=1,
        name="www",
        record_type="A",
        value="192.168.1.100",
        ttl=3600,
        priority=None,
        weight=None,
        port=None,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    try:
        record_schema = DNSRecord.model_validate(mock_record)
        serialized = record_schema.model_dump()
        
        # Verify required fields
        assert 'id' in serialized
        assert 'zone_id' in serialized
        assert 'name' in serialized
        assert 'record_type' in serialized
        assert 'value' in serialized
        
        # Test with optional fields as None
        assert serialized['priority'] is None
        assert serialized['weight'] is None
        assert serialized['port'] is None
        
        # Test JSON serialization
        json_str = record_schema.model_dump_json()
        json_data = json.loads(json_str)
        assert json_data['record_type'] == "A"
        
        print("✓ DNSRecord schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ DNSRecord schema serialization failed: {e}")
        return False


def test_forwarder_serialization():
    """Test Forwarder schema serialization"""
    print("Testing Forwarder schema serialization...")
    
    mock_forwarder = MockModel(
        id=1,
        name="AD Forwarder",
        domains=["ad.company.com", "company.local"],
        forwarder_type="active_directory",
        servers=[
            {"ip": "192.168.1.10", "port": 53, "priority": 1},
            {"ip": "192.168.1.11", "port": 53, "priority": 2}
        ],
        description="Active Directory DNS forwarder",
        health_check_enabled=True,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        health_status="healthy"
    )
    
    try:
        forwarder_schema = Forwarder.model_validate(mock_forwarder)
        serialized = forwarder_schema.model_dump()
        
        # Verify required fields
        assert 'id' in serialized
        assert 'name' in serialized
        assert 'domains' in serialized
        assert 'servers' in serialized
        assert 'forwarder_type' in serialized
        
        # Verify complex data types
        assert isinstance(serialized['domains'], list)
        assert isinstance(serialized['servers'], list)
        assert len(serialized['servers']) == 2
        
        # Test JSON serialization
        json_str = forwarder_schema.model_dump_json()
        json_data = json.loads(json_str)
        assert json_data['forwarder_type'] == "active_directory"
        
        print("✓ Forwarder schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ Forwarder schema serialization failed: {e}")
        return False


def test_forwarder_health_serialization():
    """Test ForwarderHealth schema serialization"""
    print("Testing ForwarderHealth schema serialization...")
    
    mock_health = MockModel(
        id=1,
        forwarder_id=1,
        server_ip="192.168.1.10",
        status="healthy",
        response_time=25,
        error_message=None,
        checked_at=datetime.now(timezone.utc)
    )
    
    try:
        health_schema = ForwarderHealth.model_validate(mock_health)
        serialized = health_schema.model_dump()
        
        # Verify required fields
        assert 'id' in serialized
        assert 'forwarder_id' in serialized
        assert 'server_ip' in serialized
        assert 'status' in serialized
        assert 'checked_at' in serialized
        
        # Test optional fields
        assert serialized['response_time'] == 25
        assert serialized['error_message'] is None
        
        print("✓ ForwarderHealth schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ ForwarderHealth schema serialization failed: {e}")
        return False


def test_rpz_rule_serialization():
    """Test RPZRule schema serialization"""
    print("Testing RPZRule schema serialization...")
    
    mock_rule = MockModel(
        id=1,
        domain="malicious.example.com",
        rpz_zone="malware",
        action="block",
        redirect_target=None,
        description="Malicious domain blocked by threat feed",
        is_active=True,
        source="threat_feed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    try:
        rule_schema = RPZRule.model_validate(mock_rule)
        serialized = rule_schema.model_dump()
        
        # Verify required fields
        assert 'id' in serialized
        assert 'domain' in serialized
        assert 'rpz_zone' in serialized
        assert 'action' in serialized
        
        # Test optional fields
        assert serialized['redirect_target'] is None
        assert serialized['source'] == "threat_feed"
        
        print("✓ RPZRule schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ RPZRule schema serialization failed: {e}")
        return False


def test_threat_feed_serialization():
    """Test ThreatFeed schema serialization"""
    print("Testing ThreatFeed schema serialization...")
    
    mock_feed = MockModel(
        id=1,
        name="Malware Domains",
        url="https://example.com/malware-domains.txt",
        feed_type="malware",
        format_type="domains",
        update_frequency=3600,
        description="List of known malware domains",
        is_active=True,
        last_updated=datetime.now(timezone.utc),
        last_update_status="success",
        last_update_error=None,
        rules_count=1500,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    try:
        feed_schema = ThreatFeed.model_validate(mock_feed)
        serialized = feed_schema.model_dump()
        
        # Verify required fields
        assert 'id' in serialized
        assert 'name' in serialized
        assert 'url' in serialized
        assert 'feed_type' in serialized
        assert 'format_type' in serialized
        
        # Test optional fields
        assert serialized['last_update_error'] is None
        assert serialized['rules_count'] == 1500
        
        print("✓ ThreatFeed schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ ThreatFeed schema serialization failed: {e}")
        return False


def test_system_config_serialization():
    """Test SystemConfig schema serialization"""
    print("Testing SystemConfig schema serialization...")
    
    mock_config = MockModel(
        id=1,
        key="dns.default_ttl",
        value="3600",
        value_type="integer",
        category="dns",
        description="Default TTL for DNS records",
        is_sensitive=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    try:
        config_schema = SystemConfig.model_validate(mock_config)
        serialized = config_schema.model_dump()
        
        # Verify required fields
        assert 'id' in serialized
        assert 'key' in serialized
        assert 'value' in serialized
        assert 'value_type' in serialized
        assert 'category' in serialized
        
        print("✓ SystemConfig schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ SystemConfig schema serialization failed: {e}")
        return False


def test_system_status_serialization():
    """Test SystemStatus schema serialization"""
    print("Testing SystemStatus schema serialization...")
    
    mock_bind_status = {
        "running": True,
        "config_valid": True,
        "zones_loaded": 5,
        "queries_per_second": 10.5,
        "uptime": 86400,
        "version": "9.16.1",
        "last_reload": datetime.now(timezone.utc),
        "error_message": None
    }
    
    mock_db_status = {
        "connected": True,
        "connection_pool_size": 10,
        "active_connections": 3,
        "response_time": 2.5,
        "last_check": datetime.now(timezone.utc),
        "error_message": None
    }
    
    mock_service_status = {
        "name": "monitoring",
        "status": "healthy",
        "uptime": 3600,
        "last_check": datetime.now(timezone.utc),
        "error_message": None,
        "details": {"version": "1.0.0"}
    }
    
    mock_status = {
        "overall_status": "healthy",
        "bind9": mock_bind_status,
        "database": mock_db_status,
        "services": [mock_service_status],
        "system_info": {"hostname": "dns-server", "os": "Ubuntu 24.04"},
        "last_updated": datetime.now(timezone.utc)
    }
    
    try:
        status_schema = SystemStatus.model_validate(mock_status)
        serialized = status_schema.model_dump()
        
        # Verify required fields
        assert 'overall_status' in serialized
        assert 'bind9' in serialized
        assert 'database' in serialized
        assert 'services' in serialized
        assert 'last_updated' in serialized
        
        # Verify nested objects
        assert serialized['bind9']['running'] is True
        assert serialized['database']['connected'] is True
        assert len(serialized['services']) == 1
        
        print("✓ SystemStatus schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ SystemStatus schema serialization failed: {e}")
        return False


def test_paginated_response_serialization():
    """Test PaginatedResponse schema serialization"""
    print("Testing PaginatedResponse schema serialization...")
    
    # Create mock zone data for pagination
    mock_zones = [
        {"id": 1, "name": "example.com", "zone_type": "master"},
        {"id": 2, "name": "test.com", "zone_type": "master"}
    ]
    
    mock_paginated = {
        "items": mock_zones,
        "total": 2,
        "page": 1,
        "per_page": 10,
        "pages": 1
    }
    
    try:
        paginated_schema = PaginatedResponse.model_validate(mock_paginated)
        serialized = paginated_schema.model_dump()
        
        # Verify required fields
        assert 'items' in serialized
        assert 'total' in serialized
        assert 'page' in serialized
        assert 'per_page' in serialized
        assert 'pages' in serialized
        
        # Verify data types
        assert isinstance(serialized['items'], list)
        assert len(serialized['items']) == 2
        assert serialized['total'] == 2
        
        print("✓ PaginatedResponse schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ PaginatedResponse schema serialization failed: {e}")
        return False


def test_health_check_result_serialization():
    """Test HealthCheckResult schema serialization"""
    print("Testing HealthCheckResult schema serialization...")
    
    mock_health_result = {
        "server_ip": "192.168.1.10",
        "status": "healthy",
        "response_time": 25,
        "error_message": None,
        "checked_at": datetime.now(timezone.utc)
    }
    
    try:
        health_schema = HealthCheckResult.model_validate(mock_health_result)
        serialized = health_schema.model_dump()
        
        # Verify required fields
        assert 'server_ip' in serialized
        assert 'status' in serialized
        assert 'checked_at' in serialized
        
        # Test optional fields
        assert serialized['response_time'] == 25
        assert serialized['error_message'] is None
        
        print("✓ HealthCheckResult schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ HealthCheckResult schema serialization failed: {e}")
        return False


def test_validation_result_serialization():
    """Test ValidationResult schema serialization"""
    print("Testing ValidationResult schema serialization...")
    
    mock_validation = {
        "valid": True,
        "errors": [],
        "warnings": ["Zone serial number is in the past"]
    }
    
    try:
        validation_schema = ValidationResult.model_validate(mock_validation)
        serialized = validation_schema.model_dump()
        
        # Verify required fields
        assert 'valid' in serialized
        assert 'errors' in serialized
        assert 'warnings' in serialized
        
        # Verify data types
        assert isinstance(serialized['valid'], bool)
        assert isinstance(serialized['errors'], list)
        assert isinstance(serialized['warnings'], list)
        
        print("✓ ValidationResult schema serialization passed")
        return True
        
    except Exception as e:
        print(f"✗ ValidationResult schema serialization failed: {e}")
        return False


def test_monitoring_schemas_serialization():
    """Test monitoring schema serialization"""
    print("Testing monitoring schemas serialization...")
    
    # Test DNSLog
    mock_dns_log = MockModel(
        id=1,
        timestamp=datetime.now(timezone.utc),
        client_ip="192.168.1.100",
        query_domain="example.com",
        query_type="A",
        response_code="NOERROR",
        response_time=15,
        blocked=False,
        rpz_zone=None,
        forwarder_used="192.168.1.10"
    )
    
    try:
        dns_log_schema = DNSLog.model_validate(mock_dns_log)
        serialized = dns_log_schema.model_dump()
        
        assert 'id' in serialized
        assert 'client_ip' in serialized
        assert 'query_domain' in serialized
        assert serialized['blocked'] is False
        
        print("✓ DNSLog schema serialization passed")
        
    except Exception as e:
        print(f"✗ DNSLog schema serialization failed: {e}")
        return False
    
    # Test SystemStats
    mock_system_stats = MockModel(
        id=1,
        timestamp=datetime.now(timezone.utc),
        metric_name="cpu_usage",
        metric_value="45.2",
        metric_type="gauge"
    )
    
    try:
        stats_schema = SystemStats.model_validate(mock_system_stats)
        serialized = stats_schema.model_dump()
        
        assert 'id' in serialized
        assert 'metric_name' in serialized
        assert 'metric_value' in serialized
        assert 'metric_type' in serialized
        
        print("✓ SystemStats schema serialization passed")
        
    except Exception as e:
        print(f"✗ SystemStats schema serialization failed: {e}")
        return False
    
    return True


def test_auth_schemas_serialization():
    """Test authentication schema serialization"""
    print("Testing authentication schemas serialization...")
    
    # Test UserInfo
    mock_user = MockModel(
        id=1,
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_superuser=True,
        two_factor_enabled=False,
        last_login=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    
    try:
        user_schema = UserInfo.model_validate(mock_user)
        serialized = user_schema.model_dump()
        
        assert 'id' in serialized
        assert 'username' in serialized
        assert 'email' in serialized
        assert 'is_active' in serialized
        
        print("✓ UserInfo schema serialization passed")
        
    except Exception as e:
        print(f"✗ UserInfo schema serialization failed: {e}")
        return False
    
    # Test LoginResponse
    mock_login_response = {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "refresh_token_here",
        "token_type": "bearer",
        "session_token": "session_token_here",
        "requires_2fa": False,
        "temporary_token": None
    }
    
    try:
        login_schema = LoginResponse.model_validate(mock_login_response)
        serialized = login_schema.model_dump()
        
        assert 'access_token' in serialized
        assert 'token_type' in serialized
        assert serialized['requires_2fa'] is False
        
        print("✓ LoginResponse schema serialization passed")
        
    except Exception as e:
        print(f"✗ LoginResponse schema serialization failed: {e}")
        return False
    
    return True


def test_edge_cases():
    """Test edge cases and error handling"""
    print("Testing edge cases and error handling...")
    
    # Test with None values
    try:
        mock_zone_with_nones = MockModel(
            id=1,
            name="example.com",
            zone_type="master",
            email="admin.example.com",
            description=None,  # Optional field as None
            refresh=10800,
            retry=3600,
            expire=604800,
            minimum=86400,
            serial=None,  # Optional field as None
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            record_count=0
        )
        
        zone_schema = Zone.model_validate(mock_zone_with_nones)
        serialized = zone_schema.model_dump()
        
        assert serialized['description'] is None
        assert serialized['serial'] is None
        
        print("✓ None value handling passed")
        
    except Exception as e:
        print(f"✗ None value handling failed: {e}")
        return False
    
    # Test with empty lists
    try:
        mock_paginated_empty = {
            "items": [],
            "total": 0,
            "page": 1,
            "per_page": 10,
            "pages": 0
        }
        
        paginated_schema = PaginatedResponse.model_validate(mock_paginated_empty)
        serialized = paginated_schema.model_dump()
        
        assert serialized['items'] == []
        assert serialized['total'] == 0
        
        print("✓ Empty list handling passed")
        
    except Exception as e:
        print(f"✗ Empty list handling failed: {e}")
        return False
    
    return True


def test_json_serialization_compatibility():
    """Test JSON serialization compatibility"""
    print("Testing JSON serialization compatibility...")
    
    # Test datetime serialization
    mock_zone = MockModel(
        id=1,
        name="example.com",
        zone_type="master",
        email="admin.example.com",
        description="Test zone",
        refresh=10800,
        retry=3600,
        expire=604800,
        minimum=86400,
        serial=2024011801,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        record_count=5
    )
    
    try:
        zone_schema = Zone.model_validate(mock_zone)
        
        # Test model_dump_json method
        json_str = zone_schema.model_dump_json()
        json_data = json.loads(json_str)
        
        # Verify datetime fields are properly serialized
        assert 'created_at' in json_data
        assert 'updated_at' in json_data
        assert isinstance(json_data['created_at'], str)
        assert isinstance(json_data['updated_at'], str)
        
        # Test round-trip serialization
        zone_schema_2 = Zone.model_validate(json_data)
        assert zone_schema_2.name == zone_schema.name
        assert zone_schema_2.id == zone_schema.id
        
        print("✓ JSON serialization compatibility passed")
        return True
        
    except Exception as e:
        print(f"✗ JSON serialization compatibility failed: {e}")
        return False


def main():
    """Run all serialization tests"""
    print("Starting response schema serialization validation tests...\n")
    
    tests = [
        test_zone_serialization,
        test_dns_record_serialization,
        test_forwarder_serialization,
        test_forwarder_health_serialization,
        test_rpz_rule_serialization,
        test_threat_feed_serialization,
        test_system_config_serialization,
        test_system_status_serialization,
        test_paginated_response_serialization,
        test_health_check_result_serialization,
        test_validation_result_serialization,
        test_monitoring_schemas_serialization,
        test_auth_schemas_serialization,
        test_edge_cases,
        test_json_serialization_compatibility
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
        print()  # Add spacing between tests
    
    print(f"\nTest Results:")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All response schema serialization tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())