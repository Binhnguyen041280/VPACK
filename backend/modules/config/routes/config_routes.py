from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from typing import Dict, Any, Tuple, Optional
import json
import os
import sqlite3
from datetime import datetime
from modules.db_utils.safe_connection import safe_db_connection
from modules.utils.timezone_validator import TimezoneValidator
# Import db_rwlock conditionally to avoid circular imports
try:
    from modules.scheduler.db_sync import db_rwlock
    DB_RWLOCK_AVAILABLE = True
except ImportError:
    DB_RWLOCK_AVAILABLE = False
    db_rwlock = None
from modules.sources.path_manager import PathManager
from modules.utils.timezone_validator import timezone_validator, get_available_timezones
from modules.utils.timezone_schema_migration import timezone_schema_manager
from ..utils import get_working_path_for_source, load_config

config_routes_bp = Blueprint('config_routes', __name__)

# Load config using shared utility
config = load_config()

@config_routes_bp.route('/save-config', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def save_config():
    """Fixed save_config without frame_settings table dependency"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        video_root = data.get('video_root')
        output_path = data.get('output_path', config.get("output_path", "/default/output"))
        default_days = data.get('default_days', 30)
        min_packing_time = data.get('min_packing_time', 10)
        max_packing_time = data.get('max_packing_time', 120)
        frame_rate = data.get('frame_rate', 30)
        frame_interval = data.get('frame_interval', 5)
        video_buffer = data.get('video_buffer', 2)
        selected_cameras = data.get('selected_cameras', [])
        run_default_on_start = data.get('run_default_on_start', 1)

        print(f"=== SAVE CONFIG REQUEST ===")
        print(f"Raw video_root from frontend: {video_root}")
        print(f"Selected cameras: {selected_cameras}")

        # Enhanced path mapping with better error handling
        try:
            # Try to get active source for path mapping
            try:
                path_manager = PathManager()
                active_sources = path_manager.get_all_active_sources()
                
                if active_sources:
                    active_source = active_sources[0]  # Single active source
                    source_type = active_source['source_type']
                    source_name = active_source['name']
                    source_path = active_source['path']
                    
                    print(f"Found active source: {source_name} ({source_type})")
                    
                    # Apply proper path mapping (NO NVR)
                    correct_working_path = get_working_path_for_source(source_type, source_name, source_path)
                    
                    if video_root != correct_working_path:
                        print(f"Correcting video_root: {video_root} -> {correct_working_path}")
                        video_root = correct_working_path
                    else:
                        print(f"video_root already correct: {video_root}")
                else:
                    print("No active video source found, using video_root as-is")
                    
            except ImportError:
                print("PathManager not available, using video_root as-is")
            except Exception as pm_error:
                print(f"PathManager error: {pm_error}, using video_root as-is")
                
        except Exception as path_error:
            print(f"Error in path mapping: {path_error}")

        # Final validation
        if not video_root or video_root.strip() == "":
            error_msg = "video_root cannot be empty"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        # Basic URL validation
        if '://' in video_root or 'localhost:' in video_root:
            error_msg = f"video_root cannot be a URL: {video_root}"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        print(f"Final video_root for database: {video_root}")

        # FIXED: Consolidate ALL database operations in single context
        try:
            with safe_db_connection() as conn:
                if not conn:
                    return jsonify({"error": "Database connection failed"}), 500
                    
                cursor = conn.cursor()
                
                # Check if processing_config table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='processing_config'
                """)
                if not cursor.fetchone():
                    return jsonify({"error": "processing_config table not found"}), 500
                
                # Add column if not exists (safe operation)
                try:
                    cursor.execute("ALTER TABLE processing_config ADD COLUMN run_default_on_start INTEGER DEFAULT 1")
                    print("Added run_default_on_start column")
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                # Get DB_PATH
                try:
                    from modules.db_utils import find_project_root
                    import os
                    BASE_DIR = find_project_root(os.path.abspath(__file__))
                    DB_PATH = os.path.join(BASE_DIR, "backend/database/events.db")
                except ImportError:
                    # Fallback to default database path
                    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                    DB_PATH = os.path.join(BASE_DIR, "database", "events.db")
                
                # INSERT/UPDATE processing_config (all in same context)
                cursor.execute("""
                    INSERT OR REPLACE INTO processing_config (
                        id, input_path, output_path, storage_duration, min_packing_time, 
                        max_packing_time, frame_rate, frame_interval, video_buffer, default_frame_mode, 
                        selected_cameras, db_path, run_default_on_start
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (1, video_root, output_path, default_days, min_packing_time, max_packing_time, 
                      frame_rate, frame_interval, video_buffer, "default", json.dumps(selected_cameras), 
                      DB_PATH, run_default_on_start))

                print("processing_config updated successfully")

                # Verify what was saved
                cursor.execute("SELECT input_path, selected_cameras, frame_rate, frame_interval FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                if result:
                    saved_path, saved_cameras, saved_fr, saved_fi = result
                    print(f"Verified saved input_path: {saved_path}")
                    print(f"Verified saved cameras: {saved_cameras}")
                    print(f"Verified saved frame_rate: {saved_fr}, frame_interval: {saved_fi}")
                
                # Commit all changes together
                conn.commit()
            
            print("Config saved successfully")
            return jsonify({
                "message": "Configuration saved successfully",
                "saved_path": video_root,
                "saved_cameras": selected_cameras,
                "frame_settings": {
                    "frame_rate": frame_rate,
                    "frame_interval": frame_interval
                }
            }), 200
            
        except Exception as e:
            error_msg = f"Database operation failed: {str(e)}"
            print(f"Database error: {error_msg}")
            return jsonify({"error": error_msg}), 500

    except Exception as e:
        # Catch-all error handler to ensure JSON response
        error_msg = f"Unexpected error: {str(e)}"
        print(f"CRITICAL ERROR in save_config: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/save-general-info', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def save_general_info():
    """Enhanced save general info with timezone validation and rich metadata."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    country = data.get('country')
    timezone_input = data.get('timezone')
    brand_name = data.get('brand_name')
    working_days = data.get('working_days', ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"])
    
    # Bản đồ ngày tiếng Việt sang tiếng Anh
    day_map = {
        'Thứ Hai': 'Monday', 'Thứ Ba': 'Tuesday', 'Thứ Tư': 'Wednesday',
        'Thứ Năm': 'Thursday', 'Thứ Sáu': 'Friday', 'Thứ Bảy': 'Saturday',
        'Chủ Nhật': 'Sunday'
    }
    
    # Chuyển đổi working_days sang tiếng Anh
    working_days_en = [day_map.get(day, day) for day in working_days]
    
    from_time = data.get('from_time', "07:00")
    to_time = data.get('to_time', "23:00")

    # Enhanced timezone validation
    timezone_validation_result = None
    if timezone_input:
        try:
            timezone_validation_result = timezone_validator.validate_timezone(timezone_input)
            if not timezone_validation_result.is_valid:
                # Log warning but don't block save - maintain backward compatibility
                print(f"⚠️ Timezone validation warning: {timezone_validation_result.error_message}")
        except Exception as e:
            print(f"⚠️ Timezone validation error: {e}")

    try:
        # Use db_rwlock if available, otherwise proceed without locking
        if DB_RWLOCK_AVAILABLE and db_rwlock:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    _save_general_info_to_db(conn, country, timezone_input, brand_name, working_days_en, from_time, to_time, timezone_validation_result)
        else:
            with safe_db_connection() as conn:
                _save_general_info_to_db(conn, country, timezone_input, brand_name, working_days_en, from_time, to_time, timezone_validation_result)
                
        # Build response with enhanced timezone info
        response_data = {"message": "General info saved"}
        
        if timezone_validation_result:
            response_data["timezone_validation"] = {
                "is_valid": timezone_validation_result.is_valid,
                "normalized_name": timezone_validation_result.normalized_name,
                "iana_name": timezone_validation_result.iana_name,
                "display_name": timezone_validation_result.display_name,
                "utc_offset_hours": timezone_validation_result.utc_offset_hours,
                "format_type": timezone_validation_result.format_type.value,
                "warnings": timezone_validation_result.warnings or []
            }
            
            if not timezone_validation_result.is_valid:
                response_data["timezone_validation"]["error"] = timezone_validation_result.error_message
                
    except Exception as e:
        error_msg = f"Database error: {str(e)}. Ensure the database is accessible."
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

    print("✅ General info saved with enhanced timezone support:", data)
    return jsonify(response_data), 200

@config_routes_bp.route('/get-general-info', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_general_info():
    """Get general info with enhanced timezone data."""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if enhanced timezone columns exist
            cursor.execute("PRAGMA table_info(general_info)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            has_enhanced_columns = 'timezone_iana_name' in existing_columns
            
            if has_enhanced_columns:
                # Query with enhanced timezone data
                cursor.execute("""
                    SELECT id, country, timezone, brand_name, working_days, from_time, to_time,
                           timezone_iana_name, timezone_display_name, timezone_utc_offset_hours,
                           timezone_format_type, timezone_validated, timezone_updated_at,
                           timezone_validation_warnings
                    FROM general_info WHERE id = 1
                """)
            else:
                # Fallback to basic columns
                cursor.execute("""
                    SELECT id, country, timezone, brand_name, working_days, from_time, to_time
                    FROM general_info WHERE id = 1
                """)
            
            row = cursor.fetchone()
            
            if not row:
                return jsonify({"error": "General info not found"}), 404
            
            # Build response
            response_data = {
                "id": row[0],
                "country": row[1],
                "timezone": row[2],
                "brand_name": row[3],
                "working_days": json.loads(row[4]) if row[4] else [],
                "from_time": row[5],
                "to_time": row[6]
            }
            
            # Add enhanced timezone data if available
            if has_enhanced_columns and len(row) > 7:
                response_data["timezone_enhanced"] = {
                    "iana_name": row[7],
                    "display_name": row[8],
                    "utc_offset_hours": row[9],
                    "format_type": row[10],
                    "validated": bool(row[11]) if row[11] is not None else False,
                    "updated_at": row[12],
                    "warnings": json.loads(row[13]) if row[13] else []
                }
                
                # If timezone is validated, prefer enhanced data
                if response_data["timezone_enhanced"]["validated"]:
                    response_data["timezone_display"] = response_data["timezone_enhanced"]["display_name"]
                    response_data["timezone_normalized"] = response_data["timezone_enhanced"]["iana_name"]
            
            return jsonify(response_data), 200
            
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
        print(f"❌ Get general info error: {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/timezones/available', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_available_timezones():
    """Get list of available timezones with optional filtering."""
    try:
        # Parse query parameters
        common_only = request.args.get('common', 'false').lower() == 'true'
        include_offsets = request.args.get('include_offsets', 'false').lower() == 'true'
        search = request.args.get('search', '').strip()
        
        # Get available timezones
        timezones = get_available_timezones(common_only=common_only)
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            timezones = [tz for tz in timezones if search_lower in tz.lower()]
        
        # Build response
        timezone_list = []
        
        for tz_name in timezones[:100]:  # Limit to 100 results for performance
            tz_info = {
                "name": tz_name,
                "display_name": tz_name.replace('_', ' ')
            }
            
            # Add additional info if requested
            if include_offsets:
                try:
                    validation_result = timezone_validator.validate_timezone(tz_name)
                    if validation_result.is_valid:
                        tz_info["utc_offset_hours"] = validation_result.utc_offset_hours
                        tz_info["display_name"] = validation_result.display_name or tz_info["display_name"]
                        tz_info["format_type"] = validation_result.format_type.value
                except Exception as e:
                    print(f"⚠️ Error getting timezone info for {tz_name}: {e}")
            
            timezone_list.append(tz_info)
        
        # Sort by display name for better UX
        timezone_list.sort(key=lambda x: x["display_name"])
        
        response_data = {
            "timezones": timezone_list,
            "total_count": len(timezone_list),
            "filtered": bool(search),
            "common_only": common_only,
            "include_offsets": include_offsets
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        error_msg = f"Failed to get available timezones: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/timezones/validate', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def validate_timezone_endpoint():
    """Validate a timezone string and return detailed information."""
    try:
        data = request.json
        if not data or 'timezone' not in data:
            return jsonify({"error": "Timezone parameter required"}), 400
        
        timezone_input = data.get('timezone', '').strip()
        if not timezone_input:
            return jsonify({"error": "Timezone cannot be empty"}), 400
        
        # Validate the timezone
        validation_result = timezone_validator.validate_timezone(timezone_input)
        
        response_data = {
            "input": timezone_input,
            "is_valid": validation_result.is_valid,
            "normalized_name": validation_result.normalized_name,
            "original_input": validation_result.original_input,
            "format_type": validation_result.format_type.value,
            "iana_name": validation_result.iana_name,
            "utc_offset_hours": validation_result.utc_offset_hours,
            "utc_offset_seconds": validation_result.utc_offset_seconds,
            "display_name": validation_result.display_name,
            "warnings": validation_result.warnings or []
        }
        
        if not validation_result.is_valid:
            response_data["error_message"] = validation_result.error_message
        
        # Add additional timezone information
        if validation_result.is_valid:
            try:
                tz_info = timezone_validator.get_timezone_info(timezone_input)
                response_data["current_time"] = tz_info.get("current_time")
                response_data["current_offset"] = tz_info.get("current_offset")
            except Exception as e:
                print(f"⚠️ Error getting extended timezone info: {e}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        error_msg = f"Timezone validation error: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/timezones/migrate-schema', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def migrate_timezone_schema():
    """Migrate general_info table to enhanced timezone schema."""
    try:
        data = request.json or {}
        dry_run = data.get('dry_run', True)  # Default to dry run for safety
        
        # Check if user has explicitly confirmed migration
        if not dry_run and not data.get('confirm_migration', False):
            return jsonify({
                "error": "Migration confirmation required. Set 'confirm_migration': true to proceed."
            }), 400
        
        print(f"🔄 {'Simulating' if dry_run else 'Executing'} timezone schema migration...")
        
        # Perform migration
        migration_result = timezone_schema_manager.migrate_schema(dry_run=dry_run)
        
        # Build response
        response_data = {
            "success": migration_result["success"],
            "dry_run": dry_run,
            "migration_version": migration_result["migration_version"],
            "duration": migration_result["duration"],
            "changes_made": migration_result["changes_made"],
            "warnings": migration_result["warnings"]
        }
        
        if migration_result["success"]:
            response_data["message"] = f"Schema migration {'simulated' if dry_run else 'completed'} successfully"
            
            if "columns_added" in migration_result:
                response_data["columns_added"] = migration_result["columns_added"]
            
            if "indexes_created" in migration_result:
                response_data["indexes_created"] = migration_result["indexes_created"]
            
            if "data_migration" in migration_result:
                response_data["data_migration"] = migration_result["data_migration"]
        else:
            response_data["error"] = migration_result.get("error_details", "Migration failed")
        
        status_code = 200 if migration_result["success"] else 500
        return jsonify(response_data), status_code
        
    except Exception as e:
        error_msg = f"Schema migration failed: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

def _save_general_info_to_db(conn, country, timezone_input, brand_name, working_days_en, from_time, to_time, timezone_validation_result):
    """Helper function to save general info to database without circular imports."""
    cursor = conn.cursor()
    
    # Ensure timezone schema is up to date (non-blocking)
    try:
        # Check if enhanced timezone columns exist
        cursor.execute("PRAGMA table_info(general_info)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        has_enhanced_columns = 'timezone_iana_name' in existing_columns
        
        if not has_enhanced_columns:
            print("🔄 Migrating general_info schema for enhanced timezone support...")
            # Perform schema migration in background
            try:
                migration_result = timezone_schema_manager.migrate_schema(dry_run=False)
                if migration_result['success']:
                    print("✅ Enhanced timezone schema migration completed")
                else:
                    print(f"⚠️ Schema migration failed: {migration_result.get('error_details', 'Unknown error')}")
            except Exception as migration_error:
                print(f"⚠️ Schema migration error: {migration_error}")
                # Continue with basic save
    except Exception as schema_check_error:
        print(f"⚠️ Schema check error: {schema_check_error}")
    
    # Save with enhanced timezone data if validation was successful
    if timezone_validation_result and timezone_validation_result.is_valid:
        cursor.execute("""
            INSERT OR REPLACE INTO general_info (
                id, country, timezone, brand_name, working_days, from_time, to_time,
                timezone_iana_name, timezone_display_name, timezone_utc_offset_hours,
                timezone_format_type, timezone_validated, timezone_updated_at,
                timezone_validation_warnings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1, country, timezone_input, brand_name, json.dumps(working_days_en), from_time, to_time,
            timezone_validation_result.iana_name,
            timezone_validation_result.display_name,
            timezone_validation_result.utc_offset_hours,
            timezone_validation_result.format_type.value,
            1,  # timezone_validated = True
            json.dumps(datetime.now().isoformat()),
            json.dumps(timezone_validation_result.warnings or [])
        ))
    else:
        # Fallback to basic save for backward compatibility
        cursor.execute("""
            INSERT OR REPLACE INTO general_info (
                id, country, timezone, brand_name, working_days, from_time, to_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (1, country, timezone_input, brand_name, json.dumps(working_days_en), from_time, to_time))
    
    # Commit changes
    conn.commit()

@config_routes_bp.route('/global-timezone', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_global_timezone():
    """Get global timezone configuration."""
    try:
        from modules.config.global_timezone_config import global_timezone_config
        
        timezone_info = global_timezone_config.get_timezone_info()
        
        return jsonify({
            "timezone_iana": timezone_info.timezone_iana,
            "timezone_display": timezone_info.timezone_display,
            "utc_offset_hours": timezone_info.utc_offset_hours,
            "is_validated": timezone_info.is_validated,
            "last_updated": timezone_info.last_updated.isoformat(),
            "warnings": timezone_info.warnings,
            "source": timezone_info.source
        }), 200
        
    except Exception as e:
        error_msg = f"Failed to get global timezone: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/global-timezone', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def set_global_timezone():
    """Set global timezone configuration."""
    try:
        data = request.json
        if not data or 'timezone' not in data:
            return jsonify({"error": "timezone field is required"}), 400
        
        timezone_iana = data['timezone']
        
        from modules.config.global_timezone_config import global_timezone_config
        
        success, error = global_timezone_config.set_global_timezone(timezone_iana, source='manual')
        
        if success:
            # Clear timezone manager cache to pick up new global setting
            from modules.utils.timezone_manager import timezone_manager
            timezone_manager.clear_cache()
            
            return jsonify({
                "message": "Global timezone updated successfully",
                "timezone": timezone_iana
            }), 200
        else:
            return jsonify({"error": error}), 400
            
    except Exception as e:
        error_msg = f"Failed to set global timezone: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/global-timezone/migrate', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def migrate_to_global_timezone():
    """Migrate from per-camera/general_info timezone to global timezone configuration."""
    try:
        from modules.config.global_timezone_config import global_timezone_config
        
        migration_result = global_timezone_config.migrate_from_general_info()
        
        if migration_result.get('success'):
            # Clear timezone manager cache to pick up new global setting
            from modules.utils.timezone_manager import timezone_manager
            timezone_manager.clear_cache()
            
            return jsonify(migration_result), 200
        else:
            return jsonify(migration_result), 500
            
    except Exception as e:
        error_msg = f"Migration failed: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

# Step 1 Brandname Configuration Endpoints
@config_routes_bp.route('/step/brandname', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_brandname():
    """Get current brandname from general_info table for Step 1."""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT brand_name FROM general_info WHERE id = 1")
            row = cursor.fetchone()
            
            brand_name = row[0] if row else "Alan_go"  # Default value
            
            return jsonify({
                "success": True,
                "data": {
                    "brand_name": brand_name
                }
            }), 200
            
    except Exception as e:
        error_msg = f"Failed to get brandname: {str(e)}"
        print(f"❌ Get brandname error: {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/step/brandname', methods=['PUT'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_step_brandname():
    """Update brandname only if changed for Step 1."""
    try:
        data = request.json
        if not data or 'brand_name' not in data:
            return jsonify({"error": "brand_name field is required"}), 400
        
        new_brand_name = data['brand_name'].strip()
        
        # Validation
        if not new_brand_name:
            return jsonify({"error": "Brand name cannot be empty"}), 400
        
        if len(new_brand_name) > 100:
            return jsonify({"error": "Brand name cannot exceed 100 characters"}), 400
        
        # Check for invalid characters (allow letters, numbers, underscore, hyphen, spaces)
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', new_brand_name):
            return jsonify({"error": "Brand name can only contain letters, numbers, underscore, hyphen, and spaces"}), 400
        
        # Get current brand_name and compare
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT brand_name FROM general_info WHERE id = 1")
            row = cursor.fetchone()
            
            current_brand_name = row[0] if row else "Alan_go"
            
            # Check if there's actually a change
            if current_brand_name == new_brand_name:
                return jsonify({
                    "success": True,
                    "data": {
                        "brand_name": current_brand_name,
                        "changed": False
                    },
                    "message": "No changes detected"
                }), 200
            
            # Update only if changed
            cursor.execute("""
                INSERT OR REPLACE INTO general_info (
                    id, brand_name, country, timezone, working_days, from_time, to_time
                ) VALUES (
                    1, ?, 
                    COALESCE((SELECT country FROM general_info WHERE id = 1), ''),
                    COALESCE((SELECT timezone FROM general_info WHERE id = 1), ''),
                    COALESCE((SELECT working_days FROM general_info WHERE id = 1), '[]'),
                    COALESCE((SELECT from_time FROM general_info WHERE id = 1), '07:00'),
                    COALESCE((SELECT to_time FROM general_info WHERE id = 1), '23:00')
                )
            """, (new_brand_name,))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "data": {
                    "brand_name": new_brand_name,
                    "changed": True
                },
                "message": "Brand name updated successfully"
            }), 200
            
    except Exception as e:
        error_msg = f"Failed to update brandname: {str(e)}"
        print(f"❌ Update brandname error: {error_msg}")
        return jsonify({"error": error_msg}), 500

# Step 2 Location/Time Configuration Endpoints
@config_routes_bp.route('/step/location-time', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_location_time():
    """Get current location/time configuration from general_info table for Step 2."""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT country, timezone, language, working_days, from_time, to_time 
                FROM general_info WHERE id = 1
            """)
            row = cursor.fetchone()
            
            if row:
                country, timezone, language, working_days_json, from_time, to_time = row
                
                # Parse working_days JSON string to array
                import json
                try:
                    working_days = json.loads(working_days_json) if working_days_json else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                except json.JSONDecodeError:
                    working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                return jsonify({
                    "success": True,
                    "data": {
                        "country": country or "Vietnam",
                        "timezone": timezone or "Asia/Ho_Chi_Minh",
                        "language": language or "English (en-US)",
                        "working_days": working_days,
                        "from_time": from_time or "07:00",
                        "to_time": to_time or "23:00"
                    }
                }), 200
            else:
                # Return defaults if no record exists
                return jsonify({
                    "success": True,
                    "data": {
                        "country": "Vietnam",
                        "timezone": "Asia/Ho_Chi_Minh", 
                        "language": "English (en-US)",
                        "working_days": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                        "from_time": "07:00",
                        "to_time": "23:00"
                    }
                }), 200
            
    except Exception as e:
        error_msg = f"Failed to get location-time: {str(e)}"
        print(f"❌ Get location-time error: {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/step/location-time', methods=['PUT'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_step_location_time():
    """Update location/time configuration only if changed for Step 2."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Request data is required"}), 400
        
        # Extract and validate required fields
        new_country = data.get('country', '').strip()
        new_timezone = data.get('timezone', '').strip()
        new_language = data.get('language', '').strip()
        new_working_days = data.get('working_days', [])
        new_from_time = data.get('from_time', '').strip()
        new_to_time = data.get('to_time', '').strip()
        
        # Validation
        if not new_country:
            return jsonify({"error": "Country is required"}), 400
        if not new_timezone:
            return jsonify({"error": "Timezone is required"}), 400
        if not new_language:
            return jsonify({"error": "Language is required"}), 400
        if not new_working_days or not isinstance(new_working_days, list):
            return jsonify({"error": "Working days must be a non-empty array"}), 400
        if not new_from_time or not new_to_time:
            return jsonify({"error": "Work start and end times are required"}), 400
        
        # Validate time format (HH:MM)
        import re
        time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(time_pattern, new_from_time):
            return jsonify({"error": "Invalid start time format. Use HH:MM"}), 400
        if not re.match(time_pattern, new_to_time):
            return jsonify({"error": "Invalid end time format. Use HH:MM"}), 400
        
        # Validate and process timezone with comprehensive timezone data
        try:
            timezone_validator = TimezoneValidator()
            timezone_result = timezone_validator.validate_timezone(new_timezone)
            
            if not timezone_result.is_valid:
                return jsonify({"error": f"Invalid timezone: {timezone_result.error_message}"}), 400
                
            # Extract all timezone fields
            timezone_iana_name = timezone_result.iana_name
            timezone_display_name = timezone_result.display_name
            timezone_utc_offset_hours = timezone_result.utc_offset_hours
            timezone_format_type = timezone_result.format_type.value if timezone_result.format_type else None
            timezone_validated = 1
            timezone_updated_at = datetime.now().isoformat()
            timezone_validation_warnings = None  # Could add warnings if needed
            
        except Exception as tz_error:
            print(f"Timezone validation error: {tz_error}")
            return jsonify({"error": f"Timezone validation failed: {str(tz_error)}"}), 400
        
        # Get current values and compare for diff detection
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT country, timezone, language, working_days, from_time, to_time 
                FROM general_info WHERE id = 1
            """)
            row = cursor.fetchone()
            
            # Set current values (or defaults)
            if row:
                current_country, current_timezone, current_language, current_working_days_json, current_from_time, current_to_time = row
                
                import json
                try:
                    current_working_days = json.loads(current_working_days_json) if current_working_days_json else []
                except json.JSONDecodeError:
                    current_working_days = []
            else:
                current_country, current_timezone, current_language = "Vietnam", "Asia/Ho_Chi_Minh", "English (en-US)"
                current_working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                current_from_time, current_to_time = "07:00", "23:00"
            
            # Check if there are any changes
            new_working_days_json = json.dumps(new_working_days)
            current_working_days_json = json.dumps(current_working_days) if current_working_days else json.dumps(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
            
            changes_detected = (
                current_country != new_country or
                current_timezone != new_timezone or
                current_language != new_language or
                current_working_days_json != new_working_days_json or
                current_from_time != new_from_time or
                current_to_time != new_to_time
            )
            
            if not changes_detected:
                return jsonify({
                    "success": True,
                    "data": {
                        "country": current_country or new_country,
                        "timezone": current_timezone or new_timezone,
                        "language": current_language or new_language,
                        "working_days": current_working_days or new_working_days,
                        "from_time": current_from_time or new_from_time,
                        "to_time": current_to_time or new_to_time,
                        "changed": False
                    },
                    "message": "No changes detected"
                }), 200
            
            # Update with new values including all timezone fields
            cursor.execute("""
                INSERT OR REPLACE INTO general_info (
                    id, country, timezone, language, working_days, from_time, to_time,
                    timezone_iana_name, timezone_display_name, timezone_utc_offset_hours,
                    timezone_format_type, timezone_validated, timezone_updated_at,
                    timezone_validation_warnings, brand_name
                ) VALUES (
                    1, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?,
                    COALESCE((SELECT brand_name FROM general_info WHERE id = 1), 'Alan_go')
                )
            """, (new_country, new_timezone, new_language, new_working_days_json, new_from_time, new_to_time,
                  timezone_iana_name, timezone_display_name, timezone_utc_offset_hours,
                  timezone_format_type, timezone_validated, timezone_updated_at, timezone_validation_warnings))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "data": {
                    "country": new_country,
                    "timezone": new_timezone,
                    "language": new_language,
                    "working_days": new_working_days,
                    "from_time": new_from_time,
                    "to_time": new_to_time,
                    "changed": True
                },
                "message": "Location/time configuration updated successfully"
            }), 200
            
    except Exception as e:
        error_msg = f"Failed to update location-time: {str(e)}"
        print(f"❌ Update location-time error: {error_msg}")
        return jsonify({"error": error_msg}), 500