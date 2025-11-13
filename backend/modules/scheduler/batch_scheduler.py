"""Batch Scheduler Module for V_Track Video Post-Processing System.

This module provides automated batch processing of existing video files from local storage
and Google Drive. It manages video analysis workflows with dynamic resource optimization
and system monitoring capabilities for computer vision tasks.

Classes:
    SystemMonitor: Monitors system resources and calculates optimal batch sizes
    BatchScheduler: Main scheduler class for coordinating video processing tasks

Thread Safety:
    All database operations are protected by RWLocks (db_rwlock) to ensure thread-safe
    concurrent access. The scheduler manages multiple worker threads and coordinates
    their execution using threading events.

Key Features:
    - Dynamic batch size adjustment based on CPU/memory usage
    - Timeout handling for stalled video processing
    - Coordinated file scanning and processing
    - Thread pool management for frame samplers and event detectors
"""

import os
import threading
import time
import sqlite3
import psutil
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import List, Tuple, Optional
from modules.db_utils.safe_connection import safe_db_connection
from modules.config.logging_config import get_logger
from modules.utils.simple_timezone import get_system_timezone_from_db
from .db_sync import (
    db_rwlock,
    frame_sampler_event,
    event_detector_event,
    system_idle_event,
    retry_in_progress_flag,
)
from .file_lister import run_file_scan
from .program_runner import (
    start_frame_sampler_thread,
    start_event_detector_thread,
    start_retry_processor,
)
from .config.scheduler_config import SchedulerConfig
from modules.utils.cleanup import cleanup_service

logger = get_logger(__name__, {"module": "batch_scheduler"})
logger.info("BatchScheduler logging initialized")


