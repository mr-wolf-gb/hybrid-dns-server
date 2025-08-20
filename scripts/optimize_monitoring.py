#!/usr/bin/env python3
"""
Performance optimization script for DNS monitoring service
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.database import database, init_database
from app.core.logging_config import get_logger
from app.services.monitoring_service import MonitoringService
from app.core.monitoring_config import get_monitoring_config

logger = get_logger(__name__)


async def optimize_database_indexes():
    """Optimize database indexes for monitoring performance"""
    logger.info("Optimizing database indexes for monitoring performance...")
    
    try:
        # Create additional performance indexes
        performance_indexes = [
            # DNS logs performance indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dns_logs_timestamp_client ON dns_logs(timestamp, client_ip)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dns_logs_domain_blocked ON dns_logs(query_domain, blocked)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dns_logs_response_time ON dns_logs(response_time) WHERE response_time > 0",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dns_logs_hourly_stats ON dns_logs(DATE_TRUNC('hour', timestamp), blocked)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dns_logs_daily_stats ON dns_logs(DATE(timestamp), blocked)",
            
            # System stats performance indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_stats_metric_value ON system_stats(metric_name, metric_value)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_stats_hourly ON system_stats(DATE_TRUNC('hour', timestamp), metric_name)",
            
            # Composite indexes for analytics
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dns_logs_analytics ON dns_logs(timestamp, client_ip, query_domain, blocked)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dns_logs_threat_analysis ON dns_logs(timestamp, blocked, rpz_zone) WHERE blocked = true",
        ]
        
        for index_sql in performance_indexes:
            try:
                await database.execute(index_sql)
                logger.info(f"Created index: {index_sql.split()[-1] if 'idx_' in index_sql else 'unnamed'}")
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")
        
        # Analyze tables for query planner optimization
        analyze_queries = [
            "ANALYZE dns_logs",
            "ANALYZE system_stats",
            "ANALYZE rpz_rules"
        ]
        
        for analyze_sql in analyze_queries:
            try:
                await database.execute(analyze_sql)
                logger.info(f"Analyzed table: {analyze_sql.split()[-1]}")
            except Exception as e:
                logger.warning(f"Failed to analyze table: {e}")
        
        logger.info("Database optimization completed")
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")


async def optimize_monitoring_configuration():
    """Optimize monitoring service configuration"""
    logger.info("Optimizing monitoring service configuration...")
    
    config_manager = get_monitoring_config()
    
    # Get system information for optimization
    import psutil
    
    cpu_count = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    # Optimize based on system resources
    optimizations = {}
    
    if cpu_count >= 8:
        optimizations["thread_pool_workers"] = min(8, cpu_count // 2)
        optimizations["batch_size"] = 200
    elif cpu_count >= 4:
        optimizations["thread_pool_workers"] = 4
        optimizations["batch_size"] = 150
    else:
        optimizations["thread_pool_workers"] = 2
        optimizations["batch_size"] = 100
    
    if memory_gb >= 8:
        optimizations["metrics_buffer_size"] = 5000
        optimizations["top_domains_limit"] = 200
        optimizations["response_time_samples"] = 2000
    elif memory_gb >= 4:
        optimizations["metrics_buffer_size"] = 3000
        optimizations["top_domains_limit"] = 150
        optimizations["response_time_samples"] = 1500
    else:
        optimizations["metrics_buffer_size"] = 2000
        optimizations["top_domains_limit"] = 100
        optimizations["response_time_samples"] = 1000
    
    # Apply optimizations
    config_manager.update_monitoring_config(**optimizations)
    
    logger.info(f"Applied monitoring optimizations: {optimizations}")


async def benchmark_monitoring_performance():
    """Benchmark monitoring service performance"""
    logger.info("Benchmarking monitoring service performance...")
    
    try:
        # Initialize monitoring service
        monitoring_service = MonitoringService()
        
        # Test database query performance
        start_time = time.time()
        
        # Test basic query performance
        await database.fetch_one("SELECT COUNT(*) FROM dns_logs WHERE timestamp >= NOW() - INTERVAL '1 hour'")
        basic_query_time = time.time() - start_time
        
        # Test analytics query performance
        start_time = time.time()
        await monitoring_service.get_query_statistics(hours=24)
        analytics_query_time = time.time() - start_time
        
        # Test real-time stats performance
        start_time = time.time()
        await monitoring_service.get_real_time_stats()
        realtime_stats_time = time.time() - start_time
        
        # Test trend analysis performance
        start_time = time.time()
        await monitoring_service.get_blocking_trends(days=7)
        trend_analysis_time = time.time() - start_time
        
        benchmark_results = {
            "basic_query_time": basic_query_time,
            "analytics_query_time": analytics_query_time,
            "realtime_stats_time": realtime_stats_time,
            "trend_analysis_time": trend_analysis_time
        }
        
        logger.info("Benchmark results:")
        for metric, value in benchmark_results.items():
            logger.info(f"  {metric}: {value:.3f} seconds")
        
        # Performance recommendations
        recommendations = []
        
        if basic_query_time > 1.0:
            recommendations.append("Consider adding more database indexes")
        
        if analytics_query_time > 5.0:
            recommendations.append("Enable analytics caching")
        
        if realtime_stats_time > 0.5:
            recommendations.append("Reduce real-time metrics collection frequency")
        
        if trend_analysis_time > 10.0:
            recommendations.append("Optimize trend analysis queries")
        
        if recommendations:
            logger.info("Performance recommendations:")
            for rec in recommendations:
                logger.info(f"  - {rec}")
        else:
            logger.info("Performance is within acceptable limits")
        
        return benchmark_results
        
    except Exception as e:
        logger.error(f"Error benchmarking performance: {e}")
        return {}


async def cleanup_old_monitoring_data():
    """Clean up old monitoring data to improve performance"""
    logger.info("Cleaning up old monitoring data...")
    
    try:
        config = get_monitoring_config().monitoring
        
        # Clean up old DNS logs
        dns_cutoff = f"NOW() - INTERVAL '{config.dns_logs_retention_days} days'"
        dns_deleted = await database.execute(
            f"DELETE FROM dns_logs WHERE timestamp < {dns_cutoff}"
        )
        logger.info(f"Cleaned up DNS logs older than {config.dns_logs_retention_days} days")
        
        # Clean up old system stats
        stats_cutoff = f"NOW() - INTERVAL '{config.system_stats_retention_days} days'"
        stats_deleted = await database.execute(
            f"DELETE FROM system_stats WHERE timestamp < {stats_cutoff}"
        )
        logger.info(f"Cleaned up system stats older than {config.system_stats_retention_days} days")
        
        # Vacuum database to reclaim space
        try:
            await database.execute("VACUUM ANALYZE")
            logger.info("Database vacuum completed")
        except Exception as e:
            logger.warning(f"Database vacuum failed: {e}")
        
        logger.info("Data cleanup completed")
        
    except Exception as e:
        logger.error(f"Error cleaning up data: {e}")


async def generate_performance_report():
    """Generate comprehensive performance report"""
    logger.info("Generating performance report...")
    
    try:
        # Get system information
        import psutil
        
        system_info = {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
        
        # Get database statistics
        db_stats = await database.fetch_one("""
            SELECT 
                (SELECT COUNT(*) FROM dns_logs) as total_dns_logs,
                (SELECT COUNT(*) FROM system_stats) as total_system_stats,
                (SELECT COUNT(*) FROM dns_logs WHERE timestamp >= NOW() - INTERVAL '24 hours') as recent_dns_logs,
                (SELECT AVG(response_time) FROM dns_logs WHERE response_time > 0 AND timestamp >= NOW() - INTERVAL '24 hours') as avg_response_time
        """)
        
        # Get monitoring service performance
        monitoring_service = MonitoringService()
        performance_metrics = await monitoring_service.get_performance_metrics(hours=24)
        
        # Benchmark performance
        benchmark_results = await benchmark_monitoring_performance()
        
        report = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": system_info,
            "database_stats": dict(db_stats) if db_stats else {},
            "performance_metrics": {
                "queries_per_second": performance_metrics.queries_per_second,
                "avg_response_time": performance_metrics.avg_response_time,
                "error_rate": performance_metrics.error_rate,
                "blocked_rate": performance_metrics.blocked_rate
            },
            "benchmark_results": benchmark_results,
            "configuration": get_monitoring_config().get_config_dict()
        }
        
        # Save report to file
        import json
        report_path = Path(__file__).parent.parent / "monitoring_performance_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Performance report saved to: {report_path}")
        
        # Print summary
        logger.info("Performance Report Summary:")
        logger.info(f"  System: {system_info['cpu_count']} CPUs, {system_info['memory_total_gb']:.1f}GB RAM")
        logger.info(f"  Database: {report['database_stats'].get('total_dns_logs', 0)} DNS logs, {report['database_stats'].get('total_system_stats', 0)} system stats")
        logger.info(f"  Performance: {performance_metrics.queries_per_second:.1f} QPS, {performance_metrics.avg_response_time:.1f}ms avg response")
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        return {}


async def main():
    """Main optimization function"""
    logger.info("Starting monitoring service optimization...")
    
    try:
        # Initialize database
        await init_database()
        
        # Run optimization tasks
        await optimize_database_indexes()
        await optimize_monitoring_configuration()
        await cleanup_old_monitoring_data()
        
        # Generate performance report
        report = await generate_performance_report()
        
        logger.info("Monitoring service optimization completed successfully")
        
        # Print optimization summary
        config = get_monitoring_config()
        logger.info("Optimization Summary:")
        logger.info(f"  Buffer size: {config.monitoring.metrics_buffer_size}")
        logger.info(f"  Batch size: {config.monitoring.batch_size}")
        logger.info(f"  Thread pool workers: {config.monitoring.thread_pool_workers}")
        logger.info(f"  Cache TTL: {config.monitoring.cache_ttl} seconds")
        
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
        sys.exit(1)
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())