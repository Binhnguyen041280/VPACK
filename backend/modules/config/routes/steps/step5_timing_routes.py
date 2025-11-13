"""
Step 5 Timing/Storage Configuration Routes for V.PACK.

REST wrapper endpoints for existing timing and storage configuration logic.
Integrates with existing processing_config table and save_config validation.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from ...services.step5_timing_service import step5_timing_service
from ...shared import (
    format_step_response,
    handle_database_error,
    handle_validation_error,
    handle_general_error,
    create_success_response,
    create_error_response,
    validate_request_data,
    log_step_operation,
)


# Create blueprint for Step 5 routes
step5_bp = Blueprint("step5_timing", __name__, url_prefix="/step")


@step5_bp.route("/timing", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_step_timing():
    """
    Get current timing and storage configuration from processing_config table.

    Returns:
        JSON response with current timing configuration
    """
    try:
        log_step_operation("5", "GET timing request")

        # Get configuration from service
        config = step5_timing_service.get_timing_config()

        if "error" in config:
            # Service returned error but with fallback data
            response_data = {k: v for k, v in config.items() if k != "error"}
            response = create_success_response(
                response_data, "Configuration retrieved with fallback"
            )
            response["warning"] = config["error"]
        else:
            response = create_success_response(
                config, "Timing configuration retrieved successfully"
            )

        log_step_operation(
            "5",
            "GET timing success",
            {
                "min_packing_time": config.get("min_packing_time"),
                "max_packing_time": config.get("max_packing_time"),
                "frame_rate": config.get("frame_rate"),
            },
        )

        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get timing", "step5")
        return jsonify(error_response), status_code


@step5_bp.route("/timing", methods=["PUT"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def update_step_timing():
    """
    Update timing and storage configuration using existing processing_config logic.

    Request Body:
        {
            "min_packing_time": "integer" (optional),
            "max_packing_time": "integer" (optional),
            "video_buffer": "integer" (optional),
            "storage_duration": "integer" (optional),
            "frame_rate": "integer" (optional),
            "frame_interval": "integer" (optional),
            "output_path": "string" (optional)
        }

    Returns:
        JSON response with update result
    """
    try:
        log_step_operation("5", "PUT timing request")

        # Validate request data (no required fields - all optional)
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=[])
        if not is_valid:
            error_response = create_error_response(error_msg, "step5")
            return jsonify(error_response), 400

        if not data:
            error_response = create_error_response(
                "At least one timing field must be provided", "step5"
            )
            return jsonify(error_response), 400

        # Log request details
        print(f"=== STEP 5 TIMING CONFIG UPDATE ===")
        for field in [
            "min_packing_time",
            "max_packing_time",
            "video_buffer",
            "storage_duration",
            "frame_rate",
            "frame_interval",
            "output_path",
        ]:
            if field in data:
                print(f"{field}: {data[field]}")

        # Update configuration via service
        success, result = step5_timing_service.update_timing_config(data)

        if not success:
            # Service returned validation or database error
            if "error" in result:
                error_response = create_error_response(result["error"], "step5")
                return jsonify(error_response), 400

        # Format successful response
        response_data = {
            "min_packing_time": result["min_packing_time"],
            "max_packing_time": result["max_packing_time"],
            "video_buffer": result["video_buffer"],
            "storage_duration": result["storage_duration"],
            "frame_rate": result["frame_rate"],
            "frame_interval": result["frame_interval"],
            "output_path": result["output_path"],
            "changed": result["changed"],
        }

        response = create_success_response(
            response_data,
            result.get("message", "Timing configuration updated successfully"),
            changed=result["changed"],
        )

        log_step_operation(
            "5",
            "PUT timing success",
            {
                "changed": result["changed"],
                "min_packing_time": result["min_packing_time"],
                "max_packing_time": result["max_packing_time"],
            },
        )

        # ✅ Trigger async sync for active cloud sources (non-blocking)
        # Response will be returned immediately while sync runs in background
        try:
            from modules.db_utils.safe_connection import safe_db_connection
            from modules.sources.pydrive_downloader import pydrive_downloader
            import logging
            import threading

            logger = logging.getLogger(__name__)

            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, name FROM video_sources
                    WHERE active = 1 AND source_type = 'cloud'
                """
                )
                sources = cursor.fetchall()

            if sources:

                def trigger_async_sync():
                    """Background sync worker - runs after response is sent"""
                    import time

                    time.sleep(0.1)  # Brief delay to ensure response is sent

                    logger.info(
                        "🚀 Step 5 completed - triggering background sync for cloud sources..."
                    )
                    for source_id, source_name in sources:
                        try:
                            logger.info(f"📥 Background syncing {source_name} (ID: {source_id})...")
                            sync_result = pydrive_downloader.force_sync_now(source_id)
                            if sync_result.get("success"):
                                logger.info(f"✅ Background sync completed for {source_name}")
                            else:
                                logger.warning(
                                    f"⚠️ Background sync failed for {source_name}: {sync_result.get('message')}"
                                )
                        except Exception as e:
                            logger.error(f"❌ Error in background sync for {source_name}: {e}")

                # Start background thread (daemon=True ensures it won't block app shutdown)
                sync_thread = threading.Thread(target=trigger_async_sync, daemon=True)
                sync_thread.start()

                logger.info(
                    f"✅ Step 5 completed - sync scheduled for {len(sources)} cloud source(s) in background"
                )
                response["data"]["cloud_sync_triggered"] = True
                response["data"]["cloud_sync_mode"] = "async_background"
                response["data"]["cloud_sources_count"] = len(sources)
        except Exception as sync_error:
            logger.error(f"❌ Error triggering cloud sync: {sync_error}")
            response["data"]["cloud_sync_triggered"] = False

        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "update timing", "step5")
        return jsonify(error_response), status_code


