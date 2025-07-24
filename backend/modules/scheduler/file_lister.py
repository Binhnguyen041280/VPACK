import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from statistics import median
from modules.db_utils import find_project_root, get_db_connection
from .db_sync import db_rwlock
import subprocess
import pytz

# Cấu hình múi giờ Việt Nam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("app")
logger.info("Logging initialized")

# Hằng số cho quét động
BUFFER_SECONDS = 6 * 60
N_FILES_FOR_ESTIMATE = 3
DEFAULT_DAYS = 7

DB_PATH = os.path.join(BASE_DIR, "database", "events.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db_path():
    try:
        with db_rwlock.gen_rlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT db_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else DB_PATH
    except Exception as e:
        logger.error(f"Lỗi khi lấy DB_PATH: {e}")
        return DB_PATH

DB_PATH = get_db_path()
logger.info(f"Sử dụng DB_PATH: {DB_PATH}")

def get_file_creation_time(file_path):
    """Lấy thời gian tạo tệp bằng FFmpeg, chuẩn hóa theo múi giờ Việt Nam."""
    if not os.path.isfile(file_path) or not file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
        return datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_entries", "format_tags=creation_time:format=creation_time",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        creation_time = (
            metadata.get("format", {})
                    .get("tags", {})
                    .get("creation_time")
            or metadata.get("format", {}).get("creation_time")  
        )  
        if creation_time:
            utc_time = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            utc_time = pytz.utc.localize(utc_time)
            return utc_time.astimezone(VIETNAM_TZ)
        else:
            logger.warning(f"Không tìm thấy creation_time cho {file_path}, dùng giờ hệ thống")
            return datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Lỗi khi lấy creation_time cho {file_path}: {e}")
        return datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)

def compute_chunk_interval(ctimes):
    ctimes = sorted(ctimes)[-N_FILES_FOR_ESTIMATE:]
    if len(ctimes) < 2:
        return 30
    intervals = [(ctimes[i+1] - ctimes[i]) / 60 for i in range(len(ctimes)-1)]
    return round(median(intervals))

def scan_files(root_path, video_root, time_threshold, max_ctime, restrict_to_current_date=False, camera_ctime_map=None, working_days=None, from_time=None, to_time=None, selected_cameras=None, strict_date_match=False):
    video_files = []
    file_ctimes = []
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
    current_date = datetime.now(VIETNAM_TZ).date()
    skipped_by_ctime = 0
    skipped_by_camera = 0
    ffprobe_errors = 0

    for root, dirs, files in os.walk(root_path):
        relative_path = os.path.relpath(root, video_root)
        camera_name = relative_path.split(os.sep)[0] if relative_path != "." else os.path.basename(video_root)
        if selected_cameras and camera_name not in selected_cameras:
            skipped_by_camera += len([f for f in files if f.lower().endswith(video_extensions)])
            continue

        for file in files:
            if file.lower().endswith(video_extensions):
                file_path = os.path.join(root, file)
                try:
                    file_ctime = get_file_creation_time(file_path)
                except Exception:
                    ffprobe_errors += 1
                    file_ctime = datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)

                logger.debug(f"Checking file {file_path}, ctime={file_ctime}, max_ctime={max_ctime}")
                if time_threshold and file_ctime < time_threshold:
                    skipped_by_ctime += 1
                    continue

                if max_ctime and file_ctime <= max_ctime:
                    skipped_by_ctime += 1
                    continue

                weekday = file_ctime.strftime('%A')
                if working_days and weekday not in working_days:
                    skipped_by_ctime += 1
                    logger.debug(f"Skipped file {file_path} due to non-working day: {weekday}")
                    continue

                file_time = file_ctime.time()
                if from_time and to_time and not (from_time <= file_time <= to_time):
                    skipped_by_ctime += 1
                    logger.debug(f"Skipped file {file_path} due to time outside working hours: {file_time}")
                    continue

                relative_path = os.path.relpath(file_path, video_root)
                video_files.append(relative_path)
                file_ctimes.append(file_ctime.timestamp())
                logger.info(f"Tìm thấy tệp: {file_path}")

        if camera_ctime_map is not None:
            dir_ctime = datetime.fromtimestamp(os.path.getctime(root), tz=VIETNAM_TZ)
            camera_ctime_map[camera_name] = max(camera_ctime_map.get(camera_name, 0), dir_ctime.timestamp())

    logger.info(f"Thống kê quét: {skipped_by_ctime} tệp bỏ qua do ctime, {skipped_by_camera} tệp bỏ qua do camera, {ffprobe_errors} lỗi ffprobe")
    return video_files, file_ctimes

