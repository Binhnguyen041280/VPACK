from flask import Blueprint, request, jsonify
from modules.technician.qr_detector import (
    detect_qr_at_time,
    preprocess_video_qr,
    detect_qr_from_image,
)
from modules.technician.camera_health_baseline import capture_baseline_from_step4
from modules.technician.camera_health_checker import (
    run_health_check,
    get_latest_health_check,
    get_baseline_by_camera,
    evaluate_camera_health_checklist,
)
from modules.db_utils.safe_connection import safe_db_connection
import os
import json
import logging
import sys
import threading
import time
import hashlib
from datetime import datetime, timedelta

qr_detection_bp = Blueprint("qr_detection", __name__)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# In-memory cache for pre-processed QR detections (same pattern as hand detection)
# Structure: {cache_key: {'detections': [...], 'metadata': {...}, 'expires_at': datetime}}
qr_preprocessing_cache = {}
qr_preprocessing_progress = {}  # Track progress for ongoing processing

# Baseline capture cache - stores baseline metrics captured during QR preprocessing
# Structure: {cache_key: {'baseline_success_rate_pct': float, 'detected_frames': int, 'total_frames': int, 'baseline_id': int, 'expires_at': datetime}}
qr_baseline_cache = {}

# ✅ FIXED: Use same path calculation as hand_detection_bp.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "CameraROI")


def generate_qr_cache_key(video_path: str, roi_config: dict) -> str:
    """Generate unique cache key for video + ROI combination"""
    roi_str = f"{roi_config['x']}_{roi_config['y']}_{roi_config['w']}_{roi_config['h']}"
    cache_input = f"{video_path}_{roi_str}"
    return hashlib.md5(cache_input.encode()).hexdigest()


def cleanup_expired_qr_cache():
    """Remove expired QR cache entries"""
    global qr_preprocessing_cache

    now = datetime.now()
    expired_keys = [
        key
        for key, cache_data in qr_preprocessing_cache.items()
        if cache_data.get("expires_at", now) <= now
    ]

    for key in expired_keys:
        del qr_preprocessing_cache[key]
        logger.info(f"Removed expired QR cache entry: {key}")


