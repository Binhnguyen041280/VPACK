#!/usr/bin/env python3
"""
V_Track Video Timezone Detection Utilities

Advanced timezone detection and handling for video files with metadata extraction.
Supports multiple video formats and provides intelligent fallback mechanisms
for timezone determination when video metadata is incomplete or missing.

Features:
- FFprobe-based metadata extraction with timezone parsing
- Multiple video format support (MP4, AVI, MOV, MKV, FLV, WMV)
- Intelligent timezone detection from video metadata
- Geographic location-based timezone inference
- Camera-specific timezone configuration
- TimezoneManager integration for consistent timezone handling
- Performance-optimized caching for repeated operations
- Comprehensive error handling and logging

Usage:
    from modules.utils.video_timezone_detector import video_timezone_detector
    
    # Detect timezone from video metadata
    timezone_info = video_timezone_detector.detect_video_timezone("video.mp4")
    
    # Get timezone-aware creation time
    creation_time = video_timezone_detector.get_timezone_aware_creation_time("video.mp4")
"""

import os
import json
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import logging
import re

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

try:
    import zoneinfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False

from modules.config.logging_config import get_logger
from modules.utils.timezone_manager import timezone_manager
from modules.utils.timezone_validator import timezone_validator

logger = get_logger(__name__)