def save_files_to_db(conn, video_files, file_ctimes, scan_action, days, custom_path, video_root):
    if not video_files:
        return

    insert_data = []
    days_val = len(days) if isinstance(days, list) else days if days is not None else None
    for file_path, file_ctime in zip(video_files, file_ctimes):
        absolute_path = os.path.join(video_root, file_path) if scan_action != "custom" or not os.path.isfile(custom_path) else custom_path
        file_ctime_dt = datetime.fromtimestamp(file_ctime, tz=VIETNAM_TZ)
        priority = 1 if scan_action == "custom" else 0
        relative_path = os.path.relpath(absolute_path, video_root) if scan_action != "custom" else os.path.dirname(absolute_path)
        camera_name = relative_path.split(os.sep)[0] if relative_path != "." else os.path.basename(video_root)
        insert_data.append((
            scan_action, days_val, custom_path, absolute_path, datetime.now(VIETNAM_TZ), file_ctime_dt, priority, camera_name, 'pending', 0
        ))

    with conn:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO file_list (program_type, days, custom_path, file_path, created_at, ctime, priority, camera_name, status, is_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', insert_data)
        logger.info(f"Đã chèn {len(insert_data)} tệp vào file_list")

def list_files(video_root, scan_action, custom_path, days, db_path, default_scan_days=7, camera_ctime_map=None, is_initial_scan=False):
    try:
        with db_rwlock.gen_wlock():
            conn = get_db_connection()
            cursor = conn.cursor()

            if not os.path.exists(video_root):
                try:
                    os.makedirs(video_root, exist_ok=True)
                    logger.info(f"Đã tạo thư mục video root: {video_root}")
                except Exception as e:
                    logger.error(f"Không thể tạo thư mục video root: {video_root}, lỗi: {str(e)}")
                    raise Exception(f"Không thể tạo thư mục video root: {str(e)}")

            cursor.execute('SELECT MAX(ctime) FROM file_list')
            last_ctime = cursor.fetchone()[0]
            max_ctime = datetime.fromisoformat(last_ctime.replace('Z', '+00:00')) if last_ctime else datetime.min.replace(tzinfo=VIETNAM_TZ)

            cursor.execute("SELECT input_path, selected_cameras FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            if result:
                video_root = result[0]
                selected_cameras = json.loads(result[1]) if result[1] else []
            else:
                selected_cameras = []
            logger.info(f"Sử dụng video_root: {video_root}, Camera được chọn: {selected_cameras}")

            cursor.execute("SELECT working_days, from_time, to_time FROM general_info WHERE id = 1")
            general_info = cursor.fetchone()
            if general_info:
                try:
                    working_days_raw = general_info[0].encode('utf-8').decode('utf-8') if general_info[0] else ''
                    working_days = json.loads(working_days_raw) if working_days_raw else []
                except json.JSONDecodeError as e:
                    logger.error(f"JSON không hợp lệ trong working_days: {general_info[0]}, lỗi: {e}")
                    working_days = []
                from_time = datetime.strptime(general_info[1], '%H:%M').time() if general_info[1] else None
                to_time = datetime.strptime(general_info[2], '%H:%M').time() if general_info[2] else None
            else:
                working_days, from_time, to_time = [], None, None
            logger.info(f"Ngày làm việc: {working_days}, from_time: {from_time}, to_time: {to_time}")

            video_files = []
            file_ctimes = []

            if scan_action == "custom" and custom_path:
                if not os.path.exists(custom_path):
                    raise Exception(f"Đường dẫn không tồn tại: {custom_path}")
                if os.path.isfile(custom_path) and custom_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                    file_name = os.path.basename(custom_path)
                    file_ctime = get_file_creation_time(custom_path)
                    video_files.append(file_name)
                    file_ctimes.append(file_ctime.timestamp())
                    logger.info(f"Tìm thấy tệp: {custom_path}")
                else:
                    video_files, file_ctimes = scan_files(
                        custom_path, video_root, None, None, False, None,
                        working_days, from_time, to_time, selected_cameras, strict_date_match=False
                    )
            elif scan_action == "first" and days:
                time_threshold = datetime.now(VIETNAM_TZ) - timedelta(days=days)
                video_files, file_ctimes = scan_files(
                    video_root, video_root, time_threshold, None, False, None,
                    working_days, from_time, to_time, selected_cameras, strict_date_match=False
                )
                cursor.execute('''
                    INSERT OR REPLACE INTO program_status (id, key, value)
                    VALUES ((SELECT id FROM program_status WHERE key = 'first_run_completed'), 'first_run_completed', 'true')
                ''')
                conn.commit()
            else:  # default
                time_threshold = datetime.now(VIETNAM_TZ) - timedelta(days=default_scan_days) if is_initial_scan else datetime.now(VIETNAM_TZ) - timedelta(days=1)
                restrict_to_current_date = not is_initial_scan
                video_files, file_ctimes = scan_files(
                    video_root, video_root, time_threshold, max_ctime, restrict_to_current_date, camera_ctime_map,
                    working_days, from_time, to_time, selected_cameras, strict_date_match=True
                )

            save_files_to_db(conn, video_files, file_ctimes, scan_action, days, custom_path, video_root)
            conn.close()
        logger.info(f"Tìm thấy {len(video_files)} tệp video")
        return video_files, file_ctimes
    except Exception as e:
        logger.error(f"Lỗi trong list_files: {e}")
        raise Exception(f"Lỗi trong list_files: {str(e)}")

def cleanup_stale_jobs():
    try:
        with db_rwlock.gen_wlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE file_list 
                SET status = 'pending'
                WHERE status = 'đang frame sampler ...'
                AND created_at < datetime('now', '-59 minutes')
            """)
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            if affected > 0:
                logger.info(f"Reset {affected} stale jobs to pending")
    except Exception as e:
        logger.error(f"Error cleaning up stale jobs: {e}")

def run_file_scan(scan_action="default", days=None, custom_path=None):
    db_path = get_db_path()
    cleanup_stale_jobs()
    try:
        with db_rwlock.gen_rlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            conn.close()
            video_root = result[0] if result else ""
        if not video_root:
            raise Exception("Không tìm thấy video_root trong processing_config")
        camera_ctime_map = {}
        is_initial_scan = scan_action == "default" and days is not None  # Đặt is_initial_scan=True cho lần quét đầu tiên
        files, _ = list_files(video_root, scan_action, custom_path, days, db_path, camera_ctime_map=camera_ctime_map, is_initial_scan=is_initial_scan)
        return files
    except Exception as e:
        logger.error(f"Lỗi trong run_file_scan: {e}")
        raise
