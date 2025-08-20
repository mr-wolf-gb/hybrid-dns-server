"""
Template Validation Utility

This module provides utilities for validating RPZ templates and ensuring
they generate valid BIND9 zone files.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from jinja2 import Environment, FileSystemLoader, TemplateError, UndefinedError
from pathlib import Path

# Template directory
TEMPLATE_DIR = Path(__file__).parent

def create_test_environment() -> Environment:
    """Create a Jinja2 environment for testing templates."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Add custom filters for RPZ formatting
    def rpz_format_domain(domain: str) -> str:
        """Format domain for RPZ zone file."""
        if not domain:
            return ""
        # Remove protocol if present
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        # Remove path if present
        if "/" in domain:
            domain = domain.split("/", 1)[0]
        # Ensure no trailing dot for RPZ format
        return domain.rstrip(".")
    
    def ensure_trailing_dot(hostname: str) -> str:
        """Ensure hostname has trailing dot for FQDN."""
        if not hostname:
            return ""
        return hostname if hostname.endswith(".") else f"{hostname}."
    
    env.filters['rpz_format_domain'] = rpz_format_domain
    env.filters['ensure_trailing_dot'] = ensure_trailing_dot
    
    # Add now() function for template context
    env.globals['now'] = datetime.now
    
    return env

def create_sample_data() -> Dict[str, Any]:
    """Create sample data for template testing."""
    now = datetime.now()
    
    # Sample rules for different actions
    sample_rules = [
        {
            'id': 1,
            'domain': 'example-block.com',
            'action': 'block',
            'is_active': True,
            'description': 'Sample block rule',
            'category': 'Testing',
            'source': 'Manual',
            'created_by': 'admin',
            'department': 'Security',
            'department_head': 'Jane Security Manager',
            'business_function': 'Security Testing',
            'expires_at': now + timedelta(hours=48),
            'created_at': now - timedelta(days=1),
            'updated_at': now,
            'wildcard_subdomains': True,
        },
        {
            'id': 2,
            'domain': 'example-redirect.com',
            'action': 'redirect',
            'redirect_target': 'policy.company.com',
            'is_active': True,
            'description': 'Sample redirect rule',
            'category': 'Policy',
            'source': 'Manual',
            'created_by': 'admin',
            'department': 'HR',
            'department_head': 'Bob HR Director',
            'business_function': 'Policy Enforcement',
            'expires_at': now + timedelta(days=7),
            'created_at': now - timedelta(hours=6),
            'updated_at': now,
        },
        {
            'id': 3,
            'domain': 'example-allow.com',
            'action': 'passthru',
            'is_active': True,
            'description': 'Sample allow rule',
            'category': 'Business',
            'source': 'Manual',
            'created_by': 'admin',
            'business_justification': 'Required for business operations',
            'department': 'IT',
            'department_head': 'John IT Manager',
            'business_function': 'Infrastructure Management',
            'approved_by': 'John IT Manager',
            'approval_date': now - timedelta(days=7),
            'review_date': now + timedelta(days=90),
            'expires_at': now + timedelta(days=30),
            'created_at': now - timedelta(hours=2),
            'updated_at': now,
        },
        {
            'id': 4,
            'domain': 'example-temporary.com',
            'action': 'block',
            'is_active': True,
            'description': 'Temporary block for testing',
            'category': 'Temporary',
            'source': 'Incident Response',
            'created_by': 'security-team',
            'department': 'Security',
            'department_head': 'Jane Security Manager',
            'business_function': 'Incident Response',
            'expires_at': now + timedelta(hours=24),
            'reason': 'Security incident containment',
            'incident_id': 'INC-2024-001',
            'created_at': now - timedelta(minutes=30),
            'updated_at': now,
        }
    ]
    
    # Sample business data
    business_data = {
        'executive_exceptions': [
            {
                'executive_name': 'John CEO',
                'position': 'Chief Executive Officer',
                'exception_type': 'Social Media Access',
                'approved_by': 'Board of Directors',
                'approval_date': now - timedelta(days=30),
                'review_date': now + timedelta(days=335),
                'domains': ['linkedin.com', 'twitter.com']
            }
        ],
        'compliance_rules': [
            {
                'regulation': 'GDPR',
                'requirement': 'Data Processing Restriction',
                'officer': 'Jane Compliance',
                'implementation_date': now - timedelta(days=90),
                'next_audit': now + timedelta(days=275),
                'rules': [
                    {
                        'domain': 'data-broker.com',
                        'action': 'block',
                        'redirect_target': None
                    }
                ]
            }
        ],
        'partner_access': [
            {
                'partner_name': 'Vendor Corp',
                'contract_number': 'CNT-2024-001',
                'relationship_type': 'Software Vendor',
                'contact_person': 'vendor@vendorcorp.com',
                'contract_expiry': now + timedelta(days=365),
                'allowed_domains': ['vendorcorp.com', 'support.vendorcorp.com']
            }
        ]
    }
    
    return {
        'rules': sample_rules,
        'zone_name': 'rpz.test',
        'generated_at': now,
        'ttl': 300,
        'primary_ns': 'ns1.company.com.',
        'admin_email': 'admin.company.com.',
        'serial': int(now.strftime('%Y%m%d%H')),
        'refresh': 3600,
        'retry': 1800,
        'expire': 604800,
        'minimum': 300,
        'active_rules_count': len([r for r in sample_rules if r['is_active']]),
        'rule_categories': [
            {'name': 'Testing', 'description': 'Test rules', 'rule_count': 1},
            {'name': 'Policy', 'description': 'Policy enforcement', 'rule_count': 1},
            {'name': 'Business', 'description': 'Business rules', 'rule_count': 1},
            {'name': 'Temporary', 'description': 'Temporary rules', 'rule_count': 1}
        ],
        **business_data
    }

