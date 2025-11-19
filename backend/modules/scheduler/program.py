"""Scheduler Program API Module for V_Track Video Processing System.

This module provides Flask REST API endpoints for controlling video processing programs.
It manages different processing modes (First Run, Default, Custom) and coordinates with
the BatchScheduler for automated video processing.

API Endpoints:
    POST /program: Execute different processing programs (First/Default/Custom)
    GET /program: Get current program execution status
    POST /confirm-run: Confirm and execute a processing program
    GET /program-progress: Get real-time processing progress
    GET /check-first-run: Check if first run has been completed
    GET /get-cameras: Get configured camera list
    GET /get-camera-folders: Get available camera folders

Processing Modes:
    - First Run: Initial processing for specified number of days
    - Default: Continuous processing mode with periodic scanning
    - Custom: Process specific file or directory path

Global State:
    running_state: Dictionary tracking current execution state including:
        - current_running: Currently active processing mode
        - days: Number of days for first run processing
        - custom_path: File/directory path for custom processing
        - files: List of files being processed

Thread Safety:
    Uses RWLocks (db_rwlock) for thread-safe database access and coordinates
    with BatchScheduler for safe concurrent operations.
"""

from flask import Blueprint, request, jsonify
import os
import json
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional
from modules.db_utils import find_project_root
from modules.db_utils.safe_connection import safe_db_connection
from modules.config.logging_config import get_logger
from modules.utils.simple_timezone import get_system_timezone_from_db
from modules.path_utils import get_paths, get_logs_dir
from modules.license.license_manager import LicenseManager
from .file_lister import run_file_scan, get_db_path
from .batch_scheduler import BatchScheduler
from .db_sync import frame_sampler_event, event_detector_event

program_bp = Blueprint('program', __name__)

# Use centralized path configuration
paths = get_paths()
DB_PATH = paths["DB_PATH"]
LOG_DIR = get_logs_dir()

logger = get_logger(__name__, {"module": "program_api"})
logger.info("Program logging initialized")

db_rwlock = threading.RLock()
running_state = {
    "days": None,
    "custom_path": None,
    "current_running": None,
    "files": []
}

scheduler = BatchScheduler()

def _get_log_tz():
    """Get system timezone for logging."""
    return ZoneInfo(get_system_timezone_from_db())