@dataclass
class VideoTimezoneInfo:
    """Information about video timezone detection."""
    video_path: str
    detected_timezone: Optional[str] = None
    timezone_source: str = "unknown"  # metadata, camera_config, location, user_setting, fallback
    creation_time_utc: Optional[datetime] = None
    creation_time_local: Optional[datetime] = None
    metadata_timezone: Optional[str] = None
    camera_timezone: Optional[str] = None
    confidence_score: float = 0.0  # 0.0 = low confidence, 1.0 = high confidence
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class VideoTimezoneDetector:
    """
    Advanced video timezone detection and handling system.
    
    Provides intelligent timezone detection for video files using multiple
    detection methods with confidence scoring and fallback mechanisms.
    """
    
    def __init__(self):
        """Initialize the video timezone detector."""
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._camera_timezone_cache = {}
        
        # Video format support
        self.supported_extensions = {
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.webm'
        }
        
        # Timezone detection patterns for metadata
        self.timezone_patterns = [
            re.compile(r'([+-]\d{2}):?(\d{2})$'),  # +07:00 or +0700
            re.compile(r'GMT([+-]\d{1,2})'),       # GMT+7
            re.compile(r'UTC([+-]\d{1,2})'),       # UTC+7
            re.compile(r'([A-Z]{3,4})$'),          # ICT, JST, PST
        ]
        
        # Common camera timezone mappings (based on camera brand/model patterns)
        self.camera_timezone_mappings = {
            'hikvision': 'Asia/Shanghai',
            'dahua': 'Asia/Shanghai', 
            'axis': 'Europe/Stockholm',
            'sony': 'Asia/Tokyo',
            'panasonic': 'Asia/Tokyo',
            'samsung': 'Asia/Seoul',
            'bosch': 'Europe/Berlin',
        }
        
        logger.info("VideoTimezoneDetector initialized")
    
    def detect_video_timezone(self, video_path: str, camera_name: Optional[str] = None) -> VideoTimezoneInfo:
        """
        Detect timezone information for a video file.
        
        Args:
            video_path: Path to the video file
            camera_name: Optional camera name for camera-specific timezone configuration
            
        Returns:
            VideoTimezoneInfo with detected timezone information
        """
        # Check cache first
        cache_key = f"{video_path}:{camera_name or 'none'}"
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        logger.debug(f"Detecting timezone for video: {video_path}")
        
        # Initialize result
        result = VideoTimezoneInfo(video_path=video_path)
        
        try:
            # Method 1: Extract timezone from video metadata
            metadata_result = self._detect_from_metadata(video_path)
            if metadata_result['timezone']:
                result.detected_timezone = metadata_result['timezone']
                result.timezone_source = "metadata"
                result.metadata_timezone = metadata_result['timezone']
                result.creation_time_utc = metadata_result['creation_time_utc']
                result.confidence_score = 0.9  # High confidence for metadata
                
            # Method 2: Check camera-specific configuration
            if not result.detected_timezone and camera_name:
                camera_timezone = self._get_camera_timezone(camera_name)
                if camera_timezone:
                    result.detected_timezone = camera_timezone
                    result.timezone_source = "camera_config"
                    result.camera_timezone = camera_timezone
                    result.confidence_score = 0.8  # High confidence for camera config
            
            # Method 3: Try to infer from camera brand/model
            if not result.detected_timezone and camera_name:
                brand_timezone = self._infer_timezone_from_camera_brand(camera_name)
                if brand_timezone:
                    result.detected_timezone = brand_timezone
                    result.timezone_source = "camera_brand"
                    result.confidence_score = 0.5  # Medium confidence for brand inference
            
            # Method 4: Use user's configured timezone from TimezoneManager
            if not result.detected_timezone:
                user_timezone = timezone_manager.get_user_timezone_name()
                if user_timezone:
                    result.detected_timezone = user_timezone
                    result.timezone_source = "user_setting"
                    result.confidence_score = 0.6  # Medium confidence for user setting
            
            # Method 5: Fallback to default timezone
            if not result.detected_timezone:
                result.detected_timezone = "Asia/Ho_Chi_Minh"  # V_Track default
                result.timezone_source = "fallback"
                result.confidence_score = 0.3  # Low confidence for fallback
                result.warnings.append("Using fallback timezone - no timezone information detected")
            
            # Calculate local creation time if we have UTC time
            if result.creation_time_utc and result.detected_timezone:
                try:
                    local_tz = self._get_timezone_object(result.detected_timezone)
                    if local_tz:
                        result.creation_time_local = result.creation_time_utc.astimezone(local_tz)
                except Exception as e:
                    logger.warning(f"Failed to convert to local time: {e}")
            
            # Cache the result
            with self._cache_lock:
                self._cache[cache_key] = result
            
            logger.debug(f"Timezone detection completed for {video_path}: {result.detected_timezone} (source: {result.timezone_source}, confidence: {result.confidence_score})")
            
        except Exception as e:
            logger.error(f"Error detecting timezone for {video_path}: {e}")
            result.warnings.append(f"Detection error: {str(e)}")
            result.detected_timezone = "Asia/Ho_Chi_Minh"  # Safe fallback
            result.timezone_source = "error_fallback"
            result.confidence_score = 0.1
        
        return result
    
    def get_timezone_aware_creation_time(self, video_path: str, camera_name: Optional[str] = None) -> datetime:
        """
        Get timezone-aware creation time for a video file.
        
        Args:
            video_path: Path to the video file
            camera_name: Optional camera name for timezone detection
            
        Returns:
            Timezone-aware datetime object representing video creation time
        """
        try:
            # Detect timezone information
            timezone_info = self.detect_video_timezone(video_path, camera_name)
            
            # If we have UTC time from metadata, use it
            if timezone_info.creation_time_utc:
                if timezone_info.creation_time_local:
                    return timezone_info.creation_time_local
                else:
                    # Convert UTC to detected timezone
                    local_tz = self._get_timezone_object(timezone_info.detected_timezone)
                    if local_tz:
                        return timezone_info.creation_time_utc.astimezone(local_tz)
            
            # Fallback: Use filesystem time with detected timezone
            filesystem_time = datetime.fromtimestamp(os.path.getctime(video_path))
            local_tz = self._get_timezone_object(timezone_info.detected_timezone)
            
            if local_tz:
                # Assume filesystem time is in local timezone
                return local_tz.localize(filesystem_time) if hasattr(local_tz, 'localize') else filesystem_time.replace(tzinfo=local_tz)
            else:
                # Fallback to default timezone
                default_tz = self._get_timezone_object("Asia/Ho_Chi_Minh")
                return default_tz.localize(filesystem_time) if hasattr(default_tz, 'localize') else filesystem_time.replace(tzinfo=default_tz)
                
        except Exception as e:
            logger.error(f"Error getting timezone-aware creation time for {video_path}: {e}")
            # Safe fallback
            return datetime.fromtimestamp(os.path.getctime(video_path), tz=timezone(timedelta(hours=7)))
    
    def _detect_from_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract timezone information from video metadata using FFprobe."""
        result = {
            'timezone': None,
            'creation_time_utc': None,
            'metadata_raw': None
        }
        
        try:
            # Use FFprobe to extract comprehensive metadata
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_entries", "format_tags=creation_time:format=creation_time:stream_tags=creation_time",
                video_path
            ]
            
            process_result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            metadata = json.loads(process_result.stdout)
            result['metadata_raw'] = metadata
            
            # Extract creation_time from multiple possible locations
            creation_time_str = None
            
            # Try format tags first
            format_tags = metadata.get("format", {}).get("tags", {})
            creation_time_str = (
                format_tags.get("creation_time") or
                format_tags.get("Creation Time") or
                format_tags.get("CREATION_TIME")
            )
            
            # Try format level
            if not creation_time_str:
                creation_time_str = metadata.get("format", {}).get("creation_time")
            
            # Try stream tags
            if not creation_time_str:
                streams = metadata.get("streams", [])
                for stream in streams:
                    stream_tags = stream.get("tags", {})
                    creation_time_str = (
                        stream_tags.get("creation_time") or
                        stream_tags.get("Creation Time") or
                        stream_tags.get("CREATION_TIME")
                    )
                    if creation_time_str:
                        break
            
            if creation_time_str:
                logger.debug(f"Found creation_time in metadata: {creation_time_str}")
                
                # Parse creation time and extract timezone
                parsed_time, detected_tz = self._parse_creation_time_with_timezone(creation_time_str)
                
                if parsed_time:
                    result['creation_time_utc'] = parsed_time
                    result['timezone'] = detected_tz
                    
                    logger.debug(f"Parsed creation time: {parsed_time}, detected timezone: {detected_tz}")
            else:
                logger.debug(f"No creation_time found in metadata for {video_path}")
                
        except subprocess.TimeoutExpired:
            logger.warning(f"FFprobe timeout for {video_path}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"FFprobe failed for {video_path}: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse metadata for {video_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error extracting metadata from {video_path}: {e}")
        
        return result
    
    def _parse_creation_time_with_timezone(self, creation_time_str: str) -> Tuple[Optional[datetime], Optional[str]]:
        """Parse creation time string and extract timezone information."""
        try:
            # Common creation time formats
            formats_to_try = [
                "%Y-%m-%dT%H:%M:%S.%fZ",      # 2023-12-25T10:30:45.123Z
                "%Y-%m-%dT%H:%M:%SZ",         # 2023-12-25T10:30:45Z
                "%Y-%m-%dT%H:%M:%S%z",        # 2023-12-25T10:30:45+0700
                "%Y-%m-%dT%H:%M:%S.%f%z",     # 2023-12-25T10:30:45.123+0700
                "%Y-%m-%d %H:%M:%S",          # 2023-12-25 10:30:45
                "%Y:%m:%d %H:%M:%S",          # 2023:12:25 10:30:45 (EXIF format)
            ]
            
            detected_timezone = None
            parsed_time = None
            
            # First, try to extract timezone information from the string
            for pattern in self.timezone_patterns:
                match = pattern.search(creation_time_str)
                if match:
                    if pattern.pattern.startswith(r'([+-]\d{2})'):  # Offset pattern
                        hours, minutes = match.groups()
                        offset_str = f"{hours}:{minutes}" if ':' not in hours else hours
                        detected_timezone = f"UTC{'+' if hours.startswith('+') else ''}{offset_str}"
                    elif 'GMT' in pattern.pattern or 'UTC' in pattern.pattern:
                        offset = match.group(1)
                        detected_timezone = f"UTC{'+' if not offset.startswith('-') else ''}{offset}"
                    else:  # Timezone abbreviation
                        tz_abbrev = match.group(0)
                        # Try to convert common abbreviations to IANA names
                        tz_mapping = {
                            'ICT': 'Asia/Ho_Chi_Minh',
                            'JST': 'Asia/Tokyo',
                            'KST': 'Asia/Seoul',
                            'CST': 'Asia/Shanghai',
                            'EST': 'America/New_York',
                            'PST': 'America/Los_Angeles',
                        }
                        detected_timezone = tz_mapping.get(tz_abbrev)
                    break
            
            # Try to parse the datetime
            for fmt in formats_to_try:
                try:
                    if fmt.endswith('Z'):
                        # Handle UTC format
                        parsed_time = datetime.strptime(creation_time_str, fmt)
                        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                        if not detected_timezone:
                            detected_timezone = "UTC"
                        break
                    elif '%z' in fmt:
                        # Handle timezone-aware format
                        parsed_time = datetime.strptime(creation_time_str, fmt)
                        # Extract timezone from parsed time if not already detected
                        if not detected_timezone and parsed_time.tzinfo:
                            offset = parsed_time.utcoffset()
                            if offset:
                                hours = offset.total_seconds() / 3600
                                detected_timezone = f"UTC{'+' if hours >= 0 else ''}{hours:+.0f}"
                        break
                    else:
                        # Handle naive datetime (assume local timezone)
                        parsed_time = datetime.strptime(creation_time_str, fmt)
                        # We'll need to make assumptions about timezone later
                        break
                except ValueError:
                    continue
            
            # If we parsed a naive datetime, assume it's in the detected timezone or UTC
            if parsed_time and not parsed_time.tzinfo:
                if detected_timezone:
                    # Try to apply detected timezone
                    tz_obj = self._get_timezone_object(detected_timezone)
                    if tz_obj:
                        if hasattr(tz_obj, 'localize'):
                            parsed_time = tz_obj.localize(parsed_time)
                        else:
                            parsed_time = parsed_time.replace(tzinfo=tz_obj)
                else:
                    # Assume UTC if no timezone detected
                    parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                    detected_timezone = "UTC"
            
            # Convert to UTC if not already
            if parsed_time and parsed_time.tzinfo:
                parsed_time = parsed_time.astimezone(timezone.utc)
            
            return parsed_time, detected_timezone
            
        except Exception as e:
            logger.warning(f"Failed to parse creation time '{creation_time_str}': {e}")
            return None, None
    
    def _get_camera_timezone(self, camera_name: str) -> Optional[str]:
        """Get timezone configuration for a specific camera."""
        # Check cache first
        if camera_name in self._camera_timezone_cache:
            return self._camera_timezone_cache[camera_name]
        
        try:
            # Try to get from database configuration - but avoid circular imports
            # This method will be called directly by frame samplers with database access
            db_timezone = self._get_camera_timezone_from_db_safely(camera_name)
            if db_timezone:
                return db_timezone
            
        except Exception as e:
            logger.debug(f"Could not get camera timezone from database for {camera_name}: {e}")
        
        # Cache negative result
        self._camera_timezone_cache[camera_name] = None
        return None
    
    def _get_camera_timezone_from_db_safely(self, camera_name: str) -> Optional[str]:
        """Get camera timezone from database without circular imports.
        
        This method returns None by default. It should be overridden or called
        with database access provided externally to avoid circular imports.
        """
        return None
    
    def set_camera_timezone_from_db(self, camera_name: str, db_connection, db_cursor) -> Optional[str]:
        """Set camera timezone from database using external connection.
        
        This method allows frame samplers to provide database access without
        creating circular imports.
        
        Args:
            camera_name: Name of the camera
            db_connection: Database connection object
            db_cursor: Database cursor object
            
        Returns:
            Camera timezone string if found, None otherwise
        """
        try:
            # Check if there's a camera-specific timezone configuration
            db_cursor.execute(
                "SELECT timezone FROM camera_configs WHERE camera_name = ?", 
                (camera_name,)
            )
            result = db_cursor.fetchone()
            
            if result and result[0]:
                timezone_str = result[0]
                # Validate the timezone
                validation_result = timezone_validator.validate_timezone(timezone_str)
                if validation_result.is_valid:
                    timezone_name = validation_result.iana_name or timezone_str
                    self._camera_timezone_cache[camera_name] = timezone_name
                    return timezone_name
                else:
                    logger.warning(f"Invalid timezone '{timezone_str}' for camera {camera_name}")
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not get camera timezone from database for {camera_name}: {e}")
            return None
    
    def _infer_timezone_from_camera_brand(self, camera_name: str) -> Optional[str]:
        """Infer timezone from camera brand/model patterns."""
        camera_name_lower = camera_name.lower()
        
        for brand, timezone_name in self.camera_timezone_mappings.items():
            if brand in camera_name_lower:
                logger.debug(f"Inferred timezone {timezone_name} from camera brand pattern '{brand}' for {camera_name}")
                return timezone_name
        
        return None
    
    def _get_timezone_object(self, timezone_name: str):
        """Get timezone object from timezone name."""
        try:
            # Validate timezone first
            validation_result = timezone_validator.validate_timezone(timezone_name)
            if validation_result.is_valid and validation_result.iana_name:
                timezone_name = validation_result.iana_name
            
            # Try zoneinfo first (Python 3.9+)
            if ZONEINFO_AVAILABLE:
                try:
                    return zoneinfo.ZoneInfo(timezone_name)
                except zoneinfo.ZoneInfoNotFoundError:
                    pass
            
            # Fallback to pytz
            if PYTZ_AVAILABLE:
                try:
                    return pytz.timezone(timezone_name)
                except pytz.exceptions.UnknownTimeZoneError:
                    pass
            
            # Handle UTC offset format
            if timezone_name.startswith('UTC'):
                offset_str = timezone_name[3:]  # Remove 'UTC'
                if offset_str:
                    try:
                        # Parse offset like +7 or +07:00
                        if ':' in offset_str:
                            hours, minutes = offset_str.split(':')
                            total_minutes = int(hours) * 60 + int(minutes)
                        else:
                            total_minutes = int(offset_str) * 60
                        
                        return timezone(timedelta(minutes=total_minutes))
                    except ValueError:
                        pass
                else:
                    return timezone.utc
            
            logger.warning(f"Could not create timezone object for: {timezone_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating timezone object for {timezone_name}: {e}")
            return None
    
    def get_video_metadata_summary(self, video_path: str) -> Dict[str, Any]:
        """Get comprehensive metadata summary for a video file."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_entries", "format:stream",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            metadata = json.loads(result.stdout)
            
            # Extract relevant information
            format_info = metadata.get("format", {})
            streams = metadata.get("streams", [])
            
            summary = {
                'duration': float(format_info.get("duration", 0)),
                'size_bytes': int(format_info.get("size", 0)),
                'format_name': format_info.get("format_name", "unknown"),
                'bit_rate': int(format_info.get("bit_rate", 0)),
                'tags': format_info.get("tags", {}),
                'video_streams': [],
                'audio_streams': []
            }
            
            for stream in streams:
                if stream.get("codec_type") == "video":
                    summary['video_streams'].append({
                        'codec': stream.get("codec_name"),
                        'width': stream.get("width"),
                        'height': stream.get("height"),
                        'fps': eval(stream.get("r_frame_rate", "0/1")),
                        'tags': stream.get("tags", {})
                    })
                elif stream.get("codec_type") == "audio":
                    summary['audio_streams'].append({
                        'codec': stream.get("codec_name"),
                        'sample_rate': stream.get("sample_rate"),
                        'channels': stream.get("channels"),
                        'tags': stream.get("tags", {})
                    })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting video metadata summary for {video_path}: {e}")
            return {}
    
    def clear_cache(self):
        """Clear all cached timezone detection results."""
        with self._cache_lock:
            self._cache.clear()
            self._camera_timezone_cache.clear()
        logger.info("Video timezone detection cache cleared")
    
    def is_video_file(self, file_path: str) -> bool:
        """Check if file is a supported video format."""
        return Path(file_path).suffix.lower() in self.supported_extensions

# Singleton instance
video_timezone_detector = VideoTimezoneDetector()

# Convenience functions
def detect_video_timezone(video_path: str, camera_name: Optional[str] = None) -> VideoTimezoneInfo:
    """Detect timezone information for a video file."""
    return video_timezone_detector.detect_video_timezone(video_path, camera_name)

def get_timezone_aware_creation_time(video_path: str, camera_name: Optional[str] = None) -> datetime:
    """Get timezone-aware creation time for a video file."""
    return video_timezone_detector.get_timezone_aware_creation_time(video_path, camera_name)

def get_video_metadata_summary(video_path: str) -> Dict[str, Any]:
    """Get comprehensive metadata summary for a video file."""
    return video_timezone_detector.get_video_metadata_summary(video_path)

def is_video_file(file_path: str) -> bool:
    """Check if file is a supported video format."""
    return video_timezone_detector.is_video_file(file_path)