"""
Threat Feed Template Validator

This module provides validation functions for threat feed templates to ensure
they generate valid RPZ zone files and handle all required variables correctly.
"""

import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, Template, TemplateError
from jinja2.exceptions import UndefinedError, TemplateSyntaxError

try:
    from .template_mapping import (
        THREAT_FEED_TEMPLATE_MAPPING,
        get_threat_feed_template_for_type,
        get_threat_feed_template_variables
    )
except ImportError:
    # Fallback for direct execution
    from template_mapping import (
        THREAT_FEED_TEMPLATE_MAPPING,
        get_threat_feed_template_for_type,
        get_threat_feed_template_variables
    )


class ThreatFeedTemplateValidator:
    """Validator for threat feed templates"""
    
    def __init__(self, template_dir: str = None):
        """
        Initialize the validator
        
        Args:
            template_dir: Directory containing templates (defaults to current directory)
        """
        if template_dir is None:
            template_dir = os.path.dirname(__file__)
        
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            undefined=UndefinedError  # Strict undefined handling
        )
        
        # Add custom filters for RPZ formatting
        self.env.filters['rpz_format_domain'] = self._rpz_format_domain
    
    def _rpz_format_domain(self, domain: str) -> str:
        """Format domain for RPZ zone file"""
        if not domain:
            return domain
        
        # Remove protocol if present
        domain = re.sub(r'^https?://', '', domain)
        
        # Remove trailing slash
        domain = domain.rstrip('/')
        
        # Ensure domain doesn't end with dot for RPZ format
        if domain.endswith('.'):
            domain = domain[:-1]
        
        return domain
    
    def validate_template_syntax(self, template_name: str) -> Tuple[bool, List[str]]:
        """
        Validate template syntax
        
        Args:
            template_name: Name of the template file
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            template = self.env.get_template(template_name)
            # Try to parse the template
            template.environment.parse(template.source)
            return True, []
        except TemplateSyntaxError as e:
            errors.append(f"Syntax error in {template_name}: {e}")
        except Exception as e:
            errors.append(f"Error loading template {template_name}: {e}")
        
        return False, errors
    
    def validate_template_rendering(self, template_name: str, variables: Dict[str, Any]) -> Tuple[bool, List[str], Optional[str]]:
        """
        Validate template rendering with given variables
        
        Args:
            template_name: Name of the template file
            variables: Variables to use for rendering
            
        Returns:
            Tuple of (is_valid, error_messages, rendered_content)
        """
        errors = []
        rendered_content = None
        
        try:
            template = self.env.get_template(template_name)
            rendered_content = template.render(**variables)
            return True, [], rendered_content
        except UndefinedError as e:
            errors.append(f"Undefined variable in {template_name}: {e}")
        except TemplateError as e:
            errors.append(f"Template error in {template_name}: {e}")
        except Exception as e:
            errors.append(f"Unexpected error rendering {template_name}: {e}")
        
        return False, errors, rendered_content
    
    def validate_rpz_zone_format(self, zone_content: str) -> Tuple[bool, List[str]]:
        """
        Validate that generated content is a valid RPZ zone format
        
        Args:
            zone_content: Generated zone file content
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not zone_content:
            errors.append("Zone content is empty")
            return False, errors
        
        lines = zone_content.split('\n')
        
        # Check for required RPZ zone elements
        has_ttl = False
        has_origin = False
        has_soa = False
        has_ns = False
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            
            if line.startswith('$TTL'):
                has_ttl = True
            elif line.startswith('$ORIGIN'):
                has_origin = True
                # Validate ORIGIN format
                if not line.endswith('.rpz.'):
                    errors.append(f"Invalid ORIGIN format: {line}")
            elif 'SOA' in line:
                has_soa = True
            elif 'NS' in line and not 'SOA' in line:
                has_ns = True
            elif 'CNAME' in line:
                # Validate CNAME record format
                parts = line.split()
                if len(parts) < 4:
                    errors.append(f"Invalid CNAME record format: {line}")
                elif parts[2] != 'CNAME':
                    errors.append(f"Expected CNAME in record: {line}")
        
        # Check for required elements
        if not has_ttl:
            errors.append("Missing $TTL directive")
        if not has_origin:
            errors.append("Missing $ORIGIN directive")
        if not has_soa:
            errors.append("Missing SOA record")
        if not has_ns:
            errors.append("Missing NS record")
        
        return len(errors) == 0, errors
    
    def create_test_variables(self, feed_type: str, rule_count: int = 5) -> Dict[str, Any]:
        """
        Create test variables for template validation
        
        Args:
            feed_type: Type of threat feed
            rule_count: Number of test rules to create
            
        Returns:
            Dictionary of test variables
        """
        # Get base variables
        variables = get_threat_feed_template_variables(feed_type)
        
        # Create test rules
        test_rules = []
        for i in range(rule_count):
            rule = {
                'domain': f'test-domain-{i}.example.com',
                'is_active': True,
                'confidence_score': 85 + (i * 2),
                'first_seen': datetime.now(),
                'threat_description': f'Test threat {i}',
                'ioc_id': f'IOC-{i:04d}'
            }
            
            # Add feed-type specific properties
            if feed_type == 'malware':
                rule.update({
                    'threat_type': ['ransomware', 'botnet', 'trojan', 'virus'][i % 4],
                    'threat_category': 'malware',
                    'severity': 'high'
                })
            elif feed_type == 'phishing':
                rule.update({
                    'target_brand': ['PayPal', 'Amazon', 'Google', 'Microsoft'][i % 4],
                    'target_type': ['banking', 'ecommerce', 'email', 'social'][i % 4],
                    'phishing_type': 'credential_harvesting'
                })
            elif feed_type == 'adult':
                rule.update({
                    'content_type': ['explicit', 'dating', 'mature', 'advertising'][i % 4],
                    'content_category': 'adult',
                    'content_rating': 'explicit'
                })
            elif feed_type == 'social_media':
                rule.update({
                    'platform_type': ['major', 'messaging', 'content', 'professional'][i % 4],
                    'platform_name': ['Facebook', 'WhatsApp', 'YouTube', 'LinkedIn'][i % 4],
                    'productivity_impact': 'high'
                })
            elif feed_type == 'gambling':
                rule.update({
                    'gambling_type': ['casino', 'sports', 'poker', 'lottery'][i % 4],
                    'gambling_category': 'gambling',
                    'risk_level': 'high'
                })
            elif feed_type == 'custom':
                rule.update({
                    'custom_category': ['policy', 'incident', 'compliance', 'business'][i % 4],
                    'rule_purpose': 'security',
                    'priority_level': 'medium'
                })
            
            test_rules.append(rule)
        
        # Update variables with test data
        variables.update({
            'feed_name': f'Test {feed_type.title()} Feed',
            'feed_source': 'test',
            'feed_url': f'https://test.example.com/{feed_type}-feed.txt',
            'feed_description': f'Test feed for {feed_type} validation',
            'rules': test_rules,
            'active_rules_count': len(test_rules),
            'feed_last_updated': datetime.now(),
            'feed_next_update': datetime.now(),
            'feed_update_frequency': 'hourly',
            'feed_reliability': 'high'
        })
        
        return variables
    
    def validate_threat_feed_template(self, feed_type: str) -> Dict[str, Any]:
        """
        Comprehensive validation of a threat feed template
        
        Args:
            feed_type: Type of threat feed to validate
            
        Returns:
            Dictionary containing validation results
        """
        result = {
            'feed_type': feed_type,
            'template_name': None,
            'syntax_valid': False,
            'rendering_valid': False,
            'rpz_format_valid': False,
            'errors': [],
            'warnings': [],
            'rendered_content': None
        }
        
        # Get template configuration
        template_config = get_threat_feed_template_for_type(feed_type)
        template_name = template_config['template']
        result['template_name'] = template_name
        
        # Check if template file exists
        template_path = os.path.join(self.template_dir, template_name)
        if not os.path.exists(template_path):
            result['errors'].append(f"Template file not found: {template_path}")
            return result
        
        # Validate syntax
        syntax_valid, syntax_errors = self.validate_template_syntax(template_name)
        result['syntax_valid'] = syntax_valid
        result['errors'].extend(syntax_errors)
        
        if not syntax_valid:
            return result
        
        # Create test variables and validate rendering
        test_variables = self.create_test_variables(feed_type)
        rendering_valid, rendering_errors, rendered_content = self.validate_template_rendering(
            template_name, test_variables
        )
        
        result['rendering_valid'] = rendering_valid
        result['errors'].extend(rendering_errors)
        result['rendered_content'] = rendered_content
        
        if not rendering_valid:
            return result
        
        # Validate RPZ zone format
        rpz_valid, rpz_errors = self.validate_rpz_zone_format(rendered_content)
        result['rpz_format_valid'] = rpz_valid
        result['errors'].extend(rpz_errors)
        
        # Check for warnings
        if len(rendered_content) > 1000000:  # 1MB
            result['warnings'].append("Generated zone file is very large (>1MB)")
        
        if test_variables['active_rules_count'] == 0:
            result['warnings'].append("No active rules in test data")
        
        return result
    
    def validate_all_threat_feed_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all threat feed templates
        
        Returns:
            Dictionary mapping feed types to validation results
        """
        results = {}
        
        for feed_type in THREAT_FEED_TEMPLATE_MAPPING.keys():
            results[feed_type] = self.validate_threat_feed_template(feed_type)
        
        return results
    
    def generate_validation_report(self, results: Dict[str, Dict[str, Any]]) -> str:
        """
        Generate a human-readable validation report
        
        Args:
            results: Validation results from validate_all_threat_feed_templates
            
        Returns:
            Formatted validation report
        """
        report_lines = [
            "Threat Feed Template Validation Report",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        total_templates = len(results)
        valid_templates = sum(1 for r in results.values() if r['rpz_format_valid'])
        
        report_lines.extend([
            f"Total Templates: {total_templates}",
            f"Valid Templates: {valid_templates}",
            f"Invalid Templates: {total_templates - valid_templates}",
            ""
        ])
        
        for feed_type, result in results.items():
            report_lines.append(f"Template: {feed_type} ({result['template_name']})")
            report_lines.append("-" * 40)
            
            # Status indicators
            syntax_status = "✓" if result['syntax_valid'] else "✗"
            rendering_status = "✓" if result['rendering_valid'] else "✗"
            rpz_status = "✓" if result['rpz_format_valid'] else "✗"
            
            report_lines.extend([
                f"  Syntax Valid: {syntax_status}",
                f"  Rendering Valid: {rendering_status}",
                f"  RPZ Format Valid: {rpz_status}",
            ])
            
            if result['errors']:
                report_lines.append("  Errors:")
                for error in result['errors']:
                    report_lines.append(f"    - {error}")
            
            if result['warnings']:
                report_lines.append("  Warnings:")
                for warning in result['warnings']:
                    report_lines.append(f"    - {warning}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """Main function for running template validation"""
    validator = ThreatFeedTemplateValidator()
    
    print("Validating threat feed templates...")
    results = validator.validate_all_threat_feed_templates()
    
    report = validator.generate_validation_report(results)
    print(report)
    
    # Save report to file
    report_file = os.path.join(validator.template_dir, 'validation_report.txt')
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nValidation report saved to: {report_file}")
    
    # Return exit code based on validation results
    all_valid = all(r['rpz_format_valid'] for r in results.values())
    return 0 if all_valid else 1


if __name__ == '__main__':
    exit(main())