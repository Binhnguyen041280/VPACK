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
from datetime import datetime, timedelta
from statistics import median
from typing import List, Tuple, Dict, Optional, Any
from modules.db_utils import find_project_root, get_db_connection
from modules.config.logging_config import get_logger
from .db_sync import db_rwlock
from .config.scheduler_config import SchedulerConfig
import subprocess
import pytz

# Cấu hình múi giờ Việt Nam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = get_logger(__name__, {"module": "file_lister"})
logger.info("File lister logging initialized")


DB_PATH = os.path.join(BASE_DIR, "database", "events.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db_path() -> str:
    """Get the configured database path from processing configuration.
    
    Returns:
        str: Path to the events database file
        
    Fallback:
        Returns default DB_PATH if configuration is not available or on error.
    """
    try:
        with db_rwlock.gen_rlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT db_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else DB_PATH
    except Exception as e:
        logger.error(f"Lỗi khi lấy DB_PATH: {e}")
        return DB_PATH

DB_PATH = get_db_path()
logger.info(f"Sử dụng DB_PATH: {DB_PATH}")

def get_file_creation_time(file_path: str) -> datetime:
    """Extract video creation time using FFprobe with Vietnam timezone normalization.
    
    This function uses FFprobe to extract accurate creation timestamps from video
    metadata. It handles various video formats and provides fallbacks for reliability.
    
    Args:
        file_path (str): Path to the video file
        
    Returns:
        datetime: Creation time normalized to Vietnam timezone (Asia/Ho_Chi_Minh)
        
    Extraction Process:
        1. Check if file is a supported video format
        2. Use FFprobe to extract creation_time from metadata
        3. Parse and convert UTC timestamp to Vietnam timezone
        4. Fallback to filesystem creation time if metadata extraction fails
        
    Supported Formats:
        .mp4, .avi, .mov, .mkv, .flv, .wmv
        
    Error Handling:
        Returns filesystem creation time if FFprobe fails or metadata is unavailable.
    """
    # For non-video files, return filesystem creation time immediately
    if not os.path.isfile(file_path) or not file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
        return datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)
    try:
        # Use FFprobe to extract video metadata in JSON format
        cmd = [
            "ffprobe",
            "-v", "quiet",                    # Suppress verbose output
            "-print_format", "json",         # Output in JSON format
            "-show_entries", "format_tags=creation_time:format=creation_time",  # Extract creation time
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        # Extract creation_time from metadata with multiple fallback paths
        creation_time = (
            metadata.get("format", {})
                    .get("tags", {})
                    .get("creation_time")
            or metadata.get("format", {}).get("creation_time")  # Alternative path for some formats
        )
        
        if creation_time:
            # Parse ISO 8601 format timestamp and convert to Vietnam timezone
            utc_time = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            utc_time = pytz.utc.localize(utc_time)
            return utc_time.astimezone(VIETNAM_TZ)
        else:
            logger.warning(f"No creation_time found in metadata for {file_path}, using filesystem time")
            return datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)
            
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error extracting creation_time for {file_path}: {e}")
        return datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)

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
    current_date = datetime.now(VIETNAM_TZ).date()
    
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
                    # Extract accurate creation time using FFprobe
                    file_ctime = get_file_creation_time(file_path)
                except Exception:
                    ffprobe_errors += 1
                    # Fallback to filesystem creation time if FFprobe fails
                    file_ctime = datetime.fromtimestamp(os.path.getctime(file_path), tz=VIETNAM_TZ)

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

                # Apply working hours filtering if configured
                file_time = file_ctime.time()
                if from_time and to_time and not (from_time <= file_time <= to_time):
                    skipped_by_ctime += 1
                    logger.debug(f"Skipped file {file_path} due to time outside working hours: {file_time}")
                    continue

                # File passes all filters - add to results
                relative_path = os.path.relpath(file_path, video_root)
                video_files.append(relative_path)
                file_ctimes.append(file_ctime.timestamp())
                logger.info(f"Found video file: {file_path}")

        # Track camera directory modification times if requested
        if camera_ctime_map is not None:
            dir_ctime = datetime.fromtimestamp(os.path.getctime(root), tz=VIETNAM_TZ)
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
                     video_root: str) -> None:
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
            
        # Convert timestamp to datetime object
        file_ctime_dt = datetime.fromtimestamp(file_ctime, tz=VIETNAM_TZ)
        
        # Set priority (custom processing gets higher priority)
        priority = 1 if scan_action == "custom" else 0
        
        # Extract camera name from directory structure
        if scan_action != "custom":
            relative_path = os.path.relpath(absolute_path, video_root)
        else:
            relative_path = os.path.dirname(absolute_path)
        camera_name = relative_path.split(os.sep)[0] if relative_path != "." else os.path.basename(video_root)
        
        # Prepare database record
        insert_data.append((
            scan_action,           # program_type
            days_val,             # days
            custom_path,          # custom_path
            absolute_path,        # file_path
            datetime.now(VIETNAM_TZ),  # created_at
            file_ctime_dt,        # ctime
            priority,             # priority
            camera_name,          # camera_name
            'pending',            # status
            0                     # is_processed
        ))

    # Perform batch database insertion
    with conn:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO file_list (program_type, days, custom_path, file_path, created_at, ctime, priority, camera_name, status, is_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', insert_data)
        logger.info(f"Inserted {len(insert_data)} files into file_list table")

def list_files(video_root, scan_action, custom_path, days, db_path, default_scan_days=None, camera_ctime_map=None, is_initial_scan=False):
    try:
        with db_rwlock.gen_wlock():
            conn = get_db_connection()
            cursor = conn.cursor()

            if not os.path.exists(video_root):
                try:
                    os.makedirs(video_root, exist_ok=True)
                    logger.info(f"Đã tạo thư mục video root: {video_root}")
                except Exception as e:
                    logger.error(f"Không thể tạo thư mục video root: {video_root}, lỗi: {str(e)}")
                    raise Exception(f"Không thể tạo thư mục video root: {str(e)}")

            cursor.execute('SELECT MAX(ctime) FROM file_list')
            last_ctime = cursor.fetchone()[0]
            max_ctime = datetime.fromisoformat(last_ctime.replace('Z', '+00:00')) if last_ctime else datetime.min.replace(tzinfo=VIETNAM_TZ)

            cursor.execute("SELECT input_path, selected_cameras FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            if result:
                video_root = result[0]
                selected_cameras = json.loads(result[1]) if result[1] else []
            else:
                selected_cameras = []
            logger.info(f"Sử dụng video_root: {video_root}, Camera được chọn: {selected_cameras}")

            cursor.execute("SELECT working_days, from_time, to_time FROM general_info WHERE id = 1")
            general_info = cursor.fetchone()
            if general_info:
                try:
                    working_days_raw = general_info[0].encode('utf-8').decode('utf-8') if general_info[0] else ''
                    working_days = json.loads(working_days_raw) if working_days_raw else []
                except json.JSONDecodeError as e:
                    logger.error(f"JSON không hợp lệ trong working_days: {general_info[0]}, lỗi: {e}")
                    working_days = []
                from_time = datetime.strptime(general_info[1], '%H:%M').time() if general_info[1] else None
                to_time = datetime.strptime(general_info[2], '%H:%M').time() if general_info[2] else None
            else:
                working_days, from_time, to_time = [], None, None
            logger.info(f"Ngày làm việc: {working_days}, from_time: {from_time}, to_time: {to_time}")

            video_files = []
            file_ctimes = []

            if scan_action == "custom" and custom_path:
                if not os.path.exists(custom_path):
                    raise Exception(f"Đường dẫn không tồn tại: {custom_path}")
                if os.path.isfile(custom_path) and custom_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                    file_name = os.path.basename(custom_path)
                    file_ctime = get_file_creation_time(custom_path)
                    video_files.append(file_name)
                    file_ctimes.append(file_ctime.timestamp())
                    logger.info(f"Tìm thấy tệp: {custom_path}")
                else:
                    video_files, file_ctimes = scan_files(
                        custom_path, video_root, None, None, False, None,
                        working_days, from_time, to_time, selected_cameras, strict_date_match=False
                    )
            elif scan_action == "first" and days:
                time_threshold = datetime.now(VIETNAM_TZ) - timedelta(days=days)
                video_files, file_ctimes = scan_files(
                    video_root, video_root, time_threshold, None, False, None,
                    working_days, from_time, to_time, selected_cameras, strict_date_match=False
                )
                cursor.execute('''
                    INSERT OR REPLACE INTO program_status (id, key, value)
                    VALUES ((SELECT id FROM program_status WHERE key = 'first_run_completed'), 'first_run_completed', 'true')
                ''')
                conn.commit()
            else:  # default
                scan_days = default_scan_days if default_scan_days is not None else SchedulerConfig.DEFAULT_SCAN_DAYS
                time_threshold = datetime.now(VIETNAM_TZ) - timedelta(days=scan_days) if is_initial_scan else datetime.now(VIETNAM_TZ) - timedelta(days=1)
                restrict_to_current_date = not is_initial_scan
                video_files, file_ctimes = scan_files(
                    video_root, video_root, time_threshold, max_ctime, restrict_to_current_date, camera_ctime_map,
                    working_days, from_time, to_time, selected_cameras, strict_date_match=True
                )

            save_files_to_db(conn, video_files, file_ctimes, scan_action, days, custom_path, video_root)
            conn.close()
        logger.info(f"Tìm thấy {len(video_files)} tệp video")
        return video_files, file_ctimes
    except Exception as e:
        logger.error(f"Lỗi trong list_files: {e}")
        raise Exception(f"Lỗi trong list_files: {str(e)}")

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
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE file_list 
                SET status = 'pending'
                WHERE status = 'đang frame sampler ...'
                AND created_at < datetime('now', '-59 minutes')
            """)
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            if affected > 0:
                logger.info(f"Reset {affected} stale jobs to pending status")
    except Exception as e:
        logger.error(f"Error cleaning up stale jobs: {e}")

def run_file_scan(scan_action: str = "default", days: Optional[int] = None, 
                  custom_path: Optional[str] = None) -> List[str]:
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
        1. Clean up any stale processing jobs
        2. Load video root directory from configuration
        3. Determine if this is an initial scan (affects time filtering)
        4. Execute file scanning with appropriate filters
        5. Return list of discovered files
        
    Error Handling:
        Raises exceptions if video_root is not configured or if scanning fails.
    """
    db_path = get_db_path()
    
    # Clean up any stale jobs before starting new scan
    cleanup_stale_jobs()
    
    try:
        # Load video root directory from configuration
        with db_rwlock.gen_rlock():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            conn.close()
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
            camera_ctime_map=camera_ctime_map, is_initial_scan=is_initial_scan
        )
        return files
        
    except Exception as e:
        logger.error(f"Error in run_file_scan: {e}")
        raise
