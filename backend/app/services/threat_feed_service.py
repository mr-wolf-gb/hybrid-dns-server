"""
Threat Feed service for managing external threat intelligence sources
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

logger = get_logger(__name__)


class ThreatFeedService(BaseService[ThreatFeed]):
    """Threat Feed service with authentication and automatic updates"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, ThreatFeed)
        self.rpz_service = RPZService(db)
    
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
        
        # Set default values
        feed_data.setdefault('is_active', True)
        feed_data.setdefault('update_frequency', 3600)  # 1 hour default
        feed_data.setdefault('rules_count', 0)
        feed_data.setdefault('last_update_status', UpdateStatus.NEVER)
        
        try:
            # Check for duplicate name
            existing_feed = await self.get_feed_by_name(feed_data['name'])
            if existing_feed:
                raise ThreatFeedException(f"Threat feed with name '{feed_data['name']}' already exists")
            
            # Create the feed
            feed = await self.create(feed_data, track_action=True)
            
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
            if format_type == FormatType.HOSTS:
                # Parse hosts file format (127.0.0.1 domain.com or 0.0.0.0 domain.com)
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            # Extract domain (second part in hosts format)
                            domain = parts[1].strip().lower()
                            if self.is_valid_domain(domain):
                                domains.append(domain)
                                
            elif format_type == FormatType.DOMAINS:
                # Parse plain domain list format (one domain per line)
                for line in content.split('\n'):
                    line = line.strip().lower()
                    if line and not line.startswith('#'):
                        if self.is_valid_domain(line):
                            domains.append(line)
                            
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
    
    def is_valid_domain(self, domain: str) -> bool:
        """Validate if a string is a valid domain name"""
        if not domain or len(domain) > 253:
            return False
        
        # Basic domain regex pattern
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        return bool(domain_pattern.match(domain))
    
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