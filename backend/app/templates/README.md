# DNS Zone Template System

This directory contains Jinja2 templates for generating BIND9 DNS configuration files. The templates use custom filters and variables to provide flexible and maintainable DNS zone file generation.

## Available Templates

### Zone Templates (`zones/`)
- `master.j2` - Master (authoritative) zone template with comprehensive record support
- `reverse.j2` - Reverse DNS zone template for PTR records
- `slave.j2` - Slave zone template for secondary DNS servers

### Configuration Templates
- `zone_file.j2` - Generic zone file template
- `forwarder_config.j2` - Forwarder configuration template
- `slave_zone.j2` - Slave zone configuration template

### RPZ Templates

#### General RPZ Templates
- `rpz_zone.j2` - General Response Policy Zone template
- `rpz_category.j2` - Category-specific RPZ template
- `rpz_policy.j2` - RPZ policy configuration template
- `rpz_master.j2` - Master RPZ zone template
- `rpz_custom_rules.j2` - Custom RPZ rules template
- `rpz_threat_feed.j2` - Threat feed RPZ template
- `rpz_config.j2` - Complete RPZ configuration
- `rpz_rule.j2` - Single RPZ rule template

#### Category-Specific RPZ Templates
- `rpz_malware.j2` - Malware protection with threat intelligence integration
- `rpz_phishing.j2` - Phishing protection with categorized threat types
- `rpz_safesearch.j2` - SafeSearch enforcement for major search engines
- `rpz_social_media.j2` - Social media blocking with granular controls
- `rpz_adult.j2` - Adult content filtering with configurable strictness levels
- `rpz_gambling.j2` - Gambling site blocking with category-specific rules
- `rpz_streaming.j2` - Streaming media blocking for bandwidth management
- `rpz_custom.j2` - Custom user-defined rules with advanced RPZ actions

### Template Selection Helper
- `template_mapping.py` - Automatic template selection and configuration for RPZ categories

## Category-Specific Template Features

The category-specific RPZ templates provide specialized functionality for different types of content filtering:

### Security Templates
- **Malware Protection** (`rpz_malware.j2`): Categorizes threats by type (C2, exploit kits, ransomware), integrates threat intelligence feeds, supports confidence scoring
- **Phishing Protection** (`rpz_phishing.j2`): Organizes by attack type (credential harvesting, brand impersonation, BEC, typosquatting), includes common target documentation

### Content Filtering Templates
- **Adult Content** (`rpz_adult.j2`): Configurable filter levels (Basic/Moderate/Strict), separate controls for different content types, commercial filter integration
- **Gambling Blocking** (`rpz_gambling.j2`): Comprehensive gambling categories, policy options (complete block, licensed only), addiction prevention resources
- **SafeSearch Enforcement** (`rpz_safesearch.j2`): Major search engine support, regional domain coverage, custom redirect options

### Productivity Templates
- **Social Media** (`rpz_social_media.j2`): Granular platform controls, business exception handling, time-based restriction support
- **Streaming Media** (`rpz_streaming.j2`): Bandwidth management focus, platform categorization, company-approved streaming options

### Custom Templates
- **Custom Rules** (`rpz_custom.j2`): All RPZ actions supported, rule categorization, temporary rules with expiration, wildcard support

## Template Variables

### Zone Object (`zone`)
The main zone object contains the following attributes:
- `zone.name` - Zone domain name
- `zone.zone_type` - Zone type (master, slave, forward)
- `zone.serial` - Zone serial number
- `zone.refresh` - SOA refresh interval (seconds)
- `zone.retry` - SOA retry interval (seconds)
- `zone.expire` - SOA expire time (seconds)
- `zone.minimum` - SOA minimum TTL (seconds)
- `zone.email` - SOA responsible email address
- `zone.description` - Zone description
- `zone.is_active` - Zone active status
- `zone.created_at` - Zone creation timestamp
- `zone.updated_at` - Zone last update timestamp

### DNS Records (`records`)
Array of DNS record objects with the following attributes:
- `record.name` - Record name
- `record.record_type` - DNS record type (A, AAAA, CNAME, MX, etc.)
- `record.value` - Record value/target
- `record.ttl` - Record TTL (optional)
- `record.priority` - Record priority (MX, SRV records)
- `record.weight` - Record weight (SRV records)
- `record.port` - Record port (SRV records)
- `record.is_active` - Record active status

## Custom Filters

### DNS-Specific Filters
- `ensure_trailing_dot` - Ensures domain names end with a dot
- `format_email_for_soa` - Converts email to SOA format (@ becomes .)
- `rpz_format_domain` - Formats domains for RPZ zone files
- `normalize_domain` - Normalizes domain names (lowercase, no protocols)
- `is_wildcard` - Checks if domain is a wildcard (*.example.com)

