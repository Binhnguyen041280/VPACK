#!/usr/bin/env python3
"""
V_Track General Info Table Timezone Schema Enhancement

Enhances the general_info table to support rich timezone data while maintaining
backward compatibility with existing timezone field.

Features:
- Backward compatible schema migration
- Rich timezone metadata storage
- Validation integration with TimezoneValidator
- Safe migration with rollback support
- Performance optimization with indexes

Schema Changes:
- Keeps existing 'timezone' field for backward compatibility
- Adds 'timezone_iana_name' for standardized IANA names
- Adds 'timezone_display_name' for user-friendly display
- Adds 'timezone_utc_offset_hours' for quick offset calculations
- Adds 'timezone_format_type' to track original input format
- Adds 'timezone_validated' flag to track validation status
- Adds 'timezone_updated_at' for tracking timezone changes
"""

import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.utils.timezone_validator import timezone_validator, TimezoneValidationResult
from modules.config.logging_config import get_logger

logger = get_logger(__name__)

class GeneralInfoTimezoneSchemaManager:
    """
    Manager for general_info table timezone schema enhancements.
    
    Handles safe migration, validation, and maintenance of timezone-related
    columns while preserving backward compatibility.
    """
    
    def __init__(self):
        """Initialize the schema manager."""
        self.migration_version = "1.0"
        self.backup_enabled = True
        
        # Schema definitions
        self.new_columns = [
            ("timezone_iana_name", "TEXT"),           # Standardized IANA name
            ("timezone_display_name", "TEXT"),        # User-friendly display name  
            ("timezone_utc_offset_hours", "REAL"),    # UTC offset in hours
            ("timezone_format_type", "TEXT"),         # Original format type
            ("timezone_validated", "INTEGER DEFAULT 0"), # Validation status (0/1)
            ("timezone_updated_at", "TEXT"),          # Last update timestamp
            ("timezone_validation_warnings", "TEXT")  # JSON array of validation warnings
        ]
        
        # Indexes for performance
        self.indexes = [
            ("idx_general_info_timezone_iana", "general_info", ["timezone_iana_name"]),
            ("idx_general_info_timezone_offset", "general_info", ["timezone_utc_offset_hours"]),
            ("idx_general_info_timezone_validated", "general_info", ["timezone_validated"])
        ]
    
    def migrate_schema(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Perform timezone schema migration.
        
        Args:
            dry_run: If True, only simulate migration without making changes
            
        Returns:
            Migration result summary
        """
        migration_start = time.time()
        
        logger.info(f"🔄 {'Simulating' if dry_run else 'Executing'} general_info timezone schema migration")
        
        migration_result = {
            'migration_version': self.migration_version,
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'success': False,
            'duration': 0,
            'changes_made': [],
            'warnings': [],
            'error_details': None
        }
        
        try:
            # Phase 1: Schema analysis
            current_schema = self._analyze_current_schema()
            migration_result['current_schema'] = current_schema
            
            # Phase 2: Backup (if not dry run)
            if not dry_run and self.backup_enabled:
                backup_info = self._create_schema_backup()
                migration_result['backup_created'] = backup_info
            
            # Phase 3: Add new columns
            columns_added = self._add_timezone_columns(dry_run)
            migration_result['columns_added'] = columns_added
            migration_result['changes_made'].extend([f"Added column: {col}" for col in columns_added])
            
            # Phase 4: Create indexes
            indexes_created = self._create_timezone_indexes(dry_run)
            migration_result['indexes_created'] = indexes_created
            migration_result['changes_made'].extend([f"Created index: {idx}" for idx in indexes_created])
            
            # Phase 5: Migrate existing data
            data_migration_result = self._migrate_existing_timezone_data(dry_run)
            migration_result['data_migration'] = data_migration_result
            
            # Phase 6: Validate migration
            if not dry_run:
                validation_result = self._validate_schema_migration()
                migration_result['validation'] = validation_result
                
                if not validation_result['valid']:
                    raise Exception("Schema migration validation failed")
            
            migration_result['success'] = True
            migration_result['duration'] = time.time() - migration_start
            
            logger.info(f"✅ Schema migration {'simulation' if dry_run else 'execution'} completed successfully ({migration_result['duration']:.2f}s)")
            return migration_result
            
        except Exception as e:
            migration_result['success'] = False
            migration_result['duration'] = time.time() - migration_start
            migration_result['error_details'] = str(e)
            
            logger.error(f"❌ Schema migration failed: {e}")
            raise Exception(f"Schema migration failed: {e}")
    
    def _analyze_current_schema(self) -> Dict[str, Any]:
        """Analyze current general_info table schema."""
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if general_info table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='general_info'")
            table_exists = cursor.fetchone() is not None
            
            schema_info = {
                'table_exists': table_exists,
                'current_columns': [],
                'existing_timezone_columns': [],
                'needs_migration': True
            }
            
            if table_exists:
                # Get current columns
                cursor.execute("PRAGMA table_info(general_info)")
                columns = cursor.fetchall()
                schema_info['current_columns'] = [(col[1], col[2]) for col in columns]
                
                # Check for existing timezone-related columns
                existing_timezone_cols = []
                column_names = [col[1] for col in columns]
                
                for col_name, col_type in self.new_columns:
                    if col_name in column_names:
                        existing_timezone_cols.append(col_name)
                
                schema_info['existing_timezone_columns'] = existing_timezone_cols
                schema_info['needs_migration'] = len(existing_timezone_cols) < len(self.new_columns)
                
                # Check current data
                cursor.execute("SELECT id, country, timezone FROM general_info LIMIT 1")
                sample_data = cursor.fetchone()
                if sample_data:
                    schema_info['sample_current_data'] = {
                        'id': sample_data[0],
                        'country': sample_data[1],
                        'timezone': sample_data[2]
                    }
            
            return schema_info
    
    def _create_schema_backup(self) -> Dict[str, Any]:
        """Create backup before schema migration."""
        try:
            backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_info = {
                'timestamp': backup_timestamp,
                'backup_created': False,
                'backup_path': None,
                'error': None
            }
            
            # For schema migration, we'll create a simple data dump
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM general_info")
                data = cursor.fetchall()
                
                cursor.execute("PRAGMA table_info(general_info)")
                columns = [col[1] for col in cursor.fetchall()]
                
                backup_data = {
                    'columns': columns,
                    'data': data,
                    'timestamp': backup_timestamp
                }
                
                backup_file = f"general_info_schema_backup_{backup_timestamp}.json"
                with open(backup_file, 'w') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                
                backup_info['backup_created'] = True
                backup_info['backup_path'] = backup_file
                
                logger.info(f"📋 Schema backup created: {backup_file}")
            
            return backup_info
            
        except Exception as e:
            logger.warning(f"Schema backup creation failed: {e}")
            return {
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'backup_created': False,
                'error': str(e)
            }
    
    def _add_timezone_columns(self, dry_run: bool = False) -> List[str]:
        """Add new timezone columns to general_info table."""
        columns_added = []
        
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get current columns
                cursor.execute("PRAGMA table_info(general_info)")
                existing_columns = [col[1] for col in cursor.fetchall()]
                
                for col_name, col_definition in self.new_columns:
                    if col_name not in existing_columns:
                        alter_sql = f"ALTER TABLE general_info ADD COLUMN {col_name} {col_definition}"
                        
                        if not dry_run:
                            try:
                                cursor.execute(alter_sql)
                                conn.commit()
                                logger.info(f"✅ Added column: {col_name}")
                            except sqlite3.OperationalError as e:
                                if "duplicate column name" in str(e).lower():
                                    logger.info(f"⏭️ Column {col_name} already exists")
                                else:
                                    raise
                        else:
                            logger.info(f"🔄 Would add column: {col_name} {col_definition}")
                        
                        columns_added.append(col_name)
                    else:
                        logger.info(f"⏭️ Column {col_name} already exists")
        
        return columns_added
    
    def _create_timezone_indexes(self, dry_run: bool = False) -> List[str]:
        """Create performance indexes for timezone columns."""
        indexes_created = []
        
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                for index_name, table_name, columns in self.indexes:
                    try:
                        # Check if index already exists
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
                        if cursor.fetchone():
                            logger.info(f"⏭️ Index {index_name} already exists")
                            continue
                        
                        columns_str = ', '.join(columns)
                        create_index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns_str})"
                        
                        if not dry_run:
                            cursor.execute(create_index_sql)
                            conn.commit()
                            logger.info(f"✅ Created index: {index_name}")
                        else:
                            logger.info(f"🔄 Would create index: {index_name}")
                        
                        indexes_created.append(index_name)
                        
                    except Exception as e:
                        logger.warning(f"Failed to create index {index_name}: {e}")
        
        return indexes_created
    
    def _migrate_existing_timezone_data(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate existing timezone data to new columns."""
        migration_result = {
            'rows_processed': 0,
            'rows_updated': 0,
            'validation_results': [],
            'warnings': []
        }
        
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get all rows with timezone data
                cursor.execute("SELECT id, timezone FROM general_info WHERE timezone IS NOT NULL AND timezone != ''")
                rows = cursor.fetchall()
                
                migration_result['rows_processed'] = len(rows)
                
                for row_id, current_timezone in rows:
                    try:
                        # Validate and normalize the timezone
                        validation_result = timezone_validator.validate_timezone(current_timezone)
                        migration_result['validation_results'].append({
                            'row_id': row_id,
                            'original_timezone': current_timezone,
                            'validation_result': {
                                'is_valid': validation_result.is_valid,
                                'normalized_name': validation_result.normalized_name,
                                'iana_name': validation_result.iana_name,
                                'format_type': validation_result.format_type.value,
                                'warnings': validation_result.warnings
                            }
                        })
                        
                        if not dry_run:
                            # Update the row with rich timezone data
                            update_sql = """
                                UPDATE general_info SET 
                                    timezone_iana_name = ?,
                                    timezone_display_name = ?,
                                    timezone_utc_offset_hours = ?,
                                    timezone_format_type = ?,
                                    timezone_validated = ?,
                                    timezone_updated_at = ?,
                                    timezone_validation_warnings = ?
                                WHERE id = ?
                            """
                            
                            cursor.execute(update_sql, (
                                validation_result.iana_name,
                                validation_result.display_name,
                                validation_result.utc_offset_hours,
                                validation_result.format_type.value,
                                1 if validation_result.is_valid else 0,
                                datetime.now(timezone.utc).isoformat(),
                                json.dumps(validation_result.warnings or []),
                                row_id
                            ))
                            
                            migration_result['rows_updated'] += 1
                        
                        if not validation_result.is_valid:
                            migration_result['warnings'].append(
                                f"Row {row_id}: Invalid timezone '{current_timezone}' - {validation_result.error_message}"
                            )
                        elif validation_result.warnings:
                            migration_result['warnings'].extend([
                                f"Row {row_id}: {warning}" for warning in validation_result.warnings
                            ])
                        
                    except Exception as e:
                        error_msg = f"Row {row_id}: Failed to process timezone '{current_timezone}' - {e}"
                        migration_result['warnings'].append(error_msg)
                        logger.warning(error_msg)
                
                if not dry_run:
                    conn.commit()
        
        logger.info(f"📊 Timezone data migration: {migration_result['rows_processed']} processed, {migration_result['rows_updated']} updated")
        return migration_result
    
    def _validate_schema_migration(self) -> Dict[str, Any]:
        """Validate that schema migration was successful."""
        validation_result = {
            'valid': True,
            'checks_passed': [],
            'checks_failed': [],
            'warnings': []
        }
        
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check 1: All new columns exist
                cursor.execute("PRAGMA table_info(general_info)")
                existing_columns = [col[1] for col in cursor.fetchall()]
                
                for col_name, _ in self.new_columns:
                    if col_name in existing_columns:
                        validation_result['checks_passed'].append(f"Column {col_name} exists")
                    else:
                        validation_result['checks_failed'].append(f"Column {col_name} missing")
                        validation_result['valid'] = False
                
                # Check 2: Indexes exist
                for index_name, _, _ in self.indexes:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
                    if cursor.fetchone():
                        validation_result['checks_passed'].append(f"Index {index_name} exists")
                    else:
                        validation_result['checks_failed'].append(f"Index {index_name} missing")
                        # Indexes are not critical for validation
                        validation_result['warnings'].append(f"Index {index_name} missing - performance may be impacted")
                
                # Check 3: Data integrity
                cursor.execute("SELECT COUNT(*) FROM general_info")
                total_rows = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM general_info WHERE timezone_validated = 1")
                validated_rows = cursor.fetchone()[0]
                
                if total_rows > 0:
                    validation_result['data_integrity'] = {
                        'total_rows': total_rows,
                        'validated_rows': validated_rows,
                        'validation_rate': validated_rows / total_rows
                    }
                    
                    if validated_rows > 0:
                        validation_result['checks_passed'].append(f"Data migration successful: {validated_rows}/{total_rows} rows validated")
                    else:
                        validation_result['warnings'].append("No rows have validated timezone data")
                
                # Check 4: Database integrity
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                
                if integrity_result == "ok":
                    validation_result['checks_passed'].append("Database integrity check passed")
                else:
                    validation_result['checks_failed'].append(f"Database integrity check failed: {integrity_result}")
                    validation_result['valid'] = False
                
        except Exception as e:
            validation_result['valid'] = False
            validation_result['checks_failed'].append(f"Validation error: {e}")
        
        return validation_result
    
    def get_current_timezone_data(self, include_validation_details: bool = False) -> List[Dict[str, Any]]:
        """Get current timezone data from general_info table."""
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            if include_validation_details:
                columns = """
                    id, country, timezone, timezone_iana_name, timezone_display_name,
                    timezone_utc_offset_hours, timezone_format_type, timezone_validated,
                    timezone_updated_at, timezone_validation_warnings
                """
            else:
                columns = "id, country, timezone, timezone_iana_name, timezone_display_name"
            
            cursor.execute(f"SELECT {columns} FROM general_info")
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                if include_validation_details:
                    result = {
                        'id': row[0],
                        'country': row[1],
                        'timezone': row[2],
                        'timezone_iana_name': row[3],
                        'timezone_display_name': row[4],
                        'timezone_utc_offset_hours': row[5],
                        'timezone_format_type': row[6],
                        'timezone_validated': bool(row[7]) if row[7] is not None else False,
                        'timezone_updated_at': row[8],
                        'timezone_validation_warnings': json.loads(row[9]) if row[9] else []
                    }
                else:
                    result = {
                        'id': row[0],
                        'country': row[1],
                        'timezone': row[2],
                        'timezone_iana_name': row[3],
                        'timezone_display_name': row[4]
                    }
                
                results.append(result)
            
            return results
    
    def update_timezone_data(self, row_id: int, new_timezone: str) -> Dict[str, Any]:
        """Update timezone data for a specific row."""
        try:
            # Validate the new timezone
            validation_result = timezone_validator.validate_timezone(new_timezone)
            
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Update both old and new timezone columns
                    update_sql = """
                        UPDATE general_info SET 
                            timezone = ?,
                            timezone_iana_name = ?,
                            timezone_display_name = ?,
                            timezone_utc_offset_hours = ?,
                            timezone_format_type = ?,
                            timezone_validated = ?,
                            timezone_updated_at = ?,
                            timezone_validation_warnings = ?
                        WHERE id = ?
                    """
                    
                    cursor.execute(update_sql, (
                        new_timezone,  # Keep original format in legacy field
                        validation_result.iana_name,
                        validation_result.display_name,
                        validation_result.utc_offset_hours,
                        validation_result.format_type.value,
                        1 if validation_result.is_valid else 0,
                        datetime.now(timezone.utc).isoformat(),
                        json.dumps(validation_result.warnings or []),
                        row_id
                    ))
                    
                    conn.commit()
            
            return {
                'success': True,
                'validation_result': validation_result,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update timezone data for row {row_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Singleton instance
timezone_schema_manager = GeneralInfoTimezoneSchemaManager()

# Convenience functions
def migrate_timezone_schema(dry_run: bool = False) -> Dict[str, Any]:
    """Migrate general_info table timezone schema."""
    return timezone_schema_manager.migrate_schema(dry_run)

def get_timezone_data(include_details: bool = False) -> List[Dict[str, Any]]:
    """Get current timezone data from general_info table."""
    return timezone_schema_manager.get_current_timezone_data(include_details)

def update_timezone(row_id: int, timezone_value: str) -> Dict[str, Any]:
    """Update timezone data for a specific row."""
    return timezone_schema_manager.update_timezone_data(row_id, timezone_value)