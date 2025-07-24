import threading
import time
import os
import logging
from datetime import datetime
from modules.db_utils.db_utils import get_db_connection
from modules.technician.frame_sampler_trigger import FrameSamplerTrigger
from modules.technician.frame_sampler_no_trigger import FrameSamplerNoTrigger
from modules.technician.IdleMonitor import IdleMonitor
from modules.technician.event_detector import process_single_log
from .db_sync import db_rwlock, frame_sampler_event, event_detector_event, event_detector_done
import json
from modules.config.logging_config import  get_logger
import logging

logging.info("Logging initialized for program_runner")

# Biến tạm để lưu trạng thái chạy và số ngày
running_state = {"current_running": None, "days": None, "custom_path": None, "files": []}
# Dictionary lưu khóa cho từng nhóm video
video_locks = {}

def start_frame_sampler_thread(batch_size=1):
    logging.info(f"Starting {batch_size} frame sampler threads")
    threads = []
    for _ in range(batch_size):
        frame_sampler_thread = threading.Thread(target=run_frame_sampler)
        frame_sampler_thread.start()
        threads.append(frame_sampler_thread)
    return threads

def run_frame_sampler():
    logging.info("Frame sampler thread started")
    while True:  # Vòng lặp vô hạn để thread luôn chạy
        frame_sampler_event.wait()  # Chờ thông báo từ event
        logging.debug("Frame sampler event received")
        try:
            with db_rwlock.gen_rlock():  # Đồng bộ hóa truy cập database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT file_path, camera_name FROM file_list WHERE is_processed = 0 ORDER BY priority DESC, created_at ASC")
                video_files = [(row[0], row[1]) for row in cursor.fetchall()]
                conn.close()
                logging.info(f"Found {len(video_files)} unprocessed video files")

            if not video_files:
                logging.info("No video files to process, clearing event")
                frame_sampler_event.clear()  # Xóa event và tiếp tục chờ
                continue

            for video_file, camera_name in video_files:
                # Kiểm tra trạng thái video trước khi xử lý
                with db_rwlock.gen_rlock():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT status, is_processed FROM file_list WHERE file_path = ?", (video_file,))
                    result = cursor.fetchone()
                    conn.close()
                    if result and (result[0] == "đang frame sampler ..." or result[1] == 1):
                        logging.info(f"Skipping video {video_file}: already being processed or completed")
                        continue

                # Khóa theo video
                with db_rwlock.gen_wlock():
                    if video_file not in video_locks:
                        video_locks[video_file] = threading.Lock()
                video_lock = video_locks[video_file]
                if not video_lock.acquire(blocking=False):
                    logging.info(f"Skipping video {video_file}: locked by another thread")
                    continue

                try:
                    logging.info(f"Processing video: {video_file}")
                    # Kiểm tra qr_trigger_area và packing_area từ packing_profiles
                    with db_rwlock.gen_rlock():
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        search_name = camera_name if camera_name else "CamTest"
                        if not camera_name:
                            logging.warning(f"No camera_name for {video_file}, falling back to CamTest")
                        cursor.execute("SELECT id, profile_name, qr_trigger_area, packing_area FROM packing_profiles WHERE profile_name LIKE ?", (f'%{search_name}%',))
                        profiles = cursor.fetchall()
                        conn.close()
                    
                    # Chọn profile có id lớn nhất
                    trigger = [0, 0, 0, 0]
                    packing_area = None
                    selected_profile = None
                    if profiles:
                        selected_profile = max(profiles, key=lambda x: x[0])  # Chọn id lớn nhất
                        profile_id, profile_name, qr_trigger_area, packing_area_raw = selected_profile
                        # Parse qr_trigger_area
                        try:
                            trigger = json.loads(qr_trigger_area) if qr_trigger_area else [0, 0, 0, 0]
                            if not isinstance(trigger, list) or len(trigger) != 4:
                                logging.error(f"Invalid qr_trigger_area for {profile_name}: {qr_trigger_area}, using default [0, 0, 0, 0]")
                                trigger = [0, 0, 0, 0]
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to parse qr_trigger_area for {profile_name}: {e}, using default [0, 0, 0, 0]")
                            trigger = [0, 0, 0, 0]
                        # Parse packing_area
                        try:
                            if packing_area_raw:
                                parsed = json.loads(packing_area_raw)
                                if isinstance(parsed, list) and len(parsed) == 4:
                                    packing_area = tuple(parsed)
                                else:
                                    logging.error(f"Invalid packing_area format for {profile_name}: {packing_area_raw}, using default None")
                                    packing_area = None
                            logging.info(f"Selected profile id={profile_id}, profile_name={profile_name}, qr_trigger_area={trigger}, packing_area={packing_area}")
                        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
                            logging.error(f"Failed to parse packing_area for {profile_name}: {e}, using default None")
                            packing_area = None
                    else:
                        logging.warning(f"No profile found for camera {search_name}, using default qr_trigger_area=[0, 0, 0, 0], packing_area=None")
                    
                    # Chạy IdleMonitor trước FrameSampler, truyền packing_area
                    idle_monitor = IdleMonitor()
                    logging.info(f"Running IdleMonitor for {video_file}")
                    idle_monitor.process_video(video_file, camera_name, packing_area)
                    work_block_queue = idle_monitor.get_work_block_queue()

                    # bỏ qua file không có work block
                    if work_block_queue.empty():
                        logging.info(f"No work blocks found for {video_file}, skipping FrameSampler and log file creation")
                        with db_rwlock.gen_wlock():
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE file_list SET status = ?, is_processed = 1 WHERE file_path = ?", ("xong", video_file))
                            conn.commit()
                            conn.close()
                        continue  # Bỏ qua FrameSampler và chuyển sang video tiếp theo
                    # Chọn FrameSampler dựa trên trigger
                    if trigger != [0, 0, 0, 0]:
                        frame_sampler = FrameSamplerTrigger()
                        logging.info(f"Using FrameSamplerTrigger for {video_file}")
                    else:
                        frame_sampler = FrameSamplerNoTrigger()
                        logging.info(f"Using FrameSamplerNoTrigger for {video_file}")

                    with db_rwlock.gen_wlock():  # Khóa khi cập nhật trạng thái
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("đang frame sampler ...", video_file))
                        conn.commit()
                        conn.close()
                        logging.debug(f"Updated status for {video_file} to 'đang frame sampler ...'")
                    
                    # Gọi process_video với work block từ queue
                    log_file = None
                    while not work_block_queue.empty():
                        work_block = work_block_queue.get()
                        start_time = work_block['start_time']
                        end_time = work_block['end_time']
                        logging.info(f"Processing video block: start_time={start_time}, end_time={end_time}")
                        log_file = frame_sampler.process_video(
                            video_file,
                            video_lock=frame_sampler.video_lock,
                            get_packing_area_func=frame_sampler.get_packing_area,
                            process_frame_func=frame_sampler.process_frame,
                            frame_interval=frame_sampler.frame_interval,
                            start_time=start_time,
                            end_time=end_time
                        )
                    
                    with db_rwlock.gen_wlock():  # Khóa khi cập nhật trạng thái cuối
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        if log_file:
                            cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("xong", video_file))
                            event_detector_event.set()  # Kích hoạt Event Detector sau mỗi video
                            logging.info(f"Video {video_file} processed successfully, log file: {log_file}")
                        else:
                            cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("lỗi", video_file))
                            logging.error(f"Failed to process video {video_file}")
                        conn.commit()
                        conn.close()
                    
                    # Tạm dừng sau khi xử lý xong một video
                    logging.info(f"Frame Sampler pausing after processing {video_file}, waiting for Event Detector...")
                    while not event_detector_done.is_set():
                        time.sleep(1)  # Chờ Event Detector hoàn tất

                finally:
                    video_lock.release()
                    with db_rwlock.gen_wlock():
                        video_locks.pop(video_file, None)  # Xóa khóa sau khi xử lý xong
                    logging.debug(f"Released lock for {video_file}")

            frame_sampler_event.clear()  # Xóa event sau khi xử lý hết file
            logging.info("All video files processed, clearing frame sampler event")
        except Exception as e:
            logging.error(f"Error in Frame Sampler thread: {str(e)}")
            frame_sampler_event.clear()  # Đảm bảo thread "ngủ" lại nếu có lỗi