@qr_detection_bp.route("/preprocess-video", methods=["POST"])
def preprocess_qr_video():
    """
    Pre-process entire video for QR detection at 5fps
    Results are cached for perfect synchronization during playback

    Request body:
    {
        "video_path": str,
        "roi_config": {
            "x": int, "y": int, "w": int, "h": int
        },
        "fps": int (optional, default 5)
    }

    Response:
    {
        "success": bool,
        "cache_key": str,
        "status": "started" | "completed" | "in_progress",
        "progress": float (0-100),
        "detections": list (if completed),
        "metadata": dict (if completed),
        "error": str (if error)
    }
    """
    try:
        # Clean up expired cache first
        cleanup_expired_qr_cache()

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate required parameters
        video_path = data.get("video_path")
        roi_config = data.get("roi_config")
        fps = data.get("fps", 5)  # Default 5fps

        # Optional parameters for baseline capture
        camera_name = data.get("camera_name")
        packing_profile_id = data.get("packing_profile_id")

        if camera_name:
            logger.info(
                f"[BASELINE] QR preprocessing will capture baseline for camera: {camera_name}"
            )
        else:
            logger.warning(f"[BASELINE] No camera_name provided - baseline capture will be skipped")

        if not video_path:
            return (
                jsonify({"success": False, "error": "Missing required parameter: video_path"}),
                400,
            )

        if not roi_config:
            return (
                jsonify({"success": False, "error": "Missing required parameter: roi_config"}),
                400,
            )

        # Validate ROI config
        required_roi_fields = ["x", "y", "w", "h"]
        for field in required_roi_fields:
            if field not in roi_config:
                return jsonify({"success": False, "error": f"Missing ROI field: {field}"}), 400
            try:
                roi_config[field] = int(roi_config[field])
                if roi_config[field] < 0:
                    raise ValueError(f"ROI {field} must be non-negative")
            except (ValueError, TypeError) as e:
                return (
                    jsonify({"success": False, "error": f"Invalid ROI {field} value: {str(e)}"}),
                    400,
                )

        # Validate fps
        try:
            fps = int(fps)
            if fps <= 0 or fps > 30:
                raise ValueError("fps must be between 1 and 30")
        except (ValueError, TypeError) as e:
            return jsonify({"success": False, "error": f"Invalid fps value: {str(e)}"}), 400

        # Generate cache key
        cache_key = generate_qr_cache_key(video_path, roi_config)

        # Check if already cached and not expired
        if cache_key in qr_preprocessing_cache:
            cache_data = qr_preprocessing_cache[cache_key]
            if cache_data.get("expires_at", datetime.now()) > datetime.now():
                logger.info(f"Returning cached QR results for {cache_key}")
                return (
                    jsonify(
                        {
                            "success": True,
                            "cache_key": cache_key,
                            "status": "completed",
                            "progress": 100.0,
                            "detections": cache_data["detections"],
                            "metadata": cache_data["metadata"],
                        }
                    ),
                    200,
                )

        # Check if processing is already in progress
        if cache_key in qr_preprocessing_progress:
            progress_data = qr_preprocessing_progress[cache_key]
            return (
                jsonify(
                    {
                        "success": True,
                        "cache_key": cache_key,
                        "status": "in_progress",
                        "progress": progress_data.get("progress", 0.0),
                        "estimated_completion": progress_data.get("estimated_completion"),
                    }
                ),
                202,
            )  # 202 Accepted - Processing

        # ✅ OPTION B: Baseline capture runs in PARALLEL with QR preprocessing
        # Baseline completes in ~5-10 seconds, doesn't wait for full video processing

        def background_baseline_capture():
            """Async baseline capture - runs independently of QR preprocessing"""
            try:
                logger.info(f"[BASELINE] Starting parallel baseline capture for {camera_name}")

                baseline_result = capture_baseline_from_step4(
                    camera_name=camera_name,
                    video_path=video_path,
                    trigger_roi=roi_config,
                    packing_profile_id=packing_profile_id,
                )

                # Cache baseline immediately
                if baseline_result.get("success"):
                    qr_baseline_cache[cache_key] = {
                        "baseline_success_rate_pct": baseline_result.get(
                            "baseline_success_rate_pct", 0
                        ),
                        "detected_frames": baseline_result.get("detected_frames", 0),
                        "total_frames": baseline_result.get("total_frames", 0),
                        "baseline_id": baseline_result.get("baseline_id"),
                        "first_timego_sec": baseline_result.get("first_timego_sec"),
                        "expires_at": datetime.now() + timedelta(minutes=30),
                    }
                    logger.info(
                        f"[BASELINE] ✅ Baseline READY: {baseline_result.get('baseline_success_rate_pct', 0):.1f}% ({baseline_result.get('detected_frames', 0)}/{baseline_result.get('total_frames', 0)}) for {cache_key}"
                    )
                else:
                    logger.warning(
                        f"[BASELINE] Baseline capture failed: {baseline_result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                logger.error(
                    f"[BASELINE] Error in parallel baseline capture: {str(e)}", exc_info=True
                )

        def background_qr_processing():
            try:
                # Initialize progress tracking - simplified
                qr_preprocessing_progress[cache_key] = {
                    "progress": 0.0,
                    "started_at": datetime.now(),
                    "estimated_completion": None,
                    "processed_count": 0,
                    "total_frames": 0,
                    "camera_name": camera_name,  # Store for baseline capture
                    "packing_profile_id": packing_profile_id,
                    "roi_config": roi_config,  # Store ROI config for baseline
                }

                # Initialize main cache entry for progressive accumulation
                qr_preprocessing_cache[cache_key] = {
                    "detections": [],  # Start with empty list to accumulate
                    "metadata": {
                        "partial_results": True,
                        "progress": 0.0,
                        "processed_count": 0,
                        "total_frames": 0,
                    },
                    "expires_at": datetime.now() + timedelta(minutes=30),
                    "processed_at": datetime.now(),
                }

                # Progress callback function - simplified with skip-to-end logic
                def update_qr_progress(
                    progress, processed_count, total_frames, new_detections=None
                ):
                    # Check for cancellation flag and trigger skip-to-end
                    if cache_key not in qr_preprocessing_progress:
                        logger.info(
                            f"QR preprocessing cancelled - progress tracking removed for {cache_key}"
                        )
                        raise Exception(f"QR preprocessing cancelled for {cache_key}")

                    if qr_preprocessing_progress[cache_key].get("cancelled", False):
                        logger.info(f"QR preprocessing skip-to-end triggered for {cache_key}")
                        raise Exception(f"QR preprocessing cancelled for {cache_key}")

                    qr_preprocessing_progress[cache_key].update(
                        {
                            "progress": progress,
                            "processed_count": processed_count,
                            "total_frames": total_frames,
                        }
                    )

                    # Accumulate new detections into main cache (không overwrite)
                    if new_detections and len(new_detections) > 0:
                        if cache_key in qr_preprocessing_cache:
                            # Append new detections to existing list instead of replacing
                            qr_preprocessing_cache[cache_key]["detections"].extend(new_detections)
                            qr_preprocessing_cache[cache_key]["metadata"].update(
                                {
                                    "progress": progress,
                                    "processed_count": processed_count,
                                    "total_frames": total_frames,
                                }
                            )
                            total_detections = len(qr_preprocessing_cache[cache_key]["detections"])
                            logger.debug(
                                f"QR: Accumulated {len(new_detections)} new detections. Total: {total_detections} for {cache_key}"
                            )
                        else:
                            logger.warning(f"QR: Cache key {cache_key} not found during update")

                logger.info(f"Starting QR video pre-processing for cache key: {cache_key}")

                # Call the QR pre-processing function with progress callback
                result = preprocess_video_qr(
                    video_path, roi_config, fps, progress_callback=update_qr_progress
                )

                if result.get("success"):
                    # Cache the QR results for 30 minutes
                    expires_at = datetime.now() + timedelta(minutes=30)
                    qr_preprocessing_cache[cache_key] = {
                        "detections": result["detections"],
                        "metadata": result["metadata"],
                        "expires_at": expires_at,
                        "processed_at": datetime.now(),
                    }

                    total_qr_detections = sum(d.get("qr_count", 0) for d in result["detections"])
                    logger.info(
                        f"QR pre-processing completed for {cache_key}: {len(result['detections'])} timeline entries, {total_qr_detections} QR detections cached"
                    )
                else:
                    if "cancelled" in str(result.get("error", "")).lower():
                        logger.info(
                            f"QR pre-processing cancelled for {cache_key}: {result.get('error')}"
                        )
                    else:
                        logger.error(
                            f"QR pre-processing failed for {cache_key}: {result.get('error')}"
                        )

                # Clean up progress tracking
                if cache_key in qr_preprocessing_progress:
                    del qr_preprocessing_progress[cache_key]

            except Exception as e:
                if "cancelled" in str(e).lower():
                    logger.info(f"Background QR processing cancelled for {cache_key}: {str(e)}")
                else:
                    logger.error(f"Background QR processing error for {cache_key}: {str(e)}")
                if cache_key in qr_preprocessing_progress:
                    del qr_preprocessing_progress[cache_key]

        # ✅ Start BOTH threads in parallel
        # - Baseline thread completes in ~5-10 seconds (3 second sample)
        # - QR preprocessing continues independently (30-60 seconds)
        baseline_thread = threading.Thread(
            target=background_baseline_capture, daemon=True, name=f"baseline-{cache_key[:8]}"
        )
        baseline_thread.start()

        qr_thread = threading.Thread(
            target=background_qr_processing, daemon=True, name=f"qr-{cache_key[:8]}"
        )
        qr_thread.start()

        return (
            jsonify(
                {
                    "success": True,
                    "cache_key": cache_key,
                    "status": "started",
                    "progress": 0.0,
                    "message": f"QR pre-processing started for video at {fps}fps",
                    "estimated_duration_seconds": "10-30",  # Rough estimate
                }
            ),
            202,
        )  # 202 Accepted - Processing started

    except Exception as e:
        error_msg = f"Unexpected error in QR preprocess-video endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@qr_detection_bp.route("/preprocess-status/<cache_key>", methods=["GET"])
