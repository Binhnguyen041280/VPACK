import cv2
import os
import logging
import sqlite3
import threading
import subprocess
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import frame_sampler_event, db_rwlock
from zoneinfo import ZoneInfo
# Removed video_timezone_detector - using simple timezone operations
import math
from modules.config.logging_config import get_logger


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models", "wechat_qr")
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
                cursor.execute("SELECT frame_rate, frame_interval, min_packing_time FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                self.fps, self.frame_interval, self.min_packing_time = result if result else (30, 5, 5)
            self.logger.info(f"Config loaded: video_root={self.video_root}, output_path={self.output_path}, timezone={self.video_timezone}, fps={self.fps}, frame_interval={self.frame_interval}, min_packing_time={self.min_packing_time}")

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
                cursor.execute("""
                    SELECT packing_area, qr_trigger_area, jump_time_ratio
                    FROM packing_profiles
                    WHERE profile_name = ?
                """, (camera_name,))
                result = cursor.fetchone()

        if not result:
            self.logger.warning(f"No profile found for camera {camera_name}")
            return None, None

        # Parse packing_area (main detection ROI - both Traditional & QR use this)
        packing_area_raw, qr_trigger_raw, jump_ratio = result

        # Set jump_time_ratio
        self.jump_time_ratio = float(jump_ratio) if jump_ratio is not None else 0.5
        self.logger.info(f"Loaded jump_time_ratio: {self.jump_time_ratio}")

        # Parse packing_area ROI
        packing_area = self._parse_roi(packing_area_raw, "packing_area", camera_name)

        # Parse qr_trigger_area ROI (QR method only)
        qr_trigger_area = self._parse_roi(qr_trigger_raw, "qr_trigger_area", camera_name)

        self.logger.info(f"Loaded ROIs: packing_area={packing_area}, qr_trigger_area={qr_trigger_area}")

        return packing_area, qr_trigger_area

    def _parse_roi(self, roi_raw, field_name, camera_name):
        """Parse ROI from JSON string to (x,y,w,h) tuple."""
        if not roi_raw:
            return None

        try:
            # Handle tuple string format: "(x,y,w,h)"
            if isinstance(roi_raw, str) and roi_raw.startswith('(') and roi_raw.endswith(')'):
                x, y, w, h = map(int, roi_raw.strip('()').split(','))
                return (x, y, w, h)

            # Handle JSON formats
            parsed = json.loads(roi_raw) if isinstance(roi_raw, str) else roi_raw

            # JSON array: [x, y, w, h]
            if isinstance(parsed, list) and len(parsed) == 4:
                return tuple(parsed)

            # JSON object: {"x": x, "y": y, "w": w, "h": h}
            if isinstance(parsed, dict):
                return (parsed.get('x', 0), parsed.get('y', 0),
                       parsed.get('w', 0), parsed.get('h', 0))

            self.logger.error(f"Invalid {field_name} format for {camera_name}: {roi_raw}")
            return None

        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error(f"Error parsing {field_name} for {camera_name}: {str(e)}")
            return None

    def get_video_duration(self, video_file):
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(result.stdout.strip())
        except Exception:
            self.logger.error(f"Failed to get duration of video {video_file}")
            return None

    def load_video_files(self):
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM file_list WHERE is_processed = 0 AND status != 'completed' ORDER BY priority DESC, created_at ASC")
                video_files = [row[0] for row in cursor.fetchall()]
        if not video_files:
            self.logger.info("No video files found with is_processed = 0 and status != 'completed'.")
        return video_files

    def process_frame(self, frame_packing, frame_trigger, frame_count):
        """Process 2 separate frames for MVD and TimeGo detection.

        Args:
            frame_packing: Frame cropped by packing_area ROI (for MVD detection)
            frame_trigger: Frame cropped by qr_trigger_area ROI (for TimeGo detection)
            frame_count: Current frame number

        Returns:
            tuple: (state, mvd)
                - state: "On" if TimeGo detected in trigger area, else "Off"
                - mvd: Mã vận đơn detected in packing area (empty string if none)
        """
        try:
            if self.qr_detector is None:
                return "Off", ""

            state = "Off"
            mvd = ""

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

                packing_texts, _ = self.qr_detector.detectAndDecode(frame_packing)
                for text in packing_texts:
                    # Skip TimeGo if found in packing area (should be in trigger area)
                    if text and text != "TimeGo":
                        mvd = text
                        break

            return state, mvd

        except Exception as e:
            self.logger.error(f"Error processing frame {frame_count}: {str(e)}")
            return "Off", ""

    def _get_video_start_time(self, video_file, camera_name=None):
        """Get video start time with advanced timezone detection.
        
        Uses enhanced video timezone detection to get accurate creation time
        with proper timezone information from metadata when available.
        
        Args:
            video_file (str): Path to video file
            camera_name (str, optional): Camera name for timezone detection
            
        Returns:
            datetime: Timezone-aware video start time
        """
        try:
            # Use enhanced timezone detection with camera context
            # Simple timezone-aware creation time using file system timestamp
            import os
            file_timestamp = os.path.getctime(video_file)
            timezone_aware_time = datetime.fromtimestamp(file_timestamp, tz=self.video_timezone)
            self.logger.info(f"Video start time with timezone detection: {timezone_aware_time}")
            return timezone_aware_time
            
        except Exception as e:
            self.logger.warning(f"Enhanced timezone detection failed for {video_file}: {e}, using fallback")
            
            # Fallback to original method with TimezoneManager
            try:
                result = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags=creation_time', '-of', 'default=noprint_wrappers=1:nokey=1', video_file])
                utc_time = datetime.strptime(result.decode().strip(), '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                return utc_time.astimezone(self.video_timezone)
            except (subprocess.CalledProcessError, ValueError):
                try:
                    result = subprocess.check_output(['exiftool', '-CreateDate', '-d', '%Y-%m-%d %H:%M:%S', video_file])
                    naive_time = datetime.strptime(result.decode().split('CreateDate')[1].strip().split('\n')[0].strip(), '%Y-%m-%d %H:%M:%S')
                    return naive_time.replace(tzinfo=self.video_timezone)
                except (subprocess.CalledProcessError, IndexError):
                    try:
                        result = subprocess.check_output(['exiftool', '-FileCreateDate', '-d', '%Y-%m-%d %H:%M:%S', video_file])
                        naive_time = datetime.strptime(result.decode().split('FileCreateDate')[1].strip().split('\n')[0].strip(), '%Y-%m-%d %H:%M:%S')
                        return naive_time.replace(tzinfo=self.video_timezone)
                    except (subprocess.CalledProcessError, IndexError):
                        self.logger.warning("No metadata found, using file creation time.")
                        return datetime.fromtimestamp(os.path.getctime(video_file), tz=self.video_timezone)

    def _update_log_file(self, log_file, start_second, end_second, start_time, camera_name, video_file):
        log_file_handle = open(log_file, 'w')
        log_file_handle.write(f"# Start: {start_second}, End: {end_second}, Start_Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}, Camera_Name: {camera_name}, Video_File: {video_file}\n")
        log_file_handle.flush()
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM processed_logs WHERE log_file = ?", (log_file,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO processed_logs (log_file, is_processed) VALUES (?, 0)", (log_file,))
        return log_file_handle

    def run(self):
        while True:
            frame_sampler_event.wait()
            video_files = self.load_video_files()
            if not video_files:
                self.logger.info("No videos to process")
                frame_sampler_event.clear()
                continue
            for video_file in video_files:
                log_file = self.process_video(video_file, self.video_lock, self.get_packing_area, self.process_frame, self.frame_interval)
                if log_file:
                    self.logger.info(f"Completed processing video {video_file}, log at {log_file}")
                else:
                    self.logger.error(f"Failed to process video {video_file}")
            frame_sampler_event.clear()

    def process_video(self, video_file, video_lock, get_packing_area_func, process_frame_func, frame_interval, start_time=0, end_time=None):
        with video_lock:
            self.logger.info(f"Processing video: {video_file} from {start_time}s to {end_time}s")
            if not os.path.exists(video_file):
                self.logger.error(f"File '{video_file}' does not exist")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("error", video_file))
                return None
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("frame sampling...", video_file))
                    cursor.execute("SELECT camera_name FROM file_list WHERE file_path = ?", (video_file,))
                    result = cursor.fetchone()
                    camera_name = result[0] if result and result[0] else "CamTest"
            video = cv2.VideoCapture(video_file)
            if not video.isOpened():
                self.logger.error(f"Failed to open video '{video_file}'")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("error", video_file))
            start_time_obj = self._get_video_start_time(video_file, camera_name)
            packing_area, qr_trigger_area = get_packing_area_func(camera_name)
            total_seconds = self.get_video_duration(video_file)
            if total_seconds is None:
                self.logger.error(f"Failed to get duration of video {video_file}")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("error", video_file))
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
            camera_log_dir = os.path.join(self.log_dir, camera_name)
            os.makedirs(camera_log_dir, exist_ok=True)
            log_file = os.path.join(camera_log_dir, f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt")
            log_file_handle = self._update_log_file(log_file, current_start_second, current_end_second, start_time_obj + timedelta(seconds=current_start_second), camera_name, video_file)
            # Start from frame at start_time
            start_frame = int(start_time * self.fps)
            end_frame = int(end_time * self.fps)
            video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frame_count = start_frame
            frame_states = []
            mvd_list = []
            last_state = None
            last_mvd = ""
            jump_time_ratio = getattr(self, 'jump_time_ratio', 0.5)  # Get from config or default 0.5
            while video.isOpened() and frame_count < end_frame:
                ret, frame = video.read()
                if not ret:
                    break

                # Store original frame for dual cropping
                original_frame = frame.copy()

                # Crop 2 separate regions
                frame_packing = None
                frame_trigger = None

                # Crop packing area (for MVD detection)
                if packing_area:
                    x, y, w, h = packing_area
                    frame_height, frame_width = original_frame.shape[:2]
                    if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                        frame_packing = original_frame[y:y + h, x:x + w]
                    else:
                        self.logger.warning(f"Invalid packing_area for frame {frame_count}: {packing_area}, frame size: {frame_width}x{frame_height}")

                # Crop trigger area (for TimeGo detection)
                if qr_trigger_area:
                    x, y, w, h = qr_trigger_area
                    frame_height, frame_width = original_frame.shape[:2]
                    if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                        frame_trigger = original_frame[y:y + h, x:x + w]
                    else:
                        self.logger.warning(f"Invalid qr_trigger_area for frame {frame_count}: {qr_trigger_area}, frame size: {frame_width}x{frame_height}")

                frame_count += 1
                if frame_count % frame_interval != 0:
                    continue
                if (frame_packing is None or frame_packing.size == 0) and (frame_trigger is None or frame_trigger.size == 0):
                    self.logger.warning(f"Both ROI frames empty for frame {frame_count}, skipping")
                    continue

                # Process both ROIs separately
                state, mvd = process_frame_func(frame_packing, frame_trigger, frame_count)
                second_in_video = (frame_count - 1) / self.fps
                second = round(second_in_video)
                if second >= current_end_second and second < end_time:
                    log_file_handle.close()
                    current_start_second = current_end_second
                    current_end_second = min(current_start_second + segment_duration, end_segment)
                    camera_log_dir = os.path.join(self.log_dir, camera_name)
                    os.makedirs(camera_log_dir, exist_ok=True)
                    log_file = os.path.join(camera_log_dir, f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt")
                    log_file_handle = self._update_log_file(log_file, current_start_second, current_end_second, start_time_obj + timedelta(seconds=current_start_second), camera_name, video_file)
                if second >= start_time and second <= end_time:
                    # Ghi MVD ngay nếu có và khác last_mvd
                    if mvd and mvd != last_mvd:
                        log_line = f"{second},{state},{mvd}\n"
                        log_file_handle.write(log_line)
                        self.logger.info(f"Log second {second}: state={state}, mvd={mvd}")
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
                                log_line = f"{second},{final_state},\n"
                                log_file_handle.write(log_line)
                                self.logger.info(f"Log second {second}: {frame_states_str}: {final_state}")
                                log_file_handle.flush()
                                if last_state == "On" and final_state == "Off":
                                    jump_frames = int(jump_time_ratio * self.min_packing_time * self.fps)
                                    new_frame_count = frame_count + jump_frames
                                    if new_frame_count < end_frame:
                                        video.set(cv2.CAP_PROP_POS_FRAMES, new_frame_count)
                                        frame_count = new_frame_count
                                        self.logger.info(f"Jumped {jump_frames} frames to {frame_count} after On->Off transition")
                                last_state = final_state
                        else:
                            self.logger.info(f"Skipped second {second}: {frame_states_str}, on_count={on_count}, off_count={off_count}")
                            log_file_handle.flush()
                        frame_states = []
                        mvd_list = []
            log_file_handle.close()
            video.release()
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE file_list SET is_processed = 1, status = ? WHERE file_path = ?", ("completed", video_file))
            self.logger.info(f"Completed processing video: {video_file}")
            return log_file
