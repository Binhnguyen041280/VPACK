#!/usr/bin/env python3
"""
V_Track Production Migration Pre-flight Checks
Validates environment and database before executing timezone migration.
"""

import os
import sys
import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

def check_database_exists(db_path: str) -> dict:
    """Check if database file exists and is accessible"""
    result = {'status': 'pass', 'messages': []}
    
    if not os.path.exists(db_path):
        result['status'] = 'fail'
        result['messages'].append(f"Database file not found: {db_path}")
        return result
    
    if not os.access(db_path, os.R_OK):
        result['status'] = 'fail'
        result['messages'].append(f"Database file not readable: {db_path}")
        return result
    
    if not os.access(db_path, os.W_OK):
        result['status'] = 'fail'
        result['messages'].append(f"Database file not writable: {db_path}")
        return result
    
    # Check database size
    db_size = os.path.getsize(db_path)
    result['messages'].append(f"Database size: {db_size:,} bytes ({db_size/1024/1024:.1f} MB)")
    
    return result

def check_database_integrity(db_path: str) -> dict:
    """Check database integrity"""
    result = {'status': 'pass', 'messages': []}
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Run integrity check
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        
        if integrity_result != 'ok':
            result['status'] = 'fail'
            result['messages'].append(f"Database integrity check failed: {integrity_result}")
        else:
            result['messages'].append("Database integrity check passed")
        
        # Check if database is locked
        try:
            cursor.execute("BEGIN EXCLUSIVE TRANSACTION")
            cursor.execute("ROLLBACK")
            result['messages'].append("Database lock test passed")
        except sqlite3.OperationalError as e:
            result['status'] = 'fail'
            result['messages'].append(f"Database appears to be locked: {e}")
        
        conn.close()
        
    except Exception as e:
        result['status'] = 'fail'
        result['messages'].append(f"Database connection error: {e}")
    
    return result

def check_disk_space(backup_dir: str, db_path: str) -> dict:
    """Check available disk space for backups"""
    result = {'status': 'pass', 'messages': []}
    
    try:
        # Get database size
        db_size = os.path.getsize(db_path)
        
        # Check backup directory space
        backup_stat = shutil.disk_usage(os.path.dirname(backup_dir) if os.path.exists(backup_dir) else os.getcwd())
        available_space = backup_stat.free
        
        # Need at least 3x database size for backups (primary, secondary, SQL dump)
        required_space = db_size * 3
        safety_margin = required_space * 1.5  # 50% safety margin
        
        result['messages'].append(f"Available disk space: {available_space:,} bytes ({available_space/1024/1024:.1f} MB)")
        result['messages'].append(f"Required space: {required_space:,} bytes ({required_space/1024/1024:.1f} MB)")
        result['messages'].append(f"Recommended space (with safety margin): {safety_margin:,} bytes ({safety_margin/1024/1024:.1f} MB)")
        
        if available_space < required_space:
            result['status'] = 'fail'
            result['messages'].append("Insufficient disk space for backups")
        elif available_space < safety_margin:
            result['status'] = 'warning'
            result['messages'].append("Disk space is tight, consider freeing up space")
        else:
            result['messages'].append("Sufficient disk space available")
            
    except Exception as e:
        result['status'] = 'fail'
        result['messages'].append(f"Error checking disk space: {e}")
    
    return result

def check_backup_directory(backup_dir: str) -> dict:
    """Check backup directory accessibility"""
    result = {'status': 'pass', 'messages': []}
    
    backup_path = Path(backup_dir)
    
    # Create backup directory if it doesn't exist
    try:
        backup_path.mkdir(parents=True, exist_ok=True)
        result['messages'].append(f"Backup directory created/verified: {backup_dir}")
    except Exception as e:
        result['status'] = 'fail'
        result['messages'].append(f"Cannot create backup directory: {e}")
        return result
    
    # Check write permissions
    try:
        test_file = backup_path / "write_test.tmp"
        test_file.write_text("test")
        test_file.unlink()
        result['messages'].append("Backup directory write test passed")
    except Exception as e:
        result['status'] = 'fail'
        result['messages'].append(f"Backup directory not writable: {e}")
    
    return result

def analyze_current_timestamps(db_path: str) -> dict:
    """Analyze current timestamp data in database"""
    result = {'status': 'pass', 'messages': [], 'data': {}}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        timestamp_analysis = {}
        
        for table_name in tables:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Find timestamp columns
            timestamp_columns = []
            for col in columns:
                col_name, col_type = col[1], col[2]
                if any(keyword in col_name.lower() for keyword in [
                    'time', 'timestamp', 'date', 'created_at', 'updated_at',
                    'expires_at', 'activated_at', 'sent_at', 'last_login', 'first_login'
                ]):
                    if col_type.upper() in ['TIMESTAMP', 'DATETIME', 'TEXT']:
                        timestamp_columns.append(col_name)
            
            if timestamp_columns:
                # Count rows
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # Sample timestamp formats
                sample_data = {}
                for col_name in timestamp_columns:
                    cursor.execute(f"SELECT {col_name} FROM {table_name} WHERE {col_name} IS NOT NULL LIMIT 5")
                    samples = [row[0] for row in cursor.fetchall()]
                    sample_data[col_name] = samples
                
                timestamp_analysis[table_name] = {
                    'timestamp_columns': timestamp_columns,
                    'row_count': row_count,
                    'samples': sample_data
                }
        
        result['data'] = timestamp_analysis
        
        # Summary
        total_tables = len(timestamp_analysis)
        total_rows = sum(data['row_count'] for data in timestamp_analysis.values())
        total_columns = sum(len(data['timestamp_columns']) for data in timestamp_analysis.values())
        
        result['messages'].append(f"Found {total_tables} tables with timestamp columns")
        result['messages'].append(f"Total rows to migrate: {total_rows:,}")
        result['messages'].append(f"Total timestamp columns: {total_columns}")
        
        if total_rows > 100000:
            result['messages'].append("WARNING: Large dataset detected. Migration may take longer.")
        
        conn.close()
        
    except Exception as e:
        result['status'] = 'fail'
        result['messages'].append(f"Error analyzing timestamps: {e}")
    
    return result