class SystemMonitor:
    """Monitors system resources and dynamically calculates optimal batch sizes.

    This class continuously monitors CPU and memory usage to determine the appropriate
    batch size for video processing. It prevents system overload by reducing batch sizes
    when resources are constrained and increases them when resources are available.

    Attributes:
        cpu_threshold_low (float): CPU usage threshold below which batch size can be increased
        cpu_threshold_high (float): CPU usage threshold above which batch size must be reduced
        base_batch_size (int): Default batch size to return to under normal conditions
        max_batch_size (int): Maximum allowed batch size regardless of available resources

    Thread Safety:
        This class is thread-safe and can be called from multiple threads simultaneously.
    """

    def __init__(self):
        self.cpu_threshold_low = SchedulerConfig.CPU_THRESHOLD_LOW
        self.cpu_threshold_high = SchedulerConfig.CPU_THRESHOLD_HIGH
        self.base_batch_size = SchedulerConfig.BATCH_SIZE_DEFAULT
        self.max_batch_size = SchedulerConfig.BATCH_SIZE_MAX

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage from the system.

        Returns:
            float: CPU usage percentage (0-100), or 50 if unable to determine

        Note:
            Uses psutil with a 1-second sampling interval for accurate measurement.
            Returns a fallback value of 50% if any errors occur during measurement.
        """
        try:
            # Lấy CPU usage trung bình trong 1 giây và đảm bảo trả về float
            cpu_percent = psutil.cpu_percent(interval=1)
            # Cast về float để tránh lỗi type hint khi psutil trả về list
            if isinstance(cpu_percent, list):
                cpu_percent = sum(cpu_percent) / len(cpu_percent)
            logger.debug(f"Current CPU usage: {cpu_percent}%")
            return float(cpu_percent)
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 50.0  # Fallback value nếu có lỗi

    def get_memory_usage(self) -> float:
        """Get current memory usage percentage from the system.

        Returns:
            float: Memory usage percentage (0-100), or 50 if unable to determine

        Note:
            Returns a fallback value of 50% if any errors occur during measurement.
        """
        try:
            memory_percent = psutil.virtual_memory().percent
            logger.debug(f"Current memory usage: {memory_percent}%")
            return memory_percent
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 50.0  # Fallback value

    def get_batch_size(self, current_batch_size: int) -> int:
        """Calculate optimal batch size based on current system resource usage.

        This method implements a dynamic batch size adjustment algorithm:
        - Reduces batch size when CPU > high threshold OR memory > memory threshold
        - Increases batch size when CPU < low threshold AND memory < 70%
        - Maintains current size when resources are in the stable range

        Args:
            current_batch_size (int): Current batch size being used

        Returns:
            int: Recommended batch size (between base_batch_size and max_batch_size)

        Algorithm Details:
            - Reduction: Decreases by 1 when overloaded (min: base_batch_size)
            - Increase: Increases by 1 when underutilized (max: max_batch_size)
            - Stability: No change when resources are in acceptable range
        """
        cpu_usage = self.get_cpu_usage()
        memory_usage = self.get_memory_usage()

        logger.debug(f"Resource usage - CPU: {cpu_usage}%, Memory: {memory_usage}%")

        # Check for resource overload - reduce batch size to prevent system strain
        if cpu_usage > self.cpu_threshold_high or memory_usage > SchedulerConfig.MEMORY_THRESHOLD:
            if current_batch_size > self.base_batch_size:
                new_batch_size = current_batch_size - 1
                logger.warning(
                    f"High resource usage (CPU: {cpu_usage}%, RAM: {memory_usage}%), reducing batch size: {current_batch_size} -> {new_batch_size}"
                )
                return new_batch_size

        # Check for resource availability - increase batch size to improve throughput
        elif cpu_usage < self.cpu_threshold_low and memory_usage < 70:
            if current_batch_size < self.max_batch_size:
                new_batch_size = current_batch_size + 1
                logger.info(
                    f"Low resource usage (CPU: {cpu_usage}%, RAM: {memory_usage}%), increasing batch size: {current_batch_size} -> {new_batch_size}"
                )
                return new_batch_size

        # Maintain current batch size when resources are in stable range
        return current_batch_size

    def log_system_info(self) -> None:
        """Log system information at startup for diagnostic purposes.

        Logs:
            - CPU core count
            - Total RAM in GB
            - Batch size configuration (base and max)
            - CPU threshold settings

        This information is useful for understanding system capacity and
        troubleshooting performance issues.
        """
        try:
            cpu_count = psutil.cpu_count()
            memory_total = psutil.virtual_memory().total / (1024**3)  # GB
            logger.info(f"System info - CPU cores: {cpu_count}, Total RAM: {memory_total:.1f}GB")
            logger.info(
                f"Batch size config - Base: {self.base_batch_size}, Max: {self.max_batch_size}"
            )
            logger.info(
                f"CPU thresholds - Low: {self.cpu_threshold_low}%, High: {self.cpu_threshold_high}%"
            )
        except Exception as e:
            logger.error(f"Error logging system info: {e}")


class BatchScheduler:
    """Main scheduler class for coordinating video processing tasks.

    The BatchScheduler is the central component that manages the entire video processing
    workflow. It coordinates file scanning, resource monitoring, thread management,
    and batch processing execution.

    Key Responsibilities:
        - Dynamic batch size management based on system resources
        - Coordination of frame sampler and event detector threads
        - Periodic file scanning for new video content
        - Timeout handling for stalled processing jobs
        - Thread lifecycle management (start/stop/pause/resume)

    Architecture:
        - Runs two main background threads: file scanner and batch processor
        - Manages a pool of frame sampler threads (size determined by SystemMonitor)
        - Coordinates with a single event detector thread
        - Uses threading events for inter-thread communication

    Thread Safety:
        All database operations use RWLocks to ensure thread-safe concurrent access.
        Thread coordination is handled through threading.Event objects.

    Attributes:
        batch_size (int): Current number of frame sampler threads
        sys_monitor (SystemMonitor): System resource monitor for dynamic sizing
        running (bool): Flag indicating if scheduler is active
        pause_event (threading.Event): Event for pause/resume functionality
        sampler_threads (List[threading.Thread]): List of active frame sampler threads
        detector_thread (threading.Thread): Single event detector thread
    """

    def __init__(self) -> None:
        """Initialize the BatchScheduler with default configuration.

        Sets up:
            - Default batch size from configuration
            - System monitor instance
            - Scan interval and timeout settings
            - Thread management structures
            - Pause/resume event (initially set to running)
        """
        self.batch_size = SchedulerConfig.BATCH_SIZE_DEFAULT
        self.sys_monitor = SystemMonitor()
        self.scan_interval = SchedulerConfig.SCAN_INTERVAL_SECONDS
        self.timeout_seconds = SchedulerConfig.TIMEOUT_SECONDS
        self.running = False
        self.queue_limit = SchedulerConfig.QUEUE_LIMIT
        self.sampler_threads = []
        self.detector_thread = None
        self.retry_thread = None
        self.cleanup_thread = None
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start in unpaused state
        self.last_system_cleanup = 0  # Timestamp of last system cleanup
        self.last_output_cleanup = 0  # Timestamp of last output cleanup

    def pause(self) -> None:
        """Pause the BatchScheduler, stopping new file processing.

        This method pauses all scheduler activity without terminating threads.
        Existing processing will complete, but no new files will be processed
        until resume() is called.

        Thread Safety:
            Safe to call from any thread. Uses threading.Event for coordination.
        """
        logger.info(f"BatchScheduler paused, current_batch_size={self.batch_size}")
        self.pause_event.clear()

    def resume(self) -> None:
        """Resume the BatchScheduler, allowing new file processing to continue.

        This method resumes scheduler activity that was previously paused.
        File scanning and processing will continue from where it left off.

        Thread Safety:
            Safe to call from any thread. Uses threading.Event for coordination.
        """
        logger.info(f"BatchScheduler resumed, current_batch_size={self.batch_size}")
        self.pause_event.set()

    def get_pending_files(self):
        """Get list of unprocessed files, limited by queue_limit."""
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT file_path, camera_name FROM file_list WHERE status = 'pending' AND is_processed = 0 ORDER BY priority DESC, created_at ASC LIMIT ?",
                        (self.queue_limit,),
                    )
                    files = [(row[0], row[1]) for row in cursor.fetchall()]
            return files
        except Exception as e:
            logger.error(f"Error retrieving pending files: {e}")
            return []

    def update_file_status(self, file_path, status):
        """Update file status in file_list."""
        try:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE file_list SET status = ?, is_processed = ? WHERE file_path = ?",
                        (
                            status,
                            1 if status in ["completed", "error", "timeout"] else 0,
                            file_path,
                        ),
                    )
        except Exception as e:
            logger.error(f"Error updating file status for {file_path}: {e}")

    def check_timeout(self):
        """Check and update timeout status for files over 900s with timezone-aware timestamps."""
        try:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT file_path, created_at FROM file_list WHERE status = 'frame sampling...'"
                    )

                    now_utc = datetime.now(timezone.utc)

                    for row in cursor.fetchall():
                        file_path, created_at_str = row

                        if not created_at_str:
                            # Fallback for missing timestamps
                            created_at_utc = datetime.min.replace(tzinfo=timezone.utc)
                            logger.warning(
                                f"Missing created_at timestamp for {file_path}, using minimum datetime"
                            )
                        else:
                            try:
                                # Parse created_at timestamp
                                if "Z" in created_at_str or "+" in created_at_str:
                                    # Already has timezone info
                                    created_at_utc = datetime.fromisoformat(
                                        created_at_str.replace("Z", "+00:00")
                                    )
                                    # Convert to UTC if not already
                                    if created_at_utc.tzinfo != timezone.utc:
                                        created_at_utc = created_at_utc.astimezone(timezone.utc)
                                else:
                                    # Assume naive datetime is in system timezone
                                    created_at_naive = datetime.fromisoformat(created_at_str)
                                    created_at_utc = created_at_naive.replace(
                                        tzinfo=ZoneInfo(get_system_timezone_from_db())
                                    ).astimezone(timezone.utc)
                            except (ValueError, TypeError) as e:
                                logger.warning(
                                    f"Failed to parse created_at '{created_at_str}' for {file_path}: {e}"
                                )
                                created_at_utc = datetime.min.replace(tzinfo=timezone.utc)

                        # Calculate timeout in UTC
                        time_diff = (now_utc - created_at_utc).total_seconds()

                        if time_diff > self.timeout_seconds:
                            cursor.execute(
                                "UPDATE file_list SET status = ?, is_processed = 1 WHERE file_path = ?",
                                ("timeout", file_path),
                            )

                            # Log timeout with timezone context
                            local_now = now_utc.astimezone(ZoneInfo(get_system_timezone_from_db()))
                            local_created = created_at_utc.astimezone(
                                ZoneInfo(get_system_timezone_from_db())
                            )

                            logger.warning(
                                f"Timeout processing {file_path} after {self.timeout_seconds}s "
                                f"(started: {local_created.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                                f"now: {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                                f"elapsed: {time_diff:.1f}s)"
                            )
        except Exception as e:
            logger.error(f"Error checking timeout: {e}")

    def check_system_idle(self):
        """Check if system is idle - all videos processed and no pending files.

        The system is considered idle when:
            1. file_list has no unprocessed files (is_processed=0 count = 0)
            2. No files are currently being processed

        Returns:
            bool: True if system is idle, False otherwise
        """
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM file_list WHERE is_processed = 0")
                    pending_count = cursor.fetchone()[0]

            is_idle = pending_count == 0
            if is_idle:
                logger.info("✅ System IDLE: no pending files detected")
            return is_idle

        except Exception as e:
            logger.error(f"❌ Error checking system idle: {e}")
            return False

    def monitor_cleanup(self):
        """Monitor and run cleanup tasks periodically.

        Runs:
        - System cleanup every 1 hour (logs, cache, old logs)
        - Output cleanup every 24 hours (based on retention config)

        This ensures the system doesn't accumulate excessive temporary files
        that could eventually exhaust disk space.
        """
        logger.info("🧹 Cleanup monitor started")

        while self.running:
            try:
                current_time = time.time()

                # System cleanup - every 1 hour (3600 seconds)
                if current_time - self.last_system_cleanup > 3600:
                    threading.Thread(target=self._run_system_cleanup, daemon=True).start()
                    self.last_system_cleanup = current_time

                # Output cleanup - every 24 hours (86400 seconds)
                if current_time - self.last_output_cleanup > 86400:
                    threading.Thread(target=self._run_output_cleanup, daemon=True).start()
                    self.last_output_cleanup = current_time

                # Check every 5 minutes
                time.sleep(300)

            except Exception as e:
                logger.error(f"❌ Error in cleanup monitor: {e}")
                time.sleep(300)

    def _run_system_cleanup(self):
        """Execute system cleanup in background thread"""
        try:
            result = cleanup_service.cleanup_system_files()
            logger.info(
                f"✅ System cleanup: {result['total_deleted']} files deleted, {result['total_freed_mb']:.2f} MB freed"
            )
        except Exception as e:
            logger.error(f"❌ System cleanup error: {e}")

    def _run_output_cleanup(self):
        """Execute output cleanup in background thread"""
        try:
            result = cleanup_service.cleanup_output_files()
            logger.info(
                f"✅ Output cleanup: {result.get('deleted', 0)} files deleted, {result.get('freed_mb', 0):.2f} MB freed"
            )
        except Exception as e:
            logger.error(f"❌ Output cleanup error: {e}")

    def monitor_system_idle(self):
        """Monitor and signal when system becomes idle for PASS 3 retry.

        Workflow:
            1. Check every 5 seconds if system is idle
            2. When idle: Set retry_in_progress_flag → Set system_idle_event
            3. Wait for retry to complete (system_idle_event clears when done)
            4. Clear retry_in_progress_flag to unblock file scanner
            5. Resume checking

        This ensures:
            - Retry only runs when no files are being processed
            - File scanner is blocked during retry
            - No race conditions between file loading and retry
        """
        logger.info("🔍 System idle monitor started")

        while self.running:
            try:
                if self.check_system_idle():
                    # System is idle - set up for retry
                    logger.info("⏳ Starting retry: blocking file scanner")
                    retry_in_progress_flag.set()

                    # Signal retry processor to start
                    system_idle_event.set()
                    logger.info("🚀 Idle signal set - retry processor will start")

                    # Wait for retry to complete
                    # Retry processor will clear system_idle_event when done
                    while system_idle_event.is_set() and self.running:
                        time.sleep(1)

                    # Retry complete - unblock file scanner
                    logger.info("✅ Retry complete: unblocking file scanner")
                    retry_in_progress_flag.clear()

                    # Wait 1 minute before checking idle again
                    time.sleep(60)
                else:
                    # Still processing - check again in 5 seconds
                    time.sleep(5)

            except Exception as e:
                logger.error(f"❌ Error in idle monitor: {e}")
                system_idle_event.clear()
                retry_in_progress_flag.clear()
                time.sleep(5)

    def scan_files(self):
        """Scan for new files periodically (15 minutes)."""
        logger.info("Starting periodic scan")
        while self.running:
            try:
                logger.debug(
                    "Checking periodic scan, running=%s, paused=%s",
                    self.running,
                    not self.pause_event.is_set(),
                )
                self.pause_event.wait()
                with db_rwlock.gen_rlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT COUNT(*) FROM file_list WHERE status = 'pending' AND is_processed = 0"
                        )
                        pending_count = cursor.fetchone()[0]

                if pending_count >= self.queue_limit:
                    logger.warning(
                        f"Queue full ({pending_count}/{self.queue_limit}), skipping file scan"
                    )
                else:
                    run_file_scan("default")
                    frame_sampler_event.set()
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Error in file scan: {e}")

    def run_batch(self):
        """Run batch file processing, using run_frame_sampler."""
        while self.running:
            try:
                self.pause_event.wait()
                self.batch_size = self.sys_monitor.get_batch_size(self.batch_size)

                if not self.sampler_threads or len(self.sampler_threads) != self.batch_size:
                    for thread in self.sampler_threads:
                        if thread.is_alive():
                            thread.join(timeout=SchedulerConfig.THREAD_JOIN_TIMEOUT)
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
        """Start BatchScheduler."""
        if not self.running:
            # Log system info on startup
            self.sys_monitor.log_system_info()

            self.running = True
            # Fixed: pass number of days (int) instead of list for days parameter
            initial_scan_days = 7  # Scan first 7 days
            logger.info(f"Initial scan for {initial_scan_days} days")
            try:
                run_file_scan("default", days=initial_scan_days)
                frame_sampler_event.set()
            except Exception as e:
                logger.error(f"Initial scan failed: {e}")

            scan_thread = threading.Thread(target=self.scan_files)
            batch_thread = threading.Thread(target=self.run_batch)
            idle_monitor_thread = threading.Thread(
                target=self.monitor_system_idle, name="IdleMonitor"
            )
            idle_monitor_thread.daemon = True  # Exit when main thread exits
            cleanup_monitor_thread = threading.Thread(
                target=self.monitor_cleanup, name="CleanupMonitor"
            )
            cleanup_monitor_thread.daemon = True  # Exit when main thread exits

            scan_thread.start()
            batch_thread.start()
            idle_monitor_thread.start()
            cleanup_monitor_thread.start()

            # Start PASS 3 retry processor (runs only when idle)
            if not self.retry_thread or not self.retry_thread.is_alive():
                self.retry_thread = start_retry_processor()
                logger.info("✅ PASS 3 retry processor started")

            logger.info(
                f"BatchScheduler started, batch_size={self.batch_size}, scan_interval={self.scan_interval}"
            )

    def stop(self):
        """Stop BatchScheduler safely."""
        if not self.running:
            return  # Already stopped

        logger.info("Stopping BatchScheduler...")
        self.running = False

        # Clear events so threads can exit
        frame_sampler_event.clear()
        event_detector_event.clear()

        # Set pause_event so threads don't block
        self.pause_event.set()

        # Stop sampler threads with short timeout
        for i, thread in enumerate(self.sampler_threads):
            if thread and thread.is_alive():
                try:
                    thread.join(timeout=SchedulerConfig.THREAD_JOIN_TIMEOUT)  # Short timeout
                    if thread.is_alive():
                        logger.warning(f"Sampler thread {i} did not stop gracefully")
                except Exception as e:
                    logger.warning(f"Error stopping sampler thread {i}: {e}")

        # Stop detector thread
        if self.detector_thread and self.detector_thread.is_alive():
            try:
                self.detector_thread.join(timeout=SchedulerConfig.THREAD_JOIN_TIMEOUT)
                if self.detector_thread.is_alive():
                    logger.warning("Detector thread did not stop gracefully")
            except Exception as e:
                logger.warning(f"Error stopping detector thread: {e}")

        logger.info("BatchScheduler stopped")