@step5_bp.route("/timing/validate", methods=["POST"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def validate_step_timing():
    """
    Validate timing configuration without saving.
    Useful for real-time validation in frontend forms.

    Request Body:
        {
            "min_packing_time": "integer" (optional),
            "max_packing_time": "integer" (optional),
            "video_buffer": "integer" (optional),
            "storage_duration": "integer" (optional),
            "frame_rate": "integer" (optional),
            "frame_interval": "integer" (optional),
            "output_path": "string" (optional)
        }

    Returns:
        JSON response with detailed validation result
    """
    try:
        log_step_operation("5", "POST timing validate request")

        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=[])
        if not is_valid:
            error_response = create_error_response(error_msg, "step5")
            return jsonify(error_response), 400

        if not data:
            error_response = create_error_response(
                "At least one field must be provided for validation", "step5"
            )
            return jsonify(error_response), 400

        # Validate via service
        is_valid, validation_message, validation_details = (
            step5_timing_service.validate_timing_settings(data)
        )

        if is_valid:
            response = {
                "success": True,
                "valid": True,
                "message": "Timing configuration is valid",
                "data": data,
                "validation_details": validation_details,
            }
            status_code = 200
        else:
            response = {
                "success": True,
                "valid": False,
                "error": validation_message,
                "data": data,
                "validation_details": validation_details,
            }
            status_code = 200  # 200 for validation endpoint, even with invalid data

        log_step_operation("5", "POST timing validate", {"valid": is_valid})
        return jsonify(response), status_code

    except Exception as e:
        error_response, status_code = handle_general_error(e, "validate timing", "step5")
        return jsonify(error_response), status_code


@step5_bp.route("/timing/statistics", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_step_timing_statistics():
    """
    Get timing configuration statistics and performance metrics.
    Useful for monitoring and debugging.

    Returns:
        JSON response with timing statistics
    """
    try:
        log_step_operation("5", "GET timing statistics request")

        # Get statistics from service
        stats = step5_timing_service.get_timing_statistics()

        if "error" in stats:
            error_response = create_error_response(stats["error"], "step5")
            return jsonify(error_response), 500

        response = create_success_response(stats, "Statistics retrieved successfully")

        log_step_operation("5", "GET timing statistics success")
        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get timing statistics", "step5")
        return jsonify(error_response), status_code


@step5_bp.route("/timing/defaults", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_step_timing_defaults():
    """
    Get default values for timing configuration.
    Useful for resetting forms or showing initial values.

    Returns:
        JSON response with default timing values
    """
    try:
        log_step_operation("5", "GET timing defaults request")

        defaults = {
            "min_packing_time": step5_timing_service.DEFAULT_MIN_PACKING_TIME,
            "max_packing_time": step5_timing_service.DEFAULT_MAX_PACKING_TIME,
            "video_buffer": step5_timing_service.DEFAULT_VIDEO_BUFFER,
            "storage_duration": step5_timing_service.DEFAULT_STORAGE_DURATION,
            "frame_rate": step5_timing_service.DEFAULT_FRAME_RATE,
            "frame_interval": step5_timing_service.DEFAULT_FRAME_INTERVAL,
            "output_path": step5_timing_service.DEFAULT_OUTPUT_PATH,
        }

        response = create_success_response(defaults, "Default values retrieved successfully")

        log_step_operation("5", "GET timing defaults success")
        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get timing defaults", "step5")
        return jsonify(error_response), status_code


@step5_bp.route("/timing/performance-estimate", methods=["POST"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_step_timing_performance_estimate():
    """
    Calculate performance estimates based on timing configuration.
    Useful for helping users understand the impact of their settings.

    Request Body:
        {
            "frame_rate": "integer" (required),
            "frame_interval": "integer" (required),
            "video_duration_hours": "integer" (optional, default: 24)
        }

    Returns:
        JSON response with performance estimates
    """
    try:
        log_step_operation("5", "POST timing performance-estimate request")

        # Validate request data
        data = request.json
        required_fields = ["frame_rate", "frame_interval"]
        is_valid, error_msg = validate_request_data(data, required_fields)
        if not is_valid:
            error_response = create_error_response(error_msg, "step5")
            return jsonify(error_response), 400

        frame_rate = data["frame_rate"]
        frame_interval = data["frame_interval"]
        video_duration_hours = data.get("video_duration_hours", 24)

        # Calculate performance estimates
        frames_per_second_processed = frame_rate / max(1, frame_interval)
        total_frames_per_hour = frame_rate * 3600  # 3600 seconds in an hour
        processed_frames_per_hour = frames_per_second_processed * 3600

        processing_load_percentage = (processed_frames_per_hour / total_frames_per_hour) * 100

        estimates = {
            "frame_processing": {
                "frames_per_second_original": frame_rate,
                "frames_per_second_processed": round(frames_per_second_processed, 2),
                "processing_load_percentage": round(processing_load_percentage, 2),
                "frames_skipped_percentage": round(100 - processing_load_percentage, 2),
            },
            "daily_estimates": {
                "total_frames_24h": total_frames_per_hour * video_duration_hours,
                "processed_frames_24h": int(processed_frames_per_hour * video_duration_hours),
                "estimated_storage_reduction": f"{round(100 - processing_load_percentage, 1)}%",
            },
            "performance_category": (
                "high_performance"
                if processing_load_percentage < 25
                else "balanced" if processing_load_percentage < 50 else "high_accuracy"
            ),
            "recommendations": [],
        }

        # Add recommendations based on performance
        if processing_load_percentage > 75:
            estimates["recommendations"].append(
                "Consider increasing frame_interval to reduce processing load"
            )
        if processing_load_percentage < 10:
            estimates["recommendations"].append(
                "Consider decreasing frame_interval for better detection accuracy"
            )
        if frame_interval > frame_rate:
            estimates["recommendations"].append("Frame interval should not exceed frame rate")

        response = create_success_response(
            estimates, "Performance estimates calculated successfully"
        )

        log_step_operation(
            "5",
            "POST timing performance-estimate success",
            {"processing_load": round(processing_load_percentage, 2)},
        )

        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(
            e, "calculate performance estimates", "step5"
        )
        return jsonify(error_response), status_code
