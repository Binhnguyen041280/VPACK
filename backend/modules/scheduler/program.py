from flask import Blueprint, request, jsonify
import os
import json
import threading
import pytz
from datetime import datetime, timedelta
import logging
from modules.db_utils import find_project_root, get_db_connection
from .file_lister import run_file_scan, get_db_path
from .batch_scheduler import BatchScheduler
from .db_sync import frame_sampler_event, event_detector_event
import logging

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

program_bp = Blueprint('program', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "events.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DB_PATH = get_db_path()
LOG_DIR = os.path.join(BASE_DIR, "../../resources/output_clips/LOG")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("app")
logger.info("Program logging initialized")

db_rwlock = threading.RLock()
running_state = {
    "days": None,
    "custom_path": None,
    "current_running": None,
    "files": []
}

scheduler = BatchScheduler()

def init_default_program():
    logger.info("Initializing default program")
    try:
        with db_rwlock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM program_status WHERE key = "first_run_completed"')
            result = cursor.fetchone()
            conn.close()
        first_run_completed = result[0] == 'true' if result else False
        logger.info(f"First run completed: {first_run_completed}, Scheduler running: {scheduler.running}")
        if first_run_completed and not scheduler.running:
            logger.info("Chuyển sang chế độ chạy mặc định (quét lặp)")
            running_state["current_running"] = "Mặc định"
            scheduler.start()
    except Exception as e:
        logger.error(f"Error initializing default program: {e}")

init_default_program()

@program_bp.route('/program', methods=['POST'])
def program():
    logger.info(f"POST /program called, Current state before action: scheduler_running={scheduler.running}, running_state={running_state}")
    data = request.json
    card = data.get('card')
    action = data.get('action')
    custom_path = data.get('custom_path', '')
    days = data.get('days')

    if card == "Lần đầu" and action == "run":
        try:
            with db_rwlock:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM program_status WHERE key = "first_run_completed"')
                result = cursor.fetchone()
                first_run_completed = result[0] == 'true' if result else False
                conn.close()
            if first_run_completed:
                logger.warning("First run already completed")
                return jsonify({"error": "Lần đầu đã chạy trước đó, không thể chạy lại"}), 400
        except Exception as e:
            logger.error(f"Failed to check first run status: {str(e)}")
            return jsonify({"error": f"Failed to check first run status: {str(e)}"}), 500

    if action == "run":
        logger.info(f"Action run for card: {card}, scheduler_running={scheduler.running}")
        if scheduler.running and card == "Chỉ định":
            scheduler.pause()
            running_state["current_running"] = None
            running_state["files"] = []
        if card == "Lần đầu":
            if not days:
                logger.error("Days required for Lần đầu")
                return jsonify({"error": "Days required for Lần đầu"}), 400
            running_state["days"] = days
            running_state["custom_path"] = None
            try:
                run_file_scan(scan_action="first", days=days)
            except Exception as e:
                logger.error(f"Failed to run first scan: {str(e)}")
                return jsonify({"error": f"Failed to run first scan: {str(e)}"}), 500
        elif card == "Chỉ định":
            if not custom_path:
                logger.error("Custom path required for Chỉ định")
                return jsonify({"error": "Custom path required cho Chỉ định"}), 400
            abs_path = os.path.abspath(custom_path)
            if not os.path.exists(abs_path):
                logger.error(f"Custom path {abs_path} does not exist")
                return jsonify({"error": f"Custom path {abs_path} does not exist"}), 400
            try:
                with db_rwlock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT status, is_processed FROM file_list WHERE file_path = ? AND (status = 'xong' OR is_processed = 1)", (abs_path,))
                    result = cursor.fetchone()
                    conn.close()
                    if result:
                        logger.warning(f"File {abs_path} already processed with status {result[0]}")
                        return jsonify({"error": "File đã được xử lý"}), 400
            except Exception as e:
                logger.error(f"Error checking file status: {str(e)}")
                return jsonify({"error": f"Error checking file status: {str(e)}"}), 500
            running_state["custom_path"] = abs_path
            running_state["days"] = None
            try:
                scheduler.pause()
                run_file_scan(scan_action="custom", custom_path=abs_path)
                with db_rwlock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT file_path FROM file_list WHERE custom_path = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1", (abs_path,))
                    result = cursor.fetchone()
                    conn.close()
                if result:
                    from .program_runner import start_frame_sampler_thread, start_event_detector_thread
                    frame_sampler_event.set()
                    start_frame_sampler_thread()
                    start_event_detector_thread()
                    logger.info(f"[Chỉ định] Processing started: {result[0]}")
                    import time
                    while True:
                        with db_rwlock:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT status FROM file_list WHERE file_path = ?", (result[0],))
                            status_result = cursor.fetchone()
                            conn.close()
                        if status_result and status_result[0] == 'xong':
                            break
                        time.sleep(2)
                    logger.info(f"[Chỉ định] Processing completed: {result[0]}")
                    scheduler.resume()
                    try:
                        if not scheduler.running:
                            scheduler.start()
                            logger.info("Restarted scheduler for default mode")
                        run_file_scan(scan_action="default")
                        frame_sampler_event.set()
                        event_detector_event.set()
                        logger.info(f"Completed Chỉ định, transitioning to default: scheduler_running={scheduler.running}, running_state={running_state}")
                    except Exception as e:
                        logger.error(f"Error triggering default scan: {str(e)}")
                else:
                    logger.error(f"[Chỉ định] No pending file found at: {abs_path}")
                    return jsonify({"error": "Không tìm thấy file pending để xử lý"}), 404
            except Exception as e:
                logger.error(f"[Chỉ định] Error: {str(e)}")
                scheduler.resume()
                return jsonify({"error": f"Xử lý chỉ định thất bại: {str(e)}"}), 500
        else:
            running_state["days"] = None
            running_state["custom_path"] = None

        running_state["current_running"] = card
        if not scheduler.running:
            running_state["current_running"] = "Mặc định"
            scheduler.start()

        if card == "Lần đầu":
            try:
                with db_rwlock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE program_status SET value = ? WHERE key = ?", ("true", "first_run_completed"))
                    conn.commit()
                    conn.close()
                logger.info("Chuyển sang chế độ chạy mặc định (quét lặp) sau khi hoàn thành Lần đầu")
            except Exception as e:
                logger.error(f"Error updating first_run_completed: {e}")

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
    logger.info("GET /program called")
    return jsonify({
        "current_running": running_state["current_running"],
        "days": running_state.get("days"),
        "custom_path": running_state.get("custom_path")
    }), 200

@program_bp.route('/confirm-run', methods=['POST'])
def confirm_run():
    logger.info("POST /confirm-run called")
    data = request.json
    card = data.get('card')

    scan_action = "first" if card == "Lần đầu" else "default" if card == "Mặc định" else "custom"
    days = running_state.get("days") if card == "Lần đầu" else None
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
    logger.info("GET /program-progress called")
    try:
        with db_rwlock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT file_path, status FROM file_list WHERE is_processed = 0 ORDER BY created_at DESC")
            files_status = [{"file": row[0], "status": row[1]} for row in cursor.fetchall()]
            conn.close()
        logger.info(f"Retrieved {len(files_status)} files for status")
        return jsonify({"files": files_status}), 200
    except Exception as e:
        logger.error(f"Failed to retrieve program progress: {str(e)}")
        return jsonify({"error": f"Failed to retrieve program progress: {str(e)}"}), 500

@program_bp.route('/check-first-run', methods=['GET'])
def check_first_run():
    logger.info("GET /check-first-run called")
    try:
        with db_rwlock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM program_status WHERE key = "first_run_completed"')
            result = cursor.fetchone()
            conn.close()
            first_run_completed = result[0] == 'true' if result else False
        logger.info(f"First run completed: {first_run_completed}")
        return jsonify({"first_run_completed": first_run_completed}), 200
    except Exception as e:
        logger.error(f"Failed to check first run status: {str(e)}")
        return jsonify({"error": f"Failed to check first run status: {str(e)}"}), 500

@program_bp.route('/get-cameras', methods=['GET'])
def get_cameras():
    logger.info("GET /get-cameras called")
    try:
        with db_rwlock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT selected_cameras FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            conn.close()
            cameras = result[0] if result else "[]"
            cameras_list = json.loads(cameras) if cameras else []
        logger.info(f"Retrieved {len(cameras_list)} cameras")
        return jsonify({"cameras": cameras_list}), 200
    except Exception as e:
        logger.error(f"Failed to retrieve cameras: {str(e)}")
        return jsonify({"error": f"Failed to retrieve cameras: {str(e)}"}), 500

@program_bp.route('/get-camera-folders', methods=['GET'])
def get_camera_folders():
    logger.info("GET /get-camera-folders called")
    try:
        with db_rwlock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            video_root = result[0] if result else os.path.join(BASE_DIR, "Inputvideo")
            conn.close()

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
        running_state["current_running"] = "Mặc định"
        scheduler.start()
