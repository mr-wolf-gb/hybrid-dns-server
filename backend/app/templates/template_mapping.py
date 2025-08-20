"""
RPZ Template Mapping Configuration

This module defines the mapping between RPZ categories and their specialized templates.
It provides configuration for template selection and default variables for each category.
"""

from typing import Dict, Any, Optional
from datetime import datetime

# Threat feed template mapping for different feed types
THREAT_FEED_TEMPLATE_MAPPING = {
    'malware': {
        'template': 'rpz_threat_feed_malware.j2',
        'zone_prefix': 'rpz.malware',
        'description': 'Malware Threat Feed',
        'default_ttl': 60,
        'default_variables': {
            'threat_categories': ['malware', 'ransomware', 'botnet', 'trojan', 'virus'],
            'update_frequency': 'hourly',
            'threat_level': 'high',
        }
    },
    'phishing': {
        'template': 'rpz_threat_feed_phishing.j2',
        'zone_prefix': 'rpz.phishing',
        'description': 'Phishing Threat Feed',
        'default_ttl': 60,
        'default_variables': {
            'threat_categories': ['phishing', 'brand_impersonation', 'credential_harvesting'],
            'update_frequency': 'hourly',
            'threat_level': 'high',
        }
    },
    'adult': {
        'template': 'rpz_threat_feed_adult.j2',
        'zone_prefix': 'rpz.adult',
        'description': 'Adult Content Threat Feed',
        'default_ttl': 300,
        'default_variables': {
            'content_categories': ['explicit', 'dating', 'mature', 'advertising'],
            'update_frequency': 'daily',
            'filter_level': 'strict',
        }
    },
    'social_media': {
        'template': 'rpz_threat_feed_social_media.j2',
        'zone_prefix': 'rpz.social-media',
        'description': 'Social Media Threat Feed',
        'default_ttl': 300,
        'default_variables': {
            'platform_categories': ['major_social', 'messaging', 'content_sharing', 'professional'],
            'update_frequency': 'daily',
            'productivity_impact': 'high',
        }
    },
    'gambling': {
        'template': 'rpz_threat_feed_gambling.j2',
        'zone_prefix': 'rpz.gambling',
        'description': 'Gambling Threat Feed',
        'default_ttl': 300,
        'default_variables': {
            'gambling_categories': ['casino', 'sports_betting', 'poker', 'lottery', 'crypto_gambling'],
            'update_frequency': 'daily',
            'risk_level': 'high',
        }
    },
    'custom': {
        'template': 'rpz_threat_feed_custom.j2',
        'zone_prefix': 'rpz.custom',
        'description': 'Custom Threat Feed',
        'default_ttl': 300,
        'default_variables': {
            'custom_categories': ['policy', 'incident', 'compliance', 'business', 'security'],
            'update_frequency': 'hourly',
            'priority_level': 'medium',
        }
    },
}

