#!/usr/bin/env python3
"""
Schema structure validation script.
This script validates that all response schemas are properly defined
and have the necessary fields for serialization.
"""

import os
import re
import ast
from typing import Dict, List, Set, Any


def extract_schema_classes(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Extract schema class definitions from a Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return {}
    
    schemas = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it's a schema class (inherits from BaseModel)
            is_schema = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'BaseModel':
                    is_schema = True
                    break
            
            if is_schema:
                schema_info = {
                    'name': node.name,
                    'fields': [],
                    'validators': [],
                    'config': None,
                    'docstring': ast.get_docstring(node)
                }
                
                # Extract field definitions
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        field_name = item.target.id
                        field_type = ast.unparse(item.annotation) if item.annotation else 'Any'
                        
                        # Check if it has a Field() definition
                        field_info = {
                            'name': field_name,
                            'type': field_type,
                            'has_field': False,
                            'has_default': item.value is not None
                        }
                        
                        if item.value and isinstance(item.value, ast.Call):
                            if isinstance(item.value.func, ast.Name) and item.value.func.id == 'Field':
                                field_info['has_field'] = True
                        
                        schema_info['fields'].append(field_info)
                    
                    elif isinstance(item, ast.FunctionDef) and item.name.startswith('validate_'):
                        schema_info['validators'].append(item.name)
                    
                    elif isinstance(item, ast.ClassDef) and item.name == 'Config':
                        schema_info['config'] = True
                
                schemas[node.name] = schema_info
    
    return schemas


def validate_response_schema_requirements(schema_info: Dict[str, Any]) -> List[str]:
    """Validate that a response schema meets requirements"""
    issues = []
    
    # Response schemas should have from_attributes = True in Config
    if not schema_info.get('config'):
        issues.append("Missing Config class (needed for from_attributes)")
    
    # Check for common required fields in response schemas
    field_names = [f['name'] for f in schema_info['fields']]
    
    # Most response schemas should have an id field
    if schema_info['name'] not in ['PaginatedResponse', 'HealthCheckResult', 'ValidationResult', 
                                   'ZoneValidationResult', 'SystemStatus', 'SystemMetrics', 
                                   'SystemInfo', 'BackupStatus', 'MaintenanceStatus',
                                   'LoginResponse', 'TokenResponse', 'TwoFactorSetupResponse']:
        if 'id' not in field_names:
            issues.append("Response schema missing 'id' field")
    
    # Check for timestamp fields in appropriate schemas
    if schema_info['name'].endswith(('Log', 'Stats', 'Status')):
        timestamp_fields = ['timestamp', 'created_at', 'updated_at', 'checked_at', 'last_updated']
        if not any(field in field_names for field in timestamp_fields):
            issues.append("Time-based schema missing timestamp field")
    
    return issues


def validate_field_definitions(schema_info: Dict[str, Any]) -> List[str]:
    """Validate field definitions in a schema"""
    issues = []
    
    for field in schema_info['fields']:
        # Check for proper typing
        if field['type'] == 'Any':
            issues.append(f"Field '{field['name']}' has generic 'Any' type")
        
        # Optional fields should be properly typed
        if 'Optional[' in field['type'] and not field['has_default']:
            issues.append(f"Optional field '{field['name']}' should have default value")
        
        # List and Dict fields should have proper typing
        if field['type'].startswith(('List', 'Dict')) and '[' not in field['type']:
            issues.append(f"Field '{field['name']}' has untyped collection")
    
    return issues


def check_schema_file(file_path: str) -> Dict[str, List[str]]:
    """Check all schemas in a file"""
    print(f"\nAnalyzing {file_path}...")
    
    schemas = extract_schema_classes(file_path)
    results = {}
    
    for schema_name, schema_info in schemas.items():
        issues = []
        
        # Skip base schemas and enums
        if schema_name.endswith('Base') or schema_name in ['ZoneType', 'RecordType', 'ForwarderType', 
                                                          'RPZAction', 'FeedType', 'FormatType', 
                                                          'UpdateStatus', 'ValueType', 'ConfigCategory',
                                                          'SystemHealthStatus', 'MetricType', 'QueryType',
                                                          'ResourceType']:
            continue
        
        # Check if it's a response schema (not Create/Update)
        if not schema_name.endswith(('Create', 'Update', 'Request', 'Query')):
            issues.extend(validate_response_schema_requirements(schema_info))
        
        # Validate field definitions
        issues.extend(validate_field_definitions(schema_info))
        
        if issues:
            results[schema_name] = issues
        else:
            print(f"  ✓ {schema_name}")
    
    return results


def check_serialization_methods():
    """Check that schemas have proper serialization support"""
    print("\nChecking serialization method implementations...")
    
    schema_files = [
        'app/schemas/dns.py',
        'app/schemas/security.py', 
        'app/schemas/system.py',
        'app/schemas/monitoring.py',
        'app/schemas/auth.py'
    ]
    
    serialization_issues = []
    
    for file_path in schema_files:
        if not os.path.exists(file_path):
            serialization_issues.append(f"Schema file missing: {file_path}")
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for proper imports
        if 'from pydantic import BaseModel' not in content:
            serialization_issues.append(f"{file_path}: Missing BaseModel import")
        
        # Check for Config classes with from_attributes
        if 'from_attributes = True' not in content and 'orm_mode = True' not in content:
            # Some files might not need ORM serialization
            if 'Response' in content or any(x in file_path for x in ['dns.py', 'security.py', 'system.py']):
                serialization_issues.append(f"{file_path}: Missing from_attributes configuration for ORM serialization")
    
    return serialization_issues


def validate_schema_exports():
    """Validate that all schemas are properly exported"""
    print("\nValidating schema exports...")
    
    init_file = 'app/schemas/__init__.py'
    if not os.path.exists(init_file):
        return ["Missing schemas/__init__.py file"]
    
    with open(init_file, 'r', encoding='utf-8') as f:
        init_content = f.read()
    
    issues = []
    
    # Check that response schemas are exported
    response_schemas = [
        'Zone', 'DNSRecord', 'Forwarder', 'ForwarderHealth',
        'ThreatFeed', 'RPZRule', 'SystemConfig', 'SystemStatus',
        'DNSLog', 'SystemStats', 'AuditLog', 'UserInfo'
    ]
    
    for schema in response_schemas:
        if f'"{schema}"' not in init_content and f"'{schema}'" not in init_content:
            issues.append(f"Response schema '{schema}' not exported in __init__.py")
    
    return issues


def main():
    """Run all schema validation checks"""
    print("Starting schema structure validation...\n")
    
    # Change to backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    all_issues = {}
    
    # Check individual schema files
    schema_files = [
        'app/schemas/dns.py',
        'app/schemas/security.py',
        'app/schemas/system.py', 
        'app/schemas/monitoring.py',
        'app/schemas/auth.py'
    ]
    
    for file_path in schema_files:
        if os.path.exists(file_path):
            file_issues = check_schema_file(file_path)
            if file_issues:
                all_issues[file_path] = file_issues
        else:
            all_issues[file_path] = [f"File does not exist: {file_path}"]
    
    # Check serialization methods
    serialization_issues = check_serialization_methods()
    if serialization_issues:
        all_issues['Serialization'] = serialization_issues
    
    # Check schema exports
    export_issues = validate_schema_exports()
    if export_issues:
        all_issues['Exports'] = export_issues
    
    # Report results
    print(f"\n{'='*60}")
    print("VALIDATION RESULTS")
    print(f"{'='*60}")
    
    if not all_issues:
        print("✅ All schema structure validations passed!")
        print("\nKey validations completed:")
        print("  ✓ Response schemas have proper structure")
        print("  ✓ Field definitions are properly typed")
        print("  ✓ Serialization support is configured")
        print("  ✓ Schema exports are complete")
        return 0
    else:
        print("❌ Schema validation issues found:\n")
        
        for category, issues in all_issues.items():
            print(f"{category}:")
            if isinstance(issues, dict):
                for schema_name, schema_issues in issues.items():
                    print(f"  {schema_name}:")
                    for issue in schema_issues:
                        print(f"    - {issue}")
            else:
                for issue in issues:
                    print(f"  - {issue}")
            print()
        
        return 1


if __name__ == "__main__":
    exit(main())