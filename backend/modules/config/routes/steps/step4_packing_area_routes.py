"""
Step 4 Packing Area Configuration Routes for ePACK.

REST wrapper endpoints for existing packing area/ROI detection logic.
Integrates with existing packing_profiles table and hand detection functions.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from ...services.step4_packing_area_service import step4_packing_area_service
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


# Create blueprint for Step 4 routes
step4_bp = Blueprint('step4_packing_area', __name__, url_prefix='/step')


@step4_bp.route('/packing-area', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_packing_area():
    """
    Get current packing area configuration from packing_profiles table.
    
    Returns:
        JSON response with current packing area configuration
    """
    try:
        log_step_operation("4", "GET packing-area request")
        
        # Get configuration from service
        config = step4_packing_area_service.get_packing_area_config()
        
        if "error" in config:
            # Service returned error but with fallback data
            response_data = {k: v for k, v in config.items() if k != "error"}
            response = create_success_response(response_data, "Configuration retrieved with fallback")
            response["warning"] = config["error"]
        else:
            response = create_success_response(config, "Packing area configuration retrieved successfully")
        
        log_step_operation("4", "GET packing-area success", {
            "zone_count": config.get("zone_count", 0),
            "configured_cameras": len(config.get("configured_cameras", []))
        })
        
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "get packing area", "step4")
        return jsonify(error_response), status_code


@step4_bp.route('/packing-area', methods=['PUT'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_step_packing_area():
    """
    Update packing area configuration using existing packing_profiles logic.
    
    Request Body:
        {
            "detection_zones": [
                {
                    "camera_name": "string" (required),
                    "packing_area": [x, y, w, h] (required),
                    "trigger_area": [x, y, w, h] (optional),
                    "mvd_area": [x, y, w, h] (optional)
                }
            ]
        }
    
    Returns:
        JSON response with update result
    """
    try:
        log_step_operation("4", "PUT packing-area request")
        
        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=['detection_zones'])
        if not is_valid:
            error_response = create_error_response(error_msg, "step4")
            return jsonify(error_response), 400
        
        # Log request details
        detection_zones = data.get('detection_zones', [])
        print(f"=== STEP 4 PACKING AREA UPDATE ===")
        print(f"Detection zones count: {len(detection_zones)}")
        for i, zone in enumerate(detection_zones):
            camera_name = zone.get('camera_name', 'unknown')
            print(f"Zone {i+1}: {camera_name}")
        
        # Update configuration via service
        success, result = step4_packing_area_service.update_packing_area_config(data)
        
        if not success:
            # Service returned validation or database error
            if "error" in result:
                error_response = create_error_response(result["error"], "step4")
                return jsonify(error_response), 400
        
        # Format successful response
        response_data = {
            "detection_zones": result["detection_zones"],
            "zone_count": result["zone_count"],
            "configured_cameras": result["configured_cameras"],
            "changed": result["changed"]
        }
        
        response = create_success_response(
            response_data,
            f"Packing area configuration updated successfully ({result['zone_count']} zones)",
            changed=result["changed"]
        )
        
        log_step_operation("4", "PUT packing-area success", {
            "zone_count": result["zone_count"],
            "configured_cameras": len(result["configured_cameras"])
        })
        
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "update packing area", "step4")
        return jsonify(error_response), status_code


@step4_bp.route('/packing-area/cameras/status', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_all_cameras_roi_status():
    """
    Get ROI configuration status for all cameras.
    Returns list of cameras with their ROI config status.

    Returns:
        JSON response with:
        {
            "cameras": [
                {"camera_name": "Cam1", "has_roi": true, "profile_name": "Cam1_20251002"},
                {"camera_name": "Cam2", "has_roi": false}
            ]
        }
    """
    try:
        log_step_operation("4", "GET all cameras ROI status request")

        # Get ROI status for all cameras from service
        status = step4_packing_area_service.get_all_cameras_roi_status()

        response = create_success_response(status, "Camera ROI status retrieved successfully")

        log_step_operation("4", "GET all cameras ROI status success", {
            "total_cameras": len(status.get("cameras", [])),
            "configured_count": len([c for c in status.get("cameras", []) if c.get("has_roi")])
        })

        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get all cameras ROI status", "step4")
        return jsonify(error_response), status_code


@step4_bp.route('/packing-area/camera/<camera_name>', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_camera_packing_profile(camera_name):
    """
    Get packing area configuration for a specific camera.

    Path Parameter:
        camera_name: Name of the camera

    Returns:
        JSON response with camera-specific packing configuration
    """
    try:
        log_step_operation("4", f"GET camera packing profile request for {camera_name}")

        # Get camera profile from service
        profile = step4_packing_area_service.get_camera_packing_profile(camera_name)

        if "error" in profile:
            error_response = create_error_response(profile["error"], "step4")
            return jsonify(error_response), 500

        response = create_success_response(profile, f"Camera profile retrieved for {camera_name}")

        log_step_operation("4", f"GET camera packing profile success for {camera_name}", {
            "exists": profile.get("exists", False)
        })

        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, f"get camera profile for {camera_name}", "step4")
        return jsonify(error_response), status_code


@step4_bp.route('/packing-area/roi-selection', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def step_roi_selection():
    """
    Wrapper for existing ROI selection functionality.
    Calls the existing hand detection select_roi function.
    
    Request Body:
        {
            "video_path": "string" (required),
            "camera_id": "string" (required),
            "step": "string" (optional, default: "packing")
        }
    
    Returns:
        JSON response with ROI selection result
    """
    try:
        log_step_operation("4", "POST roi-selection request")
        
        # Validate request data
        data = request.json
        required_fields = ['video_path', 'camera_id']
        is_valid, error_msg = validate_request_data(data, required_fields)
        if not is_valid:
            error_response = create_error_response(error_msg, "step4")
            return jsonify(error_response), 400
        
        video_path = data['video_path']
        camera_id = data['camera_id']
        step = data.get('step', 'packing')
        
        print(f"=== STEP 4 ROI SELECTION ===")
        print(f"Video path: {video_path}")
        print(f"Camera ID: {camera_id}")
        print(f"Step: {step}")
        
        # Call existing ROI selection via service
        result = step4_packing_area_service.call_existing_roi_selection(video_path, camera_id, step)
        
        if result.get("success"):
            response = create_success_response(result, "ROI selection completed successfully")
            status_code = 200
        else:
            error_msg = result.get("error", "ROI selection failed")
            response = create_error_response(error_msg, "step4")
            status_code = 400
        
        log_step_operation("4", "POST roi-selection", {
            "success": result.get("success", False),
            "camera_id": camera_id
        })
        
        return jsonify(response), status_code
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "ROI selection", "step4")
        return jsonify(error_response), status_code


@step4_bp.route('/packing-area/roi-finalization', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def step_roi_finalization():
    """
    Wrapper for existing ROI finalization functionality.
    Calls the existing hand detection finalize_roi function.
    
    Request Body:
        {
            "video_path": "string" (required),
            "camera_id": "string" (required),
            "rois": [array] (required)
        }
    
    Returns:
        JSON response with ROI finalization result
    """
    try:
        log_step_operation("4", "POST roi-finalization request")
        
        # Validate request data
        data = request.json
        required_fields = ['video_path', 'camera_id', 'rois']
        is_valid, error_msg = validate_request_data(data, required_fields)
        if not is_valid:
            error_response = create_error_response(error_msg, "step4")
            return jsonify(error_response), 400
        
        video_path = data['video_path']
        camera_id = data['camera_id']
        rois = data['rois']
        
        print(f"=== STEP 4 ROI FINALIZATION ===")
        print(f"Video path: {video_path}")
        print(f"Camera ID: {camera_id}")
        print(f"ROI count: {len(rois)}")
        
        # Call existing ROI finalization via service
        result = step4_packing_area_service.call_existing_roi_finalization(video_path, camera_id, rois)
        
        if result.get("success"):
            response = create_success_response(result, "ROI finalization completed successfully")
            status_code = 200
        else:
            error_msg = result.get("error", "ROI finalization failed")
            response = create_error_response(error_msg, "step4")
            status_code = 400
        
        log_step_operation("4", "POST roi-finalization", {
            "success": result.get("success", False),
            "camera_id": camera_id,
            "roi_count": len(rois)
        })
        
        return jsonify(response), status_code
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "ROI finalization", "step4")
        return jsonify(error_response), status_code


@step4_bp.route('/packing-area/statistics', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_packing_area_statistics():
    """
    Get packing area configuration statistics.
    Useful for monitoring and debugging.
    
    Returns:
        JSON response with packing area statistics
    """
    try:
        log_step_operation("4", "GET packing-area statistics request")
        
        # Get configuration from service
        config = step4_packing_area_service.get_packing_area_config()
        
        # Calculate statistics
        stats = {
            "total_zones": len(config.get("detection_zones", [])),
            "configured_cameras": config.get("configured_cameras", []),
            "cameras_with_packing_area": 0,
            "cameras_with_trigger_area": 0,
            "cameras_with_mvd_area": 0
        }
        
        for zone in config.get("detection_zones", []):
            packing_area = zone.get("packing_area", [0, 0, 0, 0])
            trigger_area = zone.get("trigger_area", [0, 0, 0, 0])
            mvd_area = zone.get("mvd_area", [0, 0, 0, 0])
            
            if any(coord != 0 for coord in packing_area):
                stats["cameras_with_packing_area"] += 1
            if any(coord != 0 for coord in trigger_area):
                stats["cameras_with_trigger_area"] += 1
            if any(coord != 0 for coord in mvd_area):
                stats["cameras_with_mvd_area"] += 1
        
        stats["configuration_completeness"] = (
            stats["cameras_with_packing_area"] / max(1, stats["total_zones"])
        ) * 100 if stats["total_zones"] > 0 else 0
        
        response = create_success_response(stats, "Statistics retrieved successfully")
        
        log_step_operation("4", "GET packing-area statistics success")
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "get packing area statistics", "step4")
        return jsonify(error_response), status_code