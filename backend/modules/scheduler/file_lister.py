"""File Lister Module for V_Track Video Processing System.

This module handles video file discovery, scanning, and metadata extraction for the
V_Track processing pipeline. It supports different scanning strategies and integrates
with FFprobe for accurate video metadata extraction.

Scanning Strategies:
    - First Run: Scan videos from a specified number of days (initial setup)
    - Default: Continuous scanning for new videos with time-based filtering
    - Custom: Scan specific file or directory path on-demand

Key Features:
    - FFprobe integration for accurate video metadata extraction
    - Vietnam timezone handling for consistent time operations
    - Working hours and working days filtering
    - Camera-specific filtering based on configuration
    - Database integration for persistent file tracking
    - Stale job cleanup and timeout handling

Metadata Extraction:
    Uses FFprobe to extract creation_time from video metadata, with fallbacks to
    filesystem timestamps. Handles various video formats and timezone conversions.

Performance Optimizations:
    - Time-based filtering to reduce unnecessary processing
    - Camera selection filtering to focus on specific sources
    - Batch database operations for improved efficiency
    - Queue limits to prevent memory overload
"""

import os
import sqlite3
import json
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from statistics import median
from typing import List, Tuple, Dict, Optional, Any
from modules.db_utils import find_project_root
from modules.db_utils.safe_connection import safe_db_connection
from modules.config.logging_config import get_logger
from modules.utils.simple_timezone import get_system_timezone_from_db
from modules.path_utils import get_paths
# Removed video_timezone_detector - using simple video detection
from .db_sync import db_rwlock, retry_in_progress_flag
from .config.scheduler_config import SchedulerConfig
from modules.utils.file_stability import is_file_stable, get_file_age, validate_video_file
import subprocess

# Use centralized path configuration
paths = get_paths()
DB_PATH = paths["DB_PATH"]

logger = get_logger(__name__, {"module": "file_lister"})
logger.info("File lister logging initialized")

def _get_system_tz():
    """Get system timezone from database configuration."""
    return ZoneInfo(get_system_timezone_from_db())


def get_db_path() -> str:
    """Get the configured database path from processing configuration.

    Returns:
        str: Path to the events database file

    Fallback:
        Returns default DB_PATH if configuration is not available or on error.
    """
    try:
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT db_path FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
            return result[0] if result else DB_PATH
    except Exception as e:
        logger.error(f"Error getting DB_PATH: {e}")
        return DB_PATH

logger.info(f"Using DB_PATH: {DB_PATH}")

def get_file_creation_time(file_path: str, camera_name: Optional[str] = None) -> datetime:
    """Extract video creation time with intelligent timezone detection and TimezoneManager integration.
    
    This function uses advanced timezone detection to extract accurate creation timestamps
    from video metadata. It supports multiple video formats, timezone detection methods,
    and provides intelligent fallbacks for reliability.
    
    Args:
        file_path (str): Path to the video file
        camera_name (str, optional): Camera name for camera-specific timezone configuration
        
    Returns:
        datetime: Timezone-aware creation time using detected or configured timezone
        
    Timezone Detection Process:
        1. Extract timezone from video metadata (high confidence)
        2. Use camera-specific timezone configuration (high confidence)
        3. Infer timezone from camera brand/model (medium confidence)
        4. Use user's configured timezone from TimezoneManager (medium confidence)
        5. Fallback to default timezone (low confidence)
        
    Supported Formats:
        .mp4, .avi, .mov, .mkv, .flv, .wmv, .m4v, .3gp, .webm
        
    Error Handling:
        Returns filesystem creation time with user's configured timezone if extraction fails.
    """
    try:
        # Check if file is a supported video format
        # Simple video file detection (replacing complex video_timezone_detector)
        video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v')
        if not os.path.isfile(file_path) or not file_path.lower().endswith(video_extensions):
            # For non-video files, use filesystem time with system timezone
            user_timezone = _get_system_tz()
            return datetime.fromtimestamp(os.path.getctime(file_path), tz=user_timezone)

        # Use simple filesystem time with system timezone (fallback approach)
        user_timezone = _get_system_tz()
        file_stat_time = os.path.getctime(file_path)
        timezone_aware_time = datetime.fromtimestamp(file_stat_time, tz=user_timezone)

        logger.debug(f"Extracted timezone-aware creation time for {file_path}: {timezone_aware_time}")
        return timezone_aware_time
        
    except Exception as e:
        logger.error(f"Error extracting timezone-aware creation time for {file_path}: {e}")
        # Safe fallback: use filesystem time with system timezone
        try:
            user_timezone = _get_system_tz()
            return datetime.fromtimestamp(os.path.getctime(file_path), tz=user_timezone)
        except Exception as fallback_error:
            logger.error(f"Fallback timezone retrieval failed for {file_path}: {fallback_error}")
            # Ultimate fallback: use system timezone
            return datetime.fromtimestamp(os.path.getctime(file_path), tz=_get_system_tz())

