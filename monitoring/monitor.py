#!/usr/bin/env python3
"""
DNS Query Monitoring Service
Parses BIND9 logs and stores analytics in PostgreSQL
"""

import asyncio
import asyncpg
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DNSMonitor:
    def __init__(self):
        self.db_host = os.getenv('DB_HOST', 'postgres')
        self.db_port = os.getenv('DB_PORT', 5432)
        self.db_name = os.getenv('DB_NAME', 'hybrid_dns')
        self.db_user = os.getenv('DB_USER', 'dns_user')
        self.db_password = os.getenv('DB_PASSWORD', 'dns_password')
        self.log_file = Path('/var/log/bind/queries.log')
        self.security_log = Path('/var/log/bind/security.log')
        
        # Regex patterns for log parsing
        self.query_pattern = re.compile(
            r'(\d+-\w+-\d+ \d+:\d+:\d+\.\d+) client @0x[a-f0-9]+ ([0-9.]+)#(\d+) \(([^)]+)\): query: ([^ ]+) IN ([^ ]+) \+([^(]*) \(([^)]+)\)'
        )
        self.security_pattern = re.compile(
            r'(\d+-\w+-\d+ \d+:\d+:\d+\.\d+) rpz: info: client ([0-9.]+)#(\d+) \(([^)]+)\): rpz ([^ ]+) policy ([^ ]+) rewritten ([^ ]+) to ([^ ]+)'
        )
        
        self.pool = None

    async def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                min_size=2,
                max_size=10
            )
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def parse_query_log(self, line: str):
        """Parse a DNS query log line"""
        match = self.query_pattern.match(line.strip())
        if not match:
            return None
            
        timestamp_str, client_ip, client_port, query_name, domain, record_type, flags, source = match.groups()
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S.%f')
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        except ValueError:
            timestamp = datetime.now(timezone.utc)
        
        return {
            'timestamp': timestamp,
            'client_ip': client_ip,
            'client_port': int(client_port),
            'query_name': query_name,
            'domain': domain,
            'record_type': record_type,
            'flags': flags.strip(),
            'source': source,
            'blocked': False
        }

    async def parse_security_log(self, line: str):
        """Parse a security/RPZ log line"""
        match = self.security_pattern.match(line.strip())
        if not match:
            return None
            
        timestamp_str, client_ip, client_port, query_name, policy_zone, policy_action, original, rewritten = match.groups()
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S.%f')
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        except ValueError:
            timestamp = datetime.now(timezone.utc)
        
        return {
            'timestamp': timestamp,
            'client_ip': client_ip,
            'client_port': int(client_port),
            'query_name': query_name,
            'domain': original,
            'record_type': 'A',  # Default assumption
            'flags': '',
            'source': 'rpz',
            'blocked': True,
            'policy_zone': policy_zone,
            'policy_action': policy_action,
            'rewritten_to': rewritten
        }

    async def store_query(self, query_data: dict):
        """Store query data in database"""
        if not self.pool:
            return
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO dns_logs (
                        timestamp, client_ip, client_port, domain, record_type,
                        response_code, query_flags, blocked, policy_zone,
                        policy_action, response_time
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    query_data['timestamp'],
                    query_data['client_ip'],
                    query_data.get('client_port', 0),
                    query_data['domain'],
                    query_data['record_type'],
                    'NOERROR',  # Default response
                    query_data.get('flags', ''),
                    query_data.get('blocked', False),
                    query_data.get('policy_zone'),
                    query_data.get('policy_action'),
                    0.0  # Response time not available from logs
                )
        except Exception as e:
            logger.error(f"Failed to store query data: {e}")

    async def tail_file(self, file_path: Path, parser_func):
        """Tail a log file and parse new lines"""
        if not file_path.exists():
            logger.warning(f"Log file {file_path} does not exist, waiting...")
            return
            
        try:
            # Start from end of file
            with open(file_path, 'r') as f:
                f.seek(0, 2)  # Go to end of file
                
                while True:
                    line = f.readline()
                    if line:
                        query_data = await parser_func(line)
                        if query_data:
                            await self.store_query(query_data)
                    else:
                        await asyncio.sleep(0.1)
                        
        except Exception as e:
            logger.error(f"Error tailing file {file_path}: {e}")
            await asyncio.sleep(5)  # Wait before retrying

    async def update_system_stats(self):
        """Update system statistics periodically"""
        if not self.pool:
            return
            
        try:
            async with self.pool.acquire() as conn:
                # Count queries in last hour
                queries_last_hour = await conn.fetchval(
                    "SELECT COUNT(*) FROM dns_logs WHERE timestamp > NOW() - INTERVAL '1 hour'"
                )
                
                # Count blocked queries in last hour
                blocked_last_hour = await conn.fetchval(
                    "SELECT COUNT(*) FROM dns_logs WHERE timestamp > NOW() - INTERVAL '1 hour' AND blocked = true"
                )
                
                # Update or insert stats
                await conn.execute(
                    """
                    INSERT INTO system_stats (metric, value, timestamp)
                    VALUES ('queries_per_hour', $1, NOW()),
                           ('blocked_per_hour', $2, NOW())
                    ON CONFLICT (metric) DO UPDATE SET
                        value = EXCLUDED.value,
                        timestamp = EXCLUDED.timestamp
                    """,
                    queries_last_hour,
                    blocked_last_hour
                )
                
                logger.info(f"Updated stats: {queries_last_hour} queries, {blocked_last_hour} blocked in last hour")
                
        except Exception as e:
            logger.error(f"Failed to update system stats: {e}")

    async def stats_updater(self):
        """Background task to update statistics"""
        while True:
            try:
                await self.update_system_stats()
                await asyncio.sleep(300)  # Update every 5 minutes
            except Exception as e:
                logger.error(f"Error in stats updater: {e}")
                await asyncio.sleep(60)

    async def run(self):
        """Main monitoring loop"""
        logger.info("Starting DNS monitoring service...")
        
        # Connect to database
        await self.connect_db()
        
        # Start background stats updater
        stats_task = asyncio.create_task(self.stats_updater())
        
        # Start log tailing tasks
        tasks = []
        
        if self.log_file.exists():
            tasks.append(asyncio.create_task(
                self.tail_file(self.log_file, self.parse_query_log)
            ))
            
        if self.security_log.exists():
            tasks.append(asyncio.create_task(
                self.tail_file(self.security_log, self.parse_security_log)
            ))
        
        if not tasks:
            logger.warning("No log files found, monitoring will be limited")
        
        # Wait for all tasks
        try:
            await asyncio.gather(stats_task, *tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down DNS monitoring service...")
        finally:
            if self.pool:
                await self.pool.close()

async def main():
    """Main entry point"""
    monitor = DNSMonitor()
    await monitor.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("DNS monitoring service stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)