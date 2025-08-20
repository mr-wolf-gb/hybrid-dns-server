#!/usr/bin/env python3
"""
Test script for forwarder priority management, grouping, and templates
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.dns import Forwarder, ForwarderTemplate
from app.schemas.dns import ForwarderCreate, ForwarderTemplateCreate
from app.services.forwarder_service import ForwarderService
from app.services.forwarder_template_service import ForwarderTemplateService
from app.core.database import get_database_session
from sqlalchemy.orm import Session


async def test_forwarder_priority_management():
    """Test forwarder priority management features"""
    print("Testing forwarder priority management...")
    
    # This would normally use a real database session
    # For now, just test the schema validation
    
    # Test ForwarderCreate with new priority fields
    forwarder_data = ForwarderCreate(
        name="Test AD Forwarder",
        domains=["corp.local", "ad.local"],
        forwarder_type="active_directory",
        servers=[
            {
                "ip": "192.168.1.10",
                "port": 53,
                "priority": 1,
                "weight": 1,
                "enabled": True
            }
        ],
        priority=2,
        group_name="Active Directory",
        group_priority=1,
        description="Test forwarder for AD"
    )
    
    print(f"✓ Created forwarder schema with priority {forwarder_data.priority}")
    print(f"✓ Group: {forwarder_data.group_name}, Group Priority: {forwarder_data.group_priority}")
    
    return True


async def test_forwarder_templates():
    """Test forwarder template features"""
    print("Testing forwarder templates...")
    
    # Test ForwarderTemplateCreate
    template_data = ForwarderTemplateCreate(
        name="Active Directory Template",
        description="Template for Active Directory DNS forwarding",
        forwarder_type="active_directory",
        default_domains=["corp.local", "ad.local"],
        default_servers=[
            {
                "ip": "192.168.1.10",
                "port": 53,
                "priority": 1,
                "weight": 1,
                "enabled": True
            },
            {
                "ip": "192.168.1.11",
                "port": 53,
                "priority": 2,
                "weight": 1,
                "enabled": True
            }
        ],
        default_priority=1,
        default_group_name="Active Directory",
        default_health_check_enabled=True,
        is_system_template=True
    )
    
    print(f"✓ Created template schema: {template_data.name}")
    print(f"✓ Default priority: {template_data.default_priority}")
    print(f"✓ Default group: {template_data.default_group_name}")
    print(f"✓ Default servers: {len(template_data.default_servers)}")
    
    return True


async def test_forwarder_grouping():
    """Test forwarder grouping features"""
    print("Testing forwarder grouping...")
    
    # Test multiple forwarders in the same group
    forwarders = [
        ForwarderCreate(
            name="AD Primary",
            domains=["corp.local"],
            forwarder_type="active_directory",
            servers=[{"ip": "192.168.1.10", "port": 53, "priority": 1, "weight": 1, "enabled": True}],
            priority=1,
            group_name="Active Directory",
            group_priority=1
        ),
        ForwarderCreate(
            name="AD Secondary",
            domains=["corp.local"],
            forwarder_type="active_directory",
            servers=[{"ip": "192.168.1.11", "port": 53, "priority": 1, "weight": 1, "enabled": True}],
            priority=1,
            group_name="Active Directory",
            group_priority=2
        ),
        ForwarderCreate(
            name="Internal DNS",
            domains=["internal.local"],
            forwarder_type="intranet",
            servers=[{"ip": "10.0.0.1", "port": 53, "priority": 1, "weight": 1, "enabled": True}],
            priority=3,
            group_name="Internal",
            group_priority=1
        )
    ]
    
    print(f"✓ Created {len(forwarders)} forwarders with grouping")
    
    # Group by group_name
    groups = {}
    for forwarder in forwarders:
        group_name = forwarder.group_name
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(forwarder)
    
    for group_name, group_forwarders in groups.items():
        print(f"✓ Group '{group_name}': {len(group_forwarders)} forwarders")
        for forwarder in sorted(group_forwarders, key=lambda x: x.group_priority):
            print(f"  - {forwarder.name} (priority: {forwarder.priority}, group_priority: {forwarder.group_priority})")
    
    return True


async def test_enhanced_server_config():
    """Test enhanced server configuration with weight and enabled fields"""
    print("Testing enhanced server configuration...")
    
    # Test server with all new fields
    forwarder_data = ForwarderCreate(
        name="Load Balanced Forwarder",
        domains=["example.com"],
        forwarder_type="public",
        servers=[
            {
                "ip": "8.8.8.8",
                "port": 53,
                "priority": 1,
                "weight": 10,
                "enabled": True
            },
            {
                "ip": "8.8.4.4",
                "port": 53,
                "priority": 1,
                "weight": 5,
                "enabled": True
            },
            {
                "ip": "1.1.1.1",
                "port": 53,
                "priority": 2,
                "weight": 1,
                "enabled": False  # Disabled server
            }
        ],
        priority=5,
        description="Load balanced public DNS forwarder"
    )
    
    print(f"✓ Created forwarder with {len(forwarder_data.servers)} servers")
    for i, server in enumerate(forwarder_data.servers):
        status = "enabled" if server.enabled else "disabled"
        print(f"  - Server {i+1}: {server.ip}:{server.port} (priority: {server.priority}, weight: {server.weight}, {status})")
    
    return True


async def main():
    """Run all tests"""
    print("Testing Forwarder Priority Management, Grouping, and Templates")
    print("=" * 60)
    
    tests = [
        test_forwarder_priority_management,
        test_forwarder_templates,
        test_forwarder_grouping,
        test_enhanced_server_config
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
            print()
        except Exception as e:
            print(f"✗ Test failed: {str(e)}")
            results.append(False)
            print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)