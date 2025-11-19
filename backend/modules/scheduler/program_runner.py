"""Program Runner Module for ePACK Video Post-Processing System.

This module manages the execution of video analysis threads for batch processing
existing video files. It coordinates computer vision analysis pipeline including
frame sampling, AI detection, and result processing stages.

Key Components:
    - Frame Sampler Threads: Process video frames for detection
    - Event Detector Thread: Analyze frame sampling logs for events
    - Video Processing Pipeline: IdleMonitor -> FrameSampler -> EventDetector
    - Thread Coordination: Uses events for synchronization between stages

Thread Architecture:
    - Multiple frame sampler threads run in parallel (batch processing)
    - Single event detector thread processes logs sequentially
    - Threads coordinate through threading.Event objects for workflow control
    - Video-level locking prevents concurrent processing of same file

Video Processing Workflow:
    1. IdleMonitor: Detects active periods in video to focus processing
    2. FrameSampler: Extracts frames and performs hand/QR detection
    3. EventDetector: Analyzes detection logs to identify significant events
    4. Database Updates: Track processing status throughout pipeline

Thread Safety:
    - Uses RWLocks for database access
    - Video-specific locks prevent concurrent processing of same file
    - Event coordination ensures proper workflow sequencing
"""

import threading
import time
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from modules.db_utils.safe_connection import safe_db_connection
from modules.technician.frame_sampler_trigger import FrameSamplerTrigger
from modules.technician.frame_sampler_no_trigger import FrameSamplerNoTrigger
from modules.technician.IdleMonitor import IdleMonitor
from modules.technician.event_detector import process_single_log
from modules.technician.retry_empty_event import start_retry_processor
from modules.utils.file_stability import validate_video_file
from .db_sync import db_rwlock, frame_sampler_event, event_detector_event, event_detector_done
from .config.scheduler_config import SchedulerConfig
import json
from modules.config.logging_config import get_logger

logger = get_logger(__name__, {"module": "program_runner"})
logger.info("Program runner logging initialized")

# Global state tracking for program execution status
# Used for coordinating between different processing modes
running_state: Dict[str, Any] = {
    "current_running": None,  # Currently active processing mode
    "days": None,             # Number of days for first run
    "custom_path": None,      # Path for custom processing
    "files": []               # List of files being processed
}

# Video-specific locks to prevent concurrent processing of the same file
# Key: video file path, Value: threading.Lock instance
video_locks: Dict[str, threading.Lock] = {}

# ==================== RETRY MECHANISM CONFIGURATION ====================
MAX_RETRIES = 3              # Retry 3 times before marking as Failed
RETRY_DELAY_SECONDS = 300    # Wait 5 minutes between retries


def get_retry_metadata(health_check_message_json):
    """
    Extract retry metadata from health_check_message JSON field.

    Args:
        health_check_message_json (str): JSON string from database

    Returns:
        dict: Retry metadata with keys: retry_count, retry_after, last_error
    """
    try:
        if health_check_message_json:
            data = json.loads(health_check_message_json)
            return {
                'retry_count': data.get('retry_count', 0),
                'retry_after': data.get('retry_after', 0),
                'last_error': data.get('last_error', None)
            }
    except (json.JSONDecodeError, TypeError):
        pass

    return {'retry_count': 0, 'retry_after': 0, 'last_error': None}


def mark_for_retry(conn, video_file, error_reason):
    """
    Mark video file for retry with updated metadata.

    Args:
        conn: Database connection
        video_file (str): Path to video file
        error_reason (str): Reason for retry
    """
    cursor = conn.cursor()

    # Get current retry metadata
    cursor.execute(
        "SELECT health_check_message FROM file_list WHERE file_path = ?",
        (video_file,)
    )
    result = cursor.fetchone()

    if not result:
        logger.error(f"File not found in database for retry: {video_file}")
        return

    current_metadata = get_retry_metadata(result[0])
    retry_count = current_metadata['retry_count'] + 1

    if retry_count > MAX_RETRIES:
        # Max retries exceeded - mark as Failed
        logger.error(
            f"❌ Max retries ({MAX_RETRIES}) exceeded for {os.path.basename(video_file)}: {error_reason}"
        )
        cursor.execute(
            "UPDATE file_list SET status = ?, is_processed = 1 WHERE file_path = ?",
            ("Failed", video_file)
        )
        return

    # Calculate next retry time
    retry_after = time.time() + RETRY_DELAY_SECONDS

    # Update metadata with retry info
    try:
        if result[0]:
            metadata = json.loads(result[0])
        else:
            metadata = {}
    except (json.JSONDecodeError, TypeError):
        metadata = {}

    metadata.update({
        'retry_count': retry_count,
        'retry_after': retry_after,
        'last_error': error_reason,
        'timestamp': datetime.now().isoformat()
    })

    # Keep status as 'pending' so it will be picked up again
    cursor.execute(
        """UPDATE file_list
           SET status = ?, health_check_message = ?
           WHERE file_path = ?""",
        ("pending", json.dumps(metadata), video_file)
    )

    logger.warning(
        f"⏳ Retry {retry_count}/{MAX_RETRIES} scheduled for {os.path.basename(video_file)} "
        f"in {RETRY_DELAY_SECONDS//60} minutes: {error_reason}"
    )


