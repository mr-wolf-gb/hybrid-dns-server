# RPZ Templates Documentation

This directory contains Jinja2 templates for generating Response Policy Zone (RPZ) configuration files for BIND9. These templates are used by the Hybrid DNS Server to create dynamic RPZ zones based on database content.

## Available RPZ Templates

### 1. `rpz_zone.j2` - General RPZ Zone Template
**Purpose**: General-purpose RPZ zone file template for basic RPZ zones.
**Use Case**: Standard RPZ zones with mixed rule types.
**Variables**:
- `rpz_zone`: Zone name
- `zone_description`: Description of the zone
- `rules`: List of RPZ rules
- `active_rules_count`: Number of active rules
- `ttl`: Zone TTL (default: 300)
- `primary_ns`: Primary name server
- `admin_email`: Administrator email

### 2. `rpz_category.j2` - Category-Specific RPZ Template
**Purpose**: Template for category-based RPZ zones (malware, phishing, adult content, etc.).
**Use Case**: Organized RPZ zones grouped by threat or content category.
**Variables**:
- `category`: Category name
- `category_info`: Category metadata (display_name, description)
- `rules_by_action`: Rules grouped by action type
- `active_rules_count`: Number of active rules

## Category-Specific Templates

### 3. `rpz_malware.j2` - Malware Protection Template
**Purpose**: Specialized template for malware and threat protection.
**Use Case**: Blocking malware, C2 servers, exploit kits, and ransomware domains.
**Variables**:
- `threat_sources`: List of threat intelligence sources
- `threat_feeds`: Active threat feed configurations
- `average_confidence`: Average confidence score of rules
- Rules categorized by: `c2`, `exploit`, `ransomware`, `malware`

### 4. `rpz_phishing.j2` - Phishing Protection Template
**Purpose**: Specialized template for phishing and credential theft protection.
**Use Case**: Blocking phishing sites, brand impersonation, and BEC domains.
**Variables**:
- `threat_sources`: List of phishing intelligence sources
- `threat_feeds`: Active phishing feed configurations
- Rules categorized by: `credential_harvest`, `brand_impersonation`, `bec`, `typosquatting`

### 5. `rpz_safesearch.j2` - SafeSearch Enforcement Template
**Purpose**: Template for enforcing safe search on popular search engines.
**Use Case**: Redirecting search engines to their SafeSearch-enabled versions.
**Variables**:
- `google_safesearch`: Enable Google SafeSearch (default: true)
- `youtube_safesearch`: Enable YouTube restricted mode (default: true)
- `bing_safesearch`: Enable Bing SafeSearch (default: true)
- `duckduckgo_safesearch`: Enable DuckDuckGo safe search (default: true)
- `yahoo_safesearch`: Enable Yahoo SafeSearch (default: true)
- `yandex_safesearch`: Enable Yandex SafeSearch (default: false)
- `custom_search_redirects`: Custom search engine redirections

### 6. `rpz_social_media.j2` - Social Media Blocking Template
**Purpose**: Template for blocking social media platforms and messaging services.
**Use Case**: Workplace productivity and bandwidth management.
**Variables**:
- `major_platforms`: Block major social networks (default: true)
- `professional_networks`: Block LinkedIn, Xing (default: false)
- `messaging_platforms`: Block WhatsApp, Telegram, Discord (default: true)
- `content_platforms`: Block Pinterest, Tumblr, Reddit (default: true)
- `regional_platforms`: Block regional platforms (default: false)
- `business_tools`: Block Slack, Teams (default: false)
- `block_target`: Target for blocked domains (default: '.')
- `redirect_page`: Company policy page URL

### 7. `rpz_adult.j2` - Adult Content Blocking Template
**Purpose**: Template for blocking adult and inappropriate content.
**Use Case**: Content filtering for workplace and family environments.
**Variables**:
- `filter_level`: Filtering strictness (Basic/Moderate/Strict)
- `block_dating`: Block dating sites (default: false)
- `common_adult_domains`: Include common adult domains (default: true)
- `content_filters`: Commercial content filtering services
- Rules categorized by: `explicit`, `dating`, `adult_social`, `mature`, `adult_ads`

