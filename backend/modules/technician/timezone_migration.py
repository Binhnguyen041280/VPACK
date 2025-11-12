#!/usr/bin/env python3
"""
Database migration for timezone-aware event detection system.

This module handles the migration of the events table to support timezone-aware
timestamp storage and event processing. It adds necessary columns and ensures
backward compatibility with existing data.

Migration Components:
- Add timezone_info column to events table
- Add timezone_metadata table for timezone configuration
- Add indexes for improved query performance
- Migrate existing data to UTC-aware format

Usage:
    from modules.technician.timezone_migration import run_timezone_migration
    run_timezone_migration()
"""

import os
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import json

from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.config.logging_config import get_logger
from zoneinfo import ZoneInfo

logger = get_logger(__name__)


def check_timezone_migration_needed() -> bool:
    """Check if timezone migration is needed for the events table."""
    try:
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Check if timezone_info column exists
                cursor.execute("PRAGMA table_info(events)")
                columns = [row[1] for row in cursor.fetchall()]

                has_timezone_info = "timezone_info" in columns

                if not has_timezone_info:
                    logger.info("Timezone migration needed: timezone_info column missing")
                    return True

                # Check if timezone_metadata table exists
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='timezone_metadata'"
                )
                has_timezone_metadata = cursor.fetchone() is not None

                if not has_timezone_metadata:
                    logger.info("Timezone migration needed: timezone_metadata table missing")
                    return True

                logger.info("Timezone migration not needed: all components present")
                return False

    except Exception as e:
        logger.error(f"Error checking timezone migration status: {e}")
        return False