def qr_preprocess_status(cache_key: str):
    """
    Check status of QR video pre-processing

    Response:
    {
        "success": bool,
        "status": "completed" | "in_progress" | "not_found",
        "progress": float (0-100),
        "detections": list (if completed),
        "metadata": dict (if completed),
        "error": str (if error)
    }
    """
    try:
        cleanup_expired_qr_cache()

        # Check if completed and cached
        if cache_key in qr_preprocessing_cache:
            cache_data = qr_preprocessing_cache[cache_key]
            if cache_data.get("expires_at", datetime.now()) > datetime.now():
                return (
                    jsonify(
                        {
                            "success": True,
                            "status": "completed",
                            "progress": 100.0,
                            "detections": cache_data["detections"],
                            "metadata": cache_data["metadata"],
                            "processed_at": cache_data["processed_at"].isoformat(),
                            "expires_at": cache_data["expires_at"].isoformat(),
                        }
                    ),
                    200,
                )

        # Check if still in progress
        if cache_key in qr_preprocessing_progress:
            progress_data = qr_preprocessing_progress[cache_key]
            return (
                jsonify(
                    {
                        "success": True,
                        "status": "in_progress",
                        "progress": progress_data.get("progress", 0.0),
                        "processed_count": progress_data.get("processed_count", 0),
                        "total_frames": progress_data.get("total_frames", 0),
                        "started_at": progress_data["started_at"].isoformat(),
                        "estimated_completion": progress_data.get("estimated_completion"),
                    }
                ),
                200,
            )

        # Not found
        return (
            jsonify(
                {
                    "success": False,
                    "status": "not_found",
                    "error": f"No QR processing found for cache key: {cache_key}",
                }
            ),
            404,
        )

    except Exception as e:
        error_msg = f"Error checking QR preprocess status: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@qr_detection_bp.route("/get-cached-qr", methods=["POST"])
