# Threat Feed Templates Documentation

This document describes the specialized threat feed templates available in the Hybrid DNS Server for generating RPZ zone files from external threat intelligence feeds.

## Overview

The threat feed template system provides specialized Jinja2 templates for different types of threat intelligence feeds. Each template is optimized for specific threat categories and provides appropriate formatting, categorization, and metadata for that threat type.

## Available Threat Feed Templates

### 1. Malware Threat Feed Template (`rpz_threat_feed_malware.j2`)

**Purpose**: Specialized template for malware threat intelligence feeds
**Zone Prefix**: `rpz.malware`
**TTL**: 60 seconds (fast updates for critical threats)
**Update Frequency**: Hourly

**Threat Categories Supported**:
- Ransomware (highest priority)
- Botnet/C2 servers
- Trojans
- Viruses
- General malware

**Special Features**:
- Prioritized threat categorization
- IOC (Indicator of Compromise) tracking
- Confidence scoring
- Threat family identification
- Severity level indicators

**Template Variables**:
```python
{
    'threat_categories': ['malware', 'ransomware', 'botnet', 'trojan', 'virus'],
    'update_frequency': 'hourly',
    'threat_level': 'high',
    'ttl': 60
}
```

### 2. Phishing Threat Feed Template (`rpz_threat_feed_phishing.j2`)

**Purpose**: Specialized template for phishing and brand impersonation feeds
**Zone Prefix**: `rpz.phishing`
**TTL**: 60 seconds (fast updates for active campaigns)
**Update Frequency**: Hourly

**Threat Categories Supported**:
- Banking/Financial phishing (highest priority)
- Cryptocurrency phishing
- Government impersonation
- Email provider phishing
- E-commerce phishing
- Social media phishing

**Special Features**:
- Target brand identification
- Phishing technique classification
- Campaign tracking
- Confidence scoring
- Target type categorization

**Template Variables**:
```python
{
    'threat_categories': ['phishing', 'brand_impersonation', 'credential_harvesting'],
    'update_frequency': 'hourly',
    'threat_level': 'high',
    'ttl': 60
}
```

### 3. Adult Content Threat Feed Template (`rpz_threat_feed_adult.j2`)

**Purpose**: Specialized template for adult content filtering feeds
**Zone Prefix**: `rpz.adult`
**TTL**: 300 seconds (moderate updates)
**Update Frequency**: Daily

**Content Categories Supported**:
- Explicit adult content (strict filtering)
- Adult dating sites
- Adult social/chat platforms
- Adult advertising networks
- Mature content

**Special Features**:
- Content rating classification
- Filter level indicators
- Maturity level assessment
- Content type categorization
- Platform type identification

**Template Variables**:
```python
{
    'content_categories': ['explicit', 'dating', 'mature', 'advertising'],
    'update_frequency': 'daily',
    'filter_level': 'strict',
    'ttl': 300
}
```

### 4. Social Media Threat Feed Template (`rpz_threat_feed_social_media.j2`)

**Purpose**: Specialized template for social media platform filtering
**Zone Prefix**: `rpz.social-media`
**TTL**: 300 seconds (moderate updates)
**Update Frequency**: Daily

**Platform Categories Supported**:
- Major social networks (high productivity impact)
- Content sharing platforms
- Messaging platforms
- Social gaming platforms
- Regional social networks
- Professional networks (lower impact)

**Special Features**:
- Productivity impact assessment
- Platform type classification
- User base indicators
- Business relevance scoring
- Regional platform identification

**Template Variables**:
```python
{
    'platform_categories': ['major_social', 'messaging', 'content_sharing', 'professional'],
    'update_frequency': 'daily',
    'productivity_impact': 'high',
    'ttl': 300
}
```

### 5. Gambling Threat Feed Template (`rpz_threat_feed_gambling.j2`)

**Purpose**: Specialized template for gambling and wagering site filtering
**Zone Prefix**: `rpz.gambling`
**TTL**: 300 seconds (moderate updates)
**Update Frequency**: Daily

**Gambling Categories Supported**:
- Online casinos (high risk)
- Sports betting
- Cryptocurrency gambling
- Poker gaming
- Lottery games
- Fantasy sports (medium risk)
- Gambling affiliates

**Special Features**:
- Risk level assessment
- Gambling type classification
- License jurisdiction tracking
- Legal compliance notices
- Affiliate network identification

**Template Variables**:
```python
{
    'gambling_categories': ['casino', 'sports_betting', 'poker', 'lottery', 'crypto_gambling'],
    'update_frequency': 'daily',
    'risk_level': 'high',
    'ttl': 300
}
```

### 6. Custom Threat Feed Template (`rpz_threat_feed_custom.j2`)

**Purpose**: Specialized template for organization-specific custom feeds
**Zone Prefix**: `rpz.custom`
**TTL**: 300 seconds (frequent updates for custom rules)
**Update Frequency**: Hourly

**Custom Categories Supported**:
- Incident response blocks (critical priority)
- Security blocks
- Compliance blocks
- Policy blocks
- Business blocks
- Temporary blocks (with expiry tracking)

**Special Features**:
- Priority-based categorization
- Incident tracking
- Expiry date management
- Policy version tracking
- Compliance authority references
- Temporary rule management