def start_event_detector_thread():
    logging.info("Starting event detector thread")
    event_detector_thread = threading.Thread(target=run_event_detector)
    event_detector_thread.start()
    return event_detector_thread

def run_event_detector():
    logging.info("Event detector thread started")
    while True:
        event_detector_event.wait()
        logging.debug("Event detector event received")
        try:
            with db_rwlock.gen_rlock():  # Đồng bộ hóa truy cập database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT log_file FROM processed_logs WHERE is_processed = 0")
                log_files = [row[0] for row in cursor.fetchall()]
                conn.close()
                logging.info(f"Found {len(log_files)} unprocessed log files")

            if not log_files:
                event_detector_event.clear()
                event_detector_done.set()  # Báo hiệu Frame Sampler tiếp tục
                logging.info("No log files to process, clearing event and signaling done")
                continue

            for log_file in log_files:
                logging.info(f"Event Detector processing: {log_file}")
                process_single_log(log_file)
            event_detector_event.clear()
            event_detector_done.set()  # Báo hiệu Frame Sampler tiếp tục sau khi xử lý hết log
            logging.info("All log files processed, clearing event and signaling done")
        except Exception as e:
            logging.error(f"Error in Event Detector thread: {str(e)}")
            event_detector_event.clear()
            event_detector_done.set()  # Vẫn báo hiệu Frame Sampler tiếp tục nếu có lỗi