def should_retry_now(health_check_message_json):
    """
    Check if enough time has passed to retry processing.

    Args:
        health_check_message_json (str): JSON metadata from database

    Returns:
        bool: True if should retry now, False if need to wait
    """
    metadata = get_retry_metadata(health_check_message_json)

    if metadata['retry_count'] == 0:
        return True  # First attempt, no retry delay

    retry_after = metadata.get('retry_after', 0)
    return time.time() >= retry_after


def start_frame_sampler_thread(batch_size: int = 1) -> List[threading.Thread]:
    """Start multiple frame sampler threads for parallel video processing.
    
    Creates and starts a pool of frame sampler threads that will process
    videos concurrently. Each thread runs the run_frame_sampler function
    which handles the complete video processing pipeline.
    
    Args:
        batch_size (int): Number of frame sampler threads to create
        
    Returns:
        List[threading.Thread]: List of started thread objects
        
    Thread Coordination:
        All threads wait on frame_sampler_event and process videos from
        the shared database queue. Video-level locking prevents conflicts.
    """
    logger.info(f"Starting {batch_size} frame sampler threads", extra={"thread_id": threading.current_thread().ident})
    threads = []
    for i in range(batch_size):
        frame_sampler_thread = threading.Thread(
            target=run_frame_sampler, 
            name=f"FrameSampler-{i}"
        )
        frame_sampler_thread.start()
        threads.append(frame_sampler_thread)
    return threads