def get_cached_qr():
    """
    Get QR detections for specific timestamp from cached results

    Request body:
    {
        "cache_key": str,
        "timestamp": float,
        "canvas_dims": {  # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "video_dims": {   # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "roi_config": {   # optional - for display coordinate mapping
            "x": int,
            "y": int,
            "w": int,
            "h": int
        }
    }

    Response:
    {
        "success": bool,
        "qr_detections": list | null,
        "canvas_qr_detections": list | null,  # NEW - display-ready coordinates
        "exact_match": bool,
        "matched_timestamp": float | null,
        "qr_count": int,
        "error": str (if error)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        cache_key = data.get("cache_key")
        timestamp = data.get("timestamp")
        canvas_dims = data.get("canvas_dims")
        video_dims = data.get("video_dims")
        roi_config = data.get("roi_config")

        if not cache_key:
            return (
                jsonify({"success": False, "error": "Missing required parameter: cache_key"}),
                400,
            )

        if timestamp is None:
            return (
                jsonify({"success": False, "error": "Missing required parameter: timestamp"}),
                400,
            )

        try:
            timestamp = float(timestamp)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid timestamp value"}), 400

        # Check main cache
        if cache_key not in qr_preprocessing_cache:
            return jsonify({"success": False, "error": "QR cache key not found or expired"}), 404

        cache_data = qr_preprocessing_cache[cache_key]
        if cache_data.get("expires_at", datetime.now()) <= datetime.now():
            del qr_preprocessing_cache[cache_key]
            return jsonify({"success": False, "error": "QR cache expired"}), 404

        # Find QR detections for timestamp (exact match within 0.15s tolerance)
        detections = cache_data["detections"]
        closest_detection = None
        min_time_diff = float("inf")

        for detection in detections:
            time_diff = abs(detection["timestamp"] - timestamp)
            if (
                time_diff < 0.15 and time_diff < min_time_diff
            ):  # 0.15s tolerance for 5fps (0.2s interval)
                closest_detection = detection
                min_time_diff = time_diff

        if closest_detection:
            qr_detections = closest_detection.get("qr_detections", [])
            qr_count = closest_detection.get("qr_count", 0)

            response = {
                "success": True,
                "qr_detections": qr_detections,
                "exact_match": min_time_diff < 0.05,  # Consider <0.05s as exact match
                "matched_timestamp": closest_detection["timestamp"],
                "qr_count": qr_count,
                "time_difference": round(min_time_diff, 3),
            }

            # Add canvas_qr_detections using LandmarkMapper for consistent coordinate transformation
            if canvas_dims and video_dims and roi_config and qr_detections:
                try:
                    from modules.technician.landmark_mapper import (
                        LandmarkMapper,
                        ROIConfig,
                        VideoDimensions,
                        CanvasDimensions,
                    )

                    # Create mapping objects
                    roi = ROIConfig(
                        x=roi_config["x"], y=roi_config["y"], w=roi_config["w"], h=roi_config["h"]
                    )
                    video_dimensions = VideoDimensions(
                        width=video_dims["width"], height=video_dims["height"]
                    )
                    canvas_dimensions = CanvasDimensions(
                        width=canvas_dims["width"], height=canvas_dims["height"]
                    )

                    # Use LandmarkMapper for coordinate transformation
                    qr_mapping_response = LandmarkMapper.create_canvas_qr_response(
                        qr_detections, roi, video_dimensions, canvas_dimensions
                    )

                    if qr_mapping_response["success"]:
                        response["canvas_qr_detections"] = qr_mapping_response[
                            "canvas_qr_detections"
                        ]
                        response["mapping_algorithm"] = qr_mapping_response["mapping_algorithm"]
                        response["mapping_info"] = qr_mapping_response["mapping_info"]
                        logger.debug(
                            f"LandmarkMapper: Mapped {len(qr_mapping_response['canvas_qr_detections'])} QR detections for timestamp {timestamp}"
                        )
                    else:
                        logger.warning(
                            f"LandmarkMapper QR mapping failed: {qr_mapping_response.get('error')}"
                        )
                        response["canvas_qr_detections"] = []

                except Exception as e:
                    logger.error(f"Error using LandmarkMapper for QR coordinate mapping: {e}")
                    response["canvas_qr_detections"] = []
            else:
                response["canvas_qr_detections"] = []

            return jsonify(response), 200
        else:
            return (
                jsonify(
                    {
                        "success": True,
                        "qr_detections": [],
                        "canvas_qr_detections": [],
                        "exact_match": False,
                        "matched_timestamp": None,
                        "qr_count": 0,
                        "message": f"No QR detection found near timestamp {timestamp}",
                    }
                ),
                200,
            )

    except Exception as e:
        error_msg = f"Error getting cached QR detections: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@qr_detection_bp.route("/get-cached-trigger", methods=["POST"])
def get_cached_trigger():
    """
    Get QR trigger detections for specific timestamp from cached results
    Specifically looks for "timego" text in QR codes within trigger area

    Request body:
    {
        "cache_key": str,  # Can include "_trigger" suffix for trigger-specific cache
        "timestamp": float,
        "canvas_dims": {  # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "video_dims": {   # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "roi_config": {   # trigger area ROI coordinates
            "x": int,
            "y": int,
            "w": int,
            "h": int
        },
        "trigger_mode": bool,  # Flag to indicate trigger detection mode
        "target_text": str     # Text to search for (default: "TimeGo")
    }

    Response:
    {
        "success": bool,
        "trigger_detected": bool,
        "trigger_text": str | null,
        "qr_detections": list,     # All QR detections in trigger area
        "canvas_qr_detections": list,  # Display-ready coordinates
        "exact_match": bool,
        "matched_timestamp": float | null,
        "detection_confidence": float,
        "error": str (if error)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        cache_key = data.get("cache_key")
        timestamp = data.get("timestamp")
        canvas_dims = data.get("canvas_dims")
        video_dims = data.get("video_dims")
        roi_config = data.get("roi_config")
        trigger_mode = data.get("trigger_mode", True)
        target_text = data.get(
            "target_text", "TimeGo"
        ).lower()  # Default to "TimeGo", convert to lowercase for comparison

        if not cache_key:
            return (
                jsonify({"success": False, "error": "Missing required parameter: cache_key"}),
                400,
            )

        if timestamp is None:
            return (
                jsonify({"success": False, "error": "Missing required parameter: timestamp"}),
                400,
            )

        try:
            timestamp = float(timestamp)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid timestamp value"}), 400

        # Remove "_trigger" suffix from cache key if present for main cache lookup
        main_cache_key = (
            cache_key.replace("_trigger", "") if cache_key.endswith("_trigger") else cache_key
        )

        # Check main QR cache (trigger detection uses same QR preprocessing)
        if main_cache_key not in qr_preprocessing_cache:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "QR cache key not found or expired",
                        "trigger_detected": False,
                        "trigger_text": None,
                    }
                ),
                404,
            )

        cache_data = qr_preprocessing_cache[main_cache_key]
        if cache_data.get("expires_at", datetime.now()) <= datetime.now():
            del qr_preprocessing_cache[main_cache_key]
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "QR cache expired",
                        "trigger_detected": False,
                        "trigger_text": None,
                    }
                ),
                404,
            )

        # Find QR detections for timestamp (exact match within 0.15s tolerance)
        detections = cache_data["detections"]
        closest_detection = None
        min_time_diff = float("inf")

        for detection in detections:
            time_diff = abs(detection["timestamp"] - timestamp)
            if time_diff < 0.15 and time_diff < min_time_diff:  # 0.15s tolerance for 5fps
                closest_detection = detection
                min_time_diff = time_diff

        if closest_detection:
            qr_detections = closest_detection.get("qr_detections", [])

            # Filter QR detections for trigger area and search for target text
            trigger_detected = False
            trigger_text = None
            detection_confidence = 0.0
            trigger_qr_detections = []

            if roi_config and qr_detections:
                # Filter QR detections that fall within trigger ROI area
                trigger_x, trigger_y, trigger_w, trigger_h = (
                    roi_config["x"],
                    roi_config["y"],
                    roi_config["w"],
                    roi_config["h"],
                )

                for qr_detection in qr_detections:
                    qr_bbox = qr_detection.get("bbox", {})
                    if not qr_bbox:
                        continue

                    # Check if QR detection bbox overlaps with trigger ROI
                    qr_x, qr_y, qr_w, qr_h = (
                        qr_bbox.get("x", 0),
                        qr_bbox.get("y", 0),
                        qr_bbox.get("w", 0),
                        qr_bbox.get("h", 0),
                    )

                    # Check for overlap between QR bbox and trigger ROI
                    overlap_x = max(
                        0, min(trigger_x + trigger_w, qr_x + qr_w) - max(trigger_x, qr_x)
                    )
                    overlap_y = max(
                        0, min(trigger_y + trigger_h, qr_y + qr_h) - max(trigger_y, qr_y)
                    )
                    overlap_area = overlap_x * overlap_y

                    if overlap_area > 0:  # QR detection is within trigger area
                        trigger_qr_detections.append(qr_detection)

                        # Check if QR text contains target text
                        qr_text = qr_detection.get("text", "").lower()
                        if target_text in qr_text:
                            trigger_detected = True
                            trigger_text = qr_detection.get("text", "")
                            detection_confidence = qr_detection.get("confidence", 0.0)
                            logger.info(
                                f"Trigger detected: '{trigger_text}' at timestamp {timestamp}"
                            )
                            break

            response = {
                "success": True,
                "trigger_detected": trigger_detected,
                "trigger_text": trigger_text,
                "qr_detections": trigger_qr_detections,
                "exact_match": min_time_diff < 0.05,
                "matched_timestamp": closest_detection["timestamp"],
                "detection_confidence": detection_confidence,
                "time_difference": round(min_time_diff, 3),
                "target_text": target_text,
                "trigger_roi": roi_config,
                "total_qr_in_area": len(trigger_qr_detections),
            }

            # Add canvas_qr_detections for trigger area QR codes
            if canvas_dims and video_dims and roi_config and trigger_qr_detections:
                try:
                    from modules.technician.landmark_mapper import (
                        LandmarkMapper,
                        ROIConfig,
                        VideoDimensions,
                        CanvasDimensions,
                    )

                    # Create mapping objects for trigger ROI
                    roi = ROIConfig(
                        x=roi_config["x"], y=roi_config["y"], w=roi_config["w"], h=roi_config["h"]
                    )
                    video_dimensions = VideoDimensions(
                        width=video_dims["width"], height=video_dims["height"]
                    )
                    canvas_dimensions = CanvasDimensions(
                        width=canvas_dims["width"], height=canvas_dims["height"]
                    )

                    # Use LandmarkMapper for coordinate transformation
                    qr_mapping_response = LandmarkMapper.create_canvas_qr_response(
                        trigger_qr_detections, roi, video_dimensions, canvas_dimensions
                    )

                    if qr_mapping_response["success"]:
                        response["canvas_qr_detections"] = qr_mapping_response[
                            "canvas_qr_detections"
                        ]
                        response["mapping_algorithm"] = qr_mapping_response["mapping_algorithm"]
                        response["mapping_info"] = qr_mapping_response["mapping_info"]
                        logger.debug(
                            f"LandmarkMapper: Mapped {len(qr_mapping_response['canvas_qr_detections'])} trigger QR detections for timestamp {timestamp}"
                        )
                    else:
                        logger.warning(
                            f"LandmarkMapper trigger QR mapping failed: {qr_mapping_response.get('error')}"
                        )
                        response["canvas_qr_detections"] = []

                except Exception as e:
                    logger.error(
                        f"Error using LandmarkMapper for trigger QR coordinate mapping: {e}"
                    )
                    response["canvas_qr_detections"] = []
            else:
                response["canvas_qr_detections"] = []

            return jsonify(response), 200
        else:
            return (
                jsonify(
                    {
                        "success": True,
                        "trigger_detected": False,
                        "trigger_text": None,
                        "qr_detections": [],
                        "canvas_qr_detections": [],
                        "exact_match": False,
                        "matched_timestamp": None,
                        "detection_confidence": 0.0,
                        "message": f"No QR detection found near timestamp {timestamp}",
                    }
                ),
                200,
            )

    except Exception as e:
        error_msg = f"Error getting cached trigger detections: {str(e)}"
        logger.error(error_msg)
        return (
            jsonify(
                {
                    "success": False,
                    "error": error_msg,
                    "trigger_detected": False,
                    "trigger_text": None,
                }
            ),
            500,
        )


