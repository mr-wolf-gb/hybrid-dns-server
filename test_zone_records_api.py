#!/usr/bin/env python3
"""
Test script for zone records API endpoints
Run this after fresh installation to verify the API is working correctly
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000/api"  # Change this to your server URL
USERNAME = "admin"  # Change this to your admin username
PASSWORD = "admin"  # Change this to your admin password

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
    
    def login(self, username: str, password: str) -> bool:
        """Login and get JWT token"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_zones_list(self) -> bool:
        """Test listing zones"""
        try:
            response = self.session.get(f"{self.base_url}/zones/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Zones list successful - Found {data.get('total', 0)} zones")
                return True
            else:
                print(f"❌ Zones list failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Zones list error: {e}")
            return False
    
    def create_test_zone(self) -> Dict[str, Any]:
        """Create a test zone"""
        zone_data = {
            "name": "test.local",
            "zone_type": "master",
            "email": "admin.test.local",
            "description": "Test zone for API testing"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/zones/", json=zone_data)
            if response.status_code == 200:
                zone = response.json()
                print(f"✅ Test zone created: {zone['name']} (ID: {zone['id']})")
                return zone
            else:
                print(f"❌ Zone creation failed: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Zone creation error: {e}")
            return {}
    
    def test_zone_records_list(self, zone_id: int) -> bool:
        """Test listing records for a zone"""
        try:
            response = self.session.get(f"{self.base_url}/zones/{zone_id}/records")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Zone records list successful - Found {len(data.get('items', []))} records")
                return True
            else:
                print(f"❌ Zone records list failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Zone records list error: {e}")
            return False
    
    def test_create_record(self, zone_id: int) -> Dict[str, Any]:
        """Test creating a DNS record"""
        record_data = {
            "name": "www",
            "type": "A",  # Frontend sends 'type'
            "value": "192.168.1.10",
            "ttl": 3600
        }
        
        try:
            response = self.session.post(f"{self.base_url}/zones/{zone_id}/records", json=record_data)
            if response.status_code == 200:
                record = response.json()
                print(f"✅ DNS record created: {record['name']} {record.get('type', record.get('record_type'))} {record['value']}")
                return record
            else:
                print(f"❌ Record creation failed: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Record creation error: {e}")
            return {}
    
    def test_update_record(self, zone_id: int, record_id: int) -> bool:
        """Test updating a DNS record"""
        update_data = {
            "value": "192.168.1.20",
            "ttl": 7200
        }
        
        try:
            response = self.session.put(f"{self.base_url}/zones/{zone_id}/records/{record_id}", json=update_data)
            if response.status_code == 200:
                record = response.json()
                print(f"✅ DNS record updated: {record['name']} -> {record['value']}")
                return True
            else:
                print(f"❌ Record update failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Record update error: {e}")
            return False
    
    def test_delete_record(self, zone_id: int, record_id: int) -> bool:
        """Test deleting a DNS record"""
        try:
            response = self.session.delete(f"{self.base_url}/zones/{zone_id}/records/{record_id}")
            if response.status_code == 200:
                print("✅ DNS record deleted successfully")
                return True
            else:
                print(f"❌ Record deletion failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Record deletion error: {e}")
            return False
    
    def cleanup_test_zone(self, zone_id: int) -> bool:
        """Delete the test zone"""
        try:
            response = self.session.delete(f"{self.base_url}/zones/{zone_id}")
            if response.status_code == 200:
                print("✅ Test zone cleaned up")
                return True
            else:
                print(f"❌ Zone cleanup failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Zone cleanup error: {e}")
            return False

def main():
    print("🧪 Testing Zone Records API Endpoints")
    print("=" * 50)
    
    # Initialize tester
    tester = APITester(BASE_URL)
    
    # Login
    if not tester.login(USERNAME, PASSWORD):
        print("❌ Cannot proceed without authentication")
        sys.exit(1)
    
    # Test zones list
    if not tester.test_zones_list():
        print("❌ Basic zones API not working")
        sys.exit(1)
    
    # Create test zone
    zone = tester.create_test_zone()
    if not zone:
        print("❌ Cannot create test zone")
        sys.exit(1)
    
    zone_id = zone['id']
    
    try:
        # Test zone records list (empty)
        if not tester.test_zone_records_list(zone_id):
            print("❌ Zone records list API not working")
            return
        
        # Test record creation
        record = tester.test_create_record(zone_id)
        if not record:
            print("❌ Record creation API not working")
            return
        
        record_id = record['id']
        
        # Test record update
        if not tester.test_update_record(zone_id, record_id):
            print("❌ Record update API not working")
            return
        
        # Test zone records list (with records)
        if not tester.test_zone_records_list(zone_id):
            print("❌ Zone records list API not working after creation")
            return
        
        # Test record deletion
        if not tester.test_delete_record(zone_id, record_id):
            print("❌ Record deletion API not working")
            return
        
        print("\n🎉 All tests passed! Zone records API is working correctly.")
        
    finally:
        # Cleanup
        tester.cleanup_test_zone(zone_id)

if __name__ == "__main__":
    main()