def run_frame_sampler() -> None:
    """Main frame sampler thread function for video processing.
    
    This function runs continuously in each frame sampler thread, processing
    videos from the database queue. It coordinates the complete video processing
    pipeline including:
    
    1. Video Selection: Gets pending videos from database queue
    2. Idle Monitoring: Analyzes video for active periods
    3. Frame Sampling: Processes frames for hand/QR detection
    4. Status Updates: Tracks processing progress in database
    5. Event Coordination: Signals event detector when ready
    
    Video Processing Pipeline:
        IdleMonitor -> FrameSampler (Trigger/NoTrigger) -> Log Generation
    
    Thread Lifecycle:
        - Waits on frame_sampler_event for work signals
        - Processes videos until queue is empty
        - Coordinates with event detector for log processing
        - Handles timeouts and error conditions
    
    Thread Safety:
        - Uses video-specific locks to prevent concurrent processing
        - RWLocks for database access
        - Event coordination for workflow control
    """
    logger.info("Frame sampler thread started", extra={"thread_id": threading.current_thread().ident})
    
    # Main processing loop - continues until thread termination
    while True:
        # Wait for signal that work is available
        frame_sampler_event.wait()
        logger.debug("Frame sampler event received")
        try:
            # Get list of pending video files from database queue (including retry metadata)
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT file_path, camera_name, health_check_message "
                        "FROM file_list "
                        "WHERE is_processed = 0 "
                        "ORDER BY priority DESC, created_at ASC"
                    )
                    video_files = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
                logger.info(f"Found {len(video_files)} unprocessed video files")

            # If no work available, clear event and wait for new signals
            if not video_files:
                logger.info("No video files to process, clearing event")
                frame_sampler_event.clear()
                continue

            # Process each video file in the queue
            for video_file, camera_name, health_check_message in video_files:
                # Check if enough time has passed for retry
                if not should_retry_now(health_check_message):
                    retry_meta = get_retry_metadata(health_check_message)
                    wait_time = int(retry_meta['retry_after'] - time.time())
                    logger.debug(
                        f"Skipping {os.path.basename(video_file)}: "
                        f"retry scheduled in {wait_time}s (attempt {retry_meta['retry_count']}/{MAX_RETRIES})"
                    )
                    continue

                # Check if video is already being processed or completed
                with db_rwlock.gen_rlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT status, is_processed FROM file_list WHERE file_path = ?", (video_file,))
                        result = cursor.fetchone()
                    if result and (result[0] in ["Processing", "Done", "health_check_failed"] or result[1] == 1):
                        logger.info(f"Skipping video {video_file}: already being processed or completed")
                        continue

                # Acquire video-specific lock to prevent concurrent processing
                with db_rwlock.gen_wlock():
                    if video_file not in video_locks:
                        video_locks[video_file] = threading.Lock()
                video_lock = video_locks[video_file]
                
                # Skip if another thread is already processing this video
                if not video_lock.acquire(blocking=False):
                    logger.info(f"Skipping video {video_file}: locked by another thread")
                    continue

                try:
                    logger.info(f"Processing video: {video_file}")
                    
                    # STEP 1: Load camera profile configuration for processing parameters
                    with db_rwlock.gen_rlock():
                        with safe_db_connection() as conn:
                            cursor = conn.cursor()
                            search_name = camera_name if camera_name else "CamTest"
                            if not camera_name:
                                logger.warning(f"No camera_name for {video_file}, falling back to CamTest")
                            
                            # Query packing profiles for camera-specific configuration
                            cursor.execute("SELECT id, profile_name, qr_trigger_area, packing_area FROM packing_profiles WHERE profile_name LIKE ?", (f'%{search_name}%',))
                            profiles = cursor.fetchall()
                    
                    # Select the profile with the highest ID (most recent)
                    trigger = [0, 0, 0, 0]  # Default trigger area coordinates
                    packing_area = None      # Default packing area (no restriction)
                    selected_profile = None
                    
                    if profiles:
                        selected_profile = max(profiles, key=lambda x: x[0])  # Select highest ID
                        profile_id, profile_name, qr_trigger_area, packing_area_raw = selected_profile
                        # Parse QR trigger area coordinates [x, y, width, height]
                        try:
                            trigger = json.loads(qr_trigger_area) if qr_trigger_area else [0, 0, 0, 0]
                            if not isinstance(trigger, list) or len(trigger) != 4:
                                logger.error(f"Invalid qr_trigger_area for {profile_name}: {qr_trigger_area}, using default [0, 0, 0, 0]")
                                trigger = [0, 0, 0, 0]
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse qr_trigger_area for {profile_name}: {e}, using default [0, 0, 0, 0]")
                            trigger = [0, 0, 0, 0]
                        # Parse packing area coordinates for region-of-interest processing
                        try:
                            if packing_area_raw:
                                parsed = json.loads(packing_area_raw)
                                if isinstance(parsed, list) and len(parsed) == 4:
                                    packing_area = tuple(parsed)  # Convert to tuple for consistency
                                elif isinstance(parsed, dict) and all(key in parsed for key in ['x', 'y', 'w', 'h']):
                                    packing_area = (parsed['x'], parsed['y'], parsed['w'], parsed['h'])
                                else:
                                    logger.error(f"Invalid packing_area format for {profile_name}: {packing_area_raw}, using default None")
                                    packing_area = None
                            logger.info(f"Selected profile id={profile_id}, profile_name={profile_name}, qr_trigger_area={trigger}, packing_area={packing_area}")
                        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
                            logger.error(f"Failed to parse packing_area for {profile_name}: {e}, using default None")
                            packing_area = None
                    else:
                        logger.warning(f"No profile found for camera {search_name}, using default qr_trigger_area=[0, 0, 0, 0], packing_area=None")
                    
                    # STEP 2: Run IdleMonitor to detect active periods in the video
                    # This optimization focuses processing on periods with actual activity
                    idle_monitor = IdleMonitor()
                    logger.info(f"Running IdleMonitor for {video_file}")

                    # ==================== VIDEO VALIDATION & ERROR HANDLING ====================
                    # Try to process video with IdleMonitor (may fail if file incomplete/corrupted)
                    try:
                        idle_monitor.process_video(video_file, camera_name, packing_area)
                        work_block_queue = idle_monitor.get_work_block_queue()
                    except Exception as e:
                        # IdleMonitor failed - validate video file to determine if retry needed
                        logger.error(f"IdleMonitor failed for {video_file}: {e}")

                        is_valid, reason = validate_video_file(video_file)

                        if not is_valid:
                            # Video file is incomplete/corrupted - mark for retry
                            logger.warning(f"Video validation failed: {reason}")
                            with db_rwlock.gen_wlock():
                                with safe_db_connection() as conn:
                                    mark_for_retry(conn, video_file, f"OpenCV error: {reason}")
                                    conn.commit()
                        else:
                            # Video file is valid but IdleMonitor failed for other reasons
                            # This shouldn't happen, but mark as Failed to avoid infinite loop
                            logger.error(f"Unexpected error: Video is valid but IdleMonitor failed: {e}")
                            with db_rwlock.gen_wlock():
                                with safe_db_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "UPDATE file_list SET status = ?, is_processed = 1 WHERE file_path = ?",
                                        ("Failed", video_file)
                                    )
                                    conn.commit()

                        continue  # Skip to next file

                    # Skip videos with no active periods to save processing time
                    if work_block_queue.empty():
                        logger.info(f"No work blocks found for {video_file}, skipping FrameSampler and log file creation")
                        with db_rwlock.gen_wlock():
                            with safe_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("UPDATE file_list SET status = ?, is_processed = 1 WHERE file_path = ?", ("Done", video_file))
                        continue  # Skip frame sampling for inactive videos
                    # STEP 3: Select appropriate FrameSampler based on trigger configuration
                    if trigger != [0, 0, 0, 0]:
                        # Use trigger-based sampling when QR trigger area is defined
                        frame_sampler = FrameSamplerTrigger()
                        logger.info(f"Using FrameSamplerTrigger for {video_file}")
                    else:
                        # Use continuous sampling when no trigger area is defined
                        frame_sampler = FrameSamplerNoTrigger()
                        logger.info(f"Using FrameSamplerNoTrigger for {video_file}")

                    # STEP 4: Update database status to indicate processing has started
                    with db_rwlock.gen_wlock():
                        with safe_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("Processing", video_file))
                        logger.debug(f"Updated status for {video_file} to 'Processing'")

                    # STEP 4.5: RUN HEALTH CHECK BEFORE ALL BLOCKS (NEW FIX)
                    # This ensures if health check is CRITICAL, ALL blocks are skipped
                    # Not just the first block
                    health_check_failed = False
                    from modules.technician.camera_health_checker import should_run_health_check, run_health_check

                    if should_run_health_check(camera_name):
                        logger.info(f"[HEALTH] Running health check BEFORE processing blocks for {camera_name}")
                        health_result = run_health_check(camera_name=camera_name, video_path=video_file)

                        if health_result.get('success') and health_result.get('status') == 'CRITICAL':
                            logger.error(f"[HEALTH] 🛑 Health check CRITICAL for {camera_name} - SKIPPING ALL BLOCKS")
                            health_check_failed = True

                            # Mark file as health check failed
                            with db_rwlock.gen_wlock():
                                with safe_db_connection() as conn:
                                    cursor = conn.cursor()
                                    health_metadata = json.dumps({
                                        "health_check_required": True,
                                        "health_check_done": True,
                                        "health_check_status": "CRITICAL"
                                    })
                                    cursor.execute("""
                                        UPDATE file_list
                                        SET health_check_failed = 1,
                                            health_check_message = ?,
                                            status = 'health_check_failed'
                                        WHERE file_path = ?
                                    """, (health_metadata, video_file))
                                    conn.commit()

                            # Clear all remaining blocks to prevent processing
                            while not work_block_queue.empty():
                                work_block_queue.get()
                            logger.error(f"[HEALTH] Cleared all work blocks for {video_file}")

                    # STEP 5: Process video blocks identified by IdleMonitor
                    log_file = None
                    if not health_check_failed:  # Only process if health check passed
                        while not work_block_queue.empty():
                            work_block = work_block_queue.get()
                            start_time = work_block['start_time']
                            end_time = work_block['end_time']
                            logger.info(f"Processing video block: start_time={start_time}, end_time={end_time}")

                            # ✅ Run frame sampling on the active video segment
                            # MUST be INSIDE loop to process ALL blocks, not just last one!
                            log_file = frame_sampler.process_video(
                                video_file,
                                video_lock=frame_sampler.video_lock,
                                get_packing_area_func=frame_sampler.get_packing_area,
                                process_frame_func=frame_sampler.process_frame,
                                frame_interval=frame_sampler.frame_interval,
                                start_time=start_time,
                                end_time=end_time
                            )
                    
                    # STEP 6: Update final processing status and trigger event detection
                    # ✅ IMPORTANT: Only update if health check passed!
                    # If health_check_failed, status already set to 'health_check_failed' in STEP 4.5
                    if not health_check_failed:
                        with db_rwlock.gen_wlock():
                            with safe_db_connection() as conn:
                                cursor = conn.cursor()
                                if log_file:
                                    cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("Done", video_file))
                                    event_detector_event.set()  # Signal event detector that logs are ready
                                    logger.info(f"Video {video_file} processed successfully, log file: {log_file}")
                                else:
                                    cursor.execute("UPDATE file_list SET status = ? WHERE file_path = ?", ("Error", video_file))
                                    logger.error(f"Failed to process video {video_file}")
                    
                    # STEP 7: Wait for event detector to process the generated logs
                    # ✅ IMPORTANT: Only wait if processing happened (health check passed)
                    # If health_check_failed, skip waiting to allow lock release
                    if not health_check_failed:
                        logger.info(f"Frame Sampler pausing after processing {video_file}, waiting for Event Detector...")
                        while not event_detector_done.is_set():
                            time.sleep(1)  # Wait for event detector to complete log analysis
                    else:
                        logger.info(f"Frame Sampler skipping Event Detector wait for {video_file} (health check failed)")

                finally:
                    # Clean up video lock and remove from global locks dictionary
                    video_lock.release()
                    with db_rwlock.gen_wlock():
                        video_locks.pop(video_file, None)
                    logger.debug(f"Released lock for {video_file}")

            # Clear event after processing all available videos
            frame_sampler_event.clear()
            logger.info("All video files processed, clearing frame sampler event")
            
        except Exception as e:
            logger.error(f"Error in Frame Sampler thread: {str(e)}")
            frame_sampler_event.clear()  # Ensure thread goes back to waiting state on error