def add_timezone_columns() -> bool:
    """Add timezone-related columns to the events table."""
    try:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Add timezone_info column if it doesn't exist
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN timezone_info TEXT")
                    logger.info("✅ Added timezone_info column to events table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info("timezone_info column already exists")
                    else:
                        raise e

                # Add created_at_utc column for new events
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN created_at_utc INTEGER")
                    logger.info("✅ Added created_at_utc column to events table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info("created_at_utc column already exists")
                    else:
                        raise e

                # Add updated_at_utc column for tracking changes
                try:
                    cursor.execute("ALTER TABLE events ADD COLUMN updated_at_utc INTEGER")
                    logger.info("✅ Added updated_at_utc column to events table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info("updated_at_utc column already exists")
                    else:
                        raise e

                conn.commit()
                return True

    except Exception as e:
        logger.error(f"Error adding timezone columns: {e}")
        return False


def create_timezone_metadata_table() -> bool:
    """Create timezone metadata table for system timezone configuration."""
    try:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Create timezone_metadata table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS timezone_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        system_timezone TEXT NOT NULL,
                        migration_version INTEGER NOT NULL DEFAULT 1,
                        migration_timestamp INTEGER NOT NULL,
                        utc_storage_enabled BOOLEAN NOT NULL DEFAULT 1,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                """
                )

                # Create indexes for performance
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_timezone_metadata_migration_version 
                    ON timezone_metadata(migration_version)
                """
                )

                # Insert initial metadata if table is empty
                cursor.execute("SELECT COUNT(*) FROM timezone_metadata")
                count = cursor.fetchone()[0]

                if count == 0:
                    user_timezone_name = "Asia/Ho_Chi_Minh"
                    current_utc_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

                    cursor.execute(
                        """
                        INSERT INTO timezone_metadata 
                        (system_timezone, migration_version, migration_timestamp, utc_storage_enabled, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            user_timezone_name,
                            1,
                            current_utc_timestamp,
                            True,
                            current_utc_timestamp,
                            current_utc_timestamp,
                        ),
                    )

                    logger.info(
                        f"✅ Created timezone_metadata table with system timezone: {user_timezone_name}"
                    )

                conn.commit()
                return True

    except Exception as e:
        logger.error(f"Error creating timezone metadata table: {e}")
        return False


def add_timezone_indexes() -> bool:
    """Add performance indexes for timezone-aware queries."""
    try:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Index for UTC timestamp queries
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_packing_time_utc 
                    ON events(packing_time_start, packing_time_end)
                """
                )

                # Index for timezone-aware queries
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_timezone_camera 
                    ON events(camera_name, packing_time_start)
                """
                )

                # Index for event processing with timezone
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_processed_timezone 
                    ON events(is_processed, packing_time_start, camera_name)
                """
                )

                conn.commit()
                logger.info("✅ Added timezone performance indexes")
                return True

    except Exception as e:
        logger.error(f"Error adding timezone indexes: {e}")
        return False


def migrate_existing_events() -> bool:
    """Migrate existing events to include timezone information."""
    try:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Get events without timezone info
                cursor.execute(
                    """
                    SELECT event_id, packing_time_start, packing_time_end, camera_name 
                    FROM events 
                    WHERE timezone_info IS NULL
                    LIMIT 1000
                """
                )
                events = cursor.fetchall()

                if not events:
                    logger.info("No events need timezone migration")
                    return True

                logger.info(f"Migrating {len(events)} events to timezone-aware format")

                # Get current user timezone for migration
                user_timezone = ZoneInfo("Asia/Ho_Chi_Minh")
                user_timezone_name = "Asia/Ho_Chi_Minh"

                # Calculate timezone offset
                now = datetime.now(user_timezone)
                utc_offset_seconds = now.utcoffset().total_seconds() if now.utcoffset() else 0

                # Default timezone info for existing events
                default_timezone_info = {
                    "video_timezone": user_timezone_name,
                    "utc_offset_seconds": utc_offset_seconds,
                    "stored_as_utc": True,
                    "migrated_from_local": True,
                    "migration_timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # Update events in batches
                current_utc_timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

                for event in events:
                    event_id, packing_time_start, packing_time_end, camera_name = event

                    cursor.execute(
                        """
                        UPDATE events 
                        SET timezone_info = ?, updated_at_utc = ?
                        WHERE event_id = ?
                    """,
                        (json.dumps(default_timezone_info), current_utc_timestamp, event_id),
                    )

                conn.commit()
                logger.info(f"✅ Migrated {len(events)} events with default timezone info")
                return True

    except Exception as e:
        logger.error(f"Error migrating existing events: {e}")
        return False


def run_timezone_migration() -> Dict[str, Any]:
    """
    Run complete timezone migration for the event detection system.

    Returns:
        Dict containing migration results and status
    """
    migration_results = {
        "success": False,
        "steps_completed": [],
        "steps_failed": [],
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "error": None,
    }

    try:
        logger.info("🔄 Starting timezone migration for event detection system")

        # Check if migration is needed
        if not check_timezone_migration_needed():
            migration_results["success"] = True
            migration_results["steps_completed"].append("migration_not_needed")
            migration_results["end_time"] = datetime.now(timezone.utc).isoformat()
            logger.info("✅ Timezone migration completed (no changes needed)")
            return migration_results

        # Step 1: Add timezone columns
        if add_timezone_columns():
            migration_results["steps_completed"].append("add_timezone_columns")
            logger.info("✅ Step 1: Added timezone columns")
        else:
            migration_results["steps_failed"].append("add_timezone_columns")
            raise Exception("Failed to add timezone columns")

        # Step 2: Create timezone metadata table
        if create_timezone_metadata_table():
            migration_results["steps_completed"].append("create_timezone_metadata_table")
            logger.info("✅ Step 2: Created timezone metadata table")
        else:
            migration_results["steps_failed"].append("create_timezone_metadata_table")
            raise Exception("Failed to create timezone metadata table")

        # Step 3: Add performance indexes
        if add_timezone_indexes():
            migration_results["steps_completed"].append("add_timezone_indexes")
            logger.info("✅ Step 3: Added timezone performance indexes")
        else:
            migration_results["steps_failed"].append("add_timezone_indexes")
            raise Exception("Failed to add timezone indexes")

        # Step 4: Migrate existing events
        if migrate_existing_events():
            migration_results["steps_completed"].append("migrate_existing_events")
            logger.info("✅ Step 4: Migrated existing events")
        else:
            migration_results["steps_failed"].append("migrate_existing_events")
            raise Exception("Failed to migrate existing events")

        migration_results["success"] = True
        migration_results["end_time"] = datetime.now(timezone.utc).isoformat()

        logger.info("✅ Timezone migration completed successfully")
        logger.info(f"   - Steps completed: {migration_results['steps_completed']}")

        return migration_results

    except Exception as e:
        migration_results["error"] = str(e)
        migration_results["end_time"] = datetime.now(timezone.utc).isoformat()
        logger.error(f"❌ Timezone migration failed: {e}")
        return migration_results


if __name__ == "__main__":
    # Run migration directly
    result = run_timezone_migration()
    if result["success"]:
        print("✅ Timezone migration completed successfully")
    else:
        print(f"❌ Timezone migration failed: {result.get('error', 'Unknown error')}")
        exit(1)
