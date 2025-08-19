# RPZ Statistics and Reporting Documentation

## Overview

The RPZ (Response Policy Zone) service now includes comprehensive statistics and reporting functionality to provide insights into DNS security rule management and effectiveness.

## New Features Added

### 1. Enhanced Statistics Methods

#### `get_comprehensive_statistics()`
Returns comprehensive statistics across all RPZ categories including:
- Overall rule counts and status
- Category-specific information
- Recent activity (last 30 days)
- Top blocked domains
- Generated timestamp

#### `get_activity_report(days=30)`
Provides activity analysis for a specified time period:
- Rules created and updated counts
- Daily activity breakdown
- Activity by category
- Time period summary

#### `get_effectiveness_report()`
Analyzes rule distribution and effectiveness:
- Activation rates
- Action distribution (block, redirect, passthru)
- Source distribution (manual, threat feeds)
- Category coverage percentages
- Protection ratios

#### `get_trend_analysis(days=90)`
Examines trends over time:
- Weekly rule creation trends
- Category-specific trends
- Growth rate calculations
- Trend direction analysis

#### `get_security_impact_report()`
Evaluates security protection coverage:
- Security category analysis (malware, phishing, adult)
- Threat feed coverage
- Overall security score (0-100)
- Protection level assessment
- Automated recommendations

### 2. Export and Reporting

#### `export_statistics_report(report_type, format)`
Exports any report type in specified format:
- Supported types: comprehensive, activity, effectiveness, trends, security
- Currently supports JSON format
- Includes export metadata

### 3. Enhanced Category Management

#### Category Status Tracking
- Real-time status monitoring (enabled/disabled/mixed/empty)
- Percentage calculations
- Rule count tracking

#### Bulk Category Operations
- Enable/disable entire categories
- Bulk rule categorization
- Error handling and reporting

## API Endpoints Added

### Statistics Endpoints

- `GET /api/rpz/statistics/comprehensive` - Comprehensive statistics
- `GET /api/rpz/reports/activity?days=30` - Activity report
- `GET /api/rpz/reports/effectiveness` - Effectiveness analysis
- `GET /api/rpz/reports/trends?days=90` - Trend analysis
- `GET /api/rpz/reports/security-impact` - Security impact assessment
- `GET /api/rpz/reports/export?report_type=comprehensive&format=json` - Export reports
- `GET /api/rpz/statistics/summary` - Quick statistics summary

### Enhanced Category Endpoints

- `GET /api/rpz/categories` - List all categories with statistics
- `GET /api/rpz/categories/{category}` - Detailed category information
- `GET /api/rpz/categories/{category}/status` - Category status
- `POST /api/rpz/categories/{category}/enable` - Enable category
- `POST /api/rpz/categories/{category}/disable` - Disable category

## Usage Examples

### Python Service Usage

```python
from app.services.rpz_service import RPZService

# Initialize service
rpz_service = RPZService(db)

# Get comprehensive statistics
stats = await rpz_service.get_comprehensive_statistics()
print(f"Total rules: {stats['overall']['total_rules']}")

# Generate activity report
activity = await rpz_service.get_activity_report(30)
print(f"Rules created last 30 days: {activity['summary']['rules_created']}")

# Get security impact
security = await rpz_service.get_security_impact_report()
print(f"Security score: {security['overall_metrics']['security_score']}")

# Export report
export_data = await rpz_service.export_statistics_report('comprehensive', 'json')
```

### API Usage

```bash
# Get comprehensive statistics
curl -X GET "http://localhost:8000/api/rpz/statistics/comprehensive" \
     -H "Authorization: Bearer YOUR_TOKEN"

# Get activity report for last 7 days
curl -X GET "http://localhost:8000/api/rpz/reports/activity?days=7" \
     -H "Authorization: Bearer YOUR_TOKEN"

# Export effectiveness report
curl -X GET "http://localhost:8000/api/rpz/reports/export?report_type=effectiveness&format=json" \
     -H "Authorization: Bearer YOUR_TOKEN"

# Get category status
curl -X GET "http://localhost:8000/api/rpz/categories/malware/status" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## Report Types and Data Structure

### Comprehensive Statistics
```json
{
  "overall": {
    "total_rules": 1500,
    "active_rules": 1450,
    "inactive_rules": 50,
    "rules_by_action": {"block": 1200, "redirect": 200, "passthru": 50},
    "rules_by_source": {"threat_feed": 1000, "manual": 450},
    "rules_by_category": {"malware": 800, "phishing": 400, "custom": 250}
  },
  "categories": [...],
  "recent_activity": {"rules_added_last_30_days": 150},
  "top_domains": [...],
  "generated_at": "2024-08-19T12:00:00Z"
}
```

### Activity Report
```json
{
  "period": {"days": 30, "start_date": "...", "end_date": "..."},
  "summary": {"rules_created": 150, "rules_updated": 25, "total_activity": 175},
  "daily_activity": [...],
  "activity_by_category": {"malware": 80, "phishing": 40, "custom": 30}
}
```

### Security Impact Report
```json
{
  "security_coverage": {
    "malware": {"total_rules": 800, "protection_level": "high"},
    "phishing": {"total_rules": 400, "protection_level": "medium"}
  },
  "overall_metrics": {
    "security_score": 75.5,
    "protection_level": "good"
  },
  "recommendations": [...]
}
```

## Performance Considerations

- Statistics queries are optimized with proper database indexing
- Large datasets are handled with pagination where appropriate
- Background processing for complex reports
- Caching recommendations for frequently accessed statistics

## Testing

The implementation includes comprehensive tests:
- `test_rpz_statistics.py` - Service-level testing
- `test_rpz_api_statistics.py` - API endpoint testing

Run tests with:
```bash
python test_rpz_statistics.py
python test_rpz_api_statistics.py
```

## Future Enhancements

Potential future improvements:
- Additional export formats (CSV, PDF)
- Scheduled report generation
- Email report delivery
- Advanced visualization data
- Historical trend comparison
- Custom report builders