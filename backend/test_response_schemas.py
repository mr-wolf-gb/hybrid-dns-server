#!/usr/bin/env python3
"""
Test script for response schemas to ensure they serialize data correctly.
This script validates that all response schemas properly serialize data to JSON.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from pydantic import ValidationError

from app.schemas.dns import (
    PaginatedResponse, HealthCheckResult, ZoneValidationResult, 
    ValidationResult, Zone, DNSRecord, Forwarder,
    ZoneType, RecordType, ForwarderType, ForwarderServer
)
from app.schemas.security import (
    ThreatFeedStatus, ThreatFeedUpdateResult, BulkThreatFeedUpdateResult,
    RPZRuleImportResult, RPZRule, RPZAction, FeedType, UpdateStatus
)
from app.schemas.system import (
    ServiceStatus, DatabaseStatus, BindStatus, SystemMetrics,
    SystemInfo, BackupStatus, MaintenanceStatus, SystemSummary,
    ConfigValidationResult, BulkConfigUpdateResult, SystemHealthStatus,
    SystemStatus
)
from app.schemas.auth import (
    LoginResponse, TokenResponse, TwoFactorSetupResponse
)


def test_response_schemas_serialization():
    """Test all response schemas for correct serialization"""
    print("Testing Response Schema Serialization...")
    
    tests_passed = 0
    tests_failed = 0
    
    def run_test(description: str, test_func):
        nonlocal tests_passed, tests_failed
        try:
            test_func()
            print(f"✓ {description}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {description} - Failed: {e}")
            tests_failed += 1
    
    # Test PaginatedResponse serialization
    def test_paginated_response():
        # Create sample zone data
        zones = [
            Zone(
                id=1,
                name="example.com",
                zone_type=ZoneType.MASTER,
                email="admin.example.com",
                serial=2024010101,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                record_count=5
            ),
            Zone(
                id=2,
                name="test.com",
                zone_type=ZoneType.SLAVE,
                email="admin.test.com",
                serial=2024010102,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                record_count=3
            )
        ]
        
        paginated = PaginatedResponse[Zone](
            items=zones,
            total=50,
            page=1,
            per_page=20,
            pages=3
        )
        
        # Test serialization to dict
        data = paginated.model_dump()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert data["total"] == 50
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["pages"] == 3
        assert len(data["items"]) == 2
        
        # Test JSON serialization
        json_str = paginated.model_dump_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["total"] == 50
        assert len(parsed["items"]) == 2
        
        # Verify datetime serialization
        assert "created_at" in parsed["items"][0]
        assert "updated_at" in parsed["items"][0]
    
    run_test("PaginatedResponse serialization", test_paginated_response)
    
    # Test HealthCheckResult serialization
    def test_health_check_result():
        now = datetime.now(timezone.utc)
        health_check = HealthCheckResult(
            server_ip="192.168.1.10",
            status="healthy",
            response_time=25,
            error_message=None,
            checked_at=now
        )
        
        # Test serialization
        data = health_check.model_dump()
        assert data["server_ip"] == "192.168.1.10"
        assert data["status"] == "healthy"
        assert data["response_time"] == 25
        assert data["error_message"] is None
        assert "checked_at" in data
        
        # Test JSON serialization with datetime
        json_str = health_check.model_dump_json()
        parsed = json.loads(json_str)
        assert "checked_at" in parsed
        
        # Test with error case
        error_health = HealthCheckResult(
            server_ip="192.168.1.11",
            status="unhealthy",
            response_time=None,
            error_message="Connection timeout",
            checked_at=now
        )
        
        error_data = error_health.model_dump()
        assert error_data["status"] == "unhealthy"
        assert error_data["response_time"] is None
        assert error_data["error_message"] == "Connection timeout"
    
    run_test("HealthCheckResult serialization", test_health_check_result)
    
    # Test ZoneValidationResult serialization
    def test_zone_validation_result():
        # Valid zone result
        valid_result = ZoneValidationResult(
            valid=True,
            errors=[],
            warnings=["TTL value is very low"]
        )
        
        data = valid_result.model_dump()
        assert data["valid"] is True
        assert data["errors"] == []
        assert len(data["warnings"]) == 1
        
        # Invalid zone result
        invalid_result = ZoneValidationResult(
            valid=False,
            errors=["Invalid domain name", "Missing SOA record"],
            warnings=[]
        )
        
        invalid_data = invalid_result.model_dump()
        assert invalid_data["valid"] is False
        assert len(invalid_data["errors"]) == 2
        assert invalid_data["warnings"] == []
    
    run_test("ZoneValidationResult serialization", test_zone_validation_result)
    
    # Test ValidationResult serialization
    def test_validation_result():
        result = ValidationResult(
            valid=False,
            errors=["Invalid format"],
            warnings=["Consider using FQDN"],
            details={
                "field": "domain",
                "value": "invalid..domain",
                "suggestion": "Use valid domain format"
            }
        )
        
        data = result.model_dump()
        assert data["valid"] is False
        assert len(data["errors"]) == 1
        assert len(data["warnings"]) == 1
        assert isinstance(data["details"], dict)
        assert data["details"]["field"] == "domain"
        
        # Test JSON serialization
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["details"]["suggestion"] == "Use valid domain format"
    
    run_test("ValidationResult serialization", test_validation_result)
    
    # Test SystemStatus serialization
    def test_system_status():
        now = datetime.now(timezone.utc)
        
        bind_status = BindStatus(
            running=True,
            config_valid=True,
            zones_loaded=25,
            queries_per_second=150.5,
            version="BIND 9.16.1"
        )
        
        db_status = DatabaseStatus(
            connected=True,
            connection_pool_size=10,
            active_connections=3
        )
        
        status = SystemStatus(
            overall_status=SystemHealthStatus.HEALTHY,
            bind9=bind_status,
            database=db_status,
            services=[],
            system_info={"hostname": "dns-server"},
            last_updated=now
        )
        
        data = status.model_dump()
        assert data["overall_status"] == "healthy"
        assert data["bind9"]["running"] is True
        assert data["bind9"]["config_valid"] is True
        assert data["database"]["connected"] is True
        assert data["bind9"]["zones_loaded"] == 25
        assert "last_updated" in data
        
        # Test JSON serialization
        json_str = status.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["bind9"]["zones_loaded"] == 25
    
    run_test("SystemStatus serialization", test_system_status)
    
    # Test ThreatFeedStatus serialization
    def test_threat_feed_status():
        now = datetime.now(timezone.utc)
        feed_status = ThreatFeedStatus(
            id=1,
            name="Malware Domains",
            is_active=True,
            last_updated=now,
            last_update_status=UpdateStatus.SUCCESS,
            rules_count=5000
        )
        
        data = feed_status.model_dump()
        assert data["id"] == 1
        assert data["name"] == "Malware Domains"
        assert data["is_active"] is True
        assert data["last_update_status"] == "success"
        assert data["rules_count"] == 5000
        assert "last_updated" in data
    
    run_test("ThreatFeedStatus serialization", test_threat_feed_status)
    
    # Test ThreatFeedUpdateResult serialization
    def test_threat_feed_update_result():
        update_result = ThreatFeedUpdateResult(
            feed_id=1,
            feed_name="Malware Domains",
            status=UpdateStatus.SUCCESS,
            rules_added=150,
            rules_updated=25,
            rules_removed=10,
            error_message=None,
            update_duration=12.5
        )
        
        data = update_result.model_dump()
        assert data["feed_id"] == 1
        assert data["feed_name"] == "Malware Domains"
        assert data["status"] == "success"
        assert data["rules_added"] == 150
        assert data["rules_updated"] == 25
        assert data["rules_removed"] == 10
        assert data["error_message"] is None
        assert data["update_duration"] == 12.5
    
    run_test("ThreatFeedUpdateResult serialization", test_threat_feed_update_result)
    
    # Test BulkThreatFeedUpdateResult serialization
    def test_bulk_threat_feed_update_result():
        bulk_result = BulkThreatFeedUpdateResult(
            total_feeds=5,
            successful_updates=4,
            failed_updates=1,
            total_rules_added=15000,
            total_rules_updated=8000,
            total_rules_removed=2000,
            update_duration=45.5
        )
        
        data = bulk_result.model_dump()
        assert data["total_feeds"] == 5
        assert data["successful_updates"] == 4
        assert data["failed_updates"] == 1
        assert data["total_rules_added"] == 15000
        assert data["total_rules_updated"] == 8000
        assert data["total_rules_removed"] == 2000
        assert data["update_duration"] == 45.5
    
    run_test("BulkThreatFeedUpdateResult serialization", test_bulk_threat_feed_update_result)
    
    # Test RPZRuleImportResult serialization
    def test_rpz_rule_import_result():
        import_result = RPZRuleImportResult(
            total_processed=1000,
            rules_added=950,
            rules_updated=25,
            rules_skipped=25,
            errors=["Invalid domain format", "Duplicate rule"]
        )
        
        data = import_result.model_dump()
        assert data["total_processed"] == 1000
        assert data["rules_added"] == 950
        assert data["rules_updated"] == 25
        assert data["rules_skipped"] == 25
        assert len(data["errors"]) == 2
    
    run_test("RPZRuleImportResult serialization", test_rpz_rule_import_result)
    
    # Test ServiceStatus serialization
    def test_service_status():
        now = datetime.now(timezone.utc)
        service = ServiceStatus(
            name="bind9",
            status=SystemHealthStatus.HEALTHY,
            uptime=86400,
            last_check=now
        )
        
        data = service.model_dump()
        assert data["name"] == "bind9"
        assert data["status"] == "healthy"
        assert data["uptime"] == 86400
        assert "last_check" in data
    
    run_test("ServiceStatus serialization", test_service_status)
    
    # Test DatabaseStatus serialization
    def test_database_status():
        now = datetime.now(timezone.utc)
        db_status = DatabaseStatus(
            connected=True,
            connection_pool_size=10,
            active_connections=3,
            response_time=25.5,
            last_check=now
        )
        
        data = db_status.model_dump()
        assert data["connected"] is True
        assert data["connection_pool_size"] == 10
        assert data["active_connections"] == 3
        assert data["response_time"] == 25.5
        assert "last_check" in data
    
    run_test("DatabaseStatus serialization", test_database_status)
    
    # Test BindStatus serialization
    def test_bind_status():
        bind_status = BindStatus(
            running=True,
            config_valid=True,
            version="BIND 9.16.1",
            zones_loaded=25,
            queries_per_second=150.5
        )
        
        data = bind_status.model_dump()
        assert data["running"] is True
        assert data["config_valid"] is True
        assert data["version"] == "BIND 9.16.1"
        assert data["zones_loaded"] == 25
        assert data["queries_per_second"] == 150.5
    
    run_test("BindStatus serialization", test_bind_status)
    
    # Test SystemMetrics serialization
    def test_system_metrics():
        now = datetime.now(timezone.utc)
        metrics = SystemMetrics(
            cpu_usage=45.2,
            memory_usage=62.8,
            disk_usage=35.1,
            network_io={"bytes_sent": 1024000, "bytes_received": 2048000},
            dns_queries_per_minute=150,
            active_zones=25,
            active_forwarders=3,
            active_rpz_rules=1500,
            timestamp=now
        )
        
        data = metrics.model_dump()
        assert data["cpu_usage"] == 45.2
        assert data["memory_usage"] == 62.8
        assert data["disk_usage"] == 35.1
        assert data["network_io"]["bytes_sent"] == 1024000
        assert data["network_io"]["bytes_received"] == 2048000
        assert data["dns_queries_per_minute"] == 150
        assert data["active_zones"] == 25
        assert data["active_forwarders"] == 3
        assert data["active_rpz_rules"] == 1500
        assert "timestamp" in data
    
    run_test("SystemMetrics serialization", test_system_metrics)
    
    # Test SystemInfo serialization
    def test_system_info():
        system_info = SystemInfo(
            hostname="dns-server-01",
            os_name="Ubuntu",
            os_version="24.04 LTS",
            python_version="3.12.3",
            application_version="1.0.0",
            uptime=259200,
            timezone="UTC"
        )
        
        data = system_info.model_dump()
        assert data["hostname"] == "dns-server-01"
        assert data["os_name"] == "Ubuntu"
        assert data["os_version"] == "24.04 LTS"
        assert data["python_version"] == "3.12.3"
        assert data["application_version"] == "1.0.0"
        assert data["uptime"] == 259200
        assert data["timezone"] == "UTC"
    
    run_test("SystemInfo serialization", test_system_info)
    
    # Test BackupStatus serialization
    def test_backup_status():
        now = datetime.now(timezone.utc)
        backup_status = BackupStatus(
            last_backup=now,
            backup_size=1073741824,
            backup_location="/opt/hybrid-dns-server/backups/",
            auto_backup_enabled=True,
            next_scheduled_backup=now,
            backup_retention_days=30
        )
        
        data = backup_status.model_dump()
        assert data["backup_size"] == 1073741824
        assert data["backup_location"] == "/opt/hybrid-dns-server/backups/"
        assert data["auto_backup_enabled"] is True
        assert data["backup_retention_days"] == 30
        assert "last_backup" in data
        assert "next_scheduled_backup" in data
    
    run_test("BackupStatus serialization", test_backup_status)
    
    # Test MaintenanceStatus serialization
    def test_maintenance_status():
        now = datetime.now(timezone.utc)
        maintenance = MaintenanceStatus(
            maintenance_mode=False,
            scheduled_maintenance=now,
            last_maintenance=now,
            maintenance_message="System maintenance scheduled"
        )
        
        data = maintenance.model_dump()
        assert data["maintenance_mode"] is False
        assert data["maintenance_message"] == "System maintenance scheduled"
        assert "last_maintenance" in data
        assert "scheduled_maintenance" in data
    
    run_test("MaintenanceStatus serialization", test_maintenance_status)
    
    # Test SystemSummary serialization
    def test_system_summary():
        now = datetime.now(timezone.utc)
        
        # Create required nested objects
        bind_status = BindStatus(
            running=True,
            config_valid=True,
            zones_loaded=25,
            queries_per_second=150.5,
            version="BIND 9.16.1"
        )
        
        db_status = DatabaseStatus(
            connected=True,
            connection_pool_size=10,
            active_connections=3
        )
        
        system_status = SystemStatus(
            overall_status=SystemHealthStatus.HEALTHY,
            bind9=bind_status,
            database=db_status,
            services=[],
            system_info={},
            last_updated=now
        )
        
        metrics = SystemMetrics(
            cpu_usage=45.2,
            memory_usage=62.8,
            active_zones=25,
            timestamp=now
        )
        
        info = SystemInfo(
            hostname="dns-server-01",
            os_name="Ubuntu",
            os_version="24.04 LTS",
            python_version="3.12.3",
            application_version="1.0.0",
            uptime=259200,
            timezone="UTC"
        )
        
        backup = BackupStatus(
            auto_backup_enabled=True,
            backup_retention_days=30
        )
        
        maintenance = MaintenanceStatus(
            maintenance_mode=False
        )
        
        summary = SystemSummary(
            status=system_status,
            metrics=metrics,
            info=info,
            backup=backup,
            maintenance=maintenance
        )
        
        data = summary.model_dump()
        assert data["status"]["overall_status"] == "healthy"
        assert data["metrics"]["cpu_usage"] == 45.2
        assert data["info"]["hostname"] == "dns-server-01"
        assert data["backup"]["auto_backup_enabled"] is True
        assert data["maintenance"]["maintenance_mode"] is False
    
    run_test("SystemSummary serialization", test_system_summary)
    
    # Test ConfigValidationResult serialization
    def test_config_validation_result():
        config_result = ConfigValidationResult(
            valid=False,
            errors=["Invalid bind9 configuration", "Missing zone file"],
            warnings=["Deprecated option used"],
            affected_services=["bind9", "dns-resolver"]
        )
        
        data = config_result.model_dump()
        assert data["valid"] is False
        assert len(data["errors"]) == 2
        assert len(data["warnings"]) == 1
        assert len(data["affected_services"]) == 2
    
    run_test("ConfigValidationResult serialization", test_config_validation_result)
    
    # Test BulkConfigUpdateResult serialization
    def test_bulk_config_update_result():
        bulk_config = BulkConfigUpdateResult(
            total_processed=10,
            successful_updates=8,
            failed_updates=2,
            validation_errors=["Invalid TTL value", "Missing required field"],
            updated_configs=["dns_timeout", "max_cache_size"],
            failed_configs=["invalid_option", "deprecated_setting"]
        )
        
        data = bulk_config.model_dump()
        assert data["total_processed"] == 10
        assert data["successful_updates"] == 8
        assert data["failed_updates"] == 2
        assert len(data["validation_errors"]) == 2
        assert len(data["updated_configs"]) == 2
        assert len(data["failed_configs"]) == 2
    
    run_test("BulkConfigUpdateResult serialization", test_bulk_config_update_result)
    
    # Test LoginResponse serialization
    def test_login_response():
        login_response = LoginResponse(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            refresh_token="refresh_token_here",
            token_type="bearer",
            requires_2fa=False,
            temporary_token="temp_token_here"
        )
        
        data = login_response.model_dump()
        assert data["access_token"] == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        assert data["refresh_token"] == "refresh_token_here"
        assert data["token_type"] == "bearer"
        assert data["requires_2fa"] is False
        assert data["temporary_token"] == "temp_token_here"
    
    run_test("LoginResponse serialization", test_login_response)
    
    # Test TokenResponse serialization
    def test_token_response():
        token_response = TokenResponse(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            token_type="bearer"
        )
        
        data = token_response.model_dump()
        assert data["access_token"] == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        assert data["token_type"] == "bearer"
    
    run_test("TokenResponse serialization", test_token_response)
    
    # Test TwoFactorSetupResponse serialization
    def test_two_factor_setup_response():
        setup_response = TwoFactorSetupResponse(
            secret="JBSWY3DPEHPK3PXP",
            qr_code="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
            backup_codes=["12345678", "87654321", "11223344"]
        )
        
        data = setup_response.model_dump()
        assert data["secret"] == "JBSWY3DPEHPK3PXP"
        assert data["qr_code"].startswith("data:image/png;base64,")
        assert len(data["backup_codes"]) == 3
    
    run_test("TwoFactorSetupResponse serialization", test_two_factor_setup_response)
    
    # Test edge cases and error handling
    def test_edge_cases():
        # Test empty paginated response
        empty_paginated = PaginatedResponse[Zone](
            items=[],
            total=0,
            page=1,
            per_page=20,
            pages=0
        )
        
        data = empty_paginated.model_dump()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["pages"] == 0
        
        # Test validation result with no errors or warnings
        clean_validation = ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            details=None
        )
        
        clean_data = clean_validation.model_dump()
        assert clean_data["valid"] is True
        assert clean_data["errors"] == []
        assert clean_data["warnings"] == []
        assert clean_data["details"] is None
        
        # Test health check with all None optional fields
        minimal_health = HealthCheckResult(
            server_ip="192.168.1.1",
            status="unknown",
            response_time=None,
            error_message=None,
            checked_at=datetime.now(timezone.utc)
        )
        
        minimal_data = minimal_health.model_dump()
        assert minimal_data["response_time"] is None
        assert minimal_data["error_message"] is None
    
    run_test("Edge cases and error handling", test_edge_cases)
    
    # Test JSON serialization consistency
    def test_json_serialization_consistency():
        now = datetime.now(timezone.utc)
        
        # Create a complex nested structure
        zones = [
            Zone(
                id=1,
                name="example.com",
                zone_type=ZoneType.MASTER,
                email="admin.example.com",
                serial=2024010101,
                is_active=True,
                created_at=now,
                updated_at=now,
                record_count=5
            )
        ]
        
        paginated = PaginatedResponse[Zone](
            items=zones,
            total=1,
            page=1,
            per_page=20,
            pages=1
        )
        
        # Test model_dump() vs model_dump_json() consistency
        dict_data = paginated.model_dump()
        json_str = paginated.model_dump_json()
        parsed_json = json.loads(json_str)
        
        # Compare keys
        assert set(dict_data.keys()) == set(parsed_json.keys())
        assert dict_data["total"] == parsed_json["total"]
        assert len(dict_data["items"]) == len(parsed_json["items"])
        
        # Verify datetime handling
        assert "created_at" in parsed_json["items"][0]
        assert isinstance(parsed_json["items"][0]["created_at"], str)
    
    run_test("JSON serialization consistency", test_json_serialization_consistency)
    
    print(f"\nTest Results: {tests_passed} passed, {tests_failed} failed")
    
    if tests_failed == 0:
        print("🎉 All response schemas serialize data correctly!")
        return True
    else:
        print("❌ Some response schemas need attention")
        return False


if __name__ == "__main__":
    success = test_response_schemas_serialization()
    exit(0 if success else 1)