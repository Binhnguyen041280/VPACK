import os
import threading
import time
import logging
import sqlite3
import pytz
import psutil  # THÊM IMPORT MỚI
from datetime import datetime, timedelta
from modules.db_utils import get_db_connection
from .db_sync import db_rwlock, frame_sampler_event, event_detector_event
from .file_lister import run_file_scan
from .program_runner import start_frame_sampler_thread, start_event_detector_thread
import logging

logger = logging.getLogger("app")
logger.info("BatchScheduler logging initialized")

# Cấu hình múi giờ Việt Nam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

class SystemMonitor:
    """Theo dõi tài nguyên hệ thống và tính batch_size động."""
    def __init__(self):
        self.cpu_threshold_low = 70
        self.cpu_threshold_high = 90
        self.base_batch_size = 2
        self.max_batch_size = 6

    def get_cpu_usage(self):
        """Lấy CPU usage thực tế từ hệ thống"""
        try:
            # Lấy CPU usage trung bình trong 1 giây
            cpu_percent = psutil.cpu_percent(interval=1)
            logger.debug(f"Current CPU usage: {cpu_percent}%")
            return cpu_percent
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 50  # Fallback value nếu có lỗi

    def get_memory_usage(self):
        """Lấy memory usage thực tế"""
        try:
            memory_percent = psutil.virtual_memory().percent
            logger.debug(f"Current memory usage: {memory_percent}%")
            return memory_percent
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 50  # Fallback value

    def get_batch_size(self, current_batch_size):
        cpu_usage = self.get_cpu_usage()
        memory_usage = self.get_memory_usage()
        
        logger.debug(f"Resource usage - CPU: {cpu_usage}%, Memory: {memory_usage}%")
        
        # Kiểm tra nếu tài nguyên quá tải
        if cpu_usage > self.cpu_threshold_high or memory_usage > 85:
            if current_batch_size > self.base_batch_size:
                new_batch_size = current_batch_size - 1
                logger.warning(f"High resource usage (CPU: {cpu_usage}%, RAM: {memory_usage}%), reducing batch size: {current_batch_size} -> {new_batch_size}")
                return new_batch_size
        
        # Kiểm tra nếu tài nguyên nhàn rỗi
        elif cpu_usage < self.cpu_threshold_low and memory_usage < 70:
            if current_batch_size < self.max_batch_size:
                new_batch_size = current_batch_size + 1
                logger.info(f"Low resource usage (CPU: {cpu_usage}%, RAM: {memory_usage}%), increasing batch size: {current_batch_size} -> {new_batch_size}")
                return new_batch_size
        
        # Giữ nguyên nếu tài nguyên ổn định
        return current_batch_size

    def log_system_info(self):
        """Log thông tin hệ thống khi khởi động"""
        try:
            cpu_count = psutil.cpu_count()
            memory_total = psutil.virtual_memory().total / (1024**3)  # GB
            logger.info(f"System info - CPU cores: {cpu_count}, Total RAM: {memory_total:.1f}GB")
            logger.info(f"Batch size config - Base: {self.base_batch_size}, Max: {self.max_batch_size}")
            logger.info(f"CPU thresholds - Low: {self.cpu_threshold_low}%, High: {self.cpu_threshold_high}%")
        except Exception as e:
            logger.error(f"Error logging system info: {e}")