# Template mapping for RPZ categories
RPZ_TEMPLATE_MAPPING = {
    'malware': {
        'template': 'rpz_malware.j2',
        'zone_prefix': 'rpz.malware',
        'description': 'Malware Protection',
        'default_ttl': 60,
        'default_variables': {
            'threat_sources': [],
            'threat_feeds': [],
            'average_confidence': None,
        }
    },
    'phishing': {
        'template': 'rpz_phishing.j2',
        'zone_prefix': 'rpz.phishing',
        'description': 'Phishing Protection',
        'default_ttl': 60,
        'default_variables': {
            'threat_sources': [],
            'threat_feeds': [],
            'average_confidence': None,
        }
    },
    'safesearch': {
        'template': 'rpz_safesearch.j2',
        'zone_prefix': 'rpz.safesearch',
        'description': 'SafeSearch Enforcement',
        'default_ttl': 60,
        'default_variables': {
            'google_safesearch': True,
            'youtube_safesearch': True,
            'bing_safesearch': True,
            'duckduckgo_safesearch': True,
            'yahoo_safesearch': True,
            'yandex_safesearch': False,
            'custom_search_redirects': [],
            'enabled_providers': ['Google', 'YouTube', 'Bing', 'DuckDuckGo', 'Yahoo'],
        }
    },
    'social-media': {
        'template': 'rpz_social_media.j2',
        'zone_prefix': 'rpz.social-media',
        'description': 'Social Media Blocking',
        'default_ttl': 60,
        'default_variables': {
            'major_platforms': True,
            'professional_networks': False,
            'messaging_platforms': True,
            'content_platforms': True,
            'regional_platforms': False,
            'business_tools': False,
            'block_target': '.',
            'blocking_policy': 'Complete Block',
            'redirect_page': None,
        }
    },
    'adult': {
        'template': 'rpz_adult.j2',
        'zone_prefix': 'rpz.adult',
        'description': 'Adult Content Blocking',
        'default_ttl': 60,
        'default_variables': {
            'filter_level': 'Strict',
            'block_dating': False,
            'common_adult_domains': True,
            'content_filters': [],
            'block_target': '.',
        }
    },
    'gambling': {
        'template': 'rpz_gambling.j2',
        'zone_prefix': 'rpz.gambling',
        'description': 'Gambling Blocking',
        'default_ttl': 60,
        'default_variables': {
            'gambling_policy': 'Complete Block',
            'online_casinos': True,
            'sports_betting': True,
            'poker_gaming': True,
            'lottery_games': True,
            'crypto_gambling': True,
            'fantasy_sports': False,
            'high_risk_trading': False,
            'block_target': '.',
            'gambling_filters': [],
        }
    },
    'streaming': {
        'template': 'rpz_streaming.j2',
        'zone_prefix': 'rpz.streaming',
        'description': 'Streaming Media Blocking',
        'default_ttl': 60,
        'default_variables': {
            'streaming_policy': 'Bandwidth Management',
            'video_streaming': True,
            'youtube_blocking': True,
            'music_streaming': True,
            'live_streaming': True,
            'podcast_platforms': False,
            'international_streaming': False,
            'company_streaming': None,
            'block_target': '.',
        }
    },
    'custom': {
        'template': 'rpz_custom.j2',
        'zone_prefix': 'rpz.custom',
        'description': 'Custom Rules',
        'default_ttl': 60,
        'default_variables': {
            'rule_categories': [],
            'temporary_rules': [],
            'block_target': '.',
        }
    },
    'ransomware': {
        'template': 'rpz_malware.j2',  # Use malware template for ransomware
        'zone_prefix': 'rpz.ransomware',
        'description': 'Ransomware Protection',
        'default_ttl': 60,
        'default_variables': {
            'threat_sources': [],
            'threat_feeds': [],
            'average_confidence': None,
        }
    },

    'custom-allow': {
        'template': 'rpz_custom_allow.j2',
        'zone_prefix': 'rpz.custom-allow',
        'description': 'Custom Allow List',
        'default_ttl': 60,
        'default_variables': {
            'rule_categories': ['Custom Allow'],
            'temporary_rules': [],
            'business_exceptions': [],
            'temporary_exceptions': [],
            'block_target': 'rpz-passthru.',
        }
    },
    'custom-block': {
        'template': 'rpz_custom_block.j2',
        'zone_prefix': 'rpz.custom-block',
        'description': 'Custom Block List',
        'default_ttl': 60,
        'default_variables': {
            'rule_categories': ['Custom Block'],
            'temporary_rules': [],
            'block_target': '.',
        }
    },
    'custom-redirect': {
        'template': 'rpz_custom_redirect.j2',
        'zone_prefix': 'rpz.custom-redirect',
        'description': 'Custom Redirect Rules',
        'default_ttl': 60,
        'default_variables': {
            'rule_categories': ['Custom Redirect'],
            'policy_redirects': [],
            'brand_protection': [],
            'maintenance_redirects': [],
            'redirect_targets': [],
        }
    },
    'custom-temporary': {
        'template': 'rpz_custom_temporary.j2',
        'zone_prefix': 'rpz.custom-temporary',
        'description': 'Custom Temporary Rules',
        'default_ttl': 300,
        'default_variables': {
            'rule_categories': ['Temporary'],
            'incident_rules': [],
            'testing_rules': [],
            'maintenance_windows': [],
            'cleanup_frequency': 'Every 4 hours',
            'inactive_cleanup_days': 30,
            'incident_cleanup_days': 7,
        }
    },
    'custom-business': {
        'template': 'rpz_custom_business.j2',
        'zone_prefix': 'rpz.custom-business',
        'description': 'Custom Business Rules',
        'default_ttl': 60,
        'default_variables': {
            'rule_categories': ['Business'],
            'executive_exceptions': [],
            'compliance_rules': [],
            'partner_access': [],
            'project_rules': [],
            'business_hours_rules': [],
            'cost_management': [],
        }
    },
}

# Fallback template for unknown categories
DEFAULT_TEMPLATE = {
    'template': 'rpz_category.j2',
    'zone_prefix': 'rpz.unknown',
    'description': 'Unknown Category',
    'default_ttl': 300,
    'default_variables': {}
}


def get_template_for_category(category: str) -> Dict[str, Any]:
    """
    Get the appropriate template configuration for an RPZ category.
    
    Args:
        category: The RPZ category name
        
    Returns:
        Dictionary containing template configuration
    """
    return RPZ_TEMPLATE_MAPPING.get(category, DEFAULT_TEMPLATE)