def init_default_program():
    """Initialize the default program based on first run status.

    Checks if the first run has been completed and automatically starts
    the default mode if appropriate. This ensures the system continues
    processing after initial setup.

    Uses timezone-aware logging for better debugging across different timezones.
    """
    start_time = datetime.now(_get_log_tz())
    logger.info(f"Initializing default program at {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    try:
        with db_rwlock:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM program_status WHERE key = "first_run_completed"')
                result = cursor.fetchone()
                first_run_completed = result[0] == 'true' if result else False
        
        logger.info(f"First run completed: {first_run_completed}, Scheduler running: {scheduler.running}")

        if first_run_completed and not scheduler.running:
            logger.info(f"Chuyển sang chế độ chạy mặc định (quét lặp) at {datetime.now(_get_log_tz()).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            running_state["current_running"] = "Default"
            scheduler.start()
            
    except Exception as e:
        logger.error(f"Error initializing default program: {e}")

init_default_program()

def _check_default_mode_license() -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if current license allows Default Mode (auto-scan 24/7).

    Returns:
        tuple: (is_allowed, error_response_dict)
               - is_allowed: True if Pro license, False if Starter/Trial
               - error_response_dict: Error response to return if not allowed, None if allowed
    """
    try:
        license_manager = LicenseManager()
        license_status = license_manager.get_license_status()

        # If no license or invalid → Block Default Mode
        if license_status.get('status') != 'valid':
            return False, {
                'success': False,
                'error': 'Default Mode requires active license',
                'message': 'Please activate a license (Starter 29k or Pro 249k) to use Default Mode',
                'current_plan': 'No License',
                'upgrade_url': '/plan'
            }

        license_data = license_status.get('license', {})
        product_type = license_data.get('product_type', '')

        # If Starter license → Block Default Mode
        if 'starter' in product_type.lower():
            return False, {
                'success': False,
                'error': 'Default Mode requires PRO license',
                'message': 'Default Mode (auto-scan 24/7) is only available for PRO license (249k/month). Your current plan: Starter (29k/month) - Custom Mode only.',
                'current_plan': 'Starter (29k/month)',
                'required_plan': 'Pro (249k/month)',
                'upgrade_url': '/plan'
            }

        # If Pro or other paid license → Allow
        logger.info(f"Default Mode allowed for license: {product_type}")
        return True, None

    except Exception as e:
        logger.error(f"Error checking Default Mode license: {e}")
        # On error, allow (fail-open for better UX)
        return True, None

@program_bp.route('/program', methods=['POST'])
def program():
    """Execute different video processing programs based on the request.
    
    This endpoint handles three types of processing programs:
    1. First Run: Initial processing for a specified number of days
    2. Default: Continuous processing mode
    3. Custom: Process a specific file or directory
    
    Request Body:
        card (str): Program type - 'First Run', 'Default', or 'Custom'
        action (str): Action to perform - 'run' or 'stop'
        custom_path (str, optional): File/directory path for custom processing
        days (int, optional): Number of days for first run processing
    
    Returns:
        JSON response with current program state and HTTP status code
        
    Processing Logic:
        - First Run: Validates days parameter, runs initial scan, transitions to default
        - Custom: Validates path exists, processes single file/directory, returns to default
        - Default: Starts continuous processing with BatchScheduler
        - Stop: Stops current processing and returns to default mode
        
    Thread Safety:
        Uses db_rwlock for thread-safe database operations and coordinates
        with BatchScheduler for safe concurrent processing.
    
    Error Handling:
        Returns appropriate HTTP error codes (400, 404, 500) with error messages
        for various failure scenarios (missing parameters, invalid paths, etc.)
    """
    logger.info(f"POST /program called, Current state before action: scheduler_running={scheduler.running}, running_state={running_state}")

    # Extract and validate request parameters
    data = request.get_json()
    if data is None:
        logger.error("No JSON data provided in request")
        return jsonify({"error": "No JSON data provided in request"}), 400

    # DEBUG: Log full request body
    logger.info(f"DEBUG: Request body received: {data}")

    card = data.get('card')    # Processing program type
    action = data.get('action')  # Action to perform ('run' or 'stop')
    custom_path = data.get('custom_path', '')  # Path for custom processing
    days = data.get('days')    # Number of days for first run
    camera_name = data.get('camera_name')  # Camera name for custom processing

    # DEBUG: Log extracted values
    logger.info(f"DEBUG: Extracted - card={card}, action={action}, custom_path={custom_path}, days={days}, camera_name={camera_name}")

    # Validate required parameters
    if not card or not action:
        logger.error("Missing required parameters: card and action")
        return jsonify({"error": "Missing required parameters: card and action"}), 400

    # Validate First Run execution - prevent duplicate runs
    if card == "First Run" and action == "run":
        try:
            # Check if first run has already been completed to prevent duplicates
            with db_rwlock:
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT value FROM program_status WHERE key = "first_run_completed"')
                    result = cursor.fetchone()
                    first_run_completed = result[0] == 'true' if result else False
            if first_run_completed:
                logger.warning("First run already completed")
                return jsonify({"error": "First Run already completed, cannot run again"}), 400
        except Exception as e:
            logger.error(f"Failed to check first run status: {str(e)}")
            return jsonify({"error": f"Failed to check first run status: {str(e)}"}), 500

    # Handle RUN action for different program types
    if action == "run":
        logger.info(f"Action run for card: {card}, scheduler_running={scheduler.running}")
        
        # Pause scheduler if switching to custom processing mode
        if scheduler.running and card == "Custom":
            scheduler.pause()  # Pause ongoing batch processing
            running_state["current_running"] = None
            running_state["files"] = []
        # FIRST RUN PROCESSING: Initial scan for specified number of days
        if card == "First Run":
            if not days:
                logger.error("Days required for First Run")
                return jsonify({"error": "Days required for First Run"}), 400
            
            # Update state for first run processing with timezone context
            running_state["days"] = days
            running_state["custom_path"] = None

            start_time = datetime.now(_get_log_tz())
            logger.info(f"Starting first run processing for {days} days at {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

            try:
                # Scan and queue files from the specified number of days
                run_file_scan(scan_action="first", days=days)

                completion_time = datetime.now(_get_log_tz())
                logger.info(f"First run scan completed at {completion_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

            except Exception as e:
                error_time = datetime.now(_get_log_tz())
                logger.error(f"Failed to run first scan at {error_time.strftime('%Y-%m-%d %H:%M:%S %Z')}: {str(e)}")
                return jsonify({"error": f"Failed to run first scan: {str(e)}"}), 500
        # CUSTOM PROCESSING: Process specific file or directory
        elif card == "Custom":
            logger.info(f"DEBUG: Entering Custom processing branch with card='{card}', custom_path='{custom_path}'")
            if not custom_path:
                logger.error("Custom path required for Custom")
                return jsonify({"error": "Custom path required for Custom"}), 400
            
            # Validate custom path exists
            abs_path = os.path.abspath(custom_path)
            if not os.path.exists(abs_path):
                logger.error(f"Custom path {abs_path} does not exist")
                return jsonify({"error": f"Custom path {abs_path} does not exist"}), 400
            try:
                # Check if file has already been processed to avoid duplicates
                with db_rwlock:
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT status, is_processed FROM file_list WHERE file_path = ? AND (status = 'xong' OR is_processed = 1)", (abs_path,))
                        result = cursor.fetchone()
                    if result:
                        logger.warning(f"File {abs_path} already processed with status {result[0]}")
                        return jsonify({"error": "File has already been processed"}), 400
            except Exception as e:
                logger.error(f"Error checking file status: {str(e)}")
                return jsonify({"error": f"Error checking file status: {str(e)}"}), 500
            running_state["custom_path"] = abs_path
            running_state["camera_name"] = camera_name
            running_state["days"] = None
            try:
                scheduler.pause()
                run_file_scan(scan_action="custom", custom_path=abs_path, camera_name=camera_name)
                with db_rwlock:
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT file_path FROM file_list WHERE custom_path = ? ORDER BY created_at DESC LIMIT 1", (abs_path,))
                        result = cursor.fetchone()
                if result:
                    from .program_runner import start_frame_sampler_thread, start_event_detector_thread
                    frame_sampler_event.set()
                    start_frame_sampler_thread()
                    start_event_detector_thread()
                    logger.info(f"[Custom] Processing started: {result[0]}")
                    import time
                    while True:
                        with db_rwlock:
                            with safe_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT status FROM file_list WHERE file_path = ?", (result[0],))
                                status_result = cursor.fetchone()
                        if status_result and status_result[0] == 'Done':
                            break
                        time.sleep(2)
                    logger.info(f"[Custom] Processing completed: {result[0]}")

                    # Show "Completed" status briefly before transitioning to default
                    running_state["current_running"] = "Completed"
                    running_state["custom_path"] = None
                    running_state["days"] = None

                    # Wait a moment to show completed status
                    import time
                    time.sleep(3)  # Show "Completed" for 3 seconds

                    # Then transition to default mode
                    running_state["current_running"] = "Default"

                    scheduler.resume()
                    try:
                        if not scheduler.running:
                            scheduler.start()
                            logger.info("Restarted scheduler for default mode")
                        run_file_scan(scan_action="default")
                        frame_sampler_event.set()
                        event_detector_event.set()
                        logger.info(f"Completed Custom, transitioning to default: scheduler_running={scheduler.running}, running_state={running_state}")
                    except Exception as e:
                        logger.error(f"Error triggering default scan: {str(e)}")
                else:
                    logger.error(f"[Custom] No pending file found at: {abs_path}")
                    return jsonify({"error": "No pending file found for processing"}), 404
            except Exception as e:
                logger.error(f"[Custom] Error: {str(e)}")
                scheduler.resume()
                return jsonify({"error": f"Custom processing failed: {str(e)}"}), 500
        # DEFAULT MODE PROCESSING: Continuous auto-scan every 2 minutes
        elif card == "Default":
            # CHECK LICENSE FOR DEFAULT MODE (Pro license required, Starter only allows Custom)
            is_allowed, error_response = _check_default_mode_license()
            if not is_allowed:
                logger.warning(f"Default Mode blocked: {error_response.get('message')}")
                return jsonify(error_response), 403

            running_state["days"] = None
            running_state["custom_path"] = None
            logger.info("Default Mode license check passed, proceeding with auto-scan")

        # Only update running_state for non-Custom programs
        # Custom program handles its own state transitions (Completed -> Default)
        if card != "Custom":
            running_state["current_running"] = card
            if not scheduler.running:
                running_state["current_running"] = "Default"
                scheduler.start()

        if card == "First Run":
            try:
                completion_time = datetime.now(_get_log_tz())
                completion_utc = datetime.now(timezone.utc)

                with db_rwlock:
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE program_status SET value = ? WHERE key = ?", ("true", "first_run_completed"))

                logger.info(
                    f"Transitioning to default mode (continuous scan) after First Run completion at "
                    f"{completion_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )

            except Exception as e:
                error_time = datetime.now(_get_log_tz())
                logger.error(f"Error updating first_run_completed at {error_time.strftime('%Y-%m-%d %H:%M:%S %Z')}: {e}")

    elif action == "stop":
        logger.info(f"Action stop called, current_state={running_state}, scheduler_running={scheduler.running}")
        running_state["current_running"] = None
        running_state["days"] = None
        running_state["custom_path"] = None
        running_state["files"] = []
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler restarted for default mode")
        logger.info(f"State after stop: running_state={running_state}, scheduler_running={scheduler.running}")

    logger.info(f"Program action completed: {card} {action}, final_state={running_state}, scheduler_running={scheduler.running}")
    return jsonify({
        "current_running": running_state["current_running"],
        "days": running_state.get("days"),
        "custom_path": running_state.get("custom_path")
    }), 200

@program_bp.route('/program', methods=['GET'])
def get_program_status():
    """Get current program execution status.
    
    Returns:
        JSON object containing:
        - current_running: Currently active processing mode
        - days: Number of days for first run (if applicable)
        - custom_path: File/directory path for custom processing (if applicable)
    """
    logger.info("GET /program called")
    return jsonify({
        "current_running": running_state["current_running"],
        "days": running_state.get("days"),
        "custom_path": running_state.get("custom_path")
    }), 200

@program_bp.route('/confirm-run', methods=['POST'])
def confirm_run():
    """Confirm and execute a processing program.
    
    This endpoint triggers file scanning for the specified program type.
    Used after program setup to actually start processing.
    
    Request Body:
        card (str): Program type to confirm
    
    Returns:
        JSON object with program_type that was executed
    """
    logger.info("POST /confirm-run called")
    data = request.get_json()
    if data is None:
        logger.error("No JSON data provided in request")
        return jsonify({"error": "No JSON data provided in request"}), 400
    
    card = data.get('card')
    if not card:
        logger.error("Missing required parameter: card")
        return jsonify({"error": "Missing required parameter: card"}), 400

    scan_action = "first" if card == "First Run" else "default" if card == "Default" else "custom"
    days = running_state.get("days") if card == "First Run" else None
    custom_path = running_state.get("custom_path", '')
    try:
        run_file_scan(scan_action=scan_action, days=days, custom_path=custom_path)
        logger.info(f"Files queued for {scan_action}")
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        return jsonify({"error": f"Failed to list files: {str(e)}"}), 500

    return jsonify({
        "program_type": scan_action
    }), 200

@program_bp.route('/program-progress', methods=['GET'])
def get_program_progress():
    """Get real-time processing progress for all active files.
    
    Returns:
        JSON object containing:
        - files: List of files with their current processing status
          Each file object includes file_path and current status
    
    Used by frontend to display live progress updates during processing.
    """
    logger.info("GET /program-progress called")
    try:
        with db_rwlock:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT file_path, status FROM file_list WHERE is_processed = 0 ORDER BY created_at DESC")
                files_status = [{"file": row[0], "status": row[1]} for row in cursor.fetchall()]
        logger.info(f"Retrieved {len(files_status)} files for status")
        return jsonify({"files": files_status}), 200
    except Exception as e:
        logger.error(f"Failed to retrieve program progress: {str(e)}")
        return jsonify({"error": f"Failed to retrieve program progress: {str(e)}"}), 500

@program_bp.route('/check-first-run', methods=['GET'])
def check_first_run():
    """Check if the first run has been completed.
    
    Returns:
        JSON object containing:
        - first_run_completed: Boolean indicating if first run is done
    
    Used by frontend to determine if first run option should be available.
    """
    logger.info("GET /check-first-run called")
    try:
        with db_rwlock:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM program_status WHERE key = "first_run_completed"')
                result = cursor.fetchone()
            first_run_completed = result[0] == 'true' if result else False
        logger.info(f"First run completed: {first_run_completed}")
        return jsonify({"first_run_completed": first_run_completed}), 200
    except Exception as e:
        logger.error(f"Failed to check first run status: {str(e)}")
        return jsonify({"error": f"Failed to check first run status: {str(e)}"}), 500

@program_bp.route('/get-cameras', methods=['GET'])
def get_cameras():
    """Get list of configured cameras for processing.
    
    Returns:
        JSON object containing:
        - cameras: List of camera names/IDs from processing configuration
    
    Used by frontend to display available cameras for selection.
    """
    logger.info("GET /get-cameras called")
    try:
        with db_rwlock:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT selected_cameras FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
            cameras = result[0] if result else "[]"
            cameras_list = json.loads(cameras) if cameras else []
        logger.info(f"Retrieved {len(cameras_list)} cameras")
        return jsonify({"cameras": cameras_list}), 200
    except Exception as e:
        logger.error(f"Failed to retrieve cameras: {str(e)}")
        return jsonify({"error": f"Failed to retrieve cameras: {str(e)}"}), 500

@program_bp.route('/get-camera-folders', methods=['GET'])
def get_camera_folders():
    """Get list of available camera folders from the input directory.
    
    Returns:
        JSON object containing:
        - folders: List of folder objects with name and path properties
    
    Scans the configured input_path directory for subdirectories that
    represent different camera sources.
    """
    logger.info("GET /get-camera-folders called")
    try:
        with db_rwlock:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                video_root = result[0] if result else os.path.join(BASE_DIR, "Inputvideo")

        if not os.path.exists(video_root):
            logger.error(f"Directory {video_root} does not exist")
            return jsonify({"error": f"Directory {video_root} does not exist. Ensure the path is correct or create the directory."}), 400

        folders = []
        for folder_name in os.listdir(video_root):
            folder_path = os.path.join(video_root, folder_name)
            if os.path.isdir(folder_path):
                folders.append({"name": folder_name, "path": folder_path})
        logger.info(f"Retrieved {len(folders)} camera folders")
        return jsonify({"folders": folders}), 200
    except Exception as e:
        logger.error(f"Failed to retrieve camera folders: {str(e)}")
        return jsonify({"error": f"Failed to retrieve camera folders: {str(e)}"}), 500

if __name__ == "__main__":
    logger.info("Main program started")
    if not scheduler.running:
        running_state["current_running"] = "Default"
        scheduler.start()