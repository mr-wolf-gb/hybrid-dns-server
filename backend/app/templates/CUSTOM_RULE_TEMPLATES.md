# Custom Rule Templates Documentation

This document describes the custom rule templates available in the Hybrid DNS Server for creating specialized RPZ (Response Policy Zone) configurations.

## Overview

Custom rule templates provide specialized Jinja2 templates for different types of custom RPZ rules. Each template is designed for specific use cases and includes appropriate variables, formatting, and documentation.

## Available Custom Rule Templates

### 1. rpz_custom_block.j2
**Purpose**: Template for custom domain blocking rules
**Zone Prefix**: `rpz.custom-block`
**Use Cases**:
- Organization-specific blocking rules
- Competitor website blocking
- Productivity control during work hours
- Security exceptions and temporary blocks
- Compliance-required blocking

**Key Features**:
- Supports wildcard subdomain blocking
- Rule categorization and organization
- Active/inactive rule management
- Detailed rule documentation and metadata
- Statistics and usage tracking

**Template Variables**:
- `rules`: List of block rules
- `rule_categories`: Categories for rule organization
- `active_rules_count`: Number of active rules
- `zone_name`: RPZ zone name
- `ttl`: Time-to-live for DNS records

### 2. rpz_custom_allow.j2
**Purpose**: Template for custom domain allow/passthrough rules (whitelist)
**Zone Prefix**: `rpz.custom-allow`
**Use Cases**:
- Business-critical application access
- Executive exceptions to blocking policies
- Marketing tool access
- Development and testing resources
- Partner/vendor access requirements

**Key Features**:
- Business justification tracking
- Approval workflow integration
- Temporary exception management
- Executive-level exception handling
- Compliance documentation

**Template Variables**:
- `rules`: List of allow rules
- `business_exceptions`: Business-justified exceptions
- `temporary_exceptions`: Time-limited exceptions
- `rule_categories`: Categories for rule organization
- `zone_name`: RPZ zone name

### 3. rpz_custom_redirect.j2
**Purpose**: Template for custom domain redirection rules
**Zone Prefix**: `rpz.custom-redirect`
**Use Cases**:
- Policy enforcement with user education
- Brand protection against typosquatting
- Service migration and maintenance
- User guidance to approved alternatives
- Compliance notification pages

**Key Features**:
- Policy enforcement redirects
- Brand protection redirects
- Maintenance window redirects
- Redirect target validation
- Usage monitoring and analytics

**Template Variables**:
- `rules`: List of redirect rules
- `policy_redirects`: Policy enforcement redirects
- `brand_protection`: Brand protection redirects
- `maintenance_redirects`: Maintenance window redirects
- `redirect_targets`: Available redirect targets

### 4. rpz_custom_temporary.j2
**Purpose**: Template for temporary RPZ rules with expiration
**Zone Prefix**: `rpz.custom-temporary`
**Use Cases**:
- Incident response and security containment
- Testing new policies before production
- Short-term blocking during investigations
- Temporary business exceptions
- Maintenance window rules

**Key Features**:
- Automatic expiration handling
- Incident response integration
- Testing rule management
- Maintenance window support
- Automatic cleanup of expired rules

**Template Variables**:
- `rules`: List of temporary rules
- `incident_rules`: Active incident response rules
- `testing_rules`: Active testing rules
- `maintenance_windows`: Active maintenance windows
- `cleanup_frequency`: How often expired rules are cleaned up
- `expiring_soon`: Rules expiring within 24 hours

### 5. rpz_custom_business.j2
**Purpose**: Template for business-specific RPZ rules and policies
**Zone Prefix**: `rpz.custom-business`
**Use Cases**:
- Department-specific access policies
- Executive-level exceptions
- Compliance-mandated rules
- Business partner access
- Project-specific requirements
- Cost management and bandwidth control

**Key Features**:
- Department-based rule organization
- Executive exception management
- Compliance requirement tracking
- Business partner access control
- Project-specific rule management
- Business hours rule enforcement
- Cost management integration

