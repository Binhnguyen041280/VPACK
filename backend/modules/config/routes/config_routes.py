from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from typing import Dict, Any, Tuple, Optional
import json
import os
import sqlite3
from datetime import datetime
from modules.db_utils.safe_connection import safe_db_connection
from zoneinfo import ZoneInfo
from modules.utils.simple_timezone import simple_validate_timezone, get_available_timezones, get_timezone_offset
# Import db_rwlock conditionally to avoid circular imports
try:
    from modules.scheduler.db_sync import db_rwlock
    DB_RWLOCK_AVAILABLE = True
except ImportError:
    DB_RWLOCK_AVAILABLE = False
    db_rwlock = None
from modules.sources.path_manager import PathManager
# timezone_schema_migration no longer needed - using simplified schema
from ..utils import get_working_path_for_source, load_config
from ..services.validate_packing_video_service import validate_packing_video
from modules.config.logging_config import get_logger

logger = get_logger(__name__)

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

    # Enhanced timezone validation using zoneinfo
    timezone_validation_result = None
    if timezone_input:
        try:
            validation_result = simple_validate_timezone(timezone_input)
            if validation_result['valid']:
                # Create compatible result structure
                timezone_validation_result = type('ValidationResult', (), {
                    'is_valid': True,
                    'normalized_name': validation_result['timezone'],
                    'iana_name': validation_result['timezone'],
                    'display_name': validation_result['timezone'].replace('_', ' '),
                    'utc_offset_hours': get_timezone_offset(validation_result['timezone']) or 7,  # Default to Vietnam
                    'format_type': type('FormatType', (), {'value': 'IANA'}),
                    'warnings': [],
                    'error_message': None
                })()
            else:
                print(f"⚠️ Timezone validation warning: {validation_result['error']}")
                # Create invalid result
                timezone_validation_result = type('ValidationResult', (), {
                    'is_valid': False,
                    'error_message': validation_result['error'],
                    'normalized_name': None,
                    'iana_name': None,
                    'display_name': None,
                    'utc_offset_hours': None,
                    'format_type': None,
                    'warnings': []
                })()
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
            # Using simplified schema after timezone migration
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
        
        # Get available timezones using simple_timezone
        timezones = get_available_timezones()
        
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
                    validation_result = simple_validate_timezone(tz_name)
                    if validation_result['valid']:
                        tz_info["utc_offset_hours"] = get_timezone_offset(tz_name)
                        tz_info["display_name"] = validation_result['timezone'].replace('_', ' ')
                        tz_info["format_type"] = "IANA"
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
        
        # Validate the timezone using simple_validate_timezone
        validation_result = simple_validate_timezone(timezone_input)
        
        # Get additional timezone info if valid
        utc_offset_hours = None
        current_time = None
        if validation_result['valid']:
            utc_offset_hours = get_timezone_offset(validation_result['timezone'])
            try:
                tz = ZoneInfo(validation_result['timezone'])
                current_time = datetime.now(tz).isoformat()
            except Exception:
                pass
        
        response_data = {
            "input": timezone_input,
            "is_valid": validation_result['valid'],
            "normalized_name": validation_result.get('timezone', ''),
            "original_input": validation_result.get('original', timezone_input),
            "format_type": "IANA" if validation_result['valid'] else "unknown",
            "iana_name": validation_result.get('timezone', ''),
            "utc_offset_hours": utc_offset_hours,
            "utc_offset_seconds": (utc_offset_hours * 3600) if utc_offset_hours else None,
            "display_name": validation_result.get('timezone', '').replace('_', ' ') if validation_result['valid'] else '',
            "warnings": []
        }
        
        if not validation_result['valid']:
            response_data["error_message"] = validation_result.get('error', 'Invalid timezone')
        
        # Add current time if available
        if current_time:
            response_data["current_time"] = current_time
            if utc_offset_hours:
                response_data["current_offset"] = f"UTC{'+' if utc_offset_hours >= 0 else ''}{utc_offset_hours}"
        
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
        # Schema migration is complete - using simplified timezone schema
        migration_result = {
            "success": True,
            "message": "Timezone schema already simplified - using zoneinfo",
            "changes_made": ["Using standard Python zoneinfo instead of custom timezone modules"]
        }
        
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
        # Schema has been migrated to simplified timezone format
        print("✅ Using simplified timezone schema (already migrated)")
        if False:  # Skip migration - already complete
            print("🔄 Migrating general_info schema for enhanced timezone support...")
            # Perform schema migration in background
            try:
                # Migration already complete - using simplified timezone schema
                migration_result = {'success': True, 'message': 'Schema already migrated to zoneinfo'}
                print("✅ Enhanced timezone schema migration completed (already using zoneinfo)")
            except Exception as migration_error:
                print(f"⚠️ Schema migration error: {migration_error}")
                # Continue with basic save
    except Exception as schema_check_error:
        print(f"⚠️ Schema check error: {schema_check_error}")
    
    # Save with simplified timezone schema
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
    """Get global timezone configuration (hardcoded to Asia/Ho_Chi_Minh)."""
    try:
        # Hardcoded timezone for Vietnam
        default_timezone = "Asia/Ho_Chi_Minh"
        utc_offset = get_timezone_offset(default_timezone) or 7
        
        return jsonify({
            "timezone_iana": default_timezone,
            "timezone_display": "Asia/Ho Chi Minh",
            "utc_offset_hours": utc_offset,
            "is_validated": True,
            "last_updated": datetime.now().isoformat(),
            "warnings": [],
            "source": "hardcoded_default"
        }), 200
        
    except Exception as e:
        error_msg = f"Failed to get global timezone: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/global-timezone', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def set_global_timezone():
    """Set global timezone configuration (validates and logs but remains hardcoded)."""
    try:
        data = request.json
        if not data or 'timezone' not in data:
            return jsonify({"error": "timezone field is required"}), 400
        
        timezone_iana = data['timezone']
        
        # Validate the provided timezone
        validation_result = simple_validate_timezone(timezone_iana)
        
        if validation_result['valid']:
            print(f"✅ Timezone validation passed for: {timezone_iana}")
            print("⚠️ Note: Global timezone remains hardcoded to Asia/Ho_Chi_Minh")
            
            return jsonify({
                "message": "Global timezone validated (remains hardcoded to Asia/Ho_Chi_Minh)",
                "timezone": "Asia/Ho_Chi_Minh",
                "requested_timezone": timezone_iana,
                "validation_status": "valid"
            }), 200
        else:
            return jsonify({
                "error": f"Invalid timezone: {validation_result.get('error', 'Unknown error')}",
                "requested_timezone": timezone_iana
            }), 400
            
    except Exception as e:
        error_msg = f"Failed to set global timezone: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/global-timezone/migrate', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def migrate_to_global_timezone():
    """Migration endpoint (no-op since timezone is hardcoded)."""
    try:
        print("📝 Migration requested - timezone remains hardcoded to Asia/Ho_Chi_Minh")
        
        migration_result = {
            'success': True,
            'message': 'Migration completed (timezone remains hardcoded)',
            'source_timezone': 'Asia/Ho_Chi_Minh',
            'target_timezone': 'Asia/Ho_Chi_Minh',
            'records_migrated': 0,
            'hardcoded_mode': True
        }
        
        return jsonify(migration_result), 200
            
    except Exception as e:
        error_msg = f"Migration failed: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/validate-packing-video', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def validate_packing_video_endpoint():
    """Validate a single training video for packing area configuration."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        file_path = data.get('file', '').strip()
        video_type = data.get('type', 'traditional').strip()
        
        # Validation
        if not file_path:
            return jsonify({"error": "file parameter is required"}), 400
        
        # Validate video type
        if video_type not in ['traditional', 'qr']:
            return jsonify({"error": "type must be 'traditional' or 'qr'"}), 400
        
        logger.info(f"Validating packing video: {file_path} (type: {video_type})")
        
        # Perform video validation
        validation_result = validate_packing_video(file_path, video_type)
        
        # Return validation result
        return jsonify(validation_result), 200
        
    except Exception as e:
        error_msg = f"Video validation error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg,
            "video_file": {
                "filename": "",
                "path": "",
                "duration_seconds": 0,
                "duration_formatted": "0s",
                "valid": False,
                "error": error_msg,
                "file_size_mb": 0.0,
                "format": "unknown"
            },
            "summary": {
                "valid": False,
                "duration_seconds": 0,
                "scan_time_ms": 0
            },
            "file_info": {
                "exists": False,
                "readable": False
            }
        }), 500

# Register step-based modular routes
from .steps import (
    step1_bp, step2_bp, step3_bp, step4_bp, step5_bp
)

# Register all step blueprints with the main config routes blueprint
config_routes_bp.register_blueprint(step1_bp)
config_routes_bp.register_blueprint(step2_bp)
config_routes_bp.register_blueprint(step3_bp)
config_routes_bp.register_blueprint(step4_bp)
config_routes_bp.register_blueprint(step5_bp)

print("✅ V.PACK Modular Config Routes Registered:")
print("   - Step 1: /step/brandname (GET, PUT)")
print("   - Step 2: /step/location-time (GET, PUT)")
print("   - Step 3: /step/video-source (GET, PUT)")
print("   - Step 4: /step/packing-area (GET, PUT)")
print("   - Step 5: /step/timing (GET, PUT)")

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
            
            # Check if language column exists first
            cursor.execute("PRAGMA table_info(general_info)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            has_language_column = 'language' in existing_columns
            
            if has_language_column:
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
                    # Return defaults if no record exists in has_language_column case
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
            else:
                cursor.execute("""
                    SELECT country, timezone, working_days, from_time, to_time 
                    FROM general_info WHERE id = 1
                """)
                row = cursor.fetchone()
                language = "English (en-US)"  # Default since column doesn't exist
                if row:
                    country, timezone, working_days_json, from_time, to_time = row
                    
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
        
        # Validate and process timezone using simple_validate_timezone
        try:
            timezone_result = simple_validate_timezone(new_timezone)
            
            if not timezone_result['valid']:
                return jsonify({"error": f"Invalid timezone: {timezone_result.get('error', 'Unknown error')}"}), 400
                
            # We only need the validated timezone string for simplified schema
            
        except Exception as tz_error:
            print(f"Timezone validation error: {tz_error}")
            return jsonify({"error": f"Timezone validation failed: {str(tz_error)}"}), 400
        
        # Get current values and compare for diff detection
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if language column exists first
            cursor.execute("PRAGMA table_info(general_info)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            has_language_column = 'language' in existing_columns
            
            if has_language_column:
                cursor.execute("""
                    SELECT country, timezone, language, working_days, from_time, to_time 
                    FROM general_info WHERE id = 1
                """)
                row = cursor.fetchone()
                if row:
                    current_country, current_timezone, current_language, current_working_days_json, current_from_time, current_to_time = row
                    
                    # Parse working_days JSON string to array
                    try:
                        current_working_days = json.loads(current_working_days_json) if current_working_days_json else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    except json.JSONDecodeError:
                        current_working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                else:
                    current_country, current_timezone, current_language = "Vietnam", "Asia/Ho_Chi_Minh", "English (en-US)"
                    current_working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    current_from_time, current_to_time = "07:00", "23:00"
                    current_working_days_json = json.dumps(current_working_days)
            else:
                cursor.execute("""
                    SELECT country, timezone, working_days, from_time, to_time 
                    FROM general_info WHERE id = 1
                """)
                row = cursor.fetchone()
                current_language = "English (en-US)"  # Default since column doesn't exist
                if row:
                    current_country, current_timezone, current_working_days_json, current_from_time, current_to_time = row
                    
                    try:
                        current_working_days = json.loads(current_working_days_json) if current_working_days_json else []
                    except json.JSONDecodeError:
                        current_working_days = []
                else:
                    current_country, current_timezone = "Vietnam", "Asia/Ho_Chi_Minh"
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
            
            # Get existing brand_name to preserve it
            cursor.execute("SELECT brand_name FROM general_info WHERE id = 1")
            brand_row = cursor.fetchone()
            existing_brand_name = brand_row[0] if brand_row and brand_row[0] else 'Alan_go'
            
            # Now that we have PRIMARY KEY, we can use INSERT OR REPLACE safely
            cursor.execute("""
                INSERT OR REPLACE INTO general_info (
                    id, country, timezone, language, working_days, from_time, to_time, brand_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (1, new_country, timezone_result['timezone'], new_language, 
                  new_working_days_json, new_from_time, new_to_time, existing_brand_name))
            
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

