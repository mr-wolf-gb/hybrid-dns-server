#!/usr/bin/env python3
"""
Debug ThreatFeed serialization issue
"""

from datetime import datetime, timezone
from app.schemas.security import ThreatFeed, FeedType, UpdateStatus

def debug_threat_feed():
    now = datetime.now(timezone.utc)
    
    try:
        threat_feed = ThreatFeed(
            id=1,
            name="Malware Domain List",
            url="https://example.com/malware-domains.txt",
            feed_type=FeedType.MALWARE,
            format_type="domains",
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
        
        print("ThreatFeed object created successfully")
        
        data = threat_feed.model_dump()
        print("model_dump() successful")
        print(f"Data keys: {list(data.keys())}")
        
        json_str = threat_feed.model_dump_json()
        print("model_dump_json() successful")
        print(f"JSON length: {len(json_str)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_threat_feed()