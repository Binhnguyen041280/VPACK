from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from datetime import datetime
import json
import os
from modules.db_utils.safe_connection import safe_db_connection
from modules.sources.video_source_manager import VideoSourceManager
from modules.license.license_manager import LicenseManager
from ..utils import detect_camera_folders, has_video_files, extract_cameras_from_cloud_folders

camera_routes_bp = Blueprint('camera_routes', __name__)

@camera_routes_bp.route('/debug-cameras', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def debug_cameras():
    """Debug endpoint to check camera sync status"""
    try:
        # Get processing_config cameras
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT selected_cameras, input_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
        
        if result:
            selected_cameras, input_path = result
            try:
                cameras = json.loads(selected_cameras) if selected_cameras else []
            except:
                cameras = []
                
            # Get active source info
            source_manager = VideoSourceManager()
            active_sources = source_manager.get_all_active_sources()
            
            return jsonify({
                "processing_config": {
                    "selected_cameras": cameras,
                    "camera_count": len(cameras),
                    "input_path": input_path
                },
                "active_sources": active_sources,
                "debug_time": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({"error": "No processing config found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Debug failed: {str(e)}"}), 500

@camera_routes_bp.route('/detect-cameras', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def detect_cameras():
    """Detect camera folders in the specified path"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        path = data.get('path')
        
        if not path:
            return jsonify({"error": "Path is required"}), 400
        
        if not os.path.exists(path):
            return jsonify({"error": f"Path does not exist: {path}"}), 400
        
        # Detect camera folders
        cameras = detect_camera_folders(path)
        
        # Get current selected cameras from processing_config
        selected_cameras = []
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT selected_cameras FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                if result and result[0]:
                    selected_cameras = json.loads(result[0])
        except Exception as e:
            print(f"Error getting selected cameras: {e}")
        
        return jsonify({
            "cameras": cameras,
            "selected_cameras": selected_cameras,
            "path": path,
            "count": len(cameras)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to detect cameras: {str(e)}"}), 500

@camera_routes_bp.route('/update-source-cameras', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_source_cameras():
    """Update selected cameras for a source in processing_config (Simple Update)"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        source_id = data.get('source_id')
        selected_cameras = data.get('selected_cameras', [])

        # CHECK CAMERA LIMIT FOR PRO LICENSE (10 cameras max)
        camera_count = len(selected_cameras)
        try:
            license_manager = LicenseManager()
            license_status = license_manager.get_license_status()

            if license_status.get('status') == 'valid':
                license_data = license_status.get('license', {})
                product_type = license_data.get('product_type', '').lower()

                # Pro license has 10 camera limit (technical constraint per machine)
                # Starter license has unlimited cameras (but no Default Mode, so impractical for many cameras)
                if 'pro' in product_type and camera_count > 10:
                    return jsonify({
                        "success": False,
                        "error": "Camera limit exceeded for Pro license",
                        "message": f"Pro license (249k/month) supports maximum 10 cameras per machine. You selected {camera_count} cameras. Please reduce selection or contact support for multi-machine deployment.",
                        "current_plan": "Pro (249k/month)",
                        "max_cameras": 10,
                        "selected_count": camera_count
                    }), 400

        except Exception as e:
            print(f"License check warning (allowing camera update): {e}")
            # On error, allow update (fail-open for better UX)

        # Update processing_config with selected cameras
        with safe_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE processing_config
                SET selected_cameras = ?
                WHERE id = 1
            """, (json.dumps(selected_cameras),))

        return jsonify({
            "message": "Camera selection updated successfully",
            "selected_cameras": selected_cameras,
            "count": len(selected_cameras)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to update camera selection: {str(e)}"}), 500

@camera_routes_bp.route('/get-cameras', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_cameras():
    try:
        source_manager = VideoSourceManager()
        sources = source_manager.get_all_active_sources()
        
        cameras = []
        
        if sources:
            # Use active source
            active_source = sources[0]  # Single active source
            source_type = active_source['source_type']
            
            if source_type == 'local':
                # Local directory scanning
                video_root = active_source['path']
                if not os.path.exists(video_root):
                    return jsonify({"error": f"Directory {video_root} does not exist. Ensure the path is correct or create the directory."}), 400
                
                # Detect camera folders
                detected_cameras = detect_camera_folders(video_root)
                for camera in detected_cameras:
                    cameras.append({"name": camera, "path": os.path.join(video_root, camera)})
            
            elif source_type in ['cloud', 'camera']:
                # For other source types, use source name as camera
                cameras.append({"name": active_source['name'], "path": active_source['path']})
        else:
            # Fallback to legacy behavior
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
                result = cursor.fetchone()

            if not result:
                return jsonify({"error": "video_root not found in configuration. Please update via /save-config endpoint."}), 400

            video_root = result[0]
            if not os.path.exists(video_root):
                return jsonify({"error": f"Directory {video_root} does not exist. Ensure the path is correct or create the directory."}), 400

            detected_cameras = detect_camera_folders(video_root)
            for camera in detected_cameras:
                cameras.append({"name": camera, "path": os.path.join(video_root, camera)})

        return jsonify({"cameras": cameras}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve cameras: {str(e)}"}), 500

@camera_routes_bp.route('/get-processing-cameras', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_processing_cameras():
    """Get selected cameras from processing_config"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT selected_cameras FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
        
        if result and result[0]:
            selected_cameras = json.loads(result[0])
            return jsonify({
                "selected_cameras": selected_cameras,
                "count": len(selected_cameras)
            }), 200
        else:
            return jsonify({
                "selected_cameras": [],
                "count": 0
            }), 200
            
    except Exception as e:
        return jsonify({"error": f"Failed to get processing cameras: {str(e)}"}), 500

@camera_routes_bp.route('/sync-cloud-cameras', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def sync_cloud_cameras():
    """Manual sync cloud cameras from active cloud source"""
    try:
        # Get active cloud source
        source_manager = VideoSourceManager()
        sources = source_manager.get_all_active_sources()
        cloud_source = None
        
        for source in sources:
            if source['source_type'] == 'cloud':
                cloud_source = source
                break
        
        if not cloud_source:
            return jsonify({"error": "No active cloud source found"}), 404
        
        print(f"Syncing cameras for cloud source: {cloud_source['name']}")
        
        # Extract cameras from cloud config
        config_data = cloud_source.get('config', {})
        selected_folders = config_data.get('selected_folders', [])
        tree_folders = config_data.get('selected_tree_folders', [])
        all_folders = selected_folders + tree_folders
        
        if all_folders:
            cloud_cameras = extract_cameras_from_cloud_folders(all_folders)
            cloud_cameras = list(set(cloud_cameras))  # Remove duplicates
            
            print(f"Generated cloud cameras: {cloud_cameras}")
            
            # Update processing_config
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE processing_config 
                    SET selected_cameras = ? 
                    WHERE id = 1
                """, (json.dumps(cloud_cameras),))
            
            print(f"Cloud cameras synced to processing_config")
            
            return jsonify({
                "success": True,
                "message": f"Synced {len(cloud_cameras)} cameras from cloud source",
                "cameras": cloud_cameras,
                "source_name": cloud_source['name']
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "No folders found in cloud source config"
            }), 400
            
    except Exception as e:
        print(f"Error syncing cloud cameras: {e}")
        return jsonify({"error": f"Failed to sync cloud cameras: {str(e)}"}), 500

@camera_routes_bp.route('/refresh-cameras', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def refresh_cameras():
    """Refresh cameras based on active source type"""
    try:
        # Get active source
        source_manager = VideoSourceManager()
        sources = source_manager.get_all_active_sources()
        
        if not sources:
            return jsonify({
                "success": False,
                "message": "No active source found",
                "cameras": []
            }), 404
        
        active_source = sources[0]  # Single active source
        source_type = active_source['source_type']
        source_name = active_source['name']
        
        print(f"Refreshing cameras for {source_type} source: {source_name}")
        
        cameras = []
        
        if source_type == 'local':
            # Local: Scan directories
            working_path = active_source['path']
            if os.path.exists(working_path):
                detected_cameras = detect_camera_folders(working_path)
                cameras = detected_cameras
                print(f"Local cameras detected: {cameras}")
            else:
                print(f"Local path not found: {working_path}")
                
        elif source_type == 'cloud':
            # Cloud: Extract from config
            config_data = active_source.get('config', {})
            selected_folders = config_data.get('selected_folders', [])
            tree_folders = config_data.get('selected_tree_folders', [])
            all_folders = selected_folders + tree_folders
            
            if all_folders:
                cameras = extract_cameras_from_cloud_folders(all_folders)
                cameras = list(set(cameras))  # Remove duplicates
                print(f"Cloud cameras extracted: {cameras}")
            else:
                # Also check existing selected_cameras in config
                cameras = config_data.get('selected_cameras', [])
                print(f"Using existing cloud cameras: {cameras}")
        
        # Update processing_config if cameras found
        if cameras:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE processing_config 
                    SET selected_cameras = ? 
                    WHERE id = 1
                """, (json.dumps(cameras),))
            
            print(f"Updated processing_config with {len(cameras)} cameras")
        
        return jsonify({
            "success": True,
            "message": f"Refreshed {len(cameras)} cameras from {source_type} source",
            "cameras": cameras,
            "source_type": source_type,
            "source_name": source_name
        }), 200
        
    except Exception as e:
        print(f"Error refreshing cameras: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to refresh cameras: {str(e)}",
            "cameras": []
        }), 500

@camera_routes_bp.route('/camera-status', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_camera_status():
    """Get comprehensive camera status for debugging"""
    try:
        # Get processing_config cameras
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT selected_cameras, input_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
        
        processing_cameras = []
        input_path = ""
        
        if result:
            selected_cameras, input_path = result
            try:
                processing_cameras = json.loads(selected_cameras) if selected_cameras else []
            except:
                processing_cameras = []

        # Get active sources
        source_manager = VideoSourceManager()
        active_sources = source_manager.get_all_active_sources()
        
        # Get source-specific camera info
        source_cameras = []
        source_info = None
        
        if active_sources:
            source = active_sources[0]
            source_info = {
                "name": source['name'],
                "type": source['source_type'],
                "path": source['path']
            }
            
            if source['source_type'] == 'cloud':
                config_data = source.get('config', {})
                selected_folders = config_data.get('selected_folders', [])
                tree_folders = config_data.get('selected_tree_folders', [])
                all_folders = selected_folders + tree_folders
                
                if all_folders:
                    source_cameras = extract_cameras_from_cloud_folders(all_folders)
                    source_cameras = list(set(source_cameras))
                
                source_info.update({
                    "folders_count": len(all_folders),
                    "legacy_folders": len(selected_folders),
                    "tree_folders": len(tree_folders)
                })
                
            elif source['source_type'] == 'local':
                working_path = source['path']
                if os.path.exists(working_path):
                    source_cameras = detect_camera_folders(working_path)
        
        # Check sync status
        cameras_synced = set(processing_cameras) == set(source_cameras)
        
        return jsonify({
            "processing_config": {
                "cameras": processing_cameras,
                "camera_count": len(processing_cameras),
                "input_path": input_path
            },
            "active_source": source_info,
            "source_cameras": {
                "cameras": source_cameras,
                "camera_count": len(source_cameras)
            },
            "sync_status": {
                "cameras_synced": cameras_synced,
                "needs_sync": not cameras_synced
            },
            "recommendations": {
                "action_needed": "sync_cloud_cameras" if source_info and source_info['type'] == 'cloud' and not cameras_synced else None,
                "message": "Cameras not synced - use /sync-cloud-cameras endpoint" if not cameras_synced else "Cameras are in sync"
            },
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get camera status: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500