**Template Variables**:
```python
{
    'custom_categories': ['policy', 'incident', 'compliance', 'business', 'security'],
    'update_frequency': 'hourly',
    'priority_level': 'medium',
    'ttl': 300
}
```

## Template Selection Logic

The system automatically selects the appropriate template based on the threat feed type:

```python
from backend.app.templates.template_mapping import get_threat_feed_template_for_type

# Get template configuration for a specific feed type
template_config = get_threat_feed_template_for_type('malware')
template_name = template_config['template']  # 'rpz_threat_feed_malware.j2'
```

## Template Variables

All threat feed templates support the following common variables:

### Required Variables
- `feed_name`: Name of the threat feed
- `feed_type`: Type of threat feed (malware, phishing, etc.)
- `rules`: List of threat intelligence rules
- `generated_at`: Timestamp when the zone file was generated

### Optional Variables
- `feed_source`: Source of the threat feed (external, internal, etc.)
- `feed_url`: URL of the threat feed
- `feed_description`: Description of the threat feed
- `feed_last_updated`: Last update timestamp
- `feed_next_update`: Next scheduled update
- `feed_update_frequency`: Update frequency description
- `feed_reliability`: Reliability level of the feed
- `active_rules_count`: Number of active rules
- `ttl`: Time-to-live for DNS records
- `primary_ns`: Primary name server
- `admin_email`: Administrator email
- `serial`: Zone serial number

### Rule Object Properties

Each rule in the `rules` list can contain:

**Common Properties**:
- `domain`: The domain to block/redirect
- `is_active`: Whether the rule is active
- `confidence_score`: Confidence level (0-100)
- `first_seen`: First detection date
- `threat_description`: Description of the threat
- `ioc_id`: Indicator of Compromise ID

**Malware-Specific Properties**:
- `threat_type`: Type of malware (ransomware, botnet, etc.)
- `threat_category`: Category of threat
- `ransomware_family`: Ransomware family name
- `botnet_family`: Botnet family name
- `c2_type`: Command and control type
- `severity`: Severity level

**Phishing-Specific Properties**:
- `target_brand`: Brand being impersonated
- `target_type`: Type of target (banking, email, etc.)
- `phishing_type`: Type of phishing attack
- `phishing_technique`: Technique used

**Content-Specific Properties**:
- `content_type`: Type of content
- `content_category`: Content category
- `content_rating`: Content rating
- `maturity_level`: Maturity level

## Usage Examples

### Using Malware Template
```python
from jinja2 import Environment, FileSystemLoader
from backend.app.templates.template_mapping import get_threat_feed_template_variables

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('backend/app/templates'))

# Get template variables for malware feed
variables = get_threat_feed_template_variables('malware', {
    'feed_name': 'Malware Domain Blocklist',
    'feed_url': 'https://example.com/malware-domains.txt',
    'rules': malware_rules_list
})

# Render template
template = env.get_template('rpz_threat_feed_malware.j2')
zone_content = template.render(**variables)
```

### Custom Variables Override
```python
# Override default variables for specific needs
custom_vars = {
    'ttl': 30,  # Faster updates
    'feed_reliability': 'very_high',
    'threat_level': 'critical'
}

variables = get_threat_feed_template_variables('malware', custom_vars)
```

## Template Customization

### Adding New Threat Feed Types

1. Create a new template file (e.g., `rpz_threat_feed_newtype.j2`)
2. Add configuration to `THREAT_FEED_TEMPLATE_MAPPING` in `template_mapping.py`
3. Update the `FeedType` enum in `schemas/security.py`

### Modifying Existing Templates

Templates can be customized by:
- Adding new categorization logic
- Modifying comment formats
- Adjusting TTL values
- Adding new metadata fields

## Best Practices

### Template Design
- Use clear, descriptive comments
- Group rules by threat severity/type
- Include comprehensive metadata
- Provide fallback values for optional fields

### Performance Considerations
- Use appropriate TTL values for threat types
- Limit template complexity for large rule sets
- Consider caching for frequently used templates

### Security Considerations
- Validate all template variables
- Escape user-provided content
- Use secure default values
- Log template rendering errors

## Troubleshooting

### Common Issues

1. **Template Not Found**: Ensure template file exists and is properly named
2. **Variable Errors**: Check that all required variables are provided
3. **Rendering Errors**: Validate template syntax and variable types
4. **Performance Issues**: Consider template complexity and rule count

### Debugging

Enable template debugging:
```python
env = Environment(
    loader=FileSystemLoader('backend/app/templates'),
    undefined=jinja2.DebugUndefined
)
```

### Validation

Validate generated zone files:
```bash
named-checkzone example.rpz /path/to/generated/zone/file
```

## Integration with Threat Feed Service

The templates integrate with the `ThreatFeedService` for automatic zone file generation:

```python
from backend.app.services.threat_feed_service import ThreatFeedService
from backend.app.services.bind_service import BindService

# Update threat feed and generate zone file
threat_service = ThreatFeedService(db)
bind_service = BindService()

# Update feed from source
result = await threat_service.update_feed_from_source(feed)

# Generate zone file using appropriate template
await bind_service.generate_threat_feed_zone(feed, result.rules)
```

This documentation provides comprehensive guidance for using and customizing threat feed templates in the Hybrid DNS Server system.