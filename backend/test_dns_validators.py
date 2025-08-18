#!/usr/bin/env python3
"""
Test script for DNS validators to ensure they work correctly.
This script validates that all custom DNS validators are functioning properly.
"""

from app.schemas.dns import (
    DNSRecordCreate, RecordType, ZoneCreate, ZoneType, 
    ForwarderCreate, ForwarderType, ForwarderServer
)


def test_dns_validators():
    """Test all DNS validators comprehensively"""
    print("Testing DNS Validators...")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test cases: (description, test_function, should_pass)
    test_cases = [
        # Zone validation tests
        ("Zone with DNS email format", lambda: ZoneCreate(
            name='example.com', zone_type=ZoneType.MASTER, email='admin.example.com'
        ), True),
        
        ("Zone with invalid email format", lambda: ZoneCreate(
            name='example.com', zone_type=ZoneType.MASTER, email='admin@example.com'
        ), False),
        
        # A record tests
        ("Valid A record", lambda: DNSRecordCreate(
            name='www', record_type=RecordType.A, value='192.168.1.1'
        ), True),
        
        ("Invalid A record IP", lambda: DNSRecordCreate(
            name='www', record_type=RecordType.A, value='invalid-ip'
        ), False),
        
        # AAAA record tests
        ("Valid AAAA record", lambda: DNSRecordCreate(
            name='ipv6', record_type=RecordType.AAAA, value='2001:db8::1'
        ), True),
        
        ("Invalid AAAA record", lambda: DNSRecordCreate(
            name='ipv6', record_type=RecordType.AAAA, value='invalid::ipv6'
        ), False),
        
        # CNAME record tests
        ("Valid CNAME record", lambda: DNSRecordCreate(
            name='alias', record_type=RecordType.CNAME, value='target.example.com'
        ), True),
        
        ("CNAME at zone apex (should fail)", lambda: DNSRecordCreate(
            name='@', record_type=RecordType.CNAME, value='target.example.com'
        ), False),
        
        # MX record tests
        ("Valid MX record", lambda: DNSRecordCreate(
            name='@', record_type=RecordType.MX, value='mail.example.com', priority=10
        ), True),
        
        ("MX record without priority", lambda: DNSRecordCreate(
            name='@', record_type=RecordType.MX, value='mail.example.com'
        ), False),
        
        # SRV record tests
        ("Valid SRV record", lambda: DNSRecordCreate(
            name='_http._tcp', record_type=RecordType.SRV, 
            value='server.example.com', priority=10, weight=5, port=80
        ), True),
        
        ("Invalid SRV record name", lambda: DNSRecordCreate(
            name='invalid-srv', record_type=RecordType.SRV,
            value='server.example.com', priority=10, weight=5, port=80
        ), False),
        
        # TXT record tests
        ("Valid TXT record", lambda: DNSRecordCreate(
            name='@', record_type=RecordType.TXT, value='Simple text record'
        ), True),
        
        ("Valid SPF TXT record", lambda: DNSRecordCreate(
            name='@', record_type=RecordType.TXT, value='v=spf1 include:_spf.google.com ~all'
        ), True),
        
        # CAA record tests
        ("Valid CAA record without quotes", lambda: DNSRecordCreate(
            name='@', record_type=RecordType.CAA, value='0 issue letsencrypt.org'
        ), True),
        
        # TTL tests
        ("Record with low TTL", lambda: DNSRecordCreate(
            name='test', record_type=RecordType.A, value='192.168.1.1', ttl=30
        ), True),
        
        ("Record with high TTL", lambda: DNSRecordCreate(
            name='test', record_type=RecordType.A, value='192.168.1.1', ttl=86400
        ), True),
        
        # Domain name validation tests
        ("Wildcard domain", lambda: DNSRecordCreate(
            name='*.example', record_type=RecordType.A, value='192.168.1.1'
        ), True),
        
        ("Underscore in domain", lambda: DNSRecordCreate(
            name='_service.example', record_type=RecordType.A, value='192.168.1.1'
        ), True),
        
        ("Long label (should fail)", lambda: DNSRecordCreate(
            name='a' * 64, record_type=RecordType.A, value='192.168.1.1'
        ), False),
        
        # Forwarder tests
        ("Valid forwarder", lambda: ForwarderCreate(
            name='AD Forwarder',
            domains=['ad.example.com'],
            forwarder_type=ForwarderType.ACTIVE_DIRECTORY,
            servers=[ForwarderServer(ip='192.168.1.10')]
        ), True),
    ]
    
    for description, test_func, should_pass in test_cases:
        try:
            result = test_func()
            if should_pass:
                print(f"✓ {description}")
                tests_passed += 1
            else:
                print(f"✗ {description} - Should have failed but passed")
                tests_failed += 1
        except Exception as e:
            if not should_pass:
                print(f"✓ {description} - Correctly failed")
                tests_passed += 1
            else:
                print(f"✗ {description} - Should have passed but failed: {e}")
                tests_failed += 1
    
    print(f"\nTest Results: {tests_passed} passed, {tests_failed} failed")
    
    if tests_failed == 0:
        print("🎉 All DNS validators are working correctly!")
        return True
    else:
        print("❌ Some validators need attention")
        return False


if __name__ == "__main__":
    success = test_dns_validators()
    exit(0 if success else 1)