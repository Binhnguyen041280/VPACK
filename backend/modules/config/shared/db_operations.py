"""
Shared database operations for V.PACK config routes.

Provides unified database connection handling, change detection,
and data synchronization utilities for the step-based configuration system.
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import Dict, Any, Tuple, Optional, Union
from modules.db_utils.safe_connection import safe_db_connection

# Import db_rwlock conditionally to avoid circular imports
try:
    from modules.scheduler.db_sync import db_rwlock

    DB_RWLOCK_AVAILABLE = True
except ImportError:
    DB_RWLOCK_AVAILABLE = False
    db_rwlock = None


@contextmanager
def safe_connection_wrapper():
    """Unified database connection handling with optional write lock."""
    if DB_RWLOCK_AVAILABLE and db_rwlock:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                yield conn
    else:
        with safe_db_connection() as conn:
            yield conn


def execute_with_change_detection(
    table_name: str, record_id: Union[int, str], new_data: Dict[str, Any], id_column: str = "id"
) -> Tuple[bool, Dict[str, Any]]:
    """
    Compare current data with new data and update only if changes detected.

    Args:
        table_name: Database table name
        record_id: Record identifier
        new_data: New data to compare and potentially save
        id_column: Name of the ID column (default: 'id')

    Returns:
        Tuple of (changed: bool, current_data: dict)
    """
    with safe_connection_wrapper() as conn:
        cursor = conn.cursor()

        # Get current data
        cursor.execute(f"SELECT * FROM {table_name} WHERE {id_column} = ?", (record_id,))
        row = cursor.fetchone()

        if not row:
            # No existing record - this is a new insert
            return True, {}

        # Get column names and build current data dict
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        current_data = dict(zip(columns, row))

        # Compare relevant fields (exclude metadata fields)
        metadata_fields = {"id", "created_at", "updated_at", "last_modified"}

        changed = False
        for key, new_value in new_data.items():
            if key in metadata_fields:
                continue

            current_value = current_data.get(key)

            # Handle JSON fields
            if isinstance(new_value, (list, dict)):
                new_value_str = json.dumps(new_value, sort_keys=True)
                if isinstance(current_value, str):
                    try:
                        current_value_str = json.dumps(json.loads(current_value), sort_keys=True)
                    except (json.JSONDecodeError, TypeError):
                        current_value_str = current_value or ""
                else:
                    current_value_str = json.dumps(current_value or {}, sort_keys=True)

                if new_value_str != current_value_str:
                    changed = True
                    break
            else:
                # Direct comparison for simple values
                if str(new_value or "").strip() != str(current_value or "").strip():
                    changed = True
                    break

        return changed, current_data


def sync_processing_config(video_source_data: Dict[str, Any]) -> bool:
    """
    Sync video source data to processing_config table for backward compatibility.
    Maps source connection info to actual working directory using get_working_path_for_source().

    Args:
        video_source_data: Video source configuration data

    Returns:
        True if sync successful, False otherwise
    """
    try:
        with safe_connection_wrapper() as conn:
            cursor = conn.cursor()

            # Ensure camera_paths column exists
            try:
                cursor.execute(
                    "ALTER TABLE processing_config ADD COLUMN camera_paths TEXT DEFAULT '{}'"
                )
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Extract data for processing_config
            source_type = video_source_data.get("source_type", "local")
            source_name = video_source_data.get("name", "")
            source_path = video_source_data.get("path", "")

            # Map source to actual working directory
            from modules.config.utils import get_working_path_for_source

            input_path = get_working_path_for_source(source_type, source_name, source_path)

            selected_cameras = video_source_data.get("config", {}).get("selected_cameras", [])
            camera_paths = video_source_data.get("config", {}).get("camera_paths", {})

            # Update processing_config
            cursor.execute(
                """
                INSERT OR REPLACE INTO processing_config (
                    id, input_path, selected_cameras, camera_paths,
                    output_path, storage_duration, min_packing_time, max_packing_time,
                    frame_rate, frame_interval, video_buffer, default_frame_mode,
                    db_path, run_default_on_start
                ) VALUES (
                    1, ?, ?, ?,
                    COALESCE((SELECT output_path FROM processing_config WHERE id = 1), '/default/output'),
                    COALESCE((SELECT storage_duration FROM processing_config WHERE id = 1), 30),
                    COALESCE((SELECT min_packing_time FROM processing_config WHERE id = 1), 10),
                    COALESCE((SELECT max_packing_time FROM processing_config WHERE id = 1), 120),
                    COALESCE((SELECT frame_rate FROM processing_config WHERE id = 1), 30),
                    COALESCE((SELECT frame_interval FROM processing_config WHERE id = 1), 5),
                    COALESCE((SELECT video_buffer FROM processing_config WHERE id = 1), 2),
                    COALESCE((SELECT default_frame_mode FROM processing_config WHERE id = 1), 'default'),
                    COALESCE((SELECT db_path FROM processing_config WHERE id = 1), ''),
                    COALESCE((SELECT run_default_on_start FROM processing_config WHERE id = 1), 1)
                )
            """,
                (input_path, json.dumps(selected_cameras), json.dumps(camera_paths)),
            )

            conn.commit()
            return True

    except Exception as e:
        print(f"⚠️ Processing config sync error: {e}")
        return False


def validate_table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.

    Args:
        table_name: Name of the table to check

    Returns:
        True if table exists, False otherwise
    """
    try:
        with safe_connection_wrapper() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """,
                (table_name,),
            )
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"Error checking table existence for {table_name}: {e}")
        return False


def get_column_names(table_name: str) -> list:
    """
    Get list of column names for a table.

    Args:
        table_name: Name of the table

    Returns:
        List of column names
    """
    try:
        with safe_connection_wrapper() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [col[1] for col in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting column names for {table_name}: {e}")
        return []


def ensure_column_exists(
    table_name: str, column_name: str, column_type: str = "TEXT", default_value: str = "''"
) -> bool:
    """
    Ensure a column exists in a table, add if missing.

    Args:
        table_name: Name of the table
        column_name: Name of the column to ensure exists
        column_type: SQL column type (default: TEXT)
        default_value: Default value for the column

    Returns:
        True if column exists or was added successfully
    """
    try:
        existing_columns = get_column_names(table_name)
        if column_name in existing_columns:
            return True

        with safe_connection_wrapper() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
            )
            conn.commit()
            print(f"Added column {column_name} to {table_name}")
            return True

    except Exception as e:
        print(f"Error ensuring column {column_name} in {table_name}: {e}")
        return False