def validate_template(template_name: str, test_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[str]]:
    """
    Validate a template by rendering it with test data.
    
    Args:
        template_name: Name of the template file
        test_data: Optional test data, uses sample data if not provided
        
    Returns:
        Tuple of (success, message, rendered_content)
    """
    try:
        env = create_test_environment()
        template = env.get_template(template_name)
        
        if test_data is None:
            test_data = create_sample_data()
        
        rendered = template.render(**test_data)
        
        # Basic validation checks
        if not rendered.strip():
            return False, "Template rendered empty content", None
        
        # Check for basic zone file structure
        required_elements = ['$TTL', '$ORIGIN', 'SOA', 'IN', 'NS']
        missing_elements = [elem for elem in required_elements if elem not in rendered]
        
        if missing_elements:
            return False, f"Missing required zone file elements: {', '.join(missing_elements)}", rendered
        
        # Check for template errors (undefined variables, etc.)
        if 'Undefined' in rendered or '{{' in rendered or '}}' in rendered:
            return False, "Template contains undefined variables or unrendered expressions", rendered
        
        return True, "Template validation successful", rendered
        
    except TemplateError as e:
        return False, f"Template error: {str(e)}", None
    except UndefinedError as e:
        return False, f"Undefined variable error: {str(e)}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None

def validate_all_custom_templates() -> Dict[str, Tuple[bool, str]]:
    """
    Validate all custom rule templates.
    
    Returns:
        Dictionary mapping template names to validation results
    """
    custom_templates = [
        'rpz_custom_block.j2',
        'rpz_custom_allow.j2',
        'rpz_custom_redirect.j2',
        'rpz_custom_temporary.j2',
        'rpz_custom_business.j2',
        'rpz_custom_rules.j2',
        'rpz_custom.j2'
    ]
    
    results = {}
    
    for template_name in custom_templates:
        template_path = TEMPLATE_DIR / template_name
        if template_path.exists():
            success, message, _ = validate_template(template_name)
            results[template_name] = (success, message)
        else:
            results[template_name] = (False, "Template file not found")
    
    return results

def generate_sample_zone_files() -> Dict[str, str]:
    """
    Generate sample zone files for all custom templates.
    
    Returns:
        Dictionary mapping template names to generated zone content
    """
    custom_templates = [
        'rpz_custom_block.j2',
        'rpz_custom_allow.j2',
        'rpz_custom_redirect.j2',
        'rpz_custom_temporary.j2',
        'rpz_custom_business.j2'
    ]
    
    zone_files = {}
    test_data = create_sample_data()
    
    for template_name in custom_templates:
        success, message, content = validate_template(template_name, test_data)
        if success and content:
            zone_files[template_name] = content
        else:
            zone_files[template_name] = f"; Error generating zone file: {message}"
    
    return zone_files

def run_validation_report() -> str:
    """
    Run a comprehensive validation report for all custom templates.
    
    Returns:
        Formatted validation report
    """
    results = validate_all_custom_templates()
    
    report = []
    report.append("=" * 60)
    report.append("CUSTOM RPZ TEMPLATE VALIDATION REPORT")
    report.append("=" * 60)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    success_count = 0
    total_count = len(results)
    
    for template_name, (success, message) in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        report.append(f"{status} {template_name}")
        if not success:
            report.append(f"    Error: {message}")
        else:
            success_count += 1
        report.append("")
    
    report.append("-" * 60)
    report.append(f"SUMMARY: {success_count}/{total_count} templates passed validation")
    
    if success_count == total_count:
        report.append("All custom rule templates are valid!")
    else:
        report.append(f"{total_count - success_count} templates need attention.")
    
    report.append("=" * 60)
    
    return "\n".join(report)

if __name__ == "__main__":
    # Run validation when script is executed directly
    print(run_validation_report())
    
    # Generate sample zone files for inspection
    print("\nGenerating sample zone files...")
    zone_files = generate_sample_zone_files()
    
    for template_name, content in zone_files.items():
        output_file = TEMPLATE_DIR / f"sample_{template_name.replace('.j2', '.zone')}"
        with open(output_file, 'w') as f:
            f.write(content)
        print(f"Generated: {output_file}")