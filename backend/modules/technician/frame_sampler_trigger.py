import json
import logging

# Removed video_timezone_detector - using simple timezone operations
import math
import os
import sqlite3
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from modules.config.logging_config import get_logger
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock, frame_sampler_event

# Health check imports
from modules.technician.camera_health_checker import run_health_check, should_run_health_check

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
    "wechat_qr",
)
DETECT_PROTO = os.path.join(MODEL_DIR, "detect.prototxt")
DETECT_MODEL = os.path.join(MODEL_DIR, "detect.caffemodel")
SR_PROTO = os.path.join(MODEL_DIR, "sr.prototxt")
SR_MODEL = os.path.join(MODEL_DIR, "sr.caffemodel")


class FrameSamplerTrigger:
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.video_lock = threading.Lock()
        self.setup_wechat_qr()

        # QR size tracking for future alternative detection methods
        self.expected_mvd_qr_size = None  # {"width": 57, "height": 58}
        self.expected_trigger_qr_size = None  # {"width": 176, "height": 181}
        self.current_camera = None

    def setup_logging(self):
        self.logger = get_logger(__name__, {})
        self.logger.info("Logging initialized")

    def setup_wechat_qr(self):
        for model_file in [DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL]:
            if not os.path.exists(model_file):
                self.logger.error(f"Model file not found: {model_file}")
                raise FileNotFoundError(f"Model file not found: {model_file}")
        try:
            # Using pattern from qr_detector.py with proper error handling
            self.qr_detector = cv2.wechat_qrcode_WeChatQRCode(DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL)  # type: ignore
            self.logger.info("WeChat QRCode detector initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize WeChat QRCode: {str(e)}")
            self.qr_detector = None

    def load_config(self):
        self.logger.info("Loading configuration from database")
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                self.video_root = result[0] if result else os.path.join(BASE_DIR, "Inputvideo")
                cursor.execute("SELECT output_path FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                self.output_path = result[0] if result else os.path.join(BASE_DIR, "output_clips")
                # Use var/logs for frame processing logs (application-managed)
                from modules.path_utils import get_logs_dir

                self.log_dir = os.path.join(get_logs_dir(), "frame_processing")
                os.makedirs(self.log_dir, exist_ok=True)
                # Use zoneinfo for user timezone instead of hardcoded parsing
                from modules.utils.simple_timezone import get_system_timezone_from_db

                system_tz_str = get_system_timezone_from_db()
                self.video_timezone = ZoneInfo(system_tz_str)
                self.logger.info(f"Using system timezone from config: {system_tz_str}")
                cursor.execute(
                    "SELECT frame_rate, frame_interval, min_packing_time FROM processing_config WHERE id = 1"
                )
                result = cursor.fetchone()
                self.fps, self.frame_interval, self.min_packing_time = (
                    result if result else (30, 5, 5)
                )
            self.logger.info(
                f"Config loaded: video_root={self.video_root}, output_path={self.output_path}, timezone={self.video_timezone}, fps={self.fps}, frame_interval={self.frame_interval}, min_packing_time={self.min_packing_time}"
            )

    def get_packing_area(self, camera_name):
        """Get 2 ROI areas for QR trigger method.

        Returns:
            tuple: (packing_area, qr_trigger_area)
                - packing_area: Main ROI for MVD detection (4-tuple: x,y,w,h)
                - qr_trigger_area: Small ROI for TimeGo QR trigger (4-tuple: x,y,w,h)
        """
        self.logger.info(f"Querying packing_area and qr_trigger_area for camera {camera_name}")
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT packing_area, qr_trigger_area, jump_time_ratio
                    FROM packing_profiles
                    WHERE profile_name = ?
                """,
                    (camera_name,),
                )
                result = cursor.fetchone()

        if not result:
            self.logger.warning(f"No profile found for camera {camera_name}")
            return None, None

        # Parse packing_area (main detection ROI - both Traditional & QR use this)
        packing_area_raw, qr_trigger_raw, jump_ratio = result

        # Note: jump_time_ratio is no longer used (jump logic removed for safety)
        # Kept here to avoid breaking database queries

        # Parse packing_area ROI
        packing_area = self._parse_roi(packing_area_raw, "packing_area", camera_name)

        # Parse qr_trigger_area ROI (QR method only)
        qr_trigger_area = self._parse_roi(qr_trigger_raw, "qr_trigger_area", camera_name)

        self.logger.info(
            f"Loaded ROIs: packing_area={packing_area}, qr_trigger_area={qr_trigger_area}"
        )

        return packing_area, qr_trigger_area

    def _parse_roi(self, roi_raw, field_name, camera_name):
        """Parse ROI from JSON string to (x,y,w,h) tuple.

        Database format: [x, y, width, height] - standard ROI format
        Returns: (x, y, w, h) - top-left corner and width/height
        """
        if not roi_raw:
            return None

        try:
            # Handle tuple string format: "(x,y,w,h)"
            if isinstance(roi_raw, str) and roi_raw.startswith("(") and roi_raw.endswith(")"):
                x, y, w, h = map(int, roi_raw.strip("()").split(","))
                return (x, y, w, h)

            # Handle JSON formats
            parsed = json.loads(roi_raw) if isinstance(roi_raw, str) else roi_raw

            # JSON array: [x, y, width, height] - standard format
            if isinstance(parsed, list) and len(parsed) == 4:
                x, y, w, h = parsed
                return (x, y, w, h)

            # JSON object: {"x": x, "y": y, "w": w, "h": h}
            if isinstance(parsed, dict):
                return (
                    parsed.get("x", 0),
                    parsed.get("y", 0),
                    parsed.get("w", 0),
                    parsed.get("h", 0),
                )

            self.logger.error(f"Invalid {field_name} format for {camera_name}: {roi_raw}")
            return None

        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error(f"Error parsing {field_name} for {camera_name}: {str(e)}")
            return None

    def _load_qr_sizes(self, camera_name):
        """Load expected QR sizes from database for size-based filtering.

        Loads expected MVD and TimeGo QR sizes from packing_profiles table.
        These sizes are used to filter TimeGo boundaries from MVD boundaries.

        Args:
            camera_name: Camera profile name to load sizes for
        """
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT expected_mvd_qr_size, expected_trigger_qr_size
                    FROM packing_profiles WHERE profile_name = ?
                """,
                    (camera_name,),
                )
                result = cursor.fetchone()

                if result:
                    self.expected_mvd_qr_size = json.loads(result[0]) if result[0] else None
                    self.expected_trigger_qr_size = json.loads(result[1]) if result[1] else None
                    self.logger.info(
                        f"📊 Loaded QR sizes for {camera_name}: "
                        f"MVD={self.expected_mvd_qr_size}, TimeGo={self.expected_trigger_qr_size}"
                    )
                else:
                    self.expected_mvd_qr_size = None
                    self.expected_trigger_qr_size = None
                    self.logger.warning(
                        f"⚠️ No QR sizes found for {camera_name}, using fallback 100px threshold"
                    )

    def _is_mvd_size(self, bbox):
        """Check if bbox size matches MVD QR (not TimeGo).

        Uses expected QR sizes from database if available, otherwise falls back
        to simple 100px threshold.

        Args:
            bbox: Bounding box [x, y, w, h]

        Returns:
            bool: True if MVD-sized, False if TimeGo-sized
        """
        w, h = bbox[2], bbox[3]

        # If we have expected sizes from database, use them with distance comparison
        if self.expected_mvd_qr_size and self.expected_trigger_qr_size:
            mvd_w = self.expected_mvd_qr_size["width"]
            mvd_h = self.expected_mvd_qr_size["height"]
            trigger_w = self.expected_trigger_qr_size["width"]
            trigger_h = self.expected_trigger_qr_size["height"]

            # Calculate Manhattan distance to MVD and TimeGo sizes
            mvd_diff = abs(w - mvd_w) + abs(h - mvd_h)
            trigger_diff = abs(w - trigger_w) + abs(h - trigger_h)

            # Accept if closer to MVD than TimeGo
            is_mvd = mvd_diff < trigger_diff
            self.logger.debug(
                f"Size check: {w}x{h}, MVD_diff={mvd_diff}, TimeGo_diff={trigger_diff}, is_MVD={is_mvd}"
            )
            return is_mvd

        # Fallback: Use simple 100px threshold if no DB data
        is_mvd = w < 100 and h < 100
        self.logger.debug(f"Size check (fallback): {w}x{h}, is_MVD={is_mvd}")
        return is_mvd

    def _update_mvd_qr_size(self, mvd_bbox):
        """Auto-update expected MVD QR size from successful decode (Last Known Good pattern).

        Updates database with new MVD QR size if it changed significantly (>10%)
        from the current expected size. This allows system to adapt when labels change.

        Args:
            mvd_bbox: Tuple (x, y, w, h) from successful MVD decode
        """
        if not self.current_camera:
            return

        new_size = {"width": mvd_bbox[2], "height": mvd_bbox[3]}

        # Only update if size changed significantly (>10%)
        if self.expected_mvd_qr_size:
            old_w = self.expected_mvd_qr_size["width"]
            change_ratio = abs(new_size["width"] - old_w) / old_w
            if change_ratio < 0.1:
                return  # Change too small, ignore

        # Update database
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE packing_profiles
                    SET expected_mvd_qr_size = ?
                    WHERE profile_name = ?
                """,
                    (json.dumps(new_size), self.current_camera),
                )
                conn.commit()

        self.expected_mvd_qr_size = new_size
        self.logger.info(
            f"📊 Auto-updated MVD QR size: {new_size} for camera {self.current_camera}"
        )

    def get_video_duration(self, video_file):
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
            self.logger.error(f"Failed to get duration of video {video_file}")
            return None

    def load_video_files(self):
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                # Exclude files that failed health checks (status='health_check_failed')
                cursor.execute(
                    """
                    SELECT file_path FROM file_list
                    WHERE is_processed = 0
                    AND status NOT IN ('completed', 'health_check_failed')
                    ORDER BY priority DESC, created_at ASC
                """
                )
                video_files = [row[0] for row in cursor.fetchall()]
        if not video_files:
            self.logger.info("No video files found (excluding completed and health_check_failed).")
        return video_files

    def process_frame(self, frame_packing, frame_trigger, frame_count, packing_area_offset=None):
        """Process 2 separate frames for MVD and TimeGo detection.

        Args:
            frame_packing: Frame cropped by packing_area ROI (for MVD detection)
            frame_trigger: Frame cropped by qr_trigger_area ROI (for TimeGo detection)
            frame_count: Current frame number
            packing_area_offset: Tuple (x, y) offset of packing_area in full frame (for bbox calculation)

        Returns:
            tuple: (state, mvd, mvd_bbox, packing_points)
                - state: "On" if TimeGo detected in trigger area, else "Off"
                - mvd: Mã vận đơn detected in packing area (empty string if none)
                - mvd_bbox: Bounding box (x, y, w, h) in full-frame coordinates, or None
                - packing_points: QR boundary points for empty event processing
        """
        try:
            if self.qr_detector is None:
                return "Off", "", None, None

            state = "Off"
            mvd = ""
            mvd_bbox = None
            boundary_points = None

            # Detect TimeGo in trigger area (if provided)
            if frame_trigger is not None and frame_trigger.size > 0:
                if len(frame_trigger.shape) == 2:
                    frame_trigger = cv2.cvtColor(frame_trigger, cv2.COLOR_GRAY2BGR)

                trigger_texts, _ = self.qr_detector.detectAndDecode(frame_trigger)
                for text in trigger_texts:
                    if text == "TimeGo":
                        state = "On"
                        break

            # Detect MVD in packing area (if provided)
            if frame_packing is not None and frame_packing.size > 0:
                if len(frame_packing.shape) == 2:
                    frame_packing = cv2.cvtColor(frame_packing, cv2.COLOR_GRAY2BGR)

                packing_texts, packing_points = self.qr_detector.detectAndDecode(frame_packing)

                # Track MVD index for boundary points
                mvd_index = None
                non_timego_index = None  # Track first non-TimeGo QR (even if decode failed)

                # DEBUG: Log all detected QR codes
                if len(packing_texts) > 0:
                    self.logger.debug(
                        f"Frame {frame_count}: Detected {len(packing_texts)} QR codes, texts={packing_texts}"
                    )

                # Process each detected QR code
                for i, text in enumerate(packing_texts):
                    # Skip TimeGo if found in packing area (should be in trigger area)
                    if text == "TimeGo":
                        continue  # Skip TimeGo, check next QR

                    # Track first non-TimeGo QR (even if text is empty = decode failed)
                    if non_timego_index is None:
                        non_timego_index = i

                    # If text successfully decoded (not empty string)
                    if text:
                        mvd = text
                        mvd_index = i  # Track index for boundary points

                        # Calculate bounding box if points available and offset provided
                        if i < len(packing_points) and packing_area_offset is not None:
                            box = packing_points[i]
                            if len(box) >= 4:
                                # Extract x, y coordinates from 4 corner points
                                x_coords = [int(pt[0]) for pt in box]
                                y_coords = [int(pt[1]) for pt in box]

                                # Calculate bbox in ROI-local coordinates
                                bbox_x_local = min(x_coords)
                                bbox_y_local = min(y_coords)
                                bbox_w = max(x_coords) - bbox_x_local
                                bbox_h = max(y_coords) - bbox_y_local

                                # Convert to full-frame coordinates by adding packing_area offset
                                offset_x, offset_y = packing_area_offset
                                mvd_bbox = (
                                    bbox_x_local + offset_x,
                                    bbox_y_local + offset_y,
                                    bbox_w,
                                    bbox_h,
                                )

                                self.logger.debug(
                                    f"QR bbox calculated: local=({bbox_x_local},{bbox_y_local},{bbox_w},{bbox_h}), "
                                    f"offset=({offset_x},{offset_y}), full={mvd_bbox}"
                                )
                        break  # Found decoded MVD, stop searching

                # Return boundary points for empty event processing
                # Priority: MVD decoded > MVD detected but not decoded
                # PERFORMANCE OPTIMIZATION: Size filtering moved to _log_boundary()
                if len(packing_points) > 0 and packing_area_offset is not None:
                    if mvd_index is not None:
                        # MVD decoded successfully → use its boundary
                        boundary_points = packing_points[mvd_index]
                        self.logger.debug(
                            f"Frame {frame_count}: Using MVD boundary (mvd_index={mvd_index})"
                        )
                    elif non_timego_index is not None:
                        # MVD detected but decode failed → use non-TimeGo boundary
                        boundary_points = packing_points[non_timego_index]
                        self.logger.debug(
                            f"Frame {frame_count}: Using non-TimeGo boundary (non_timego_index={non_timego_index}, decode failed)"
                        )
                    else:
                        self.logger.debug(
                            f"Frame {frame_count}: Only TimeGo detected, skipping boundary"
                        )
                    # else: Only TimeGo detected → boundary_points stays None (skip)

            return state, mvd, mvd_bbox, boundary_points

        except Exception as e:
            self.logger.error(f"Error processing frame {frame_count}: {str(e)}")
            return "Off", "", None, None

    def _get_video_start_time(self, video_file, camera_name=None):
        """Get video start time from metadata (ffprobe/exiftool).

        Priority:
        1. ffprobe: Read creation_time from video metadata (most accurate)
        2. exiftool: Fallback for special video formats
        3. ctime: Last resort - filesystem creation time

        Args:
            video_file (str): Path to video file
            camera_name (str, optional): Camera name for timezone detection

        Returns:
            datetime: Timezone-aware video start time
        """
        try:
            # Primary: Read metadata using ffprobe
            result = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_entries",
                    "format_tags=creation_time",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    video_file,
                ]
            )
            utc_time = datetime.strptime(result.decode().strip(), "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            )
            local_time = utc_time.astimezone(self.video_timezone)
            self.logger.info(f"Video start time from metadata: {local_time}")
            return local_time
        except (subprocess.CalledProcessError, ValueError) as e:
            self.logger.warning(f"ffprobe failed for {video_file}: {e}, trying exiftool")

            # Fallback 1: exiftool CreateDate
            try:
                result = subprocess.check_output(
                    ["exiftool", "-CreateDate", "-d", "%Y-%m-%d %H:%M:%S", video_file]
                )
                naive_time = datetime.strptime(
                    result.decode().split("CreateDate")[1].strip().split("\n")[0].strip(),
                    "%Y-%m-%d %H:%M:%S",
                )
                local_time = naive_time.replace(tzinfo=self.video_timezone)
                self.logger.info(f"Video start time from exiftool CreateDate: {local_time}")
                return local_time
            except (subprocess.CalledProcessError, IndexError) as e:
                self.logger.warning(f"exiftool CreateDate failed: {e}, trying FileCreateDate")

                # Fallback 2: exiftool FileCreateDate
                try:
                    result = subprocess.check_output(
                        ["exiftool", "-FileCreateDate", "-d", "%Y-%m-%d %H:%M:%S", video_file]
                    )
                    naive_time = datetime.strptime(
                        result.decode().split("FileCreateDate")[1].strip().split("\n")[0].strip(),
                        "%Y-%m-%d %H:%M:%S",
                    )
                    local_time = naive_time.replace(tzinfo=self.video_timezone)
                    self.logger.info(f"Video start time from exiftool FileCreateDate: {local_time}")
                    return local_time
                except (subprocess.CalledProcessError, IndexError) as e:
                    # Last resort: filesystem ctime
                    import os

                    self.logger.warning(f"All metadata methods failed: {e}, using filesystem ctime")
                    file_timestamp = os.path.getctime(video_file)
                    local_time = datetime.fromtimestamp(file_timestamp, tz=self.video_timezone)
                    self.logger.info(f"Video start time from ctime (last resort): {local_time}")
                    return local_time

    def _get_log_directory(self, video_file, camera_name):
        """Get log directory based on program type from database.

        Args:
            video_file: Path to video file
            camera_name: Camera name for folder fallback

        Returns:
            str: Log directory path (custom/ for custom mode, camera_name/ for others)
        """
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT program_type FROM file_list WHERE file_path = ?", (video_file,)
                )
                result = cursor.fetchone()
                program_type = result[0] if result and result[0] else "default"

        if program_type == "custom":
            # Custom mode: Use "custom" folder
            return os.path.join(self.log_dir, "custom")
        else:
            # First Run & Default: Use camera name folder
            return os.path.join(self.log_dir, camera_name)

    def _update_log_file(
        self, log_file, start_second, end_second, start_time, camera_name, video_file
    ):
        log_file_handle = open(log_file, "w")
        log_file_handle.write(
            f"# Start: {start_second}, End: {end_second}, Start_Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}, Camera_Name: {camera_name}, Video_File: {video_file}\n"
        )
        log_file_handle.flush()
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM processed_logs WHERE log_file = ?", (log_file,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO processed_logs (log_file, is_processed) VALUES (?, 0)",
                        (log_file,),
                    )
        return log_file_handle

    # ============== EMPTY EVENT PROCESSING METHODS ==============

    # ============== EMPTY EVENT PROCESSING METHODS (REMOVED) ==============
    # Methods _calculate_bbox_from_points, _should_buffer_boundary,
    # _process_empty_event, and _log_boundary were removed because they were
    # based on incorrect assumption that WeChat QR detectAndDecode() returns
    # boundary points when decode fails. In reality, if decode fails, both
    # texts and points are empty.
    #
    # For future Empty Event detection, implement alternative detection methods
    # (template matching, edge detection, etc.) using expected_qr_size data.
    # ============== END REMOVED SECTION ==============

    def run(self):
        while True:
            frame_sampler_event.wait()
            video_files = self.load_video_files()
            if not video_files:
                self.logger.info("No videos to process")
                frame_sampler_event.clear()
                continue
            for video_file in video_files:
                log_file = self.process_video(
                    video_file,
                    self.video_lock,
                    self.get_packing_area,
                    self.process_frame,
                    self.frame_interval,
                )
                if log_file:
                    self.logger.info(f"Completed processing video {video_file}, log at {log_file}")
                else:
                    self.logger.error(f"Failed to process video {video_file}")
            frame_sampler_event.clear()

    def process_video(
        self,
        video_file,
        video_lock,
        get_packing_area_func,
        process_frame_func,
        frame_interval,
        start_time=0,
        end_time=None,
    ):
        with video_lock:
            self.logger.info(f"Processing video: {video_file} from {start_time}s to {end_time}s")

            # Safety check: Skip if this file already failed health check
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT health_check_failed, status FROM file_list WHERE file_path = ?",
                        (video_file,),
                    )
                    result = cursor.fetchone()
                    if result:
                        health_check_failed, status = result
                        if health_check_failed == 1 or status == "health_check_failed":
                            self.logger.error(
                                f"[HEALTH] Skipping {video_file} - already marked as health_check_failed"
                            )
                            return None

            if not os.path.exists(video_file):
                self.logger.error(f"File '{video_file}' does not exist")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE file_list SET status = ? WHERE file_path = ?",
                            ("error", video_file),
                        )
                return None
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE file_list SET status = ? WHERE file_path = ?",
                        ("frame sampling...", video_file),
                    )
                    cursor.execute(
                        "SELECT camera_name FROM file_list WHERE file_path = ?", (video_file,)
                    )
                    result = cursor.fetchone()
                    camera_name = result[0] if result and result[0] else "CamTest"

            # Load QR sizes if camera changed (for size-based filtering)
            if camera_name != self.current_camera:
                self._load_qr_sizes(camera_name)
                self.current_camera = camera_name

            # ========== HEALTH CHECK AT START OF PROCESS_VIDEO ==========
            # Read health check metadata (set by file_lister)
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT health_check_message, health_check_failed FROM file_list WHERE file_path = ?",
                        (video_file,),
                    )
                    result = cursor.fetchone()
                    health_metadata_json = result[0] if result else "{}"
                    health_check_failed = result[1] if result else 0

            # Parse health metadata
            try:
                health_metadata = json.loads(health_metadata_json) if health_metadata_json else {}
            except json.JSONDecodeError:
                health_metadata = {}

            # If health check is required and not yet done, execute it now
            if health_metadata.get("health_check_required") and not health_metadata.get(
                "health_check_done"
            ):
                self.logger.info(f"[HEALTH] Executing health check for {camera_name}")

                # Run health check (new function handles baseline lookup, first TimeGo detection, and UPDATE logic)
                health_result = run_health_check(camera_name=camera_name, video_path=video_file)

                if health_result.get("success"):
                    # Update health metadata with result
                    health_metadata.update(
                        {
                            "health_check_done": True,
                            "health_check_status": health_result.get("status"),
                            "health_check_metrics": health_result.get("metrics"),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                else:
                    # Health check failed or skipped (no baseline)
                    self.logger.warning(
                        f"[HEALTH] ⚠️ Health check skipped for {camera_name}: {health_result.get('error')}"
                    )
                    health_metadata.update(
                        {
                            "health_check_done": False,
                            "health_check_error": health_result.get("error"),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                if health_result.get("success"):

                    # Handle health check result
                    if health_result.get("status") == "CRITICAL":
                        # CRITICAL (<70%) → PAUSE processing
                        self.logger.error(
                            f"[HEALTH] 🛑 CRITICAL - Pausing processing for {camera_name}"
                        )
                        metrics = health_result.get("metrics", {})
                        self.logger.error(
                            f"[HEALTH] QR degradation: {metrics.get('qr_readable', {}).get('degradation_pct', 'N/A')}%"
                        )

                        # Update file_list with health_check_failed=1 and mark as blocked (health_check_failed)
                        # Mark as is_processed=1 to prevent re-queueing, but use special status to indicate health failure
                        with db_rwlock.gen_wlock():
                            with safe_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    UPDATE file_list
                                    SET health_check_failed = 1,
                                        health_check_message = ?,
                                        is_processed = 0,
                                        status = 'health_check_failed'
                                    WHERE file_path = ?
                                """,
                                    (json.dumps(health_metadata), video_file),
                                )
                                conn.commit()

                        # STOP processing this video
                        self.logger.error(
                            f"[HEALTH] Skipping video {video_file} due to CRITICAL health check"
                        )
                        return None

                    elif health_result.get("status") == "CAUTION":
                        # CAUTION (70-84%) → Warning + Continue
                        metrics = health_result.get("metrics", {})
                        self.logger.warning(
                            f"[HEALTH] ⚠️ CAUTION - QR degradation: {metrics.get('qr_readable', {}).get('degradation_pct', 'N/A')}%"
                        )

                        # Mark health check done but keep health_check_failed=0
                        with db_rwlock.gen_wlock():
                            with safe_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    UPDATE file_list
                                    SET health_check_failed = 0,
                                        health_check_message = ?
                                    WHERE file_path = ?
                                """,
                                    (json.dumps(health_metadata), video_file),
                                )
                                conn.commit()

                    elif health_result.get("status") == "OK":
                        # OK (≥85%) → Continue normally
                        self.logger.info(f"[HEALTH] ✅ Camera health OK - no degradation detected")

                        # Mark health check done, health_check_failed=0
                        with db_rwlock.gen_wlock():
                            with safe_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    UPDATE file_list
                                    SET health_check_failed = 0,
                                        health_check_message = ?
                                    WHERE file_path = ?
                                """,
                                    (json.dumps(health_metadata), video_file),
                                )
                                conn.commit()

                else:
                    # No TimeGo found - skip health check, continue processing
                    self.logger.warning(
                        f"[HEALTH] No TimeGo found - skipping health check, continuing processing"
                    )
                    health_metadata["health_check_done"] = True
                    health_metadata["health_check_status"] = "SKIPPED"
                    health_metadata["health_check_message"] = "No TimeGo detected"

                    with db_rwlock.gen_wlock():
                        with safe_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                UPDATE file_list
                                SET health_check_failed = 0,
                                    health_check_message = ?
                                WHERE file_path = ?
                            """,
                                (json.dumps(health_metadata), video_file),
                            )
                            conn.commit()

            # ========== END HEALTH CHECK ==========

            video = cv2.VideoCapture(video_file)
            if not video.isOpened():
                self.logger.error(f"Failed to open video '{video_file}'")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE file_list SET status = ? WHERE file_path = ?",
                            ("error", video_file),
                        )
            start_time_obj = self._get_video_start_time(video_file, camera_name)
            packing_area, qr_trigger_area = get_packing_area_func(camera_name)
            total_seconds = self.get_video_duration(video_file)
            if total_seconds is None:
                self.logger.error(f"Failed to get duration of video {video_file}")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE file_list SET status = ? WHERE file_path = ?",
                            ("error", video_file),
                        )
                return None
            self.logger.info(f"Video duration {video_file}: {total_seconds} seconds")
            video_name = os.path.splitext(os.path.basename(video_file))[0]
            segment_duration = 300
            # Determine 300s segments containing [start_time, end_time]
            end_time = total_seconds if end_time is None else min(end_time, total_seconds)
            start_segment = math.floor(start_time / segment_duration) * segment_duration
            end_segment = math.ceil(end_time / segment_duration) * segment_duration
            current_start_second = start_segment
            current_end_second = min(current_start_second + segment_duration, end_segment)

            # Get log directory based on program type
            camera_log_dir = self._get_log_directory(video_file, camera_name)
            os.makedirs(camera_log_dir, exist_ok=True)
            log_file = os.path.join(
                camera_log_dir,
                f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt",
            )
            log_file_handle = self._update_log_file(
                log_file,
                current_start_second,
                current_end_second,
                start_time_obj + timedelta(seconds=current_start_second),
                camera_name,
                video_file,
            )
            # Start from frame at start_time
            start_frame = int(start_time * self.fps)
            end_frame = int(end_time * self.fps)
            video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frame_count = start_frame
            frame_states = []
            mvd_list = []
            last_state = None
            last_mvd = ""
            # Jump logic removed - no longer needed
            while video.isOpened() and frame_count < end_frame:
                ret, frame = video.read()
                if not ret:
                    break

                # Store original frame for dual cropping
                original_frame = frame.copy()

                # Crop 2 separate regions
                frame_packing = None
                frame_trigger = None
                packing_offset = None

                # Crop packing area (for MVD detection)
                if packing_area:
                    x, y, w, h = packing_area
                    frame_height, frame_width = original_frame.shape[:2]
                    if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                        frame_packing = original_frame[y : y + h, x : x + w]
                        packing_offset = (x, y)  # Store offset for bbox calculation
                    else:
                        self.logger.warning(
                            f"Invalid packing_area for frame {frame_count}: {packing_area}, frame size: {frame_width}x{frame_height}"
                        )

                # Crop trigger area (for TimeGo detection)
                if qr_trigger_area:
                    x, y, w, h = qr_trigger_area
                    frame_height, frame_width = original_frame.shape[:2]
                    if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                        frame_trigger = original_frame[y : y + h, x : x + w]
                    else:
                        self.logger.warning(
                            f"Invalid qr_trigger_area for frame {frame_count}: {qr_trigger_area}, frame size: {frame_width}x{frame_height}"
                        )

                frame_count += 1
                if frame_count % frame_interval != 0:
                    continue
                if (frame_packing is None or frame_packing.size == 0) and (
                    frame_trigger is None or frame_trigger.size == 0
                ):
                    self.logger.warning(f"Both ROI frames empty for frame {frame_count}, skipping")
                    continue

                # Process both ROIs separately (with packing_offset for bbox calculation)
                state, mvd, mvd_bbox, boundary_points = process_frame_func(
                    frame_packing, frame_trigger, frame_count, packing_offset
                )
                second_in_video = (frame_count - 1) / self.fps
                second = round(second_in_video)

                # Cache successful bbox and update QR size
                if mvd and mvd_bbox:
                    self._update_mvd_qr_size(mvd_bbox)  # Auto-update QR size from successful decode
                if second >= current_end_second and second < end_time:
                    log_file_handle.close()
                    current_start_second = current_end_second
                    current_end_second = min(current_start_second + segment_duration, end_segment)

                    # Get log directory based on program type
                    camera_log_dir = self._get_log_directory(video_file, camera_name)
                    os.makedirs(camera_log_dir, exist_ok=True)
                    log_file = os.path.join(
                        camera_log_dir,
                        f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt",
                    )
                    log_file_handle = self._update_log_file(
                        log_file,
                        current_start_second,
                        current_end_second,
                        start_time_obj + timedelta(seconds=current_start_second),
                        camera_name,
                        video_file,
                    )
                if second >= start_time and second <= end_time:
                    # Ghi MVD ngay nếu có và khác last_mvd
                    if mvd and mvd != last_mvd:
                        # Format log line with bbox if available
                        if mvd_bbox is not None:
                            bbox_x, bbox_y, bbox_w, bbox_h = mvd_bbox
                            log_line = f"{second},{state},{mvd},bbox:[{bbox_x},{bbox_y},{bbox_w},{bbox_h}]\n"
                            self.logger.info(
                                f"Log second {second}: state={state}, mvd={mvd}, bbox={mvd_bbox}"
                            )
                        else:
                            log_line = f"{second},{state},{mvd}\n"
                            self.logger.info(f"Log second {second}: state={state}, mvd={mvd}")

                        log_file_handle.write(log_line)
                        log_file_handle.flush()
                        last_mvd = mvd
                    # Tiếp tục thu thập trạng thái cho final_state
                    frame_states.append(state)
                    mvd_list.append(mvd)
                    if len(frame_states) == 5:
                        on_count = sum(1 for s in frame_states if s == "On")
                        off_count = sum(1 for s in frame_states if s == "Off")
                        frame_states_str = " ".join(frame_states).lower()
                        final_state = None
                        if on_count >= 3:
                            final_state = "On"
                        elif off_count == 5:
                            final_state = "Off"
                        if final_state:
                            if final_state != last_state:
                                # Detect Ts and Te transitions (kept for future use)
                                if final_state == "Off":
                                    self.logger.debug(f"Event transition: Ts at second {second}")
                                elif final_state == "On":
                                    self.logger.debug(f"Event transition: Te at second {second}")

                                log_line = f"{second},{final_state},\n"
                                log_file_handle.write(log_line)
                                self.logger.info(
                                    f"Log second {second}: {frame_states_str}: {final_state}"
                                )
                                log_file_handle.flush()
                                # Jump logic removed for safety - scan all frames sequentially
                                last_state = final_state
                        else:
                            self.logger.info(
                                f"Skipped second {second}: {frame_states_str}, on_count={on_count}, off_count={off_count}"
                            )
                            log_file_handle.flush()
                        frame_states = []
                        mvd_list = []
            log_file_handle.close()
            video.release()
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE file_list SET is_processed = 1, status = ? WHERE file_path = ?",
                        ("completed", video_file),
                    )
            self.logger.info(f"Completed processing video: {video_file}")
            return log_file