@qr_detection_bp.route("/detect-qr-image", methods=["POST"])
def detect_qr_from_uploaded_image():
    """
    Detect QR codes from uploaded image using WeChat QRCode model

    Request JSON:
    {
        "image_content": "base64_string",
        "image_name": "filename.jpg" (optional)
    }

    Response JSON:
    {
        "success": bool,
        "qr_detections": [str] - Array of detected QR code texts,
        "qr_count": int,
        "image_name": str (if provided),
        "error": str (if success=False)
    }
    """
    try:
        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        image_content = data.get("image_content")
        image_name = data.get("image_name", "unknown.jpg")

        if not image_content:
            return jsonify({"success": False, "error": "image_content is required"}), 400

        logger.info(f"[QR-IMAGE] Processing image: {image_name}")

        # Call the QR detection function
        result = detect_qr_from_image(image_content)

        # Add image name to response
        if result.get("success"):
            result["image_name"] = image_name
            logger.info(
                f"[QR-IMAGE] Success: {result.get('qr_count', 0)} QR codes detected in {image_name}"
            )
        else:
            logger.warning(
                f"[QR-IMAGE] Failed: {result.get('error', 'Unknown error')} for {image_name}"
            )

        return jsonify(result), 200 if result.get("success") else 400

    except Exception as e:
        error_msg = f"Image QR detection endpoint error: {str(e)}"
        logger.error(f"[QR-IMAGE] {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@qr_detection_bp.route("/get-baseline-info/<cache_key>", methods=["GET"])
def get_baseline_info(cache_key: str):
    """
    Get cached baseline information captured during QR preprocessing

    Response:
    {
        "success": bool,
        "baseline_available": bool,
        "baseline_success_rate_pct": float (if available),
        "detected_frames": int (if available),
        "total_frames": int (if available),
        "baseline_id": int (if available),
        "first_timego_sec": float (if available),
        "error": str (if error)
    }
    """
    try:
        # Check if baseline is cached and not expired
        if cache_key in qr_baseline_cache:
            baseline_data = qr_baseline_cache[cache_key]

            # Check expiration
            if baseline_data.get("expires_at", datetime.now()) <= datetime.now():
                del qr_baseline_cache[cache_key]
                return (
                    jsonify(
                        {
                            "success": False,
                            "baseline_available": False,
                            "error": "Baseline cache expired",
                        }
                    ),
                    404,
                )

            # Return cached baseline
            return (
                jsonify(
                    {
                        "success": True,
                        "baseline_available": True,
                        "baseline_success_rate_pct": baseline_data.get(
                            "baseline_success_rate_pct", 0
                        ),
                        "detected_frames": baseline_data.get("detected_frames", 0),
                        "total_frames": baseline_data.get("total_frames", 0),
                        "baseline_id": baseline_data.get("baseline_id"),
                        "first_timego_sec": baseline_data.get("first_timego_sec"),
                    }
                ),
                200,
            )

        # Not cached
        return (
            jsonify(
                {
                    "success": False,
                    "baseline_available": False,
                    "error": "No baseline found for this cache key",
                }
            ),
            404,
        )

    except Exception as e:
        error_msg = f"Error getting baseline info: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "baseline_available": False, "error": error_msg}), 500


@qr_detection_bp.route("/camera-health-check", methods=["POST"])
def camera_health_check():
    """
    Run health check for a camera

    Request:
    {
        "camera_name": "Cam1_PackingTable",
        "video_path": "/path/to/video.mp4"
    }

    Response:
    {
        "success": true,
        "camera_name": "Cam1_PackingTable",
        "baseline": {"success_rate_pct": 93.3},
        "current": {"success_rate_pct": 86.7, "detected": 13, "total": 15},
        "comparison": {"degradation_pct": -7.0, "status": "OK"},
        "diagnosis": {"probable_causes": [], "primary_cause": null, "recommended_action": "..."},
        "alert": {"severity": "INFO", "message": "QR success rate: 86.7%..."}
    }
    """
    try:
        data = request.get_json()
        camera_name = data.get("camera_name")
        video_path = data.get("video_path")

        if not camera_name or not video_path:
            return jsonify({"success": False, "error": "camera_name and video_path required"}), 400

        if not os.path.exists(video_path):
            return jsonify({"success": False, "error": f"Video not found: {video_path}"}), 404

        # Run health check
        result = run_health_check(camera_name, video_path)

        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        error_msg = f"Health check error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@qr_detection_bp.route("/camera-health-status/<camera_name>", methods=["GET"])
def get_camera_health_status(camera_name):
    """
    Get latest health status for a camera

    Response:
    {
        "success": true,
        "camera_name": "Cam1_PackingTable",
        "baseline": {
            "exists": true,
            "success_rate_pct": 93.3
        },
        "latest_check": {
            "current_success_rate_pct": 86.7,
            "degradation_pct": -7.0,
            "status": "OK",
            "severity": "INFO",
            "message": "QR success rate: 86.7% (baseline: 93.3%) - Degraded 7.0%",
            "recommendation": "Monitor next check or restart system",
            "timestamp": "2025-10-25T14:30:00"
        }
    }
    """
    try:
        # Get baseline
        baseline = get_baseline_by_camera(camera_name)
        baseline_info = {
            "exists": baseline is not None,
            "success_rate_pct": baseline["baseline_success_rate_pct"] if baseline else None,
        }

        # Get latest check
        latest_check = get_latest_health_check(camera_name)

        # ✅ Transform 'status' key to 'overall_status' for frontend consistency
        if latest_check and "status" in latest_check:
            latest_check["overall_status"] = latest_check.pop("status")

        result = {
            "success": True,
            "camera_name": camera_name,
            "baseline": baseline_info,
            "latest_check": latest_check,
        }

        return jsonify(result), 200

    except Exception as e:
        error_msg = f"Error getting health status: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@qr_detection_bp.route("/cameras", methods=["GET"])
def get_all_cameras():
    """
    Get all cameras with baseline information and latest health check status

    Response:
    [
        {
            "camera_name": "Cloud_Cam3",
            "baseline_success_rate_pct": 93.3,
            "status": "active",
            "overall_status": "CRITICAL"  // Latest health check status
        },
        ...
    ]
    """
    try:
        from modules.db_utils.safe_connection import safe_db_connection

        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT camera_name, baseline_success_rate_pct, status
                FROM camera_baseline_samples
                WHERE status = 'active'
                ORDER BY camera_name
            """
            )

            rows = cursor.fetchall()
            cameras = []

            for row in rows:
                camera_name = row[0]

                # Get latest health check status for this camera
                cursor.execute(
                    """
                    SELECT overall_status FROM camera_health_check_results
                    WHERE camera_name = ?
                    ORDER BY check_timestamp DESC
                    LIMIT 1
                """,
                    (camera_name,),
                )

                health_result = cursor.fetchone()
                overall_status = health_result[0] if health_result else None

                cameras.append(
                    {
                        "camera_name": camera_name,
                        "baseline_success_rate_pct": row[1],
                        "status": row[2],
                        "overall_status": overall_status,  # ✅ Latest health check status
                    }
                )

            return jsonify(cameras), 200

    except Exception as e:
        logger.error(f"Error getting cameras: {str(e)}")
        return jsonify({"error": f"Error getting cameras: {str(e)}"}), 500


@qr_detection_bp.route("/health-status-summary", methods=["GET"])
def get_health_status_summary():
    """
    Get summary of camera health status (for sidebar badge)

    Response:
    {
        "critical_count": 1,
        "caution_count": 0,
        "ok_count": 2,
        "no_baseline_count": 0
    }
    """
    try:
        from modules.db_utils.safe_connection import safe_db_connection

        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Get latest health check for each active camera
            cursor.execute(
                """
                SELECT DISTINCT camera_name FROM camera_baseline_samples
                WHERE status = 'active'
            """
            )

            cameras = [row[0] for row in cursor.fetchall()]

            status_count = {"CRITICAL": 0, "CAUTION": 0, "OK": 0, "NO_BASELINE": 0}

            for camera_name in cameras:
                # Get latest health check status
                cursor.execute(
                    """
                    SELECT overall_status FROM camera_health_check_results
                    WHERE camera_name = ?
                    ORDER BY check_timestamp DESC
                    LIMIT 1
                """,
                    (camera_name,),
                )

                result = cursor.fetchone()
                if result:
                    status = result[0]
                    if status in status_count:
                        status_count[status] += 1
                else:
                    status_count["NO_BASELINE"] += 1

            return (
                jsonify(
                    {
                        "critical_count": status_count["CRITICAL"],
                        "caution_count": status_count["CAUTION"],
                        "ok_count": status_count["OK"],
                        "no_baseline_count": status_count["NO_BASELINE"],
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Error getting health status summary: {str(e)}")
        return jsonify({"error": f"Error getting health status summary: {str(e)}"}), 500


@qr_detection_bp.route("/health", methods=["GET"])
def qr_health_check():
    """Health check endpoint for QR detection"""
    try:
        cleanup_expired_qr_cache()

        return (
            jsonify(
                {
                    "status": "healthy",
                    "service": "qr_detection",
                    "version": "2.0_preprocessing",
                    "endpoints": [
                        "POST /preprocess-video - Pre-process entire video at 5fps",
                        "GET /preprocess-status/<cache_key> - Check preprocessing progress",
                        "POST /get-cached-qr - Get QR detections from cache by timestamp",
                        "POST /get-cached-trigger - Get QR trigger detections (search for 'TimeGo')",
                        "GET /get-baseline-info/<cache_key> - Get cached baseline info",
                        "POST /detect-qr-image - Detect QR codes from uploaded image",
                        "GET /test - Test QR detection with sample video",
                        "GET /health - Health check",
                    ],
                    "cache_status": {
                        "active_cache_entries": len(qr_preprocessing_cache),
                        "active_processing_jobs": len(qr_preprocessing_progress),
                        "active_baseline_cache_entries": len(qr_baseline_cache),
                        "total_cached_detections": sum(
                            len(cache_data.get("detections", []))
                            for cache_data in qr_preprocessing_cache.values()
                        ),
                        "cache_ttl_minutes": 30,
                    },
                    "features": [
                        "5fps QR video preprocessing",
                        "Perfect timestamp synchronization",
                        "Dynamic QR bbox mapping to canvas",
                        "QR trigger detection for 'TimeGo' text",
                        "Trigger area ROI filtering",
                        "Automatic cache expiration",
                        "Background processing",
                        "WeChat QR model integration",
                        "Baseline capture during preprocessing",
                        "Baseline success rate calculation",
                    ],
                    "camera_roi_dir": CAMERA_ROI_DIR,
                    "camera_roi_dir_exists": os.path.exists(CAMERA_ROI_DIR),
                    "base_dir": BASE_DIR,
                    "backend_dir": BACKEND_DIR,
                    "script_path": os.path.join(
                        BACKEND_DIR, "modules", "technician", "qr_detector.py"
                    ),
                    "script_exists": os.path.exists(
                        os.path.join(BACKEND_DIR, "modules", "technician", "qr_detector.py")
                    ),
                    "description": "Advanced QR detection with preprocessing and caching for perfect video synchronization",
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


# ==================== HEALTH CHECK RESUME ENDPOINT ====================


@qr_detection_bp.route("/resume-processing", methods=["POST"])
def resume_processing():
    """
    Resume processing after operator fixed camera.

    When health check fails with CRITICAL status, processing is paused.
    Operator fixes the camera (clean lens, adjust position, etc.) and clicks
    "Fixed - Resume Processing" button, which calls this endpoint.

    Flow:
    1. Re-run health check immediately
    2. If overall_status = OK → Resume processing (reset health_check_failed flag)
    3. If overall_status = CRITICAL/CAUTION → Do NOT resume, return new status

    Request JSON:
        {
            "camera_name": "Cam1"
        }

    Response (Success):
        {
            "success": true,
            "message": "Health check passed! Processing resumed.",
            "overall_status": "OK",
            "videos_resumed": 3
        }

    Response (Failed):
        {
            "success": false,
            "message": "Health check still CRITICAL. Please fix and try again.",
            "overall_status": "CRITICAL"
        }
    """
    try:
        from modules.technician.camera_health_checker import run_health_check

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON body provided"}), 400

        camera_name = data.get("camera_name")
        if not camera_name:
            return jsonify({"success": False, "error": "camera_name required"}), 400

        logger.info(f"[HEALTH] User clicked 'Fixed - Resume Processing' for {camera_name}")

        # ✅ Step 1: Re-run health check immediately
        logger.info(f"[HEALTH] Re-checking camera health for {camera_name}")

        # Find latest video for this camera to re-check
        # Status is 'health_check_failed' when health check CRITICAL (not 'Error')
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT file_path FROM file_list
                WHERE camera_name = ? AND status = 'health_check_failed'
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (camera_name,),
            )
            result = cursor.fetchone()
            video_path = result[0] if result else None

        if not video_path:
            logger.warning(f"[HEALTH] No failed video found for {camera_name}")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "No video to re-check found",
                        "overall_status": "NO_DATA",
                    }
                ),
                400,
            )

        # Re-run health check
        health_result = run_health_check(camera_name, video_path)

        if not health_result.get("success"):
            logger.error(f"[HEALTH] Health check re-run failed for {camera_name}")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Health check re-run failed",
                        "error": health_result.get("error"),
                    }
                ),
                500,
            )

        new_status = health_result.get(
            "status"
        )  # Note: run_health_check returns 'status', not 'overall_status'
        logger.info(f"[HEALTH] Health check re-run result: {new_status}")

        # ✅ Step 2: Check result and decide whether to resume
        if new_status == "OK":
            # ✅ PASS - Resume processing
            # NOTE: run_health_check() already updated camera_health_check_results table
            # We only need to reset the failed videos in file_list here
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Reset failed videos for this camera (include both 'Error' and 'health_check_failed' statuses)
                # ✅ IMPORTANT: Set status = 'pending' (not 'Queued') to trigger full re-processing
                # 'pending' status tells framework to run IdleMonitor from beginning again
                cursor.execute(
                    """
                    UPDATE file_list
                    SET status = 'pending',
                        health_check_failed = 0,
                        health_check_message = NULL,
                        is_processed = 0
                    WHERE camera_name = ? AND status IN ('Error', 'health_check_failed')
                """,
                    (camera_name,),
                )

                updated_count = cursor.rowcount
                conn.commit()

            logger.info(
                f"[HEALTH] ✅ Health check PASSED! Reset {updated_count} videos for {camera_name}"
            )

            # Trigger FrameSampler to pick up videos again
            try:
                from modules.scheduler.db_sync import frame_sampler_event

                frame_sampler_event.set()
                logger.info(f"[HEALTH] Triggered FrameSampler to resume processing")
            except Exception as e:
                logger.warning(f"[HEALTH] Could not trigger FrameSampler: {e}")

            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Health check passed! Processing resumed.",
                        "overall_status": "OK",
                        "videos_resumed": updated_count,
                    }
                ),
                200,
            )

        else:
            # ❌ FAIL - Do NOT resume, keep CRITICAL status
            logger.error(
                f"[HEALTH] Health check FAILED! Status is still {new_status} for {camera_name}"
            )

            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Health check still {new_status}. Please fix and try again.",
                        "overall_status": new_status,
                    }
                ),
                200,
            )  # Return 200 because it's not an error, just a failed check

    except Exception as e:
        logger.error(f"[HEALTH] Error in resume_processing: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