### 8. `rpz_gambling.j2` - Gambling Blocking Template
**Purpose**: Template for blocking gambling and betting websites.
**Use Case**: Compliance with gambling policies and addiction prevention.
**Variables**:
- `gambling_policy`: Blocking policy (Complete Block/Licensed Only/Regional)
- `online_casinos`: Block casino sites (default: true)
- `sports_betting`: Block sports betting (default: true)
- `poker_gaming`: Block poker sites (default: true)
- `lottery_games`: Block lottery sites (default: true)
- `crypto_gambling`: Block crypto gambling (default: true)
- `fantasy_sports`: Block fantasy sports (default: false)
- `high_risk_trading`: Block binary options/forex (default: false)

### 9. `rpz_streaming.j2` - Streaming Media Blocking Template
**Purpose**: Template for blocking streaming video and audio platforms.
**Use Case**: Bandwidth management and workplace productivity.
**Variables**:
- `streaming_policy`: Purpose of blocking (Bandwidth Management/Productivity)
- `video_streaming`: Block video streaming services (default: true)
- `youtube_blocking`: Block YouTube (default: true)
- `music_streaming`: Block music streaming (default: true)
- `live_streaming`: Block live streaming platforms (default: true)
- `podcast_platforms`: Block podcast platforms (default: false)
- `international_streaming`: Block international services (default: false)
- `company_streaming`: Company-approved streaming configuration

### 10. `rpz_custom.j2` - Custom Rules Template
**Purpose**: Template for user-defined custom RPZ rules and policies.
**Use Case**: Organization-specific rules, exceptions, and business requirements.
**Variables**:
- `rule_categories`: Custom rule categories
- `temporary_rules`: Time-limited rules with expiration
- `block_target`: Default block target
- Rules support all RPZ actions: `block`, `redirect`, `passthru`, `nxdomain`, `nodata`, `drop`, `tcp-only`

### 3. `rpz_master.j2` - Master RPZ Zone Template
**Purpose**: Comprehensive RPZ template with advanced features and detailed organization.
**Use Case**: Primary RPZ zones requiring detailed rule organization and metadata.
**Variables**:
- `zone_name`: RPZ zone name
- `zone_type`: Zone type (master/slave)
- `zone_description`: Zone description
- `default_policy`: Default RPZ policy
- `break_dnssec`: DNSSEC breaking setting
- `max_policy_ttl`: Maximum policy TTL

### 4. `rpz_custom_rules.j2` - Custom Rules Template
**Purpose**: Template for manually created custom RPZ rules.
**Use Case**: User-defined rules with custom actions and detailed metadata.
**Variables**:
- `zone_name`: Custom rules zone name
- `rules`: Custom rules with metadata
- Supports advanced actions: nxdomain, nodata, tcp-only, drop

### 5. `rpz_threat_feed.j2` - Threat Intelligence Feed Template
**Purpose**: Template for RPZ zones populated from external threat intelligence feeds.
**Use Case**: Automated threat blocking based on external feeds.
**Variables**:
- `feed_name`: Name of the threat feed
- `feed_source`: Source of the threat feed
- `feed_url`: URL of the threat feed
- `feed_last_updated`: Last update timestamp
- `threat_category`: Threat categorization
- `confidence_score`: Threat confidence level

### 6. `rpz_policy.j2` - RPZ Policy Configuration Template
**Purpose**: Template for BIND9 RPZ policy configuration block.
**Use Case**: Main BIND configuration file inclusion.
**Variables**:
- `categories`: RPZ categories and their configurations
- `enabled`: RPZ enabled status
- `qname_wait_recurse`: QName wait recurse setting
- `break_dnssec`: DNSSEC breaking setting

### 7. `rpz_config.j2` - Complete RPZ Configuration Template
**Purpose**: Complete RPZ configuration for BIND9 including zones and policies.
**Use Case**: Full RPZ setup in BIND9 configuration.
**Variables**:
- `rpz_zones`: List of all RPZ zones
- `rpz_enabled`: RPZ enabled status
- `qname_wait_recurse`: QName wait recurse setting
- `break_dnssec`: DNSSEC breaking setting

### 8. `rpz_rule.j2` - Single RPZ Rule Template
**Purpose**: Template for generating individual RPZ rules.
**Use Case**: Single rule generation and testing.
**Variables**:
- `rule`: Single rule object with domain, action, metadata

## RPZ Actions Supported

All templates support the following RPZ actions:

- **block/nxdomain**: Return NXDOMAIN (domain does not exist)
- **redirect**: Redirect to specified target domain
- **passthru/passthrough**: Allow through (whitelist)
- **nodata**: Return empty response (NODATA)
- **tcp-only**: Force TCP queries only
- **drop**: Drop queries (no response)

## Template Variables

