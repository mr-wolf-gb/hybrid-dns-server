# Enhanced DNS Monitoring & Analytics

This document describes the enhanced monitoring service with performance optimizations, comprehensive analytics, and trend analysis capabilities.

## Overview

The enhanced monitoring service provides:

- **Real-time Performance Monitoring**: Live metrics with sub-second updates
- **Advanced Analytics**: Comprehensive query analysis and insights
- **Trend Analysis**: Historical patterns and predictive analytics
- **Anomaly Detection**: Automated detection of unusual patterns
- **Performance Optimization**: Batch processing and intelligent caching

## Key Features

### 1. Performance Optimizations

#### Batch Processing
- **Metrics Buffer**: Collects metrics in memory before batch database writes
- **Configurable Batch Size**: Optimizes database performance based on system resources
- **Timeout-based Flushing**: Ensures timely data processing even with low query volumes

#### Intelligent Caching
- **Analytics Cache**: Caches expensive analytics queries with configurable TTL
- **Real-time Metrics**: In-memory counters for instant dashboard updates
- **Cache Invalidation**: Smart cache clearing based on data freshness

#### Database Optimizations
- **Performance Indexes**: Specialized indexes for analytics queries
- **Query Optimization**: Efficient SQL queries with proper indexing
- **Connection Pooling**: Optimized database connection management

### 2. Comprehensive Analytics

#### Query Analytics
```typescript
interface QueryAnalytics {
  query_volume: {
    hourly_breakdown: Array<HourlyData>;
    query_type_distribution: Array<QueryTypeData>;
  };
  domain_analytics: {
    top_domains: Array<DomainData>;
    tld_distribution: Array<TLDData>;
  };
  client_analytics: {
    top_clients: Array<ClientData>;
    hourly_activity: Array<ActivityData>;
  };
  response_time_analytics: {
    overall_stats: ResponseTimeStats;
    by_query_type: Array<QueryTypeStats>;
  };
}
```

#### Performance Metrics
- **Queries Per Second (QPS)**: Real-time and historical query rates
- **Response Time Analysis**: Average, median, P95, P99 response times
- **Error Rate Tracking**: DNS resolution errors and timeouts
- **Cache Hit Rates**: DNS cache performance metrics
- **Block Rate Analysis**: Security filtering effectiveness

### 3. Trend Analysis & Predictions

#### Trend Detection
- **Linear Trend Analysis**: Identifies increasing, decreasing, or stable patterns
- **Seasonal Adjustments**: Accounts for daily and weekly patterns
- **Anomaly Detection**: Statistical analysis to identify unusual behavior

#### Predictive Analytics
```python
@dataclass
class Predictions:
    next_hour_queries: PredictionData
    threat_level: ThreatLevelData
    resource_usage: ResourcePrediction
```

#### Trend Visualization
- **Hourly Trends**: Query volume and response time patterns
- **Daily Aggregations**: Long-term trend analysis
- **Comparative Analysis**: Period-over-period comparisons

### 4. Anomaly Detection

#### Detection Algorithms
- **Statistical Analysis**: Standard deviation-based anomaly detection
- **Threshold Monitoring**: Configurable thresholds for key metrics
- **Pattern Recognition**: Identifies unusual query patterns

#### Alert Types
- **High Query Volume**: Unusual spikes in DNS queries
- **Response Time Anomalies**: Degraded DNS performance
- **Error Rate Spikes**: Increased DNS resolution failures
- **Threat Pattern Changes**: Unusual security event patterns

## API Endpoints

### Performance Metrics
```http
GET /api/analytics/performance?hours=24
```
Returns comprehensive performance metrics for the specified time period.

### Real-time Analytics
```http
GET /api/analytics/real-time
```
Returns current real-time statistics and metrics.

### Query Analytics
```http
GET /api/analytics/query-analytics?hours=24&use_cache=true
```
Returns detailed query analysis with caching support.

### Trend Analysis
```http
GET /api/analytics/trends?days=30
```
Returns trend analysis and predictions.

### Anomaly Detection
```http
GET /api/analytics/anomalies
```
Returns current anomaly detection results.

### Top Domains Analytics
```http
GET /api/analytics/top-domains?hours=24&limit=50
```
Returns top queried domains with detailed analytics.

### Client Analytics
```http
GET /api/analytics/client-analytics?hours=24&limit=50
```
Returns detailed client behavior analysis.

### Response Time Analytics
```http
GET /api/analytics/response-time-analytics?hours=24
```
Returns comprehensive response time analysis.

### Threat Analytics
```http
GET /api/analytics/threat-analytics?days=7&category=malware
```
Returns threat detection and blocking analytics.

## Configuration

### Monitoring Configuration
```python
@dataclass
class MonitoringConfig:
    metrics_buffer_size: int = 2000
    batch_size: int = 100
    batch_timeout: float = 5.0
    thread_pool_workers: int = 4
    cache_ttl: int = 300
    real_time_update_interval: int = 10
```

### Performance Thresholds
```python
@dataclass
class PerformanceThresholds:
    max_queries_per_second: float = 1000.0
    max_avg_response_time: float = 100.0
    max_p95_response_time: float = 500.0
    max_cpu_usage: float = 80.0
    max_memory_usage: float = 85.0
```

