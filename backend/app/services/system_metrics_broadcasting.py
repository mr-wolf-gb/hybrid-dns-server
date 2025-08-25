"""
System metrics broadcasting service with configurable collection and streaming
Implements CPU, memory, disk, network metrics and BIND9 status monitoring
"""

import asyncio
import json
import psutil
import subprocess
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import threading
import socket
import shutil

from ..core.config import get_settings
from ..core.logging_config import get_logger
from ..websocket.event_types import EventType, EventPriority, EventSeverity, create_event
from ..services.enhanced_event_service import get_enhanced_event_service

logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """System metrics data structure"""
    timestamp: datetime
    cpu_usage: float
    cpu_cores: int
    cpu_frequency: float
    memory_total: int
    memory_used: int
    memory_available: int
    memory_percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    disk_total: int
    disk_used: int
    disk_free: int
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    network_packets_sent: int
    network_packets_recv: int
    load_average: Tuple[float, float, float]
    uptime: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu": {
                "usage_percent": self.cpu_usage,
                "cores": self.cpu_cores,
                "frequency_mhz": self.cpu_frequency
            },
            "memory": {
                "total_bytes": self.memory_total,
                "used_bytes": self.memory_used,
                "available_bytes": self.memory_available,
                "usage_percent": self.memory_percent
            },
            "swap": {
                "total_bytes": self.swap_total,
                "used_bytes": self.swap_used,
                "usage_percent": self.swap_percent
            },
            "disk": {
                "total_bytes": self.disk_total,
                "used_bytes": self.disk_used,
                "free_bytes": self.disk_free,
                "usage_percent": self.disk_percent
            },
            "network": {
                "bytes_sent": self.network_bytes_sent,
                "bytes_received": self.network_bytes_recv,
                "packets_sent": self.network_packets_sent,
                "packets_received": self.network_packets_recv
            },
            "system": {
                "load_average_1m": self.load_average[0],
                "load_average_5m": self.load_average[1],
                "load_average_15m": self.load_average[2],
                "uptime_seconds": self.uptime
            }
        }


@dataclass
class BIND9Metrics:
    """BIND9 specific metrics"""
    timestamp: datetime
    is_running: bool
    pid: Optional[int]
    memory_usage: float
    cpu_usage: float
    queries_per_second: float
    cache_size: int
    cache_hit_rate: float
    zones_loaded: int
    forwarders_active: int
    recursive_queries: int
    authoritative_queries: int
    nxdomain_responses: int
    servfail_responses: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": {
                "running": self.is_running,
                "pid": self.pid
            },
            "performance": {
                "memory_usage_mb": self.memory_usage,
                "cpu_usage_percent": self.cpu_usage,
                "queries_per_second": self.queries_per_second
            },
            "cache": {
                "size_bytes": self.cache_size,
                "hit_rate_percent": self.cache_hit_rate
            },
            "zones": {
                "loaded_count": self.zones_loaded
            },
            "forwarders": {
                "active_count": self.forwarders_active
            },
            "queries": {
                "recursive": self.recursive_queries,
                "authoritative": self.authoritative_queries,
                "nxdomain": self.nxdomain_responses,
                "servfail": self.servfail_responses
            }
        }


@dataclass
class NetworkInterfaceMetrics:
    """Network interface specific metrics"""
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drops_in: int
    drops_out: int
    is_up: bool
    speed: Optional[int]
    mtu: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "interface": self.interface,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_recv,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_recv,
            "errors_in": self.errors_in,
            "errors_out": self.errors_out,
            "drops_in": self.drops_in,
            "drops_out": self.drops_out,
            "is_up": self.is_up,
            "speed_mbps": self.speed,
            "mtu": self.mtu
        }


@dataclass
class DiskMetrics:
    """Disk/filesystem specific metrics"""
    device: str
    mountpoint: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "device": self.device,
            "mountpoint": self.mountpoint,
            "filesystem_type": self.fstype,
            "total_bytes": self.total,
            "used_bytes": self.used,
            "free_bytes": self.free,
            "usage_percent": self.percent
        }


