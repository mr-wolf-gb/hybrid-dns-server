"""
DNS Record Template Service

This service provides predefined templates for common DNS record types
to help users quickly create standard DNS configurations.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class RecordTemplateCategory(str, Enum):
    """Categories for DNS record templates"""
    WEB_SERVICES = "web_services"
    EMAIL_SERVICES = "email_services"
    SECURITY = "security"
    CLOUD_SERVICES = "cloud_services"
    NETWORK_SERVICES = "network_services"
    DEVELOPMENT = "development"


class RecordTemplate:
    """Represents a DNS record template"""
    
    def __init__(self, name: str, description: str, category: RecordTemplateCategory,
                 records: List[Dict[str, Any]], variables: List[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.category = category
        self.records = records
        self.variables = variables or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "records": self.records,
            "variables": self.variables
        }


class RecordTemplateService:
    """Service for managing DNS record templates"""
    
    def __init__(self):
        self._templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, RecordTemplate]:
        """Initialize predefined record templates"""
        templates = {}
        
        # Web Services Templates
        templates["basic_website"] = RecordTemplate(
            name="Basic Website",
            description="Standard A and AAAA records for a website with www subdomain",
            category=RecordTemplateCategory.WEB_SERVICES,
            records=[
                {
                    "name": "@",
                    "record_type": "A",
                    "value": "{ipv4_address}",
                    "ttl": 300,
                    "description": "Main domain A record"
                },
                {
                    "name": "www",
                    "record_type": "A",
                    "value": "{ipv4_address}",
                    "ttl": 300,
                    "description": "WWW subdomain A record"
                },
                {
                    "name": "@",
                    "record_type": "AAAA",
                    "value": "{ipv6_address}",
                    "ttl": 300,
                    "description": "Main domain AAAA record (optional)"
                },
                {
                    "name": "www",
                    "record_type": "AAAA",
                    "value": "{ipv6_address}",
                    "ttl": 300,
                    "description": "WWW subdomain AAAA record (optional)"
                }
            ],
            variables=[
                {"name": "ipv4_address", "type": "ipv4", "required": True, "description": "IPv4 address of your web server"},
                {"name": "ipv6_address", "type": "ipv6", "required": False, "description": "IPv6 address of your web server (optional)"}
            ]
        )
        
        templates["cdn_website"] = RecordTemplate(
            name="CDN Website",
            description="Website configuration with CDN using CNAME records",
            category=RecordTemplateCategory.WEB_SERVICES,
            records=[
                {
                    "name": "@",
                    "record_type": "A",
                    "value": "{origin_ipv4}",
                    "ttl": 300,
                    "description": "Origin server A record"
                },
                {
                    "name": "www",
                    "record_type": "CNAME",
                    "value": "{cdn_domain}",
                    "ttl": 300,
                    "description": "WWW subdomain pointing to CDN"
                },
                {
                    "name": "cdn",
                    "record_type": "CNAME",
                    "value": "{cdn_domain}",
                    "ttl": 300,
                    "description": "CDN subdomain"
                }
            ],
            variables=[
                {"name": "origin_ipv4", "type": "ipv4", "required": True, "description": "IPv4 address of your origin server"},
                {"name": "cdn_domain", "type": "domain", "required": True, "description": "CDN domain name (e.g., example.cloudfront.net)"}
            ]
        )
        
        # Email Services Templates
        templates["basic_email"] = RecordTemplate(
            name="Basic Email Server",
            description="Standard MX record configuration for email services",
            category=RecordTemplateCategory.EMAIL_SERVICES,
            records=[
                {
                    "name": "@",
                    "record_type": "MX",
                    "value": "{mail_server}",
                    "priority": 10,
                    "ttl": 300,
                    "description": "Primary mail server"
                },
                {
                    "name": "mail",
                    "record_type": "A",
                    "value": "{mail_ipv4}",
                    "ttl": 300,
                    "description": "Mail server A record"
                }
            ],
            variables=[
                {"name": "mail_server", "type": "domain", "required": True, "description": "Mail server hostname (e.g., mail.example.com)"},
                {"name": "mail_ipv4", "type": "ipv4", "required": True, "description": "Mail server IPv4 address"}
            ]
        )
        
        templates["google_workspace"] = RecordTemplate(
            name="Google Workspace",
            description="Complete Google Workspace (Gmail) configuration",
            category=RecordTemplateCategory.EMAIL_SERVICES,
            records=[
                {
                    "name": "@",
                    "record_type": "MX",
                    "value": "aspmx.l.google.com",
                    "priority": 1,
                    "ttl": 300,
                    "description": "Primary Google MX record"
                },
                {
                    "name": "@",
                    "record_type": "MX",
                    "value": "alt1.aspmx.l.google.com",
                    "priority": 5,
                    "ttl": 300,
                    "description": "Secondary Google MX record"
                },
                {
                    "name": "@",
                    "record_type": "MX",
                    "value": "alt2.aspmx.l.google.com",
                    "priority": 5,
                    "ttl": 300,
                    "description": "Secondary Google MX record"
                },
                {
                    "name": "@",
                    "record_type": "MX",
                    "value": "alt3.aspmx.l.google.com",
                    "priority": 10,
                    "ttl": 300,
                    "description": "Tertiary Google MX record"
                },
                {
                    "name": "@",
                    "record_type": "MX",
                    "value": "alt4.aspmx.l.google.com",
                    "priority": 10,
                    "ttl": 300,
                    "description": "Tertiary Google MX record"
                }
            ],
            variables=[]
        )
        
        templates["microsoft_365"] = RecordTemplate(
            name="Microsoft 365",
            description="Microsoft 365 (Outlook) email configuration",
            category=RecordTemplateCategory.EMAIL_SERVICES,
            records=[
                {
                    "name": "@",
                    "record_type": "MX",
                    "value": "{domain}-mail.protection.outlook.com",
                    "priority": 0,
                    "ttl": 300,
                    "description": "Microsoft 365 MX record"
                },
                {
                    "name": "autodiscover",
                    "record_type": "CNAME",
                    "value": "autodiscover.outlook.com",
                    "ttl": 300,
                    "description": "Autodiscover for email clients"
                }
            ],
            variables=[
                {"name": "domain", "type": "domain_part", "required": True, "description": "Your domain name without TLD (e.g., 'example' for example.com)"}
            ]
        )
        
        # Security Templates
        templates["spf_basic"] = RecordTemplate(
            name="Basic SPF Record",
            description="Basic SPF (Sender Policy Framework) record for email security",
            category=RecordTemplateCategory.SECURITY,
            records=[
                {
                    "name": "@",
                    "record_type": "TXT",
                    "value": "v=spf1 include:{mail_provider} ~all",
                    "ttl": 300,
                    "description": "SPF record to prevent email spoofing"
                }
            ],
            variables=[
                {"name": "mail_provider", "type": "domain", "required": True, "description": "Mail provider SPF domain (e.g., _spf.google.com for Google, spf.protection.outlook.com for Microsoft)"}
            ]
        )
        
        templates["dmarc_basic"] = RecordTemplate(
            name="Basic DMARC Record",
            description="Basic DMARC record for email authentication",
            category=RecordTemplateCategory.SECURITY,
            records=[
                {
                    "name": "_dmarc",
                    "record_type": "TXT",
                    "value": "v=DMARC1; p={policy}; rua=mailto:{report_email}",
                    "ttl": 300,
                    "description": "DMARC policy record"
                }
            ],
            variables=[
                {"name": "policy", "type": "select", "options": ["none", "quarantine", "reject"], "required": True, "description": "DMARC policy (none for monitoring, quarantine for suspicious, reject for strict)"},
                {"name": "report_email", "type": "email", "required": True, "description": "Email address to receive DMARC reports"}
            ]
        )
        
        # Cloud Services Templates
        templates["aws_website"] = RecordTemplate(
            name="AWS Website",
            description="AWS CloudFront and S3 website configuration",
            category=RecordTemplateCategory.CLOUD_SERVICES,
            records=[
                {
                    "name": "@",
                    "record_type": "A",
                    "value": "{cloudfront_ipv4}",
                    "ttl": 300,
                    "description": "CloudFront IPv4 address"
                },
                {
                    "name": "www",
                    "record_type": "CNAME",
                    "value": "{cloudfront_domain}",
                    "ttl": 300,
                    "description": "WWW subdomain pointing to CloudFront"
                }
            ],
            variables=[
                {"name": "cloudfront_ipv4", "type": "ipv4", "required": True, "description": "CloudFront distribution IPv4 address"},
                {"name": "cloudfront_domain", "type": "domain", "required": True, "description": "CloudFront distribution domain (e.g., d123456.cloudfront.net)"}
            ]
        )
        
        templates["azure_website"] = RecordTemplate(
            name="Azure Website",
            description="Azure App Service website configuration",
            category=RecordTemplateCategory.CLOUD_SERVICES,
            records=[
                {
                    "name": "@",
                    "record_type": "A",
                    "value": "{azure_ipv4}",
                    "ttl": 300,
                    "description": "Azure App Service IPv4 address"
                },
                {
                    "name": "www",
                    "record_type": "CNAME",
                    "value": "{app_name}.azurewebsites.net",
                    "ttl": 300,
                    "description": "WWW subdomain pointing to Azure App Service"
                },
                {
                    "name": "awverify",
                    "record_type": "CNAME",
                    "value": "awverify.{app_name}.azurewebsites.net",
                    "ttl": 300,
                    "description": "Azure domain verification record"
                }
            ],
            variables=[
                {"name": "azure_ipv4", "type": "ipv4", "required": True, "description": "Azure App Service IPv4 address"},
                {"name": "app_name", "type": "text", "required": True, "description": "Azure App Service name"}
            ]
        )
        
        # Network Services Templates
        templates["ftp_server"] = RecordTemplate(
            name="FTP Server",
            description="FTP server configuration with A record",
            category=RecordTemplateCategory.NETWORK_SERVICES,
            records=[
                {
                    "name": "ftp",
                    "record_type": "A",
                    "value": "{ftp_ipv4}",
                    "ttl": 300,
                    "description": "FTP server A record"
                }
            ],
            variables=[
                {"name": "ftp_ipv4", "type": "ipv4", "required": True, "description": "FTP server IPv4 address"}
            ]
        )
        
        templates["vpn_server"] = RecordTemplate(
            name="VPN Server",
            description="VPN server configuration",
            category=RecordTemplateCategory.NETWORK_SERVICES,
            records=[
                {
                    "name": "vpn",
                    "record_type": "A",
                    "value": "{vpn_ipv4}",
                    "ttl": 300,
                    "description": "VPN server A record"
                }
            ],
            variables=[
                {"name": "vpn_ipv4", "type": "ipv4", "required": True, "description": "VPN server IPv4 address"}
            ]
        )
        
        # Development Templates
        templates["development_env"] = RecordTemplate(
            name="Development Environment",
            description="Common development subdomains",
            category=RecordTemplateCategory.DEVELOPMENT,
            records=[
                {
                    "name": "dev",
                    "record_type": "A",
                    "value": "{dev_ipv4}",
                    "ttl": 300,
                    "description": "Development environment"
                },
                {
                    "name": "staging",
                    "record_type": "A",
                    "value": "{staging_ipv4}",
                    "ttl": 300,
                    "description": "Staging environment"
                },
                {
                    "name": "api",
                    "record_type": "A",
                    "value": "{api_ipv4}",
                    "ttl": 300,
                    "description": "API server"
                }
            ],
            variables=[
                {"name": "dev_ipv4", "type": "ipv4", "required": True, "description": "Development server IPv4 address"},
                {"name": "staging_ipv4", "type": "ipv4", "required": True, "description": "Staging server IPv4 address"},
                {"name": "api_ipv4", "type": "ipv4", "required": True, "description": "API server IPv4 address"}
            ]
        )
        
        return templates
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Get all available record templates"""
        return [template.to_dict() for template in self._templates.values()]
    
    def get_templates_by_category(self, category: RecordTemplateCategory) -> List[Dict[str, Any]]:
        """Get templates filtered by category"""
        return [
            template.to_dict() 
            for template in self._templates.values() 
            if template.category == category
        ]
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by name"""
        template = self._templates.get(template_name)
        return template.to_dict() if template else None
    
    def get_categories(self) -> List[Dict[str, str]]:
        """Get all available template categories"""
        return [
            {"value": category.value, "label": category.value.replace("_", " ").title()}
            for category in RecordTemplateCategory
        ]
    
    def apply_template(self, template_name: str, variables: Dict[str, str]) -> List[Dict[str, Any]]:
        """Apply a template with provided variables to generate DNS records"""
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Validate required variables
        required_vars = [var["name"] for var in template.variables if var.get("required", False)]
        missing_vars = [var for var in required_vars if var not in variables]
        if missing_vars:
            raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")
        
        # Apply variables to template records
        applied_records = []
        for record_template in template.records:
            record = record_template.copy()
            
            # Replace variables in all string fields
            for field in ["name", "value"]:
                if field in record and isinstance(record[field], str):
                    record[field] = self._replace_variables(record[field], variables)
            
            # Remove description field as it's not part of the DNS record schema
            record.pop("description", None)
            
            # Only include the record if all required variables were provided
            # Skip optional records if their variables are missing
            if self._has_all_required_variables(record, variables):
                applied_records.append(record)
        
        return applied_records
    
    def _replace_variables(self, text: str, variables: Dict[str, str]) -> str:
        """Replace template variables in text"""
        for var_name, var_value in variables.items():
            text = text.replace(f"{{{var_name}}}", var_value)
        return text
    
    def _has_all_required_variables(self, record: Dict[str, Any], variables: Dict[str, str]) -> bool:
        """Check if record has all required variables filled"""
        for field in ["name", "value"]:
            if field in record and isinstance(record[field], str):
                # Check if there are any unreplaced variables (still in {var} format)
                if "{" in record[field] and "}" in record[field]:
                    # This record has unfilled variables, check if they're optional
                    import re
                    unfilled_vars = re.findall(r'\{([^}]+)\}', record[field])
                    # For now, skip records with unfilled variables
                    # In a more sophisticated implementation, we could check if variables are optional
                    return False
        return True
    
    def validate_template_variables(self, template_name: str, variables: Dict[str, str]) -> Dict[str, Any]:
        """Validate template variables"""
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        errors = []
        warnings = []
        
        # Check required variables
        required_vars = [var["name"] for var in template.variables if var.get("required", False)]
        missing_vars = [var for var in required_vars if var not in variables or not variables[var]]
        if missing_vars:
            errors.extend([f"Missing required variable: {var}" for var in missing_vars])
        
        # Validate variable formats
        for var_config in template.variables:
            var_name = var_config["name"]
            if var_name in variables and variables[var_name]:
                var_value = variables[var_name]
                var_type = var_config.get("type", "text")
                
                try:
                    self._validate_variable_format(var_name, var_value, var_type, var_config)
                except ValueError as e:
                    errors.append(str(e))
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_variable_format(self, var_name: str, var_value: str, var_type: str, var_config: Dict[str, Any]):
        """Validate individual variable format"""
        from ..schemas.dns import DNSValidators
        
        if var_type == "ipv4":
            try:
                DNSValidators.validate_ipv4_address(var_value)
            except ValueError:
                raise ValueError(f"Variable '{var_name}' must be a valid IPv4 address")
        
        elif var_type == "ipv6":
            try:
                DNSValidators.validate_ipv6_address(var_value)
            except ValueError:
                raise ValueError(f"Variable '{var_name}' must be a valid IPv6 address")
        
        elif var_type == "domain":
            try:
                DNSValidators.validate_domain_name(var_value, "template variable")
            except ValueError:
                raise ValueError(f"Variable '{var_name}' must be a valid domain name")
        
        elif var_type == "email":
            if "@" not in var_value or len(var_value.split("@")) != 2:
                raise ValueError(f"Variable '{var_name}' must be a valid email address")
        
        elif var_type == "select":
            options = var_config.get("options", [])
            if var_value not in options:
                raise ValueError(f"Variable '{var_name}' must be one of: {', '.join(options)}")
        
        elif var_type == "domain_part":
            # Domain part without TLD (e.g., "example" from "example.com")
            if not var_value or not var_value.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"Variable '{var_name}' must be a valid domain part (letters, numbers, hyphens, underscores only)")