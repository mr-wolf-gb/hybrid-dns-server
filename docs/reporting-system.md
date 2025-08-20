# DNS Server Reporting System

The DNS Server includes a comprehensive reporting and analytics system that provides automated report generation, customizable templates, scheduling capabilities, and advanced analytics.

## Features

### 1. Report Templates

The system includes several built-in report templates:

- **DNS Zone Summary**: Comprehensive overview of DNS zones and their statistics
- **Security Report**: RPZ statistics, threat detection, and blocked queries analysis
- **Performance Report**: DNS query performance metrics and forwarder statistics

#### Creating Custom Templates

Templates use Jinja2 syntax for dynamic content generation:

```jinja2
# {{ template_name }} Report
Generated: {{ report_date }}
Period: {{ start_date }} to {{ end_date }}

## Summary
- Total Zones: {{ total_zones }}
- Active Zones: {{ active_zones }}

## Zone Details
{% for zone in zones %}
### {{ zone.name }}
- Type: {{ zone.zone_type }}
- Status: {{ zone.status }}
- Records: {{ zone.record_count }}
{% endfor %}
```

### 2. Report Scheduling

Automated report generation with configurable schedules:

- **Frequencies**: Daily, Weekly, Monthly
- **Recipients**: Multiple email recipients per schedule
- **Parameters**: Customizable parameters for each scheduled report
- **Enable/Disable**: Toggle schedules on/off

### 3. Export Formats

Reports can be exported in multiple formats:

- **HTML**: Formatted web-ready reports
- **PDF**: Professional document format
- **CSV**: Data for spreadsheet analysis
- **JSON**: Machine-readable structured data
- **TXT**: Plain text format

### 4. Analytics Dashboard

Real-time analytics and insights:

- **Query Trends**: Time-series analysis of DNS queries
- **Top Domains**: Most frequently queried domains
- **Client Analytics**: Per-client query statistics
- **Performance Metrics**: Response times and success rates
- **Error Analysis**: Error patterns and troubleshooting data
- **Security Analytics**: Threat detection and blocking statistics

## API Endpoints

### Templates

- `GET /api/reports/templates` - List all templates
- `POST /api/reports/templates` - Create new template
- `GET /api/reports/templates/{id}` - Get specific template
- `PUT /api/reports/templates/{id}` - Update template
- `DELETE /api/reports/templates/{id}` - Delete template

### Schedules

- `GET /api/reports/schedules` - List all schedules
- `POST /api/reports/schedules` - Create new schedule
- `GET /api/reports/schedules/{id}` - Get specific schedule
- `PUT /api/reports/schedules/{id}` - Update schedule
- `DELETE /api/reports/schedules/{id}` - Delete schedule
- `POST /api/reports/schedules/{id}/run` - Run schedule manually

### Report Generation

- `POST /api/reports/generate` - Generate report
- `POST /api/reports/export` - Export report in specified format

### Analytics

- `GET /api/reports/analytics/trends` - Query trends
- `GET /api/reports/analytics/top-domains` - Top queried domains
- `GET /api/reports/analytics/clients` - Client analytics
- `GET /api/reports/analytics/performance` - Performance metrics
- `GET /api/reports/analytics/errors` - Error analysis
- `GET /api/reports/analytics/security` - Security analytics
- `GET /api/reports/analytics/zones` - Zone analytics
- `GET /api/reports/analytics/insights` - Automated insights

## Usage Examples

### Creating a Report Template

```python
template_data = {
    "template_id": "custom_summary",
    "name": "Custom DNS Summary",
    "description": "Custom report for DNS overview",
    "template_content": """
# DNS Summary Report
Generated: {{ report_date }}

## Statistics
- Total Queries: {{ total_queries }}
- Success Rate: {{ success_rate }}%
    """,
    "parameters": {
        "include_details": True,
        "time_range": "24h"
    }
}

response = requests.post('/api/reports/templates', json=template_data)
```

### Scheduling a Report

```python
schedule_data = {
    "schedule_id": "weekly_summary",
    "template_id": "zone_summary",
    "name": "Weekly DNS Zone Report",
    "frequency": "weekly",
    "parameters": {
        "include_inactive": False,
        "top_zones_limit": 20
    },
    "recipients": ["admin@company.com", "ops@company.com"],
    "enabled": True
}

response = requests.post('/api/reports/schedules', json=schedule_data)
```

### Generating a Report

```python
report_data = {
    "template_id": "security_report",
    "parameters": {
        "include_threat_details": True,
        "recent_threats_days": 7
    },
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-07T23:59:59Z"
}

response = requests.post('/api/reports/generate', json=report_data)
```

### Exporting a Report

```python
export_data = {
    "template_id": "performance_report",
    "format": "pdf",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-07T23:59:59Z"
}

response = requests.post('/api/reports/export', json=export_data)
# Response will be a downloadable file
```

## Frontend Components

### Reports Page

The main reports interface provides:

- **Templates Tab**: Manage report templates
- **Schedules Tab**: Configure automated reporting
- **Analytics Tab**: Interactive analytics dashboard

### Report Generation Modal

Interactive report generation with:

- Template selection
- Parameter configuration
- Date range selection
- Real-time preview
- Export options

### Analytics Dashboard

Comprehensive analytics with:

- Interactive charts and graphs
- Key performance indicators
- Automated insights
- Customizable date ranges

## Configuration

### Environment Variables

```bash
# Report scheduling interval (seconds)
REPORT_SCHEDULER_INTERVAL=300

# Default report retention (days)
REPORT_RETENTION_DAYS=90

# Maximum report size (MB)
MAX_REPORT_SIZE_MB=50
```

### Background Tasks

The reporting system runs background tasks for:

- **Scheduled Reports**: Automatic execution of scheduled reports
- **Report Cleanup**: Removal of old report files
- **Analytics Processing**: Real-time analytics data processing

## Security Considerations

- **Authentication**: All reporting endpoints require authentication
- **Authorization**: Role-based access to sensitive reports
- **Data Privacy**: Reports respect user permissions and data access rules
- **Rate Limiting**: API endpoints are rate-limited to prevent abuse

## Monitoring and Troubleshooting

### Logging

The reporting system logs:

- Report generation events
- Schedule execution
- Export operations
- Analytics processing
- Error conditions

### Health Checks

Monitor reporting system health:

- Template validation
- Schedule execution status
- Analytics data freshness
- Export functionality

### Common Issues

1. **Report Generation Failures**
   - Check template syntax
   - Verify data availability
   - Review parameter values

2. **Schedule Not Running**
   - Verify schedule is enabled
   - Check background task service
   - Review recipient email addresses

3. **Analytics Data Missing**
   - Ensure monitoring service is running
   - Check database connectivity
   - Verify log collection

## Performance Optimization

- **Caching**: Analytics data is cached for improved performance
- **Pagination**: Large datasets are paginated
- **Async Processing**: Report generation runs asynchronously
- **Resource Limits**: Memory and CPU usage are monitored

## Future Enhancements

Planned improvements include:

- **Dashboard Widgets**: Embeddable report widgets
- **Custom Visualizations**: User-defined charts and graphs
- **Report Sharing**: Secure report sharing with external users
- **Advanced Filtering**: More sophisticated data filtering options
- **Machine Learning**: Predictive analytics and anomaly detection