"""
Simple timezone utilities using Python's standard zoneinfo library.
Replaces 670+ lines of custom timezone code with native implementations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, available_timezones

logger = logging.getLogger(__name__)

# Legacy format mappings for backward compatibility
LEGACY_MAPPINGS = {
    "UTC+7": "Asia/Ho_Chi_Minh",
    "GMT+7": "Asia/Ho_Chi_Minh",
    "UTC+07:00": "Asia/Ho_Chi_Minh",
    "Asia/Saigon": "Asia/Ho_Chi_Minh",
    "ICT": "Asia/Ho_Chi_Minh",  # Indochina Time
}


def simple_validate_timezone(timezone_str: str) -> Dict[str, Any]:
    """
    Validate timezone string using zoneinfo.
    Returns validation result with status and normalized timezone.
    """
    if not timezone_str:
        return {"valid": False, "error": "Timezone string is empty"}

    # Check legacy mappings first
    normalized_tz = LEGACY_MAPPINGS.get(timezone_str, timezone_str)

    try:
        # Test if timezone exists in zoneinfo
        ZoneInfo(normalized_tz)
        return {"valid": True, "timezone": normalized_tz, "original": timezone_str}
    except Exception as e:
        logger.warning(f"Invalid timezone '{timezone_str}': {e}")
        return {
            "valid": False,
            "error": f"Invalid timezone: {timezone_str}",
            "original": timezone_str,
        }


def get_timezone_offset(timezone_str: str) -> Optional[int]:
    """Get UTC offset in hours for a timezone."""
    try:
        normalized_tz = LEGACY_MAPPINGS.get(timezone_str, timezone_str)
        tz = ZoneInfo(normalized_tz)
        now = datetime.now(tz)
        offset_seconds = now.utcoffset().total_seconds()
        return int(offset_seconds / 3600)
    except Exception:
        return None


def get_available_timezones():
    """Get available timezone identifiers."""
    return sorted(available_timezones())


def get_system_timezone_from_db() -> str:
    """
    Get configured system timezone from database.

    Priority:
        1. timezone_metadata.system_timezone
        2. general_info.timezone
        3. Default: 'Asia/Ho_Chi_Minh'

    Returns:
        str: IANA timezone string (e.g., 'Asia/Ho_Chi_Minh')
    """
    try:
        from modules.db_utils.safe_connection import safe_db_connection

        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Priority 1: timezone_metadata table
            cursor.execute("SELECT system_timezone FROM timezone_metadata ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            if result and result[0]:
                logger.info(f"Timezone from timezone_metadata: {result[0]}")
                return result[0]

            # Priority 2: general_info table
            cursor.execute("SELECT timezone FROM general_info LIMIT 1")
            result = cursor.fetchone()
            if result and result[0]:
                logger.info(f"Timezone from general_info: {result[0]}")
                return result[0]

        # Default fallback
        logger.warning("No timezone config found, using default: Asia/Ho_Chi_Minh")
        return "Asia/Ho_Chi_Minh"

    except Exception as e:
        logger.warning(f"Could not get timezone from database: {e}, using default")
        return "Asia/Ho_Chi_Minh"


def get_video_creation_time_utc(video_path: str) -> Dict[str, Any]:
    """
    Extract video creation time from metadata as UTC datetime.

    Priority:
        1. Video metadata creation_time (ffprobe) - HIGH confidence
        2. File system ctime - LOW confidence

    Args:
        video_path: Path to video file

    Returns:
        dict: {
            'utc_time': datetime (UTC aware),
            'source': 'metadata' | 'filesystem',
            'confidence': 'high' | 'low'
        }
    """
    import json
    import subprocess
    from pathlib import Path

    # Priority 1: Read from video metadata (ffprobe)
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            creation_time_str = data.get("format", {}).get("tags", {}).get("creation_time")

            if creation_time_str:
                # Parse ISO 8601 format: "2025-06-04T04:05:17.000000Z"
                # The 'Z' suffix indicates UTC
                creation_time = datetime.fromisoformat(creation_time_str.replace("Z", "+00:00"))
                logger.info(
                    f"Video creation time from metadata (UTC): {creation_time} [HIGH confidence]"
                )
                return {"utc_time": creation_time, "source": "metadata", "confidence": "high"}
    except Exception as e:
        logger.debug(f"Could not read creation_time from video metadata: {e}")

    # Priority 2: Fallback to file system ctime (interpret as UTC)
    try:
        file_timestamp = Path(video_path).stat().st_ctime
        # IMPORTANT: Interpret Unix timestamp as UTC (not local time)
        creation_time = datetime.fromtimestamp(file_timestamp, tz=timezone.utc)
        logger.info(f"Video creation time from file ctime (UTC): {creation_time} [LOW confidence]")
        return {"utc_time": creation_time, "source": "filesystem", "confidence": "low"}
    except Exception as e:
        logger.error(f"Could not get file creation time: {e}")
        # Last resort: current time
        return {"utc_time": datetime.now(timezone.utc), "source": "fallback", "confidence": "none"}
