#!/usr/bin/env python3
"""
Database migration script to simplify timezone schema.
Replaces complex timezone columns with simple IANA timezone strings.
Part of the timezone migration from custom modules to zoneinfo.
"""
import sqlite3
import os
import logging
from datetime import datetime
from modules.db_utils import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_database():
    """Create a backup of the database before migration."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'events.db')
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Simple file copy
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
            
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return None

def simplify_general_info_timezone():
    """Simplify the general_info table timezone columns."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(general_info)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        logger.info(f"Current general_info columns: {column_names}")
        
        # Check if we need to simplify timezone columns
        timezone_columns_to_remove = [
            'timezone_iana_name', 'timezone_display_name', 'timezone_utc_offset_hours',
            'timezone_format_type', 'timezone_validated', 'timezone_updated_at',
            'timezone_validation_warnings'
        ]
        
        columns_to_remove = [col for col in timezone_columns_to_remove if col in column_names]
        
        if not columns_to_remove:
            logger.info("No complex timezone columns found. Schema is already simplified.")
            return True
            
        # Update any UTC+7 format values to Asia/Ho_Chi_Minh
        logger.info("Converting legacy timezone formats to IANA standard...")
        
        # Update timezone column to standardize values
        if 'timezone' in column_names:
            cursor.execute("""
                UPDATE general_info 
                SET timezone = 'Asia/Ho_Chi_Minh' 
                WHERE timezone IN ('UTC+7', 'GMT+7', 'UTC+07:00', 'Asia/Saigon', 'ICT')
                   OR timezone IS NULL
                   OR timezone = ''
            """)
            updated_rows = cursor.rowcount
            logger.info(f"Updated {updated_rows} rows to use Asia/Ho_Chi_Minh timezone")
        
        # Remove complex timezone columns if they exist
        if columns_to_remove:
            logger.info(f"Removing complex timezone columns: {columns_to_remove}")
            
            # Create new table without complex timezone columns
            keep_columns = [col for col in column_names if col not in columns_to_remove]
            columns_def = []
            
            for col in columns:
                col_name, col_type = col[1], col[2]
                if col_name in keep_columns:
                    columns_def.append(f"{col_name} {col_type}")
            
            # Create new simplified table
            cursor.execute(f"""
                CREATE TABLE general_info_new (
                    {', '.join(columns_def)}
                )
            """)
            
            # Copy data to new table
            cursor.execute(f"""
                INSERT INTO general_info_new ({', '.join(keep_columns)})
                SELECT {', '.join(keep_columns)} FROM general_info
            """)
            
            # Replace old table with new one
            cursor.execute("DROP TABLE general_info")
            cursor.execute("ALTER TABLE general_info_new RENAME TO general_info")
            
            logger.info(f"Removed {len(columns_to_remove)} complex timezone columns")
        
        conn.commit()
        logger.info("✅ Timezone schema simplification completed successfully")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to simplify timezone schema: {e}")
        return False
    finally:
        if conn:
            conn.close()

def drop_global_timezone_config_table():
    """Drop the global_timezone_config table if it exists."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='global_timezone_config'
        """)
        
        if cursor.fetchone():
            cursor.execute("DROP TABLE global_timezone_config")
            logger.info("✅ Dropped global_timezone_config table")
        else:
            logger.info("global_timezone_config table doesn't exist - nothing to drop")
            
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to drop global_timezone_config table: {e}")
        return False
    finally:
        if conn:
            conn.close()

def validate_migration():
    """Validate that the migration was successful."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check general_info schema
        cursor.execute("PRAGMA table_info(general_info)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        logger.info(f"Final general_info columns: {column_names}")
        
        # Check timezone values
        cursor.execute("SELECT DISTINCT timezone FROM general_info WHERE timezone IS NOT NULL")
        timezones = [row[0] for row in cursor.fetchall()]
        logger.info(f"Timezone values in database: {timezones}")
        
        # Validate all timezones are IANA format
        for tz in timezones:
            if tz not in ['Asia/Ho_Chi_Minh']:
                logger.warning(f"Non-standard timezone found: {tz}")
        
        logger.info("✅ Migration validation completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration validation failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting timezone schema migration...")
    
    # Step 1: Backup database
    backup_path = backup_database()
    if not backup_path:
        logger.error("❌ Cannot proceed without database backup")
        exit(1)
    
    # Step 2: Simplify general_info timezone columns
    if not simplify_general_info_timezone():
        logger.error("❌ Failed to simplify timezone schema")
        exit(1)
    
    # Step 3: Drop global_timezone_config table
    if not drop_global_timezone_config_table():
        logger.error("❌ Failed to drop global timezone config table")
        exit(1)
    
    # Step 4: Validate migration
    if not validate_migration():
        logger.error("❌ Migration validation failed")
        exit(1)
    
    logger.info("🎉 Timezone schema migration completed successfully!")
    logger.info(f"Database backup available at: {backup_path}")