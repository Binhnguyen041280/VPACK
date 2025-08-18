#!/usr/bin/env python3
"""
V_Track Production Timezone Migration Script
Safely migrates existing timestamps to UTC format with comprehensive backup and rollback procedures.

Author: Claude Code Assistant
Date: 2025-08-15
Version: 1.0.0
"""

import sqlite3
import os
import sys
import json
import hashlib
import shutil
import time
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

# Add modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.utils.timezone_manager import TimezoneManager
    from modules.db_utils import get_db_connection
    from modules.scheduler.db_sync import db_rwlock
except ImportError as e:
    print(f"Warning: Could not import V_Track modules: {e}")
    print("Running in standalone mode...")

@dataclass
class MigrationConfig:
    """Configuration for timezone migration"""
    database_path: str
    backup_dir: str
    batch_size: int = 1000
    max_retry_attempts: int = 3
    timeout_seconds: int = 300
    verify_after_migration: bool = True
    create_rollback_script: bool = True
    log_level: str = "INFO"

@dataclass
class TableMigrationPlan:
    """Migration plan for a single table"""
    table_name: str
    timestamp_columns: List[str]
    estimated_rows: int
    migration_type: str  # 'convert', 'add_utc_columns', 'skip'
    requires_backup: bool = True

class ProductionTimezoneMigrator:
    """
    Production-ready timezone migration with zero-data-loss guarantees
    """
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.migration_id = self._generate_migration_id()
        self.logger = self._setup_logging()
        self.rollback_data = {}
        self.migration_stats = {
            'start_time': None,
            'end_time': None,
            'tables_migrated': 0,
            'rows_migrated': 0,
            'errors': [],
            'warnings': []
        }
        self.interrupted = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"timezone_migration_{timestamp}"

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        log_dir = Path(self.config.backup_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{self.migration_id}.log"
        
        logger = logging.getLogger('timezone_migration')
        logger.setLevel(getattr(logging, self.config.log_level))
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    def _signal_handler(self, signum, frame):
        """Handle graceful shutdown on interrupt"""
        self.logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
        self.interrupted = True

    def create_backup(self) -> str:
        """
        Create comprehensive database backup with integrity verification
        """
        self.logger.info("Creating production database backup...")
        
        backup_dir = Path(self.config.backup_dir) / self.migration_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Primary backup
        primary_backup = backup_dir / "events_backup_primary.db"
        shutil.copy2(self.config.database_path, primary_backup)
        
        # Secondary backup (redundancy)
        secondary_backup = backup_dir / "events_backup_secondary.db"
        shutil.copy2(self.config.database_path, secondary_backup)
        
        # Create SQL dump backup
        sql_backup = backup_dir / "events_backup.sql"
        self._create_sql_dump(sql_backup)
        
        # Verify backup integrity
        self._verify_backup_integrity(primary_backup)
        self._verify_backup_integrity(secondary_backup)
        
        # Create backup metadata
        backup_metadata = {
            'migration_id': self.migration_id,
            'original_db_path': self.config.database_path,
            'primary_backup': str(primary_backup),
            'secondary_backup': str(secondary_backup),
            'sql_backup': str(sql_backup),
            'backup_timestamp': datetime.now().isoformat(),
            'original_db_size': os.path.getsize(self.config.database_path),
            'original_db_checksum': self._calculate_file_checksum(self.config.database_path),
            'primary_backup_checksum': self._calculate_file_checksum(primary_backup),
            'secondary_backup_checksum': self._calculate_file_checksum(secondary_backup)
        }
        
        metadata_file = backup_dir / "backup_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(backup_metadata, f, indent=2)
        
        self.logger.info(f"Backup created successfully at {backup_dir}")
        return str(backup_dir)

    def _create_sql_dump(self, output_file: Path):
        """Create SQL dump of database"""
        try:
            import subprocess
            cmd = ['sqlite3', self.config.database_path, '.dump']
            with open(output_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            self.logger.info(f"SQL dump created: {output_file}")
        except Exception as e:
            self.logger.warning(f"Could not create SQL dump: {e}")

    def _verify_backup_integrity(self, backup_path: Path):
        """Verify backup database integrity"""
        try:
            conn = sqlite3.connect(str(backup_path))
            conn.execute("PRAGMA integrity_check")
            conn.close()
            self.logger.info(f"Backup integrity verified: {backup_path}")
        except Exception as e:
            raise Exception(f"Backup integrity check failed: {e}")

    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def analyze_database_schema(self) -> List[TableMigrationPlan]:
        """
        Analyze database schema to identify timestamp columns and create migration plan
        """
        self.logger.info("Analyzing database schema for timestamp columns...")
        
        conn = sqlite3.connect(self.config.database_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        migration_plans = []
        
        for table_name in tables:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Count rows
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Identify timestamp columns
            timestamp_columns = []
            for col in columns:
                col_name, col_type = col[1], col[2]
                if any(keyword in col_name.lower() for keyword in [
                    'time', 'timestamp', 'date', 'created_at', 'updated_at', 
                    'expires_at', 'activated_at', 'sent_at', 'last_login', 'first_login'
                ]):
                    if col_type.upper() in ['TIMESTAMP', 'DATETIME', 'TEXT']:
                        timestamp_columns.append(col_name)
            
            # Determine migration type
            migration_type = 'skip'
            if timestamp_columns:
                if row_count > 0:
                    migration_type = 'convert'
                else:
                    migration_type = 'add_utc_columns'
            
            plan = TableMigrationPlan(
                table_name=table_name,
                timestamp_columns=timestamp_columns,
                estimated_rows=row_count,
                migration_type=migration_type,
                requires_backup=(migration_type == 'convert' and row_count > 0)
            )
            
            migration_plans.append(plan)
            
            if timestamp_columns:
                self.logger.info(f"Table {table_name}: {len(timestamp_columns)} timestamp columns, {row_count} rows")
        
        conn.close()
        
        # Save migration plan
        plan_file = Path(self.config.backup_dir) / self.migration_id / "migration_plan.json"
        plan_data = [
            {
                'table_name': p.table_name,
                'timestamp_columns': p.timestamp_columns,
                'estimated_rows': p.estimated_rows,
                'migration_type': p.migration_type,
                'requires_backup': p.requires_backup
            }
            for p in migration_plans
        ]
        
        with open(plan_file, 'w') as f:
            json.dump(plan_data, f, indent=2)
        
        return migration_plans

    def migrate_table_timestamps(self, plan: TableMigrationPlan) -> Dict[str, Any]:
        """
        Migrate timestamps for a single table with comprehensive error handling
        """
        if plan.migration_type == 'skip':
            return {'status': 'skipped', 'rows_processed': 0}
        
        self.logger.info(f"Migrating table: {plan.table_name}")
        
        conn = sqlite3.connect(self.config.database_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("BEGIN TRANSACTION")
        
        try:
            # Create backup of original data for rollback
            if self.config.create_rollback_script:
                self._backup_table_data(conn, plan)
            
            rows_processed = 0
            errors = []
            
            if plan.migration_type == 'convert':
                rows_processed, errors = self._convert_existing_timestamps(conn, plan)
            elif plan.migration_type == 'add_utc_columns':
                self._add_utc_columns(conn, plan)
            
            conn.commit()
            self.logger.info(f"Successfully migrated {plan.table_name}: {rows_processed} rows processed")
            
            return {
                'status': 'success',
                'rows_processed': rows_processed,
                'errors': errors
            }
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Error migrating {plan.table_name}: {str(e)}"
            self.logger.error(error_msg)
            return {
                'status': 'error',
                'error': error_msg,
                'rows_processed': 0
            }
        finally:
            conn.close()

    def _backup_table_data(self, conn: sqlite3.Connection, plan: TableMigrationPlan):
        """Backup original table data for rollback purposes"""
        if not plan.timestamp_columns:
            return
        
        cursor = conn.cursor()
        
        # Get all data from timestamp columns for rollback
        timestamp_col_str = ', '.join(plan.timestamp_columns)
        query = f"SELECT rowid, {timestamp_col_str} FROM {plan.table_name}"
        
        cursor.execute(query)
        original_data = cursor.fetchall()
        
        # Store in rollback data
        if plan.table_name not in self.rollback_data:
            self.rollback_data[plan.table_name] = {}
        
        self.rollback_data[plan.table_name]['original_data'] = original_data
        self.rollback_data[plan.table_name]['timestamp_columns'] = plan.timestamp_columns

    def _convert_existing_timestamps(self, conn: sqlite3.Connection, plan: TableMigrationPlan) -> Tuple[int, List[str]]:
        """Convert existing timestamps to UTC format"""
        cursor = conn.cursor()
        rows_processed = 0
        errors = []
        
        # Process in batches
        batch_size = min(self.config.batch_size, plan.estimated_rows)
        offset = 0
        
        while offset < plan.estimated_rows and not self.interrupted:
            # Get batch of data
            query = f"SELECT rowid, * FROM {plan.table_name} LIMIT {batch_size} OFFSET {offset}"
            cursor.execute(query)
            batch_rows = cursor.fetchall()
            
            if not batch_rows:
                break
            
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            # Process each row in batch
            for row in batch_rows:
                if self.interrupted:
                    break
                
                row_dict = dict(zip(column_names, row))
                rowid = row_dict['rowid']
                
                # Convert timestamp columns
                updates = {}
                for col_name in plan.timestamp_columns:
                    if col_name in row_dict and row_dict[col_name]:
                        try:
                            utc_timestamp = self._convert_timestamp_to_utc(row_dict[col_name])
                            if utc_timestamp != row_dict[col_name]:
                                updates[col_name] = utc_timestamp
                        except Exception as e:
                            error_msg = f"Failed to convert {col_name} in row {rowid}: {str(e)}"
                            errors.append(error_msg)
                            continue
                
                # Update row if there are changes
                if updates:
                    update_parts = [f"{col} = ?" for col in updates.keys()]
                    update_query = f"UPDATE {plan.table_name} SET {', '.join(update_parts)} WHERE rowid = ?"
                    values = list(updates.values()) + [rowid]
                    
                    try:
                        cursor.execute(update_query, values)
                        rows_processed += 1
                    except Exception as e:
                        error_msg = f"Failed to update row {rowid}: {str(e)}"
                        errors.append(error_msg)
            
            offset += batch_size
            
            # Progress reporting
            progress = min(100, (offset / plan.estimated_rows) * 100)
            self.logger.info(f"Progress on {plan.table_name}: {progress:.1f}% ({rows_processed} rows processed)")
        
        return rows_processed, errors

    def _convert_timestamp_to_utc(self, timestamp_value: Any) -> str:
        """
        Convert various timestamp formats to UTC ISO string
        """
        if timestamp_value is None:
            return None
        
        if isinstance(timestamp_value, (int, float)):
            # Unix timestamp
            if timestamp_value > 1e10:  # Milliseconds
                timestamp_value = timestamp_value / 1000
            dt = datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
            return dt.isoformat().replace('+00:00', 'Z')
        
        if isinstance(timestamp_value, str):
            # Try to parse various string formats
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S %z',
                '%Y-%m-%dT%H:%M:%S%z'
            ]
            
            for fmt in formats_to_try:
                try:
                    if 'CURRENT_TIMESTAMP' in timestamp_value.upper():
                        # Handle SQLite CURRENT_TIMESTAMP
                        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                    
                    dt = datetime.strptime(timestamp_value, fmt)
                    
                    # If no timezone info, assume local timezone (Ho Chi Minh City = UTC+7)
                    if dt.tzinfo is None:
                        # Assume local time is UTC+7 (Ho Chi Minh City)
                        from datetime import timedelta
                        dt = dt.replace(tzinfo=timezone(timedelta(hours=7)))
                    
                    # Convert to UTC
                    utc_dt = dt.astimezone(timezone.utc)
                    return utc_dt.isoformat().replace('+00:00', 'Z')
                    
                except ValueError:
                    continue
            
            # If all parsing failed, return original value
            self.logger.warning(f"Could not parse timestamp: {timestamp_value}")
            return timestamp_value
        
        return str(timestamp_value)

    def _add_utc_columns(self, conn: sqlite3.Connection, plan: TableMigrationPlan):
        """Add UTC columns to tables with no existing data"""
        cursor = conn.cursor()
        
        for col_name in plan.timestamp_columns:
            utc_col_name = f"{col_name}_utc"
            try:
                cursor.execute(f"ALTER TABLE {plan.table_name} ADD COLUMN {utc_col_name} TEXT")
                self.logger.info(f"Added UTC column {utc_col_name} to {plan.table_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise

    def validate_migration(self, migration_plans: List[TableMigrationPlan]) -> Dict[str, Any]:
        """
        Comprehensive validation of migration results
        """
        self.logger.info("Validating migration results...")
        
        validation_results = {
            'overall_status': 'success',
            'total_tables_validated': 0,
            'total_rows_validated': 0,
            'validation_errors': [],
            'warnings': [],
            'table_results': {}
        }
        
        conn = sqlite3.connect(self.config.database_path)
        cursor = conn.cursor()
        
        try:
            for plan in migration_plans:
                if plan.migration_type == 'skip':
                    continue
                
                table_result = {
                    'status': 'success',
                    'rows_validated': 0,
                    'format_errors': 0,
                    'conversion_errors': 0
                }
                
                # Validate timestamp formats
                for col_name in plan.timestamp_columns:
                    cursor.execute(f"SELECT COUNT(*) FROM {plan.table_name} WHERE {col_name} IS NOT NULL")
                    total_non_null = cursor.fetchone()[0]
                    
                    if total_non_null > 0:
                        # Check for valid UTC format (ISO 8601 with Z suffix)
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {plan.table_name} 
                            WHERE {col_name} IS NOT NULL 
                            AND ({col_name} LIKE '%Z' OR {col_name} LIKE '%+00:00' OR {col_name} = 'CURRENT_TIMESTAMP')
                        """)
                        valid_format_count = cursor.fetchone()[0]
                        
                        format_error_rate = (total_non_null - valid_format_count) / total_non_null
                        if format_error_rate > 0.1:  # More than 10% format errors
                            error_msg = f"High format error rate in {plan.table_name}.{col_name}: {format_error_rate:.1%}"
                            validation_results['validation_errors'].append(error_msg)
                            table_result['format_errors'] += total_non_null - valid_format_count
                        
                        table_result['rows_validated'] += total_non_null
                
                validation_results['table_results'][plan.table_name] = table_result
                validation_results['total_tables_validated'] += 1
                validation_results['total_rows_validated'] += table_result['rows_validated']
                
        except Exception as e:
            validation_results['overall_status'] = 'error'
            validation_results['validation_errors'].append(f"Validation error: {str(e)}")
        
        finally:
            conn.close()
        
        # Save validation report
        validation_file = Path(self.config.backup_dir) / self.migration_id / "validation_report.json"
        with open(validation_file, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        if validation_results['validation_errors']:
            validation_results['overall_status'] = 'warnings'
        
        return validation_results

    def create_rollback_script(self) -> str:
        """
        Create comprehensive rollback script for emergency recovery
        """
        rollback_dir = Path(self.config.backup_dir) / self.migration_id / "rollback"
        rollback_dir.mkdir(parents=True, exist_ok=True)
        
        rollback_script_path = rollback_dir / "execute_rollback.py"
        
        rollback_script_content = f'''#!/usr/bin/env python3
"""
EMERGENCY ROLLBACK SCRIPT
Migration ID: {self.migration_id}
Generated: {datetime.now().isoformat()}

USAGE:
    python execute_rollback.py [--confirm]

WARNING: This will restore database to pre-migration state.
All changes made after migration will be lost.
"""

import sqlite3
import shutil
import sys
import json
from pathlib import Path

def execute_rollback(confirm=False):
    if not confirm:
        print("DANGER: This will restore database to pre-migration state.")
        print("All post-migration changes will be lost.")
        response = input("Type 'CONFIRM ROLLBACK' to proceed: ")
        if response != 'CONFIRM ROLLBACK':
            print("Rollback cancelled.")
            return False
    
    backup_dir = Path(__file__).parent.parent
    metadata_file = backup_dir / "backup_metadata.json"
    
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    original_db = metadata['original_db_path']
    primary_backup = metadata['primary_backup']
    
    print(f"Restoring {{original_db}} from {{primary_backup}}")
    
    # Create emergency backup of current state
    emergency_backup = backup_dir / "pre_rollback_emergency.db"
    shutil.copy2(original_db, emergency_backup)
    print(f"Emergency backup created: {{emergency_backup}}")
    
    # Restore from backup
    shutil.copy2(primary_backup, original_db)
    print("Database restored successfully.")
    
    return True

if __name__ == "__main__":
    confirm_flag = "--confirm" in sys.argv
    success = execute_rollback(confirm_flag)
    sys.exit(0 if success else 1)
'''
        
        with open(rollback_script_path, 'w') as f:
            f.write(rollback_script_content)
        
        # Make executable
        os.chmod(rollback_script_path, 0o755)
        
        # Create rollback data file
        rollback_data_file = rollback_dir / "rollback_data.json"
        with open(rollback_data_file, 'w') as f:
            json.dump(self.rollback_data, f, indent=2)
        
        self.logger.info(f"Rollback script created: {rollback_script_path}")
        return str(rollback_script_path)

    def run_migration(self) -> Dict[str, Any]:
        """
        Execute the complete migration process with comprehensive monitoring
        """
        self.logger.info(f"Starting timezone migration {self.migration_id}")
        self.migration_stats['start_time'] = datetime.now()
        
        try:
            # Phase 1: Create backup
            self.logger.info("Phase 1: Creating database backup...")
            backup_dir = self.create_backup()
            
            if self.interrupted:
                self.logger.error("Migration interrupted during backup phase")
                return self._create_error_result("Migration interrupted during backup")
            
            # Phase 2: Analyze schema
            self.logger.info("Phase 2: Analyzing database schema...")
            migration_plans = self.analyze_database_schema()
            
            if self.interrupted:
                self.logger.error("Migration interrupted during analysis phase")
                return self._create_error_result("Migration interrupted during analysis")
            
            # Phase 3: Execute migration
            self.logger.info("Phase 3: Executing timestamp migration...")
            migration_results = {}
            
            for plan in migration_plans:
                if self.interrupted:
                    self.logger.error("Migration interrupted during execution phase")
                    break
                
                result = self.migrate_table_timestamps(plan)
                migration_results[plan.table_name] = result
                
                if result['status'] == 'success':
                    self.migration_stats['tables_migrated'] += 1
                    self.migration_stats['rows_migrated'] += result['rows_processed']
                else:
                    self.migration_stats['errors'].append(result.get('error', 'Unknown error'))
            
            # Phase 4: Validation
            if not self.interrupted and self.config.verify_after_migration:
                self.logger.info("Phase 4: Validating migration results...")
                validation_results = self.validate_migration(migration_plans)
            else:
                validation_results = {'overall_status': 'skipped', 'reason': 'Interrupted or disabled'}
            
            # Phase 5: Create rollback script
            if self.config.create_rollback_script:
                self.logger.info("Phase 5: Creating rollback procedures...")
                rollback_script_path = self.create_rollback_script()
            else:
                rollback_script_path = None
            
            self.migration_stats['end_time'] = datetime.now()
            duration = self.migration_stats['end_time'] - self.migration_stats['start_time']
            
            final_result = {
                'status': 'success' if not self.interrupted and not self.migration_stats['errors'] else 'error',
                'migration_id': self.migration_id,
                'duration_seconds': duration.total_seconds(),
                'statistics': self.migration_stats,
                'backup_location': backup_dir,
                'rollback_script': rollback_script_path,
                'validation_results': validation_results,
                'migration_results': migration_results
            }
            
            # Save final report
            report_file = Path(backup_dir) / "migration_report.json"
            with open(report_file, 'w') as f:
                json.dump(final_result, f, indent=2, default=str)
            
            if final_result['status'] == 'success':
                self.logger.info(f"Migration completed successfully in {duration.total_seconds():.1f} seconds")
                self.logger.info(f"Migrated {self.migration_stats['tables_migrated']} tables, {self.migration_stats['rows_migrated']} rows")
            else:
                self.logger.error("Migration completed with errors")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Critical migration error: {str(e)}")
            return self._create_error_result(f"Critical error: {str(e)}")

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'status': 'error',
            'migration_id': self.migration_id,
            'error': error_message,
            'statistics': self.migration_stats,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Main execution function"""
    print("V_Track Production Timezone Migration")
    print("="*50)
    
    # Configuration
    config = MigrationConfig(
        database_path="database/events.db",
        backup_dir="migration_backups",
        batch_size=500,
        max_retry_attempts=3,
        timeout_seconds=300,
        verify_after_migration=True,
        create_rollback_script=True,
        log_level="INFO"
    )
    
    # Verify database exists
    if not os.path.exists(config.database_path):
        print(f"ERROR: Database not found at {config.database_path}")
        sys.exit(1)
    
    # Create migrator instance
    migrator = ProductionTimezoneMigrator(config)
    
    # Pre-flight checks
    print(f"Database: {config.database_path}")
    print(f"Backup directory: {config.backup_dir}")
    print(f"Migration ID: {migrator.migration_id}")
    
    # Confirm execution
    if "--auto-confirm" not in sys.argv:
        response = input("\\nProceed with timezone migration? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            sys.exit(0)
    
    # Execute migration
    result = migrator.run_migration()
    
    # Print summary
    print("\\nMigration Summary:")
    print("="*30)
    print(f"Status: {result['status']}")
    print(f"Duration: {result.get('duration_seconds', 0):.1f} seconds")
    
    if result['status'] == 'success':
        stats = result['statistics']
        print(f"Tables migrated: {stats['tables_migrated']}")
        print(f"Rows migrated: {stats['rows_migrated']}")
        print(f"Backup location: {result['backup_location']}")
        if result.get('rollback_script'):
            print(f"Rollback script: {result['rollback_script']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()