def check_dependencies() -> dict:
    """Check required dependencies"""
    result = {'status': 'pass', 'messages': []}
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 7):
        result['status'] = 'fail'
        result['messages'].append(f"Python 3.7+ required, found {python_version.major}.{python_version.minor}")
    else:
        result['messages'].append(f"Python version check passed: {python_version.major}.{python_version.minor}")
    
    # Check required modules
    required_modules = ['sqlite3', 'json', 'pathlib', 'datetime', 'shutil']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        result['status'] = 'fail'
        result['messages'].append(f"Missing required modules: {', '.join(missing_modules)}")
    else:
        result['messages'].append("All required modules available")
    
    return result

def estimate_migration_time(db_path: str) -> dict:
    """Estimate migration time based on data volume"""
    result = {'status': 'pass', 'messages': []}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables with timestamp columns
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        total_timestamp_rows = 0
        
        for table_name in tables:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Count timestamp columns
            timestamp_columns = []
            for col in columns:
                col_name, col_type = col[1], col[2]
                if any(keyword in col_name.lower() for keyword in [
                    'time', 'timestamp', 'date', 'created_at', 'updated_at'
                ]):
                    if col_type.upper() in ['TIMESTAMP', 'DATETIME', 'TEXT']:
                        timestamp_columns.append(col_name)
            
            if timestamp_columns:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                total_timestamp_rows += row_count * len(timestamp_columns)
        
        # Estimate processing rate: ~500 timestamp conversions per second
        processing_rate = 500
        estimated_seconds = total_timestamp_rows / processing_rate
        
        result['messages'].append(f"Total timestamp fields to process: {total_timestamp_rows:,}")
        result['messages'].append(f"Estimated processing time: {estimated_seconds:.1f} seconds ({estimated_seconds/60:.1f} minutes)")
        
        if estimated_seconds > 300:  # 5 minutes
            result['status'] = 'warning'
            result['messages'].append("WARNING: Migration may take longer than 5 minutes")
        
        conn.close()
        
    except Exception as e:
        result['status'] = 'fail'
        result['messages'].append(f"Error estimating migration time: {e}")
    
    return result

def run_pre_flight_checks(db_path: str = "database/events.db", backup_dir: str = "migration_backups") -> dict:
    """Run all pre-flight checks"""
    
    print("V_Track Timezone Migration Pre-flight Checks")
    print("=" * 50)
    
    checks = {
        'database_exists': check_database_exists(db_path),
        'database_integrity': check_database_integrity(db_path),
        'disk_space': check_disk_space(backup_dir, db_path),
        'backup_directory': check_backup_directory(backup_dir),
        'dependencies': check_dependencies(),
        'timestamp_analysis': analyze_current_timestamps(db_path),
        'time_estimate': estimate_migration_time(db_path)
    }
    
    # Print results
    overall_status = 'pass'
    has_warnings = False
    
    for check_name, check_result in checks.items():
        status_icon = "✅" if check_result['status'] == 'pass' else "⚠️" if check_result['status'] == 'warning' else "❌"
        print(f"\n{status_icon} {check_name.replace('_', ' ').title()}")
        
        for message in check_result['messages']:
            print(f"   {message}")
        
        if check_result['status'] == 'fail':
            overall_status = 'fail'
        elif check_result['status'] == 'warning':
            has_warnings = True
    
    # Final recommendation
    print("\n" + "=" * 50)
    print("OVERALL ASSESSMENT:")
    
    if overall_status == 'fail':
        print("❌ MIGRATION NOT RECOMMENDED")
        print("   Critical issues found that must be resolved before migration.")
        return {'status': 'fail', 'checks': checks}
    elif has_warnings:
        print("⚠️  MIGRATION POSSIBLE WITH CAUTION")
        print("   Warnings detected. Review carefully before proceeding.")
        return {'status': 'warning', 'checks': checks}
    else:
        print("✅ MIGRATION READY")
        print("   All checks passed. Safe to proceed with migration.")
        return {'status': 'pass', 'checks': checks}

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='V_Track Migration Pre-flight Checks')
    parser.add_argument('--database', default='database/events.db', help='Path to database file')
    parser.add_argument('--backup-dir', default='migration_backups', help='Backup directory path')
    parser.add_argument('--json-output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Run checks
    results = run_pre_flight_checks(args.database, args.backup_dir)
    
    # Save JSON output if requested
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {args.json_output}")
    
    # Exit code based on results
    sys.exit(0 if results['status'] in ['pass', 'warning'] else 1)

if __name__ == "__main__":
    main()