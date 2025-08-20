"""
Enhanced monitoring configuration for performance optimization
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class MonitoringConfig:
    """Configuration for enhanced monitoring service"""
    
    # Buffer settings
    metrics_buffer_size: int = 2000
    batch_size: int = 100
    batch_timeout: float = 5.0
    
    # Performance settings
    thread_pool_workers: int = 4
    cache_ttl: int = 300  # 5 minutes
    real_time_update_interval: int = 10  # seconds
    
    # Data retention
    dns_logs_retention_days: int = 30
    system_stats_retention_days: int = 7
    analytics_cache_retention_hours: int = 24
    
    # Real-time metrics limits
    top_domains_limit: int = 100
    top_clients_limit: int = 100
    response_time_samples: int = 1000
    
    # Trend analysis
    trend_analysis_interval: int = 900  # 15 minutes
    anomaly_detection_interval: int = 300  # 5 minutes
    cleanup_interval: int = 3600  # 1 hour
    
    # Alert thresholds
    high_query_volume_threshold: float = 2.0  # 200% of normal
    low_query_volume_threshold: float = 0.5   # 50% of normal
    high_response_time_threshold: float = 2.0  # 200% of normal
    error_rate_threshold: float = 5.0  # 5% error rate
    
    # WebSocket broadcasting
    broadcast_throttle_queries: int = 10  # Broadcast every 10th query
    broadcast_system_metrics_interval: int = 60  # seconds
    
    # Database optimization
    enable_batch_inserts: bool = True
    enable_query_optimization: bool = True
    enable_index_hints: bool = True
    
    # Analytics features
    enable_trend_analysis: bool = True
    enable_anomaly_detection: bool = True
    enable_predictive_analytics: bool = True
    enable_geographic_analytics: bool = True
    
    # Export settings
    max_export_records: int = 100000
    export_formats: List[str] = None
    
    def __post_init__(self):
        if self.export_formats is None:
            self.export_formats = ["json", "csv"]


@dataclass
class PerformanceThresholds:
    """Performance thresholds for monitoring and alerting"""
    
    # Query performance
    max_queries_per_second: float = 1000.0
    max_avg_response_time: float = 100.0  # milliseconds
    max_p95_response_time: float = 500.0  # milliseconds
    
    # System performance
    max_cpu_usage: float = 80.0  # percentage
    max_memory_usage: float = 85.0  # percentage
    max_disk_usage: float = 90.0  # percentage
    
    # Error rates
    max_error_rate: float = 1.0  # percentage
    max_timeout_rate: float = 0.5  # percentage
    
    # Threat detection
    max_block_rate: float = 20.0  # percentage
    threat_spike_threshold: float = 3.0  # 300% increase
    
    # Database performance
    max_db_connection_time: float = 1000.0  # milliseconds
    max_query_execution_time: float = 5000.0  # milliseconds


@dataclass
class AnalyticsConfig:
    """Configuration for analytics features"""
    
    # Cache settings
    enable_caching: bool = True
    cache_size_mb: int = 100
    cache_compression: bool = True
    
    # Aggregation settings
    hourly_aggregation: bool = True
    daily_aggregation: bool = True
    weekly_aggregation: bool = True
    monthly_aggregation: bool = True
    
    # Trend analysis
    trend_window_hours: int = 24
    trend_sensitivity: float = 0.1  # 10% change threshold
    seasonal_adjustment: bool = True
    
    # Anomaly detection
    anomaly_sensitivity: float = 2.0  # Standard deviations
    anomaly_window_hours: int = 168  # 1 week
    anomaly_min_samples: int = 100
    
    # Predictive analytics
    prediction_horizon_hours: int = 24
    prediction_confidence_threshold: float = 0.7
    prediction_models: List[str] = None
    
    # Geographic analytics
    enable_ip_geolocation: bool = False  # Requires external service
    geolocation_cache_hours: int = 24
    
    def __post_init__(self):
        if self.prediction_models is None:
            self.prediction_models = ["linear", "moving_average"]


class MonitoringConfigManager:
    """Manager for monitoring configuration"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self._monitoring_config = MonitoringConfig()
        self._performance_thresholds = PerformanceThresholds()
        self._analytics_config = AnalyticsConfig()
    
    @property
    def monitoring(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        return self._monitoring_config
    
    @property
    def performance(self) -> PerformanceThresholds:
        """Get performance thresholds"""
        return self._performance_thresholds
    
    @property
    def analytics(self) -> AnalyticsConfig:
        """Get analytics configuration"""
        return self._analytics_config
    
    def update_monitoring_config(self, **kwargs):
        """Update monitoring configuration"""
        for key, value in kwargs.items():
            if hasattr(self._monitoring_config, key):
                setattr(self._monitoring_config, key, value)
    
    def update_performance_thresholds(self, **kwargs):
        """Update performance thresholds"""
        for key, value in kwargs.items():
            if hasattr(self._performance_thresholds, key):
                setattr(self._performance_thresholds, key, value)
    
    def update_analytics_config(self, **kwargs):
        """Update analytics configuration"""
        for key, value in kwargs.items():
            if hasattr(self._analytics_config, key):
                setattr(self._analytics_config, key, value)
    
    def get_config_dict(self) -> Dict:
        """Get all configuration as dictionary"""
        return {
            "monitoring": self._monitoring_config.__dict__,
            "performance": self._performance_thresholds.__dict__,
            "analytics": self._analytics_config.__dict__
        }
    
    def load_from_dict(self, config_dict: Dict):
        """Load configuration from dictionary"""
        if "monitoring" in config_dict:
            for key, value in config_dict["monitoring"].items():
                if hasattr(self._monitoring_config, key):
                    setattr(self._monitoring_config, key, value)
        
        if "performance" in config_dict:
            for key, value in config_dict["performance"].items():
                if hasattr(self._performance_thresholds, key):
                    setattr(self._performance_thresholds, key, value)
        
        if "analytics" in config_dict:
            for key, value in config_dict["analytics"].items():
                if hasattr(self._analytics_config, key):
                    setattr(self._analytics_config, key, value)


# Global configuration manager instance
_config_manager = None

def get_monitoring_config() -> MonitoringConfigManager:
    """Get global monitoring configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MonitoringConfigManager()
    return _config_manager


def get_monitoring_settings() -> MonitoringConfig:
    """Get monitoring configuration"""
    return get_monitoring_config().monitoring


def get_performance_thresholds() -> PerformanceThresholds:
    """Get performance thresholds"""
    return get_monitoring_config().performance


def get_analytics_config() -> AnalyticsConfig:
    """Get analytics configuration"""
    return get_monitoring_config().analytics