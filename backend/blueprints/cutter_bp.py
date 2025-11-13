import os
from datetime import datetime
import subprocess
from flask import Blueprint, request, jsonify
from modules.db_utils.safe_connection import safe_db_connection
import ast
from modules.technician.cutter.cutter_complete import cut_complete_event
from modules.technician.cutter.cutter_incomplete import (
    cut_incomplete_event,
    merge_incomplete_events,
)
from modules.technician.cutter.cutter_utils import generate_output_filename, update_event_in_db
from modules.scheduler.db_sync import db_rwlock

cutter_bp = Blueprint("cutter", __name__)


# Docker-compatible output directory initialization
# Uses database config first, falls back to environment-aware defaults
def get_output_directory():
    """
    Get output directory with Docker compatibility.

    Priority:
    1. Environment variable (VTRACK_OUTPUT_DIR) - takes precedence in Docker
    2. Docker default (/app/resources/output) - when in Docker mode
    3. Database configuration (processing_config.output_path) - local development only
    4. Local development default (../../resources/output_clips)
    """
    # Docker mode: Use environment variable or Docker default (ignore database)
    if os.getenv("VTRACK_IN_DOCKER") == "true":
        return os.getenv("VTRACK_OUTPUT_DIR", "/app/resources/output")

    # Local development: Check database first
    try:
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT output_path FROM processing_config LIMIT 1")
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
    except Exception as e:
        print(f"Warning: Could not read output_path from database: {e}")

    # Local development fallback
    return os.getenv(
        "VTRACK_OUTPUT_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../resources/output_clips"),
    )


# Initialize output directory at module load time
output_dir = get_output_directory()
try:
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"✅ Created output directory: {output_dir}")
except (OSError, PermissionError) as e:
    print(f"⚠️ Warning: Could not create output directory {output_dir}: {e}")
    print(f"   Videos may not be saved correctly. Please check permissions.")


def get_video_duration(video_file):
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_file,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception:
        return None


