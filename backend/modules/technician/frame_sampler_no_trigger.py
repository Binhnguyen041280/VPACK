import cv2
import os
import logging
import sqlite3
import threading
import subprocess
import json
import queue
import numpy as np
import mediapipe as mp
from datetime import datetime, timezone, timedelta
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import frame_sampler_event, db_rwlock
import math
from modules.config.logging_config import get_logger


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models", "wechat_qr")
DETECT_PROTO = os.path.join(MODEL_DIR, "detect.prototxt")
DETECT_MODEL = os.path.join(MODEL_DIR, "detect.caffemodel")
SR_PROTO = os.path.join(MODEL_DIR, "sr.prototxt")
SR_MODEL = os.path.join(MODEL_DIR, "sr.caffemodel")

class FrameSamplerNoTrigger:
    def __init__(self):
        self.setup_logging()
        self.load_config()
        self.video_lock = threading.Lock()
        self.setup_wechat_qr()
        # Initialize MediaPipe Hands (using pattern from hand_detection.py)
        try:
            self.mp_hands = mp.solutions.hands  # type: ignore
            self.mp_drawing = mp.solutions.drawing_utils  # type: ignore
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        except AttributeError as e:
            logging.error(f"MediaPipe import error: {e}")
            raise ImportError("MediaPipe modules not found. Please reinstall MediaPipe.")
        # Initialize log queue and writer thread
        self.log_queue = queue.Queue()
        self.log_thread = threading.Thread(target=self._log_writer)
        self.log_thread.daemon = True
        self.log_thread.start()

    def setup_logging(self):
        self.logger = get_logger(__name__, {})
        self.logger.info("Logging initialized")

    def setup_wechat_qr(self):
        for model_file in [DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL]:
            if not os.path.exists(model_file):
                logging.error(f"Model file not found: {model_file}")
                raise FileNotFoundError(f"Model file not found: {model_file}")
        try:
            # Using pattern from qr_detector.py with proper error handling
            self.qr_detector = cv2.wechat_qrcode_WeChatQRCode(DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL)  # type: ignore
            logging.info("WeChat QRCode detector initialized")
        except Exception as e:
            logging.error(f"Failed to initialize WeChat QRCode: {str(e)}")
            self.qr_detector = None

    def load_config(self):
        logging.info("Loading configuration from database")
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
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
                cursor.execute("SELECT frame_rate, frame_interval, min_packing_time, motion_threshold, stable_duration_sec FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                self.fps, self.frame_interval, self.min_packing_time, self.motion_threshold, self.stable_duration_sec = result if result else (30, 5, 3, 0.1, 1.0)
            logging.info(f"Config loaded: video_root={self.video_root}, output_path={self.output_path}, timezone={self.video_timezone}, fps={self.fps}, frame_interval={self.frame_interval}, min_packing_time={self.min_packing_time}, motion_threshold={self.motion_threshold}, stable_duration_sec={self.stable_duration_sec}")

    def get_packing_area(self, camera_name):
        logging.info(f"Querying qr_mvd_area for camera {camera_name}")
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT qr_mvd_area FROM packing_profiles WHERE profile_name = ?", (camera_name,))
                result = cursor.fetchone()
        if result and result[0]:
            try:
                qr_mvd_area = result[0]
                if qr_mvd_area.startswith('(') and qr_mvd_area.endswith(')'):
                    x, y, w, h = map(int, qr_mvd_area.strip('()').split(','))
                else:
                    parsed = json.loads(qr_mvd_area)
                    if isinstance(parsed, list) and len(parsed) == 4:
                        x, y, w, h = parsed
                    elif isinstance(parsed, dict):
                        x, y, w, h = parsed.get('x', 0), parsed.get('y', 0), parsed.get('w', 0), parsed.get('h', 0)
                    else:
                        x, y, w, h = 0, 0, 0, 0
                roi = (x, y, w, h)
                logging.info(f"Using qr_mvd_area: {roi}")
            except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
                logging.error(f"Error parsing qr_mvd_area for camera {camera_name}: {str(e)}")
                roi = None
        else:
            logging.warning(f"No qr_mvd_area found for camera {camera_name}")
            roi = None
        return roi

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
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM file_list WHERE is_processed = 0 AND status != 'xong' ORDER BY priority DESC, created_at ASC")
                video_files = [row[0] for row in cursor.fetchall()]
        if not video_files:
            logging.info("No video files found with is_processed = 0 and status != 'xong'.")
        return video_files

    def process_frame(self, frame, frame_count):
        try:
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            if self.qr_detector is None:
                return []
            texts, _ = self.qr_detector.detectAndDecode(frame)
            for text in texts:
                if text and text != "TimeGo":
                    logging.info(f"Second {round((frame_count - 1) / self.fps)}: QR texts={texts}, mvd={text}")
                    return text
            return ""
        except Exception as e:
            logging.error(f"Error processing frame {frame_count}: {str(e)}")
            return ""

    def detect_hand(self, frame):
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Process frame with MediaPipe Hands
            results = self.hands.process(rgb_frame)
            # Return True if hand landmarks are detected
            return bool(results.multi_hand_landmarks) if results and hasattr(results, 'multi_hand_landmarks') else False
        except Exception as e:
            logging.error(f"Error in hand detection: {str(e)}")
            return False

    def compute_motion_level(self, prev_frame, curr_frame):
        try:
            if len(prev_frame.shape) == 3:
                prev_frame = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            if len(curr_frame.shape) == 3:
                curr_frame = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(prev_frame, curr_frame)
            motion_level = np.mean(diff) / 255.0
            return motion_level
        except Exception as e:
            logging.error(f"Error computing motion level: {str(e)}")
            return 1.0

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

    def _log_writer(self):
        while True:
            log_file, entry, timestamp = self.log_queue.get()
            with threading.Lock():
                mode = 'w' if not os.path.exists(log_file) else 'a'
                with open(log_file, mode) as f:
                    if mode == 'w':
                        f.write(f"# Start: {timestamp['start']}, End: {timestamp['end']}, Start_Time: {timestamp['start_time']}, Camera_Name: {timestamp['camera']}, Video_File: {timestamp['video']}\n")
                    f.write(f"{entry}\n")
                    f.flush()
            self.log_queue.task_done()

    def _update_log_file(self, log_file, start_second, end_second, start_time, camera_name, video_file):
        timestamp = {
            'start': start_second,
            'end': end_second,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'camera': camera_name,
            'video': video_file
        }
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM processed_logs WHERE log_file = ?", (log_file,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO processed_logs (log_file, is_processed) VALUES (?, 0)", (log_file,))
        return lambda entry, ts: self.log_queue.put((log_file, f"{ts},{entry}", timestamp))

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
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("lỗi", video_file))
                return None
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("đang frame sampler ...", video_file))
                    cursor.execute("SELECT camera_name FROM file_list WHERE file_path = ?", (video_file,))
                    result = cursor.fetchone()
                    camera_name = result[0] if result and result[0] else "CamTest"
            video = cv2.VideoCapture(video_file)
            if not video.isOpened():
                logging.error(f"Failed to open video '{video_file}'")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("lỗi", video_file))
                return None
            start_time_obj = self._get_video_start_time(video_file)
            roi = get_packing_area_func(camera_name)
            total_seconds = self.get_video_duration(video_file)
            if total_seconds is None:
                logging.error(f"Failed to get duration of video {video_file}")
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("lỗi", video_file))
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
            prev_frame = None
            stable_segments = []
            qr_events = []
            stable_start = None
            last_te = -self.min_packing_time * self.fps
            is_stable = False
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
                        logging.warning(f"Invalid ROI for frame {frame_count}: {roi}, frame_size: {frame_width}x{frame_height}")
                        frame = frame
                frame_count += 1
                if frame_count % frame_interval != 0:
                    continue
                if frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
                    logging.warning(f"Empty frame {frame_count}, skipping")
                    continue
                # QR detection
                mvd = process_frame_func(frame, frame_count)
                if mvd:
                    qr_events.append((frame_count, mvd))
                # Motion detection
                if prev_frame is not None:
                    motion_level = self.compute_motion_level(prev_frame, frame)
                    min_stable_frames = max(6, int(self.fps * self.stable_duration_sec / self.frame_interval))
                    if motion_level < self.motion_threshold:
                        if not is_stable:
                            stable_start = frame_count
                            is_stable = True
                    else:
                        if is_stable and stable_start is not None and (frame_count - stable_start) >= min_stable_frames * frame_interval:
                            start_second = round((stable_start - 1) / self.fps, 1)
                            end_second = round((frame_count - frame_interval - 1) / self.fps, 1)
                            if start_second >= start_time and end_second <= end_time:
                                stable_segments.append((stable_start, frame_count - frame_interval))
                                logging.info(f"Stable segment: start={start_second}s, end={end_second}s")
                        is_stable = False
                prev_frame = frame.copy()
                second_in_video = (frame_count - 1) / self.fps
                second = round(second_in_video)
                if second >= current_end_second and second < end_time:
                    current_start_second = current_end_second
                    current_end_second = min(current_start_second + segment_duration, end_segment)
                    camera_log_dir = os.path.join(self.log_dir, camera_name)
                    os.makedirs(camera_log_dir, exist_ok=True)
                    log_file = os.path.join(camera_log_dir, f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt")
                    log_file_handle = self._update_log_file(log_file, current_start_second, current_end_second, start_time_obj + timedelta(seconds=current_start_second), camera_name, video_file)
            if is_stable and stable_start is not None and (frame_count - stable_start) >= min_stable_frames * frame_interval:
                start_second = round((stable_start - 1) / self.fps, 1)
                end_second = round((frame_count - 1) / self.fps, 1)
                if start_second >= start_time and end_second <= end_time:
                    stable_segments.append((stable_start, frame_count))
                    logging.info(f"Stable segment: start={start_second}s, end={end_second}s")
            # Group QR codes and select the last frame of each sequence
            grouped_qr = []
            current_mvd = None
            current_frames = []
            for frame, mvd in qr_events:
                if mvd == "TimeGo":
                    continue
                if mvd != current_mvd:
                    if current_mvd and current_frames:
                        grouped_qr.append((current_frames[-1], current_mvd))
                    current_mvd = mvd
                    current_frames = [frame]
                else:
                    current_frames.append(frame)
            if current_mvd and current_frames:
                grouped_qr.append((current_frames[-1], current_mvd))
            # Log last QR event
            if grouped_qr:
                last_qr_frame, last_qr_code = grouped_qr[-1]
                last_qr_second = round((last_qr_frame - 1) / self.fps, 1)
                if last_qr_second >= start_time and last_qr_second <= end_time:
                    logging.info(f"Last QR event: Te={last_qr_second}s, QR={last_qr_code}")
            # Find Ts/Te
            video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frame_count = start_frame
            last_te = -self.min_packing_time * self.fps
            prev_te_frame = None
            for idx, (te_frame, qr_code) in enumerate(grouped_qr):
                if te_frame <= last_te + self.min_packing_time * self.fps:
                    logging.info(f"Skipping event for QR {qr_code} at frame {te_frame}: too close to last_te {last_te}")
                    continue
                second_te = round((te_frame - 1) / self.fps)
                if second_te < start_time or second_te > end_time:
                    continue
                segment_index = math.floor(second_te / segment_duration)
                target_start_second = segment_index * segment_duration
                target_end_second = (segment_index + 1) * segment_duration
                if second_te >= current_end_second or target_start_second != current_start_second:
                    current_start_second = target_start_second
                    current_end_second = min(target_start_second + segment_duration, end_segment)
                    camera_log_dir = os.path.join(self.log_dir, camera_name)
                    os.makedirs(camera_log_dir, exist_ok=True)
                    log_file = os.path.join(camera_log_dir, f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt")
                    log_file_handle = self._update_log_file(log_file, current_start_second, current_end_second, start_time_obj + timedelta(seconds=current_start_second), camera_name, video_file)
                ts_frame = None
                # Trường hợp đặc biệt: Te đầu tiên
                if idx == 0:
                    has_stable_segment = any(start <= te_frame for start, end in stable_segments)
                    if not has_stable_segment:
                        log_file_handle(f"On,{qr_code}", second_te)
                        logging.info(f"Logged only Te for QR {qr_code} at second {second_te}: no stable segments for first Te")
                        last_te = te_frame
                        prev_te_frame = te_frame
                        continue
                # Tìm vùng ổn định sau Te phía trước (hoặc đầu video nếu không có Te trước)
                closest_stable = None
                search_start = max(prev_te_frame if prev_te_frame is not None else start_frame, start_frame)
                for start, end in stable_segments:
                    if start > search_start and end < te_frame:
                        if closest_stable is None or start < closest_stable[0]:
                            closest_stable = (start, end)
                if closest_stable:
                    # Tìm tay sau vùng ổn định
                    video.set(cv2.CAP_PROP_POS_FRAMES, closest_stable[1])
                    hand_frame_count = closest_stable[1]
                    while hand_frame_count < te_frame and hand_frame_count < end_frame:
                        ret, frame = video.read()
                        if not ret:
                            break
                        if roi:
                            x, y, w, h = roi
                            frame_height, frame_width = frame.shape[:2]
                            if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                                frame = frame[y:y + h, x:x + w]
                        hand_frame_count += 1
                        if hand_frame_count % self.frame_interval != 0:
                            continue
                        if self.detect_hand(frame) and hand_frame_count > last_te + self.min_packing_time * self.fps:
                            ts_frame = hand_frame_count
                            second_ts = round((ts_frame - 1) / self.fps, 1)
                            if second_ts >= start_time and second_ts <= end_time:
                                logging.info(f"Hand detected for Ts: frame={ts_frame}, time={second_ts}s")
                                break
                            ts_frame = None
                else:
                    # Không có vùng ổn định, tìm tay ngay sau Te phía trước
                    if prev_te_frame is not None:
                        video.set(cv2.CAP_PROP_POS_FRAMES, max(prev_te_frame, start_frame))
                        hand_frame_count = max(prev_te_frame, start_frame)
                        while hand_frame_count < te_frame and hand_frame_count < end_frame:
                            ret, frame = video.read()
                            if not ret:
                                break
                            if roi:
                                x, y, w, h = roi
                                frame_height, frame_width = frame.shape[:2]
                                if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                                    frame = frame[y:y + h, x:x + w]
                            hand_frame_count += 1
                            if hand_frame_count % self.frame_interval != 0:
                                continue
                            if self.detect_hand(frame) and hand_frame_count > last_te + self.min_packing_time * self.fps:
                                ts_frame = hand_frame_count
                                second_ts = round((ts_frame - 1) / self.fps, 1)
                                if second_ts >= start_time and second_ts <= end_time:
                                    logging.info(f"Hand detected for Ts: frame={ts_frame}, time={second_ts}s")
                                    break
                                ts_frame = None
                # Ghi log
                if ts_frame:
                    second_ts = round((ts_frame - 1) / self.fps)
                    segment_index = math.floor(max(second_ts, second_te) / segment_duration)
                    target_start_second = segment_index * segment_duration
                    target_end_second = (segment_index + 1) * segment_duration
                    if max(second_ts, second_te) >= current_end_second or target_start_second != current_start_second:
                        current_start_second = target_start_second
                        current_end_second = min(target_start_second + segment_duration, end_segment)
                        camera_log_dir = os.path.join(self.log_dir, camera_name)
                        os.makedirs(camera_log_dir, exist_ok=True)
                        log_file = os.path.join(camera_log_dir, f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt")
                        log_file_handle = self._update_log_file(log_file, current_start_second, current_end_second, start_time_obj + timedelta(seconds=current_start_second), camera_name, video_file)
                    log_file_handle("On,", second_ts - 1)
                    log_file_handle("Off,", second_ts)
                    log_file_handle("Off,", second_te - 1)
                    log_file_handle(f"On,{qr_code}", second_te)
                    logging.info(f"Event logged: Ts={second_ts}, Te={second_te}, QR={qr_code}")
                else:
                    second_ts = second_te - self.min_packing_time - 1
                    if second_ts >= start_time and second_ts >= (last_te / self.fps):
                        segment_index = math.floor(max(second_ts, second_te) / segment_duration)
                        target_start_second = segment_index * segment_duration
                        target_end_second = (segment_index + 1) * segment_duration
                        if max(second_ts, second_te) >= current_end_second or target_start_second != current_start_second:
                            current_start_second = target_start_second
                            current_end_second = min(target_start_second + segment_duration, end_segment)
                            camera_log_dir = os.path.join(self.log_dir, camera_name)
                            os.makedirs(camera_log_dir, exist_ok=True)
                            log_file = os.path.join(camera_log_dir, f"log_{video_name}_{current_start_second:04d}_{current_end_second:04d}.txt")
                            log_file_handle = self._update_log_file(log_file, current_start_second, current_end_second, start_time_obj + timedelta(seconds=current_start_second), camera_name, video_file)
                        log_file_handle("On,", second_ts - 1)
                        log_file_handle("Off,", second_ts)
                        log_file_handle("Off,", second_te - 1)
                        log_file_handle(f"On,{qr_code}", second_te)
                        logging.info(f"Assumed Ts={second_ts} for Te={second_te}, QR={qr_code}")
                    else:
                        log_file_handle("Off,", second_te - 1)
                        log_file_handle(f"On,{qr_code}", second_te)
                        logging.info(f"Logged only Te for QR {qr_code} at second {second_te}: assumed Ts={second_ts} invalid (out of range or too close to last_te)")
                last_te = te_frame
                prev_te_frame = te_frame
            video.release()
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE file_list SET is_processed = 1, status = ? WHERE file_path = ?", ("xong", video_file))
            logging.info(f"Completed processing video: {video_file}")
            return log_file
