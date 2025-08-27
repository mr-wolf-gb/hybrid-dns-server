"""
Threat Feed service for managing external threat intelligence sources with event broadcasting
"""

import asyncio
import aiohttp
import re
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.exc import IntegrityError

from .base_service import BaseService
from .rpz_service import RPZService
from ..models.security import ThreatFeed, RPZRule
from ..schemas.security import (
    ThreatFeedCreate, ThreatFeedUpdate, ThreatFeedUpdateResult, 
    BulkThreatFeedUpdateResult, FeedType, FormatType, UpdateStatus
)
from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger
from ..core.exceptions import ValidationException, ThreatFeedException
from .enhanced_event_service import get_enhanced_event_service
from ..websocket.event_types import EventType, EventPriority, EventCategory, EventSeverity, create_event

logger = get_logger(__name__)


class ThreatFeedService(BaseService[ThreatFeed]):
    """Threat Feed service with authentication, automatic updates, and event broadcasting"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, ThreatFeed)
        self.rpz_service = RPZService(db)
        self.event_service = get_enhanced_event_service()
    
    async def create_feed(self, feed_data: Dict[str, Any]) -> ThreatFeed:
        """Create a new threat feed with validation"""
        logger.info(f"Creating threat feed: {feed_data.get('name')}")
        
        # Validate required fields
        if not feed_data.get('name'):
            raise ValidationException("Feed name is required")
        if not feed_data.get('url'):
            raise ValidationException("Feed URL is required")
        if not feed_data.get('feed_type'):
            raise ValidationException("Feed type is required")
        if not feed_data.get('format_type'):
            raise ValidationException("Format type is required")
        
        # Convert URL to string if it's a Pydantic URL object
        if hasattr(feed_data.get('url'), '__str__'):
            feed_data['url'] = str(feed_data['url'])
        
        # Set default values
        feed_data.setdefault('is_active', True)
        feed_data.setdefault('update_frequency', 3600)  # 1 hour default
        feed_data.setdefault('rules_count', 0)
        feed_data.setdefault('last_update_status', None)  # NULL for new feeds
        
        try:
            # Check for duplicate name
            existing_feed = await self.get_feed_by_name(feed_data['name'])
            if existing_feed:
                raise ThreatFeedException(f"Threat feed with name '{feed_data['name']}' already exists")
            
            # Remove fields that are not part of the model
            model_data = {k: v for k, v in feed_data.items() if k not in ['category']}
            
            # Create the feed
            feed = await self.create(model_data, track_action=True)
            
            # Emit threat feed creation event
            await self._emit_threat_feed_event(
                event_type=EventType.THREAT_FEED_UPDATE,
                feed=feed,
                action="create",
                details={
                    "feed_name": feed.name,
                    "feed_type": feed.feed_type,
                    "url": feed.url,
                    "format_type": feed.format_type,
                    "update_frequency": feed.update_frequency
                }
            )
            
            logger.info(f"Created threat feed {feed.id}: {feed.name}")
            return feed
            
        except IntegrityError as e:
            logger.error(f"Failed to create threat feed due to integrity constraint: {e}")
            raise ThreatFeedException("Feed conflicts with existing data")
    
    async def update_feed(self, feed_id: int, feed_data: Dict[str, Any]) -> Optional[ThreatFeed]:
        """Update a threat feed with validation"""
        logger.info(f"Updating threat feed ID: {feed_id}")
        
        # Get existing feed
        existing_feed = await self.get_by_id(feed_id)
        if not existing_feed:
            logger.warning(f"Threat feed {feed_id} not found for update")
            return None
        
        try:
            # Convert URL to string if it's a Pydantic URL object
            if 'url' in feed_data and hasattr(feed_data.get('url'), '__str__'):
                feed_data['url'] = str(feed_data['url'])
            
            # Check for duplicate name if name is being changed
            if 'name' in feed_data and feed_data['name'] != existing_feed.name:
                duplicate_feed = await self.get_feed_by_name(feed_data['name'])
                if duplicate_feed and duplicate_feed.id != feed_id:
                    raise ThreatFeedException(f"Threat feed with name '{feed_data['name']}' already exists")
            
            feed = await self.update(feed_id, feed_data, track_action=True)
            
            if feed:
                logger.info(f"Updated threat feed {feed.id}: {feed.name}")
            
            return feed
            
        except IntegrityError as e:
            logger.error(f"Failed to update threat feed due to integrity constraint: {e}")
            raise ThreatFeedException("Feed update conflicts with existing data")
    
    async def delete_feed(self, feed_id: int, remove_rules: bool = True) -> bool:
        """Delete a threat feed and optionally remove associated rules"""
        logger.info(f"Deleting threat feed ID: {feed_id}")
        
        # Get feed info before deletion for logging
        feed = await self.get_by_id(feed_id)
        if not feed:
            logger.warning(f"Threat feed {feed_id} not found for deletion")
            return False
        
        feed_name = feed.name
        
        # Remove associated RPZ rules if requested
        if remove_rules:
            logger.info(f"Removing RPZ rules associated with feed: {feed_name}")
            try:
                # Get rules created by this feed
                rules = await self.rpz_service.get_rules(
                    source=f"threat_feed_{feed_id}",
                    active_only=False,
                    limit=10000  # Large limit to get all rules
                )
                
                if rules:
                    rule_ids = [rule.id for rule in rules]
                    deleted_count, error_count, errors = await self.rpz_service.bulk_delete_rules(rule_ids)
                    logger.info(f"Removed {deleted_count} RPZ rules from feed {feed_name}")
                    
                    if errors:
                        logger.warning(f"Errors removing rules from feed {feed_name}: {errors}")
                
            except Exception as e:
                logger.error(f"Error removing rules from feed {feed_name}: {e}")
                # Continue with feed deletion even if rule removal fails
        
        success = await self.delete(feed_id, track_action=True)
        
        if success:
            logger.info(f"Deleted threat feed: {feed_name}")
        
        return success
    
    async def get_feed(self, feed_id: int) -> Optional[ThreatFeed]:
        """Get a threat feed by ID"""
        return await self.get_by_id(feed_id)
    
    async def get_feed_by_name(self, name: str) -> Optional[ThreatFeed]:
        """Get a threat feed by name"""
        if self.is_async:
            result = await self.db.execute(
                select(ThreatFeed).filter(ThreatFeed.name == name)
            )
            return result.scalar_one_or_none()
        else:
            return self.db.query(ThreatFeed).filter(ThreatFeed.name == name).first()
    
    async def get_feeds(self, 
                       skip: int = 0, 
                       limit: int = 100,
                       feed_type: Optional[str] = None,
                       active_only: bool = True,
                       sort_by: str = "created_at",
                       sort_order: str = "desc") -> List[ThreatFeed]:
        """Get threat feeds with filtering and pagination"""
        
        if self.is_async:
            query = select(ThreatFeed)
        else:
            query = self.db.query(ThreatFeed)
        
        # Apply filters
        filters = []
        
        if active_only:
            filters.append(ThreatFeed.is_active == True)
        
        if feed_type:
            filters.append(ThreatFeed.feed_type == feed_type)
        
        if filters:
            if self.is_async:
                query = query.filter(and_(*filters))
            else:
                query = query.filter(and_(*filters))
        
        # Apply sorting
        sort_column = getattr(ThreatFeed, sort_by, ThreatFeed.created_at)
        if sort_order.lower() == "asc":
            if self.is_async:
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            if self.is_async:
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
        
        # Apply pagination
        if self.is_async:
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        else:
            return query.offset(skip).limit(limit).all()
    
    async def count_feeds(self,
                         feed_type: Optional[str] = None,
                         active_only: bool = True) -> int:
        """Count threat feeds with filtering"""
        
        if self.is_async:
            query = select(func.count(ThreatFeed.id))
        else:
            query = self.db.query(func.count(ThreatFeed.id))
        
        # Apply filters
        filters = []
        
        if active_only:
            filters.append(ThreatFeed.is_active == True)
        
        if feed_type:
            filters.append(ThreatFeed.feed_type == feed_type)
        
        if filters:
            if self.is_async:
                query = query.filter(and_(*filters))
            else:
                query = query.filter(and_(*filters))
        
        if self.is_async:
            result = await self.db.execute(query)
            return result.scalar()
        else:
            return query.scalar()
    
    async def get_feeds_due_for_update(self) -> List[ThreatFeed]:
        """Get feeds that are due for update based on their update frequency"""
        now = datetime.utcnow()
        
        if self.is_async:
            query = select(ThreatFeed).filter(
                and_(
                    ThreatFeed.is_active == True,
                    or_(
                        ThreatFeed.last_updated.is_(None),
                        ThreatFeed.last_updated + func.make_interval(0, 0, 0, 0, 0, 0, ThreatFeed.update_frequency) <= now
                    )
                )
            )
            result = await self.db.execute(query)
            return result.scalars().all()
        else:
            return self.db.query(ThreatFeed).filter(
                and_(
                    ThreatFeed.is_active == True,
                    or_(
                        ThreatFeed.last_updated.is_(None),
                        ThreatFeed.last_updated + timedelta(seconds=ThreatFeed.update_frequency) <= now
                    )
                )
            ).all()
    
    async def fetch_feed_data(self, feed: ThreatFeed, timeout: int = 30) -> Tuple[bool, str, Optional[str]]:
        """Fetch data from a threat feed URL"""
        logger.info(f"Fetching data from feed: {feed.name} ({feed.url})")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(str(feed.url)) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"Successfully fetched {len(content)} characters from feed: {feed.name}")
                        return True, "success", content
                    else:
                        error_msg = f"HTTP {response.status}: {response.reason}"
                        logger.warning(f"Failed to fetch feed {feed.name}: {error_msg}")
                        return False, error_msg, None
                        
        except asyncio.TimeoutError:
            error_msg = f"Timeout after {timeout} seconds"
            logger.warning(f"Timeout fetching feed {feed.name}: {error_msg}")
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"Error fetching feed {feed.name}: {error_msg}")
            return False, error_msg, None
    
    def parse_feed_content(self, content: str, format_type: FormatType) -> List[str]:
        """Parse feed content based on format type and extract domains"""
        domains = []
        
        try:
            # Pre-process content to handle different encodings and line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            if format_type == FormatType.HOSTS:
                # Parse hosts file format (127.0.0.1 domain.com or 0.0.0.0 domain.com)
                domains = self._parse_hosts_format(content)
                                
            elif format_type == FormatType.DOMAINS:
                # Parse plain domain list format (one domain per line)
                domains = self._parse_domains_format(content)
            elif format_type == FormatType.URLS:
                # Parse URL list format (extract domains from URLs)
                domains = self._parse_urls_format(content)
            elif format_type == FormatType.JSON:
                # Parse JSON format (extract domains from JSON structure)
                domains = self._parse_json_format(content)
            elif format_type == FormatType.RPZ:
                # Parse RPZ format (domain CNAME .)
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith(';') and not line.startswith('$'):
                        parts = line.split()
                        if len(parts) >= 3 and parts[1].upper() == 'CNAME':
                            domain = parts[0].strip().lower()
                            if domain.endswith('.'):
                                domain = domain[:-1]  # Remove trailing dot
                            if self.is_valid_domain(domain):
                                domains.append(domain)
                                
            else:
                logger.warning(f"Unsupported format type: {format_type}")
                
        except Exception as e:
            logger.error(f"Error parsing feed content: {e}")
        
        # Remove duplicates while preserving order
        unique_domains = list(dict.fromkeys(domains))
        logger.info(f"Parsed {len(unique_domains)} unique domains from {len(content)} characters")
        
        return unique_domains
    
    def _parse_hosts_format(self, content: str) -> List[str]:
        """Parse hosts file format (127.0.0.1 domain.com or 0.0.0.0 domain.com)"""
        domains = []
        for line in content.split('\n'):
            line = self._clean_line(line)
            if not line:
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                # Extract domain (second part in hosts format)
                item = parts[1].strip().lower()
                domain = self._extract_domain_from_item(item)
                if domain and self.is_valid_domain(domain):
                    domains.append(domain)
        return domains
    
    def _parse_domains_format(self, content: str) -> List[str]:
        """Parse plain domain list format (one domain per line or URLs)"""
        domains = []
        for line in content.split('\n'):
            line = self._clean_line(line)
            if not line:
                continue
                
            # Handle multiple domains/URLs per line (space or tab separated)
            potential_items = re.split(r'\s+', line)
            for item in potential_items:
                item = item.strip().lower()
                if not item:
                    continue
                
                # Check if it's a URL and extract domain
                domain = self._extract_domain_from_item(item)
                if domain and self.is_valid_domain(domain):
                    domains.append(domain)
        return domains
    
    def _parse_urls_format(self, content: str) -> List[str]:
        """Parse URL list format (extract domains from URLs)"""
        domains = []
        for line in content.split('\n'):
            line = self._clean_line(line)
            if not line:
                continue
                
            # Handle multiple URLs per line (space or tab separated)
            potential_urls = re.split(r'\s+', line)
            for url in potential_urls:
                url = url.strip()
                if not url:
                    continue
                
                # Extract domain from URL
                domain = self._extract_domain_from_item(url)
                if domain and self.is_valid_domain(domain):
                    domains.append(domain)
        return domains
    
    def _parse_json_format(self, content: str) -> List[str]:
        """Parse JSON format (extract domains from JSON structure)"""
        domains = []
        try:
            import json
            data = json.loads(content)
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Array of domains/URLs
                for item in data:
                    if isinstance(item, str):
                        domain = self._extract_domain_from_item(item)
                        if domain and self.is_valid_domain(domain):
                            domains.append(domain)
                    elif isinstance(item, dict):
                        # Look for common domain/URL fields
                        for key in ['domain', 'url', 'host', 'hostname', 'site']:
                            if key in item and isinstance(item[key], str):
                                domain = self._extract_domain_from_item(item[key])
                                if domain and self.is_valid_domain(domain):
                                    domains.append(domain)
                                    break
            elif isinstance(data, dict):
                # Look for arrays of domains in the JSON object
                for key, value in data.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                domain = self._extract_domain_from_item(item)
                                if domain and self.is_valid_domain(domain):
                                    domains.append(domain)
                            elif isinstance(item, dict):
                                # Look for common domain/URL fields
                                for field in ['domain', 'url', 'host', 'hostname', 'site']:
                                    if field in item and isinstance(item[field], str):
                                        domain = self._extract_domain_from_item(item[field])
                                        if domain and self.is_valid_domain(domain):
                                            domains.append(domain)
                                            break
                    elif isinstance(value, str):
                        domain = self._extract_domain_from_item(value)
                        if domain and self.is_valid_domain(domain):
                            domains.append(domain)
                            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON content: {e}")
        except Exception as e:
            logger.error(f"Error processing JSON feed content: {e}")
            
        return domains
    
    def _parse_rpz_format(self, content: str) -> List[str]:
        """Parse RPZ format (domain CNAME .)"""
        domains = []
        for line in content.split('\n'):
            line = self._clean_line(line, comment_chars=[';', '#'])
            if not line:
                continue
                
            parts = line.split()
            if len(parts) >= 3 and parts[1].upper() == 'CNAME':
                domain = parts[0].strip().lower()
                if domain.endswith('.'):
                    domain = domain[:-1]  # Remove trailing dot
                if self.is_valid_domain(domain):
                    domains.append(domain)
        return domains
    
    def _clean_line(self, line: str, comment_chars: List[str] = None) -> str:
        """Clean and normalize a line from feed content"""
        if comment_chars is None:
            comment_chars = ['#', '//', ';']
        
        # Strip whitespace
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return ""
        
        # Remove comments (handle inline comments)
        for comment_char in comment_chars:
            if comment_char in line:
                # Find the first occurrence of comment character
                comment_pos = line.find(comment_char)
                # Only treat as comment if it's at start or preceded by whitespace
                if comment_pos == 0 or line[comment_pos - 1].isspace():
                    line = line[:comment_pos].strip()
                    break
        
        # Skip lines that are now empty after comment removal
        if not line:
            return ""
        
        # Skip common header patterns
        header_patterns = [
            r'^#.*',  # Lines starting with #
            r'^!.*',  # AdBlock style comments
            r'^\[.*\]$',  # Section headers like [Adblock Plus 2.0]
            r'^Last Update:.*',  # Update timestamps
            r'^Project website:.*',  # Project info
            r'^Support.*:.*',  # Support info
            r'^This work is licensed.*',  # License info
            r'^={3,}.*',  # Separator lines with equals
            r'^-{3,}.*',  # Separator lines with dashes
            r'^\s*$',  # Empty or whitespace-only lines
        ]
        
        for pattern in header_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return ""
        
        return line
    
    def _extract_domain_from_item(self, item: str) -> str:
        """Extract domain from either a plain domain or a URL"""
        item = item.strip().lower()
        
        # If it looks like a URL, extract the domain
        if item.startswith(('http://', 'https://', 'ftp://', 'ftps://')):
            try:
                # Remove protocol
                if item.startswith('http://'):
                    item = item[7:]
                elif item.startswith('https://'):
                    item = item[8:]
                elif item.startswith('ftp://'):
                    item = item[6:]
                elif item.startswith('ftps://'):
                    item = item[7:]
                
                # Extract domain part (everything before first slash, colon, or query)
                domain = item.split('/')[0].split(':')[0].split('?')[0].split('#')[0]
                
                # Remove any remaining unwanted characters
                domain = domain.strip()
                
                return domain
            except Exception as e:
                logger.debug(f"Failed to extract domain from URL '{item}': {e}")
                return ""
        
        # If it's already a plain domain, return as-is
        return item
    
    def is_valid_domain(self, domain: str) -> bool:
        """Validate if a string is a valid domain name"""
        if not domain or len(domain) > 253:
            return False
        
        # Basic domain regex pattern
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        return bool(domain_pattern.match(domain))
    
    async def load_default_feeds(self) -> Dict[str, Any]:
        """Load default threat feed configurations from JSON file"""
        try:
            import json
            from pathlib import Path
            
            # Get the path to the default feeds file
            current_dir = Path(__file__).parent.parent.parent
            feeds_file = current_dir / "data" / "default_threat_feeds.json"
            
            if not feeds_file.exists():
                logger.warning(f"Default feeds file not found: {feeds_file}")
                return {"default_feeds": [], "categories": {}, "metadata": {}}
            
            with open(feeds_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded {len(data.get('default_feeds', []))} default threat feeds")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load default threat feeds: {e}")
            return {"default_feeds": [], "categories": {}, "metadata": {}}
    
    async def import_default_feeds(self, selected_feeds: List[str] = None, activate_feeds: bool = True) -> Dict[str, Any]:
        """Import selected default threat feeds into the database"""
        try:
            default_data = await self.load_default_feeds()
            default_feeds = default_data.get("default_feeds", [])
            
            if not default_feeds:
                return {"success": False, "message": "No default feeds available", "imported": 0}
            
            imported_count = 0
            skipped_count = 0
            errors = []
            imported_feeds = []
            
            for feed_config in default_feeds:
                feed_name = feed_config.get("name")
                
                # Skip if specific feeds were requested and this isn't one of them
                if selected_feeds and feed_name not in selected_feeds:
                    continue
                
                # Check if feed already exists
                existing_feed = await self.get_feed_by_name(feed_name)
                if existing_feed:
                    logger.info(f"Skipping existing feed: {feed_name}")
                    skipped_count += 1
                    continue
                
                try:
                    # Prepare feed data for creation
                    feed_data = {
                        "name": feed_config["name"],
                        "url": feed_config["url"],
                        "feed_type": feed_config["feed_type"],
                        "format_type": feed_config["format_type"],
                        "description": feed_config.get("description", ""),
                        "update_frequency": feed_config.get("update_frequency", 3600),
                        "is_active": feed_config.get("is_active", True) if activate_feeds else False
                    }
                    
                    # Create the feed
                    new_feed = await self.create_feed(feed_data)
                    imported_count += 1
                    imported_feeds.append({
                        "id": new_feed.id,
                        "name": new_feed.name,
                        "category": feed_config.get("category", "unknown"),
                        "is_active": new_feed.is_active
                    })
                    
                    logger.info(f"Imported default feed: {feed_name}")
                    
                except Exception as e:
                    error_msg = f"Failed to import feed '{feed_name}': {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                "success": True,
                "imported": imported_count,
                "skipped": skipped_count,
                "errors": errors,
                "feeds": imported_feeds,
                "categories": default_data.get("categories", {}),
                "metadata": default_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to import default feeds: {e}")
            return {
                "success": False,
                "message": f"Import failed: {str(e)}",
                "imported": 0,
                "errors": [str(e)]
            }
    
    async def get_available_default_feeds(self) -> Dict[str, Any]:
        """Get list of available default feeds with their status"""
        try:
            default_data = await self.load_default_feeds()
            default_feeds = default_data.get("default_feeds", [])
            
            # Check which feeds are already imported
            feeds_with_status = []
            for feed_config in default_feeds:
                existing_feed = await self.get_feed_by_name(feed_config["name"])
                
                feed_info = {
                    "name": feed_config["name"],
                    "url": feed_config["url"],
                    "feed_type": feed_config["feed_type"],
                    "format_type": feed_config["format_type"],
                    "description": feed_config.get("description", ""),
                    "category": feed_config.get("category", "unknown"),
                    "update_frequency": feed_config.get("update_frequency", 3600),
                    "recommended_active": feed_config.get("is_active", True),
                    "is_imported": existing_feed is not None,
                    "current_status": {
                        "id": existing_feed.id if existing_feed else None,
                        "is_active": existing_feed.is_active if existing_feed else False,
                        "last_updated": existing_feed.last_updated.isoformat() if existing_feed and existing_feed.last_updated else None,
                        "rules_count": existing_feed.rules_count if existing_feed else 0
                    } if existing_feed else None
                }
                feeds_with_status.append(feed_info)
            
            return {
                "success": True,
                "feeds": feeds_with_status,
                "categories": default_data.get("categories", {}),
                "metadata": default_data.get("metadata", {}),
                "summary": {
                    "total_available": len(feeds_with_status),
                    "already_imported": sum(1 for f in feeds_with_status if f["is_imported"]),
                    "recommended_active": sum(1 for f in feeds_with_status if f["recommended_active"])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get available default feeds: {e}")
            return {
                "success": False,
                "message": f"Failed to load default feeds: {str(e)}",
                "feeds": []
            }
    
    async def update_feed_from_source(self, feed: ThreatFeed) -> ThreatFeedUpdateResult:
        """Update a single threat feed from its source"""
        logger.info(f"Updating feed from source: {feed.name}")
        
        start_time = datetime.utcnow()
        
        # Mark feed as pending update
        await self.update_feed(feed.id, {
            'last_update_status': UpdateStatus.PENDING
        })
        
        try:
            # Fetch feed data
            success, error_msg, content = await self.fetch_feed_data(feed)
            
            if not success or not content:
                # Update feed with failure status
                await self.update_feed(feed.id, {
                    'last_updated': start_time,
                    'last_update_status': UpdateStatus.FAILED,
                    'last_update_error': error_msg
                })
                
                return ThreatFeedUpdateResult(
                    feed_id=feed.id,
                    feed_name=feed.name,
                    status=UpdateStatus.FAILED,
                    error_message=error_msg,
                    update_duration=(datetime.utcnow() - start_time).total_seconds()
                )
            
            # Parse domains from content
            domains = self.parse_feed_content(content, feed.format_type)
            
            if not domains:
                error_msg = "No valid domains found in feed"
                await self.update_feed(feed.id, {
                    'last_updated': start_time,
                    'last_update_status': UpdateStatus.FAILED,
                    'last_update_error': error_msg
                })
                
                return ThreatFeedUpdateResult(
                    feed_id=feed.id,
                    feed_name=feed.name,
                    status=UpdateStatus.FAILED,
                    error_message=error_msg,
                    update_duration=(datetime.utcnow() - start_time).total_seconds()
                )
            
            # Get existing rules from this feed
            existing_rules = await self.rpz_service.get_rules(
                source=f"threat_feed_{feed.id}",
                active_only=False,
                limit=100000  # Large limit to get all rules
            )
            
            existing_domains = {rule.domain: rule for rule in existing_rules}
            
            # Determine what needs to be added, updated, or removed
            new_domains = set(domains)
            old_domains = set(existing_domains.keys())
            
            domains_to_add = new_domains - old_domains
            domains_to_remove = old_domains - new_domains
            domains_to_keep = new_domains & old_domains
            
            rules_added = 0
            rules_updated = 0
            rules_removed = 0
            
            # Add new rules
            if domains_to_add:
                new_rules_data = []
                for domain in domains_to_add:
                    rule_data = {
                        'domain': domain,
                        'rpz_zone': feed.feed_type,
                        'action': 'block',
                        'source': f"threat_feed_{feed.id}",
                        'description': f"Blocked by threat feed: {feed.name}",
                        'is_active': True
                    }
                    new_rules_data.append(rule_data)
                
                created_count, error_count, errors = await self.rpz_service.bulk_create_rules(
                    new_rules_data, 
                    source=f"threat_feed_{feed.id}"
                )
                rules_added = created_count
                
                if errors:
                    logger.warning(f"Errors adding rules from feed {feed.name}: {errors[:5]}")  # Log first 5 errors
            
            # Reactivate existing rules that are still in the feed
            if domains_to_keep:
                for domain in domains_to_keep:
                    rule = existing_domains[domain]
                    if not rule.is_active:
                        await self.rpz_service.update_rule(rule.id, {'is_active': True})
                        rules_updated += 1
            
            # Remove rules for domains no longer in the feed
            if domains_to_remove:
                rules_to_remove = [existing_domains[domain].id for domain in domains_to_remove]
                deleted_count, error_count, errors = await self.rpz_service.bulk_delete_rules(rules_to_remove)
                rules_removed = deleted_count
                
                if errors:
                    logger.warning(f"Errors removing rules from feed {feed.name}: {errors[:5]}")  # Log first 5 errors
            
            # Update feed status
            total_rules = len(new_domains)
            await self.update_feed(feed.id, {
                'last_updated': start_time,
                'last_update_status': UpdateStatus.SUCCESS,
                'last_update_error': None,
                'rules_count': total_rules
            })
            
            update_duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Successfully updated feed {feed.name}: "
                       f"{rules_added} added, {rules_updated} updated, {rules_removed} removed")
            
            return ThreatFeedUpdateResult(
                feed_id=feed.id,
                feed_name=feed.name,
                status=UpdateStatus.SUCCESS,
                rules_added=rules_added,
                rules_updated=rules_updated,
                rules_removed=rules_removed,
                update_duration=update_duration
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Error updating feed {feed.name}: {error_msg}")
            
            # Update feed with failure status
            await self.update_feed(feed.id, {
                'last_updated': start_time,
                'last_update_status': UpdateStatus.FAILED,
                'last_update_error': error_msg
            })
            
            return ThreatFeedUpdateResult(
                feed_id=feed.id,
                feed_name=feed.name,
                status=UpdateStatus.FAILED,
                error_message=error_msg,
                update_duration=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def update_all_feeds(self, force_update: bool = False) -> BulkThreatFeedUpdateResult:
        """Update all active threat feeds"""
        logger.info("Starting bulk threat feed update")
        
        start_time = datetime.utcnow()
        
        # Get feeds to update
        if force_update:
            feeds = await self.get_feeds(active_only=True, limit=1000)
        else:
            feeds = await self.get_feeds_due_for_update()
        
        if not feeds:
            logger.info("No feeds due for update")
            return BulkThreatFeedUpdateResult(
                total_feeds=0,
                successful_updates=0,
                failed_updates=0,
                update_duration=0
            )
        
        logger.info(f"Updating {len(feeds)} threat feeds")
        
        # Update feeds concurrently (but limit concurrency to avoid overwhelming servers)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent updates
        
        async def update_with_semaphore(feed):
            async with semaphore:
                return await self.update_feed_from_source(feed)
        
        # Execute updates
        update_tasks = [update_with_semaphore(feed) for feed in feeds]
        feed_results = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # Process results
        successful_updates = 0
        failed_updates = 0
        total_rules_added = 0
        total_rules_updated = 0
        total_rules_removed = 0
        processed_results = []
        
        for i, result in enumerate(feed_results):
            if isinstance(result, Exception):
                # Handle exceptions
                feed = feeds[i]
                error_result = ThreatFeedUpdateResult(
                    feed_id=feed.id,
                    feed_name=feed.name,
                    status=UpdateStatus.FAILED,
                    error_message=str(result)
                )
                processed_results.append(error_result)
                failed_updates += 1
                logger.error(f"Exception updating feed {feed.name}: {result}")
            else:
                # Handle successful results
                processed_results.append(result)
                if result.status == UpdateStatus.SUCCESS:
                    successful_updates += 1
                    total_rules_added += result.rules_added
                    total_rules_updated += result.rules_updated
                    total_rules_removed += result.rules_removed
                else:
                    failed_updates += 1
        
        update_duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Bulk update completed: {successful_updates} successful, {failed_updates} failed, "
                   f"{total_rules_added} rules added, {total_rules_updated} updated, {total_rules_removed} removed")
        
        return BulkThreatFeedUpdateResult(
            total_feeds=len(feeds),
            successful_updates=successful_updates,
            failed_updates=failed_updates,
            total_rules_added=total_rules_added,
            total_rules_updated=total_rules_updated,
            total_rules_removed=total_rules_removed,
            feed_results=processed_results,
            update_duration=update_duration
        )
    
    async def test_feed_connectivity(self, feed: ThreatFeed) -> Dict[str, Any]:
        """Test connectivity to a threat feed without updating rules"""
        logger.info(f"Testing connectivity to feed: {feed.name}")
        
        start_time = datetime.utcnow()
        
        # Fetch feed data
        success, error_msg, content = await self.fetch_feed_data(feed, timeout=10)
        
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        if success and content:
            # Parse content to get domain count
            domains = self.parse_feed_content(content, feed.format_type)
            
            return {
                'success': True,
                'response_time': response_time,
                'content_length': len(content),
                'domains_found': len(domains),
                'sample_domains': domains[:5] if domains else [],
                'error_message': None
            }
        else:
            return {
                'success': False,
                'response_time': response_time,
                'content_length': 0,
                'domains_found': 0,
                'sample_domains': [],
                'error_message': error_msg
            }
    
    async def get_feed_statistics(self) -> Dict[str, Any]:
        """Get comprehensive threat feed statistics"""
        logger.info("Generating threat feed statistics")
        
        # Get overall counts
        total_feeds = await self.count_feeds(active_only=False)
        active_feeds = await self.count_feeds(active_only=True)
        
        # Get feeds by type
        feed_types = [ft.value for ft in FeedType]
        feeds_by_type = {}
        
        for feed_type in feed_types:
            count = await self.count_feeds(feed_type=feed_type, active_only=True)
            feeds_by_type[feed_type] = count
        
        # Get update status counts
        if self.is_async:
            status_query = select(ThreatFeed.last_update_status, func.count(ThreatFeed.id)).group_by(ThreatFeed.last_update_status)
            status_result = await self.db.execute(status_query)
            status_counts = dict(status_result.fetchall())
        else:
            status_result = self.db.query(ThreatFeed.last_update_status, func.count(ThreatFeed.id)).group_by(ThreatFeed.last_update_status).all()
            status_counts = dict(status_result)
        
        # Get total rules from all feeds
        if self.is_async:
            rules_query = select(func.sum(ThreatFeed.rules_count)).filter(ThreatFeed.is_active == True)
            rules_result = await self.db.execute(rules_query)
            total_rules = rules_result.scalar() or 0
        else:
            total_rules = self.db.query(func.sum(ThreatFeed.rules_count)).filter(ThreatFeed.is_active == True).scalar() or 0
        
        # Get feeds due for update
        feeds_due = await self.get_feeds_due_for_update()
        
        return {
            'total_feeds': total_feeds,
            'active_feeds': active_feeds,
            'inactive_feeds': total_feeds - active_feeds,
            'feeds_by_type': feeds_by_type,
            'update_status_counts': status_counts,
            'total_rules_from_feeds': total_rules,
            'feeds_due_for_update': len(feeds_due),
            'last_generated': datetime.utcnow()
        }
    
    async def toggle_feed(self, feed_id: int) -> Optional[ThreatFeed]:
        """Toggle the active status of a threat feed"""
        feed = await self.get_by_id(feed_id)
        if not feed:
            return None
        
        new_status = not feed.is_active
        return await self.update_feed(feed_id, {'is_active': new_status})
    
    async def get_feed_health_status(self, feed_id: int) -> Dict[str, Any]:
        """Get health status information for a specific feed"""
        feed = await self.get_by_id(feed_id)
        if not feed:
            return {'error': 'Feed not found'}
        
        # Calculate next update time
        next_update = None
        if feed.last_updated and feed.is_active:
            next_update = feed.last_updated + timedelta(seconds=feed.update_frequency)
        
        # Determine health status
        health_status = 'unknown'
        if not feed.is_active:
            health_status = 'disabled'
        elif feed.last_update_status == UpdateStatus.SUCCESS:
            health_status = 'healthy'
        elif feed.last_update_status == UpdateStatus.FAILED:
            health_status = 'unhealthy'
        elif feed.last_update_status == UpdateStatus.PENDING:
            health_status = 'updating'
        elif feed.last_update_status == UpdateStatus.NEVER:
            health_status = 'never_updated'
        
        return {
            'feed_id': feed.id,
            'feed_name': feed.name,
            'health_status': health_status,
            'is_active': feed.is_active,
            'last_updated': feed.last_updated,
            'last_update_status': feed.last_update_status,
            'last_update_error': feed.last_update_error,
            'next_update': next_update,
            'rules_count': feed.rules_count,
            'update_frequency': feed.update_frequency
        }
    
    async def get_feed_effectiveness_report(self, days: int = 30) -> Dict[str, Any]:
        """Get effectiveness report for threat feeds based on blocking statistics"""
        logger.info(f"Generating feed effectiveness report for last {days} days")
        
        try:
            from datetime import timedelta
            from ..core.database import database
            
            since = datetime.utcnow() - timedelta(days=days)
            
            # Get all active feeds
            feeds = await self.get_feeds(active_only=True, limit=1000)
            
            feed_effectiveness = []
            
            for feed in feeds:
                # Get blocking statistics for this feed's rules
                blocking_stats = await database.fetch_one("""
                    SELECT 
                        COUNT(*) as blocks_generated,
                        COUNT(DISTINCT dl.client_ip) as clients_protected,
                        COUNT(DISTINCT dl.query_domain) as unique_threats_blocked
                    FROM dns_logs dl
                    JOIN rpz_rules rr ON dl.query_domain = rr.domain
                    WHERE dl.timestamp >= :since 
                    AND dl.blocked = true
                    AND rr.source LIKE :source_pattern
                """, {
                    "since": since,
                    "source_pattern": f"%feed_{feed.id}%"
                })
                
                if blocking_stats:
                    blocks = blocking_stats['blocks_generated'] or 0
                    clients = blocking_stats['clients_protected'] or 0
                    threats = blocking_stats['unique_threats_blocked'] or 0
                else:
                    blocks = clients = threats = 0
                
                # Calculate effectiveness metrics
                rules_count = feed.rules_count or 1  # Avoid division by zero
                effectiveness_score = min((blocks / rules_count) * 10, 100) if rules_count > 0 else 0
                
                feed_effectiveness.append({
                    'feed_id': feed.id,
                    'feed_name': feed.name,
                    'feed_type': feed.feed_type,
                    'rules_count': feed.rules_count,
                    'blocks_generated': blocks,
                    'clients_protected': clients,
                    'unique_threats_blocked': threats,
                    'effectiveness_score': round(effectiveness_score, 2),
                    'blocks_per_rule': round(blocks / rules_count, 2) if rules_count > 0 else 0,
                    'last_updated': feed.last_updated,
                    'update_status': feed.last_update_status
                })
            
            # Sort by effectiveness score
            feed_effectiveness.sort(key=lambda x: x['effectiveness_score'], reverse=True)
            
            # Calculate overall statistics
            total_feeds = len(feed_effectiveness)
            total_rules = sum(f['rules_count'] for f in feed_effectiveness)
            total_blocks = sum(f['blocks_generated'] for f in feed_effectiveness)
            
            # Find most and least effective feeds
            most_effective = feed_effectiveness[0] if feed_effectiveness else None
            least_effective = feed_effectiveness[-1] if feed_effectiveness else None
            
            return {
                'report_period': {
                    'days': days,
                    'start_date': since.isoformat(),
                    'end_date': datetime.utcnow().isoformat()
                },
                'overall_summary': {
                    'total_feeds_analyzed': total_feeds,
                    'total_rules_deployed': total_rules,
                    'total_blocks_generated': total_blocks,
                    'average_effectiveness_score': round(
                        sum(f['effectiveness_score'] for f in feed_effectiveness) / total_feeds, 2
                    ) if total_feeds > 0 else 0,
                    'most_effective_feed': most_effective['feed_name'] if most_effective else None,
                    'least_effective_feed': least_effective['feed_name'] if least_effective else None
                },
                'feed_effectiveness': feed_effectiveness,
                'effectiveness_categories': {
                    'highly_effective': len([f for f in feed_effectiveness if f['effectiveness_score'] >= 75]),
                    'moderately_effective': len([f for f in feed_effectiveness if 25 <= f['effectiveness_score'] < 75]),
                    'low_effectiveness': len([f for f in feed_effectiveness if f['effectiveness_score'] < 25])
                },
                'generated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate feed effectiveness report: {str(e)}")
            return {
                'error': f"Failed to generate effectiveness report: {str(e)}",
                'generated_at': datetime.utcnow()
            }
    
    async def schedule_feed_updates(self) -> BulkThreatFeedUpdateResult:
        """Schedule and execute updates for all feeds that are due"""
        logger.info("Starting scheduled threat feed updates")
        start_time = datetime.utcnow()
        
        try:
            # Get feeds due for update
            feeds_to_update = await self.get_feeds_due_for_update()
            
            if not feeds_to_update:
                logger.info("No feeds due for update")
                return BulkThreatFeedUpdateResult(
                    total_feeds=0,
                    successful_updates=0,
                    failed_updates=0,
                    update_duration=(datetime.utcnow() - start_time).total_seconds()
                )
            
            logger.info(f"Found {len(feeds_to_update)} feeds due for update")
            
            # Update feeds using existing bulk update method
            result = await self.update_all_feeds(force_update=False)
            
            logger.info(f"Scheduled updates completed: {result.successful_updates} successful, {result.failed_updates} failed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled updates: {str(e)}")
            raise ThreatFeedException(f"Scheduled update failed: {str(e)}")
    
    async def create_custom_threat_list(self, name: str, domains: List[str], 
                                      category: str = "custom", 
                                      description: Optional[str] = None) -> ThreatFeed:
        """Create a custom threat list from provided domains"""
        logger.info(f"Creating custom threat list: {name}")
        
        try:
            # Validate domains
            valid_domains = []
            for domain in domains:
                domain = domain.strip().lower()
                if domain and self.is_valid_domain(domain):
                    valid_domains.append(domain)
            
            if not valid_domains:
                raise ValidationException("No valid domains provided")
            
            # Create feed entry
            feed_data = {
                "name": name,
                "url": f"custom://{name.lower().replace(' ', '_')}",
                "feed_type": category,
                "format_type": "domains",
                "is_active": True,
                "update_frequency": 86400,  # 24 hours
                "description": description or f"Custom threat list with {len(valid_domains)} domains",
                "rules_count": len(valid_domains),
                "last_updated": datetime.utcnow(),
                "last_update_status": "success"
            }
            
            feed = await self.create_feed(feed_data)
            
            # Create RPZ rules for domains
            rules_created = 0
            
            for domain in valid_domains:
                try:
                    rule_data = {
                        "domain": domain,
                        "rpz_zone": category,
                        "action": "block",
                        "source": f"custom_feed_{feed.id}",
                        "description": f"Custom rule from {name}"
                    }
                    
                    await self.rpz_service.create_rule(rule_data)
                    rules_created += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to create rule for domain {domain}: {str(e)}")
            
            # Update feed with actual rules count
            await self.update_feed(feed.id, {"rules_count": rules_created})
            
            logger.info(f"Created custom threat list {feed.id} with {rules_created} rules")
            return feed
            
        except Exception as e:
            logger.error(f"Failed to create custom threat list: {str(e)}")
            raise ThreatFeedException(f"Failed to create custom list: {str(e)}")
    
    async def update_custom_threat_list(self, feed_id: int, domains: List[str]) -> ThreatFeedUpdateResult:
        """Update a custom threat list with new domains"""
        logger.info(f"Updating custom threat list {feed_id}")
        start_time = datetime.utcnow()
        
        try:
            # Get feed
            feed = await self.get_feed(feed_id)
            if not feed:
                raise ThreatFeedException("Feed not found")
            
            if not feed.url.startswith("custom://"):
                raise ThreatFeedException("Not a custom threat list")
            
            # Validate domains
            valid_domains = []
            for domain in domains:
                domain = domain.strip().lower()
                if domain and self.is_valid_domain(domain):
                    valid_domains.append(domain)
            
            # Get existing rules for this feed
            existing_rules = await self.rpz_service.get_rules(
                source=f"custom_feed_{feed_id}",
                active_only=False,
                limit=100000
            )
            existing_domains = {rule.domain for rule in existing_rules}
            
            new_domains = set(valid_domains)
            
            # Calculate changes
            domains_to_add = new_domains - existing_domains
            domains_to_remove = existing_domains - new_domains
            
            rules_added = 0
            rules_removed = 0
            
            # Add new domains
            for domain in domains_to_add:
                try:
                    rule_data = {
                        "domain": domain,
                        "rpz_zone": feed.feed_type,
                        "action": "block",
                        "source": f"custom_feed_{feed_id}",
                        "description": f"Custom rule from {feed.name}"
                    }
                    
                    await self.rpz_service.create_rule(rule_data)
                    rules_added += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to add rule for domain {domain}: {str(e)}")
            
            # Remove old domains
            for rule in existing_rules:
                if rule.domain in domains_to_remove:
                    try:
                        await self.rpz_service.delete_rule(rule.id)
                        rules_removed += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove rule for domain {rule.domain}: {str(e)}")
            
            # Update feed
            new_count = len(valid_domains)
            await self.update_feed(feed_id, {
                "rules_count": new_count,
                "last_updated": datetime.utcnow(),
                "last_update_status": "success"
            })
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Updated custom threat list {feed_id}: +{rules_added}, -{rules_removed} rules in {duration:.2f}s")
            
            return ThreatFeedUpdateResult(
                feed_id=feed_id,
                feed_name=feed.name,
                status=UpdateStatus.SUCCESS,
                rules_added=rules_added,
                rules_updated=0,
                rules_removed=rules_removed,
                update_duration=duration
            )
            
        except Exception as e:
            logger.error(f"Failed to update custom threat list {feed_id}: {str(e)}")
            return ThreatFeedUpdateResult(
                feed_id=feed_id,
                feed_name=f"Feed {feed_id}",
                status=UpdateStatus.FAILED,
                error_message=str(e),
                update_duration=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def get_comprehensive_statistics(self, feed_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive threat feed statistics with health metrics"""
        try:
            stats = {
                "total_feeds": 0,
                "active_feeds": 0,
                "inactive_feeds": 0,
                "total_rules": 0,
                "rules_by_category": {},
                "feeds_by_status": {},
                "update_statistics": {
                    "successful_updates_24h": 0,
                    "failed_updates_24h": 0,
                    "pending_updates": 0,
                    "never_updated": 0
                },
                "health_metrics": {
                    "overall_health_score": 0,
                    "feeds_needing_attention": [],
                    "recommendations": []
                },
                "feed_details": []
            }
            
            # Get base query
            if self.is_async:
                if feed_id:
                    query = select(ThreatFeed).filter(ThreatFeed.id == feed_id)
                else:
                    query = select(ThreatFeed)
                result = await self.db.execute(query)
                feeds = result.scalars().all()
            else:
                if feed_id:
                    feeds = self.db.query(ThreatFeed).filter(ThreatFeed.id == feed_id).all()
                else:
                    feeds = self.db.query(ThreatFeed).all()
            
            # Calculate statistics
            now = datetime.utcnow()
            twenty_four_hours_ago = now - timedelta(hours=24)
            health_issues = []
            
            for feed in feeds:
                stats["total_feeds"] += 1
                
                if feed.is_active:
                    stats["active_feeds"] += 1
                else:
                    stats["inactive_feeds"] += 1
                
                stats["total_rules"] += feed.rules_count
                
                # Rules by category
                category = feed.feed_type
                if category not in stats["rules_by_category"]:
                    stats["rules_by_category"][category] = 0
                stats["rules_by_category"][category] += feed.rules_count
                
                # Feeds by status
                status = feed.last_update_status or "never"
                if status not in stats["feeds_by_status"]:
                    stats["feeds_by_status"][status] = 0
                stats["feeds_by_status"][status] += 1
                
                # Update statistics
                if feed.last_updated:
                    if feed.last_updated >= twenty_four_hours_ago:
                        if feed.last_update_status == "success":
                            stats["update_statistics"]["successful_updates_24h"] += 1
                        elif feed.last_update_status == "failed":
                            stats["update_statistics"]["failed_updates_24h"] += 1
                    
                    if feed.last_update_status == "pending":
                        stats["update_statistics"]["pending_updates"] += 1
                else:
                    stats["update_statistics"]["never_updated"] += 1
                
                # Health assessment
                feed_health_issues = []
                if not feed.is_active:
                    feed_health_issues.append("Feed is disabled")
                elif feed.last_update_status == "failed":
                    feed_health_issues.append("Last update failed")
                elif not feed.last_updated:
                    feed_health_issues.append("Never updated")
                elif feed.rules_count == 0:
                    feed_health_issues.append("No rules generated")
                
                if feed_health_issues:
                    stats["health_metrics"]["feeds_needing_attention"].append({
                        "feed_id": feed.id,
                        "feed_name": feed.name,
                        "issues": feed_health_issues
                    })
                
                # Feed details
                next_update = None
                if feed.is_active and feed.last_updated:
                    next_update = feed.last_updated + timedelta(seconds=feed.update_frequency)
                
                stats["feed_details"].append({
                    "id": feed.id,
                    "name": feed.name,
                    "feed_type": feed.feed_type,
                    "is_active": feed.is_active,
                    "rules_count": feed.rules_count,
                    "last_updated": feed.last_updated,
                    "last_update_status": feed.last_update_status,
                    "next_update": next_update,
                    "update_frequency": feed.update_frequency,
                    "health_issues": feed_health_issues
                })
            
            # Calculate overall health score
            total_feeds = stats["total_feeds"]
            if total_feeds == 0:
                stats["health_metrics"]["overall_health_score"] = 0
                stats["health_metrics"]["recommendations"].append("Configure at least one threat feed")
            else:
                health_score = 100
                
                # Deduct points for various issues
                inactive_ratio = stats["inactive_feeds"] / total_feeds
                if inactive_ratio > 0.2:  # More than 20% inactive
                    health_score -= min(30, inactive_ratio * 100)
                    stats["health_metrics"]["recommendations"].append("Enable more threat feeds")
                
                failed_ratio = stats["update_statistics"]["failed_updates_24h"] / max(1, stats["active_feeds"])
                if failed_ratio > 0.1:  # More than 10% failed
                    health_score -= min(25, failed_ratio * 100)
                    stats["health_metrics"]["recommendations"].append("Fix failing threat feeds")
                
                never_updated_ratio = stats["update_statistics"]["never_updated"] / total_feeds
                if never_updated_ratio > 0.1:  # More than 10% never updated
                    health_score -= min(20, never_updated_ratio * 100)
                    stats["health_metrics"]["recommendations"].append("Update feeds that have never been updated")
                
                if stats["total_rules"] < 1000:
                    health_score -= 15
                    stats["health_metrics"]["recommendations"].append("Add more comprehensive threat feeds")
                
                stats["health_metrics"]["overall_health_score"] = max(0, int(health_score))
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive statistics: {str(e)}")
            raise ThreatFeedException(f"Failed to get statistics: {str(e)}")
    
    async def get_feed_update_schedule(self) -> Dict[str, Any]:
        """Get the update schedule for all active feeds"""
        try:
            feeds = await self.get_feeds(active_only=True, limit=1000)
            now = datetime.utcnow()
            
            schedule = {
                "current_time": now,
                "feeds_due_now": [],
                "upcoming_updates": [],
                "overdue_feeds": [],
                "schedule_summary": {
                    "total_active_feeds": len(feeds),
                    "feeds_due_now": 0,
                    "feeds_overdue": 0,
                    "next_update_in_minutes": None
                }
            }
            
            next_update_times = []
            
            for feed in feeds:
                if not feed.last_updated:
                    # Never updated - due now
                    schedule["feeds_due_now"].append({
                        "feed_id": feed.id,
                        "feed_name": feed.name,
                        "reason": "Never updated",
                        "priority": "high"
                    })
                    schedule["schedule_summary"]["feeds_due_now"] += 1
                else:
                    next_update = feed.last_updated + timedelta(seconds=feed.update_frequency)
                    next_update_times.append(next_update)
                    
                    if next_update <= now:
                        # Overdue
                        minutes_overdue = int((now - next_update).total_seconds() / 60)
                        schedule["overdue_feeds"].append({
                            "feed_id": feed.id,
                            "feed_name": feed.name,
                            "next_update": next_update,
                            "minutes_overdue": minutes_overdue,
                            "priority": "high" if minutes_overdue > 60 else "medium"
                        })
                        schedule["schedule_summary"]["feeds_overdue"] += 1
                    else:
                        # Upcoming
                        minutes_until = int((next_update - now).total_seconds() / 60)
                        schedule["upcoming_updates"].append({
                            "feed_id": feed.id,
                            "feed_name": feed.name,
                            "next_update": next_update,
                            "minutes_until": minutes_until,
                            "update_frequency_hours": feed.update_frequency / 3600
                        })
            
            # Find next update time
            if next_update_times:
                next_update = min(next_update_times)
                if next_update > now:
                    schedule["schedule_summary"]["next_update_in_minutes"] = int(
                        (next_update - now).total_seconds() / 60
                    )
            
            # Sort upcoming updates by time
            schedule["upcoming_updates"].sort(key=lambda x: x["minutes_until"])
            
            return schedule
            
        except Exception as e:
            logger.error(f"Failed to get feed update schedule: {str(e)}")
            raise ThreatFeedException(f"Failed to get update schedule: {str(e)}")   
 
    async def _emit_threat_feed_event(self, event_type: EventType, feed: Optional[ThreatFeed], 
                                     action: str, details: Dict[str, Any]):
        """Helper method to emit threat feed-related events"""
        try:
            user_id = get_current_user_id()
            
            # Create event data
            event_data = {
                "action": action,
                "feed_id": feed.id if feed else details.get("feed_id"),
                "feed_name": feed.name if feed else details.get("feed_name"),
                "feed_type": feed.feed_type if feed else details.get("feed_type"),
                "url": feed.url if feed else details.get("url"),
                "rules_count": feed.rules_count if feed else details.get("rules_count", 0),
                "last_update_status": feed.last_update_status if feed else details.get("last_update_status"),
                **details
            }
            
            # Determine event priority and severity
            if action == "update_failed":
                priority = EventPriority.HIGH
                severity = EventSeverity.ERROR
            elif action == "update_success" and details.get("rules_added", 0) > 100:
                priority = EventPriority.HIGH
                severity = EventSeverity.MEDIUM
            elif action == "delete":
                priority = EventPriority.HIGH
                severity = EventSeverity.MEDIUM
            else:
                priority = EventPriority.NORMAL
                severity = EventSeverity.LOW
            
            # Create and emit the event
            event = create_event(
                event_type=event_type,
                category=EventCategory.SECURITY,
                data=event_data,
                user_id=user_id,
                priority=priority,
                severity=severity,
                metadata={
                    "service": "threat_feed_service",
                    "action": action,
                    "feed_name": feed.name if feed else details.get("feed_name"),
                    "feed_type": feed.feed_type if feed else details.get("feed_type")
                }
            )
            
            await self.event_service.emit_event(event)
            
        except Exception as e:
            logger.error(f"Failed to emit threat feed event: {e}")
            # Don't raise the exception to avoid breaking the main operation
    
    async def _emit_threat_detection_event(self, threat_type: str, domain: str, 
                                          source: str, details: Dict[str, Any]):
        """Helper method to emit real-time threat detection events"""
        try:
            # Create event data for threat detection
            event_data = {
                "threat_type": threat_type,
                "domain": domain,
                "source": source,
                "detection_time": datetime.utcnow().isoformat(),
                **details
            }
            
            # Determine severity based on threat type
            if threat_type in ["malware", "ransomware", "trojan"]:
                severity = EventSeverity.CRITICAL
                priority = EventPriority.CRITICAL
            elif threat_type in ["phishing", "scam"]:
                severity = EventSeverity.WARNING
                priority = EventPriority.HIGH
            else:
                severity = EventSeverity.MEDIUM
                priority = EventPriority.NORMAL
            
            # Create and emit the event
            event = create_event(
                event_type=EventType.SECURITY_THREAT_DETECTED,
                category=EventCategory.SECURITY,
                data=event_data,
                priority=priority,
                severity=severity,
                metadata={
                    "service": "threat_feed_service",
                    "threat_type": threat_type,
                    "domain": domain,
                    "source": source
                }
            )
            
            await self.event_service.emit_event(event)
            
        except Exception as e:
            logger.error(f"Failed to emit threat detection event: {e}")
            # Don't raise the exception to avoid breaking the main operation