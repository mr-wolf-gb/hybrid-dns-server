"""
RPZ (Response Policy Zone) service with authentication integration
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.exc import IntegrityError

from .base_service import BaseService
from ..models.security import RPZRule, ThreatFeed
from ..schemas.security import RPZRuleCreate, RPZRuleUpdate, RPZAction
from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger
from ..core.exceptions import ValidationException, RPZException

logger = get_logger(__name__)


class RPZService(BaseService[RPZRule]):
    """RPZ service with authentication and audit logging"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, RPZRule)
    
    async def create_rule(self, rule_data: Dict[str, Any]) -> RPZRule:
        """Create a new RPZ rule with validation and user tracking"""
        logger.info(f"Creating RPZ rule for domain: {rule_data.get('domain')}")
        
        # Validate required fields
        if not rule_data.get('domain'):
            raise ValidationException("Domain is required")
        if not rule_data.get('rpz_zone'):
            raise ValidationException("RPZ zone is required")
        if not rule_data.get('action'):
            raise ValidationException("Action is required")
        
        # Normalize domain
        rule_data['domain'] = rule_data['domain'].strip().lower()
        
        # Validate action and redirect target
        if rule_data['action'] == RPZAction.REDIRECT and not rule_data.get('redirect_target'):
            raise ValidationException("Redirect target is required for redirect action")
        
        # Set default values
        rule_data.setdefault('is_active', True)
        rule_data.setdefault('source', 'manual')
        
        try:
            # Check for duplicate domain in same zone
            existing_rule = await self.get_rule_by_domain_and_zone(
                rule_data['domain'], 
                rule_data['rpz_zone']
            )
            if existing_rule:
                raise RPZException(f"Rule for domain '{rule_data['domain']}' already exists in zone '{rule_data['rpz_zone']}'")
            
            # Create the rule
            rule = await self.create(rule_data, track_action=True)
            
            logger.info(f"Created RPZ rule {rule.id} for domain {rule.domain} with action {rule.action}")
            return rule
            
        except IntegrityError as e:
            logger.error(f"Failed to create RPZ rule due to integrity constraint: {e}")
            raise RPZException("Rule conflicts with existing data")
    
    async def update_rule(self, rule_id: int, rule_data: Dict[str, Any]) -> Optional[RPZRule]:
        """Update an RPZ rule with validation and user tracking"""
        logger.info(f"Updating RPZ rule ID: {rule_id}")
        
        # Get existing rule
        existing_rule = await self.get_by_id(rule_id)
        if not existing_rule:
            logger.warning(f"RPZ rule {rule_id} not found for update")
            return None
        
        # Normalize domain if provided
        if 'domain' in rule_data and rule_data['domain']:
            rule_data['domain'] = rule_data['domain'].strip().lower()
        
        # Validate action and redirect target
        action = rule_data.get('action', existing_rule.action)
        redirect_target = rule_data.get('redirect_target', existing_rule.redirect_target)
        
        if action == RPZAction.REDIRECT and not redirect_target:
            raise ValidationException("Redirect target is required for redirect action")
        
        try:
            # Check for duplicate domain if domain or zone is being changed
            if 'domain' in rule_data or 'rpz_zone' in rule_data:
                new_domain = rule_data.get('domain', existing_rule.domain)
                new_zone = rule_data.get('rpz_zone', existing_rule.rpz_zone)
                
                # Only check if domain or zone actually changed
                if new_domain != existing_rule.domain or new_zone != existing_rule.rpz_zone:
                    duplicate_rule = await self.get_rule_by_domain_and_zone(new_domain, new_zone)
                    if duplicate_rule and duplicate_rule.id != rule_id:
                        raise RPZException(f"Rule for domain '{new_domain}' already exists in zone '{new_zone}'")
            
            rule = await self.update(rule_id, rule_data, track_action=True)
            
            if rule:
                logger.info(f"Updated RPZ rule {rule.id} for domain {rule.domain}")
            
            return rule
            
        except IntegrityError as e:
            logger.error(f"Failed to update RPZ rule due to integrity constraint: {e}")
            raise RPZException("Rule update conflicts with existing data")
    
    async def delete_rule(self, rule_id: int) -> bool:
        """Delete an RPZ rule with user tracking"""
        logger.info(f"Deleting RPZ rule ID: {rule_id}")
        
        # Get rule info before deletion for logging
        rule = await self.get_by_id(rule_id)
        if not rule:
            logger.warning(f"RPZ rule {rule_id} not found for deletion")
            return False
        
        domain = rule.domain
        success = await self.delete(rule_id, track_action=True)
        
        if success:
            logger.info(f"Deleted RPZ rule for domain {domain}")
        
        return success
    
    async def get_rule(self, rule_id: int) -> Optional[RPZRule]:
        """Get an RPZ rule by ID"""
        return await self.get_by_id(rule_id)
    
    async def get_rule_by_domain_and_zone(self, domain: str, rpz_zone: str) -> Optional[RPZRule]:
        """Get an RPZ rule by domain and zone"""
        domain = domain.strip().lower()
        
        if self.is_async:
            result = await self.db.execute(
                select(RPZRule).filter(
                    and_(
                        RPZRule.domain == domain,
                        RPZRule.rpz_zone == rpz_zone
                    )
                )
            )
            return result.scalar_one_or_none()
        else:
            return self.db.query(RPZRule).filter(
                and_(
                    RPZRule.domain == domain,
                    RPZRule.rpz_zone == rpz_zone
                )
            ).first()
    
    async def get_rules(self, 
                       skip: int = 0, 
                       limit: int = 100,
                       rpz_zone: Optional[str] = None,
                       action: Optional[str] = None,
                       source: Optional[str] = None,
                       active_only: bool = True,
                       search: Optional[str] = None,
                       sort_by: str = "created_at",
                       sort_order: str = "desc") -> List[RPZRule]:
        """Get RPZ rules with filtering and pagination"""
        
        if self.is_async:
            query = select(RPZRule)
        else:
            query = self.db.query(RPZRule)
        
        # Apply filters
        filters = []
        
        if active_only:
            filters.append(RPZRule.is_active == True)
        
        if rpz_zone:
            filters.append(RPZRule.rpz_zone == rpz_zone)
        
        if action:
            filters.append(RPZRule.action == action)
        
        if source:
            filters.append(RPZRule.source == source)
        
        if search:
            search_term = f"%{search.lower()}%"
            filters.append(
                or_(
                    RPZRule.domain.ilike(search_term),
                    RPZRule.description.ilike(search_term)
                )
            )
        
        if filters:
            if self.is_async:
                query = query.filter(and_(*filters))
            else:
                query = query.filter(and_(*filters))
        
        # Apply sorting
        sort_column = getattr(RPZRule, sort_by, RPZRule.created_at)
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
    
    async def count_rules(self,
                         rpz_zone: Optional[str] = None,
                         action: Optional[str] = None,
                         source: Optional[str] = None,
                         active_only: bool = True,
                         search: Optional[str] = None) -> int:
        """Count RPZ rules with filtering"""
        
        if self.is_async:
            query = select(func.count(RPZRule.id))
        else:
            query = self.db.query(func.count(RPZRule.id))
        
        # Apply filters
        filters = []
        
        if active_only:
            filters.append(RPZRule.is_active == True)
        
        if rpz_zone:
            filters.append(RPZRule.rpz_zone == rpz_zone)
        
        if action:
            filters.append(RPZRule.action == action)
        
        if source:
            filters.append(RPZRule.source == source)
        
        if search:
            search_term = f"%{search.lower()}%"
            filters.append(
                or_(
                    RPZRule.domain.ilike(search_term),
                    RPZRule.description.ilike(search_term)
                )
            )
        
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
    
    async def get_rules_by_zone(self, rpz_zone: str, active_only: bool = True) -> List[RPZRule]:
        """Get all rules for a specific RPZ zone"""
        filters = {'rpz_zone': rpz_zone}
        if active_only:
            filters['is_active'] = True
        
        return await self.get_all(filters=filters)
    
    async def get_rules_by_action(self, action: str, active_only: bool = True) -> List[RPZRule]:
        """Get all rules with a specific action"""
        filters = {'action': action}
        if active_only:
            filters['is_active'] = True
        
        return await self.get_all(filters=filters)
    
    async def toggle_rule(self, rule_id: int) -> Optional[RPZRule]:
        """Toggle the active status of an RPZ rule"""
        rule = await self.get_by_id(rule_id)
        if not rule:
            return None
        
        new_status = not rule.is_active
        return await self.update_rule(rule_id, {'is_active': new_status})
    
    async def bulk_create_rules(self, rules_data: List[Dict[str, Any]], 
                               source: str = "bulk_import") -> Tuple[int, int, List[str]]:
        """Bulk create RPZ rules with error handling"""
        logger.info(f"Bulk creating {len(rules_data)} RPZ rules")
        
        created_count = 0
        error_count = 0
        errors = []
        
        for i, rule_data in enumerate(rules_data):
            try:
                rule_data['source'] = source
                await self.create_rule(rule_data)
                created_count += 1
            except Exception as e:
                error_count += 1
                error_msg = f"Rule {i+1} (domain: {rule_data.get('domain', 'unknown')}): {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Failed to create rule in bulk import: {error_msg}")
        
        logger.info(f"Bulk import completed: {created_count} created, {error_count} errors")
        return created_count, error_count, errors
    
    async def bulk_update_rules(self, updates: List[Tuple[int, Dict[str, Any]]]) -> Tuple[int, int, List[str]]:
        """Bulk update RPZ rules with error handling"""
        logger.info(f"Bulk updating {len(updates)} RPZ rules")
        
        updated_count = 0
        error_count = 0
        errors = []
        
        for rule_id, rule_data in updates:
            try:
                result = await self.update_rule(rule_id, rule_data)
                if result:
                    updated_count += 1
                else:
                    error_count += 1
                    errors.append(f"Rule {rule_id}: Not found")
            except Exception as e:
                error_count += 1
                error_msg = f"Rule {rule_id}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Failed to update rule in bulk update: {error_msg}")
        
        logger.info(f"Bulk update completed: {updated_count} updated, {error_count} errors")
        return updated_count, error_count, errors
    
    async def bulk_delete_rules(self, rule_ids: List[int]) -> Tuple[int, int, List[str]]:
        """Bulk delete RPZ rules with error handling"""
        logger.info(f"Bulk deleting {len(rule_ids)} RPZ rules")
        
        deleted_count = 0
        error_count = 0
        errors = []
        
        for rule_id in rule_ids:
            try:
                success = await self.delete_rule(rule_id)
                if success:
                    deleted_count += 1
                else:
                    error_count += 1
                    errors.append(f"Rule {rule_id}: Not found")
            except Exception as e:
                error_count += 1
                error_msg = f"Rule {rule_id}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Failed to delete rule in bulk delete: {error_msg}")
        
        logger.info(f"Bulk delete completed: {deleted_count} deleted, {error_count} errors")
        return deleted_count, error_count, errors
    
    async def get_zone_statistics(self, rpz_zone: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for RPZ rules"""
        logger.info(f"Getting RPZ statistics for zone: {rpz_zone or 'all'}")
        
        base_filters = []
        if rpz_zone:
            base_filters.append(RPZRule.rpz_zone == rpz_zone)
        
        if self.is_async:
            # Total rules
            total_query = select(func.count(RPZRule.id))
            if base_filters:
                total_query = total_query.filter(and_(*base_filters))
            total_result = await self.db.execute(total_query)
            total_rules = total_result.scalar()
            
            # Active rules
            active_query = select(func.count(RPZRule.id))
            active_filters = base_filters + [RPZRule.is_active == True]
            active_query = active_query.filter(and_(*active_filters))
            active_result = await self.db.execute(active_query)
            active_rules = active_result.scalar()
            
            # Rules by action
            action_query = select(RPZRule.action, func.count(RPZRule.id))
            if base_filters:
                action_query = action_query.filter(and_(*base_filters))
            action_query = action_query.group_by(RPZRule.action)
            action_result = await self.db.execute(action_query)
            rules_by_action = dict(action_result.fetchall())
            
            # Rules by source
            source_query = select(RPZRule.source, func.count(RPZRule.id))
            if base_filters:
                source_query = source_query.filter(and_(*base_filters))
            source_query = source_query.group_by(RPZRule.source)
            source_result = await self.db.execute(source_query)
            rules_by_source = dict(source_result.fetchall())
            
            # Rules by category (rpz_zone)
            category_query = select(RPZRule.rpz_zone, func.count(RPZRule.id))
            if base_filters:
                category_query = category_query.filter(and_(*base_filters))
            category_query = category_query.group_by(RPZRule.rpz_zone)
            category_result = await self.db.execute(category_query)
            rules_by_category = dict(category_result.fetchall())
            
        else:
            # Total rules
            total_query = self.db.query(func.count(RPZRule.id))
            if base_filters:
                total_query = total_query.filter(and_(*base_filters))
            total_rules = total_query.scalar()
            
            # Active rules
            active_query = self.db.query(func.count(RPZRule.id))
            active_filters = base_filters + [RPZRule.is_active == True]
            active_query = active_query.filter(and_(*active_filters))
            active_rules = active_query.scalar()
            
            # Rules by action
            action_query = self.db.query(RPZRule.action, func.count(RPZRule.id))
            if base_filters:
                action_query = action_query.filter(and_(*base_filters))
            action_query = action_query.group_by(RPZRule.action)
            rules_by_action = dict(action_query.all())
            
            # Rules by source
            source_query = self.db.query(RPZRule.source, func.count(RPZRule.id))
            if base_filters:
                source_query = source_query.filter(and_(*base_filters))
            source_query = source_query.group_by(RPZRule.source)
            rules_by_source = dict(source_query.all())
            
            # Rules by category (rpz_zone)
            category_query = self.db.query(RPZRule.rpz_zone, func.count(RPZRule.id))
            if base_filters:
                category_query = category_query.filter(and_(*base_filters))
            category_query = category_query.group_by(RPZRule.rpz_zone)
            rules_by_category = dict(category_query.all())
        
        statistics = {
            'total_rules': total_rules,
            'active_rules': active_rules,
            'inactive_rules': total_rules - active_rules,
            'rules_by_action': rules_by_action,
            'rules_by_source': rules_by_source,
            'rules_by_category': rules_by_category,
            'zone': rpz_zone
        }
        
        logger.info(f"RPZ statistics: {statistics}")
        return statistics
    
    async def validate_rule_data(self, rule_data: Dict[str, Any]) -> List[str]:
        """Validate RPZ rule data and return list of validation errors"""
        errors = []
        
        # Required fields
        if not rule_data.get('domain'):
            errors.append("Domain is required")
        elif not rule_data['domain'].strip():
            errors.append("Domain cannot be empty")
        
        if not rule_data.get('rpz_zone'):
            errors.append("RPZ zone is required")
        
        if not rule_data.get('action'):
            errors.append("Action is required")
        
        # Action-specific validation
        if rule_data.get('action') == RPZAction.REDIRECT:
            if not rule_data.get('redirect_target'):
                errors.append("Redirect target is required for redirect action")
            elif not rule_data['redirect_target'].strip():
                errors.append("Redirect target cannot be empty")
        
        # Domain format validation (basic)
        domain = rule_data.get('domain', '').strip().lower()
        if domain:
            if not all(c.isalnum() or c in '.-_' for c in domain):
                errors.append("Domain contains invalid characters")
            
            if domain.startswith('.') or domain.endswith('.'):
                errors.append("Domain cannot start or end with a dot")
            
            if '..' in domain:
                errors.append("Domain cannot contain consecutive dots")
        
        return errors
    
    async def get_rule_zone(self, rule_id: int) -> Optional[str]:
        """Get the RPZ zone for a specific rule"""
        rule = await self.get_by_id(rule_id)
        return rule.rpz_zone if rule else None
    
    # Category Management Methods
    
    async def get_available_categories(self) -> List[str]:
        """Get list of available RPZ categories"""
        return ['malware', 'phishing', 'adult', 'social-media', 'gambling', 'custom']
    
    async def get_category_info(self, category: str) -> Dict[str, Any]:
        """Get detailed information about a specific category"""
        if category not in await self.get_available_categories():
            raise ValidationException(f"Invalid category: {category}")
        
        category_descriptions = {
            'malware': 'Malicious domains including viruses, trojans, and other malware',
            'phishing': 'Phishing and fraudulent domains attempting to steal credentials',
            'adult': 'Adult content and pornography domains',
            'social-media': 'Social media platforms and related domains',
            'gambling': 'Online gambling and betting domains',
            'custom': 'Custom user-defined rules and exceptions'
        }
        
        # Get statistics for this category
        stats = await self.get_zone_statistics(rpz_zone=category)
        
        return {
            'name': category,
            'display_name': category.replace('-', ' ').title(),
            'description': category_descriptions.get(category, 'Custom category'),
            'total_rules': stats.get('total_rules', 0),
            'active_rules': stats.get('active_rules', 0),
            'rules_by_action': stats.get('rules_by_action', {}),
            'rules_by_source': stats.get('rules_by_source', {})
        }
    
    async def get_all_categories_info(self) -> List[Dict[str, Any]]:
        """Get information about all available categories"""
        categories = await self.get_available_categories()
        category_info = []
        
        for category in categories:
            info = await self.get_category_info(category)
            category_info.append(info)
        
        return category_info
    
    async def enable_category(self, category: str) -> Tuple[int, List[str]]:
        """Enable all rules in a category"""
        logger.info(f"Enabling category: {category}")
        
        if category not in await self.get_available_categories():
            raise ValidationException(f"Invalid category: {category}")
        
        # Get all inactive rules in this category
        rules = await self.get_rules(
            rpz_zone=category,
            active_only=False
        )
        
        inactive_rules = [rule for rule in rules if not rule.is_active]
        updated_count = 0
        errors = []
        
        for rule in inactive_rules:
            try:
                await self.update_rule(rule.id, {'is_active': True})
                updated_count += 1
            except Exception as e:
                error_msg = f"Failed to enable rule {rule.id} ({rule.domain}): {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        logger.info(f"Enabled {updated_count} rules in category {category}")
        return updated_count, errors
    
    async def disable_category(self, category: str) -> Tuple[int, List[str]]:
        """Disable all rules in a category"""
        logger.info(f"Disabling category: {category}")
        
        if category not in await self.get_available_categories():
            raise ValidationException(f"Invalid category: {category}")
        
        # Get all active rules in this category
        rules = await self.get_rules(
            rpz_zone=category,
            active_only=True
        )
        
        updated_count = 0
        errors = []
        
        for rule in rules:
            try:
                await self.update_rule(rule.id, {'is_active': False})
                updated_count += 1
            except Exception as e:
                error_msg = f"Failed to disable rule {rule.id} ({rule.domain}): {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        logger.info(f"Disabled {updated_count} rules in category {category}")
        return updated_count, errors
    
    async def get_category_status(self, category: str) -> Dict[str, Any]:
        """Get the current status of a category (enabled/disabled/mixed)"""
        if category not in await self.get_available_categories():
            raise ValidationException(f"Invalid category: {category}")
        
        # Get rule counts
        total_rules = await self.count_rules(rpz_zone=category, active_only=False)
        active_rules = await self.count_rules(rpz_zone=category, active_only=True)
        inactive_rules = total_rules - active_rules
        
        # Determine status
        if total_rules == 0:
            status = 'empty'
        elif active_rules == total_rules:
            status = 'enabled'
        elif active_rules == 0:
            status = 'disabled'
        else:
            status = 'mixed'
        
        return {
            'category': category,
            'status': status,
            'total_rules': total_rules,
            'active_rules': active_rules,
            'inactive_rules': inactive_rules,
            'enabled_percentage': round((active_rules / total_rules * 100) if total_rules > 0 else 0, 1)
        }
    
    async def bulk_categorize_rules(self, rule_ids: List[int], new_category: str) -> Tuple[int, int, List[str]]:
        """Move multiple rules to a different category"""
        logger.info(f"Bulk categorizing {len(rule_ids)} rules to category: {new_category}")
        
        if new_category not in await self.get_available_categories():
            raise ValidationException(f"Invalid category: {new_category}")
        
        updated_count = 0
        error_count = 0
        errors = []
        
        for rule_id in rule_ids:
            try:
                result = await self.update_rule(rule_id, {'rpz_zone': new_category})
                if result:
                    updated_count += 1
                else:
                    error_count += 1
                    errors.append(f"Rule {rule_id}: Not found")
            except Exception as e:
                error_count += 1
                error_msg = f"Rule {rule_id}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Failed to categorize rule in bulk operation: {error_msg}")
        
        logger.info(f"Bulk categorization completed: {updated_count} updated, {error_count} errors")
        return updated_count, error_count, errors
    
    async def get_rules_by_category(self, category: str, 
                                   skip: int = 0, 
                                   limit: int = 100,
                                   active_only: bool = True,
                                   action: Optional[str] = None,
                                   search: Optional[str] = None) -> List[RPZRule]:
        """Get rules filtered by category with additional filters"""
        return await self.get_rules(
            skip=skip,
            limit=limit,
            rpz_zone=category,
            action=action,
            active_only=active_only,
            search=search
        )
    
    async def count_rules_by_category(self, category: str,
                                     active_only: bool = True,
                                     action: Optional[str] = None,
                                     search: Optional[str] = None) -> int:
        """Count rules in a specific category with filters"""
        return await self.count_rules(
            rpz_zone=category,
            action=action,
            active_only=active_only,
            search=search
        )
    
    # Enhanced Statistics and Reporting Methods
    
    async def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive RPZ statistics across all categories"""
        logger.info("Generating comprehensive RPZ statistics")
        
        # Get overall statistics
        overall_stats = await self.get_zone_statistics()
        
        # Get category-specific statistics
        categories = await self.get_available_categories()
        category_stats = []
        
        for category in categories:
            category_info = await self.get_category_info(category)
            category_stats.append(category_info)
        
        # Get recent activity (rules created in last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        if self.is_async:
            recent_query = select(func.count(RPZRule.id)).filter(
                RPZRule.created_at >= thirty_days_ago
            )
            recent_result = await self.db.execute(recent_query)
            recent_rules = recent_result.scalar()
        else:
            recent_rules = self.db.query(func.count(RPZRule.id)).filter(
                RPZRule.created_at >= thirty_days_ago
            ).scalar()
        
        # Get top blocked domains (most common domains in rules)
        if self.is_async:
            top_domains_query = select(
                RPZRule.domain, 
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.is_active == True
            ).group_by(RPZRule.domain).order_by(
                desc(func.count(RPZRule.id))
            ).limit(10)
            top_domains_result = await self.db.execute(top_domains_query)
            top_domains = [
                {'domain': row[0], 'count': row[1]} 
                for row in top_domains_result.fetchall()
            ]
        else:
            top_domains_result = self.db.query(
                RPZRule.domain, 
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.is_active == True
            ).group_by(RPZRule.domain).order_by(
                desc(func.count(RPZRule.id))
            ).limit(10).all()
            top_domains = [
                {'domain': row[0], 'count': row[1]} 
                for row in top_domains_result
            ]
        
        return {
            'overall': overall_stats,
            'categories': category_stats,
            'recent_activity': {
                'rules_added_last_30_days': recent_rules
            },
            'top_domains': top_domains,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def get_activity_report(self, days: int = 30) -> Dict[str, Any]:
        """Get activity report for the specified number of days"""
        logger.info(f"Generating activity report for last {days} days")
        
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        
        if self.is_async:
            # Rules created
            created_query = select(func.count(RPZRule.id)).filter(
                RPZRule.created_at >= start_date
            )
            created_result = await self.db.execute(created_query)
            rules_created = created_result.scalar()
            
            # Rules updated
            updated_query = select(func.count(RPZRule.id)).filter(
                RPZRule.updated_at >= start_date,
                RPZRule.created_at < start_date
            )
            updated_result = await self.db.execute(updated_query)
            rules_updated = updated_result.scalar()
            
            # Daily activity breakdown
            daily_query = select(
                func.date(RPZRule.created_at).label('date'),
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.created_at >= start_date
            ).group_by(
                func.date(RPZRule.created_at)
            ).order_by(
                func.date(RPZRule.created_at)
            )
            daily_result = await self.db.execute(daily_query)
            daily_activity = [
                {'date': str(row[0]), 'rules_created': row[1]}
                for row in daily_result.fetchall()
            ]
            
            # Activity by category
            category_query = select(
                RPZRule.rpz_zone,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.created_at >= start_date
            ).group_by(RPZRule.rpz_zone)
            category_result = await self.db.execute(category_query)
            activity_by_category = dict(category_result.fetchall())
            
        else:
            # Rules created
            rules_created = self.db.query(func.count(RPZRule.id)).filter(
                RPZRule.created_at >= start_date
            ).scalar()
            
            # Rules updated
            rules_updated = self.db.query(func.count(RPZRule.id)).filter(
                RPZRule.updated_at >= start_date,
                RPZRule.created_at < start_date
            ).scalar()
            
            # Daily activity breakdown
            daily_result = self.db.query(
                func.date(RPZRule.created_at).label('date'),
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.created_at >= start_date
            ).group_by(
                func.date(RPZRule.created_at)
            ).order_by(
                func.date(RPZRule.created_at)
            ).all()
            daily_activity = [
                {'date': str(row[0]), 'rules_created': row[1]}
                for row in daily_result
            ]
            
            # Activity by category
            category_result = self.db.query(
                RPZRule.rpz_zone,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.created_at >= start_date
            ).group_by(RPZRule.rpz_zone).all()
            activity_by_category = dict(category_result)
        
        return {
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat()
            },
            'summary': {
                'rules_created': rules_created,
                'rules_updated': rules_updated,
                'total_activity': rules_created + rules_updated
            },
            'daily_activity': daily_activity,
            'activity_by_category': activity_by_category,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def get_effectiveness_report(self) -> Dict[str, Any]:
        """Get effectiveness report showing rule distribution and coverage"""
        logger.info("Generating effectiveness report")
        
        # Get basic statistics
        total_rules = await self.count_rules(active_only=False)
        active_rules = await self.count_rules(active_only=True)
        
        # Get rules by action distribution
        if self.is_async:
            action_query = select(
                RPZRule.action,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.is_active == True
            ).group_by(RPZRule.action)
            action_result = await self.db.execute(action_query)
            action_distribution = dict(action_result.fetchall())
        else:
            action_result = self.db.query(
                RPZRule.action,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.is_active == True
            ).group_by(RPZRule.action).all()
            action_distribution = dict(action_result)
        
        # Calculate effectiveness metrics
        block_rules = action_distribution.get('block', 0)
        redirect_rules = action_distribution.get('redirect', 0)
        passthru_rules = action_distribution.get('passthru', 0)
        
        # Get source distribution
        if self.is_async:
            source_query = select(
                RPZRule.source,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.is_active == True
            ).group_by(RPZRule.source)
            source_result = await self.db.execute(source_query)
            source_distribution = dict(source_result.fetchall())
        else:
            source_result = self.db.query(
                RPZRule.source,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.is_active == True
            ).group_by(RPZRule.source).all()
            source_distribution = dict(source_result)
        
        # Get category coverage
        categories = await self.get_available_categories()
        category_coverage = {}
        
        for category in categories:
            category_rules = await self.count_rules(rpz_zone=category, active_only=True)
            category_coverage[category] = {
                'active_rules': category_rules,
                'percentage': round((category_rules / active_rules * 100) if active_rules > 0 else 0, 1)
            }
        
        return {
            'summary': {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'inactive_rules': total_rules - active_rules,
                'activation_rate': round((active_rules / total_rules * 100) if total_rules > 0 else 0, 1)
            },
            'action_distribution': action_distribution,
            'source_distribution': source_distribution,
            'category_coverage': category_coverage,
            'effectiveness_metrics': {
                'blocking_rules': block_rules,
                'redirect_rules': redirect_rules,
                'passthrough_rules': passthru_rules,
                'protection_ratio': round((block_rules / active_rules * 100) if active_rules > 0 else 0, 1)
            },
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def get_trend_analysis(self, days: int = 90) -> Dict[str, Any]:
        """Get trend analysis for rule creation and management over time"""
        logger.info(f"Generating trend analysis for last {days} days")
        
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Weekly trend data
        if self.is_async:
            weekly_query = select(
                func.date_trunc('week', RPZRule.created_at).label('week'),
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.created_at >= start_date
            ).group_by(
                func.date_trunc('week', RPZRule.created_at)
            ).order_by(
                func.date_trunc('week', RPZRule.created_at)
            )
            weekly_result = await self.db.execute(weekly_query)
            weekly_trends = [
                {'week': str(row[0]), 'rules_created': row[1]}
                for row in weekly_result.fetchall()
            ]
            
            # Category trends
            category_trend_query = select(
                func.date_trunc('week', RPZRule.created_at).label('week'),
                RPZRule.rpz_zone,
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.created_at >= start_date
            ).group_by(
                func.date_trunc('week', RPZRule.created_at),
                RPZRule.rpz_zone
            ).order_by(
                func.date_trunc('week', RPZRule.created_at)
            )
            category_trend_result = await self.db.execute(category_trend_query)
            category_trends = {}
            
            for row in category_trend_result.fetchall():
                week = str(row[0])
                category = row[1]
                count = row[2]
                
                if week not in category_trends:
                    category_trends[week] = {}
                category_trends[week][category] = count
                
        else:
            # For synchronous database, we'll use a simpler approach
            # Get weekly data by grouping by week number
            weekly_result = self.db.query(
                func.extract('week', RPZRule.created_at).label('week'),
                func.extract('year', RPZRule.created_at).label('year'),
                func.count(RPZRule.id).label('count')
            ).filter(
                RPZRule.created_at >= start_date
            ).group_by(
                func.extract('week', RPZRule.created_at),
                func.extract('year', RPZRule.created_at)
            ).order_by(
                func.extract('year', RPZRule.created_at),
                func.extract('week', RPZRule.created_at)
            ).all()
            
            weekly_trends = [
                {'week': f"{int(row[1])}-W{int(row[0]):02d}", 'rules_created': row[2]}
                for row in weekly_result
            ]
            
            # Simplified category trends
            category_trends = {}
        
        # Calculate growth rate
        if len(weekly_trends) >= 2:
            recent_avg = sum(week['rules_created'] for week in weekly_trends[-4:]) / min(4, len(weekly_trends))
            older_avg = sum(week['rules_created'] for week in weekly_trends[:4]) / min(4, len(weekly_trends))
            growth_rate = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        else:
            growth_rate = 0
        
        return {
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat()
            },
            'weekly_trends': weekly_trends,
            'category_trends': category_trends,
            'growth_metrics': {
                'growth_rate_percentage': round(growth_rate, 1),
                'trend_direction': 'increasing' if growth_rate > 5 else 'decreasing' if growth_rate < -5 else 'stable'
            },
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def get_security_impact_report(self) -> Dict[str, Any]:
        """Get security impact report showing protection coverage"""
        logger.info("Generating security impact report")
        
        # Get active rules by security category
        security_categories = ['malware', 'phishing', 'adult']
        security_coverage = {}
        
        for category in security_categories:
            rules_count = await self.count_rules(rpz_zone=category, active_only=True)
            block_count = await self.count_rules(
                rpz_zone=category, 
                action='block', 
                active_only=True
            )
            redirect_count = await self.count_rules(
                rpz_zone=category, 
                action='redirect', 
                active_only=True
            )
            
            security_coverage[category] = {
                'total_rules': rules_count,
                'block_rules': block_count,
                'redirect_rules': redirect_count,
                'protection_level': 'high' if rules_count > 1000 else 'medium' if rules_count > 100 else 'low'
            }
        
        # Calculate overall security score
        total_security_rules = sum(cat['total_rules'] for cat in security_coverage.values())
        total_block_rules = sum(cat['block_rules'] for cat in security_coverage.values())
        
        # Get threat feed statistics
        if self.is_async:
            threat_feed_query = select(
                RPZRule.source,
                func.count(RPZRule.id).label('count')
            ).filter(
                and_(
                    RPZRule.is_active == True,
                    RPZRule.source != 'manual'
                )
            ).group_by(RPZRule.source)
            threat_feed_result = await self.db.execute(threat_feed_query)
            threat_feed_coverage = dict(threat_feed_result.fetchall())
        else:
            threat_feed_result = self.db.query(
                RPZRule.source,
                func.count(RPZRule.id).label('count')
            ).filter(
                and_(
                    RPZRule.is_active == True,
                    RPZRule.source != 'manual'
                )
            ).group_by(RPZRule.source).all()
            threat_feed_coverage = dict(threat_feed_result)
        
        # Calculate security score (0-100)
        security_score = min(100, (total_security_rules / 10000) * 100)  # Assume 10k rules = 100% score
        
        return {
            'security_coverage': security_coverage,
            'threat_feed_coverage': threat_feed_coverage,
            'overall_metrics': {
                'total_security_rules': total_security_rules,
                'total_block_rules': total_block_rules,
                'security_score': round(security_score, 1),
                'protection_level': 'excellent' if security_score >= 80 else 'good' if security_score >= 60 else 'basic'
            },
            'recommendations': self._generate_security_recommendations(security_coverage, security_score),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_security_recommendations(self, coverage: Dict[str, Any], score: float) -> List[str]:
        """Generate security recommendations based on current coverage"""
        recommendations = []
        
        if score < 60:
            recommendations.append("Consider adding more threat intelligence feeds to improve protection coverage")
        
        if coverage.get('malware', {}).get('total_rules', 0) < 1000:
            recommendations.append("Increase malware protection by adding more malware domain feeds")
        
        if coverage.get('phishing', {}).get('total_rules', 0) < 500:
            recommendations.append("Enhance phishing protection with additional phishing domain lists")
        
        # Check for balanced protection
        total_rules = sum(cat.get('total_rules', 0) for cat in coverage.values())
        if total_rules > 0:
            malware_ratio = coverage.get('malware', {}).get('total_rules', 0) / total_rules
            if malware_ratio < 0.4:
                recommendations.append("Consider increasing malware protection rules for better balance")
        
        if not recommendations:
            recommendations.append("Security coverage looks good. Continue monitoring and updating threat feeds regularly")
        
        return recommendations
    
    async def export_statistics_report(self, report_type: str = 'comprehensive', 
                                     format: str = 'json') -> Dict[str, Any]:
        """Export statistics report in specified format"""
        logger.info(f"Exporting {report_type} statistics report in {format} format")
        
        if report_type == 'comprehensive':
            data = await self.get_comprehensive_statistics()
        elif report_type == 'activity':
            data = await self.get_activity_report()
        elif report_type == 'effectiveness':
            data = await self.get_effectiveness_report()
        elif report_type == 'trends':
            data = await self.get_trend_analysis()
        elif report_type == 'security':
            data = await self.get_security_impact_report()
        else:
            raise ValidationException(f"Invalid report type: {report_type}")
        
        # Add export metadata
        export_data = {
            'report_type': report_type,
            'export_format': format,
            'exported_at': datetime.utcnow().isoformat(),
            'data': data
        }
        
        return export_data