def cut_and_update_events(selected_events, tracking_codes_filter, brand_name="Alan"):
    with db_rwlock.gen_wlock():
        with safe_db_connection() as conn:
            cursor = conn.cursor()
        cursor.execute("SELECT video_buffer, max_packing_time FROM processing_config LIMIT 1")
        result = cursor.fetchone()
        video_buffer = result[0] if result else 5
        max_packing_time = result[1] if result else 120
        cut_files = []

        for event in selected_events:
            event_id = event.get("event_id")
            ts = event.get("ts")
            te = event.get("te")
            video_file = event.get("video_file")
            cursor.execute("SELECT is_processed FROM events WHERE event_id = ?", (event_id,))
            is_processed = cursor.fetchone()[0]
            if is_processed:
                print(f"Skipping: Event {event_id} was already processed")
                continue

            has_ts = ts is not None
            has_te = te is not None
            is_incomplete = (has_ts and not has_te) or (not has_ts and has_te)

            if is_incomplete:
                next_event = None
                if has_ts and not has_te:
                    cursor.execute(
                        "SELECT event_id, ts, te, video_file, packing_time_start, packing_time_end, tracking_codes, is_processed FROM events WHERE event_id = ? AND is_processed = 0",
                        (event_id + 1,),
                    )
                    next_event_row = cursor.fetchone()
                    if next_event_row:
                        next_event = {
                            "event_id": next_event_row[0],
                            "ts": next_event_row[1],
                            "te": next_event_row[2],
                            "video_file": next_event_row[3],
                            "packing_time_start": next_event_row[4],
                            "packing_time_end": next_event_row[5],
                            "tracking_codes": next_event_row[6],
                            "is_processed": next_event_row[7],
                        }
                elif not has_ts and has_te:
                    cursor.execute(
                        "SELECT event_id, ts, te, video_file, packing_time_start, packing_time_end, tracking_codes, is_processed FROM events WHERE event_id = ? AND is_processed = 0",
                        (event_id - 1,),
                    )
                    prev_event_row = cursor.fetchone()
                    if prev_event_row:
                        next_event = {
                            "event_id": prev_event_row[0],
                            "ts": prev_event_row[1],
                            "te": prev_event_row[2],
                            "video_file": prev_event_row[3],
                            "packing_time_start": prev_event_row[4],
                            "packing_time_end": prev_event_row[5],
                            "tracking_codes": prev_event_row[6],
                            "is_processed": prev_event_row[7],
                        }

                if next_event:
                    next_event_id = next_event.get("event_id")
                    next_ts = next_event.get("ts")
                    next_te = next_event.get("te")
                    next_video_file = next_event.get("video_file")
                    next_has_ts = next_ts is not None
                    next_has_te = next_te is not None
                    can_merge = (has_ts and not has_te and not next_has_ts and next_has_te) or (
                        not has_ts and has_te and next_has_ts and not next_has_te
                    )

                    if can_merge:
                        video_length_a = get_video_duration(video_file)
                        video_length_b = get_video_duration(next_video_file)
                        if video_length_a is None or video_length_b is None:
                            print(
                                f"Error: Cannot get duration of video {video_file} or {next_video_file}"
                            )
                            continue

                        output_file_a = generate_output_filename(
                            event, tracking_codes_filter, output_dir, brand_name
                        )
                        print(
                            f"Processing event {event_id}: output_file={output_file_a}, packing_time_start={event.get('packing_time_start')}, packing_time_end={event.get('packing_time_end')}"
                        )
                        if cut_incomplete_event(event, video_buffer, video_length_a, output_file_a):
                            update_event_in_db(cursor, event_id, output_file_a)

                        output_file_b = generate_output_filename(
                            next_event, tracking_codes_filter, output_dir, brand_name
                        )
                        print(
                            f"Processing event {next_event_id}: output_file={output_file_b}, packing_time_start={next_event.get('packing_time_start')}, packing_time_end={next_event.get('packing_time_end')}"
                        )
                        if cut_incomplete_event(
                            next_event, video_buffer, video_length_b, output_file_b
                        ):
                            update_event_in_db(cursor, next_event_id, output_file_b)

                        if has_ts and not has_te:
                            event_a = event
                            event_b = next_event
                            video_length_event_a = video_length_a
                            video_length_event_b = video_length_b
                        else:
                            event_a = next_event
                            event_b = event
                            video_length_event_a = video_length_b
                            video_length_event_b = video_length_a

                        print(
                            f"Gọi merge_incomplete_events: event_a (ID: {event_a.get('event_id')}, ts: {event_a.get('ts')}, te: {event_a.get('te')}), event_b (ID: {event_b.get('event_id')}, ts: {event_b.get('ts')}, te: {event_b.get('te')})"
                        )

                        merged_file = merge_incomplete_events(
                            event_a,
                            event_b,
                            video_buffer,
                            video_length_event_a,
                            video_length_event_b,
                            output_dir,
                            max_packing_time,
                            brand_name,
                        )
                        if merged_file:
                            update_event_in_db(cursor, event_id, merged_file)
                            update_event_in_db(cursor, next_event_id, merged_file)
                            cut_files.append(merged_file)
                        continue

            video_length = get_video_duration(video_file)
            if video_length is None:
                print(f"Error: Cannot get video duration {video_file}")
                continue

            output_file = generate_output_filename(
                event, tracking_codes_filter, output_dir, brand_name
            )
            print(
                f"Processing event {event_id}: output_file={output_file}, packing_time_start={event.get('packing_time_start')}, packing_time_end={event.get('packing_time_end')}"
            )

            if has_ts and has_te:
                if cut_complete_event(event, video_buffer, video_length, output_file):
                    update_event_in_db(cursor, event_id, output_file)
                    cut_files.append(output_file)
            elif is_incomplete:
                if cut_incomplete_event(event, video_buffer, video_length, output_file):
                    update_event_in_db(cursor, event_id, output_file)
                    cut_files.append(output_file)
            else:
                print(f"Skipping: Event {event_id} has no ts or te")
                continue

            # Auto-commit handled by context manager
    return cut_files


@cutter_bp.route("/cut-videos", methods=["POST"])
def cut_videos():
    data = request.get_json()
    selected_events = data.get("selected_events", [])
    tracking_codes_filter = data.get("tracking_codes_filter", [])

    if not selected_events:
        return jsonify({"error": "No selected events provided"}), 400

    try:
        cut_files = cut_and_update_events(selected_events, tracking_codes_filter)
        return jsonify({"message": "Videos cut successfully", "cut_files": cut_files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