def compute_chunk_interval(ctimes: List[float]) -> int:
    """Calculate median time interval between video files for processing estimation.
    
    This function analyzes the timestamps of video files to estimate typical
    recording intervals, which can be useful for processing time estimation.
    
    Args:
        ctimes (List[float]): List of file creation timestamps
        
    Returns:
        int: Median interval in minutes between files, or 30 if insufficient data
        
    Algorithm:
        1. Use the most recent N_FILES_FOR_ESTIMATE files for calculation
        2. Calculate time differences between consecutive files
        3. Return median of intervals converted to minutes
        4. Fallback to 30 minutes if less than 2 files available
    """
    # Use only the most recent files for more accurate current interval estimation
    ctimes = sorted(ctimes)[-SchedulerConfig.N_FILES_FOR_ESTIMATE:]
    if len(ctimes) < 2:
        return 30  # Default 30-minute interval if insufficient data
        
    # Calculate intervals in minutes between consecutive files
    intervals = [(ctimes[i+1] - ctimes[i]) / 60 for i in range(len(ctimes)-1)]
    return round(median(intervals))

def scan_files(root_path: str, video_root: str, time_threshold: Optional[datetime], 
               max_ctime: Optional[datetime], restrict_to_current_date: bool = False, 
               camera_ctime_map: Optional[Dict[str, float]] = None, 
               working_days: Optional[List[str]] = None, from_time: Optional[Any] = None, 
               to_time: Optional[Any] = None, selected_cameras: Optional[List[str]] = None, 
               strict_date_match: bool = False) -> Tuple[List[str], List[float]]:
    """Scan directory tree for video files with advanced filtering options.
    
    This function performs comprehensive video file discovery with multiple
    filtering criteria including time ranges, camera selection, and working schedules.
    
    Args:
        root_path (str): Root directory to scan for videos
        video_root (str): Base video directory for relative path calculation
        time_threshold (datetime, optional): Minimum file creation time
        max_ctime (datetime, optional): Maximum file creation time (for incremental scans)
        restrict_to_current_date (bool): Limit to current date only
        camera_ctime_map (dict, optional): Track camera directory modification times
        working_days (List[str], optional): List of valid working days
        from_time (time, optional): Start of working hours
        to_time (time, optional): End of working hours
        selected_cameras (List[str], optional): Camera names to include
        strict_date_match (bool): Enforce strict date matching
        
    Returns:
        Tuple[List[str], List[float]]: (relative file paths, creation timestamps)
        
    Filtering Logic:
        1. File format validation (video extensions only)
        2. Time threshold filtering (skip old files)
        3. Incremental scanning (skip already processed files)
        4. Working day filtering (optional)
        5. Working hours filtering (optional)
        6. Camera selection filtering (optional)
        
    Performance Tracking:
        Logs scan duration and file counts for performance monitoring.
    """
    # Initialize performance tracking and counters
    scan_start_time = datetime.now()
    logger.info(f"Starting file scan at {root_path}", extra={"performance_timing": True})
    
    video_files = []
    file_ctimes = []
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
    current_date = datetime.now(_get_system_tz()).date()
    
    # Performance counters for diagnostic logging
    skipped_by_ctime = 0
    skipped_by_camera = 0
    ffprobe_errors = 0

    # Walk directory tree and process each directory
    for root, dirs, files in os.walk(root_path):
        # Determine camera name from directory structure
        relative_path = os.path.relpath(root, video_root)
        camera_name = relative_path.split(os.sep)[0] if relative_path != "." else os.path.basename(video_root)
        
        # Skip directories not in selected cameras list
        if selected_cameras and camera_name not in selected_cameras:
            skipped_by_camera += len([f for f in files if f.lower().endswith(video_extensions)])
            continue

        # Process each video file in the directory
        for file in files:
            if file.lower().endswith(video_extensions):
                file_path = os.path.join(root, file)
                try:
                    # Extract accurate creation time with timezone detection
                    file_ctime = get_file_creation_time(file_path, camera_name)
                except Exception as e:
                    ffprobe_errors += 1
                    logger.warning(f"Enhanced creation time extraction failed for {file_path}: {e}")
                    # Fallback to filesystem creation time with system timezone
                    try:
                        user_timezone = _get_system_tz()
                        file_ctime = datetime.fromtimestamp(os.path.getctime(file_path), tz=user_timezone)
                    except Exception:
                        # Ultimate fallback
                        file_ctime = datetime.fromtimestamp(os.path.getctime(file_path), tz=_get_system_tz())

                logger.debug(f"Checking file {file_path}, ctime={file_ctime}, max_ctime={max_ctime}")
                
                # Apply time threshold filtering (skip files older than threshold)
                if time_threshold and file_ctime < time_threshold:
                    skipped_by_ctime += 1
                    continue

                # Apply incremental scanning (skip files already processed)
                if max_ctime and file_ctime <= max_ctime:
                    skipped_by_ctime += 1
                    continue

                # Apply working days filtering if configured
                weekday = file_ctime.strftime('%A')
                if working_days and weekday not in working_days:
                    skipped_by_ctime += 1
                    logger.debug(f"Skipped file {file_path} due to non-working day: {weekday}")
                    continue

                # Apply working hours filtering if configured (timezone-aware)
                if from_time and to_time:
                    # Convert file creation time to user's local timezone for working hours comparison
                    try:
                        # Ensure file_ctime is timezone-aware
                        if file_ctime.tzinfo is None:
                            # Assume naive datetime is in system timezone
                            file_ctime_local = file_ctime.replace(tzinfo=_get_system_tz())
                        else:
                            # Convert to system timezone
                            file_ctime_local = file_ctime.astimezone(_get_system_tz())

                        file_time = file_ctime_local.time()

                        # Working hours comparison with midnight crossing support
                        # Examples: 00:00-00:00 (24h), 06:00-00:00 (6am-midnight), 22:00-06:00 (night shift)
                        if from_time == to_time:
                            # Special case: same start/end time means 24/7 operation
                            time_in_range = True
                        elif from_time < to_time:
                            # Normal range: e.g., 08:00-17:00
                            time_in_range = from_time <= file_time <= to_time
                        else:
                            # Crosses midnight: e.g., 22:00-06:00 or 06:00-00:00
                            time_in_range = file_time >= from_time or file_time <= to_time

                        if not time_in_range:
                            skipped_by_ctime += 1
                            user_tz_name = get_system_timezone_from_db()
                            logger.debug(
                                f"Skipped file {file_path} due to time outside working hours: "
                                f"{file_time} (local time in {user_tz_name}) not in "
                                f"{from_time}-{to_time} range"
                            )
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to apply timezone-aware working hours filter for {file_path}: {e}")
                        # Fallback to naive time comparison for backward compatibility
                        file_time = file_ctime.time() if hasattr(file_ctime, 'time') else file_ctime

                        if from_time == to_time:
                            time_in_range = True
                        elif from_time < to_time:
                            time_in_range = from_time <= file_time <= to_time
                        else:
                            time_in_range = file_time >= from_time or file_time <= to_time

                        if not time_in_range:
                            skipped_by_ctime += 1
                            logger.debug(f"Skipped file {file_path} due to time outside working hours (fallback): {file_time}")
                            continue

                # File passes all filters - add to results
                relative_path = os.path.relpath(file_path, video_root)
                video_files.append(relative_path)
                file_ctimes.append(file_ctime.timestamp())
                logger.info(f"Found video file: {file_path}")

        # Track camera directory modification times if requested
        if camera_ctime_map is not None:
            user_timezone = _get_system_tz()
            dir_ctime = datetime.fromtimestamp(os.path.getctime(root), tz=user_timezone)
            camera_ctime_map[camera_name] = max(camera_ctime_map.get(camera_name, 0), dir_ctime.timestamp())

    # Log performance metrics and return results
    scan_duration = (datetime.now() - scan_start_time).total_seconds()
    logger.info(
        f"Scan completed in {scan_duration:.2f}s - Found: {len(video_files)} files, "
        f"Skipped: {skipped_by_ctime} (time), {skipped_by_camera} (camera), {ffprobe_errors} ffprobe errors", 
        extra={"performance_timing": True, "scan_duration_seconds": scan_duration}
    )
    return video_files, file_ctimes

