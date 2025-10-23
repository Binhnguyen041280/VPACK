from flask import Blueprint, jsonify
import os
import sqlite3
import logging
import ast
import re
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

def parse_qr_detections_from_log(log_file_path, event_ts):
    """
    Parse QR detections with bbox from log file.

    Supports two patterns:
    1. Success: timestamp,state,TRACKING_CODE,bbox:[x,y,w,h]
    2. Boundary: timestamp,state,,boundary:[x,y,w,h]

    Args:
        log_file_path: Path to log file
        event_ts: Event start timestamp (relative seconds in video)

    Returns:
        List of tuples: (relative_timestamp, tracking_code, bbox_x, bbox_y, bbox_w, bbox_h, decode_success)
        decode_success: 1 for successful decode, 0 for boundary only
    """
    qr_detections = []
    # Pattern 1: Success - timestamp,state,TRACKING_CODE,bbox:[x,y,w,h]
    success_pattern = r'^(\d+),\w+,([A-Z0-9]+),bbox:\[(\d+),(\d+),(\d+),(\d+)\]'
    # Pattern 2: Boundary - timestamp,state,,boundary:[x,y,w,h]
    boundary_pattern = r'^(\d+),\w+,,boundary:\[(\d+),(\d+),(\d+),(\d+)\]'

    try:
        with open(log_file_path, 'r') as f:
            next(f)  # Skip header
            for line in f:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    continue

                # Try success pattern first
                match = re.match(success_pattern, line_stripped)
                if match:
                    log_timestamp = int(match.group(1))
                    tracking_code = match.group(2)
                    bbox_x = int(match.group(3))
                    bbox_y = int(match.group(4))
                    bbox_w = int(match.group(5))
                    bbox_h = int(match.group(6))
                    decode_success = 1

                    # Calculate relative timestamp from event start
                    relative_timestamp = log_timestamp - event_ts

                    # Skip negative timestamps (shouldn't happen)
                    if relative_timestamp >= 0:
                        qr_detections.append((
                            relative_timestamp,
                            tracking_code,
                            bbox_x,
                            bbox_y,
                            bbox_w,
                            bbox_h,
                            decode_success
                        ))
                    continue

                # Try boundary pattern
                match = re.match(boundary_pattern, line_stripped)
                if match:
                    log_timestamp = int(match.group(1))
                    tracking_code = ""  # Empty for boundary entries
                    bbox_x = int(match.group(2))
                    bbox_y = int(match.group(3))
                    bbox_w = int(match.group(4))
                    bbox_h = int(match.group(5))
                    decode_success = 0

                    # Calculate relative timestamp from event start
                    relative_timestamp = log_timestamp - event_ts

                    # Skip negative timestamps (shouldn't happen)
                    if relative_timestamp >= 0:
                        qr_detections.append((
                            relative_timestamp,
                            tracking_code,
                            bbox_x,
                            bbox_y,
                            bbox_w,
                            bbox_h,
                            decode_success
                        ))

        return qr_detections
    except Exception as e:
        return []

