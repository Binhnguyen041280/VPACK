"""
ROI Configuration Routes for Step 4
Web-based ROI selection and video streaming endpoints
"""

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response
from werkzeug.exceptions import BadRequest
from modules.config.services.step4_roi_service import roi_video_service
from modules.config.shared.error_handlers import handle_general_error
from modules.config.shared.validation import validate_required_fields
from modules.db_utils import find_project_root

# Import QR baseline cache for retrieving cached baseline during save
try:
    from blueprints.qr_detection_bp import qr_baseline_cache
except ImportError:
    qr_baseline_cache = {}  # Fallback empty dict if import fails

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
step4_roi_bp = Blueprint("step4_roi", __name__, url_prefix="/api/config/step4/roi")


@step4_roi_bp.before_request
def handle_preflight():
    """Handle CORS preflight requests"""
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, Cache-Control, Pragma, Expires, Range",
        )
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add(
            "Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges"
        )
        return response
    return None


@step4_roi_bp.route("/video-info", methods=["GET", "OPTIONS"])
def get_video_metadata():
    """
    Get video metadata including duration, resolution, frame rate

    Query params:
        video_path: Path to video file

    Returns:
        JSON with video metadata or error
    """
    try:
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200

        video_path = request.args.get("video_path")
        if not video_path:
            return jsonify({"success": False, "error": "video_path parameter is required"}), 400

        logger.info(f"Getting video metadata for: {video_path}")

        # Get metadata using service
        result = roi_video_service.get_video_metadata(video_path)

        if result["success"]:
            logger.info(f"Video metadata extracted successfully for {video_path}")
            return jsonify({"success": True, "data": result["metadata"]}), 200
        else:
            logger.warning(f"Failed to get video metadata for {video_path}: {result['error']}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result["error"],
                        "details": result.get("details", {}),
                    }
                ),
                400,
            )

    except Exception as e:
        response, status_code = handle_general_error(e, "get video metadata")
        return jsonify(response), status_code


@step4_roi_bp.route("/stream-video", methods=["GET", "OPTIONS"])
def stream_video():
    """
    Stream video with range request support for HTML5 video player

    Query params:
        video_path: Path to video file

    Headers:
        Range: For seeking support (e.g., "bytes=0-1023")

    Returns:
        Video stream response
    """
    try:
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200

        video_path = request.args.get("video_path")
        if not video_path:
            return jsonify({"success": False, "error": "video_path parameter is required"}), 400

        logger.info(f"Streaming video: {video_path}")

        # Get range header for seeking
        range_header = request.headers.get("Range")

        # Stream video using service
        response = roi_video_service.stream_video_range(video_path, range_header)

        return response

    except Exception as e:
        response, status_code = handle_general_error(e, "stream video")
        return jsonify(response), status_code


@step4_roi_bp.route("/extract-frame", methods=["POST", "OPTIONS"])
def extract_frame():
    """
    Extract frame at specific timestamp or frame number

    POST body:
        {
            "video_path": "/path/to/video.mp4",
            "timestamp": 30.5,  // seconds (optional)
            "frame_number": 123,  // frame number (optional)
            "format": "jpg",  // "jpg" or "png" (optional, default: jpg)
            "quality": 85  // JPEG quality 1-100 (optional, default: 85)
        }

    Returns:
        JSON with base64 encoded frame data
    """
    try:
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body is required"}), 400

        # Validate required fields
        is_valid, error_msg = validate_required_fields(data, ["video_path"])
        if not is_valid:
            return jsonify({"success": False, "error": error_msg}), 400

        video_path = data["video_path"]
        timestamp = data.get("timestamp")
        frame_number = data.get("frame_number")
        frame_format = data.get("format", "jpg")
        quality = data.get("quality", 85)

        # Must specify either timestamp or frame_number
        if timestamp is None and frame_number is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Either timestamp or frame_number must be specified",
                    }
                ),
                400,
            )

        if timestamp is not None and frame_number is not None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Specify either timestamp OR frame_number, not both",
                    }
                ),
                400,
            )

        logger.info(
            f"Extracting frame from {video_path} at timestamp={timestamp}, frame={frame_number}"
        )

        # Extract frame using appropriate method
        if timestamp is not None:
            result = roi_video_service.extract_frame_at_time(
                video_path, float(timestamp), frame_format, int(quality)
            )
        else:
            result = roi_video_service.extract_frame_by_number(
                video_path, int(frame_number), frame_format, int(quality)
            )

        if result["success"]:
            logger.info(f"Frame extracted successfully from {video_path}")
            return (
                jsonify(
                    {
                        "success": True,
                        "data": result["frame"],
                        "video_metadata": result.get("video_metadata"),
                    }
                ),
                200,
            )
        else:
            logger.warning(f"Failed to extract frame from {video_path}: {result['error']}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result["error"],
                        "details": result.get("details", {}),
                    }
                ),
                400,
            )

    except Exception as e:
        response, status_code = handle_general_error(e, "extract frame")
        return jsonify(response), status_code


