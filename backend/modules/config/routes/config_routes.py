from flask import Blueprint, request, jsonify
from typing import Dict, Any, Tuple, Optional
import json
import os
import sqlite3
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.sources.path_manager import PathManager
from ..utils import get_working_path_for_source, load_config

config_routes_bp = Blueprint('config_routes', __name__)

# Load config using shared utility
config = load_config()

@config_routes_bp.route('/save-config', methods=['POST'])
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
def save_general_info():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    country = data.get('country')
    timezone = data.get('timezone')
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

    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO general_info (
                    id, country, timezone, brand_name, working_days, from_time, to_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (1, country, timezone, brand_name, json.dumps(working_days_en), from_time, to_time))
            
            # Commit changes
            conn.commit()
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}. Ensure the database is accessible."}), 500

    print("General info saved:", data)
    return jsonify({"message": "General info saved"}), 200