def process_single_log_with_cursor(log_file_path, cursor, conn):
    """
    FIXED: Xử lý single log với cursor và connection được truyền vào
    Tránh tạo nested locks và cursor escape issues
    """
    # Khởi tạo logger với context log_file
    logger = get_logger(__name__, {"log_file": log_file_path})

    if not os.path.isfile(log_file_path):
        logger.warning(f"Log file not found: {log_file_path}, skipping.")
        return

    logger.info("Logging initialized for process_single_log_with_cursor")

    # NOTE: Không cần try-except ở đây vì được handle ở caller level

    # Check is_processed status of log file
    cursor.execute("SELECT is_processed FROM processed_logs WHERE log_file = ?", (log_file_path,))
    result = cursor.fetchone()
    if result and result[0] == 1:
        logger.info(f"Log file {log_file_path} already processed, skipping")
        return

    with open(log_file_path, "r") as f:
        header = f.readline().strip()
        logger.info(f"Header: {header}")
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
        logger.info(f"Parsed header - Start: {start_time}, End: {end_time}, Start_Time: {start_time_str} (UTC: {start_time_dt_utc}), Camera_Name: {camera_name}, Video_File: {video_path}")

        # Check if log file is empty
        first_data_line = f.readline().strip()
        if not first_data_line:
            logger.info(f"Log file {log_file_path} is empty, skipping")
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
                logger.info(f"Error parsing line '{line.strip()}': {str(e)}")

    # Get min_packing_time from Processing_config
    cursor.execute("SELECT min_packing_time FROM Processing_config LIMIT 1")
    min_packing_time_row = cursor.fetchone()
    min_packing_time = min_packing_time_row[0] if min_packing_time_row else 5
    logger.info(f"Min packing time: {min_packing_time}")

    # Get latest pending_event by ts
    cursor.execute("SELECT event_id, ts, tracking_codes, video_file FROM events WHERE te IS NULL AND camera_name = ? ORDER BY event_id DESC LIMIT 1", (camera_name,))
    pending_event = cursor.fetchone()
    logger.info(f"Pending event: {pending_event}")
    ts = pending_event[1] if pending_event else None
    # 🔒 SECURITY FIX: Use ast.literal_eval() instead of eval() to prevent code injection
    pending_tracking_codes = ast.literal_eval(pending_event[2]) if pending_event and pending_event[2] else []
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
                logger.info(f"Adjusted pending event: Ts={ts}, Te={te}, Duration per event set to {duration_per_event}")

                if pending_video_file == video_path:
                    current_ts = ts
                    for i, code in enumerate(all_tracking_codes):
                        current_te = current_ts + duration_per_event if current_ts is not None else te
                        if i == 0:
                            # Update pending event for first code
                            segments.append((current_ts, current_te, duration_per_event, [code], video_path, event_id))
                            logger.info(f"Updated consecutive pending event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        else:
                            # Add new event for subsequent codes
                            segments.append((current_ts, current_te, duration_per_event, [code], video_path, None))
                            logger.info(f"Added new consecutive event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        current_ts = current_te
                else:
                    current_ts = None
                    for i, code in enumerate(all_tracking_codes):
                        current_te = te - (num_codes - i - 1) * duration_per_event
                        segments.append((current_ts, current_te, duration_per_event, [code], video_path, None))
                        logger.info(f"Added consecutive pending event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        current_ts = current_te

                ts = None
                has_pending = False
            elif current_state == "Off":
                pending_tracking_codes.extend([code for code in current_tracking_codes if code and code not in pending_tracking_codes])
                # Check and delete pending event if no tracking_codes
                if not pending_tracking_codes and not current_tracking_codes:
                    cursor.execute("DELETE FROM events WHERE te IS NULL AND event_id = (SELECT MAX(event_id) FROM events WHERE te IS NULL AND camera_name = ?)", (camera_name,))
                    logger.info(f"Deleted last pending event for camera {camera_name} due to no tracking_codes")
        elif not has_pending:
            if prev_state == "On" and current_state == "Off":
                ts = current_second
                pending_tracking_codes = current_tracking_codes[:]
                logger.info(f"Detected event Ts at second {current_second}")

            elif prev_state == "Off" and current_state == "On" and ts is not None:
                te = current_second
                total_duration = calculate_duration(ts, te)

                # Tách tracking_codes thành các sự kiện liên tiếp
                all_tracking_codes = list(set(pending_tracking_codes + current_tracking_codes))  # Loại bỏ trùng lặp
                num_codes = len(all_tracking_codes) if all_tracking_codes else 1
                duration_per_event = max(round((total_duration or 0) / num_codes), min_packing_time)  # Round and ensure >= min_packing_time
                total_duration = duration_per_event * num_codes  # Update total_duration
                te = ts + total_duration if ts is not None else te
                logger.info(f"Adjusted event: Ts={ts}, Te={te}, Duration per event set to {duration_per_event}")

                if all_tracking_codes:
                    current_ts = ts
                    for i, code in enumerate(all_tracking_codes):
                        current_te = current_ts + duration_per_event if current_ts is not None else te
                        segments.append((current_ts, current_te, duration_per_event, [code], video_path, None))
                        logger.info(f"Added consecutive event {i+1}/{num_codes}: Ts={current_ts}, Te={current_te}, Duration={duration_per_event}, Tracking_code={code}")
                        current_ts = current_te
                else:
                    segments.append((ts, te, duration_per_event, [], video_path, None))
                    logger.info(f"Added event without tracking_code: Ts={ts}, Te={te}, Duration={duration_per_event}")

                ts = None
                pending_tracking_codes = []

            elif ts is not None and current_state == "Off":
                pending_tracking_codes.extend([code for code in current_tracking_codes if code and code not in pending_tracking_codes])

        prev_state = current_state

    if ts is not None:
        segments.append((ts, None, None, pending_tracking_codes, video_path, None))
        logger.info(f"Second {frame_sampler_data[-1]['second']}: Ts={ts}, Te=Not finished")

    logger.info(f"All segments detected: {segments}")

    for segment in segments:
        ts, te, duration, tracking_codes, segment_video_path, segment_event_id = segment
        # Note: Don't skip events with empty tracking_codes yet - they may have boundary detections
        # We'll validate after parsing QR detections
        # Calculate UTC timestamps for database storage
        packing_time_start = int((start_time_dt_utc.timestamp() + ts) * 1000) if ts is not None else None
        packing_time_end = int((start_time_dt_utc.timestamp() + te) * 1000) if te is not None else None

        # Store timezone metadata for reference
        timezone_info = {
            'video_timezone': str(start_time_dt.tzinfo),
            'utc_offset_seconds': start_time_dt.utcoffset().total_seconds() if start_time_dt.utcoffset() else 0,
            'stored_as_utc': True
        }

        current_event_id = None
        if segment_event_id is not None:
            cursor.execute("UPDATE events SET te=?, duration=?, tracking_codes=?, packing_time_end=?, timezone_info=? WHERE event_id=?",
                           (te, duration, str(tracking_codes), packing_time_end, str(timezone_info), segment_event_id))
            logger.info(f"Updated event_id {segment_event_id}: ts={ts}, te={te}, duration={duration}")
            current_event_id = segment_event_id
        else:
            cursor.execute('''INSERT INTO events (ts, te, duration, tracking_codes, video_file, buffer, camera_name, packing_time_start, packing_time_end, timezone_info)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (ts, te, duration, str(tracking_codes), segment_video_path, 0, camera_name, packing_time_start, packing_time_end, str(timezone_info)))
            current_event_id = cursor.lastrowid
            logger.info(f"Inserted new event: event_id={current_event_id}, ts={ts}, te={te}, duration={duration}")

        # Parse and insert QR detections for this event (if event is completed)
        if current_event_id and te is not None and ts is not None:
            qr_detections = parse_qr_detections_from_log(log_file_path, int(ts))

            if qr_detections:
                logger.info(f"Found {len(qr_detections)} QR detections for event {current_event_id}")

                success_count = 0
                boundary_count = 0

                for rel_ts, code, bbox_x, bbox_y, bbox_w, bbox_h, decode_success in qr_detections:
                    # Insert logic:
                    # - Success entries (decode_success=1): Only if code matches tracking_codes
                    # - Boundary entries (decode_success=0): Always insert (for empty events)
                    should_insert = False
                    if decode_success == 1 and code in tracking_codes:
                        should_insert = True
                        success_count += 1
                    elif decode_success == 0:
                        should_insert = True
                        boundary_count += 1

                    if should_insert:
                        try:
                            cursor.execute("""
                                INSERT INTO qr_detections
                                (event_id, timestamp_seconds, tracking_code, bbox_x, bbox_y, bbox_w, bbox_h, decode_success)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (current_event_id, rel_ts, code, bbox_x, bbox_y, bbox_w, bbox_h, decode_success))

                            if decode_success == 1:
                                logger.debug(f"Inserted SUCCESS detection: event={current_event_id}, ts={rel_ts}s, code={code}, bbox=({bbox_x},{bbox_y},{bbox_w},{bbox_h})")
                            else:
                                logger.debug(f"Inserted BOUNDARY detection: event={current_event_id}, ts={rel_ts}s, bbox=({bbox_x},{bbox_y},{bbox_w},{bbox_h})")
                        except sqlite3.IntegrityError as e:
                            logger.error(f"Error inserting QR detection for event {current_event_id}: {e}")
                            continue

                logger.info(f"Inserted {success_count} success detections and {boundary_count} boundary detections for event {current_event_id}")

                # Validate: Check if event is empty (no MVD codes found)
                if success_count == 0 and not tracking_codes:
                    # Get duration from segment
                    event_duration = duration if duration else 0

                    if event_duration >= min_packing_time:
                        # Event long enough → có thể có QR miss do 5fps sampling, mark retry
                        cursor.execute("""
                            UPDATE events
                            SET retry_needed = 1, retry_count = 0, status = 'empty_need_retry'
                            WHERE event_id = ?
                        """, (current_event_id,))
                        logger.info(f"✓ Marked event {current_event_id} for retry (duration={event_duration}s >= min={min_packing_time}s)")
                    else:
                        # Event quá ngắn → noise, delete
                        logger.info(f"✗ Deleting noise event {current_event_id} (duration={event_duration}s < min={min_packing_time}s)")
                        cursor.execute("DELETE FROM events WHERE event_id = ?", (current_event_id,))
            else:
                # No detections found in log
                if not tracking_codes:
                    # Get duration from segment
                    event_duration = duration if duration else 0

                    if event_duration >= min_packing_time:
                        # Event long enough → mark retry
                        cursor.execute("""
                            UPDATE events
                            SET retry_needed = 1, retry_count = 0, status = 'empty_need_retry'
                            WHERE event_id = ?
                        """, (current_event_id,))
                        logger.info(f"✓ Marked event {current_event_id} for retry (no detections but duration={event_duration}s >= min={min_packing_time}s)")
                    else:
                        # Noise, delete
                        logger.info(f"✗ Deleting noise event {current_event_id}: no detections found (duration={event_duration}s < min={min_packing_time}s)")
                        cursor.execute("DELETE FROM events WHERE event_id = ?", (current_event_id,))

    cursor.execute("UPDATE processed_logs SET is_processed = 1, processed_at = ? WHERE log_file = ?", (datetime.now(timezone.utc), log_file_path))
    logger.info("Database changes committed")


def process_single_log(log_file_path):
    """
    LEGACY: Wrapper function để maintain backward compatibility
    Sử dụng riêng lock cho single file processing
    """
    # Khởi tạo logger với context log_file
    logger = get_logger(__name__, {"log_file": log_file_path})

    if not os.path.isfile(log_file_path):
        logger.warning(f"Log file not found: {log_file_path}, skipping.")
        return

    logger.info("Logging initialized for process_single_log")

    try:
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                # Delegate to the new function
                process_single_log_with_cursor(log_file_path, cursor, conn)

    except Exception as e:
        logger.error(f"Error in process_single_log: {str(e)}")
        raise

@event_detector_bp.route('/process-events', methods=['GET'])
def process_events():
    logger = get_logger(__name__)
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
                logger.info(f"Log files to process: {log_files}")

                # FIXED: Xử lý tất cả files trong cùng transaction/lock scope
                for log_file in log_files:
                    if not os.path.isfile(log_file):
                        logger.warning(f"Log file not found, skipping: {log_file}")
                        continue
                    if os.path.exists(log_file):
                        logger.info(f"Starting to process file: {log_file}")
                        # FIXED: Gọi helper function với cursor hiện tại thay vì tạo mới
                        process_single_log_with_cursor(log_file, cursor, conn)
                        logger.info(f"Finished processing file: {log_file}")
                    else:
                        logger.info(f"File not found: {log_file}")

        return jsonify({"message": "Event detection completed successfully"}), 200
    except Exception as e:
        logger.error(f"Error in process_events: {str(e)}")
        return jsonify({"error": str(e)}), 500