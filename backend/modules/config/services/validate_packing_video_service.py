"""
Video validation service for packing area configuration.
Validates video files for training purposes with duration requirements (1-5 minutes).
"""

import os
import cv2
import time
from typing import Dict, Any, Optional
from modules.config.logging_config import get_logger

logger = get_logger(__name__)

# Supported video formats
SUPPORTED_FORMATS = [".mp4", ".avi", ".mov", ".mkv", ".wmv"]

# Duration constraints (in seconds)
MIN_DURATION = 60  # 1 minute
MAX_DURATION = 300  # 5 minutes


def format_duration(seconds: float) -> str:
    """Format duration seconds to human-readable string (e.g., '2m 30s')"""
    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)

    if remaining_seconds == 0:
        return f"{minutes}m"
    else:
        return f"{minutes}m {remaining_seconds}s"


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes"""
    try:
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    except Exception:
        return 0.0


def get_video_format(file_path: str) -> str:
    """Extract video format from file extension"""
    _, ext = os.path.splitext(file_path.lower())
    return ext.lstrip(".") if ext else "unknown"


def validate_packing_video(file_path: str, video_type: str = "traditional") -> Dict[str, Any]:
    """
    Validate a single training video for packing area configuration.

    Args:
        file_path (str): Full path to video file
        video_type (str): Type of video ('traditional' or 'qr') - for future enhancement

    Returns:
        Dict containing validation results and video metadata
    """
    start_time = time.time()

    # Initialize response structure
    response = {
        "success": False,
        "video_file": {
            "filename": os.path.basename(file_path) if file_path else "",
            "path": file_path,
            "duration_seconds": 0,
            "duration_formatted": "0s",
            "valid": False,
            "error": None,
            "file_size_mb": 0.0,
            "format": "unknown",
        },
        "summary": {"valid": False, "duration_seconds": 0, "scan_time_ms": 0},
        "file_info": {"exists": False, "readable": False},
    }

    try:
        logger.info(f"Validating video file: {file_path}")

        # Basic file validation
        if not file_path or not file_path.strip():
            response["video_file"]["error"] = "File path cannot be empty"
            return response

        # Check if file exists
        if not os.path.exists(file_path):
            response["video_file"]["error"] = "File does not exist"
            return response

        response["file_info"]["exists"] = True

        # Check if file is readable
        try:
            with open(file_path, "rb") as f:
                f.read(1)  # Try to read one byte
            response["file_info"]["readable"] = True
        except PermissionError:
            response["video_file"]["error"] = "Permission denied to access file"
            return response
        except Exception:
            response["video_file"]["error"] = "Cannot read file or corrupted"
            return response

        # Get file metadata
        response["video_file"]["file_size_mb"] = get_file_size_mb(file_path)
        response["video_file"]["format"] = get_video_format(file_path)

        # Check file format
        file_ext = os.path.splitext(file_path.lower())[1]
        if file_ext not in SUPPORTED_FORMATS:
            response["video_file"][
                "error"
            ] = f"Unsupported video format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            return response

        # Video analysis using OpenCV
        try:
            cap = cv2.VideoCapture(file_path)

            if not cap.isOpened():
                response["video_file"]["error"] = "Cannot read video file or corrupted"
                return response

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

            cap.release()

            if fps <= 0 or frame_count <= 0:
                response["video_file"]["error"] = "Invalid video properties detected"
                return response

            # Calculate duration
            duration_seconds = frame_count / fps

            # Update response with video data
            response["video_file"]["duration_seconds"] = round(duration_seconds, 1)
            response["video_file"]["duration_formatted"] = format_duration(duration_seconds)
            response["summary"]["duration_seconds"] = round(duration_seconds, 1)

            # Validate duration constraints
            if duration_seconds < MIN_DURATION:
                response["video_file"][
                    "error"
                ] = f"Video too short ({format_duration(duration_seconds)}). Minimum: 1 minute"
                response["video_file"]["valid"] = False
                response["summary"]["valid"] = False
            elif duration_seconds > MAX_DURATION:
                response["video_file"][
                    "error"
                ] = f"Video too long ({format_duration(duration_seconds)}). Maximum: 5 minutes"
                response["video_file"]["valid"] = False
                response["summary"]["valid"] = False
            else:
                # Video is valid
                response["video_file"]["valid"] = True
                response["video_file"]["error"] = None
                response["summary"]["valid"] = True
                response["success"] = True

                logger.info(f"Video validation successful: {format_duration(duration_seconds)}")

        except Exception as cv_error:
            logger.error(f"OpenCV error during video analysis: {cv_error}")
            response["video_file"]["error"] = f"Cannot analyze video: {str(cv_error)}"
            return response

    except Exception as e:
        logger.error(f"Unexpected error during video validation: {e}")
        response["video_file"]["error"] = f"Validation error: {str(e)}"
        return response

    finally:
        # Record scan time
        scan_time_ms = round((time.time() - start_time) * 1000, 2)
        response["summary"]["scan_time_ms"] = scan_time_ms

        logger.info(f"Video validation completed in {scan_time_ms}ms")

    return response


def validate_multiple_videos(file_paths: list, video_type: str = "traditional") -> Dict[str, Any]:
    """
    Validate multiple training videos (for future enhancement).

    Args:
        file_paths (list): List of file paths to validate
        video_type (str): Type of videos to validate

    Returns:
        Dict containing validation results for all videos
    """
    results = {
        "success": True,
        "total_files": len(file_paths),
        "valid_files": 0,
        "invalid_files": 0,
        "videos": [],
        "summary": {"total_duration_seconds": 0, "average_duration_seconds": 0, "scan_time_ms": 0},
    }

    start_time = time.time()
    total_duration = 0

    for file_path in file_paths:
        video_result = validate_packing_video(file_path, video_type)
        results["videos"].append(video_result)

        if video_result["success"] and video_result["video_file"]["valid"]:
            results["valid_files"] += 1
            total_duration += video_result["video_file"]["duration_seconds"]
        else:
            results["invalid_files"] += 1
            results["success"] = False

    # Calculate summary statistics
    results["summary"]["total_duration_seconds"] = round(total_duration, 1)
    if results["valid_files"] > 0:
        results["summary"]["average_duration_seconds"] = round(
            total_duration / results["valid_files"], 1
        )

    results["summary"]["scan_time_ms"] = round((time.time() - start_time) * 1000, 2)

    return results
