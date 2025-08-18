#!/usr/bin/env python3
"""
Comprehensive test script for response schema serialization.
This script validates that all response schemas properly serialize data to JSON
including edge cases, nested objects, and complex data structures.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from decimal import Decimal
import pytest

from app.schemas.dns import (
    PaginatedResponse, HealthCheckResult, ZoneValidationResult, 
    ValidationResult, Zone, DNSRecord, Forwarder,
    ZoneType, RecordType, ForwarderType, ForwarderServer, ForwarderHealth
)
from app.schemas.security import (
    ThreatFeedStatus, ThreatFeedUpdateResult, BulkThreatFeedUpdateResult,
    RPZRuleImportResult, RPZRule, RPZAction, FeedType, UpdateStatus, ThreatFeed, FormatType
)
from app.schemas.system import (
    ServiceStatus, DatabaseStatus, BindStatus, SystemMetrics,
    SystemInfo, BackupStatus, MaintenanceStatus, SystemSummary,
    ConfigValidationResult, BulkConfigUpdateResult, SystemHealthStatus,
    SystemStatus, SystemConfig
)
from app.schemas.monitoring import (
    DNSLog, SystemStats, AuditLog, DNSQueryStats, SystemMetricsSummary,
    AuditSummary, MonitoringDashboard, QueryType, MetricType, ResourceType
)
from app.schemas.auth import (
    LoginResponse, TokenResponse, TwoFactorSetupResponse, UserInfo, SessionInfo
)


def test_comprehensive_serialization():
    """Test comprehensive serialization scenarios"""
    print("Testing Comprehensive Response Schema Serialization...")
    
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
            import traceback
            traceback.print_exc()
            tests_failed += 1
    
    # Test complex nested structures
    def test_complex_nested_structures():
        now = datetime.now(timezone.utc)
        
        # Create a complex Zone with all fields populated
        zone = Zone(
            id=1,
            name="example.com",
            zone_type=ZoneType.MASTER,
            email="admin.example.com",
            description="Primary zone for example.com domain",
            serial=2024010101,
            refresh=10800,
            retry=3600,
            expire=604800,
            minimum=86400,
            is_active=True,
            created_at=now,
            updated_at=now,
            record_count=25
        )
        
        # Test serialization with all fields
        data = zone.model_dump()
        json_str = zone.model_dump_json()
        parsed = json.loads(json_str)
        
        # Verify all fields are present and correctly serialized
        assert data["id"] == 1
        assert data["name"] == "example.com"
        assert data["zone_type"] == "master"
        assert data["email"] == "admin.example.com"
        assert data["description"] == "Primary zone for example.com domain"
        assert data["serial"] == 2024010101
        assert data["refresh"] == 10800
        assert data["retry"] == 3600
        assert data["expire"] == 604800
        assert data["minimum"] == 86400
        assert data["is_active"] is True
        assert data["record_count"] == 25
        assert "created_at" in data
        assert "updated_at" in data
        
        # Verify JSON serialization matches dict serialization
        assert parsed["id"] == data["id"]
        assert parsed["name"] == data["name"]
        assert parsed["zone_type"] == data["zone_type"]
        assert isinstance(parsed["created_at"], str)
        assert isinstance(parsed["updated_at"], str)
    
    run_test("Complex nested structures", test_complex_nested_structures)
    
    # Test DNS Record serialization with all record types
    def test_dns_record_serialization():
        now = datetime.now(timezone.utc)
        
        # Test A record
        a_record = DNSRecord(
            id=1,
            zone_id=1,
            name="www",
            record_type=RecordType.A,
            value="192.168.1.100",
            ttl=3600,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        a_data = a_record.model_dump()
        assert a_data["record_type"] == "A"
        assert a_data["value"] == "192.168.1.100"
        assert a_data["ttl"] == 3600
        
        # Test MX record with priority
        mx_record = DNSRecord(
            id=2,
            zone_id=1,
            name="@",
            record_type=RecordType.MX,
            value="mail.example.com",
            ttl=3600,
            priority=10,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        mx_data = mx_record.model_dump()
        assert mx_data["record_type"] == "MX"
        assert mx_data["priority"] == 10
        
        # Test SRV record with all fields
        srv_record = DNSRecord(
            id=3,
            zone_id=1,
            name="_sip._tcp",
            record_type=RecordType.SRV,
            value="sip.example.com",
            ttl=3600,
            priority=10,
            weight=20,
            port=5060,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        srv_data = srv_record.model_dump()
        assert srv_data["record_type"] == "SRV"
        assert srv_data["priority"] == 10
        assert srv_data["weight"] == 20
        assert srv_data["port"] == 5060
    
    run_test("DNS Record serialization with all types", test_dns_record_serialization)
    
    # Test Forwarder with complex server configurations
    def test_forwarder_serialization():
        now = datetime.now(timezone.utc)
        
        servers = [
            ForwarderServer(ip="192.168.1.10", port=53, priority=1),
            ForwarderServer(ip="192.168.1.11", port=53, priority=2),
            ForwarderServer(ip="10.0.0.10", port=5353, priority=3)
        ]
        
        forwarder = Forwarder(
            id=1,
            name="Active Directory Forwarder",
            domains=["ad.company.com", "company.local"],
            forwarder_type=ForwarderType.ACTIVE_DIRECTORY,
            servers=servers,
            description="Forwards AD queries to domain controllers",
            health_check_enabled=True,
            is_active=True,
            created_at=now,
            updated_at=now,
            health_status="healthy"
        )
        
        data = forwarder.model_dump()
        json_str = forwarder.model_dump_json()
        parsed = json.loads(json_str)
        
        # Verify complex nested server data
        assert len(data["servers"]) == 3
        assert data["servers"][0]["ip"] == "192.168.1.10"
        assert data["servers"][0]["port"] == 53
        assert data["servers"][0]["priority"] == 1
        assert data["servers"][2]["port"] == 5353
        
        # Verify domains array
        assert len(data["domains"]) == 2
        assert "ad.company.com" in data["domains"]
        assert "company.local" in data["domains"]
        
        # Verify JSON consistency
        assert parsed["servers"][0]["ip"] == data["servers"][0]["ip"]
        assert len(parsed["domains"]) == len(data["domains"])
    
    run_test("Forwarder with complex server configurations", test_forwarder_serialization)
    
    # Test ForwarderHealth serialization
    def test_forwarder_health_serialization():
        now = datetime.now(timezone.utc)
        
        health = ForwarderHealth(
            id=1,
            forwarder_id=1,
            server_ip="192.168.1.10",
            status="healthy",
            response_time=25,
            error_message=None,
            checked_at=now
        )
        
        data = health.model_dump()
        assert data["server_ip"] == "192.168.1.10"
        assert data["status"] == "healthy"
        assert data["response_time"] == 25
        assert data["error_message"] is None
        
        # Test unhealthy status
        unhealthy = ForwarderHealth(
            id=2,
            forwarder_id=1,
            server_ip="192.168.1.11",
            status="unhealthy",
            response_time=None,
            error_message="Connection timeout after 5 seconds",
            checked_at=now
        )
        
        unhealthy_data = unhealthy.model_dump()
        assert unhealthy_data["status"] == "unhealthy"
        assert unhealthy_data["response_time"] is None
        assert unhealthy_data["error_message"] == "Connection timeout after 5 seconds"
    
    run_test("ForwarderHealth serialization", test_forwarder_health_serialization)
    
    # Test ThreatFeed serialization
    def test_threat_feed_serialization():
        now = datetime.now(timezone.utc)
        
        threat_feed = ThreatFeed(
            id=1,
            name="Malware Domain List",
            url="https://example.com/malware-domains.txt",
            feed_type=FeedType.MALWARE,
            format_type=FormatType.DOMAINS,
            update_frequency=3600,
            description="List of known malware domains",
            is_active=True,
            last_updated=now,
            last_update_status=UpdateStatus.SUCCESS,
            last_update_error=None,
            rules_count=15000,
            created_at=now,
            updated_at=now
        )
        
        data = threat_feed.model_dump()
        json_str = threat_feed.model_dump_json()
        parsed = json.loads(json_str)
        
        assert data["name"] == "Malware Domain List"
        assert str(data["url"]) == "https://example.com/malware-domains.txt"
        assert data["feed_type"] == "malware"
        assert data["format_type"] == "domains"
        assert data["update_frequency"] == 3600
        assert data["is_active"] is True
        assert data["last_update_status"] == "success"
        assert data["rules_count"] == 15000
        
        # Verify URL serialization in JSON (URLs are serialized as strings in JSON)
        assert parsed["url"] == "https://example.com/malware-domains.txt"
    
    run_test("ThreatFeed serialization", test_threat_feed_serialization)
    
    # Test RPZRule serialization
    def test_rpz_rule_serialization():
        now = datetime.now(timezone.utc)
        
        # Test block rule
        block_rule = RPZRule(
            id=1,
            domain="malware.example.com",
            rpz_zone="malware",
            action=RPZAction.BLOCK,
            redirect_target=None,
            description="Known malware domain",
            is_active=True,
            source="threat_feed",
            created_at=now,
            updated_at=now
        )
        
        block_data = block_rule.model_dump()
        assert block_data["domain"] == "malware.example.com"
        assert block_data["rpz_zone"] == "malware"
        assert block_data["action"] == "block"
        assert block_data["redirect_target"] is None
        assert block_data["source"] == "threat_feed"
        
        # Test redirect rule
        redirect_rule = RPZRule(
            id=2,
            domain="social.example.com",
            rpz_zone="social_media",
            action=RPZAction.REDIRECT,
            redirect_target="blocked.company.com",
            description="Social media site redirect",
            is_active=True,
            source="manual",
            created_at=now,
            updated_at=now
        )
        
        redirect_data = redirect_rule.model_dump()
        assert redirect_data["action"] == "redirect"
        assert redirect_data["redirect_target"] == "blocked.company.com"
    
    run_test("RPZRule serialization", test_rpz_rule_serialization)
    
    # Test SystemConfig serialization
    def test_system_config_serialization():
        now = datetime.now(timezone.utc)
        
        config = SystemConfig(
            id=1,
            key="dns.timeout",
            value="30",
            value_type="integer",
            category="dns",
            description="DNS query timeout in seconds",
            is_sensitive=False,
            created_at=now,
            updated_at=now
        )
        
        data = config.model_dump()
        assert data["key"] == "dns.timeout"
        assert data["value"] == "30"
        assert data["value_type"] == "integer"
        assert data["category"] == "dns"
        assert data["is_sensitive"] is False
        
        # Test sensitive config
        sensitive_config = SystemConfig(
            id=2,
            key="auth.secret_key",
            value="super_secret_key_here",
            value_type="string",
            category="authentication",
            description="JWT secret key",
            is_sensitive=True,
            created_at=now,
            updated_at=now
        )
        
        sensitive_data = sensitive_config.model_dump()
        assert sensitive_data["is_sensitive"] is True
        assert sensitive_data["value"] == "super_secret_key_here"  # Value should be present in full model
    
    run_test("SystemConfig serialization", test_system_config_serialization)
    
    # Test monitoring schemas
    def test_monitoring_schemas_serialization():
        now = datetime.now(timezone.utc)
        
        # Test DNSLog
        dns_log = DNSLog(
            id=1,
            timestamp=now,
            client_ip="192.168.1.100",
            query_domain="example.com",
            query_type=QueryType.A,
            response_code="NOERROR",
            response_time=25,
            blocked=False,
            rpz_zone=None,
            forwarder_used="192.168.1.10"
        )
        
        log_data = dns_log.model_dump()
        assert log_data["client_ip"] == "192.168.1.100"
        assert log_data["query_domain"] == "example.com"
        assert log_data["query_type"] == "A"
        assert log_data["response_code"] == "NOERROR"
        assert log_data["blocked"] is False
        
        # Test SystemStats
        system_stats = SystemStats(
            id=1,
            timestamp=now,
            metric_name="cpu_usage",
            metric_value="45.2",
            metric_type=MetricType.GAUGE
        )
        
        stats_data = system_stats.model_dump()
        assert stats_data["metric_name"] == "cpu_usage"
        assert stats_data["metric_value"] == "45.2"
        assert stats_data["metric_type"] == "gauge"
        
        # Test AuditLog
        audit_log = AuditLog(
            id=1,
            timestamp=now,
            user_id=1,
            action="create_zone",
            resource_type=ResourceType.ZONE,
            resource_id="1",
            details="Created zone example.com",
            ip_address="192.168.1.50",
            user_agent="Mozilla/5.0..."
        )
        
        audit_data = audit_log.model_dump()
        assert audit_data["action"] == "create_zone"
        assert audit_data["resource_type"] == "zone"
        assert audit_data["resource_id"] == "1"
        assert audit_data["details"] == "Created zone example.com"
    
    run_test("Monitoring schemas serialization", test_monitoring_schemas_serialization)
    
    # Test analytics schemas
    def test_analytics_schemas_serialization():
        now = datetime.now(timezone.utc)
        
        # Test DNSQueryStats
        query_stats = DNSQueryStats(
            total_queries=10000,
            blocked_queries=500,
            unique_clients=150,
            unique_domains=2500,
            top_domains=[
                {"domain": "example.com", "count": 1000},
                {"domain": "google.com", "count": 800}
            ],
            top_clients=[
                {"ip": "192.168.1.100", "count": 500},
                {"ip": "192.168.1.101", "count": 300}
            ],
            query_types={"A": 7000, "AAAA": 2000, "MX": 500, "TXT": 500},
            response_codes={"NOERROR": 9500, "NXDOMAIN": 400, "SERVFAIL": 100},
            blocked_by_rpz={"malware": 300, "phishing": 150, "adult": 50}
        )
        
        stats_data = query_stats.model_dump()
        assert stats_data["total_queries"] == 10000
        assert stats_data["blocked_queries"] == 500
        assert len(stats_data["top_domains"]) == 2
        assert stats_data["top_domains"][0]["domain"] == "example.com"
        assert stats_data["query_types"]["A"] == 7000
        assert stats_data["blocked_by_rpz"]["malware"] == 300
        
        # Test SystemMetricsSummary
        metrics_summary = SystemMetricsSummary(
            cpu_usage=45.2,
            memory_usage=62.8,
            disk_usage=35.1,
            network_io={"bytes_sent": 1024000, "bytes_received": 2048000},
            dns_queries_per_minute=150,
            active_connections=25,
            uptime=259200
        )
        
        metrics_data = metrics_summary.model_dump()
        assert metrics_data["cpu_usage"] == 45.2
        assert metrics_data["network_io"]["bytes_sent"] == 1024000
        assert metrics_data["dns_queries_per_minute"] == 150
        
        # Test MonitoringDashboard
        dashboard = MonitoringDashboard(
            dns_stats=query_stats,
            system_metrics=metrics_summary,
            audit_summary=AuditSummary(
                total_actions=1000,
                unique_users=5,
                actions_by_type={"create": 400, "update": 300, "delete": 100},
                resources_by_type={"zone": 500, "record": 400, "forwarder": 100},
                recent_actions=[],
                failed_actions=10
            ),
            alerts=[
                {"type": "warning", "message": "High CPU usage detected"},
                {"type": "info", "message": "Backup completed successfully"}
            ],
            last_updated=now
        )
        
        dashboard_data = dashboard.model_dump()
        assert dashboard_data["dns_stats"]["total_queries"] == 10000
        assert dashboard_data["system_metrics"]["cpu_usage"] == 45.2
        assert len(dashboard_data["alerts"]) == 2
        assert dashboard_data["alerts"][0]["type"] == "warning"
    
    run_test("Analytics schemas serialization", test_analytics_schemas_serialization)
    
    # Test authentication schemas
    def test_auth_schemas_serialization():
        now = datetime.now(timezone.utc)
        
        # Test UserInfo
        user_info = UserInfo(
            id=1,
            username="admin",
            email="admin@example.com",
            is_active=True,
            is_superuser=True,
            two_factor_enabled=True,
            last_login=now,
            created_at=now
        )
        
        user_data = user_info.model_dump()
        assert user_data["username"] == "admin"
        assert user_data["email"] == "admin@example.com"
        assert user_data["is_active"] is True
        assert user_data["two_factor_enabled"] is True
        
        # Test SessionInfo
        session_info = SessionInfo(
            id=1,
            user_id=1,
            session_token="session_token_here",
            expires_at=now,
            created_at=now,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0...",
            is_current=True
        )
        
        session_data = session_info.model_dump()
        assert session_data["user_id"] == 1
        assert session_data["session_token"] == "session_token_here"
        assert session_data["ip_address"] == "192.168.1.100"
        assert session_data["is_current"] is True
    
    run_test("Authentication schemas serialization", test_auth_schemas_serialization)
    
    # Test edge cases and special values
    def test_edge_cases_and_special_values():
        now = datetime.now(timezone.utc)
        
        # Test with None values
        health_check = HealthCheckResult(
            server_ip="192.168.1.1",
            status="unknown",
            response_time=None,
            error_message=None,
            checked_at=now
        )
        
        data = health_check.model_dump()
        json_str = health_check.model_dump_json()
        parsed = json.loads(json_str)
        
        assert data["response_time"] is None
        assert data["error_message"] is None
        assert parsed["response_time"] is None
        assert parsed["error_message"] is None
        
        # Test with empty lists and dicts
        validation_result = ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            details={}
        )
        
        validation_data = validation_result.model_dump()
        assert validation_data["errors"] == []
        assert validation_data["warnings"] == []
        assert validation_data["details"] == {}
        
        # Test with large numbers
        metrics = SystemMetrics(
            cpu_usage=99.99,
            memory_usage=100.0,
            disk_usage=0.01,
            network_io={"bytes_sent": 999999999999, "bytes_received": 0},
            dns_queries_per_minute=0,
            active_zones=10000,
            active_forwarders=0,
            active_rpz_rules=999999,
            timestamp=now
        )
        
        metrics_data = metrics.model_dump()
        assert metrics_data["cpu_usage"] == 99.99
        assert metrics_data["memory_usage"] == 100.0
        assert metrics_data["disk_usage"] == 0.01
        assert metrics_data["network_io"]["bytes_sent"] == 999999999999
        assert metrics_data["active_rpz_rules"] == 999999
    
    run_test("Edge cases and special values", test_edge_cases_and_special_values)
    
    # Test datetime serialization consistency
    def test_datetime_serialization_consistency():
        now = datetime.now(timezone.utc)
        
        # Test various datetime fields
        zone = Zone(
            id=1,
            name="example.com",
            zone_type=ZoneType.MASTER,
            email="admin.example.com",
            serial=2024010101,
            is_active=True,
            created_at=now,
            updated_at=now,
            record_count=0
        )
        
        # Test model_dump vs model_dump_json consistency
        dict_data = zone.model_dump()
        json_str = zone.model_dump_json()
        parsed_json = json.loads(json_str)
        
        # Both should have datetime fields
        assert "created_at" in dict_data
        assert "updated_at" in dict_data
        assert "created_at" in parsed_json
        assert "updated_at" in parsed_json
        
        # JSON should have string representation
        assert isinstance(parsed_json["created_at"], str)
        assert isinstance(parsed_json["updated_at"], str)
        
        # Should be valid ISO format
        from datetime import datetime as dt
        dt.fromisoformat(parsed_json["created_at"].replace('Z', '+00:00'))
        dt.fromisoformat(parsed_json["updated_at"].replace('Z', '+00:00'))
    
    run_test("Datetime serialization consistency", test_datetime_serialization_consistency)
    
    print(f"\nComprehensive Test Results: {tests_passed} passed, {tests_failed} failed")
    
    if tests_failed == 0:
        print("🎉 All response schemas serialize data correctly in all scenarios!")
        return True
    else:
        print("❌ Some response schemas need attention")
        return False


if __name__ == "__main__":
    success = test_comprehensive_serialization()
    exit(0 if success else 1)