"""
Forwarder service with authentication integration and health monitoring
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc
import asyncio
import socket
import dns.resolver
import dns.exception
import ipaddress

from .base_service import BaseService
from ..models.dns import Forwarder, ForwarderHealth
from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ForwarderService(BaseService[Forwarder]):
    """Forwarder service with authentication, audit logging, and health monitoring"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, Forwarder)
    
    async def create_forwarder(self, forwarder_data: Dict[str, Any]) -> Forwarder:
        """Create a new DNS forwarder with user tracking and validation"""
        logger.info(f"Creating forwarder: {forwarder_data.get('name')}")
        
        # Validate forwarder data
        validation_result = await self.validate_forwarder_data(forwarder_data)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid forwarder data: {', '.join(validation_result['errors'])}")
        
        # Set default values
        forwarder_data.setdefault('is_active', True)
        forwarder_data.setdefault('health_check_enabled', True)
        
        # Validate and normalize server configurations
        if 'servers' in forwarder_data:
            forwarder_data['servers'] = await self.normalize_server_configs(forwarder_data['servers'])
        
        # Validate and normalize domain list
        if 'domains' in forwarder_data:
            forwarder_data['domains'] = await self.normalize_domain_list(forwarder_data['domains'])
        
        # Create the forwarder
        forwarder = await self.create(forwarder_data, track_action=True)
        
        # Perform initial health check if enabled
        if forwarder.health_check_enabled:
            await self.perform_health_check(forwarder.id)
        
        logger.info(f"Created forwarder {forwarder.name} with ID {forwarder.id}")
        return forwarder
    
    async def update_forwarder(self, forwarder_id: int, forwarder_data: Dict[str, Any]) -> Optional[Forwarder]:
        """Update a DNS forwarder with user tracking and validation"""
        logger.info(f"Updating forwarder ID: {forwarder_id}")
        
        # Get existing forwarder for validation
        existing_forwarder = await self.get_by_id(forwarder_id)
        if not existing_forwarder:
            logger.warning(f"Forwarder {forwarder_id} not found for update")
            return None
        
        # Validate forwarder data (partial validation for updates)
        validation_result = await self.validate_forwarder_data(forwarder_data, forwarder_id)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid forwarder data: {', '.join(validation_result['errors'])}")
        
        # Normalize server configurations if provided
        if 'servers' in forwarder_data:
            forwarder_data['servers'] = await self.normalize_server_configs(forwarder_data['servers'])
        
        # Normalize domain list if provided
        if 'domains' in forwarder_data:
            forwarder_data['domains'] = await self.normalize_domain_list(forwarder_data['domains'])
        
        # Update the forwarder
        forwarder = await self.update(forwarder_id, forwarder_data, track_action=True)
        
        if forwarder:
            # Perform health check if servers or health check settings changed
            if ('servers' in forwarder_data or 'health_check_enabled' in forwarder_data) and forwarder.health_check_enabled:
                await self.perform_health_check(forwarder.id)
            
            logger.info(f"Updated forwarder {forwarder.name}")
        
        return forwarder
    
    async def delete_forwarder(self, forwarder_id: int) -> bool:
        """Delete a DNS forwarder with user tracking"""
        logger.info(f"Deleting forwarder ID: {forwarder_id}")
        
        # Get forwarder info before deletion for logging
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            logger.warning(f"Forwarder {forwarder_id} not found for deletion")
            return False
        
        forwarder_name = forwarder.name
        success = await self.delete(forwarder_id, track_action=True)
        
        if success:
            logger.info(f"Deleted forwarder {forwarder_name}")
        
        return success
    
    async def get_forwarder(self, forwarder_id: int) -> Optional[Forwarder]:
        """Get a forwarder by ID"""
        return await self.get_by_id(forwarder_id)
    
    async def get_forwarders(self, skip: int = 0, limit: int = 100,
                           forwarder_type: Optional[str] = None,
                           active_only: bool = True,
                           search: Optional[str] = None,
                           sort_by: Optional[str] = None,
                           sort_order: str = "asc") -> Dict[str, Any]:
        """Get forwarders with enhanced filtering and pagination"""
        
        # Build the base query
        if self.is_async:
            query = select(Forwarder)
            count_query = select(func.count(Forwarder.id))
        else:
            query = self.db.query(Forwarder)
            count_query = self.db.query(func.count(Forwarder.id))
        
        # Apply filters
        conditions = []
        
        if forwarder_type:
            conditions.append(Forwarder.forwarder_type == forwarder_type)
        
        if active_only:
            conditions.append(Forwarder.is_active == True)
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            search_conditions = [
                Forwarder.name.ilike(search_term)
            ]
            # Add description search if the field exists
            if hasattr(Forwarder, 'description') and Forwarder.description is not None:
                search_conditions.append(Forwarder.description.ilike(search_term))
            
            conditions.append(or_(*search_conditions))
        
        # Apply all conditions
        if conditions:
            if self.is_async:
                query = query.filter(and_(*conditions))
                count_query = count_query.filter(and_(*conditions))
            else:
                query = query.filter(and_(*conditions))
                count_query = count_query.filter(and_(*conditions))
        
        # Apply sorting
        if sort_by and hasattr(Forwarder, sort_by):
            sort_column = getattr(Forwarder, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sorting by name
            query = query.order_by(asc(Forwarder.name))
        
        # Get total count
        if self.is_async:
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
        else:
            total = count_query.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        if self.is_async:
            result = await self.db.execute(query)
            forwarders = result.scalars().all()
        else:
            forwarders = query.all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "items": forwarders,
            "total": total,
            "page": current_page,
            "per_page": limit,
            "pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1
        }
    
    async def get_forwarders_by_user(self, user_id: int, created_only: bool = False) -> List[Forwarder]:
        """Get forwarders created or updated by a specific user"""
        return await self.get_by_user(user_id, created_only=created_only)
    
    async def get_forwarder_with_health(self, forwarder_id: int) -> Optional[Dict[str, Any]]:
        """Get a forwarder with its health check results"""
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            return None
        
        # Get recent health checks for this forwarder
        if self.is_async:
            result = await self.db.execute(
                select(ForwarderHealth)
                .filter(ForwarderHealth.forwarder_id == forwarder_id)
                .order_by(desc(ForwarderHealth.checked_at))
                .limit(10)
            )
            health_checks = result.scalars().all()
        else:
            health_checks = self.db.query(ForwarderHealth).filter(
                ForwarderHealth.forwarder_id == forwarder_id
            ).order_by(desc(ForwarderHealth.checked_at)).limit(10).all()
        
        # Get current health status
        current_health = await self.get_current_health_status(forwarder_id)
        
        return {
            "forwarder": forwarder,
            "health_checks": health_checks,
            "current_health": current_health,
            "health_check_count": len(health_checks)
        }
    
    async def get_current_health_status(self, forwarder_id: int) -> Dict[str, Any]:
        """Get the current health status for a forwarder"""
        if self.is_async:
            # Get the most recent health check for each server
            result = await self.db.execute(
                select(ForwarderHealth)
                .filter(ForwarderHealth.forwarder_id == forwarder_id)
                .order_by(desc(ForwarderHealth.checked_at))
            )
            all_checks = result.scalars().all()
        else:
            all_checks = self.db.query(ForwarderHealth).filter(
                ForwarderHealth.forwarder_id == forwarder_id
            ).order_by(desc(ForwarderHealth.checked_at)).all()
        
        if not all_checks:
            return {
                "overall_status": "unknown",
                "healthy_servers": 0,
                "total_servers": 0,
                "last_checked": None,
                "server_statuses": {}
            }
        
        # Group by server IP and get the most recent status for each
        server_statuses = {}
        for check in all_checks:
            if check.server_ip not in server_statuses:
                server_statuses[check.server_ip] = {
                    "status": check.status,
                    "response_time": check.response_time,
                    "error_message": check.error_message,
                    "checked_at": check.checked_at
                }
        
        # Calculate overall status
        healthy_count = sum(1 for status in server_statuses.values() if status["status"] == "healthy")
        total_count = len(server_statuses)
        
        if healthy_count == 0:
            overall_status = "unhealthy"
        elif healthy_count == total_count:
            overall_status = "healthy"
        else:
            overall_status = "degraded"
        
        # Get the most recent check time
        last_checked = max(check.checked_at for check in all_checks) if all_checks else None
        
        return {
            "overall_status": overall_status,
            "healthy_servers": healthy_count,
            "total_servers": total_count,
            "last_checked": last_checked,
            "server_statuses": server_statuses
        }
    
    async def perform_health_check(self, forwarder_id: int) -> Dict[str, Any]:
        """Perform health check for all servers in a forwarder"""
        logger.info(f"Performing health check for forwarder ID: {forwarder_id}")
        
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            logger.error(f"Forwarder {forwarder_id} not found for health check")
            return {"error": "Forwarder not found"}
        
        if not forwarder.health_check_enabled:
            logger.info(f"Health check disabled for forwarder {forwarder.name}")
            return {"message": "Health check disabled"}
        
        results = []
        
        # Test each server
        for server_config in forwarder.servers:
            server_ip = server_config.get('ip')
            server_port = server_config.get('port', 53)
            
            if not server_ip:
                continue
            
            result = await self.test_dns_server(server_ip, server_port, forwarder.domains[0] if forwarder.domains else 'google.com')
            
            # Store health check result
            health_data = {
                'forwarder_id': forwarder_id,
                'server_ip': server_ip,
                'status': result['status'],
                'response_time': result.get('response_time'),
                'error_message': result.get('error_message'),
                'checked_at': datetime.utcnow()
            }
            
            # Create health check record
            health_check = ForwarderHealth(**health_data)
            self.db.add(health_check)
            
            results.append({
                'server_ip': server_ip,
                'server_port': server_port,
                **result
            })
        
        # Commit health check results
        if self.is_async:
            await self.db.commit()
        else:
            self.db.commit()
        
        logger.info(f"Completed health check for forwarder {forwarder.name}: {len(results)} servers tested")
        
        return {
            "forwarder_id": forwarder_id,
            "forwarder_name": forwarder.name,
            "results": results,
            "checked_at": datetime.utcnow()
        }
    
    async def test_dns_server(self, server_ip: str, server_port: int = 53, test_domain: str = 'google.com') -> Dict[str, Any]:
        """Test a single DNS server for connectivity and response"""
        start_time = datetime.utcnow()
        
        try:
            # Validate IP address
            try:
                ipaddress.ip_address(server_ip)
            except ValueError:
                return {
                    "status": "error",
                    "error_message": f"Invalid IP address: {server_ip}"
                }
            
            # Create DNS resolver with custom nameserver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [server_ip]
            resolver.port = server_port
            resolver.timeout = 5.0  # 5 second timeout
            resolver.lifetime = 10.0  # 10 second total timeout
            
            # Perform DNS query
            try:
                response = resolver.resolve(test_domain, 'A')
                end_time = datetime.utcnow()
                response_time = int((end_time - start_time).total_seconds() * 1000)  # milliseconds
                
                if response:
                    return {
                        "status": "healthy",
                        "response_time": response_time,
                        "resolved_ips": [str(rdata) for rdata in response]
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error_message": "No response received"
                    }
                    
            except dns.resolver.NXDOMAIN:
                # Domain doesn't exist - this is actually a valid response
                end_time = datetime.utcnow()
                response_time = int((end_time - start_time).total_seconds() * 1000)
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "message": "NXDOMAIN response (server is responding)"
                }
                
            except dns.resolver.NoAnswer:
                # No answer for this record type - server is responding
                end_time = datetime.utcnow()
                response_time = int((end_time - start_time).total_seconds() * 1000)
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "message": "No answer for query (server is responding)"
                }
                
            except dns.resolver.Timeout:
                return {
                    "status": "timeout",
                    "error_message": f"DNS query timeout after 5 seconds"
                }
                
            except dns.exception.DNSException as e:
                return {
                    "status": "error",
                    "error_message": f"DNS error: {str(e)}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Unexpected error: {str(e)}"
            }
    
    async def test_forwarder(self, forwarder: Forwarder, test_domains: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Test a forwarder by querying its servers with test domains"""
        logger.info(f"Testing forwarder {forwarder.name}")
        
        if not test_domains:
            # Use the forwarder's configured domains or default test domains
            test_domains = forwarder.domains[:3] if forwarder.domains else ['google.com', 'cloudflare.com', 'example.com']
        
        results = []
        
        for server_config in forwarder.servers:
            server_ip = server_config.get('ip')
            server_port = server_config.get('port', 53)
            
            if not server_ip:
                continue
            
            server_results = []
            
            for domain in test_domains:
                result = await self.test_dns_server(server_ip, server_port, domain)
                server_results.append({
                    'domain': domain,
                    **result
                })
            
            # Calculate server summary
            successful_queries = sum(1 for r in server_results if r['status'] == 'healthy')
            avg_response_time = None
            if successful_queries > 0:
                response_times = [r['response_time'] for r in server_results if r.get('response_time')]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
            
            results.append({
                'server_ip': server_ip,
                'server_port': server_port,
                'successful_queries': successful_queries,
                'total_queries': len(test_domains),
                'success_rate': (successful_queries / len(test_domains)) * 100,
                'avg_response_time': avg_response_time,
                'query_results': server_results
            })
        
        return results
    
    async def get_health_status(self, forwarder_id: int) -> Dict[str, Any]:
        """Get comprehensive health status for a forwarder"""
        return await self.get_current_health_status(forwarder_id)
    
    async def get_health_history(self, forwarder_id: int, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get health check history for a forwarder"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        if self.is_async:
            result = await self.db.execute(
                select(ForwarderHealth)
                .filter(
                    ForwarderHealth.forwarder_id == forwarder_id,
                    ForwarderHealth.checked_at >= since
                )
                .order_by(desc(ForwarderHealth.checked_at))
                .limit(limit)
            )
            health_checks = result.scalars().all()
        else:
            health_checks = self.db.query(ForwarderHealth).filter(
                ForwarderHealth.forwarder_id == forwarder_id,
                ForwarderHealth.checked_at >= since
            ).order_by(desc(ForwarderHealth.checked_at)).limit(limit).all()
        
        return [
            {
                'id': check.id,
                'server_ip': check.server_ip,
                'status': check.status,
                'response_time': check.response_time,
                'error_message': check.error_message,
                'checked_at': check.checked_at
            }
            for check in health_checks
        ]
    
    async def get_health_status_trends(self, forwarder_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get health status trends for a forwarder over time"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        if self.is_async:
            result = await self.db.execute(
                select(ForwarderHealth)
                .filter(
                    ForwarderHealth.forwarder_id == forwarder_id,
                    ForwarderHealth.checked_at >= since
                )
                .order_by(ForwarderHealth.checked_at)
            )
            health_checks = result.scalars().all()
        else:
            health_checks = self.db.query(ForwarderHealth).filter(
                ForwarderHealth.forwarder_id == forwarder_id,
                ForwarderHealth.checked_at >= since
            ).order_by(ForwarderHealth.checked_at).all()
        
        if not health_checks:
            return {
                "forwarder_id": forwarder_id,
                "period_hours": hours,
                "total_checks": 0,
                "status_distribution": {},
                "average_response_time": None,
                "uptime_percentage": 0.0,
                "status_changes": []
            }
        
        # Calculate status distribution
        status_counts = {}
        response_times = []
        status_changes = []
        last_status = None
        
        for check in health_checks:
            # Count status occurrences
            status_counts[check.status] = status_counts.get(check.status, 0) + 1
            
            # Collect response times for healthy checks
            if check.response_time is not None and check.status == 'healthy':
                response_times.append(check.response_time)
            
            # Track status changes
            if last_status is not None and last_status != check.status:
                status_changes.append({
                    "from_status": last_status,
                    "to_status": check.status,
                    "changed_at": check.checked_at,
                    "server_ip": check.server_ip
                })
            last_status = check.status
        
        # Calculate uptime percentage (healthy checks / total checks)
        healthy_checks = status_counts.get('healthy', 0)
        uptime_percentage = (healthy_checks / len(health_checks)) * 100 if health_checks else 0.0
        
        # Calculate average response time
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            "forwarder_id": forwarder_id,
            "period_hours": hours,
            "total_checks": len(health_checks),
            "status_distribution": status_counts,
            "average_response_time": avg_response_time,
            "uptime_percentage": uptime_percentage,
            "status_changes": status_changes[-10:],  # Last 10 status changes
            "period_start": since,
            "period_end": datetime.utcnow()
        }
    
    async def track_health_status_change(self, forwarder_id: int, old_status: str, new_status: str) -> None:
        """Track health status changes for alerting and monitoring"""
        if old_status == new_status:
            return
        
        logger.info(f"Health status change for forwarder {forwarder_id}: {old_status} -> {new_status}")
        
        # Track the status change in user actions for audit trail
        forwarder = await self.get_by_id(forwarder_id)
        if forwarder:
            track_user_action(
                action="forwarder_health_status_change",
                resource_type="forwarder",
                resource_id=str(forwarder_id),
                details=f"Health status changed from {old_status} to {new_status} for forwarder {forwarder.name}",
                db=self.db
            )
    
    async def get_all_forwarders_health_tracking(self) -> Dict[str, Any]:
        """Get comprehensive health tracking for all forwarders"""
        result = await self.get_forwarders(limit=1000)
        forwarders = result["items"]
        
        tracking_data = {
            "total_forwarders": len(forwarders),
            "health_enabled_count": 0,
            "status_summary": {
                "healthy": 0,
                "unhealthy": 0,
                "degraded": 0,
                "unknown": 0
            },
            "forwarder_tracking": [],
            "last_updated": datetime.utcnow()
        }
        
        for forwarder in forwarders:
            if forwarder.health_check_enabled:
                tracking_data["health_enabled_count"] += 1
                
                # Get current health status
                health_status = await self.get_current_health_status(forwarder.id)
                status = health_status.get("overall_status", "unknown")
                
                tracking_data["status_summary"][status] = tracking_data["status_summary"].get(status, 0) + 1
                
                # Get health trends for the last 24 hours
                trends = await self.get_health_status_trends(forwarder.id, hours=24)
                
                tracking_data["forwarder_tracking"].append({
                    "forwarder_id": forwarder.id,
                    "forwarder_name": forwarder.name,
                    "forwarder_type": forwarder.forwarder_type,
                    "current_status": status,
                    "healthy_servers": health_status.get("healthy_servers", 0),
                    "total_servers": health_status.get("total_servers", 0),
                    "last_checked": health_status.get("last_checked"),
                    "uptime_24h": trends.get("uptime_percentage", 0.0),
                    "avg_response_time": trends.get("average_response_time"),
                    "status_changes_24h": len(trends.get("status_changes", []))
                })
        
        return tracking_data
    
    async def get_forwarder_statistics(self, forwarder_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive statistics for a specific forwarder"""
        logger.info(f"Getting statistics for forwarder ID: {forwarder_id}")
        
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            logger.warning(f"Forwarder {forwarder_id} not found for statistics")
            return {}
        
        # Get basic forwarder info
        stats = {
            "forwarder_id": forwarder_id,
            "forwarder_name": forwarder.name,
            "forwarder_type": forwarder.forwarder_type,
            "is_active": forwarder.is_active,
            "health_check_enabled": forwarder.health_check_enabled,
            "domains_count": len(forwarder.domains) if forwarder.domains else 0,
            "servers_count": len(forwarder.servers) if forwarder.servers else 0,
            "created_at": forwarder.created_at,
            "updated_at": forwarder.updated_at,
            "period_hours": hours,
            "generated_at": datetime.utcnow()
        }
        
        # Get domain list
        stats["domains"] = forwarder.domains if forwarder.domains else []
        
        # Get server configurations
        stats["servers"] = []
        if forwarder.servers:
            for server_config in forwarder.servers:
                stats["servers"].append({
                    "ip": server_config.get("ip"),
                    "port": server_config.get("port", 53),
                    "priority": server_config.get("priority", 1)
                })
        
        # Get health statistics if health checking is enabled
        if forwarder.health_check_enabled:
            health_status = await self.get_current_health_status(forwarder_id)
            health_trends = await self.get_health_status_trends(forwarder_id, hours)
            
            stats.update({
                "current_health_status": health_status.get("overall_status", "unknown"),
                "healthy_servers": health_status.get("healthy_servers", 0),
                "total_health_checks": health_trends.get("total_checks", 0),
                "uptime_percentage": health_trends.get("uptime_percentage", 0.0),
                "average_response_time": health_trends.get("average_response_time"),
                "status_distribution": health_trends.get("status_distribution", {}),
                "status_changes": len(health_trends.get("status_changes", [])),
                "last_health_check": health_status.get("last_checked"),
                "server_health_details": health_status.get("server_statuses", {})
            })
        else:
            stats.update({
                "current_health_status": "disabled",
                "healthy_servers": 0,
                "total_health_checks": 0,
                "uptime_percentage": 0.0,
                "average_response_time": None,
                "status_distribution": {},
                "status_changes": 0,
                "last_health_check": None,
                "server_health_details": {}
            })
        
        return stats
    
    async def get_forwarder_usage_statistics(self, forwarder_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get usage statistics for a forwarder (queries, performance, etc.)"""
        logger.info(f"Getting usage statistics for forwarder ID: {forwarder_id}")
        
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            return {}
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get health check data as a proxy for usage patterns
        if self.is_async:
            result = await self.db.execute(
                select(ForwarderHealth)
                .filter(
                    ForwarderHealth.forwarder_id == forwarder_id,
                    ForwarderHealth.checked_at >= since
                )
                .order_by(ForwarderHealth.checked_at)
            )
            health_checks = result.scalars().all()
        else:
            health_checks = self.db.query(ForwarderHealth).filter(
                ForwarderHealth.forwarder_id == forwarder_id,
                ForwarderHealth.checked_at >= since
            ).order_by(ForwarderHealth.checked_at).all()
        
        # Calculate usage statistics
        usage_stats = {
            "forwarder_id": forwarder_id,
            "forwarder_name": forwarder.name,
            "period_hours": hours,
            "period_start": since,
            "period_end": datetime.utcnow(),
            "total_health_checks": len(health_checks),
            "unique_servers_checked": len(set(check.server_ip for check in health_checks)),
            "successful_checks": sum(1 for check in health_checks if check.status == "healthy"),
            "failed_checks": sum(1 for check in health_checks if check.status in ["unhealthy", "error", "timeout"]),
            "average_response_time": None,
            "min_response_time": None,
            "max_response_time": None,
            "response_time_distribution": {
                "fast": 0,      # < 50ms
                "normal": 0,    # 50-200ms
                "slow": 0,      # 200-1000ms
                "very_slow": 0  # > 1000ms
            },
            "server_performance": {},
            "hourly_distribution": {}
        }
        
        # Calculate response time statistics
        response_times = [check.response_time for check in health_checks if check.response_time is not None]
        if response_times:
            usage_stats["average_response_time"] = sum(response_times) / len(response_times)
            usage_stats["min_response_time"] = min(response_times)
            usage_stats["max_response_time"] = max(response_times)
            
            # Categorize response times
            for rt in response_times:
                if rt < 50:
                    usage_stats["response_time_distribution"]["fast"] += 1
                elif rt < 200:
                    usage_stats["response_time_distribution"]["normal"] += 1
                elif rt < 1000:
                    usage_stats["response_time_distribution"]["slow"] += 1
                else:
                    usage_stats["response_time_distribution"]["very_slow"] += 1
        
        # Calculate per-server performance
        server_checks = {}
        for check in health_checks:
            if check.server_ip not in server_checks:
                server_checks[check.server_ip] = []
            server_checks[check.server_ip].append(check)
        
        for server_ip, checks in server_checks.items():
            successful = sum(1 for check in checks if check.status == "healthy")
            response_times = [check.response_time for check in checks if check.response_time is not None]
            
            usage_stats["server_performance"][server_ip] = {
                "total_checks": len(checks),
                "successful_checks": successful,
                "success_rate": (successful / len(checks)) * 100 if checks else 0,
                "average_response_time": sum(response_times) / len(response_times) if response_times else None,
                "last_check_status": checks[-1].status if checks else "unknown",
                "last_check_time": checks[-1].checked_at if checks else None
            }
        
        # Calculate hourly distribution
        for i in range(hours):
            hour_start = datetime.utcnow() - timedelta(hours=i+1)
            hour_end = datetime.utcnow() - timedelta(hours=i)
            hour_checks = [check for check in health_checks if hour_start <= check.checked_at < hour_end]
            
            hour_key = hour_start.strftime("%Y-%m-%d %H:00")
            usage_stats["hourly_distribution"][hour_key] = {
                "total_checks": len(hour_checks),
                "successful_checks": sum(1 for check in hour_checks if check.status == "healthy"),
                "average_response_time": None
            }
            
            hour_response_times = [check.response_time for check in hour_checks if check.response_time is not None]
            if hour_response_times:
                usage_stats["hourly_distribution"][hour_key]["average_response_time"] = sum(hour_response_times) / len(hour_response_times)
        
        return usage_stats
    
    async def get_all_forwarders_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive statistics for all forwarders"""
        logger.info(f"Getting statistics for all forwarders (last {hours} hours)")
        
        result = await self.get_forwarders(limit=1000)
        forwarders = result["items"]
        
        overall_stats = {
            "total_forwarders": len(forwarders),
            "active_forwarders": sum(1 for f in forwarders if f.is_active),
            "inactive_forwarders": sum(1 for f in forwarders if not f.is_active),
            "health_enabled_forwarders": sum(1 for f in forwarders if f.health_check_enabled),
            "forwarder_types": {},
            "overall_health_summary": {
                "healthy": 0,
                "unhealthy": 0,
                "degraded": 0,
                "unknown": 0,
                "disabled": 0
            },
            "total_domains": 0,
            "total_servers": 0,
            "period_hours": hours,
            "generated_at": datetime.utcnow(),
            "forwarder_details": []
        }
        
        # Count forwarder types
        for forwarder in forwarders:
            ftype = forwarder.forwarder_type
            overall_stats["forwarder_types"][ftype] = overall_stats["forwarder_types"].get(ftype, 0) + 1
            
            # Count domains and servers
            if forwarder.domains:
                overall_stats["total_domains"] += len(forwarder.domains)
            if forwarder.servers:
                overall_stats["total_servers"] += len(forwarder.servers)
        
        # Get detailed statistics for each forwarder
        for forwarder in forwarders:
            forwarder_stats = await self.get_forwarder_statistics(forwarder.id, hours)
            
            # Update overall health summary
            health_status = forwarder_stats.get("current_health_status", "unknown")
            overall_stats["overall_health_summary"][health_status] = overall_stats["overall_health_summary"].get(health_status, 0) + 1
            
            # Add to forwarder details
            overall_stats["forwarder_details"].append({
                "id": forwarder.id,
                "name": forwarder.name,
                "type": forwarder.forwarder_type,
                "is_active": forwarder.is_active,
                "health_enabled": forwarder.health_check_enabled,
                "domains_count": forwarder_stats.get("domains_count", 0),
                "servers_count": forwarder_stats.get("servers_count", 0),
                "current_health_status": health_status,
                "uptime_percentage": forwarder_stats.get("uptime_percentage", 0.0),
                "average_response_time": forwarder_stats.get("average_response_time"),
                "last_health_check": forwarder_stats.get("last_health_check")
            })
        
        return overall_stats
    
    async def get_forwarder_performance_metrics(self, forwarder_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get detailed performance metrics for a forwarder"""
        logger.info(f"Getting performance metrics for forwarder ID: {forwarder_id}")
        
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            return {}
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get health check data
        if self.is_async:
            result = await self.db.execute(
                select(ForwarderHealth)
                .filter(
                    ForwarderHealth.forwarder_id == forwarder_id,
                    ForwarderHealth.checked_at >= since
                )
                .order_by(ForwarderHealth.checked_at)
            )
            health_checks = result.scalars().all()
        else:
            health_checks = self.db.query(ForwarderHealth).filter(
                ForwarderHealth.forwarder_id == forwarder_id,
                ForwarderHealth.checked_at >= since
            ).order_by(ForwarderHealth.checked_at).all()
        
        metrics = {
            "forwarder_id": forwarder_id,
            "forwarder_name": forwarder.name,
            "period_hours": hours,
            "period_start": since,
            "period_end": datetime.utcnow(),
            "performance_summary": {
                "total_checks": len(health_checks),
                "availability_percentage": 0.0,
                "average_response_time": None,
                "response_time_percentiles": {
                    "p50": None,
                    "p90": None,
                    "p95": None,
                    "p99": None
                },
                "error_rate": 0.0,
                "timeout_rate": 0.0
            },
            "time_series_data": [],
            "server_metrics": {},
            "error_analysis": {
                "total_errors": 0,
                "error_types": {},
                "most_common_errors": []
            }
        }
        
        if not health_checks:
            return metrics
        
        # Calculate availability
        healthy_checks = sum(1 for check in health_checks if check.status == "healthy")
        metrics["performance_summary"]["availability_percentage"] = (healthy_checks / len(health_checks)) * 100
        
        # Calculate response time statistics
        response_times = [check.response_time for check in health_checks if check.response_time is not None and check.status == "healthy"]
        if response_times:
            response_times.sort()
            metrics["performance_summary"]["average_response_time"] = sum(response_times) / len(response_times)
            
            # Calculate percentiles
            def percentile(data, p):
                index = int(len(data) * p / 100)
                return data[min(index, len(data) - 1)]
            
            metrics["performance_summary"]["response_time_percentiles"] = {
                "p50": percentile(response_times, 50),
                "p90": percentile(response_times, 90),
                "p95": percentile(response_times, 95),
                "p99": percentile(response_times, 99)
            }
        
        # Calculate error rates
        error_checks = sum(1 for check in health_checks if check.status in ["error", "unhealthy"])
        timeout_checks = sum(1 for check in health_checks if check.status == "timeout")
        
        metrics["performance_summary"]["error_rate"] = (error_checks / len(health_checks)) * 100
        metrics["performance_summary"]["timeout_rate"] = (timeout_checks / len(health_checks)) * 100
        
        # Generate time series data (hourly aggregation)
        time_buckets = {}
        for check in health_checks:
            hour_key = check.checked_at.replace(minute=0, second=0, microsecond=0)
            if hour_key not in time_buckets:
                time_buckets[hour_key] = []
            time_buckets[hour_key].append(check)
        
        for hour, checks in sorted(time_buckets.items()):
            healthy = sum(1 for check in checks if check.status == "healthy")
            response_times = [check.response_time for check in checks if check.response_time is not None and check.status == "healthy"]
            
            metrics["time_series_data"].append({
                "timestamp": hour,
                "total_checks": len(checks),
                "healthy_checks": healthy,
                "availability": (healthy / len(checks)) * 100,
                "average_response_time": sum(response_times) / len(response_times) if response_times else None,
                "error_count": sum(1 for check in checks if check.status in ["error", "unhealthy"]),
                "timeout_count": sum(1 for check in checks if check.status == "timeout")
            })
        
        # Calculate per-server metrics
        server_data = {}
        for check in health_checks:
            if check.server_ip not in server_data:
                server_data[check.server_ip] = []
            server_data[check.server_ip].append(check)
        
        for server_ip, checks in server_data.items():
            healthy = sum(1 for check in checks if check.status == "healthy")
            response_times = [check.response_time for check in checks if check.response_time is not None and check.status == "healthy"]
            
            metrics["server_metrics"][server_ip] = {
                "total_checks": len(checks),
                "healthy_checks": healthy,
                "availability": (healthy / len(checks)) * 100,
                "average_response_time": sum(response_times) / len(response_times) if response_times else None,
                "error_count": sum(1 for check in checks if check.status in ["error", "unhealthy"]),
                "timeout_count": sum(1 for check in checks if check.status == "timeout"),
                "last_status": checks[-1].status,
                "last_check": checks[-1].checked_at
            }
        
        # Analyze errors
        error_checks = [check for check in health_checks if check.error_message]
        metrics["error_analysis"]["total_errors"] = len(error_checks)
        
        error_types = {}
        for check in error_checks:
            error_msg = check.error_message[:100]  # Truncate long error messages
            error_types[error_msg] = error_types.get(error_msg, 0) + 1
        
        metrics["error_analysis"]["error_types"] = error_types
        metrics["error_analysis"]["most_common_errors"] = sorted(
            error_types.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]  # Top 5 most common errors
        
        return metrics
    
    async def toggle_forwarder_status(self, forwarder_id: int) -> Optional[Forwarder]:
        """Toggle forwarder active status"""
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            return None
        
        new_status = not forwarder.is_active
        updated_forwarder = await self.update(forwarder_id, {"is_active": new_status}, track_action=True)
        
        if updated_forwarder:
            status_text = "activated" if new_status else "deactivated"
            logger.info(f"Forwarder {forwarder.name} {status_text}")
            
            # Track specific action
            track_user_action(
                action=f"forwarder_{'activate' if new_status else 'deactivate'}",
                resource_type="forwarder",
                resource_id=str(forwarder_id),
                details=f"Forwarder {forwarder.name} {status_text}",
                db=self.db
            )
        
        return updated_forwarder
    
    async def toggle_health_check(self, forwarder_id: int) -> Optional[Forwarder]:
        """Toggle forwarder health check enabled status"""
        forwarder = await self.get_by_id(forwarder_id)
        if not forwarder:
            return None
        
        new_status = not forwarder.health_check_enabled
        updated_forwarder = await self.update(forwarder_id, {"health_check_enabled": new_status}, track_action=True)
        
        if updated_forwarder:
            status_text = "enabled" if new_status else "disabled"
            logger.info(f"Health check {status_text} for forwarder {forwarder.name}")
            
            # Track specific action
            track_user_action(
                action=f"forwarder_health_check_{'enable' if new_status else 'disable'}",
                resource_type="forwarder",
                resource_id=str(forwarder_id),
                details=f"Health check {status_text} for forwarder {forwarder.name}",
                db=self.db
            )
        
        return updated_forwarder
    
    async def validate_forwarder_data(self, forwarder_data: Dict[str, Any], forwarder_id: Optional[int] = None) -> Dict[str, Any]:
        """Validate forwarder data and return validation results"""
        errors = []
        warnings = []
        
        # Required fields
        if not forwarder_data.get('name'):
            errors.append("Forwarder name is required")
        elif len(forwarder_data['name']) > 255:
            errors.append("Forwarder name must be 255 characters or less")
        
        if not forwarder_data.get('domains'):
            errors.append("At least one domain is required")
        elif not isinstance(forwarder_data['domains'], list) or len(forwarder_data['domains']) == 0:
            errors.append("Domains must be a non-empty list")
        
        if not forwarder_data.get('servers'):
            errors.append("At least one server is required")
        elif not isinstance(forwarder_data['servers'], list) or len(forwarder_data['servers']) == 0:
            errors.append("Servers must be a non-empty list")
        
        # Forwarder type validation
        valid_types = ['active_directory', 'intranet', 'public']
        if forwarder_data.get('forwarder_type') and forwarder_data['forwarder_type'] not in valid_types:
            errors.append(f"Forwarder type must be one of: {', '.join(valid_types)}")
        
        # Validate domains
        if forwarder_data.get('domains'):
            for domain in forwarder_data['domains']:
                if not isinstance(domain, str) or not domain.strip():
                    errors.append("All domains must be non-empty strings")
                    break
                # Basic domain validation
                if not self.is_valid_domain(domain.strip()):
                    errors.append(f"Invalid domain format: {domain}")
        
        # Validate servers
        if forwarder_data.get('servers'):
            for i, server in enumerate(forwarder_data['servers']):
                if not isinstance(server, dict):
                    errors.append(f"Server {i+1} must be an object with ip, port, and priority fields")
                    continue
                
                # Validate IP address
                if not server.get('ip'):
                    errors.append(f"Server {i+1} must have an IP address")
                else:
                    try:
                        ipaddress.ip_address(server['ip'])
                    except ValueError:
                        errors.append(f"Server {i+1} has invalid IP address: {server['ip']}")
                
                # Validate port
                port = server.get('port', 53)
                if not isinstance(port, int) or port < 1 or port > 65535:
                    errors.append(f"Server {i+1} port must be between 1 and 65535")
                
                # Validate priority
                priority = server.get('priority', 1)
                if not isinstance(priority, int) or priority < 1 or priority > 10:
                    errors.append(f"Server {i+1} priority must be between 1 and 10")
        
        # Check for duplicate forwarder name (exclude current forwarder if updating)
        if forwarder_data.get('name'):
            if self.is_async:
                query = select(func.count(Forwarder.id)).filter(Forwarder.name == forwarder_data['name'])
                if forwarder_id:
                    query = query.filter(Forwarder.id != forwarder_id)
                result = await self.db.execute(query)
                existing_count = result.scalar()
            else:
                query = self.db.query(func.count(Forwarder.id)).filter(Forwarder.name == forwarder_data['name'])
                if forwarder_id:
                    query = query.filter(Forwarder.id != forwarder_id)
                existing_count = query.scalar()
            
            if existing_count > 0:
                errors.append(f"Forwarder '{forwarder_data['name']}' already exists")
        
        # Warnings
        if forwarder_data.get('servers') and len(forwarder_data['servers']) == 1:
            warnings.append("Consider adding multiple servers for redundancy")
        
        if forwarder_data.get('forwarder_type') == 'active_directory' and len(forwarder_data.get('servers', [])) < 2:
            warnings.append("Active Directory forwarders should have multiple domain controllers for failover")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def normalize_server_configs(self, servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize and validate server configurations"""
        normalized_servers = []
        
        for server in servers:
            normalized_server = {
                'ip': server.get('ip', '').strip(),
                'port': int(server.get('port', 53)),
                'priority': int(server.get('priority', 1))
            }
            
            # Validate IP address
            try:
                ipaddress.ip_address(normalized_server['ip'])
                normalized_servers.append(normalized_server)
            except ValueError:
                logger.warning(f"Skipping invalid IP address: {normalized_server['ip']}")
                continue
        
        # Sort by priority (lower number = higher priority)
        normalized_servers.sort(key=lambda x: x['priority'])
        
        return normalized_servers
    
    async def normalize_domain_list(self, domains: List[str]) -> List[str]:
        """Normalize and validate domain list"""
        normalized_domains = []
        
        for domain in domains:
            domain = domain.strip().lower()
            if domain and self.is_valid_domain(domain):
                if domain not in normalized_domains:  # Avoid duplicates
                    normalized_domains.append(domain)
            else:
                logger.warning(f"Skipping invalid domain: {domain}")
        
        return normalized_domains
    
    def is_valid_domain(self, domain: str) -> bool:
        """Basic domain validation"""
        import re
        
        # Basic domain regex pattern
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        
        if not re.match(pattern, domain):
            return False
        
        # Check length
        if len(domain) > 253:
            return False
        
        # Check each label
        labels = domain.split('.')
        for label in labels:
            if len(label) > 63:
                return False
        
        return True
    
    async def search_forwarders(self, search_term: str, forwarder_type: Optional[str] = None,
                              active_only: bool = True, skip: int = 0, limit: int = 100) -> List[Forwarder]:
        """Search forwarders by name or description"""
        filters = {}
        
        if forwarder_type:
            filters['forwarder_type'] = forwarder_type
        if active_only:
            filters['is_active'] = True
        
        if self.is_async:
            query = select(Forwarder)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(Forwarder, key):
                    query = query.filter(getattr(Forwarder, key) == value)
            
            # Add search condition
            search_condition = Forwarder.name.ilike(f'%{search_term}%')
            if hasattr(Forwarder, 'description') and Forwarder.description is not None:
                search_condition = search_condition | Forwarder.description.ilike(f'%{search_term}%')
            
            query = query.filter(search_condition).offset(skip).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        else:
            query = self.db.query(Forwarder)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(Forwarder, key):
                    query = query.filter(getattr(Forwarder, key) == value)
            
            # Add search condition
            search_condition = Forwarder.name.ilike(f'%{search_term}%')
            if hasattr(Forwarder, 'description') and Forwarder.description is not None:
                search_condition = search_condition | Forwarder.description.ilike(f'%{search_term}%')
            
            return query.filter(search_condition).offset(skip).limit(limit).all()
    
    async def get_forwarder_by_name(self, forwarder_name: str) -> Optional[Forwarder]:
        """Get a forwarder by its name"""
        if self.is_async:
            result = await self.db.execute(
                select(Forwarder).filter(Forwarder.name == forwarder_name)
            )
            return result.scalar_one_or_none()
        else:
            return self.db.query(Forwarder).filter(Forwarder.name == forwarder_name).first()
    
    async def get_forwarders_summary(self) -> Dict[str, Any]:
        """Get a summary of all forwarders"""
        if self.is_async:
            # Total forwarders
            result = await self.db.execute(select(func.count(Forwarder.id)))
            total_forwarders = result.scalar()
            
            # Active forwarders
            result = await self.db.execute(
                select(func.count(Forwarder.id)).filter(Forwarder.is_active == True)
            )
            active_forwarders = result.scalar()
            
            # Forwarders by type
            result = await self.db.execute(
                select(Forwarder.forwarder_type, func.count(Forwarder.id))
                .group_by(Forwarder.forwarder_type)
            )
            forwarders_by_type = dict(result.fetchall())
            
            # Health check enabled count
            result = await self.db.execute(
                select(func.count(Forwarder.id)).filter(Forwarder.health_check_enabled == True)
            )
            health_check_enabled = result.scalar()
        else:
            # Total forwarders
            total_forwarders = self.db.query(func.count(Forwarder.id)).scalar()
            
            # Active forwarders
            active_forwarders = self.db.query(func.count(Forwarder.id)).filter(Forwarder.is_active == True).scalar()
            
            # Forwarders by type
            forwarders_by_type = dict(
                self.db.query(Forwarder.forwarder_type, func.count(Forwarder.id))
                .group_by(Forwarder.forwarder_type)
                .all()
            )
            
            # Health check enabled count
            health_check_enabled = self.db.query(func.count(Forwarder.id)).filter(
                Forwarder.health_check_enabled == True
            ).scalar()
        
        return {
            "total_forwarders": total_forwarders,
            "active_forwarders": active_forwarders,
            "inactive_forwarders": total_forwarders - active_forwarders,
            "forwarders_by_type": forwarders_by_type,
            "health_check_enabled": health_check_enabled
        }
    
    async def bulk_update_forwarders(self, forwarder_ids: List[int], update_data: Dict[str, Any]) -> List[Forwarder]:
        """Bulk update multiple forwarders"""
        logger.info(f"Bulk updating {len(forwarder_ids)} forwarders")
        
        updated_forwarders = []
        for forwarder_id in forwarder_ids:
            try:
                updated_forwarder = await self.update(forwarder_id, update_data, track_action=True)
                if updated_forwarder:
                    updated_forwarders.append(updated_forwarder)
            except Exception as e:
                logger.error(f"Failed to update forwarder {forwarder_id}: {e}")
                continue
        
        logger.info(f"Successfully updated {len(updated_forwarders)} forwarders")
        return updated_forwarders
    
    async def bulk_toggle_forwarders(self, forwarder_ids: List[int], active: bool) -> List[Forwarder]:
        """Bulk toggle forwarder active status"""
        logger.info(f"Bulk {'activating' if active else 'deactivating'} {len(forwarder_ids)} forwarders")
        
        updated_forwarders = []
        for forwarder_id in forwarder_ids:
            try:
                updated_forwarder = await self.update(forwarder_id, {"is_active": active}, track_action=True)
                if updated_forwarder:
                    updated_forwarders.append(updated_forwarder)
                    
                    # Track specific action
                    action = "forwarder_bulk_activate" if active else "forwarder_bulk_deactivate"
                    track_user_action(
                        action=action,
                        resource_type="forwarder",
                        resource_id=str(forwarder_id),
                        details=f"Forwarder {updated_forwarder.name} {'activated' if active else 'deactivated'} in bulk operation",
                        db=self.db
                    )
            except Exception as e:
                logger.error(f"Failed to toggle forwarder {forwarder_id}: {e}")
                continue
        
        logger.info(f"Successfully {'activated' if active else 'deactivated'} {len(updated_forwarders)} forwarders")
        return updated_forwarders
    
    async def bulk_health_check(self, forwarder_ids: List[int]) -> List[Dict[str, Any]]:
        """Perform bulk health check for multiple forwarders"""
        logger.info(f"Performing bulk health check for {len(forwarder_ids)} forwarders")
        
        results = []
        for forwarder_id in forwarder_ids:
            try:
                result = await self.perform_health_check(forwarder_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to perform health check for forwarder {forwarder_id}: {e}")
                results.append({
                    "forwarder_id": forwarder_id,
                    "error": str(e)
                })
        
        logger.info(f"Completed bulk health check for {len(results)} forwarders")
        return results
    
    async def cleanup_old_health_checks(self, days: int = 30) -> int:
        """Clean up old health check records"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        if self.is_async:
            result = await self.db.execute(
                select(func.count(ForwarderHealth.id))
                .filter(ForwarderHealth.checked_at < cutoff_date)
            )
            count_to_delete = result.scalar()
            
            # Delete old records
            await self.db.execute(
                ForwarderHealth.__table__.delete()
                .where(ForwarderHealth.checked_at < cutoff_date)
            )
            await self.db.commit()
        else:
            count_to_delete = self.db.query(func.count(ForwarderHealth.id)).filter(
                ForwarderHealth.checked_at < cutoff_date
            ).scalar()
            
            # Delete old records
            self.db.query(ForwarderHealth).filter(
                ForwarderHealth.checked_at < cutoff_date
            ).delete()
            self.db.commit()
        
        logger.info(f"Cleaned up {count_to_delete} old health check records older than {days} days")
        return count_to_delete