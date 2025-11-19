from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import json
import os
from modules.db_utils.safe_connection import safe_db_connection
from modules.sources.video_source_manager import VideoSourceManager
from ..utils import (
    get_working_path_for_source,
    detect_camera_folders,
    has_video_files,
    extract_cameras_from_cloud_folders,
    scan_subdirectories_as_cameras
)

source_routes_bp = Blueprint('source_routes', __name__)

@source_routes_bp.route('/save-sources', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def save_video_sources():
    """Save single active video source - ENHANCED: Support overwrite"""
    data = request.json
    if not data:
      return jsonify({"error": "No JSON data provided"}), 400
    sources = data.get('sources', [])
    
    if not sources:
      return jsonify({"error": "No sources provided"}), 400
    
    # Single Active Source: only process the first source
    source = sources[0]
    source_type = source.get('source_type')
    name = source.get('name')
    path = source.get('path')
    config_data = source.get('config', {})
    overwrite = source.get('overwrite', False)  # NEW: Check overwrite flag
    
    print(f"=== SAVE SOURCE: {name} ({source_type}) ===")
    print(f"Connection path: {path}")
    print(f"Config data: {config_data}")
    print(f"Overwrite mode: {overwrite}")  # NEW: Log overwrite mode
    
    if not all([source_type, name, path]):
        return jsonify({"error": "Source missing required fields"}), 400
    
    source_manager = VideoSourceManager()
    
    try:
        # ENHANCED: Handle overwrite mode
        if overwrite:
            print(f"Overwrite mode: Replacing existing source '{name}'")
            
            # Delete existing source with same name first
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM video_sources WHERE name = ?", (name,))
                deleted_count = cursor.rowcount
            
            print(f"Deleted {deleted_count} existing source(s) with name '{name}'")
        else:
            # EXISTING: Disable all existing sources first (normal mode)
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE video_sources SET active = 0")
        
        # COMMON: Add new source as active
        success, message = source_manager.add_source(source_type, name, path, config_data)
        
        if success:
            # Get source ID for database operations
            source_id = source_manager.get_source_id_by_name(name)
            
            # Calculate correct working path and update processing_config
            working_path = get_working_path_for_source(source_type, name, path)
            
            # FIXED: Consolidate ALL database operations in single context
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Update processing_config.input_path to point to working path
                cursor.execute("""
                    UPDATE processing_config 
                    SET input_path = ? 
                    WHERE id = 1
                """, (working_path,))
                
                print(f"Updated processing_config.input_path to: {working_path}")
                
                # Handle different source types (existing logic)
                if source_type == 'cloud':
                    print(f"PROCESSING CLOUD SOURCE...")
                    
                    selected_folders = config_data.get('selected_folders', [])
                    tree_folders = config_data.get('selected_tree_folders', [])
                    all_folders = selected_folders + tree_folders
                    
                    if all_folders:
                        cloud_cameras = extract_cameras_from_cloud_folders(all_folders)
                        cloud_cameras = list(set(cloud_cameras))
                        
                        cursor.execute("""
                            UPDATE processing_config 
                            SET selected_cameras = ? 
                            WHERE id = 1
                        """, (json.dumps(cloud_cameras),))
                        
                        print(f"Cloud cameras synced to processing_config: {cloud_cameras}")
                        
                        # Create camera directories
                        try:
                            for camera_name in cloud_cameras:
                                camera_dir = os.path.join(working_path, camera_name)
                                os.makedirs(camera_dir, exist_ok=True)
                                print(f"Created camera directory: {camera_dir}")
                        except Exception as dir_error:
                            print(f"Could not create camera directories: {dir_error}")
                
                elif source_type == 'local':
                    # Auto-detect cameras from file system
                    try:
                        cameras = detect_camera_folders(working_path)
                        if cameras:
                            cursor.execute("""
                                UPDATE processing_config 
                                SET selected_cameras = ? 
                                WHERE id = 1
                            """, (json.dumps(cameras),))
                            print(f"Local cameras auto-selected: {cameras}")
                        else:
                            cursor.execute("UPDATE processing_config SET selected_cameras = '[]' WHERE id = 1")
                    except Exception as camera_error:
                        print(f"Camera detection failed: {camera_error}")
                        cursor.execute("UPDATE processing_config SET selected_cameras = '[]' WHERE id = 1")
                
                # Commit all changes together
                conn.commit()
            
            # ENHANCED RESPONSE
            action_taken = "replaced" if overwrite else "added"
            response_data = {
                "message": f"Source '{name}' {action_taken} successfully",
                "source_type": source_type,
                "connection_path": path,
                "working_path": working_path,
                "action": action_taken,
                "overwrite_mode": overwrite
            }
            
            return jsonify(response_data), 200
        else:
            return jsonify({"error": f"Failed to save source: {message}"}), 400
            
    except Exception as e:
        print(f"Failed to save sources: {str(e)}")
        return jsonify({"error": f"Failed to save sources: {str(e)}"}), 500

@source_routes_bp.route('/test-source', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def test_source_connection():
    """Test connectivity for local and cloud source types only"""
    try:
        # Ensure we have valid JSON request
        if not request.is_json:
            return jsonify({
                "accessible": False,
                "message": "Invalid request format - JSON required",
                "source_type": "unknown"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "accessible": False,
                "message": "No data provided",
                "source_type": "unknown"
            }), 400
        
        source_type = data.get('source_type')
        
        if not source_type:
            return jsonify({
                "accessible": False,
                "message": "source_type is required",
                "source_type": "unknown"
            }), 400
        
        # Handle different source types
        if source_type == 'local':
            # Existing local path validation
            source_config = {
                'source_type': source_type,
                'path': data.get('path'),
                'config': data.get('config', {})
            }
            
            if not source_config['path']:
                return jsonify({
                    "accessible": False,
                    "message": "path is required for local sources",
                    "source_type": source_type
                }), 400
            
            source_manager = VideoSourceManager()
            is_accessible, message = source_manager.validate_source_accessibility(source_config)
            
            return jsonify({
                "accessible": is_accessible,
                "message": message,
                "source_type": source_type
            }), 200
            
        elif source_type == 'cloud':
            # Cloud connection testing + folder discovery
            from modules.sources.cloud_manager import CloudManager
            cloud_manager = CloudManager(provider='google_drive')
            result = cloud_manager.test_connection_and_discover_folders(data)
            return jsonify(result), 200
            
        else:
            return jsonify({
                "accessible": False,
                "message": f"Source type '{source_type}' not supported. Only 'local' and 'cloud' are available.",
                "source_type": source_type
            }), 400
        
    except ImportError as e:
        return jsonify({
            "accessible": False,
            "message": f"Required module not available: {str(e)}",
            "source_type": data.get('source_type', 'unknown')
        }), 500
        
    except json.JSONDecodeError:
        return jsonify({
            "accessible": False,
            "message": "Invalid JSON format",
            "source_type": "unknown"
        }), 400
        
    except Exception as e:
        return jsonify({
            "accessible": False,
            "message": f"Test failed: {str(e)}",
            "source_type": data.get('source_type', 'unknown')
        }), 500

@source_routes_bp.route('/get-sources', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_video_sources():
    """Get all video sources"""
    try:
        source_manager = VideoSourceManager()
        sources = source_manager.get_all_active_sources()
        
        return jsonify({"sources": sources}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve sources: {str(e)}"}), 500

@source_routes_bp.route('/update-source/<int:source_id>', methods=['PUT'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_video_source(source_id):
    """Simple update video source - same type only, mainly for camera selection"""
    try:
        data = request.json
        if not data:
          return jsonify({"error": "No JSON data provided"}), 400
        source_manager = VideoSourceManager()
        
        # Get current source for validation
        current_source = source_manager.get_source_by_id(source_id)
        if not current_source:
            return jsonify({"error": f"Source with id {source_id} not found"}), 404
        
        # For now, we only support updating the config (mainly for camera selection)
        # Path and source_type changes are handled by "Change" button workflow
        new_config = data.get('config', current_source['config'])
        
        # Update source config only
        success, message = source_manager.update_source(source_id, config=new_config)
        
        if not success:
            return jsonify({"error": message}), 400
        
        return jsonify({
            "message": message,
            "source_id": source_id,
            "updated_fields": ["config"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update source: {str(e)}"}), 500

@source_routes_bp.route('/delete-source/<int:source_id>', methods=['DELETE'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def delete_video_source(source_id):
    """Delete video source (used by Change button to reset workflow)"""
    source_manager = VideoSourceManager()
    
    try:
        # Get source info before deletion for logging
        source = source_manager.get_source_by_id(source_id)
        source_name = source.get('name', 'Unknown') if source else 'Unknown'
        
        success, message = source_manager.delete_source(source_id)
        
        if success:
            # Clean reset processing_config 
            try:
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE processing_config 
                        SET input_path = '', selected_cameras = '[]' 
                        WHERE id = 1
                    """)
                
                print(f"Source '{source_name}' deleted and processing_config reset")
                
            except Exception as config_error:
                print(f"Failed to reset processing_config: {config_error}")
            
            return jsonify({
                "message": f"Source '{source_name}' removed successfully. You can now add a new source.",
                "reset": True
            }), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        return jsonify({"error": f"Failed to delete source: {str(e)}"}), 500

@source_routes_bp.route('/toggle-source/<int:source_id>', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def toggle_source_status(source_id):
    """Toggle source active status"""
    data = request.json
    if not data:
      return jsonify({"error": "No JSON data provided"}), 400
    active = data.get('active', True)
    source_manager = VideoSourceManager()
    
    try:
        # FIXED: Consolidate ALL database operations in single context
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            if active:
                # Disable all other sources first (Single Active Source)
                cursor.execute("UPDATE video_sources SET active = 0")
            
            success, message = source_manager.toggle_source_status(source_id, active)
            
            if success and active:
                # Update input_path to this source
                source = source_manager.get_source_by_id(source_id)
                if source:
                    # Update input_path
                    cursor.execute("""
                        UPDATE processing_config 
                        SET input_path = ? 
                        WHERE id = 1
                    """, (source['path'],))
                    
                    # Auto-detect cameras for local sources
                    if source['source_type'] == 'local':
                        try:
                            cameras = detect_camera_folders(source['path'])
                            if cameras:
                                cursor.execute("""
                                    UPDATE processing_config 
                                    SET selected_cameras = ? 
                                    WHERE id = 1
                                """, (json.dumps(cameras),))
                            else:
                                cursor.execute("""
                                    UPDATE processing_config 
                                    SET selected_cameras = '[]' 
                                    WHERE id = 1
                                """)
                        except Exception as camera_error:
                            print(f"Camera detection failed: {camera_error}")
                            cursor.execute("""
                                UPDATE processing_config 
                                SET selected_cameras = '[]' 
                                WHERE id = 1
                            """)
                    else:
                        # Clear cameras for non-local sources
                        cursor.execute("""
                            UPDATE processing_config 
                            SET selected_cameras = '[]' 
                            WHERE id = 1
                        """)
                    
                    # Commit all changes together
                    conn.commit()
        
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        return jsonify({"error": f"Failed to toggle source status: {str(e)}"}), 500

@source_routes_bp.route('/scan-folders', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def scan_folders():
    """
    ePACK Step 3 Enhancement: Auto-scan subdirectories as camera folders
    
    POST /api/config/scan-folders
    Body: {"path": "directory_path"}
    Response: {"success": bool, "folders": [{"name": str, "path": str}], "message": str}
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                "success": False,
                "folders": [],
                "message": "Invalid request format - JSON required"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "folders": [],
                "message": "No data provided"
            }), 400
        
        input_path = data.get('path')
        if not input_path:
            return jsonify({
                "success": False,
                "folders": [],
                "message": "Path parameter is required"
            }), 400
        
        print(f"=== SCAN FOLDERS REQUEST: {input_path} ===")
        
        # Use enhanced scanning function
        scan_result = scan_subdirectories_as_cameras(input_path)
        
        print(f"Scan result: {scan_result['message']}")
        print(f"Found folders: {[f['name'] for f in scan_result['folders']]}")
        
        # Return result (success status is already set by scan function)
        return jsonify(scan_result), 200 if scan_result['success'] else 400
        
    except Exception as e:
        error_message = f"Failed to scan folders: {str(e)}"
        print(f"Scan folders error: {error_message}")
        return jsonify({
            "success": False,
            "folders": [],
            "message": error_message
        }), 500