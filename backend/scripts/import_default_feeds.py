#!/usr/bin/env python3
"""
Script to import default threat feeds into the hybrid DNS server
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_database_session
from app.services.threat_feed_service import ThreatFeedService
from app.core.logging_config import setup_logging

# Setup logging
logger = setup_logging()


async def main():
    parser = argparse.ArgumentParser(description="Import default threat feeds")
    parser.add_argument(
        "--list", "-l", 
        action="store_true", 
        help="List available default feeds"
    )
    parser.add_argument(
        "--import", "-i", 
        nargs="*", 
        dest="import_feeds",
        help="Import specific feeds by name (empty for recommended feeds)"
    )
    parser.add_argument(
        "--all", "-a", 
        action="store_true", 
        help="Import all available feeds"
    )
    parser.add_argument(
        "--inactive", 
        action="store_true", 
        help="Import feeds as inactive (disabled by default)"
    )
    parser.add_argument(
        "--categories", "-c", 
        action="store_true", 
        help="Show available categories"
    )
    
    args = parser.parse_args()
    
    # Get database session using async context manager
    async for db in get_database_session():
        try:
            threat_feed_service = ThreatFeedService(db)
            
            if args.categories:
                await show_categories(threat_feed_service)
            elif args.list:
                await list_available_feeds(threat_feed_service)
            elif args.import_feeds is not None or args.all:
                await import_feeds(threat_feed_service, args)
            else:
                parser.print_help()
                
        except Exception as e:
            logger.error(f"Script failed: {e}")
            sys.exit(1)
        finally:
            # Session is automatically closed by the async generator
            pass
        break  # Only use the first (and only) session


async def show_categories(service: ThreatFeedService):
    """Show available threat feed categories"""
    print("Available Threat Feed Categories:")
    print("=" * 50)
    
    default_data = await service.load_default_feeds()
    categories = default_data.get("categories", {})
    
    if not categories:
        print("No categories found.")
        return
    
    for cat_id, cat_info in categories.items():
        print(f"\n{cat_info['name']} ({cat_id})")
        print(f"  Description: {cat_info['description']}")
        print(f"  Color: {cat_info.get('color', 'N/A')}")


async def list_available_feeds(service: ThreatFeedService):
    """List all available default feeds with their status"""
    print("Available Default Threat Feeds:")
    print("=" * 80)
    
    result = await service.get_available_default_feeds()
    
    if not result["success"]:
        print(f"Error: {result.get('message', 'Failed to load feeds')}")
        return
    
    feeds = result["feeds"]
    summary = result["summary"]
    
    print(f"\nSummary:")
    print(f"  Total Available: {summary['total_available']}")
    print(f"  Already Imported: {summary['already_imported']}")
    print(f"  Recommended Active: {summary['recommended_active']}")
    
    print(f"\nFeeds:")
    print("-" * 80)
    
    for feed in feeds:
        status = "✓ IMPORTED" if feed["is_imported"] else "○ Available"
        active_status = ""
        
        if feed["is_imported"] and feed["current_status"]:
            active_status = " (ACTIVE)" if feed["current_status"]["is_active"] else " (INACTIVE)"
            rules_count = feed["current_status"]["rules_count"]
            active_status += f" - {rules_count} rules"
        
        recommended = " [RECOMMENDED]" if feed["recommended_active"] else ""
        
        print(f"{status:<12} {feed['name']:<35} {feed['category']:<15}{active_status}{recommended}")
        print(f"             {feed['description']}")
        print(f"             URL: {feed['url']}")
        print(f"             Format: {feed['format_type']}, Update: {feed['update_frequency']}s")
        print()


async def import_feeds(service: ThreatFeedService, args):
    """Import selected feeds"""
    if args.all:
        # Import all available feeds
        result = await service.get_available_default_feeds()
        if result["success"]:
            selected_feeds = [feed["name"] for feed in result["feeds"] if not feed["is_imported"]]
        else:
            print(f"Error loading feeds: {result.get('message')}")
            return
    elif args.import_feeds:
        # Import specific feeds
        selected_feeds = args.import_feeds
    else:
        # Import recommended feeds only
        selected_feeds = None
    
    activate_feeds = not args.inactive
    
    print(f"Importing feeds...")
    if selected_feeds:
        print(f"Selected feeds: {', '.join(selected_feeds)}")
    else:
        print("Importing recommended active feeds")
    
    print(f"Feeds will be {'ACTIVE' if activate_feeds else 'INACTIVE'} after import")
    print()
    
    result = await service.import_default_feeds(
        selected_feeds=selected_feeds,
        activate_feeds=activate_feeds
    )
    
    if result["success"]:
        print(f"✓ Successfully imported {result['imported']} feeds")
        if result["skipped"] > 0:
            print(f"  Skipped {result['skipped']} existing feeds")
        
        if result.get("errors"):
            print(f"\n⚠ Errors encountered:")
            for error in result["errors"]:
                print(f"  - {error}")
        
        if result.get("feeds"):
            print(f"\nImported feeds:")
            for feed in result["feeds"]:
                status = "ACTIVE" if feed["is_active"] else "INACTIVE"
                print(f"  - {feed['name']} ({feed['category']}) - {status}")
    else:
        print(f"✗ Import failed: {result.get('message')}")
        if result.get("errors"):
            for error in result["errors"]:
                print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main())