def get_template_variables(category: str, custom_variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get template variables for a specific category with custom overrides.
    
    Args:
        category: The RPZ category name
        custom_variables: Custom variables to override defaults
        
    Returns:
        Dictionary of template variables
    """
    template_config = get_template_for_category(category)
    variables = template_config['default_variables'].copy()
    
    # Add common variables
    variables.update({
        'zone_name': template_config['zone_prefix'],
        'category': category,
        'generated_at': datetime.now(),
        'ttl': template_config['default_ttl'],
        'primary_ns': 'localhost.',
        'admin_email': 'admin.localhost.',
    })
    
    # Override with custom variables if provided
    if custom_variables:
        variables.update(custom_variables)
    
    return variables


def get_available_categories() -> Dict[str, str]:
    """
    Get a list of all available RPZ categories and their descriptions.
    
    Returns:
        Dictionary mapping category names to descriptions
    """
    return {
        category: config['description']
        for category, config in RPZ_TEMPLATE_MAPPING.items()
    }


def is_category_supported(category: str) -> bool:
    """
    Check if a category has a specialized template.
    
    Args:
        category: The RPZ category name
        
    Returns:
        True if category has specialized template, False otherwise
    """
    return category in RPZ_TEMPLATE_MAPPING


def get_template_name(category: str) -> str:
    """
    Get the template filename for a category.
    
    Args:
        category: The RPZ category name
        
    Returns:
        Template filename
    """
    template_config = get_template_for_category(category)
    return template_config['template']


def get_zone_prefix(category: str) -> str:
    """
    Get the default zone prefix for a category.
    
    Args:
        category: The RPZ category name
        
    Returns:
        Zone prefix (e.g., 'rpz.malware')
    """
    template_config = get_template_for_category(category)
    return template_config['zone_prefix']


# Category groupings for UI organization
CATEGORY_GROUPS = {
    'Security': ['malware', 'phishing', 'ransomware'],
    'Content Filtering': ['adult', 'gambling', 'safesearch'],
    'Productivity': ['social-media', 'streaming'],
    'Custom': ['custom', 'custom-block', 'custom-allow', 'custom-redirect', 'custom-temporary', 'custom-business'],
}


def get_category_group(category: str) -> str:
    """
    Get the group that a category belongs to.
    
    Args:
        category: The RPZ category name
        
    Returns:
        Group name or 'Other' if not found
    """
    for group, categories in CATEGORY_GROUPS.items():
        if category in categories:
            return group
    return 'Other'


def get_categories_by_group() -> Dict[str, Dict[str, str]]:
    """
    Get categories organized by groups.
    
    Returns:
        Dictionary with groups as keys and category dictionaries as values
    """
    result = {}
    for group, categories in CATEGORY_GROUPS.items():
        result[group] = {
            cat: RPZ_TEMPLATE_MAPPING[cat]['description']
            for cat in categories
            if cat in RPZ_TEMPLATE_MAPPING
        }
    return result


# Threat Feed Template Functions
def get_threat_feed_template_for_type(feed_type: str) -> Dict[str, Any]:
    """
    Get the appropriate threat feed template configuration for a feed type.
    
    Args:
        feed_type: The threat feed type (malware, phishing, adult, etc.)
        
    Returns:
        Dictionary containing template configuration
    """
    return THREAT_FEED_TEMPLATE_MAPPING.get(feed_type, {
        'template': 'rpz_threat_feed.j2',  # Fallback to generic template
        'zone_prefix': f'rpz.{feed_type}',
        'description': f'{feed_type.title()} Threat Feed',
        'default_ttl': 300,
        'default_variables': {}
    })


def get_threat_feed_template_variables(feed_type: str, custom_variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get template variables for a specific threat feed type with custom overrides.
    
    Args:
        feed_type: The threat feed type
        custom_variables: Custom variables to override defaults
        
    Returns:
        Dictionary of template variables
    """
    template_config = get_threat_feed_template_for_type(feed_type)
    variables = template_config['default_variables'].copy()
    
    # Add common variables
    variables.update({
        'feed_zone': template_config['zone_prefix'].replace('rpz.', ''),
        'feed_type': feed_type,
        'generated_at': datetime.now(),
        'ttl': template_config['default_ttl'],
        'primary_ns': 'localhost.',
        'admin_email': 'admin.localhost.',
    })
    
    # Override with custom variables if provided
    if custom_variables:
        variables.update(custom_variables)
    
    return variables


def get_available_threat_feed_types() -> Dict[str, str]:
    """
    Get a list of all available threat feed types and their descriptions.
    
    Returns:
        Dictionary mapping feed types to descriptions
    """
    return {
        feed_type: config['description']
        for feed_type, config in THREAT_FEED_TEMPLATE_MAPPING.items()
    }


def is_threat_feed_type_supported(feed_type: str) -> bool:
    """
    Check if a threat feed type has a specialized template.
    
    Args:
        feed_type: The threat feed type
        
    Returns:
        True if feed type has specialized template, False otherwise
    """
    return feed_type in THREAT_FEED_TEMPLATE_MAPPING


def get_threat_feed_template_name(feed_type: str) -> str:
    """
    Get the template filename for a threat feed type.
    
    Args:
        feed_type: The threat feed type
        
    Returns:
        Template filename
    """
    template_config = get_threat_feed_template_for_type(feed_type)
    return template_config['template']


def get_threat_feed_zone_prefix(feed_type: str) -> str:
    """
    Get the default zone prefix for a threat feed type.
    
    Args:
        feed_type: The threat feed type
        
    Returns:
        Zone prefix (e.g., 'rpz.malware')
    """
    template_config = get_threat_feed_template_for_type(feed_type)
    return template_config['zone_prefix']