class MetricsCollectionConfig:
    """Configuration for metrics collection"""
    
    def __init__(self,
                 collect_system_metrics: bool = True,
                 collect_bind9_metrics: bool = True,
                 collect_network_interfaces: bool = True,
                 collect_disk_metrics: bool = True,
                 system_metrics_interval: int = 30,
                 bind9_metrics_interval: int = 60,
                 network_metrics_interval: int = 30,
                 disk_metrics_interval: int = 300,
                 enable_detailed_network: bool = False,
                 enable_detailed_disk: bool = False,
                 max_history_points: int = 1440):  # 24 hours at 1-minute intervals
        self.collect_system_metrics = collect_system_metrics
        self.collect_bind9_metrics = collect_bind9_metrics
        self.collect_network_interfaces = collect_network_interfaces
        self.collect_disk_metrics = collect_disk_metrics
        self.system_metrics_interval = system_metrics_interval
        self.bind9_metrics_interval = bind9_metrics_interval
        self.network_metrics_interval = network_metrics_interval
        self.disk_metrics_interval = disk_metrics_interval
        self.enable_detailed_network = enable_detailed_network
        self.enable_detailed_disk = enable_detailed_disk
        self.max_history_points = max_history_points


class SystemMetricsBroadcastingService:
    """System metrics broadcasting service with configurable collection"""
    
    def __init__(self, config: Optional[MetricsCollectionConfig] = None):
        self.config = config or MetricsCollectionConfig()
        self.settings = get_settings()
        self.event_service = get_enhanced_event_service()
        
        # Metrics history
        self.system_metrics_history = deque(maxlen=self.config.max_history_points)
        self.bind9_metrics_history = deque(maxlen=self.config.max_history_points)
        self.network_metrics_history = deque(maxlen=self.config.max_history_points)
        self.disk_metrics_history = deque(maxlen=self.config.max_history_points)
        
        # Background tasks
        self._running = False
        self._system_task: Optional[asyncio.Task] = None
        self._bind9_task: Optional[asyncio.Task] = None
        self._network_task: Optional[asyncio.Task] = None
        self._disk_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Cached data for rate calculations
        self._last_network_stats = None
        self._last_network_time = None
        self._last_bind9_stats = None
        self._last_bind9_time = None
        
        # BIND9 process tracking
        self._bind9_process = None
        self._bind9_pid = None
        
        # Thread lock for metrics access
        self._metrics_lock = threading.Lock()
        
        # Alert thresholds
        self.cpu_alert_threshold = 90.0
        self.memory_alert_threshold = 90.0
        self.disk_alert_threshold = 90.0
        self.load_alert_threshold = 10.0
    
    async def start(self):
        """Start the system metrics broadcasting service"""
        if self._running:
            return
        
        self._running = True
        
        # Start collection tasks based on configuration
        if self.config.collect_system_metrics:
            self._system_task = asyncio.create_task(self._collect_system_metrics())
        
        if self.config.collect_bind9_metrics:
            self._bind9_task = asyncio.create_task(self._collect_bind9_metrics())
        
        if self.config.collect_network_interfaces:
            self._network_task = asyncio.create_task(self._collect_network_metrics())
        
        if self.config.collect_disk_metrics:
            self._disk_task = asyncio.create_task(self._collect_disk_metrics())
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())
        
        logger.info("System metrics broadcasting service started")
    
    async def stop(self):
        """Stop the system metrics broadcasting service"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all tasks
        tasks = [self._system_task, self._bind9_task, self._network_task, 
                self._disk_task, self._cleanup_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("System metrics broadcasting service stopped")
    
    async def _collect_system_metrics(self):
        """Collect and broadcast system metrics"""
        while self._running:
            try:
                metrics = await self._get_system_metrics()
                
                # Store in history
                with self._metrics_lock:
                    self.system_metrics_history.append(metrics)
                
                # Check for alerts
                await self._check_system_alerts(metrics)
                
                # Broadcast metrics
                await self.event_service.emit_event(
                    event_type=EventType.SYSTEM_METRICS,
                    data=metrics.to_dict(),
                    priority=EventPriority.LOW,
                    severity=EventSeverity.INFO
                )
                
                await asyncio.sleep(self.config.system_metrics_interval)
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(self.config.system_metrics_interval)
    
    async def _get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        cpu_frequency = cpu_freq.current if cpu_freq else 0.0
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics (root filesystem)
        disk = psutil.disk_usage('/')
        
        # Network metrics (total across all interfaces)
        network = psutil.net_io_counters()
        
        # System load and uptime
        try:
            load_avg = psutil.getloadavg()
        except AttributeError:
            # Windows doesn't have load average
            load_avg = (0.0, 0.0, 0.0)
        
        uptime = time.time() - psutil.boot_time()
        
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_usage=cpu_percent,
            cpu_cores=cpu_count,
            cpu_frequency=cpu_frequency,
            memory_total=memory.total,
            memory_used=memory.used,
            memory_available=memory.available,
            memory_percent=memory.percent,
            swap_total=swap.total,
            swap_used=swap.used,
            swap_percent=swap.percent,
            disk_total=disk.total,
            disk_used=disk.used,
            disk_free=disk.free,
            disk_percent=disk.percent,
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            network_packets_sent=network.packets_sent,
            network_packets_recv=network.packets_recv,
            load_average=load_avg,
            uptime=uptime
        )
    
    async def _check_system_alerts(self, metrics: SystemMetrics):
        """Check system metrics for alert conditions"""
        alerts = []
        
        # CPU usage alert
        if metrics.cpu_usage > self.cpu_alert_threshold:
            alerts.append({
                "type": "high_cpu_usage",
                "value": metrics.cpu_usage,
                "threshold": self.cpu_alert_threshold,
                "message": f"CPU usage is {metrics.cpu_usage:.1f}% (threshold: {self.cpu_alert_threshold}%)"
            })
        
        # Memory usage alert
        if metrics.memory_percent > self.memory_alert_threshold:
            alerts.append({
                "type": "high_memory_usage",
                "value": metrics.memory_percent,
                "threshold": self.memory_alert_threshold,
                "message": f"Memory usage is {metrics.memory_percent:.1f}% (threshold: {self.memory_alert_threshold}%)"
            })
        
        # Disk usage alert
        if metrics.disk_percent > self.disk_alert_threshold:
            alerts.append({
                "type": "high_disk_usage",
                "value": metrics.disk_percent,
                "threshold": self.disk_alert_threshold,
                "message": f"Disk usage is {metrics.disk_percent:.1f}% (threshold: {self.disk_alert_threshold}%)"
            })
        
        # Load average alert
        if metrics.load_average[0] > self.load_alert_threshold:
            alerts.append({
                "type": "high_load_average",
                "value": metrics.load_average[0],
                "threshold": self.load_alert_threshold,
                "message": f"Load average is {metrics.load_average[0]:.2f} (threshold: {self.load_alert_threshold})"
            })
        
        # Emit alerts
        for alert in alerts:
            await self.event_service.emit_event(
                event_type=EventType.PERFORMANCE_ALERT,
                data=alert,
                priority=EventPriority.HIGH,
                severity=EventSeverity.WARNING
            )
    
    async def _collect_bind9_metrics(self):
        """Collect and broadcast BIND9 metrics"""
        while self._running:
            try:
                metrics = await self._get_bind9_metrics()
                
                # Store in history
                with self._metrics_lock:
                    self.bind9_metrics_history.append(metrics)
                
                # Check for BIND9 alerts
                await self._check_bind9_alerts(metrics)
                
                # Broadcast metrics
                await self.event_service.emit_event(
                    event_type=EventType.BIND_STATUS_UPDATE,
                    data=metrics.to_dict(),
                    priority=EventPriority.NORMAL,
                    severity=EventSeverity.INFO
                )
                
                await asyncio.sleep(self.config.bind9_metrics_interval)
                
            except Exception as e:
                logger.error(f"Error collecting BIND9 metrics: {e}")
                await asyncio.sleep(self.config.bind9_metrics_interval)
    
    async def _get_bind9_metrics(self) -> BIND9Metrics:
        """Get current BIND9 metrics"""
        # Find BIND9 process
        bind9_process = None
        bind9_pid = None
        is_running = False
        memory_usage = 0.0
        cpu_usage = 0.0
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] and 'named' in proc.info['name'].lower():
                    bind9_process = psutil.Process(proc.info['pid'])
                    bind9_pid = proc.info['pid']
                    is_running = True
                    
                    # Get process metrics
                    memory_info = bind9_process.memory_info()
                    memory_usage = memory_info.rss / (1024 * 1024)  # MB
                    cpu_usage = bind9_process.cpu_percent()
                    
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        
        # Get BIND9 statistics if available
        queries_per_second = 0.0
        cache_size = 0
        cache_hit_rate = 0.0
        zones_loaded = 0
        forwarders_active = 0
        recursive_queries = 0
        authoritative_queries = 0
        nxdomain_responses = 0
        servfail_responses = 0
        
        if is_running:
            try:
                # Try to get BIND9 statistics via rndc
                stats = await self._get_bind9_statistics()
                if stats:
                    queries_per_second = stats.get('queries_per_second', 0.0)
                    cache_size = stats.get('cache_size', 0)
                    cache_hit_rate = stats.get('cache_hit_rate', 0.0)
                    zones_loaded = stats.get('zones_loaded', 0)
                    forwarders_active = stats.get('forwarders_active', 0)
                    recursive_queries = stats.get('recursive_queries', 0)
                    authoritative_queries = stats.get('authoritative_queries', 0)
                    nxdomain_responses = stats.get('nxdomain_responses', 0)
                    servfail_responses = stats.get('servfail_responses', 0)
            except Exception as e:
                logger.debug(f"Could not get BIND9 statistics: {e}")
        
        return BIND9Metrics(
            timestamp=datetime.utcnow(),
            is_running=is_running,
            pid=bind9_pid,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            queries_per_second=queries_per_second,
            cache_size=cache_size,
            cache_hit_rate=cache_hit_rate,
            zones_loaded=zones_loaded,
            forwarders_active=forwarders_active,
            recursive_queries=recursive_queries,
            authoritative_queries=authoritative_queries,
            nxdomain_responses=nxdomain_responses,
            servfail_responses=servfail_responses
        )
    
    async def _get_bind9_statistics(self) -> Optional[Dict[str, Any]]:
        """Get BIND9 statistics via rndc or statistics channel"""
        try:
            # Try rndc stats command
            result = subprocess.run(
                ['rndc', 'stats'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse statistics from named.stats file
                stats_file = Path('/var/cache/bind/named.stats')
                if stats_file.exists():
                    return await self._parse_bind9_stats_file(stats_file)
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try statistics channel (if configured)
        try:
            return await self._get_bind9_stats_via_http()
        except Exception:
            pass
        
        return None
    
    async def _parse_bind9_stats_file(self, stats_file: Path) -> Dict[str, Any]:
        """Parse BIND9 statistics file"""
        stats = {}
        
        try:
            with open(stats_file, 'r') as f:
                content = f.read()
            
            # Parse basic statistics (simplified parsing)
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if 'queries resulted in' in line:
                    # Extract query statistics
                    pass
                elif 'cache' in line.lower():
                    # Extract cache statistics
                    pass
        
        except Exception as e:
            logger.debug(f"Error parsing BIND9 stats file: {e}")
        
        return stats
    
    async def _get_bind9_stats_via_http(self) -> Dict[str, Any]:
        """Get BIND9 statistics via HTTP statistics channel"""
        # This would require BIND9 to be configured with statistics-channels
        # For now, return empty dict
        return {}
    
    async def _check_bind9_alerts(self, metrics: BIND9Metrics):
        """Check BIND9 metrics for alert conditions"""
        alerts = []
        
        # BIND9 not running alert
        if not metrics.is_running:
            alerts.append({
                "type": "bind9_not_running",
                "message": "BIND9 service is not running"
            })
        
        # High memory usage alert
        if metrics.memory_usage > 1000:  # 1GB
            alerts.append({
                "type": "bind9_high_memory",
                "value": metrics.memory_usage,
                "threshold": 1000,
                "message": f"BIND9 memory usage is {metrics.memory_usage:.1f}MB"
            })
        
        # High CPU usage alert
        if metrics.cpu_usage > 80:
            alerts.append({
                "type": "bind9_high_cpu",
                "value": metrics.cpu_usage,
                "threshold": 80,
                "message": f"BIND9 CPU usage is {metrics.cpu_usage:.1f}%"
            })
        
        # Emit alerts
        for alert in alerts:
            await self.event_service.emit_event(
                event_type=EventType.HEALTH_ALERT,
                data=alert,
                priority=EventPriority.HIGH,
                severity=EventSeverity.WARNING
            )
    
    async def _collect_network_metrics(self):
        """Collect and broadcast network interface metrics"""
        while self._running:
            try:
                if self.config.enable_detailed_network:
                    # Collect per-interface metrics
                    interfaces = await self._get_network_interface_metrics()
                    
                    # Broadcast detailed metrics
                    await self.event_service.emit_event(
                        event_type=EventType.NETWORK_INTERFACE_METRICS,
                        data={"interfaces": [iface.to_dict() for iface in interfaces]},
                        priority=EventPriority.LOW,
                        severity=EventSeverity.INFO
                    )
                else:
                    # Collect aggregate metrics
                    metrics = await self._get_aggregate_network_metrics()
                    
                    # Broadcast aggregate metrics
                    await self.event_service.emit_event(
                        event_type=EventType.NETWORK_METRICS,
                        data=metrics,
                        priority=EventPriority.LOW,
                        severity=EventSeverity.INFO
                    )
                
                await asyncio.sleep(self.config.network_metrics_interval)
                
            except Exception as e:
                logger.error(f"Error collecting network metrics: {e}")
                await asyncio.sleep(self.config.network_metrics_interval)
    
    async def _get_network_interface_metrics(self) -> List[NetworkInterfaceMetrics]:
        """Get per-interface network metrics"""
        interfaces = []
        
        try:
            net_io = psutil.net_io_counters(pernic=True)
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for interface, io_counters in net_io.items():
                if interface in net_if_stats:
                    stats = net_if_stats[interface]
                    
                    interface_metrics = NetworkInterfaceMetrics(
                        interface=interface,
                        bytes_sent=io_counters.bytes_sent,
                        bytes_recv=io_counters.bytes_recv,
                        packets_sent=io_counters.packets_sent,
                        packets_recv=io_counters.packets_recv,
                        errors_in=io_counters.errin,
                        errors_out=io_counters.errout,
                        drops_in=io_counters.dropin,
                        drops_out=io_counters.dropout,
                        is_up=stats.isup,
                        speed=stats.speed,
                        mtu=stats.mtu
                    )
                    
                    interfaces.append(interface_metrics)
        
        except Exception as e:
            logger.error(f"Error getting network interface metrics: {e}")
        
        return interfaces
    
    async def _get_aggregate_network_metrics(self) -> Dict[str, Any]:
        """Get aggregate network metrics"""
        try:
            net_io = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "bytes_sent": net_io.bytes_sent,
                "bytes_received": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_received": net_io.packets_recv,
                "errors_in": net_io.errin,
                "errors_out": net_io.errout,
                "drops_in": net_io.dropin,
                "drops_out": net_io.dropout
            }
        
        except Exception as e:
            logger.error(f"Error getting aggregate network metrics: {e}")
            return {"timestamp": datetime.utcnow().isoformat(), "error": str(e)}
    
    async def _collect_disk_metrics(self):
        """Collect and broadcast disk metrics"""
        while self._running:
            try:
                if self.config.enable_detailed_disk:
                    # Collect per-disk metrics
                    disks = await self._get_disk_metrics()
                    
                    # Broadcast detailed metrics
                    await self.event_service.emit_event(
                        event_type=EventType.DISK_METRICS,
                        data={"disks": [disk.to_dict() for disk in disks]},
                        priority=EventPriority.LOW,
                        severity=EventSeverity.INFO
                    )
                else:
                    # Just broadcast root filesystem metrics
                    root_disk = psutil.disk_usage('/')
                    
                    await self.event_service.emit_event(
                        event_type=EventType.DISK_METRICS,
                        data={
                            "timestamp": datetime.utcnow().isoformat(),
                            "root_filesystem": {
                                "total_bytes": root_disk.total,
                                "used_bytes": root_disk.used,
                                "free_bytes": root_disk.free,
                                "usage_percent": root_disk.percent
                            }
                        },
                        priority=EventPriority.LOW,
                        severity=EventSeverity.INFO
                    )
                
                await asyncio.sleep(self.config.disk_metrics_interval)
                
            except Exception as e:
                logger.error(f"Error collecting disk metrics: {e}")
                await asyncio.sleep(self.config.disk_metrics_interval)
    
    async def _get_disk_metrics(self) -> List[DiskMetrics]:
        """Get per-disk metrics"""
        disks = []
        
        try:
            disk_partitions = psutil.disk_partitions()
            
            for partition in disk_partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    disk_metrics = DiskMetrics(
                        device=partition.device,
                        mountpoint=partition.mountpoint,
                        fstype=partition.fstype,
                        total=usage.total,
                        used=usage.used,
                        free=usage.free,
                        percent=usage.percent
                    )
                    
                    disks.append(disk_metrics)
                
                except (PermissionError, FileNotFoundError):
                    # Skip inaccessible partitions
                    continue
        
        except Exception as e:
            logger.error(f"Error getting disk metrics: {e}")
        
        return disks
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent memory leaks"""
        while self._running:
            try:
                # Clean up every hour
                await asyncio.sleep(3600)
                
                with self._metrics_lock:
                    # Trim history to max size (should be automatic with deque maxlen)
                    # But we can also clean up based on age
                    cutoff_time = datetime.utcnow() - timedelta(hours=24)
                    
                    # Clean system metrics
                    self.system_metrics_history = deque(
                        [m for m in self.system_metrics_history if m.timestamp > cutoff_time],
                        maxlen=self.config.max_history_points
                    )
                    
                    # Clean BIND9 metrics
                    self.bind9_metrics_history = deque(
                        [m for m in self.bind9_metrics_history if m.timestamp > cutoff_time],
                        maxlen=self.config.max_history_points
                    )
                
                logger.debug("Cleaned up old metrics data")
                
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
                await asyncio.sleep(3600)
    
    def get_current_system_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent system metrics"""
        with self._metrics_lock:
            return self.system_metrics_history[-1] if self.system_metrics_history else None
    
    def get_current_bind9_metrics(self) -> Optional[BIND9Metrics]:
        """Get the most recent BIND9 metrics"""
        with self._metrics_lock:
            return self.bind9_metrics_history[-1] if self.bind9_metrics_history else None
    
    def get_metrics_history(self, 
                          metric_type: str, 
                          hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._metrics_lock:
            if metric_type == "system":
                return [m.to_dict() for m in self.system_metrics_history 
                       if m.timestamp > cutoff_time]
            elif metric_type == "bind9":
                return [m.to_dict() for m in self.bind9_metrics_history 
                       if m.timestamp > cutoff_time]
            else:
                return []
    
    def update_config(self, config: MetricsCollectionConfig):
        """Update metrics collection configuration"""
        self.config = config
        logger.info("Updated metrics collection configuration")
    
    def set_alert_thresholds(self, 
                           cpu_threshold: Optional[float] = None,
                           memory_threshold: Optional[float] = None,
                           disk_threshold: Optional[float] = None,
                           load_threshold: Optional[float] = None):
        """Update alert thresholds"""
        if cpu_threshold is not None:
            self.cpu_alert_threshold = cpu_threshold
        if memory_threshold is not None:
            self.memory_alert_threshold = memory_threshold
        if disk_threshold is not None:
            self.disk_alert_threshold = disk_threshold
        if load_threshold is not None:
            self.load_alert_threshold = load_threshold
        
        logger.info("Updated alert thresholds")


# Add new event types for system metrics
# These should be added to the event_types.py file
SYSTEM_METRICS_EVENTS = [
    "SYSTEM_METRICS",
    "BIND_STATUS_UPDATE", 
    "NETWORK_INTERFACE_METRICS",
    "NETWORK_METRICS",
    "DISK_METRICS"
]


# Global service instance
_system_metrics_service: Optional[SystemMetricsBroadcastingService] = None


def get_system_metrics_service(config: Optional[MetricsCollectionConfig] = None) -> SystemMetricsBroadcastingService:
    """Get the global system metrics broadcasting service instance"""
    global _system_metrics_service
    if _system_metrics_service is None:
        _system_metrics_service = SystemMetricsBroadcastingService(config)
    return _system_metrics_service


async def initialize_system_metrics_service(config: Optional[MetricsCollectionConfig] = None) -> SystemMetricsBroadcastingService:
    """Initialize and start the system metrics broadcasting service"""
    service = get_system_metrics_service(config)
    await service.start()
    return service


async def shutdown_system_metrics_service():
    """Shutdown the system metrics broadcasting service"""
    global _system_metrics_service
    if _system_metrics_service:
        await _system_metrics_service.stop()
        _system_metrics_service = None