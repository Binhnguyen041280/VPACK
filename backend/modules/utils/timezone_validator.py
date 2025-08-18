#!/usr/bin/env python3
"""
V_Track Timezone Validation Utilities

Comprehensive timezone validation with IANA timezone database support.
Handles multiple timezone formats including UTC offsets, IANA names,
and legacy formats with proper fallback mechanisms.

Features:
- IANA timezone database validation
- UTC offset format support (UTC+7, GMT-5, etc.)
- Legacy timezone format compatibility
- Comprehensive format detection and normalization
- Performance-optimized with caching
- Thread-safe operations
- Integration with TimezoneManager

Usage:
    from modules.utils.timezone_validator import TimezoneValidator
    
    validator = TimezoneValidator()
    result = validator.validate_timezone("Asia/Ho_Chi_Minh")
    if result.is_valid:
        print(f"Timezone: {result.normalized_name}")
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager
import threading

try:
    import zoneinfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False
    try:
        import pytz
        PYTZ_AVAILABLE = True
    except ImportError:
        PYTZ_AVAILABLE = False

from modules.config.logging_config import get_logger

logger = get_logger(__name__)

class TimezoneFormat(Enum):
    """Supported timezone format types."""
    IANA = "iana"           # Asia/Ho_Chi_Minh, America/New_York
    UTC_OFFSET = "utc_offset"  # UTC+7, GMT-5, +07:00
    LEGACY = "legacy"       # Asia/Ho_Chi_Minh (legacy format)
    UNKNOWN = "unknown"     # Unable to determine format

@dataclass
class TimezoneValidationResult:
    """Result of timezone validation."""
    is_valid: bool
    normalized_name: str
    original_input: str
    format_type: TimezoneFormat
    iana_name: Optional[str] = None
    utc_offset_hours: Optional[float] = None
    utc_offset_seconds: Optional[int] = None
    display_name: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class TimezoneValidator:
    """
    Comprehensive timezone validation with IANA support.
    
    Validates and normalizes timezone strings in various formats:
    - IANA timezone names (Asia/Ho_Chi_Minh, America/New_York)
    - UTC offsets (UTC+7, GMT-5, +07:00, -05:30)
    - Legacy formats with fallback handling
    """
    
    def __init__(self):
        """Initialize the timezone validator."""
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._iana_zones = None
        self._iana_zones_lock = threading.RLock()
        
        # Compile regex patterns for performance
        self._utc_offset_patterns = [
            re.compile(r'^UTC([+-])(\d{1,2})(?::?(\d{2}))?$', re.IGNORECASE),
            re.compile(r'^GMT([+-])(\d{1,2})(?::?(\d{2}))?$', re.IGNORECASE),
            re.compile(r'^([+-])(\d{1,2})(?::?(\d{2}))?$'),
            re.compile(r'^([+-])(\d{4})$'),  # +0700, -0530
        ]
        
        # Legacy timezone mappings
        self._legacy_mappings = {
            'ICT': 'Asia/Ho_Chi_Minh',  # Indochina Time
            'JST': 'Asia/Tokyo',        # Japan Standard Time
            'EST': 'America/New_York',  # Eastern Standard Time
            'PST': 'America/Los_Angeles', # Pacific Standard Time
            'CST': 'Asia/Shanghai',     # China Standard Time
        }
        
        logger.info("TimezoneValidator initialized with IANA support")
    
    def validate_timezone(self, timezone_input: str, allow_cache: bool = True) -> TimezoneValidationResult:
        """
        Validate and normalize a timezone string.
        
        Args:
            timezone_input: Timezone string to validate
            allow_cache: Whether to use cached results
            
        Returns:
            TimezoneValidationResult with validation details
        """
        if not timezone_input or not isinstance(timezone_input, str):
            return TimezoneValidationResult(
                is_valid=False,
                normalized_name="",
                original_input=str(timezone_input) if timezone_input else "",
                format_type=TimezoneFormat.UNKNOWN,
                error_message="Invalid input: timezone must be a non-empty string"
            )
        
        timezone_input = timezone_input.strip()
        
        # Check cache first
        if allow_cache:
            with self._cache_lock:
                if timezone_input in self._cache:
                    return self._cache[timezone_input]
        
        # Validate the timezone
        result = self._validate_timezone_internal(timezone_input)
        
        # Cache the result
        if allow_cache:
            with self._cache_lock:
                self._cache[timezone_input] = result
        
        return result
    
    def _validate_timezone_internal(self, timezone_input: str) -> TimezoneValidationResult:
        """Internal timezone validation logic."""
        try:
            # Try IANA timezone validation first
            iana_result = self._validate_iana_timezone(timezone_input)
            if iana_result.is_valid:
                return iana_result
            
            # Try UTC offset validation
            offset_result = self._validate_utc_offset(timezone_input)
            if offset_result.is_valid:
                return offset_result
            
            # Try legacy timezone mappings
            legacy_result = self._validate_legacy_timezone(timezone_input)
            if legacy_result.is_valid:
                return legacy_result
            
            # All validation methods failed
            return TimezoneValidationResult(
                is_valid=False,
                normalized_name="",
                original_input=timezone_input,
                format_type=TimezoneFormat.UNKNOWN,
                error_message=f"Unrecognized timezone format: {timezone_input}"
            )
            
        except Exception as e:
            logger.error(f"Timezone validation error for '{timezone_input}': {e}")
            return TimezoneValidationResult(
                is_valid=False,
                normalized_name="",
                original_input=timezone_input,
                format_type=TimezoneFormat.UNKNOWN,
                error_message=f"Validation error: {str(e)}"
            )
    
    def _validate_iana_timezone(self, timezone_name: str) -> TimezoneValidationResult:
        """Validate IANA timezone name."""
        try:
            if ZONEINFO_AVAILABLE:
                # Use zoneinfo (Python 3.9+)
                try:
                    tz = zoneinfo.ZoneInfo(timezone_name)
                    
                    # Test the timezone by creating a datetime
                    test_dt = datetime.now(tz)
                    utc_offset_seconds = test_dt.utcoffset().total_seconds()
                    utc_offset_hours = utc_offset_seconds / 3600
                    
                    return TimezoneValidationResult(
                        is_valid=True,
                        normalized_name=timezone_name,
                        original_input=timezone_name,
                        format_type=TimezoneFormat.IANA,
                        iana_name=timezone_name,
                        utc_offset_hours=utc_offset_hours,
                        utc_offset_seconds=int(utc_offset_seconds),
                        display_name=self._get_timezone_display_name(timezone_name)
                    )
                    
                except zoneinfo.ZoneInfoNotFoundError:
                    pass
            
            elif PYTZ_AVAILABLE:
                # Fallback to pytz
                try:
                    tz = pytz.timezone(timezone_name)
                    
                    # Get current offset (may vary due to DST)
                    test_dt = datetime.now()
                    localized_dt = tz.localize(test_dt)
                    utc_offset_seconds = localized_dt.utcoffset().total_seconds()
                    utc_offset_hours = utc_offset_seconds / 3600
                    
                    return TimezoneValidationResult(
                        is_valid=True,
                        normalized_name=timezone_name,
                        original_input=timezone_name,
                        format_type=TimezoneFormat.IANA,
                        iana_name=timezone_name,
                        utc_offset_hours=utc_offset_hours,
                        utc_offset_seconds=int(utc_offset_seconds),
                        display_name=self._get_timezone_display_name(timezone_name),
                        warnings=["Using pytz fallback - zoneinfo not available"]
                    )
                    
                except pytz.exceptions.UnknownTimeZoneError:
                    pass
            
            else:
                return TimezoneValidationResult(
                    is_valid=False,
                    normalized_name="",
                    original_input=timezone_name,
                    format_type=TimezoneFormat.UNKNOWN,
                    error_message="No timezone library available (zoneinfo or pytz required)"
                )
        
        except Exception as e:
            logger.debug(f"IANA timezone validation failed for '{timezone_name}': {e}")
        
        return TimezoneValidationResult(
            is_valid=False,
            normalized_name="",
            original_input=timezone_name,
            format_type=TimezoneFormat.UNKNOWN,
            error_message=f"Invalid IANA timezone: {timezone_name}"
        )
    
    def _validate_utc_offset(self, offset_str: str) -> TimezoneValidationResult:
        """Validate UTC offset format."""
        for pattern in self._utc_offset_patterns:
            match = pattern.match(offset_str)
            if match:
                try:
                    if len(match.groups()) == 3:  # UTC+7, GMT-5 format
                        sign, hours, minutes = match.groups()
                        hours = int(hours)
                        minutes = int(minutes) if minutes else 0
                    elif len(match.groups()) == 2:  # +0700 format
                        sign, offset = match.groups()
                        if len(offset) == 4:
                            hours = int(offset[:2])
                            minutes = int(offset[2:])
                        else:
                            hours = int(offset)
                            minutes = 0
                    else:
                        continue
                    
                    # Validate ranges
                    if hours > 18 or minutes > 59:
                        continue
                    
                    # Calculate total offset
                    total_minutes = hours * 60 + minutes
                    if sign == '-':
                        total_minutes = -total_minutes
                    
                    utc_offset_hours = total_minutes / 60
                    utc_offset_seconds = total_minutes * 60
                    
                    # Normalize to standard format
                    normalized_name = f"UTC{'+' if total_minutes >= 0 else ''}{utc_offset_hours:+.1f}".replace('.0', '')
                    
                    # Try to find corresponding IANA timezone
                    iana_name = self._offset_to_iana_timezone(utc_offset_hours)
                    
                    warnings = []
                    if not iana_name:
                        warnings.append("No corresponding IANA timezone found for this offset")
                    
                    return TimezoneValidationResult(
                        is_valid=True,
                        normalized_name=normalized_name,
                        original_input=offset_str,
                        format_type=TimezoneFormat.UTC_OFFSET,
                        iana_name=iana_name,
                        utc_offset_hours=utc_offset_hours,
                        utc_offset_seconds=utc_offset_seconds,
                        display_name=f"UTC{utc_offset_hours:+.1f}".replace('.0', ''),
                        warnings=warnings
                    )
                    
                except (ValueError, TypeError) as e:
                    logger.debug(f"UTC offset parsing error for '{offset_str}': {e}")
                    continue
        
        return TimezoneValidationResult(
            is_valid=False,
            normalized_name="",
            original_input=offset_str,
            format_type=TimezoneFormat.UNKNOWN,
            error_message=f"Invalid UTC offset format: {offset_str}"
        )
    
    def _validate_legacy_timezone(self, timezone_str: str) -> TimezoneValidationResult:
        """Validate legacy timezone formats."""
        # Check direct mapping
        if timezone_str.upper() in self._legacy_mappings:
            iana_name = self._legacy_mappings[timezone_str.upper()]
            
            # Validate the mapped IANA name
            iana_result = self._validate_iana_timezone(iana_name)
            if iana_result.is_valid:
                return TimezoneValidationResult(
                    is_valid=True,
                    normalized_name=iana_name,
                    original_input=timezone_str,
                    format_type=TimezoneFormat.LEGACY,
                    iana_name=iana_name,
                    utc_offset_hours=iana_result.utc_offset_hours,
                    utc_offset_seconds=iana_result.utc_offset_seconds,
                    display_name=iana_result.display_name,
                    warnings=[f"Legacy timezone '{timezone_str}' mapped to '{iana_name}'"]
                )
        
        return TimezoneValidationResult(
            is_valid=False,
            normalized_name="",
            original_input=timezone_str,
            format_type=TimezoneFormat.UNKNOWN,
            error_message=f"Unknown legacy timezone: {timezone_str}"
        )
    
    def _offset_to_iana_timezone(self, utc_offset_hours: float) -> Optional[str]:
        """Convert UTC offset to most appropriate IANA timezone."""
        offset_mapping = {
            7.0: "Asia/Ho_Chi_Minh",    # UTC+7
            9.0: "Asia/Tokyo",          # UTC+9
            8.0: "Asia/Shanghai",       # UTC+8
            5.5: "Asia/Kolkata",        # UTC+5:30
            0.0: "UTC",                 # UTC+0
            -5.0: "America/New_York",   # UTC-5
            -8.0: "America/Los_Angeles", # UTC-8
            -6.0: "America/Chicago",    # UTC-6
        }
        
        return offset_mapping.get(utc_offset_hours)
    
    def _get_timezone_display_name(self, iana_name: str) -> str:
        """Generate user-friendly display name for timezone."""
        try:
            # Simple mapping for common timezones
            display_names = {
                "Asia/Ho_Chi_Minh": "Vietnam (Ho Chi Minh City)",
                "Asia/Tokyo": "Japan (Tokyo)",
                "Asia/Shanghai": "China (Shanghai)",
                "America/New_York": "US Eastern",
                "America/Los_Angeles": "US Pacific",
                "America/Chicago": "US Central",
                "Europe/London": "UK (London)",
                "UTC": "Coordinated Universal Time",
            }
            
            if iana_name in display_names:
                return display_names[iana_name]
            
            # Generate from IANA name
            parts = iana_name.split('/')
            if len(parts) == 2:
                region, city = parts
                city = city.replace('_', ' ')
                return f"{region} ({city})"
            
            return iana_name.replace('_', ' ')
            
        except Exception:
            return iana_name
    
    def get_available_iana_timezones(self, filter_common: bool = False) -> List[str]:
        """
        Get list of available IANA timezones.
        
        Args:
            filter_common: If True, return only commonly used timezones
            
        Returns:
            List of available IANA timezone names
        """
        with self._iana_zones_lock:
            if self._iana_zones is None:
                self._iana_zones = self._load_iana_timezones()
        
        if filter_common:
            # Common timezones for Asia-Pacific region and major zones
            common_zones = [
                "UTC",
                "Asia/Ho_Chi_Minh",
                "Asia/Tokyo", 
                "Asia/Shanghai",
                "Asia/Seoul",
                "Asia/Singapore",
                "Asia/Bangkok",
                "Asia/Jakarta",
                "Asia/Manila",
                "Asia/Kuala_Lumpur",
                "Asia/Kolkata",
                "Asia/Dubai",
                "Europe/London",
                "Europe/Paris",
                "Europe/Berlin",
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "Australia/Sydney",
                "Australia/Melbourne",
            ]
            return [tz for tz in common_zones if tz in self._iana_zones]
        
        return sorted(self._iana_zones)
    
    def _load_iana_timezones(self) -> List[str]:
        """Load available IANA timezones."""
        try:
            if ZONEINFO_AVAILABLE:
                return list(zoneinfo.available_timezones())
            elif PYTZ_AVAILABLE:
                return list(pytz.all_timezones)
            else:
                # Fallback list of common timezones
                return [
                    "UTC", "Asia/Ho_Chi_Minh", "Asia/Tokyo", "Asia/Shanghai",
                    "America/New_York", "America/Chicago", "America/Los_Angeles",
                    "Europe/London", "Europe/Paris"
                ]
        except Exception as e:
            logger.warning(f"Failed to load IANA timezones: {e}")
            return []
    
    def get_timezone_info(self, timezone_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a timezone.
        
        Args:
            timezone_name: Timezone name to get info for
            
        Returns:
            Dictionary with timezone information
        """
        result = self.validate_timezone(timezone_name)
        
        info = {
            'is_valid': result.is_valid,
            'normalized_name': result.normalized_name,
            'format_type': result.format_type.value,
            'iana_name': result.iana_name,
            'display_name': result.display_name,
            'utc_offset_hours': result.utc_offset_hours,
            'utc_offset_seconds': result.utc_offset_seconds,
            'warnings': result.warnings,
            'error_message': result.error_message
        }
        
        # Add current time information if valid
        if result.is_valid and result.iana_name:
            try:
                if ZONEINFO_AVAILABLE:
                    tz = zoneinfo.ZoneInfo(result.iana_name)
                    current_time = datetime.now(tz)
                elif PYTZ_AVAILABLE and result.iana_name != "UTC":
                    tz = pytz.timezone(result.iana_name)
                    current_time = datetime.now(tz)
                else:
                    current_time = datetime.now(timezone.utc)
                
                info['current_time'] = current_time.isoformat()
                info['current_offset'] = current_time.strftime('%z')
                
            except Exception as e:
                logger.debug(f"Failed to get current time for {timezone_name}: {e}")
        
        return info
    
    def normalize_timezone_for_storage(self, timezone_input: str) -> str:
        """
        Normalize timezone for database storage.
        
        Args:
            timezone_input: Input timezone string
            
        Returns:
            Normalized timezone name suitable for database storage
        """
        result = self.validate_timezone(timezone_input)
        
        if not result.is_valid:
            # Return original input with warning logged
            logger.warning(f"Invalid timezone for storage normalization: {timezone_input}")
            return timezone_input
        
        # Prefer IANA names for storage
        if result.iana_name:
            return result.iana_name
        
        # Fall back to normalized name
        return result.normalized_name
    
    def clear_cache(self):
        """Clear validation cache."""
        with self._cache_lock:
            self._cache.clear()
        logger.info("Timezone validation cache cleared")


# Singleton instance for easy import
timezone_validator = TimezoneValidator()

# Convenience functions
def validate_timezone(timezone_input: str) -> TimezoneValidationResult:
    """Validate a timezone string using the global validator."""
    return timezone_validator.validate_timezone(timezone_input)

def get_available_timezones(common_only: bool = False) -> List[str]:
    """Get list of available IANA timezones."""
    return timezone_validator.get_available_iana_timezones(filter_common=common_only)

def normalize_timezone(timezone_input: str) -> str:
    """Normalize timezone for storage."""
    return timezone_validator.normalize_timezone_for_storage(timezone_input)

def get_timezone_info(timezone_name: str) -> Dict[str, Any]:
    """Get comprehensive timezone information."""
    return timezone_validator.get_timezone_info(timezone_name)