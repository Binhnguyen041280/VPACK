import cv2
import os
import logging
import sqlite3
import threading
import subprocess
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from modules.db_utils import get_db_connection
from modules.scheduler.db_sync import frame_sampler_event, db_rwlock
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
        self.logger = get_logger(__name__, {"video_id": os.path.basename(self.video_file)})
        self.logger.info("Logging initialized")

    def load_config(self):
        logging.info("Loading configuration from database")
        with db_rwlock.gen_rlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            self.video_root = result[0] if result else os.path.join(BASE_DIR, "Inputvideo")
            cursor.execute("SELECT output_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            self.output_path = result[0] if result else os.path.join(BASE_DIR, "output_clips")
            self.log_dir = os.path.join(self.output_path, "LOG", "Frame")
            os.makedirs(self.log_dir, exist_ok=True)
            cursor.execute("SELECT timezone FROM general_info WHERE id = 1")
            result = cursor.fetchone()
            tz_hours = int(result[0].split("+")[1]) if result and "+" in result[0] else 7
            self.video_timezone = timezone(timedelta(hours=tz_hours))
            cursor.execute("SELECT frame_rate, frame_interval, min_packing_time FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            self.fps, self.frame_interval, self.min_packing_time = result if result else (30, 5, 5)
            logging.info(f"Config loaded: video_root={self.video_root}, output_path={self.output_path}, timezone={self.video_timezone}, fps={self.fps}, frame_interval={self.frame_interval}, min_packing_time={self.min_packing_time}")

    def get_packing_area(self, camera_name):
        logging.info(f"Querying qr_mvd_area and jump_time_ratio for camera {camera_name}")
        with db_rwlock.gen_rlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT qr_mvd_area, jump_time_ratio FROM packing_profiles WHERE profile_name = ?", (camera_name,))
            result = cursor.fetchone()
            cursor.execute("SELECT qr_trigger_area FROM packing_profiles WHERE profile_name = ?", (camera_name,))
            trigger_result = cursor.fetchone()
            conn.close()
        if result and result[1] is not None:
            self.jump_time_ratio = float(result[1])
            logging.info(f"Loaded jump_time_ratio: {self.jump_time_ratio}")
        else:
            self.jump_time_ratio = 0.5
            logging.info(f"Using default jump_time_ratio: {self.jump_time_ratio}")

        if result and result[0]:
            try:
                qr_mvd_area = result[0]
                if qr_mvd_area.startswith('(') and qr_mvd_area.endswith(')'):
                    x, y, w, h = map(int, qr_mvd_area.strip('()').split(','))
                else:
                    parsed = json.loads(qr_mvd_area)
                    if isinstance(parsed, list) and len(parsed) == 4:
                        x, y, w, h = parsed
                    else:
                        x, y, w, h = parsed['x'], parsed['y'], parsed['w'], parsed['h']
                roi = (x, y, w, h)
                logging.info(f"Using qr_mvd_area: {roi}")
            except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
                logging.error(f"Error parsing qr_mvd_area for camera {camera_name}: {str(e)}")
                roi = None
        else:
            logging.warning(f"No qr_mvd_area found for camera {camera_name}")
            roi = None
        trigger = json.loads(trigger_result[0]) if trigger_result and trigger_result[0] else [0, 0, 0, 0]
        logging.info(f"Using trigger: {trigger}")
        return roi, trigger

    def get_video_duration(self, video_file):
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(result.stdout.strip())
        except Exception:
            logging.error(f"Failed to get duration of video {video_file}")
            return None

    def load_video_files(self):
        with db_rwlock.gen_rlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM file_list WHERE is_processed = 0 AND status != 'xong' ORDER BY priority DESC, created_at ASC")
            video_files = [row[0] for row in cursor.fetchall()]
            conn.close()
        if not video_files:
            logging.info("No video files found with is_processed = 0 and status != 'xong'.")
        return video_files

    def process_frame(self, frame, frame_count):
        try:
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            texts, _ = self.qr_detector.detectAndDecode(frame)
            state = "Off"
            mvd = ""
            for text in texts:
                if text == "TimeGo":
                    state = "On"
                elif text:
                    mvd = text
            return state, mvd
        except Exception as e:
            logging.error(f"Error processing frame {frame_count}: {str(e)}")
            return "", ""

    def _get_video_start_time(self, video_file):
        try:
            result = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags=creation_time', '-of', 'default=noprint_wrappers=1:nokey=1', video_file])
            return datetime.strptime(result.decode().strip(), '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc).astimezone(self.video_timezone)
        except (subprocess.CalledProcessError, ValueError):
            try:
                result = subprocess.check_output(['exiftool', '-CreateDate', '-d', '%Y-%m-%d %H:%M:%S', video_file])
                return datetime.strptime(result.decode().split('CreateDate')[1].strip().split('\n')[0].strip(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.video_timezone)
            except (subprocess.CalledProcessError, IndexError):
                try:
                    result = subprocess.check_output(['exiftool', '-FileCreateDate', '-d', '%Y-%m-%d %H:%M:%S', video_file])
                    return datetime.strptime(result.decode().split('FileCreateDate')[1].strip().split('\n')[0].strip(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=self.video_timezone)
                except (subprocess.CalledProcessError, IndexError):
                    logging.warning("No metadata found, using file creation time.")
                    return datetime.fromtimestamp(os.path.getctime(video_file), tz=self.video_timezone)

    def _update_log_file(self, log_file, start_second, end_second, start_time, camera_name, video_file):
        log_file_handle = open(log_file, 'w')
        log_file_handle.write(f"# Start: {start_second}, End: {end_second}, Start_Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}, Camera_Name: {camera_name}, Video_File: {video_file}\n")
        log_file_handle.flush()
        with db_rwlock.gen_wlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_logs WHERE log_file = ?", (log_file,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO processed_logs (log_file, is_processed) VALUES (?, 0)", (log_file,))
            conn.commit()
            conn.close()
        return log_file_handle

    def run(self):
        while True:
            frame_sampler_event.wait()
            video_files = self.load_video_files()
            if not video_files:
                logging.info("No videos to process")
                frame_sampler_event.clear()
                continue
            for video_file in video_files:
                log_file = self.process_video(video_file, self.video_lock, self.get_packing_area, self.process_frame, self.frame_interval)
                if log_file:
                    logging.info(f"Completed processing video {video_file}, log at {log_file}")
                else:
                    logging.error(f"Failed to process video {video_file}")
            frame_sampler_event.clear()

    def process_video(self, video_file, video_lock, get_packing_area_func, process_frame_func, frame_interval, start_time=0, end_time=None):
        with video_lock:
            logging.info(f"Processing video: {video_file} from {start_time}s to {end_time}s")
            if not os.path.exists(video_file):
                logging.error(f"File '{video_file}' does not exist")
                with db_rwlock.gen_wlock():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("lỗi", video_file))
                    conn.commit()
                    conn.close()
                return None
            with db_rwlock.gen_wlock():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("đang frame sampler ...", video_file))
                cursor.execute("SELECT camera_name FROM file_list WHERE file_path = ?", (video_file,))
                result = cursor.fetchone()
                camera_name = result[0] if result and result[0] else "CamTest"
                conn.commit()
                conn.close()
            video = cv2.VideoCapture(video_file)
            if not video.isOpened():
                logging.error(f"Failed to open video '{video_file}'")
                with db_rwlock.gen_wlock():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("lỗi", video_file))
                    conn.commit()
                    conn.close()
                return None
            start_time_obj = self._get_video_start_time(video_file)
            roi, trigger = get_packing_area_func(camera_name)
            total_seconds = self.get_video_duration(video_file)
            if total_seconds is None:
                logging.error(f"Failed to get duration of video {video_file}")
                with db_rwlock.gen_wlock():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("lỗi", video_file))
                    conn.commit()
                    conn.close()
                return None
            logging.info(f"Video duration {video_file}: {total_seconds} seconds")
            video_name = os.path.splitext(os.path.basename(video_file))[0]
            segment_duration = 300
            # Xác định các đoạn 300s chứa [start_time, end_time]
            end_time = total_seconds if end_time is None else min(end_time, total_seconds)
            start_segment = math.floor(start_time / segment_duration) * segment_duration
            end_segment = math.ceil(end_time / segment_duration) * segment_duration
            current_start_second = start_segment
            current_end_second = min(current_start_second + segment_duration, end_segment)
            camera_log_dir = os.path.join(self.log_dir, camera_name)
            os.makedirs(camera_log_dir, exist_ok=True)
            log_file = os.path.join(camera_log_dir, f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt")
            log_file_handle = self._update_log_file(log_file, current_start_second, current_end_second, start_time_obj + timedelta(seconds=current_start_second), camera_name, video_file)
            # Bắt đầu từ khung hình tại start_time
            start_frame = int(start_time * self.fps)
            end_frame = int(end_time * self.fps)
            video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frame_count = start_frame
            frame_states = []
            mvd_list = []
            last_state = None
            last_mvd = ""
            jump_time_ratio = getattr(self, 'jump_time_ratio', 0.5)  # Lấy từ config hoặc mặc định 0.5
            while video.isOpened() and frame_count < end_frame:
                ret, frame = video.read()
                if not ret:
                    break
                if roi:
                    x, y, w, h = roi
                    frame_height, frame_width = frame.shape[:2]
                    if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                        frame = frame[y:y + h, x:x + w]
                    else:
                        logging.warning(f"Invalid ROI for frame {frame_count}: {roi}, frame size: {frame_width}x{frame_height}")
                        frame = frame
                frame_count += 1
                if frame_count % frame_interval != 0:
                    continue
                if frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
                    logging.warning(f"Empty frame {frame_count}, skipping")
                    continue
                state, mvd = process_frame_func(frame, frame_count)
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
                        logging.info(f"Log second {second}: state={state}, mvd={mvd}")
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
                                logging.info(f"Log second {second}: {frame_states_str}: {final_state}")
                                log_file_handle.flush()
                                if last_state == "On" and final_state == "Off":
                                    jump_frames = int(jump_time_ratio * self.min_packing_time * self.fps)
                                    new_frame_count = frame_count + jump_frames
                                    if new_frame_count < end_frame:
                                        video.set(cv2.CAP_PROP_POS_FRAMES, new_frame_count)
                                        frame_count = new_frame_count
                                        logging.info(f"Jumped {jump_frames} frames to {frame_count} after On->Off transition")
                                last_state = final_state
                        else:
                            logging.info(f"Skipped second {second}: {frame_states_str}, on_count={on_count}, off_count={off_count}")
                            log_file_handle.flush()
                        frame_states = []
                        mvd_list = []
            log_file_handle.close()
            video.release()
            with db_rwlock.gen_wlock():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE file_list SET is_processed = 1, status = ? WHERE file_path = ?", ("xong", video_file))
                conn.commit()
                conn.close()
            logging.info(f"Completed processing video: {video_file}")
            return log_file