### Formatting Filters
- `format_ttl` - Formats TTL values with human-readable comments
- `format_serial` - Formats serial numbers with date information
- `format_duration` - Converts seconds to human-readable duration
- `format_mx_priority` - Formats MX record priority with validation
- `format_srv_record` - Formats complete SRV record string
- `escape_txt_record` - Properly escapes TXT record content
- `format_comment` - Formats comments for zone files

### Validation Filters
- `validate_ip` - Validates IP addresses (returns boolean)
- `reverse_ip` - Converts IP to reverse DNS format

## Global Functions

### Date/Time Functions
- `now()` - Current local datetime
- `utcnow()` - Current UTC datetime
- `format_timestamp(dt, format)` - Format timestamp with custom format

### DNS Utility Functions
- `generate_serial()` - Generate new serial number in YYYYMMDDNN format
- `default_ttl()` - Get default TTL value (3600 seconds)
- `get_zone_type_description(type)` - Get human-readable zone type description
- `get_record_type_description(type)` - Get human-readable record type description

## Usage Examples

### Basic Zone File Generation
```jinja2
; Zone: {{ zone.name }}
; Type: {{ get_zone_type_description(zone.zone_type) }}
; Serial: {{ zone.serial | format_serial }}
; Updated: {{ format_timestamp(zone.updated_at) }}

$TTL {{ zone.minimum | format_duration }}
$ORIGIN {{ zone.name | ensure_trailing_dot }}

@	IN	SOA	{{ zone.name | ensure_trailing_dot }} {{ zone.email | format_email_for_soa }} (
		{{ zone.serial | format_serial }}
		{{ zone.refresh | format_ttl }}
		{{ zone.retry | format_ttl }}
		{{ zone.expire | format_ttl }}
		{{ zone.minimum | format_ttl }}
		)
```

### Record Formatting
```jinja2
{% for record in records %}
{% if record.is_active %}
{{ "%-20s"|format(record.name) }}	{{ record.ttl | format_ttl }}	IN	{{ record.record_type }}	
{%- if record.record_type == 'MX' -%}
	{{ record.priority | format_mx_priority }}	{{ record.value | ensure_trailing_dot }}
{%- elif record.record_type == 'SRV' -%}
	{{ record | format_srv_record }}
{%- elif record.record_type == 'TXT' -%}
	{{ record.value | escape_txt_record }}
{%- else -%}
	{{ record.value | ensure_trailing_dot if record.record_type in ['CNAME', 'NS', 'PTR'] else record.value }}
{%- endif %}
{% endif %}
{% endfor %}
```

### Conditional Logic
```jinja2
{% if zone.zone_type == 'master' %}
; This is an authoritative master zone
{% elif zone.zone_type == 'slave' %}
; This is a slave zone, masters: {{ zone.master_servers | join(', ') }}
{% endif %}

{% if records %}
; Total records: {{ records | selectattr('is_active') | list | length }}
{% else %}
; No records defined for this zone
{% endif %}
```

### Record Grouping and Sorting
```jinja2
{% set a_records = records | selectattr('record_type', 'equalto', 'A') | selectattr('is_active') | sort(attribute='name') %}
{% set mx_records = records | selectattr('record_type', 'equalto', 'MX') | selectattr('is_active') | sort(attribute='priority') %}

{% if a_records %}
; A Records ({{ a_records | length }})
{% for record in a_records %}
{{ "%-20s"|format(record.name) }}	{{ record.ttl | format_ttl }}	IN	A	{{ record.value }}
{% endfor %}
{% endif %}
```

## Template Best Practices

1. **Always use filters for DNS-specific formatting**
   - Use `ensure_trailing_dot` for domain names in NS, CNAME, MX, SRV, PTR records
   - Use `format_email_for_soa` for SOA email addresses
   - Use `format_ttl` for TTL values to include human-readable comments

2. **Include comprehensive comments**
   - Document zone purpose and configuration
   - Include generation timestamp and template variables
   - Add record type descriptions and statistics

3. **Handle edge cases**
   - Check for empty or null values
   - Provide sensible defaults
   - Validate record-specific requirements

4. **Organize records logically**
   - Group by record type
   - Sort within groups (by name, priority, etc.)
   - Separate active and inactive records

5. **Use consistent formatting**
   - Align columns for readability
   - Use consistent spacing and indentation
   - Include helpful inline comments

## Error Handling

Templates should handle common error conditions gracefully:
- Missing or null values
- Invalid record data
- Empty record sets
- Malformed domain names
- Invalid IP addresses

Use conditional blocks and default values to ensure templates always generate valid BIND9 configuration files.