# Step 3 Video Source Configuration Endpoints
@config_routes_bp.route('/step/video-source', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_video_source():
    """Get current video source configuration for Step 3 using UPSERT pattern."""
    try:
        from modules.video_sources.video_source_repository import get_active_source, get_source_statistics
        
        # Get active video source using new repository
        active_source = get_active_source()
        source_stats = get_source_statistics()
        
        # Build response based on active source
        if active_source:
            config = active_source.get('config', {})
            
            # Extract configuration data
            selected_cameras = config.get('selected_cameras', [])
            camera_paths = config.get('camera_paths', {})
            detected_folders = config.get('detected_folders', [])
            selected_tree_folders = config.get('selected_tree_folders', [])
            original_source_type = config.get('original_source_type', active_source['source_type'])
            
            video_source_data = {
                "current_source": {
                    "id": active_source['id'],
                    "source_type": active_source['source_type'],
                    "name": active_source['name'],
                    "path": active_source['path'],
                    "created_at": active_source['created_at'],
                    "original_source_type": original_source_type
                },
                "input_path": active_source['path'],
                "selected_cameras": selected_cameras,
                "camera_paths": camera_paths,
                "detected_folders": detected_folders,
                "selected_tree_folders": selected_tree_folders,
                "camera_count": len(selected_cameras),
                "statistics": source_stats,
                "single_source_mode": True  # Flag to indicate single source architecture
            }
            
            print(f"✅ Retrieved active source: {active_source['name']} (Type: {active_source['source_type']})")
            
        else:
            # No active source - return defaults
            video_source_data = {
                "current_source": None,
                "input_path": "",
                "selected_cameras": [],
                "camera_paths": {},
                "detected_folders": [],
                "selected_tree_folders": [],
                "camera_count": 0,
                "statistics": {"error": "No active source found"},
                "single_source_mode": True
            }
            
            print("⚠️ No active video source found")
        
        # Get processing config for backward compatibility
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT input_path, selected_cameras, camera_paths FROM processing_config WHERE id = 1")
                row = cursor.fetchone()
                
                if row:
                    proc_input_path, proc_selected_cameras_json, proc_camera_paths_json = row
                    proc_selected_cameras = json.loads(proc_selected_cameras_json) if proc_selected_cameras_json else []
                    proc_camera_paths = json.loads(proc_camera_paths_json) if proc_camera_paths_json else {}
                    
                    # Add backward compatibility data
                    video_source_data["backward_compatibility"] = {
                        "processing_config_input_path": proc_input_path or "",
                        "processing_config_selected_cameras": proc_selected_cameras,
                        "processing_config_camera_paths": proc_camera_paths
                    }
                    
                    # Use processing_config data as fallback if no active source
                    if not active_source and proc_input_path:
                        video_source_data["input_path"] = proc_input_path
                        video_source_data["selected_cameras"] = proc_selected_cameras
                        video_source_data["camera_paths"] = proc_camera_paths
                        video_source_data["camera_count"] = len(proc_selected_cameras)
                        
                        print("📦 Using processing_config as fallback data")
                        
        except Exception as compat_error:
            print(f"⚠️ Backward compatibility query warning: {compat_error}")
            video_source_data["backward_compatibility"] = {"error": str(compat_error)}
        
        return jsonify({
            "success": True,
            "data": video_source_data
        }), 200
            
    except Exception as e:
        error_msg = f"Failed to get video source configuration: {str(e)}"
        print(f"❌ Get video source error: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

@config_routes_bp.route('/step/video-source', methods=['PUT'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_step_video_source():
    """Update video source configuration for Step 3 using UPSERT pattern."""
    try:
        from modules.video_sources.video_source_repository import upsert_video_source
        
        data = request.json
        if not data:
            return jsonify({"error": "Request data is required"}), 400
        
        source_type = data.get('sourceType')
        input_path = data.get('inputPath', '').strip()
        detected_folders = data.get('detectedFolders', [])
        selected_cameras = data.get('selectedCameras', [])
        selected_tree_folders = data.get('selected_tree_folders', [])  # For cloud storage
        
        print(f"=== UPDATE VIDEO SOURCE STEP 3 (UPSERT Pattern) ===")
        print(f"Source Type: {source_type}")
        print(f"Input Path: {input_path}")
        print(f"Detected Folders: {len(detected_folders)} folders")
        print(f"Selected Cameras: {selected_cameras}")
        print(f"Selected Tree Folders: {len(selected_tree_folders)} folders")
        
        # Map source type to database format
        db_source_type = 'local' if source_type == 'local_storage' else 'cloud' if source_type == 'cloud_storage' else source_type
        
        # Validation
        if db_source_type == 'local':
            if not input_path:
                return jsonify({"error": "Input path is required for local storage"}), 400
            if not selected_cameras:
                return jsonify({"error": "At least one camera must be selected"}), 400
        elif db_source_type == 'cloud':
            if not selected_tree_folders:
                return jsonify({"error": "At least one folder must be selected for cloud storage"}), 400
        
        # Build camera_paths mapping for both local and cloud
        camera_paths = {}
        actual_selected_cameras = selected_cameras.copy()  # Start with provided cameras
        processing_input_path = input_path  # Default to original input_path, will be overridden for cloud
        
        if db_source_type == 'local' and detected_folders:
            # Local storage: build camera_paths from detected_folders
            for folder in detected_folders:
                if folder.get('name') in selected_cameras:
                    camera_paths[folder['name']] = folder['path']
        
        elif db_source_type == 'cloud' and selected_tree_folders:
            # Cloud storage: convert selected_tree_folders to selected_cameras format
            print("🔄 Converting cloud folders to camera format...")
            actual_selected_cameras = []  # Reset for cloud
            
            # FIXED: Create separate camera_paths for video_sources vs processing_config
            video_sources_camera_paths = {}  # Google Drive folder IDs for download
            processing_config_camera_paths = {}  # Local sync paths for processing
            
            # Build temporary source name for working path calculation
            temp_source_name = f"CloudStorage_{int(datetime.now().timestamp())}"
            
            # Determine input path for cloud storage first
            if selected_tree_folders and len(selected_tree_folders) > 0:
                temp_input_path = selected_tree_folders[0].get('path', '')
            else:
                temp_input_path = "google_drive://"
            
            # Get working path for cloud storage
            working_path = get_working_path_for_source(db_source_type, temp_source_name, temp_input_path)
            processing_input_path = working_path  # FIXED: Use working_path for processing_config.input_path
            print(f"☁️ Working path for cloud storage: {working_path}")
            print(f"🔧 Processing input path set to: {processing_input_path}")
            
            for folder in selected_tree_folders:
                folder_name = folder.get('name', '')
                folder_path = folder.get('path', '')  # Google Drive path
                folder_id = folder.get('id', '')  # Google Drive folder ID
                
                if folder_name:
                    actual_selected_cameras.append(folder_name)
                    
                    # For video_sources: use Google Drive folder ID (for download API)
                    video_sources_camera_paths[folder_name] = folder_id if folder_id else folder_path
                    
                    # For processing_config: use local sync path (for processing logic)
                    local_camera_path = os.path.join(working_path, folder_name)
                    processing_config_camera_paths[folder_name] = local_camera_path
                    
                    print(f"📁 Cloud camera mapping:")
                    print(f"   - Name: {folder_name}")
                    print(f"   - Video Sources (Google Drive): {video_sources_camera_paths[folder_name]}")
                    print(f"   - Processing Config (Local): {local_camera_path}")
            
            # For backward compatibility, set camera_paths to processing_config format
            camera_paths = processing_config_camera_paths
        
        # Build source data for UPSERT
        if db_source_type == 'cloud' and 'temp_source_name' in locals():
            source_name = temp_source_name  # Use the same name used for working_path calculation
        else:
            source_name = f"{'LocalStorage' if db_source_type == 'local' else 'CloudStorage'}_{int(datetime.now().timestamp())}"
        
        # Set path based on source type
        if db_source_type == 'cloud':
            # For cloud: use the temp_input_path we already determined
            if 'temp_input_path' in locals():
                actual_input_path = temp_input_path
                print(f"☁️ Using Google Drive path: {actual_input_path}")
            else:
                actual_input_path = "google_drive://"  # Fallback
        else:
            actual_input_path = input_path
        
        # FIXED: Use appropriate camera_paths for video_sources table
        video_sources_config_camera_paths = video_sources_camera_paths if db_source_type == 'cloud' and 'video_sources_camera_paths' in locals() else camera_paths
        
        source_data = {
            'source_type': db_source_type,
            'name': source_name,
            'path': actual_input_path,
            'config': {
                'selected_cameras': actual_selected_cameras,  # Use converted cameras for cloud
                'camera_paths': video_sources_config_camera_paths,  # FIXED: Use Google Drive folder IDs for cloud
                'detected_folders': detected_folders,
                'selected_tree_folders': selected_tree_folders,  # Keep original tree data
                'original_source_type': source_type  # Keep original for reference
            }
        }
        
        print(f"UPSERT Source Data: {json.dumps(source_data, indent=2)}")
        
        # FIXED: Debug log to verify correct data separation
        if db_source_type == 'cloud':
            print("🔧 FIXED - Data Mapping Verification:")
            print(f"✅ Video Sources camera_paths (Google Drive): {video_sources_config_camera_paths}")
            print(f"✅ Processing Config camera_paths (Local): {camera_paths}")
        
        # Execute UPSERT operation
        new_source_id = upsert_video_source(source_data)
        
        if new_source_id is None:
            return jsonify({"error": "Failed to create/update video source"}), 500
        
        # Update processing_config for backward compatibility
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Ensure camera_paths column exists
                try:
                    cursor.execute("ALTER TABLE processing_config ADD COLUMN camera_paths TEXT DEFAULT '{}'")
                    print("Added camera_paths column")
                except sqlite3.OperationalError:
                    pass  # Column already exists
                
                # Update processing config with camera selection
                cursor.execute("""
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
                """, (processing_input_path, 
                      json.dumps(actual_selected_cameras), 
                      json.dumps(camera_paths)))  # FIXED: Use processing_input_path (local sync path for cloud)
                
                conn.commit()
                print("✅ Processing config updated for backward compatibility")
                print(f"🔧 FIXED: processing_config.input_path = {processing_input_path}")
                
                # Debug: Verify what was actually saved
                cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
                saved_path = cursor.fetchone()
                if saved_path:
                    print(f"✅ Verified saved input_path: {saved_path[0]}")
                    if '/My Drive/' in saved_path[0]:
                        print("❌ ERROR: Still contains Google Drive path!")
                    else:
                        print("✅ SUCCESS: Contains local filesystem path")
                
        except Exception as compat_error:
            print(f"⚠️ Backward compatibility update warning: {compat_error}")
            # Don't fail the entire operation for this
        
        # Validate paths for local storage
        if db_source_type == 'local' and camera_paths:
            try:
                for camera_name, camera_path in camera_paths.items():
                    if os.path.exists(camera_path) and os.path.isdir(camera_path):
                        print(f"✅ Camera directory validated: {camera_name} -> {camera_path}")
                    else:
                        print(f"⚠️ Camera directory not found: {camera_name} -> {camera_path}")
            except Exception as dir_error:
                print(f"⚠️ Directory validation error: {dir_error}")
        
        # Build successful response
        response_data = {
            "success": True,
            "data": {
                "sourceType": source_type,
                "inputPath": actual_input_path,
                "selectedCameras": actual_selected_cameras,  # Use converted cameras
                "cameraPathsCount": len(camera_paths),
                "videoSourceId": new_source_id,
                "videoSourceName": source_name,
                "changed": True,
                "upsert_operation": True  # Flag to indicate UPSERT was used
            },
            "message": f"Video source configuration updated successfully using UPSERT pattern (ID: {new_source_id})"
        }
        
        # Add cloud-specific response data
        if db_source_type == 'cloud':
            response_data["data"]["selectedTreeFoldersCount"] = len(selected_tree_folders)
            response_data["data"]["convertedFromFolders"] = True  # Indicate conversion happened
            response_data["data"]["googleDrivePaths"] = camera_paths  # Show Google Drive paths
            response_data["data"]["originalTreeFolders"] = selected_tree_folders  # Keep original data
        
        print(f"✅ UPSERT operation completed successfully: ID={new_source_id}")
        return jsonify(response_data), 200
            
    except Exception as e:
        error_msg = f"Failed to update video source configuration: {str(e)}"
        print(f"❌ Update video source error: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500