"""Cleanup API endpoints for V_Track application

Provides REST APIs for:
- Manual system cleanup trigger
- Manual output cleanup trigger
- Output file deletion
"""

from flask import Blueprint, jsonify, request
from modules.utils.cleanup import cleanup_service
from modules.config.logging_config import get_logger

cleanup_bp = Blueprint("cleanup", __name__)
logger = get_logger(__name__)


@cleanup_bp.route("/cleanup/system/trigger", methods=["POST"])
def trigger_system_cleanup():
    """
    Manually trigger system cleanup (normally runs every 1 hour).

    Cleans:
    - var/logs/application/ (keep 1 day + *_latest.log)
    - var/cache/cloud_downloads/ (keep 1 day)
    - resources/output_clips/LOG/ (delete all)

    Returns:
        JSON response with cleanup statistics
    """
    try:
        result = cleanup_service.cleanup_system_files()
        logger.info(f"Manual system cleanup triggered: {result['total_deleted']} files deleted")
        return (
            jsonify({"success": True, "message": "System cleanup completed", "result": result}),
            200,
        )
    except Exception as e:
        logger.error(f"System cleanup failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cleanup_bp.route("/cleanup/output/trigger", methods=["POST"])
def trigger_output_cleanup():
    """
    Manually trigger output files cleanup (normally runs every 24 hours).

    Cleans output files based on storage_duration config.
    Excludes: CameraROI/, LOG/ directories

    Returns:
        JSON response with cleanup statistics
    """
    try:
        result = cleanup_service.cleanup_output_files()
        if result.get("error"):
            logger.warning(f"Output cleanup partial error: {result['error']}")
            return (
                jsonify(
                    {"success": False, "message": "Output cleanup with errors", "result": result}
                ),
                400,
            )

        logger.info(f"Manual output cleanup triggered: {result['deleted']} files deleted")
        return (
            jsonify({"success": True, "message": "Output cleanup completed", "result": result}),
            200,
        )
    except Exception as e:
        logger.error(f"Output cleanup failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cleanup_bp.route("/cleanup/output/file", methods=["DELETE"])
def delete_output_file():
    """
    Delete a specific output file by path.

    Request body:
        {
            "file_path": "/path/to/file"
        }

    Returns:
        JSON response indicating success/failure
    """
    try:
        data = request.get_json()
        if not data or "file_path" not in data:
            return jsonify({"success": False, "error": "file_path required in request body"}), 400

        file_path = data["file_path"]

        # Security: Validate path is within safe directory
        from pathlib import Path

        file = Path(file_path).resolve()

        # Basic safety check - ensure it's not trying to escape
        if ".." in str(file):
            return jsonify({"success": False, "error": "Invalid path"}), 400

        if file.exists() and file.is_file():
            try:
                file_size = file.stat().st_size / (1024 * 1024)
                file.unlink()
                logger.info(f"Deleted file: {file_path} ({file_size:.2f} MB)")
                return (
                    jsonify({"success": True, "message": f"File deleted ({file_size:.2f} MB)"}),
                    200,
                )
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
                return jsonify({"success": False, "error": f"Failed to delete: {str(e)}"}), 500
        else:
            return jsonify({"success": False, "error": "File not found"}), 404

    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cleanup_bp.route("/cleanup/stats", methods=["GET"])
def get_cleanup_stats():
    """
    Get cleanup statistics and configuration.

    Returns:
        JSON with system cleanup info and output config
    """
    try:
        from modules.db_utils.safe_connection import safe_db_connection

        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT output_path, storage_duration
                FROM processing_config
                WHERE id = 1
            """
            )
            result = cursor.fetchone()

        if result:
            output_path, storage_duration = result
            return (
                jsonify(
                    {
                        "success": True,
                        "cleanup_config": {
                            "system_cleanup_interval": "1 hour",
                            "system_log_retention": "1 day",
                            "system_cache_retention": "1 day",
                            "output_cleanup_interval": "24 hours",
                            "output_retention_days": storage_duration or 30,
                            "output_path": output_path,
                        },
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "No cleanup config found"}), 404

    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