def save_files_to_db(conn: Any, video_files: List[str], file_ctimes: List[float],
                     scan_action: str, days: Optional[int], custom_path: Optional[str],
                     video_root: str, override_camera_name: Optional[str] = None) -> None:
    """Save discovered video files to the database for processing.
    
    This function takes the results of file scanning and stores them in the
    file_list table with appropriate metadata and processing flags.
    
    Args:
        conn: Database connection object
        video_files (List[str]): List of relative video file paths
        file_ctimes (List[float]): List of file creation timestamps
        scan_action (str): Type of scan ('first', 'default', 'custom')
        days (int, optional): Number of days for first run scanning
        custom_path (str, optional): Custom path for targeted scanning
        video_root (str): Base directory for video files
        
    Database Fields:
        - program_type: Type of processing program
        - days: Number of days (for first run)
        - custom_path: Custom path (for custom processing)
        - file_path: Absolute path to video file
        - created_at: When the database record was created
        - ctime: When the video file was created
        - priority: Processing priority (1 for custom, 0 for others)
        - camera_name: Camera identifier from directory structure
        - status: Processing status ('pending' initially)
        - is_processed: Processing completion flag (0 initially)
    
    Performance:
        Uses executemany() for efficient batch insertion of multiple files.
    """
    if not video_files:
        return  # Nothing to save

    # Prepare data for batch database insertion
    insert_data = []
    days_val = len(days) if isinstance(days, list) else days if days is not None else None
    
    for file_path, file_ctime in zip(video_files, file_ctimes):
        # Calculate absolute path based on scan type
        if scan_action == "custom" and custom_path and os.path.isfile(custom_path):
            absolute_path = custom_path
        else:
            absolute_path = os.path.join(video_root, file_path)

        # ==================== VIDEO FILE VALIDATION ====================
        # Validate that video file can be opened with OpenCV
        # This prevents processing incomplete downloads (e.g., moov atom not found)
        # More reliable than file stability check as it directly validates video integrity
        is_valid, reason = validate_video_file(absolute_path)
        if not is_valid:
            file_age = get_file_age(absolute_path)
            logger.info(
                f"⏳ Skipping invalid video file: {os.path.basename(absolute_path)} "
                f"(reason: {reason}, age: {file_age:.0f}s)"
            )
            continue  # Skip this file, will be picked up in next scan

        # Convert timestamp to datetime object with system timezone
        user_timezone = _get_system_tz()
        file_ctime_dt = datetime.fromtimestamp(file_ctime, tz=user_timezone)
        
        # Set priority (custom processing gets higher priority)
        priority = 1 if scan_action == "custom" else 0

        # Extract camera name - prioritize override parameter for custom mode
        if override_camera_name:
            camera_name = override_camera_name
            logger.info(f"Using override camera_name from custom mode: {camera_name}")
        else:
            # Extract camera name from directory structure
            # Always use relative path from video_root for consistent camera detection
            try:
                relative_path = os.path.relpath(absolute_path, video_root)
                # Check if video is outside video_root
                if relative_path.startswith(".."):
                    # Video is outside video_root, use parent folder
                    camera_name = os.path.basename(os.path.dirname(absolute_path))
                    logger.info(f"Video outside video_root, using parent folder: {camera_name}")
                elif relative_path == ".":
                    # Video is directly in video_root
                    camera_name = os.path.basename(video_root)
                else:
                    # First level directory is camera name (e.g., Cloud_Cam1, Cam2N)
                    camera_name = relative_path.split(os.sep)[0]
            except ValueError:
                # If relpath fails (different drives on Windows), fallback to basename
                camera_name = os.path.basename(os.path.dirname(absolute_path))

            # Validation: reject invalid camera names
            if camera_name in ['..', '.', 'Inputvideo', 'videos', 'resources', 'uploads']:
                logger.warning(f"Invalid camera_name '{camera_name}' detected, using CamTest")
                camera_name = "CamTest"
        
        # Check if health check required for this camera
        from modules.technician.camera_health_checker import should_run_health_check
        import json

        health_check_needed = should_run_health_check(camera_name)

        # Store health check metadata in JSON (but status stays 'pending')
        health_metadata = json.dumps({
            "health_check_required": health_check_needed,
            "health_check_done": False,
            "health_check_status": None,
            "timestamp": datetime.now(_get_system_tz()).isoformat()
        })

        # Prepare database record - status always 'pending', health check tracked via metadata
        insert_data.append((
            scan_action,           # program_type
            days_val,             # days
            custom_path,          # custom_path
            absolute_path,        # file_path
            datetime.now(_get_system_tz()),  # created_at
            file_ctime_dt,        # ctime
            priority,             # priority
            camera_name,          # camera_name
            'pending',            # status (always 'pending' - no status changes for health check)
            0,                    # is_processed
            health_metadata       # health_check_message (JSON with health_check_required flag)
        ))

    # Perform batch database insertion with duplicate check
    with conn:
        cursor = conn.cursor()

        # FIXED: Check for duplicates before inserting
        inserted_count = 0
        skipped_count = 0

        for record in insert_data:
            file_path = record[3]  # file_path is 4th element

            # Check if file already exists (any status)
            cursor.execute("""
                SELECT id FROM file_list
                WHERE file_path = ?
            """, (file_path,))

            if cursor.fetchone():
                skipped_count += 1
                logger.debug(f"Skipping duplicate file: {file_path}")
            else:
                # File not in queue, safe to insert
                cursor.execute('''
                    INSERT INTO file_list (program_type, days, custom_path, file_path, created_at, ctime, priority, camera_name, status, is_processed, health_check_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', record)
                inserted_count += 1

        logger.info(f"Inserted {inserted_count} new files, skipped {skipped_count} duplicates")

def list_files(video_root, scan_action, custom_path, days, db_path, default_scan_days=None, camera_ctime_map=None, is_initial_scan=False, camera_name=None):
    try:
        # First, get configuration from database
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                if not os.path.exists(video_root):
                    try:
                        os.makedirs(video_root, exist_ok=True)
                        logger.info(f"Created video root directory: {video_root}")
                    except Exception as e:
                        logger.error(f"Cannot create video root directory: {video_root}, error: {str(e)}")
                        raise Exception(f"Cannot create video root directory: {str(e)}")

                cursor.execute('SELECT MAX(ctime) FROM file_list')
                last_ctime = cursor.fetchone()[0]
                max_ctime = datetime.fromisoformat(last_ctime.replace('Z', '+00:00')) if last_ctime else datetime.now(_get_system_tz()).replace(year=1900)

                cursor.execute("SELECT input_path, selected_cameras FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                if result:
                    video_root = result[0]
                    selected_cameras = json.loads(result[1]) if result[1] else []
                else:
                    selected_cameras = []
                logger.info(f"Using video_root: {video_root}, Selected cameras: {selected_cameras}")

                # Retrieve working hours configuration with timezone context
                cursor.execute("SELECT working_days, from_time, to_time, timezone FROM general_info WHERE id = 1")
                general_info = cursor.fetchone()

                if general_info:
                    try:
                        working_days_raw = general_info[0].encode('utf-8').decode('utf-8') if general_info[0] else ''
                        working_days = json.loads(working_days_raw) if working_days_raw else []
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in working_days: {general_info[0]}, error: {e}")
                        working_days = []

                    # Parse working hours times
                    from_time = datetime.strptime(general_info[1], '%H:%M').time() if general_info[1] else None
                    to_time = datetime.strptime(general_info[2], '%H:%M').time() if general_info[2] else None

                    # Get timezone configuration for logging context
                    configured_timezone = general_info[3] if len(general_info) > 3 and general_info[3] else None
                    user_timezone_name = get_system_timezone_from_db()

                    # Log working hours configuration with timezone context
                    if from_time and to_time:
                        logger.info(
                            f"Working hours configured: {from_time}-{to_time} "
                            f"(evaluated in user timezone: {user_timezone_name})"
                        )
                        if configured_timezone and configured_timezone != user_timezone_name:
                            logger.info(
                                f"Note: Database timezone setting '{configured_timezone}' differs from "
                                f"current user timezone '{user_timezone_name}'. Using user timezone for evaluation."
                            )
                else:
                    working_days, from_time, to_time = [], None, None
                    user_timezone_name = get_system_timezone_from_db()

                logger.info(
                    f"Scanning configuration - Working days: {working_days}, "
                    f"Working hours: {from_time}-{to_time}, "
                    f"Timezone: {user_timezone_name}"
                )

        # Now perform file scanning outside database connection
        video_files = []
        file_ctimes = []

        if scan_action == "custom" and custom_path:
            if not os.path.exists(custom_path):
                raise Exception(f"Path does not exist: {custom_path}")
            if os.path.isfile(custom_path) and custom_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                file_name = os.path.basename(custom_path)
                # Use camera_name parameter if provided, otherwise extract from path
                if not camera_name:
                    custom_dir = os.path.dirname(custom_path)
                    camera_name = os.path.basename(custom_dir) if custom_dir else None
                file_ctime = get_file_creation_time(custom_path, camera_name)
                video_files.append(file_name)
                file_ctimes.append(file_ctime.timestamp())
                logger.info(f"Found file: {custom_path}, camera_name: {camera_name}")
            else:
                video_files, file_ctimes = scan_files(
                    custom_path, video_root, None, None, False, None,
                    working_days, from_time, to_time, selected_cameras, strict_date_match=False
                )
        elif scan_action == "first" and days:
            time_threshold = datetime.now(_get_system_tz()) - timedelta(days=days)
            video_files, file_ctimes = scan_files(
                video_root, video_root, time_threshold, None, False, None,
                working_days, from_time, to_time, selected_cameras, strict_date_match=False
            )
        else:  # default
            scan_days = default_scan_days if default_scan_days is not None else SchedulerConfig.DEFAULT_SCAN_DAYS
            time_threshold = datetime.now(_get_system_tz()) - timedelta(days=scan_days) if is_initial_scan else datetime.now(_get_system_tz()) - timedelta(days=1)
            restrict_to_current_date = not is_initial_scan
            video_files, file_ctimes = scan_files(
                video_root, video_root, time_threshold, max_ctime, restrict_to_current_date, camera_ctime_map,
                working_days, from_time, to_time, selected_cameras, strict_date_match=True
            )

        # Finally, save files to database with a fresh connection
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                save_files_to_db(conn, video_files, file_ctimes, scan_action, days, custom_path, video_root, camera_name)

                # Handle first run completion flag
                if scan_action == "first" and days:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO program_status (id, key, value)
                        VALUES ((SELECT id FROM program_status WHERE key = 'first_run_completed'), 'first_run_completed', 'true')
                    ''')
                    conn.commit()

        logger.info(f"Found {len(video_files)} video files")
        return video_files, file_ctimes
    except Exception as e:
        logger.error(f"Error in list_files: {e}")
        raise Exception(f"Error in list_files: {str(e)}")

