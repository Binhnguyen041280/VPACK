#!/usr/bin/env python3
"""
Timezone Validation Module for Event Query System

Provides comprehensive validation, parsing, and error handling for timezone-aware
event queries. Ensures consistent timezone handling across all query endpoints
with robust error reporting and fallback mechanisms.

Features:
- Multi-format datetime parsing with timezone support
- Comprehensive timezone validation and normalization
- Intelligent fallbacks for malformed input
- Performance-optimized validation with caching
- Detailed error reporting for debugging

Usage:
    from modules.query.timezone_validation import validate_query_parameters
    
    result = validate_query_parameters(request_data)
    if result['valid']:
        # Use validated parameters
        time_range = result['time_range']
        timezone_info = result['timezone_info']
    else:
        # Handle validation errors
        return jsonify({"error": result['error']}), 400
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import json
from dataclasses import dataclass

from modules.utils.timezone_manager import timezone_manager
from modules.utils.timezone_validator import timezone_validator
from modules.config.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class TimeRangeValidation:
    """Result of time range validation."""
    valid: bool
    from_timestamp: Optional[int] = None  # UTC milliseconds
    to_timestamp: Optional[int] = None    # UTC milliseconds
    from_datetime: Optional[datetime] = None  # Parsed datetime object
    to_datetime: Optional[datetime] = None    # Parsed datetime object
    user_timezone: Optional[Any] = None   # User timezone object
    user_timezone_name: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

@dataclass
class QueryValidation:
    """Result of complete query validation."""
    valid: bool
    time_range: Optional[TimeRangeValidation] = None
    cameras: List[str] = None
    tracking_codes: List[str] = None
    pagination: Dict[str, int] = None
    error: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.cameras is None:
            self.cameras = []
        if self.tracking_codes is None:
            self.tracking_codes = []
        if self.pagination is None:
            self.pagination = {'limit': 100, 'offset': 0}

class TimezoneQueryValidator:
    """
    Comprehensive validator for timezone-aware event queries.
    """
    
    def __init__(self):
        """Initialize the validator with caching and pattern compilation."""
        self._cache = {}
        self._cache_size_limit = 1000
        
        # Compile regex patterns for performance
        self.timestamp_pattern = re.compile(r'^\d{10,13}$')  # Unix timestamp (seconds or milliseconds)
        self.iso_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')  # ISO format
        self.simple_date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')  # Simple date
        
        logger.info("TimezoneQueryValidator initialized")
    
    def validate_query_parameters(self, data: Dict[str, Any]) -> QueryValidation:
        """
        Validate complete query parameters with timezone support.
        
        Args:
            data: Query parameters dictionary
            
        Returns:
            QueryValidation object with validation results
        """
        try:
            result = QueryValidation(valid=True)
            
            # Extract and validate basic parameters
            from_time = data.get('from_time')
            to_time = data.get('to_time')
            user_timezone_name = data.get('user_timezone') or data.get('timezone')
            default_days = data.get('default_days', 7)
            
            # Validate time range
            time_range_result = self.validate_time_range(
                from_time, to_time, default_days, user_timezone_name
            )
            
            if not time_range_result.valid:
                result.valid = False
                result.error = time_range_result.error
                return result
            
            result.time_range = time_range_result
            
            # Validate cameras
            cameras = self._validate_cameras(data.get('selected_cameras', []))
            result.cameras = cameras['cameras']
            result.warnings.extend(cameras['warnings'])
            
            # Validate tracking codes
            tracking_codes = self._validate_tracking_codes(data.get('search_string', ''))
            result.tracking_codes = tracking_codes['codes']
            result.warnings.extend(tracking_codes['warnings'])
            
            # Validate pagination
            pagination = self._validate_pagination(data)
            result.pagination = pagination['pagination']
            result.warnings.extend(pagination['warnings'])
            
            logger.debug(f"Query validation successful: {len(result.cameras)} cameras, {len(result.tracking_codes)} codes")
            return result
            
        except Exception as e:
            logger.error(f"Error validating query parameters: {e}")
            return QueryValidation(
                valid=False,
                error=f"Query validation failed: {str(e)}"
            )
    
    def validate_time_range(self, from_time: Optional[str], to_time: Optional[str], 
                           default_days: int = 7, user_timezone_name: Optional[str] = None) -> TimeRangeValidation:
        """
        Validate and parse time range parameters.
        
        Args:
            from_time: Start time in various formats
            to_time: End time in various formats
            default_days: Default range if no times provided
            user_timezone_name: User timezone override
            
        Returns:
            TimeRangeValidation object with parsed results
        """
        try:
            # Validate user timezone
            user_tz, tz_name = self._get_validated_timezone(user_timezone_name)
            
            if from_time and to_time:
                # Parse custom time range
                from_dt = self._parse_datetime(from_time, user_tz)
                to_dt = self._parse_datetime(to_time, user_tz)
                
                if not from_dt:
                    return TimeRangeValidation(
                        valid=False,
                        error=f"Invalid from_time format: '{from_time}'. Use ISO format, Unix timestamp, or YYYY-MM-DD format."
                    )
                
                if not to_dt:
                    return TimeRangeValidation(
                        valid=False,
                        error=f"Invalid to_time format: '{to_time}'. Use ISO format, Unix timestamp, or YYYY-MM-DD format."
                    )
                
                # Validate time range logic
                if from_dt >= to_dt:
                    return TimeRangeValidation(
                        valid=False,
                        error="from_time must be before to_time"
                    )
                
                # Check for reasonable time range (not more than 1 year)
                if (to_dt - from_dt).days > 365:
                    return TimeRangeValidation(
                        valid=False,
                        error="Time range cannot exceed 365 days"
                    )
                
            else:
                # Use default time range
                to_dt = datetime.now(timezone.utc)
                from_dt = to_dt - timedelta(days=default_days)
            
            # Convert to UTC timestamps
            from_timestamp = int(from_dt.astimezone(timezone.utc).timestamp() * 1000)
            to_timestamp = int(to_dt.astimezone(timezone.utc).timestamp() * 1000)
            
            # Validate timestamp ranges
            if from_timestamp < 0 or to_timestamp < 0:
                return TimeRangeValidation(
                    valid=False,
                    error="Invalid timestamp range (negative values not allowed)"
                )
            
            # Check for future dates (warning only)
            warnings = []
            now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
            if from_timestamp > now_ts:
                warnings.append("from_time is in the future")
            if to_timestamp > now_ts:
                warnings.append("to_time is in the future")
            
            return TimeRangeValidation(
                valid=True,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                from_datetime=from_dt,
                to_datetime=to_dt,
                user_timezone=user_tz,
                user_timezone_name=tz_name,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error validating time range: {e}")
            return TimeRangeValidation(
                valid=False,
                error=f"Time range validation failed: {str(e)}"
            )
    
    def _get_validated_timezone(self, user_timezone_name: Optional[str]) -> Tuple[Any, str]:
        """Get validated timezone object and name."""
        if user_timezone_name:
            try:
                validation_result = timezone_validator.validate_timezone(user_timezone_name)
                if validation_result.is_valid and validation_result.iana_name:
                    try:
                        # Try to get timezone object from TimezoneManager
                        user_tz = timezone_manager._get_timezone_from_iana(validation_result.iana_name)
                        return user_tz, validation_result.iana_name
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Timezone validation failed for '{user_timezone_name}': {e}")
        
        # Fallback to user's configured timezone
        user_tz = timezone_manager.get_user_timezone()
        tz_name = timezone_manager.get_user_timezone_name()
        return user_tz, tz_name
    
    def _parse_datetime(self, time_str: str, user_tz) -> Optional[datetime]:
        """
        Parse datetime string with comprehensive format support.
        
        Supports:
        - Unix timestamps (seconds/milliseconds): 1705287000, 1705287000000
        - ISO with timezone: 2024-01-15T10:30:00+07:00
        - ISO UTC: 2024-01-15T03:30:00Z
        - ISO naive: 2024-01-15T10:30:00 (assumes user timezone)
        - Date only: 2024-01-15 (assumes start of day in user timezone)
        - Common formats: 2024-01-15 10:30:00, 2024/01/15 10:30:00
        """
        if not time_str:
            return None
        
        time_str = time_str.strip()
        
        try:
            # Check cache first
            cache_key = f"{time_str}:{user_tz}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            result = None
            
            # 1. Try Unix timestamp
            if self.timestamp_pattern.match(time_str):
                timestamp = int(time_str)
                # Handle both seconds and milliseconds
                if timestamp > 1e12:  # milliseconds
                    result = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                else:  # seconds
                    result = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # 2. Try ISO format
            elif self.iso_pattern.match(time_str):
                try:
                    if time_str.endswith('Z'):
                        result = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    else:
                        result = datetime.fromisoformat(time_str)
                        # If naive datetime, apply user timezone
                        if result.tzinfo is None:
                            if hasattr(user_tz, 'localize'):
                                result = user_tz.localize(result)
                            else:
                                result = result.replace(tzinfo=user_tz)
                except ValueError:
                    pass
            
            # 3. Try simple date format
            elif self.simple_date_pattern.match(time_str):
                try:
                    naive_dt = datetime.strptime(time_str, '%Y-%m-%d')
                    if hasattr(user_tz, 'localize'):
                        result = user_tz.localize(naive_dt)
                    else:
                        result = naive_dt.replace(tzinfo=user_tz)
                except ValueError:
                    pass
            
            # 4. Try common datetime formats
            else:
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y/%m/%d %H:%M:%S',
                    '%Y/%m/%d %H:%M',
                    '%Y/%m/%d',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y %H:%M',
                    '%d/%m/%Y',
                    '%m/%d/%Y %H:%M:%S',
                    '%m/%d/%Y %H:%M',
                    '%m/%d/%Y'
                ]
                
                for fmt in formats:
                    try:
                        naive_dt = datetime.strptime(time_str, fmt)
                        if hasattr(user_tz, 'localize'):
                            result = user_tz.localize(naive_dt)
                        else:
                            result = naive_dt.replace(tzinfo=user_tz)
                        break
                    except ValueError:
                        continue
            
            # Cache result if successful
            if result and len(self._cache) < self._cache_size_limit:
                self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.warning(f"Error parsing datetime '{time_str}': {e}")
            return None
    
    def _validate_cameras(self, cameras: Union[List[str], str]) -> Dict[str, Any]:
        """Validate camera selection parameters."""
        try:
            if isinstance(cameras, str):
                cameras = [c.strip() for c in cameras.split(',') if c.strip()]
            elif not isinstance(cameras, list):
                cameras = []
            
            # Validate camera names
            valid_cameras = []
            warnings = []
            
            for camera in cameras:
                if isinstance(camera, str) and camera.strip():
                    camera_name = camera.strip()
                    # Basic validation - no special characters that could cause SQL issues
                    if re.match(r'^[a-zA-Z0-9_\-\.]+$', camera_name):
                        valid_cameras.append(camera_name)
                    else:
                        warnings.append(f"Invalid camera name format: '{camera_name}'")
                else:
                    warnings.append(f"Invalid camera name: {camera}")
            
            return {
                'cameras': valid_cameras,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.warning(f"Error validating cameras: {e}")
            return {
                'cameras': [],
                'warnings': [f"Camera validation failed: {str(e)}"]
            }
    
    def _validate_tracking_codes(self, search_string: str) -> Dict[str, Any]:
        """Validate tracking codes from search string."""
        try:
            tracking_codes = []
            warnings = []
            
            if search_string:
                lines = search_string.splitlines()
                for line in lines:
                    line = line.strip()
                    if line:
                        # Remove numbering (e.g., "1. ", "2. ")
                        code = line.split('. ', 1)[-1].strip()
                        if code:
                            # Basic validation for tracking codes
                            if len(code) <= 100:  # Reasonable length limit
                                tracking_codes.append(code)
                            else:
                                warnings.append(f"Tracking code too long (max 100 chars): '{code[:50]}...'")
            
            return {
                'codes': tracking_codes,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.warning(f"Error validating tracking codes: {e}")
            return {
                'codes': [],
                'warnings': [f"Tracking code validation failed: {str(e)}"]
            }
    
    def _validate_pagination(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pagination parameters."""
        try:
            limit = data.get('limit', 100)
            offset = data.get('offset', 0)
            warnings = []
            
            # Validate limit
            if not isinstance(limit, int) or limit < 1:
                limit = 100
                warnings.append("Invalid limit, using default: 100")
            elif limit > 1000:
                limit = 1000
                warnings.append("Limit too high, capped at: 1000")
            
            # Validate offset
            if not isinstance(offset, int) or offset < 0:
                offset = 0
                warnings.append("Invalid offset, using default: 0")
            
            return {
                'pagination': {'limit': limit, 'offset': offset},
                'warnings': warnings
            }
            
        except Exception as e:
            logger.warning(f"Error validating pagination: {e}")
            return {
                'pagination': {'limit': 100, 'offset': 0},
                'warnings': [f"Pagination validation failed: {str(e)}"]
            }

# Singleton instance
timezone_query_validator = TimezoneQueryValidator()

def validate_query_parameters(data: Dict[str, Any]) -> QueryValidation:
    """Convenience function for query validation."""
    return timezone_query_validator.validate_query_parameters(data)

def validate_time_range(from_time: Optional[str], to_time: Optional[str], 
                       default_days: int = 7, user_timezone_name: Optional[str] = None) -> TimeRangeValidation:
    """Convenience function for time range validation."""
    return timezone_query_validator.validate_time_range(from_time, to_time, default_days, user_timezone_name)