### Common Variables
- `generated_at`: Template generation timestamp
- `primary_ns`: Primary name server (default: localhost.)
- `admin_email`: Administrator email (default: admin.localhost.)
- `ttl`: Zone TTL (default: 300)
- `serial`: Zone serial number (auto-generated from timestamp)

### Rule Object Structure
```python
rule = {
    'id': int,                    # Rule ID
    'domain': str,                # Domain name
    'action': str,                # RPZ action
    'redirect_target': str,       # Redirect target (for redirect action)
    'description': str,           # Rule description
    'category': str,              # Rule category
    'source': str,                # Rule source
    'is_active': bool,            # Rule active status
    'created_at': datetime,       # Creation timestamp
    'updated_at': datetime,       # Update timestamp
    'threat_category': str,       # Threat category (for threat feeds)
    'confidence_score': int,      # Confidence score (0-100)
    'ioc_id': str,               # Indicator of Compromise ID
}
```

## Custom Filters

The templates use custom Jinja2 filters defined in the BindService:

- `rpz_format_domain`: Format domain for RPZ zone file
- `ensure_trailing_dot`: Ensure domain has trailing dot
- `format_ttl`: Format TTL value
- `format_serial`: Format serial number

## Usage Examples

### Basic RPZ Zone
```python
template = jinja_env.get_template('rpz_zone.j2')
content = template.render(
    rpz_zone='malware',
    rules=malware_rules,
    generated_at=datetime.now()
)
```

### Malware Protection Zone
```python
template = jinja_env.get_template('rpz_malware.j2')
content = template.render(
    zone_name='rpz.malware',
    rules=malware_rules,
    threat_sources=['Spamhaus', 'Malware Domain List'],
    threat_feeds=active_feeds,
    average_confidence=85,
    generated_at=datetime.now()
)
```

### SafeSearch Enforcement Zone
```python
template = jinja_env.get_template('rpz_safesearch.j2')
content = template.render(
    zone_name='rpz.safesearch',
    google_safesearch=True,
    youtube_safesearch=True,
    bing_safesearch=True,
    duckduckgo_safesearch=True,
    yahoo_safesearch=True,
    yandex_safesearch=False,
    generated_at=datetime.now()
)
```

### Social Media Blocking Zone
```python
template = jinja_env.get_template('rpz_social_media.j2')
content = template.render(
    zone_name='rpz.social-media',
    major_platforms=True,
    professional_networks=False,  # Allow LinkedIn for business
    messaging_platforms=True,
    business_tools=False,  # Allow Slack/Teams
    block_target='.',
    redirect_page='https://company.com/policy',
    generated_at=datetime.now()
)
```

### Adult Content Blocking Zone
```python
template = jinja_env.get_template('rpz_adult.j2')
content = template.render(
    zone_name='rpz.adult',
    filter_level='Strict',
    block_dating=False,
    rules=adult_content_rules,
    content_filters=commercial_filters,
    generated_at=datetime.now()
)
```

### Custom Rules Zone
```python
template = jinja_env.get_template('rpz_custom.j2')
content = template.render(
    zone_name='rpz.custom',
    rules=custom_rules,
    rule_categories=categories,
    temporary_rules=temp_rules,
    generated_at=datetime.now()
)
```

### Threat Feed Zone
```python
template = jinja_env.get_template('rpz_threat_feed.j2')
content = template.render(
    feed_name='Malware Domain List',
    feed_source='external',
    feed_url='https://example.com/malware-domains.txt',
    rules=threat_rules,
    generated_at=datetime.now()
)
```

## File Naming Convention

RPZ zone files should follow this naming convention:
- `db.rpz.{category}` - Category-based zones (e.g., db.rpz.malware)
- `db.rpz.{feed_name}` - Threat feed zones (e.g., db.rpz.spamhaus)
- `db.rpz.custom` - Custom rules zone
- `db.rpz.{zone_name}` - General zones

## Integration with BIND9

These templates generate zone files that should be placed in the BIND9 zones directory (typically `/etc/bind/rpz/`) and referenced in the BIND9 configuration file.

Example BIND9 configuration:
```
response-policy {
    zone "malware.rpz" policy given;
    zone "phishing.rpz" policy given;
    zone "custom.rpz" policy given;
} qname-wait-recurse no break-dnssec yes;
```

## Template Maintenance

When modifying templates:
1. Test with sample data before deployment
2. Validate generated zone files with `named-checkzone`
3. Ensure backward compatibility with existing rules
4. Update this documentation for any new variables or features