@step4_roi_bp.route("/validate-roi", methods=["POST", "OPTIONS"])
def validate_roi_coordinates():
    """
    Validate ROI coordinate data against video dimensions

    POST body:
        {
            "video_path": "/path/to/video.mp4",
            "roi_data": [
                {
                    "x": 100,
                    "y": 100,
                    "w": 200,
                    "h": 150,
                    "type": "detection",
                    "label": "Packing Area"
                }
            ]
        }

    Returns:
        JSON with validation results
    """
    try:
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body is required"}), 400

        # Validate required fields
        is_valid, error_msg = validate_required_fields(data, ["video_path", "roi_data"])
        if not is_valid:
            return jsonify({"success": False, "error": error_msg}), 400

        video_path = data["video_path"]
        roi_data = data["roi_data"]

        logger.info(f"Validating ROI coordinates for {video_path}")

        # Get video metadata first
        metadata_result = roi_video_service.get_video_metadata(video_path)
        if not metadata_result["success"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Cannot get video metadata: {metadata_result["error"]}',
                        "details": metadata_result.get("details", {}),
                    }
                ),
                400,
            )

        video_width = metadata_result["metadata"]["resolution"]["width"]
        video_height = metadata_result["metadata"]["resolution"]["height"]

        # Validate ROI coordinates
        result = roi_video_service.validate_roi_coordinates(roi_data, video_width, video_height)

        if result["valid"]:
            logger.info(f"ROI validation successful for {video_path}")
            return (
                jsonify(
                    {
                        "success": True,
                        "data": {
                            "validated_rois": result["validated_rois"],
                            "count": result["count"],
                            "video_dimensions": {"width": video_width, "height": video_height},
                        },
                    }
                ),
                200,
            )
        else:
            logger.warning(f"ROI validation failed for {video_path}: {result['error']}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result["error"],
                        "errors": result.get("errors", []),
                        "valid_rois": result.get("valid_rois", []),
                    }
                ),
                400,
            )

    except Exception as e:
        response, status_code = handle_general_error(e, "validate ROI coordinates")
        return jsonify(response), status_code