### Analytics Configuration
```python
@dataclass
class AnalyticsConfig:
    enable_caching: bool = True
    cache_size_mb: int = 100
    trend_window_hours: int = 24
    anomaly_sensitivity: float = 2.0
    prediction_horizon_hours: int = 24
```

## Performance Optimization

### Database Indexes
The system creates specialized indexes for optimal query performance:

```sql
-- DNS logs performance indexes
CREATE INDEX idx_dns_logs_timestamp_client ON dns_logs(timestamp, client_ip);
CREATE INDEX idx_dns_logs_domain_blocked ON dns_logs(query_domain, blocked);
CREATE INDEX idx_dns_logs_response_time ON dns_logs(response_time) WHERE response_time > 0;
CREATE INDEX idx_dns_logs_hourly_stats ON dns_logs(DATE_TRUNC('hour', timestamp), blocked);

-- Analytics composite indexes
CREATE INDEX idx_dns_logs_analytics ON dns_logs(timestamp, client_ip, query_domain, blocked);
CREATE INDEX idx_dns_logs_threat_analysis ON dns_logs(timestamp, blocked, rpz_zone) WHERE blocked = true;
```

### Memory Management
- **Buffer Management**: Configurable buffer sizes based on system resources
- **Cache Limits**: Automatic cache trimming to prevent memory bloat
- **Data Retention**: Automated cleanup of old data

### Batch Processing
- **Intelligent Batching**: Adapts batch sizes based on query volume
- **Timeout Handling**: Ensures data is processed even during low activity
- **Error Recovery**: Fallback to individual inserts on batch failures

## Monitoring Dashboard

### Real-time Metrics
- **Live Updates**: Auto-refreshing dashboard with 10-second intervals
- **Key Performance Indicators**: QPS, response time, block rate, buffer size
- **Visual Indicators**: Trend arrows and color-coded alerts

### Analytics Views
- **Overview Tab**: Query volume charts and top domains
- **Performance Tab**: Detailed performance metrics and query type distribution
- **Trends Tab**: Trend analysis and predictions
- **Analytics Tab**: Client analysis and threat categories

### Interactive Features
- **Time Range Selection**: 1 hour to 7 days
- **Auto-refresh Toggle**: Enable/disable automatic updates
- **Cache Management**: Manual cache clearing
- **Data Export**: JSON and CSV export formats

## Optimization Script

The `scripts/optimize_monitoring.py` script provides:

### Database Optimization
- **Index Creation**: Creates performance-optimized indexes
- **Table Analysis**: Updates query planner statistics
- **Vacuum Operations**: Reclaims database space

### Configuration Tuning
- **Resource-based Optimization**: Adjusts settings based on system resources
- **Performance Benchmarking**: Tests query performance
- **Recommendation Engine**: Suggests optimizations

### Performance Reporting
- **Comprehensive Reports**: System info, database stats, performance metrics
- **Benchmark Results**: Query execution times and recommendations
- **Configuration Summary**: Current optimization settings

## Best Practices

### Performance
1. **Regular Optimization**: Run optimization script weekly
2. **Monitor Buffer Sizes**: Adjust based on query volume
3. **Cache Management**: Clear cache after configuration changes
4. **Index Maintenance**: Monitor index usage and effectiveness

### Analytics
1. **Time Range Selection**: Use appropriate time ranges for analysis
2. **Cache Utilization**: Enable caching for frequently accessed data
3. **Trend Analysis**: Review trends regularly for capacity planning
4. **Anomaly Response**: Investigate anomalies promptly

### Monitoring
1. **Dashboard Usage**: Use real-time dashboard for operational monitoring
2. **Alert Configuration**: Set appropriate thresholds for your environment
3. **Data Retention**: Configure retention based on compliance requirements
4. **Export Capabilities**: Regular data exports for external analysis

## Troubleshooting

### Performance Issues
- **High Response Times**: Check database indexes and query optimization
- **Memory Usage**: Adjust buffer sizes and cache limits
- **CPU Usage**: Reduce thread pool workers or batch processing frequency

### Data Issues
- **Missing Data**: Check monitoring service status and log files
- **Inconsistent Metrics**: Clear analytics cache and restart service
- **Database Errors**: Review database logs and connection settings

### Dashboard Issues
- **Loading Problems**: Check API endpoint availability
- **Outdated Data**: Verify auto-refresh settings and cache status
- **Export Failures**: Check user permissions and data size limits

## Future Enhancements

### Planned Features
- **Machine Learning**: Advanced anomaly detection using ML algorithms
- **Geographic Analytics**: IP-based geographic analysis
- **Custom Dashboards**: User-configurable dashboard layouts
- **Advanced Predictions**: Multi-step ahead forecasting

### Integration Opportunities
- **External Monitoring**: Integration with Prometheus/Grafana
- **SIEM Integration**: Security event forwarding
- **Alerting Systems**: Integration with PagerDuty, Slack, etc.
- **Reporting Tools**: Automated report generation and distribution