**Template Variables**:
- `rules`: List of business rules organized by department
- `executive_exceptions`: Executive-level exceptions
- `compliance_rules`: Compliance-mandated rules
- `partner_access`: Business partner access rules
- `project_rules`: Project-specific rules
- `business_hours_rules`: Time-based rules
- `cost_management`: Cost management rules

## Template Usage

### Basic Usage

```python
from app.templates.template_mapping import get_template_for_category, get_template_variables

# Get template configuration for a category
template_config = get_template_for_category('custom-block')
template_name = template_config['template']  # 'rpz_custom_block.j2'

# Get template variables with defaults
variables = get_template_variables('custom-block', {
    'rules': block_rules,
    'rule_categories': categories
})

# Render template
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('backend/app/templates'))
template = env.get_template(template_name)
zone_content = template.render(**variables)
```

### Advanced Usage with Custom Variables

```python
# Custom variables for business rules
custom_vars = {
    'rules': business_rules,
    'executive_exceptions': exec_exceptions,
    'compliance_rules': compliance_data,
    'partner_access': partner_rules,
    'project_rules': project_data
}

variables = get_template_variables('custom-business', custom_vars)
```

## Template Customization

### Adding Custom Filters

Templates support custom Jinja2 filters for RPZ-specific formatting:

- `rpz_format_domain`: Formats domain names for RPZ zones
- `ensure_trailing_dot`: Ensures FQDN has trailing dot
- `selectattr`: Filters objects by attribute value
- `rejectattr`: Excludes objects by attribute value
- `groupby`: Groups objects by attribute

### Template Inheritance

Custom templates can extend base templates for consistency:

```jinja2
{% extends "rpz_base.j2" %}

{% block zone_content %}
<!-- Custom zone content here -->
{% endblock %}
```

## Best Practices

### Rule Organization
- Use meaningful rule categories
- Include business justification for all rules
- Document approval processes
- Implement regular review cycles

### Template Maintenance
- Keep templates updated with current business needs
- Test templates with sample data
- Validate generated zone files
- Monitor template performance

### Security Considerations
- Validate all input data
- Escape template variables appropriately
- Implement access controls for template modification
- Audit template usage and changes

### Performance Optimization
- Use efficient Jinja2 constructs
- Minimize template complexity
- Cache rendered templates when appropriate
- Monitor zone file generation performance

## Integration with Services

### RPZ Service Integration

```python
from app.services.rpz_service import RPZService
from app.templates.template_mapping import get_template_name

rpz_service = RPZService(db)
template_name = get_template_name('custom-block')
zone_content = rpz_service.generate_zone_file(
    category='custom-block',
    template=template_name,
    rules=block_rules
)
```

### BIND Service Integration

```python
from app.services.bind_service import BindService

bind_service = BindService()
await bind_service.update_rpz_zone_file('custom-block', zone_content)
await bind_service.reload_configuration()
```

## Troubleshooting

### Common Issues

1. **Template Not Found**
   - Verify template file exists in templates directory
   - Check template mapping configuration
   - Ensure correct template name in mapping

2. **Variable Errors**
   - Validate all required variables are provided
   - Check variable types match template expectations
   - Use default values for optional variables

3. **Zone File Validation Errors**
   - Validate generated zone file syntax
   - Check DNS record formatting
   - Verify BIND9 configuration compatibility

4. **Performance Issues**
   - Monitor template rendering time
   - Optimize complex template logic
   - Consider caching for frequently used templates

### Debugging Templates

Enable template debugging:

```python
from jinja2 import Environment, DebugUndefined

env = Environment(
    loader=FileSystemLoader('templates'),
    undefined=DebugUndefined
)
```

## Future Enhancements

### Planned Features
- Template versioning and migration
- Visual template editor
- Template validation tools
- Performance monitoring
- Template usage analytics

### Extension Points
- Custom filter development
- Template plugin system
- External template repositories
- Template sharing and collaboration

## Support and Documentation

For additional support:
- Review template source code for detailed implementation
- Check service layer integration points
- Consult API documentation for template usage
- Review test cases for example usage patterns

## Version History

- v1.0: Initial custom rule templates
- v1.1: Added business rules template
- v1.2: Enhanced temporary rules with expiration
- v1.3: Added redirect and allow templates
- v1.4: Improved template documentation and examples