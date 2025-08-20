"""
DNS Record Import/Export service for handling various formats
"""

import csv
import json
import re
from io import StringIO
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..schemas.dns import (
    RecordImportFormat, RecordExportFormat, RecordImportResult, RecordExportResult,
    DNSRecordCreate, DNSRecord
)
from ..models.dns import DNSRecord as DNSRecordModel, Zone
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class RecordImportExportService:
    """Service for importing and exporting DNS records in various formats"""
    
    def __init__(self):
        self.supported_record_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS']
    
    async def import_records(self, format_type: RecordImportFormat, data: str, 
                           zone_name: str, validate_only: bool = False) -> RecordImportResult:
        """Import DNS records from various formats"""
        logger.info(f"Importing records in {format_type} format for zone {zone_name}")
        
        try:
            if format_type == RecordImportFormat.BIND_ZONE:
                return await self._import_bind_zone(data, zone_name, validate_only)
            elif format_type == RecordImportFormat.CSV:
                return await self._import_csv(data, zone_name, validate_only)
            elif format_type == RecordImportFormat.JSON:
                return await self._import_json(data, zone_name, validate_only)
            else:
                return RecordImportResult(
                    success=False,
                    errors=[f"Unsupported import format: {format_type}"]
                )
        except Exception as e:
            logger.error(f"Error importing records: {e}")
            return RecordImportResult(
                success=False,
                errors=[f"Import failed: {str(e)}"]
            )
    
    async def export_records(self, format_type: RecordExportFormat, records: List[DNSRecordModel], 
                           zone_name: str) -> RecordExportResult:
        """Export DNS records to various formats"""
        logger.info(f"Exporting {len(records)} records in {format_type} format for zone {zone_name}")
        
        try:
            if format_type == RecordExportFormat.BIND_ZONE:
                return await self._export_bind_zone(records, zone_name)
            elif format_type == RecordExportFormat.CSV:
                return await self._export_csv(records, zone_name)
            elif format_type == RecordExportFormat.JSON:
                return await self._export_json(records, zone_name)
            else:
                return RecordExportResult(
                    success=False,
                    errors=[f"Unsupported export format: {format_type}"]
                )
        except Exception as e:
            logger.error(f"Error exporting records: {e}")
            return RecordExportResult(
                success=False,
                errors=[f"Export failed: {str(e)}"]
            )
    
    async def _import_bind_zone(self, data: str, zone_name: str, validate_only: bool) -> RecordImportResult:
        """Import records from BIND zone file format"""
        logger.debug(f"Importing BIND zone format for {zone_name}")
        
        records = []
        errors = []
        warnings = []
        line_number = 0
        
        # Parse zone file line by line
        for line in data.split('\n'):
            line_number += 1
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith(';'):
                continue
            
            # Skip SOA records (handled separately)
            if 'SOA' in line.upper():
                continue
            
            try:
                record_data = self._parse_bind_zone_line(line, zone_name)
                if record_data:
                    records.append(record_data)
            except ValueError as e:
                errors.append(f"Line {line_number}: {str(e)}")
            except Exception as e:
                errors.append(f"Line {line_number}: Unexpected error - {str(e)}")
        
        # Validate records if not validate_only
        if not validate_only:
            validated_records = []
            for i, record in enumerate(records):
                try:
                    # Basic validation
                    if not record.get('name') or not record.get('record_type') or not record.get('value'):
                        errors.append(f"Record {i+1}: Missing required fields")
                        continue
                    
                    validated_records.append(record)
                except Exception as e:
                    errors.append(f"Record {i+1}: Validation error - {str(e)}")
            
            records = validated_records
        
        success = len(errors) == 0
        
        return RecordImportResult(
            success=success,
            records_imported=len(records) if not validate_only else 0,
            records_validated=len(records),
            errors=errors,
            warnings=warnings,
            records=records if validate_only else None
        )
    
    def _parse_bind_zone_line(self, line: str, zone_name: str) -> Optional[Dict[str, Any]]:
        """Parse a single line from a BIND zone file"""
        # Handle different BIND zone file formats
        parts = line.split()
        if len(parts) < 3:
            return None
        
        # Determine if first part is a name or if it's implied from previous record
        if parts[0].isdigit() or parts[0].upper() in self.supported_record_types:
            # No name specified, use zone name or previous name
            name = '@'
            ttl_or_class = parts[0]
            record_type = parts[1] if len(parts) > 1 else None
            value_parts = parts[2:] if len(parts) > 2 else []
        else:
            name = parts[0]
            ttl_or_class = parts[1] if len(parts) > 1 else None
            record_type = parts[2] if len(parts) > 2 else None
            value_parts = parts[3:] if len(parts) > 3 else []
        
        # Handle TTL and class
        ttl = None
        if ttl_or_class and ttl_or_class.isdigit():
            ttl = int(ttl_or_class)
        elif ttl_or_class and ttl_or_class.upper() in ['IN', 'CH', 'HS']:
            # Class specified, no TTL
            pass
        
        if not record_type or record_type.upper() not in self.supported_record_types:
            raise ValueError(f"Unsupported or missing record type: {record_type}")
        
        # Join value parts
        value = ' '.join(value_parts) if value_parts else ''
        
        # Handle special cases for different record types
        priority = None
        weight = None
        port = None
        
        if record_type.upper() == 'MX' and len(value_parts) >= 2:
            priority = int(value_parts[0])
            value = ' '.join(value_parts[1:])
        elif record_type.upper() == 'SRV' and len(value_parts) >= 4:
            priority = int(value_parts[0])
            weight = int(value_parts[1])
            port = int(value_parts[2])
            value = ' '.join(value_parts[3:])
        
        # Convert @ to zone name
        if name == '@':
            name = zone_name
        elif not name.endswith('.') and name != zone_name:
            name = f"{name}.{zone_name}"
        
        return {
            'name': name.rstrip('.'),
            'record_type': record_type.upper(),
            'value': value.strip('"'),
            'ttl': ttl,
            'priority': priority,
            'weight': weight,
            'port': port
        }
    
    async def _import_csv(self, data: str, zone_name: str, validate_only: bool) -> RecordImportResult:
        """Import records from CSV format"""
        logger.debug(f"Importing CSV format for {zone_name}")
        
        records = []
        errors = []
        warnings = []
        
        try:
            csv_reader = csv.DictReader(StringIO(data))
            
            # Validate CSV headers
            required_headers = ['name', 'type', 'value']
            optional_headers = ['ttl', 'priority', 'weight', 'port']
            
            if not all(header in csv_reader.fieldnames for header in required_headers):
                missing = [h for h in required_headers if h not in csv_reader.fieldnames]
                return RecordImportResult(
                    success=False,
                    errors=[f"Missing required CSV headers: {', '.join(missing)}"]
                )
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header row
                try:
                    # Clean and validate row data
                    record_data = {
                        'name': row['name'].strip(),
                        'record_type': row['type'].strip().upper(),
                        'value': row['value'].strip(),
                        'ttl': int(row['ttl']) if row.get('ttl') and row['ttl'].strip() else None,
                        'priority': int(row['priority']) if row.get('priority') and row['priority'].strip() else None,
                        'weight': int(row['weight']) if row.get('weight') and row['weight'].strip() else None,
                        'port': int(row['port']) if row.get('port') and row['port'].strip() else None
                    }
                    
                    # Basic validation
                    if not record_data['name'] or not record_data['record_type'] or not record_data['value']:
                        errors.append(f"Row {row_num}: Missing required fields")
                        continue
                    
                    if record_data['record_type'] not in self.supported_record_types:
                        errors.append(f"Row {row_num}: Unsupported record type '{record_data['record_type']}'")
                        continue
                    
                    records.append(record_data)
                    
                except ValueError as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: Unexpected error - {str(e)}")
        
        except Exception as e:
            return RecordImportResult(
                success=False,
                errors=[f"CSV parsing error: {str(e)}"]
            )
        
        success = len(errors) == 0
        
        return RecordImportResult(
            success=success,
            records_imported=len(records) if not validate_only else 0,
            records_validated=len(records),
            errors=errors,
            warnings=warnings,
            records=records if validate_only else None
        )
    
    async def _import_json(self, data: str, zone_name: str, validate_only: bool) -> RecordImportResult:
        """Import records from JSON format"""
        logger.debug(f"Importing JSON format for {zone_name}")
        
        try:
            json_data = json.loads(data)
        except json.JSONDecodeError as e:
            return RecordImportResult(
                success=False,
                errors=[f"Invalid JSON format: {str(e)}"]
            )
        
        records = []
        errors = []
        warnings = []
        
        # Handle different JSON structures
        if isinstance(json_data, list):
            # Array of record objects
            record_list = json_data
        elif isinstance(json_data, dict) and 'records' in json_data:
            # Object with records array
            record_list = json_data['records']
        else:
            return RecordImportResult(
                success=False,
                errors=["JSON must be an array of records or an object with 'records' property"]
            )
        
        for i, record_data in enumerate(record_list):
            try:
                if not isinstance(record_data, dict):
                    errors.append(f"Record {i+1}: Must be an object")
                    continue
                
                # Validate required fields
                required_fields = ['name', 'type', 'value']
                missing_fields = [field for field in required_fields if not record_data.get(field)]
                if missing_fields:
                    errors.append(f"Record {i+1}: Missing required fields: {', '.join(missing_fields)}")
                    continue
                
                # Clean and validate record data
                clean_record = {
                    'name': str(record_data['name']).strip(),
                    'record_type': str(record_data['type']).strip().upper(),
                    'value': str(record_data['value']).strip(),
                    'ttl': int(record_data['ttl']) if record_data.get('ttl') else None,
                    'priority': int(record_data['priority']) if record_data.get('priority') else None,
                    'weight': int(record_data['weight']) if record_data.get('weight') else None,
                    'port': int(record_data['port']) if record_data.get('port') else None
                }
                
                if clean_record['record_type'] not in self.supported_record_types:
                    errors.append(f"Record {i+1}: Unsupported record type '{clean_record['record_type']}'")
                    continue
                
                records.append(clean_record)
                
            except ValueError as e:
                errors.append(f"Record {i+1}: {str(e)}")
            except Exception as e:
                errors.append(f"Record {i+1}: Unexpected error - {str(e)}")
        
        success = len(errors) == 0
        
        return RecordImportResult(
            success=success,
            records_imported=len(records) if not validate_only else 0,
            records_validated=len(records),
            errors=errors,
            warnings=warnings,
            records=records if validate_only else None
        )
    
    async def _export_bind_zone(self, records: List[DNSRecordModel], zone_name: str) -> RecordExportResult:
        """Export records to BIND zone file format"""
        logger.debug(f"Exporting to BIND zone format for {zone_name}")
        
        try:
            lines = []
            lines.append(f"; Zone file for {zone_name}")
            lines.append(f"; Generated on {datetime.utcnow().isoformat()}Z")
            lines.append("")
            
            # Group records by name for better readability
            records_by_name = {}
            for record in records:
                if not record.is_active:
                    continue
                
                name = record.name
                if name == zone_name:
                    name = "@"
                elif name.endswith(f".{zone_name}"):
                    name = name[:-len(zone_name)-1]
                
                if name not in records_by_name:
                    records_by_name[name] = []
                records_by_name[name].append(record)
            
            # Sort names for consistent output
            for name in sorted(records_by_name.keys()):
                name_records = records_by_name[name]
                
                for record in sorted(name_records, key=lambda r: (r.record_type, r.value)):
                    line_parts = [name.ljust(20)]
                    
                    # Add TTL if specified
                    if record.ttl:
                        line_parts.append(str(record.ttl))
                    
                    line_parts.append("IN")
                    line_parts.append(record.record_type)
                    
                    # Handle record type-specific formatting
                    if record.record_type == 'MX':
                        line_parts.append(str(record.priority or 10))
                        line_parts.append(record.value)
                    elif record.record_type == 'SRV':
                        line_parts.extend([
                            str(record.priority or 0),
                            str(record.weight or 0),
                            str(record.port or 0),
                            record.value
                        ])
                    elif record.record_type == 'TXT':
                        # Quote TXT records
                        line_parts.append(f'"{record.value}"')
                    else:
                        line_parts.append(record.value)
                    
                    lines.append(" ".join(line_parts))
                
                lines.append("")  # Empty line between different names
            
            content = "\n".join(lines)
            
            return RecordExportResult(
                success=True,
                content=content,
                filename=f"{zone_name}.zone",
                content_type="text/plain"
            )
            
        except Exception as e:
            logger.error(f"Error exporting BIND zone: {e}")
            return RecordExportResult(
                success=False,
                errors=[f"BIND zone export failed: {str(e)}"]
            )
    
    async def _export_csv(self, records: List[DNSRecordModel], zone_name: str) -> RecordExportResult:
        """Export records to CSV format"""
        logger.debug(f"Exporting to CSV format for {zone_name}")
        
        try:
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['name', 'type', 'value', 'ttl', 'priority', 'weight', 'port', 'active'])
            
            # Write records
            for record in records:
                writer.writerow([
                    record.name,
                    record.record_type,
                    record.value,
                    record.ttl or '',
                    record.priority or '',
                    record.weight or '',
                    record.port or '',
                    'yes' if record.is_active else 'no'
                ])
            
            content = output.getvalue()
            output.close()
            
            return RecordExportResult(
                success=True,
                content=content,
                filename=f"{zone_name}_records.csv",
                content_type="text/csv"
            )
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return RecordExportResult(
                success=False,
                errors=[f"CSV export failed: {str(e)}"]
            )
    
    async def _export_json(self, records: List[DNSRecordModel], zone_name: str) -> RecordExportResult:
        """Export records to JSON format"""
        logger.debug(f"Exporting to JSON format for {zone_name}")
        
        try:
            records_data = []
            
            for record in records:
                record_dict = {
                    'name': record.name,
                    'type': record.record_type,
                    'value': record.value,
                    'active': record.is_active
                }
                
                # Add optional fields if they exist
                if record.ttl:
                    record_dict['ttl'] = record.ttl
                if record.priority is not None:
                    record_dict['priority'] = record.priority
                if record.weight is not None:
                    record_dict['weight'] = record.weight
                if record.port is not None:
                    record_dict['port'] = record.port
                
                records_data.append(record_dict)
            
            export_data = {
                'zone': zone_name,
                'exported_at': datetime.utcnow().isoformat() + 'Z',
                'record_count': len(records_data),
                'records': records_data
            }
            
            content = json.dumps(export_data, indent=2)
            
            return RecordExportResult(
                success=True,
                content=content,
                filename=f"{zone_name}_records.json",
                content_type="application/json"
            )
            
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            return RecordExportResult(
                success=False,
                errors=[f"JSON export failed: {str(e)}"]
            )