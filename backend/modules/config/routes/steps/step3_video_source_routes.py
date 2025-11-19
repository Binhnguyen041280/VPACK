"""
Step 3 Video Source Configuration Routes for ePACK.

RESTful endpoints for managing video source configuration with 
proper data mapping between video_sources and processing_config tables.
FIXED: Ensures data sync for backward compatibility.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from ...services.step3_video_source_service import step3_video_source_service
from ...shared import (
    format_step_response,
    handle_database_error,
    handle_validation_error,
    handle_general_error,
    create_success_response,
    create_error_response,
    validate_request_data,
    log_step_operation
)


# Create blueprint for Step 3 routes
step3_bp = Blueprint('step3_video_source', __name__, url_prefix='/step')


@step3_bp.route('/video-source', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_video_source():
    """
    Get current video source configuration for Step 3.
    Includes backward compatibility data from processing_config.
    
    Returns:
        JSON response with current video source configuration
    """
    try:
        log_step_operation("3", "GET video-source request")
        
        # Get configuration from service
        config = step3_video_source_service.get_video_source_config()
        
        if "error" in config:
            # Service returned error but with fallback data
            response_data = {k: v for k, v in config.items() if k != "error"}
            response = create_success_response(response_data, "Configuration retrieved with fallback")
            response["warning"] = config["error"]
        else:
            response = create_success_response(config, "Video source configuration retrieved successfully")
        
        log_step_operation("3", "GET video-source success", {
            "has_active_source": config.get("current_source") is not None,
            "camera_count": config.get("camera_count", 0),
            "has_fallback": "fallback_source" in config
        })
        
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "get video source", "step3")
        return jsonify(error_response), status_code


@step3_bp.route('/video-source', methods=['PUT'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_step_video_source():
    """
    Update video source configuration for Step 3.
    FIXED: Proper data mapping and sync between tables.
    
    Request Body:
        {
            "sourceType": "local_storage" | "cloud_storage" (required),
            "inputPath": "string" (required for local),
            "selectedCameras": ["array"] (required for local),
            "detectedFolders": ["array"] (optional),
            "selected_tree_folders": ["array"] (required for cloud)
        }
    
    Returns:
        JSON response with update result and new video source ID
    """
    try:
        log_step_operation("3", "PUT video-source request")
        
        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=['sourceType'])
        if not is_valid:
            error_response = create_error_response(error_msg, "step3")
            return jsonify(error_response), 400
        
        # Log request details
        source_type = data.get('sourceType')
        input_path = data.get('inputPath', '')
        selected_cameras = data.get('selectedCameras', [])
        selected_tree_folders = data.get('selected_tree_folders', [])
        
        print(f"=== STEP 3 VIDEO SOURCE UPDATE ===")
        print(f"Source Type: {source_type}")
        print(f"Input Path: {input_path}")
        print(f"Selected Cameras: {selected_cameras}")
        print(f"Selected Tree Folders: {len(selected_tree_folders)} folders")
        
        # Update configuration via service
        success, result = step3_video_source_service.update_video_source_config(data)
        
        if not success:
            # Service returned validation or database error
            if "error" in result:
                error_response = create_error_response(result["error"], "step3")
                return jsonify(error_response), 400
        
        # Format successful response
        response_data = {
            "sourceType": result["sourceType"],
            "inputPath": result["inputPath"],
            "selectedCameras": result["selectedCameras"],
            "cameraPathsCount": result["cameraPathsCount"],
            "videoSourceId": result["videoSourceId"],
            "changed": result["changed"],
            "upsert_operation": result.get("upsert_operation", False)
        }
        
        # Add cloud-specific response data
        if source_type == 'cloud_storage':
            if "selectedTreeFoldersCount" in result:
                response_data["selectedTreeFoldersCount"] = result["selectedTreeFoldersCount"]
            if "convertedFromFolders" in result:
                response_data["convertedFromFolders"] = result["convertedFromFolders"]
            if "googleDrivePaths" in result:
                response_data["googleDrivePaths"] = result["googleDrivePaths"]
        
        response = create_success_response(
            response_data,
            f"Video source configuration updated successfully (ID: {result['videoSourceId']})",
            changed=result["changed"]
        )

        log_step_operation("3", "PUT video-source success", {
            "video_source_id": result["videoSourceId"],
            "camera_count": len(result["selectedCameras"]),
            "source_type": source_type
        })

        # AUTO-START SYNC for cloud sources immediately after config
        if source_type == 'cloud_storage':
            try:
                from modules.sources.pydrive_downloader import pydrive_downloader
                video_source_id = result['videoSourceId']

                print(f"🚀 Auto-starting sync for cloud source {video_source_id}...")
                if pydrive_downloader.start_auto_sync(video_source_id):
                    print(f"✅ Auto-sync started successfully for source {video_source_id}")
                    response['data']['auto_sync_started'] = True
                else:
                    print(f"⚠️ Failed to start auto-sync for source {video_source_id}")
                    response['data']['auto_sync_started'] = False
            except Exception as sync_error:
                print(f"❌ Error starting auto-sync: {sync_error}")
                response['data']['auto_sync_started'] = False

        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "update video source", "step3")
        return jsonify(error_response), status_code


@step3_bp.route('/video-source/validate', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def validate_step_video_source():
    """
    Validate video source configuration without saving.
    Useful for real-time validation in frontend forms.
    
    Request Body:
        {
            "sourceType": "string" (required),
            "inputPath": "string" (conditional),
            "selectedCameras": ["array"] (conditional),
            "selected_tree_folders": ["array"] (conditional)
        }
    
    Returns:
        JSON response with validation result
    """
    try:
        log_step_operation("3", "POST video-source validate request")
        
        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=['sourceType'])
        if not is_valid:
            error_response = create_error_response(error_msg, "step3")
            return jsonify(error_response), 400
        
        # Validate via shared validation function
        from ...shared.validation import validate_video_source_config
        is_valid, validation_message = validate_video_source_config(data)
        
        if is_valid:
            response = {
                "success": True,
                "valid": True,
                "message": "Video source configuration is valid",
                "data": {
                    "sourceType": data.get("sourceType"),
                    "validationChecks": {
                        "sourceType": "valid",
                        "requirements": "satisfied"
                    }
                }
            }
            
            # Add source-specific validation details
            if data.get("sourceType") == "local_storage":
                response["data"]["validationChecks"]["inputPath"] = "valid" if data.get("inputPath") else "missing"
                response["data"]["validationChecks"]["selectedCameras"] = "valid" if data.get("selectedCameras") else "missing"
            elif data.get("sourceType") == "cloud_storage":
                response["data"]["validationChecks"]["selected_tree_folders"] = "valid" if data.get("selected_tree_folders") else "missing"
            
            status_code = 200
        else:
            response = {
                "success": True,
                "valid": False,
                "error": validation_message,
                "data": {
                    "sourceType": data.get("sourceType")
                }
            }
            status_code = 200  # 200 for validation endpoint, even with invalid data
        
        log_step_operation("3", "POST video-source validate", {
            "valid": is_valid,
            "source_type": data.get("sourceType")
        })
        
        return jsonify(response), status_code
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "validate video source", "step3")
        return jsonify(error_response), status_code


@step3_bp.route('/video-source/cameras', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_video_source_cameras():
    """
    Get current camera configuration from active video source.
    Useful for displaying current camera selections.
    
    Returns:
        JSON response with camera configuration details
    """
    try:
        log_step_operation("3", "GET video-source cameras request")
        
        # Get configuration from service
        config = step3_video_source_service.get_video_source_config()
        
        # Extract camera-specific data
        camera_data = {
            "selected_cameras": config.get("selected_cameras", []),
            "camera_paths": config.get("camera_paths", {}),
            "camera_count": config.get("camera_count", 0),
            "source_type": config.get("current_source", {}).get("source_type") if config.get("current_source") else None
        }
        
        # Add detected folders if available
        if config.get("detected_folders"):
            camera_data["detected_folders"] = config["detected_folders"]
            camera_data["detected_count"] = len(config["detected_folders"])
        
        # Add cloud folders if available
        if config.get("selected_tree_folders"):
            camera_data["selected_tree_folders"] = config["selected_tree_folders"]
            camera_data["tree_folders_count"] = len(config["selected_tree_folders"])
        
        response = create_success_response(camera_data, "Camera configuration retrieved successfully")
        
        log_step_operation("3", "GET video-source cameras success", {
            "camera_count": camera_data["camera_count"],
            "source_type": camera_data["source_type"]
        })
        
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "get video source cameras", "step3")
        return jsonify(error_response), status_code


@step3_bp.route('/video-source/sync-status', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_video_source_sync_status():
    """
    Get synchronization status between video_sources and processing_config.
    Useful for debugging and monitoring data consistency.
    
    Returns:
        JSON response with sync status information
    """
    try:
        log_step_operation("3", "GET video-source sync-status request")
        
        # Get configuration from service
        config = step3_video_source_service.get_video_source_config()
        
        # Build sync status data
        sync_status = {
            "has_active_source": config.get("current_source") is not None,
            "has_backward_compatibility": "backward_compatibility" in config,
            "sync_status": "unknown"
        }
        
        # Compare video_sources vs processing_config data
        if config.get("current_source") and config.get("backward_compatibility"):
            vs_cameras = set(config.get("selected_cameras", []))
            pc_cameras = set(config.get("backward_compatibility", {}).get("processing_config_selected_cameras", []))
            
            vs_path = config.get("input_path", "")
            pc_path = config.get("backward_compatibility", {}).get("processing_config_input_path", "")
            
            cameras_match = vs_cameras == pc_cameras
            paths_match = vs_path == pc_path
            
            if cameras_match and paths_match:
                sync_status["sync_status"] = "synchronized"
            elif cameras_match:
                sync_status["sync_status"] = "cameras_synced_paths_differ"
            elif paths_match:
                sync_status["sync_status"] = "paths_synced_cameras_differ"
            else:
                sync_status["sync_status"] = "out_of_sync"
            
            sync_status["details"] = {
                "cameras_match": cameras_match,
                "paths_match": paths_match,
                "video_sources_cameras": list(vs_cameras),
                "processing_config_cameras": list(pc_cameras),
                "video_sources_path": vs_path,
                "processing_config_path": pc_path
            }
        elif config.get("backward_compatibility"):
            sync_status["sync_status"] = "processing_config_only"
        elif config.get("current_source"):
            sync_status["sync_status"] = "video_sources_only"
        else:
            sync_status["sync_status"] = "no_configuration"
        
        response = create_success_response(sync_status, "Sync status retrieved successfully")
        
        log_step_operation("3", "GET video-source sync-status success", {
            "sync_status": sync_status["sync_status"]
        })
        
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "get video source sync status", "step3")
        return jsonify(error_response), status_code