@step4_roi_bp.route("/save-roi-config", methods=["POST", "OPTIONS"])
def save_roi_configuration():
    """
    Save ROI configuration to processing_config table

    POST body:
        {
            "camera_id": "camera_1",
            "video_path": "/path/to/video.mp4",
            "roi_data": [
                {
                    "x": 100,
                    "y": 100,
                    "w": 200,
                    "h": 150,
                    "type": "packing_area",
                    "label": "Packing Area"
                }
            ],
            "packing_method": "traditional"  // "traditional" or "qr"
        }

    Returns:
        JSON with save results
    """
    try:
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body is required"}), 400

        # Validate required fields
        is_valid, error_msg = validate_required_fields(
            data, ["camera_id", "video_path", "roi_data", "packing_method"]
        )
        if not is_valid:
            return jsonify({"success": False, "error": error_msg}), 400

        camera_id = data["camera_id"]
        video_path = data["video_path"]
        roi_data = data["roi_data"]
        packing_method = data["packing_method"]

        logger.info(f"Saving ROI configuration for camera {camera_id}")

        # First validate the ROI data
        metadata_result = roi_video_service.get_video_metadata(video_path)
        if not metadata_result["success"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Cannot validate video: {metadata_result["error"]}',
                        "details": metadata_result.get("details", {}),
                    }
                ),
                400,
            )

        video_width = metadata_result["metadata"]["resolution"]["width"]
        video_height = metadata_result["metadata"]["resolution"]["height"]

        roi_validation = roi_video_service.validate_roi_coordinates(
            roi_data, video_width, video_height
        )
        if not roi_validation["valid"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'ROI validation failed: {roi_validation["error"]}',
                        "errors": roi_validation.get("errors", []),
                    }
                ),
                400,
            )

        # Save to database (packing_profiles table)
        try:
            from modules.db_utils import get_db_connection
            import json

            conn = get_db_connection()
            cursor = conn.cursor()

            # Separate different ROI types for both Traditional and QR methods
            packing_area_roi = None  # Both methods: movement detection/packing area
            qr_trigger_roi = None  # QR method only: small trigger area for QR detection

            for roi in roi_validation["validated_rois"]:
                if roi["type"] == "packing_area":
                    packing_area_roi = roi  # This will be saved to packing_area column
                elif roi["type"] == "qr_trigger":
                    qr_trigger_roi = roi  # This will be saved to qr_trigger_area column

            # Get QR boundary sizes from frontend sidebar (QR method only)
            # Frontend displays detected QR in sidebar, user confirms before saving
            expected_mvd_qr_size = None
            expected_trigger_qr_size = None

            if packing_method == "qr":
                logger.info(
                    "QR method detected - getting QR boundary sizes from frontend sidebar..."
                )

                # Frontend sends QR sizes that user saw in sidebar (may be NULL if not detected)
                mvd_qr_size = data.get("mvd_qr_size")  # {"width": 54, "height": 56} or None
                trigger_qr_size = data.get(
                    "trigger_qr_size"
                )  # {"width": 175, "height": 181} or None

                # Convert to JSON string for database storage (NULL is OK)
                if mvd_qr_size and isinstance(mvd_qr_size, dict):
                    expected_mvd_qr_size = json.dumps(mvd_qr_size)
                    logger.info(
                        f"✅ MVD QR boundary size: {mvd_qr_size['width']}x{mvd_qr_size['height']}px"
                    )
                else:
                    logger.info(
                        "ℹ️ No MVD QR detected - boundary size will be NULL (video may not show MVD QR)"
                    )

                if trigger_qr_size and isinstance(trigger_qr_size, dict):
                    expected_trigger_qr_size = json.dumps(trigger_qr_size)
                    logger.info(
                        f"✅ TimeGo QR boundary size: {trigger_qr_size['width']}x{trigger_qr_size['height']}px"
                    )
                else:
                    logger.info(
                        "ℹ️ No TimeGo QR detected - boundary size will be NULL (video may not show TimeGo QR)"
                    )

            # ✅ RETRIEVE BASELINE from cache (captured during QR preprocessing)
            baseline_captured = False
            baseline_data = None

            if packing_method == "qr":
                qr_cache_key = data.get("qr_cache_key")
                if qr_cache_key:
                    try:
                        if qr_cache_key in qr_baseline_cache:
                            baseline_info = qr_baseline_cache[qr_cache_key]
                            baseline_captured = True
                            baseline_data = {
                                "baseline_success_rate_pct": baseline_info.get(
                                    "baseline_success_rate_pct", 0
                                ),
                                "detected_frames": baseline_info.get("detected_frames", 0),
                                "total_frames": baseline_info.get("total_frames", 0),
                                "baseline_id": baseline_info.get("baseline_id"),
                                "first_timego_sec": baseline_info.get("first_timego_sec"),
                            }
                            logger.info(
                                f"✅ Retrieved cached baseline: {baseline_data['baseline_success_rate_pct']:.1f}%"
                            )
                        else:
                            logger.warning(
                                f"⚠️ Baseline cache not found for key: {qr_cache_key}. Available keys: {list(qr_baseline_cache.keys())}"
                            )
                    except Exception as baseline_error:
                        logger.warning(f"⚠️ Error retrieving baseline from cache: {baseline_error}")
                else:
                    logger.info("ℹ️ No QR cache key provided - baseline will not be included")

            # Create profile name based on camera (no timestamp for consistent lookup)
            profile_name = camera_id

            # Prepare additional params with full metadata
            additional_params = json.dumps(
                {
                    "camera_id": camera_id,
                    "video_path": video_path,
                    "packing_method": packing_method,
                    "video_metadata": metadata_result["metadata"],
                    "created_at": datetime.now().isoformat(),
                    "status": "configured",
                }
            )

            # Check if profile already exists for this camera
            cursor.execute("SELECT id FROM packing_profiles WHERE profile_name = ?", (camera_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing profile
                # packing_area column: stores movement detection area for both Traditional and QR methods
                # qr_trigger_area column: stores QR trigger area (QR method only)
                cursor.execute(
                    """
                    UPDATE packing_profiles
                    SET packing_area = ?,
                        qr_trigger_area = ?,
                        expected_mvd_qr_size = ?,
                        expected_trigger_qr_size = ?,
                        additional_params = ?
                    WHERE id = ?
                """,
                    (
                        # packing_area column: movement detection area (both Traditional and QR methods)
                        (
                            json.dumps(
                                [
                                    packing_area_roi["x"],
                                    packing_area_roi["y"],
                                    packing_area_roi["w"],
                                    packing_area_roi["h"],
                                ]
                            )
                            if packing_area_roi
                            else None
                        ),
                        # qr_trigger_area column: QR trigger area (QR method only)
                        (
                            json.dumps(
                                [
                                    qr_trigger_roi["x"],
                                    qr_trigger_roi["y"],
                                    qr_trigger_roi["w"],
                                    qr_trigger_roi["h"],
                                ]
                            )
                            if qr_trigger_roi
                            else None
                        ),
                        # expected_mvd_qr_size: Auto-detected MVD QR size for boundary filtering
                        expected_mvd_qr_size,
                        # expected_trigger_qr_size: Auto-detected TimeGo QR size for boundary filtering
                        expected_trigger_qr_size,
                        additional_params,
                        existing[0],
                    ),
                )
                logger.info(f"Updated packing profile for camera {camera_id}")
            else:
                # Insert new profile
                # packing_area column: stores movement detection area for both Traditional and QR methods
                # qr_trigger_area column: stores QR trigger area (QR method only)
                cursor.execute(
                    """
                    INSERT INTO packing_profiles
                    (profile_name, packing_area, qr_trigger_area, expected_mvd_qr_size,
                     expected_trigger_qr_size, min_packing_time, jump_time_ratio,
                     scan_mode, additional_params)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        profile_name,
                        # packing_area column: movement detection area (both Traditional and QR methods)
                        (
                            json.dumps(
                                [
                                    packing_area_roi["x"],
                                    packing_area_roi["y"],
                                    packing_area_roi["w"],
                                    packing_area_roi["h"],
                                ]
                            )
                            if packing_area_roi
                            else None
                        ),
                        # qr_trigger_area column: QR trigger area (QR method only)
                        (
                            json.dumps(
                                [
                                    qr_trigger_roi["x"],
                                    qr_trigger_roi["y"],
                                    qr_trigger_roi["w"],
                                    qr_trigger_roi["h"],
                                ]
                            )
                            if qr_trigger_roi
                            else None
                        ),
                        # expected_mvd_qr_size: Auto-detected MVD QR size for boundary filtering
                        expected_mvd_qr_size,
                        # expected_trigger_qr_size: Auto-detected TimeGo QR size for boundary filtering
                        expected_trigger_qr_size,
                        5,  # Default min_packing_time
                        0.5,  # Default jump_time_ratio
                        packing_method,  # traditional or qr
                        additional_params,
                    ),
                )
                logger.info(f"Created new packing profile: {profile_name}")

            conn.commit()
            conn.close()

            # ✅ Delete uploaded video file after successful configuration save
            try:
                if os.path.exists(video_path):
                    # Security check: only delete files from uploads directory (using centralized path resolution)
                    project_root = find_project_root(os.path.abspath(__file__))
                    uploads_dir = os.path.join(project_root, "var", "uploads", "videos")
                    if os.path.abspath(video_path).startswith(os.path.abspath(uploads_dir)):
                        os.remove(video_path)
                        logger.info(f"✅ Deleted uploaded video file: {video_path}")
                    else:
                        logger.debug(
                            f"⚠️ Video file outside uploads directory, not deleting: {video_path}"
                        )
                else:
                    logger.debug(f"Video file not found: {video_path}")
            except Exception as delete_error:
                logger.warning(f"⚠️ Failed to delete video file {video_path}: {delete_error}")
                # Don't fail the entire operation if deletion fails

            config_data = {
                "camera_id": camera_id,
                "video_path": video_path,
                "roi_configuration": roi_validation["validated_rois"],
                "packing_method": packing_method,
                "video_metadata": metadata_result["metadata"],
                "created_at": datetime.now().isoformat(),
                "status": "configured",
                "saved_to_database": True,
                "database_table": "packing_profiles",
                "profile_name": profile_name,
                "packing_area_saved": packing_area_roi is not None,
                "qr_trigger_saved": qr_trigger_roi is not None,
                "baseline_captured": baseline_captured,
            }

            # Add baseline info if captured
            if baseline_data:
                config_data["baseline"] = baseline_data

        except Exception as db_error:
            logger.error(f"Failed to save ROI to database: {db_error}")

            # ✅ Still delete video file even if database save fails
            try:
                if os.path.exists(video_path):
                    # Security check: only delete files from uploads directory (using centralized path resolution)
                    project_root = find_project_root(os.path.abspath(__file__))
                    uploads_dir = os.path.join(project_root, "var", "uploads", "videos")
                    if os.path.abspath(video_path).startswith(os.path.abspath(uploads_dir)):
                        os.remove(video_path)
                        logger.info(
                            f"✅ Deleted uploaded video file (after DB error): {video_path}"
                        )
                    else:
                        logger.debug(
                            f"⚠️ Video file outside uploads directory, not deleting: {video_path}"
                        )
                else:
                    logger.debug(f"Video file not found: {video_path}")
            except Exception as delete_error:
                logger.warning(f"⚠️ Failed to delete video file {video_path}: {delete_error}")

            # Still return success for validation, but note database error
            config_data = {
                "camera_id": camera_id,
                "video_path": video_path,
                "roi_configuration": roi_validation["validated_rois"],
                "packing_method": packing_method,
                "video_metadata": metadata_result["metadata"],
                "created_at": datetime.now().isoformat(),
                "status": "configured",
                "saved_to_database": False,
                "database_table": "packing_profiles",
                "database_error": str(db_error),
                "baseline_captured": baseline_captured,
            }

            # Add baseline info even if database save failed
            if baseline_data:
                config_data["baseline"] = baseline_data

        # Stop any active detection processes before completing save
        try:
            logger.info("Triggering detection process termination...")

            cache_cleanup_attempted = []

            # ✅ SIMPLE APPROACH: Just set cancellation flags and let the "skip to end" logic handle it
            try:
                from blueprints.simple_hand_detection_bp import preprocessing_progress

                if preprocessing_progress:
                    progress_size = len(preprocessing_progress)
                    for cache_key in list(preprocessing_progress.keys()):
                        preprocessing_progress[cache_key]["cancelled"] = True
                        logger.info(f"Triggered hand detection skip-to-end for: {cache_key}")
                    cache_cleanup_attempted.append(f"hand_detection:{progress_size}_jobs_triggered")
            except Exception as e:
                logger.warning(f"Could not trigger hand detection termination: {e}")

            try:
                from blueprints.qr_detection_bp import qr_preprocessing_progress

                if qr_preprocessing_progress:
                    progress_size = len(qr_preprocessing_progress)
                    for cache_key in list(qr_preprocessing_progress.keys()):
                        qr_preprocessing_progress[cache_key]["cancelled"] = True
                        logger.info(f"Triggered QR detection skip-to-end for: {cache_key}")
                    cache_cleanup_attempted.append(f"qr_detection:{progress_size}_jobs_triggered")
            except Exception as e:
                logger.warning(f"Could not trigger QR detection termination: {e}")

            # Give processes a brief moment to detect cancellation and skip to end
            import time

            time.sleep(0.2)  # Minimal delay

            logger.info("Detection termination signals sent - processes will finish quickly")

        except Exception as cleanup_error:
            logger.warning(f"Detection process cleanup failed: {cleanup_error}")
            # Continue with success even if cleanup fails

        logger.info(f"ROI configuration saved successfully for camera {camera_id}")

        return (
            jsonify(
                {
                    "success": True,
                    "data": config_data,
                    "message": f"ROI configuration saved for camera {camera_id}",
                    "detection_cleanup": "completed",
                    "cleaned_caches": (
                        cache_cleanup_attempted if "cache_cleanup_attempted" in locals() else []
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        response, status_code = handle_general_error(e, "save ROI configuration")
        return jsonify(response), status_code


@step4_roi_bp.route("/upload-video", methods=["POST", "OPTIONS"])
def upload_video():
    """
    Upload video file for processing

    POST body (multipart/form-data):
        video: Video file

    Returns:
        JSON with file path on server
    """
    try:
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200

        if "video" not in request.files:
            return jsonify({"success": False, "error": "No video file provided"}), 400

        file = request.files["video"]

        if file.filename == "":
            return jsonify({"success": False, "error": "Empty filename"}), 400

        # Validate file extension
        allowed_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Unsupported file type: {file_ext}. Allowed: {", ".join(allowed_extensions)}',
                    }
                ),
                400,
            )

        # Create upload directory if it doesn't exist (using project root, not cwd)
        project_root = find_project_root(os.path.abspath(__file__))
        upload_dir = os.path.join(project_root, "var", "uploads", "videos")
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)

        # Save file
        file.save(file_path)

        logger.info(f"Video uploaded successfully: {file_path}")

        return (
            jsonify(
                {
                    "success": True,
                    "file_path": file_path,
                    "filename": safe_filename,
                    "original_name": file.filename,
                }
            ),
            200,
        )

    except Exception as e:
        response, status_code = handle_general_error(e, "upload video")
        return jsonify(response), status_code


# Register error handlers for this blueprint
@step4_roi_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    return jsonify({"success": False, "error": "Bad request", "details": str(error)}), 400


@step4_roi_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({"success": False, "error": "Endpoint not found", "details": str(error)}), 404


@step4_roi_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(error)}")
    return (
        jsonify(
            {
                "success": False,
                "error": "Internal server error",
                "details": "Please check server logs for details",
            }
        ),
        500,
    )