def cleanup_stale_jobs() -> None:
    """Clean up stale processing jobs that have been stuck in processing state.
    
    This function identifies files that have been in 'đang frame sampler ...' status
    for more than 59 minutes and resets them to 'pending' status for reprocessing.
    This prevents deadlocks and ensures system recovery from failed processing jobs.
    
    Cleanup Criteria:
        - Status is 'đang frame sampler ...'
        - Created more than 59 minutes ago
        - Reset to 'pending' status for retry
        
    Thread Safety:
        Uses write lock for safe database modification.
    """
    try:
        # Reset stale jobs that have been stuck in processing state
        with db_rwlock.gen_wlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE file_list 
                    SET status = 'pending'
                    WHERE status = 'đang frame sampler ...'
                    AND created_at < datetime('now', '-59 minutes')
                """)
                affected = cursor.rowcount
            if affected > 0:
                logger.info(f"Reset {affected} stale jobs to pending status")
    except Exception as e:
        logger.error(f"Error cleaning up stale jobs: {e}")

def run_file_scan(scan_action: str = "default", days: Optional[int] = None,
                  custom_path: Optional[str] = None, camera_name: Optional[str] = None) -> List[str]:
    """Execute file scanning with the specified strategy and parameters.

    This is the main entry point for file scanning operations. It coordinates
    cleanup, configuration loading, and the actual scanning process.

    Args:
        scan_action (str): Type of scan to perform:
            - 'default': Continuous scanning for new files
            - 'first': Initial scan for specified number of days
            - 'custom': Scan specific file or directory
        days (int, optional): Number of days for 'first' scan
        custom_path (str, optional): File/directory path for 'custom' scan

    Returns:
        List[str]: List of discovered video files

    Process Flow:
        1. Check if retry is in progress - if so, pause scanning
        2. Clean up any stale processing jobs
        3. Load video root directory from configuration
        4. Determine if this is an initial scan (affects time filtering)
        5. Execute file scanning with appropriate filters
        6. Return list of discovered files

    Error Handling:
        Raises exceptions if video_root is not configured or if scanning fails.
    """
    # Check if retry is in progress - pause if so
    if retry_in_progress_flag.is_set():
        logger = get_logger(__name__)
        logger.info("⏸️ File scan paused: PASS 3 retry in progress")
        time.sleep(5)
        return []

    db_path = get_db_path()
    
    # Clean up any stale jobs before starting new scan
    cleanup_stale_jobs()
    
    try:
        # Load video root directory from configuration
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
            video_root = result[0] if result else ""
            
        if not video_root:
            raise Exception("No video_root found in processing_config")
            
        # Initialize camera modification time tracking
        camera_ctime_map = {}
        
        # Determine if this is an initial scan (affects time filtering behavior)
        is_initial_scan = scan_action == "default" and days is not None
        
        # Execute the file scanning operation
        files, _ = list_files(
            video_root, scan_action, custom_path, days, db_path,
            camera_ctime_map=camera_ctime_map, is_initial_scan=is_initial_scan, camera_name=camera_name
        )
        return files
        
    except Exception as e:
        logger.error(f"Error in run_file_scan: {e}")
        raise