class BatchScheduler:
    def __init__(self):
        self.batch_size = 2
        self.sys_monitor = SystemMonitor()
        self.scan_interval = 60
        self.timeout_seconds = 3600
        self.running = False
        self.queue_limit = 5
        self.sampler_threads = []
        self.detector_thread = None
        self.pause_event = threading.Event()
        self.pause_event.set()

    def pause(self):
        logger.info(f"BatchScheduler paused, current_batch_size={self.batch_size}")
        self.pause_event.clear()

    def resume(self):
        logger.info(f"BatchScheduler resumed, current_batch_size={self.batch_size}")
        self.pause_event.set()

    def get_pending_files(self):
        """Lấy danh sách file chưa xử lý, giới hạn queue_limit."""
        try:
            with db_rwlock.gen_rlock():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT file_path, camera_name FROM file_list WHERE status = 'pending' AND is_processed = 0 ORDER BY priority DESC, created_at ASC LIMIT ?", 
                             (self.queue_limit,))
                files = [(row[0], row[1]) for row in cursor.fetchall()]
                conn.close()
            return files
        except Exception as e:
            logger.error(f"Error retrieving pending files: {e}")
            return []

    def update_file_status(self, file_path, status):
        """Cập nhật trạng thái file trong file_list."""
        try:
            with db_rwlock.gen_wlock():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE file_list SET status = ?, is_processed = ? WHERE file_path = ?",
                             (status, 1 if status in ['xong', 'lỗi', 'timeout'] else 0, file_path))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Error updating file status for {file_path}: {e}")

    def check_timeout(self):
        """Kiểm tra và cập nhật trạng thái timeout cho file quá 900s."""
        try:
            with db_rwlock.gen_wlock():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT file_path, created_at FROM file_list WHERE status = 'đang frame sampler ...'")
                for row in cursor.fetchall():
                    created_at = datetime.fromisoformat(row[1].replace('Z', '+00:00')) if row[1] else datetime.min.replace(tzinfo=VIETNAM_TZ)
                    if (datetime.now(VIETNAM_TZ) - created_at).total_seconds() > self.timeout_seconds:
                        cursor.execute("UPDATE file_list SET status = ?, is_processed = 1 WHERE file_path = ?", 
                                     ('timeout', row[0]))
                        logger.warning(f"Timeout processing {row[0]} after {self.timeout_seconds}s")
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Error checking timeout: {e}")

    def scan_files(self):
        """Quét file mới định kỳ (15 phút)."""
        logger.info("Bắt đầu quét lặp")
        while self.running:
            try:
                logger.debug("Kiểm tra quét lặp, running=%s, paused=%s", self.running, not self.pause_event.is_set())
                self.pause_event.wait()
                with db_rwlock.gen_rlock():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM file_list WHERE status = 'pending' AND is_processed = 0")
                    pending_count = cursor.fetchone()[0]
                    conn.close()

                if pending_count >= self.queue_limit:
                    logger.warning(f"Queue full ({pending_count}/{self.queue_limit}), skipping file scan")
                else:
                    run_file_scan("default")
                    frame_sampler_event.set()
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Error in file scan: {e}")

    def run_batch(self):
        """Chạy batch xử lý file, sử dụng run_frame_sampler."""
        while self.running:
            try:
                self.pause_event.wait()
                self.batch_size = self.sys_monitor.get_batch_size(self.batch_size)

                if not self.sampler_threads or len(self.sampler_threads) != self.batch_size:
                    for thread in self.sampler_threads:
                        if thread.is_alive():
                            thread.join(timeout=1)
                    self.sampler_threads = start_frame_sampler_thread(self.batch_size)
                    logger.info(f"Started {self.batch_size} frame sampler threads")

                if not self.detector_thread or not self.detector_thread.is_alive():
                    self.detector_thread = start_event_detector_thread()
                    logger.info("Started event detector thread")

                self.check_timeout()

                files = self.get_pending_files()
                if not files:
                    frame_sampler_event.clear()
                    frame_sampler_event.wait()
                    continue

                frame_sampler_event.set()
                event_detector_event.set()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")

    def start(self):
        """Khởi động BatchScheduler."""
        if not self.running:
            # Log system info khi khởi động
            self.sys_monitor.log_system_info()
            
            self.running = True
            days = [(datetime.now(VIETNAM_TZ) - timedelta(days=i)).date().isoformat() for i in range(6, -1, -1)]
            logger.info(f"Initial scan for days: {days}")
            try:
                run_file_scan("default", days=days)
                frame_sampler_event.set()
            except Exception as e:
                logger.error(f"Initial scan failed: {e}")

            scan_thread = threading.Thread(target=self.scan_files)
            batch_thread = threading.Thread(target=self.run_batch)
            scan_thread.start()
            batch_thread.start()
            logger.info(f"BatchScheduler started, batch_size={self.batch_size}, scan_interval={self.scan_interval}")

    def stop(self):
        """Dừng BatchScheduler một cách an toàn."""
        if not self.running:
            return  # Đã dừng rồi
            
        logger.info("Stopping BatchScheduler...")
        self.running = False
        
        # Clear events để các thread có thể thoát
        frame_sampler_event.clear()
        event_detector_event.clear()
        
        # Đặt pause_event để các thread không bị block
        self.pause_event.set()
        
        # Dừng sampler threads với timeout ngắn
        for i, thread in enumerate(self.sampler_threads):
            if thread and thread.is_alive():
                try:
                    thread.join(timeout=0.5)  # Timeout ngắn
                    if thread.is_alive():
                        logger.warning(f"Sampler thread {i} did not stop gracefully")
                except Exception as e:
                    logger.warning(f"Error stopping sampler thread {i}: {e}")
        
        # Dừng detector thread
        if self.detector_thread and self.detector_thread.is_alive():
            try:
                self.detector_thread.join(timeout=0.5)
                if self.detector_thread.is_alive():
                    logger.warning("Detector thread did not stop gracefully")
            except Exception as e:
                logger.warning(f"Error stopping detector thread: {e}")
        
        logger.info("BatchScheduler stopped")