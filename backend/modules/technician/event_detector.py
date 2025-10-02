from flask import Blueprint, jsonify
import os
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.config.logging_config import get_logger
from zoneinfo import ZoneInfo
# Removed video_timezone_detector - using simple timezone operations


# Define BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

event_detector_bp = Blueprint('event_detector', __name__)

def calculate_duration(ts, te):
    if ts is None or te is None:
        return None
    if te < ts:
        return None
    return te - ts

def process_single_log_with_cursor(log_file_path, cursor, conn):
    """
    FIXED: Xử lý single log với cursor và connection được truyền vào
    Tránh tạo nested locks và cursor escape issues
    """
    if not os.path.isfile(log_file_path):
        logging.warning(f"Log file not found: {log_file_path}, skipping.")
        return
    # Khởi tạo logger với context log_file
    logger = get_logger(__name__, {"log_file": log_file_path})
    logger.info("Logging initialized for process_single_log_with_cursor")

    # NOTE: Không cần try-except ở đây vì được handle ở caller level

    # Check is_processed status of log file
    cursor.execute("SELECT is_processed FROM processed_logs WHERE log_file = ?", (log_file_path,))
    result = cursor.fetchone()
    if result and result[0] == 1:
        logging.info(f"Log file {log_file_path} already processed, skipping")
        return

    with open(log_file_path, "r") as f:
        header = f.readline().strip()
        logging.info(f"Header: {header}")
        start_time = int(header.split("Start: ")[1].split(",")[0])
        end_time = int(header.split("End: ")[1].split(",")[0])
        start_time_str = header.split("Start_Time: ")[1].split(",")[0].strip()
        camera_name = header.split("Camera_Name: ")[1].split(",")[0].strip()
        video_path = header.split("Video_File: ")[1].split(",")[0].strip()
        # Parse start_time with timezone awareness
        start_time_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        # Get system timezone from config instead of hardcoding
        from modules.utils.simple_timezone import get_system_timezone_from_db
        system_tz_str = get_system_timezone_from_db()
        user_timezone = ZoneInfo(system_tz_str)
        start_time_dt = start_time_dt.replace(tzinfo=user_timezone)
        # Convert to UTC for consistent storage
        start_time_dt_utc = start_time_dt.astimezone(timezone.utc)
        logging.info(f"Parsed header - Start: {start_time}, End: {end_time}, Start_Time: {start_time_str} (UTC: {start_time_dt_utc}), Camera_Name: {camera_name}, Video_File: {video_path}")

        # Check if log file is empty
        first_data_line = f.readline().strip()
        if not first_data_line:
            logging.info(f"Log file {log_file_path} is empty, skipping")
            cursor.execute("UPDATE processed_logs SET is_processed = 1, processed_at = ? WHERE log_file = ?", (datetime.now(timezone.utc), log_file_path))
            return

        # If data exists, go back and process
        f.seek(0)
        next(f)
        frame_sampler_data = []
        for line in f:
            parts = line.strip().split(",")
            try:
                second, state = parts[0], parts[1]
                codes = [parts[2]] if len(parts) > 2 and parts[2] else []
                frame_sampler_data.append({"second": float(second), "state": state, "tracking_codes": codes})
            except Exception as e:
                logging.info(f"Error parsing line '{line.strip()}': {str(e)}")

    # Get min_packing_time from Processing_config
    cursor.execute("SELECT min_packing_time FROM Processing_config LIMIT 1")
    min_packing_time_row = cursor.fetchone()
    min_packing_time = min_packing_time_row[0] if min_packing_time_row else 5
    logging.info(f"Min packing time: {min_packing_time}")

    # Get latest pending_event by ts
    cursor.execute("SELECT event_id, ts, tracking_codes, video_file FROM events WHERE te IS NULL AND camera_name = ? ORDER BY event_id DESC LIMIT 1", (camera_name,))
    pending_event = cursor.fetchone()
    logging.info(f"Pending event: {pending_event}")
    ts = pending_event[1] if pending_event else None
    pending_tracking_codes = eval(pending_event[2]) if pending_event and pending_event[2] else []
    pending_video_file = pending_event[3] if pending_event else None
    event_id = pending_event[0] if pending_event else None
    segments = []
    prev_state = None
    has_pending = ts is not None and ts <= start_time

    for data in frame_sampler_data:
        current_state = data["state"]
        current_second = data["second"]
        current_tracking_codes = data["tracking_codes"]

        if has_pending and ts is not None:
            if current_state == "On":
                te = current_second
                total_duration = calculate_duration(ts, te)
                
                # Tách tracking_codes thành các sự kiện liên tiếp
                all_tracking_codes = list(set(pending_tracking_codes + current_tracking_codes))
                num_codes = len(all_tracking_codes) if all_tracking_codes else 1
                duration_per_event = max(round((total_duration or 0) / num_codes), min_packing_time)  # Round and ensure >= min_packing_time
                total_duration = duration_per_event * num_codes  # Update total_duration
                te = ts + total_duration if ts is not None else te
                logging.info(f"Adjusted pending event: Ts={ts}, Te={te}, Duration per event set to {duration_per_event}")
                
                if pending_video_file == video_path:
                    current_ts = ts
                    for i, code in enumerate(all_tracking_codes):
                        current_te = current_ts + duration_per_event if current_ts is not None else te
                        if i == 0:
                            # Update pending event for first code
                            segments.append((current_ts, current_te, duration_per_event, [code], video_path, event_id))
                            logging.info(f"Updated consecutive pending event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        else:
                            # Add new event for subsequent codes
                            segments.append((current_ts, current_te, duration_per_event, [code], video_path, None))
                            logging.info(f"Added new consecutive event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        current_ts = current_te
                else:
                    current_ts = None
                    for i, code in enumerate(all_tracking_codes):
                        current_te = te - (num_codes - i - 1) * duration_per_event
                        segments.append((current_ts, current_te, duration_per_event, [code], video_path, None))
                        logging.info(f"Added consecutive pending event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        current_ts = current_te
                
                ts = None
                has_pending = False
            elif current_state == "Off":
                pending_tracking_codes.extend([code for code in current_tracking_codes if code and code not in pending_tracking_codes])
                # Check and delete pending event if no tracking_codes
                if not pending_tracking_codes and not current_tracking_codes:
                    cursor.execute("DELETE FROM events WHERE te IS NULL AND event_id = (SELECT MAX(event_id) FROM events WHERE te IS NULL AND camera_name = ?)", (camera_name,))
                    logging.info(f"Deleted last pending event for camera {camera_name} due to no tracking_codes")
        elif not has_pending:
            if prev_state == "On" and current_state == "Off":
                ts = current_second
                pending_tracking_codes = current_tracking_codes[:]
                logging.info(f"Detected event Ts at second {current_second}")

            elif prev_state == "Off" and current_state == "On" and ts is not None:
                te = current_second
                total_duration = calculate_duration(ts, te)
                
                # Tách tracking_codes thành các sự kiện liên tiếp
                all_tracking_codes = list(set(pending_tracking_codes + current_tracking_codes))  # Loại bỏ trùng lặp
                num_codes = len(all_tracking_codes) if all_tracking_codes else 1
                duration_per_event = max(round((total_duration or 0) / num_codes), min_packing_time)  # Round and ensure >= min_packing_time
                total_duration = duration_per_event * num_codes  # Update total_duration
                te = ts + total_duration if ts is not None else te
                logging.info(f"Adjusted event: Ts={ts}, Te={te}, Duration per event set to {duration_per_event}")
                
                if all_tracking_codes:
                    current_ts = ts
                    for i, code in enumerate(all_tracking_codes):
                        current_te = current_ts + duration_per_event if current_ts is not None else te
                        segments.append((current_ts, current_te, duration_per_event, [code], video_path, None))
                        logging.info(f"Added consecutive event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        current_ts = current_te
                else:
                    segments.append((ts, te, duration_per_event, [], video_path, None))
                    logging.info(f"Added event without tracking_code: Ts={ts}, Te={te}, Duration={duration_per_event}")
                
                ts = None
                pending_tracking_codes = []

            elif ts is not None and current_state == "Off":
                pending_tracking_codes.extend([code for code in current_tracking_codes if code and code not in pending_tracking_codes])

        prev_state = current_state

    if ts is not None:
        segments.append((ts, None, None, pending_tracking_codes, video_path, None))
        logging.info(f"Second {frame_sampler_data[-1]['second']}: Ts={ts}, Te=Not finished")

    logging.info(f"All segments detected: {segments}")

    for segment in segments:
        ts, te, duration, tracking_codes, segment_video_path, segment_event_id = segment
        if te is not None and not tracking_codes:
            logging.info(f"Skipping completed event due to empty tracking_codes: ts={ts}, te={te}")
            continue
        # Calculate UTC timestamps for database storage
        packing_time_start = int((start_time_dt_utc.timestamp() + ts) * 1000) if ts is not None else None
        packing_time_end = int((start_time_dt_utc.timestamp() + te) * 1000) if te is not None else None
        
        # Store timezone metadata for reference
        timezone_info = {
            'video_timezone': str(start_time_dt.tzinfo),
            'utc_offset_seconds': start_time_dt.utcoffset().total_seconds() if start_time_dt.utcoffset() else 0,
            'stored_as_utc': True
        }
        if segment_event_id is not None:
            cursor.execute("UPDATE events SET te=?, duration=?, tracking_codes=?, packing_time_end=?, timezone_info=? WHERE event_id=?",
                           (te, duration, str(tracking_codes), packing_time_end, str(timezone_info), segment_event_id))
            logging.info(f"Updated event_id {segment_event_id}: ts={ts}, te={te}, duration={duration}")
        else:
            cursor.execute('''INSERT INTO events (ts, te, duration, tracking_codes, video_file, buffer, camera_name, packing_time_start, packing_time_end, timezone_info)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (ts, te, duration, str(tracking_codes), segment_video_path, 0, camera_name, packing_time_start, packing_time_end, str(timezone_info)))
            logging.info(f"Inserted new event: ts={ts}, te={te}, duration={duration}")

    cursor.execute("UPDATE processed_logs SET is_processed = 1, processed_at = ? WHERE log_file = ?", (datetime.now(timezone.utc), log_file_path))
    logging.info("Database changes committed")


def process_single_log(log_file_path):
    """
    LEGACY: Wrapper function để maintain backward compatibility
    Sử dụng riêng lock cho single file processing
    """
    if not os.path.isfile(log_file_path):
        logging.warning(f"Log file not found: {log_file_path}, skipping.")
        return
    # Khởi tạo logger với context log_file
    logger = get_logger(__name__, {"log_file": log_file_path})
    logger.info("Logging initialized for process_single_log")

    try:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                # Delegate to the new function
                process_single_log_with_cursor(log_file_path, cursor, conn)

    except Exception as e:
        logging.error(f"Error in process_single_log: {str(e)}")
        raise

@event_detector_bp.route('/process-events', methods=['GET'])
def process_events():
    try:
        # FIXED: Sử dụng write lock cho toàn bộ operation để tránh cursor escape
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Lấy danh sách log files cần xử lý
                cursor.execute("""
                    SELECT DISTINCT log_file_path, (
                        SELECT CAST(SUBSTR(header, INSTR(header, 'Start: ') + 7, INSTR(SUBSTR(header, INSTR(header, 'Start: ') + 7), ',') - 1) AS INTEGER)
                        FROM (
                            SELECT SUBSTR(CAST(READFILE(log_file_path) AS TEXT), 1, INSTR(CAST(READFILE(log_file_path) AS TEXT), '\n') - 1) AS header
                        )
                    ) AS start_time
                    FROM file_list 
                    WHERE is_processed = 1 AND log_file_path IS NOT NULL 
                    AND log_file_path IN (SELECT log_file FROM processed_logs WHERE is_processed = 0)
                    ORDER BY start_time
                """)
                log_files = [row[0] for row in cursor.fetchall()]
                logging.info(f"Log files to process: {log_files}")

                # FIXED: Xử lý tất cả files trong cùng transaction/lock scope
                for log_file in log_files:
                    if not os.path.isfile(log_file):
                        logging.warning(f"Log file not found, skipping: {log_file}")
                        continue
                    if os.path.exists(log_file):
                        logging.info(f"Starting to process file: {log_file}")
                        # FIXED: Gọi helper function với cursor hiện tại thay vì tạo mới
                        process_single_log_with_cursor(log_file, cursor, conn)
                        logging.info(f"Finished processing file: {log_file}")
                    else:
                        logging.info(f"File not found: {log_file}")

        return jsonify({"message": "Event detection completed successfully"}), 200
    except Exception as e:
        logging.error(f"Error in process_events: {str(e)}")
        return jsonify({"error": str(e)}), 500