def start_event_detector_thread() -> threading.Thread:
    """Start the event detector thread for log analysis.
    
    Creates and starts a single event detector thread that processes
    frame sampling logs to identify significant events and patterns.
    
    Returns:
        threading.Thread: The started event detector thread
        
    Thread Coordination:
        The event detector waits on event_detector_event and processes
        logs generated by frame sampler threads.
    """
    logger.info("Starting event detector thread", extra={"thread_id": threading.current_thread().ident})
    event_detector_thread = threading.Thread(target=run_event_detector, name="EventDetector")
    event_detector_thread.start()
    return event_detector_thread

def run_event_detector() -> None:
    """Main event detector thread function for log analysis.
    
    This function runs continuously to process frame sampling logs and
    identify significant events. It coordinates with frame sampler threads
    to ensure proper workflow sequencing.
    
    Event Detection Pipeline:
        1. Wait for signal from frame samplers that logs are ready
        2. Query database for unprocessed log files
        3. Process each log file through event detection algorithms
        4. Signal frame samplers that processing is complete
    
    Thread Coordination:
        - Waits on event_detector_event for work signals
        - Sets event_detector_done to signal frame samplers
        - Ensures sequential processing of logs for consistency
    
    Thread Safety:
        Uses RWLocks for database access and event coordination
        for proper workflow control.
    """
    logger.info("Event detector thread started", extra={"thread_id": threading.current_thread().ident})
    
    # Main event detection loop - continues until thread termination
    while True:
        # Wait for signal that logs are ready for processing
        event_detector_event.wait()
        logger.debug("Event detector event received")
        try:
            # Get list of unprocessed log files from database
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT log_file FROM processed_logs WHERE is_processed = 0")
                    log_files = [row[0] for row in cursor.fetchall()]
                logger.info(f"Found {len(log_files)} unprocessed log files")

            # If no logs to process, signal frame samplers to continue
            if not log_files:
                event_detector_event.clear()
                event_detector_done.set()  # Signal frame samplers they can continue
                logger.info("No log files to process, clearing event and signaling done")
                continue

            # Process each log file through event detection algorithms
            for log_file in log_files:
                logger.info(f"Event Detector processing: {log_file}")
                process_single_log(log_file)  # Analyze log for events and patterns
                
            # Signal completion to frame samplers after processing all logs
            event_detector_event.clear()
            event_detector_done.set()  # Allow frame samplers to continue with next video
            logger.info("All log files processed, clearing event and signaling done")
            
        except Exception as e:
            logger.error(f"Error in Event Detector thread: {str(e)}")
            event_detector_event.clear()
            event_detector_done.set()  # Still signal completion even on error to prevent deadlock
