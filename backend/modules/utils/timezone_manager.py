"""
TimezoneManager Module for V_Track Video Processing System

Provides unified timezone handling with support for user-configurable timezones,
UTC ↔ Local conversions, and integration with the existing safe_db_connection pattern.

Features:
    - Uses zoneinfo (Python 3.9+) as primary, pytz as fallback
    - Thread-safe implementation with caching
    - Database integration for user timezone settings
    - Comprehensive error handling and fallback mechanisms
    - Performance optimized (< 1ms for basic conversions)
    
Usage:
    from modules.utils.timezone_manager import TimezoneManager
    
    tz = TimezoneManager()
    now_local = tz.now_local()
    now_utc = tz.now_utc()
    db_timestamp = tz.format_for_db(now_local)
"""

import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Primary timezone library (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False

# Fallback timezone library
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

# V_Track modules
from modules.db_utils.safe_connection import safe_db_connection
from modules.config.logging_config import get_logger

logger = get_logger(__name__, {"module": "timezone_manager"})


class TimezoneError(Exception):
    """Custom exception for timezone-related errors."""
    pass


class TimezoneManager:
    """
    Unified timezone management for V_Track application.
    
    Provides thread-safe timezone operations with database integration
    and performance optimizations.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Default fallback timezone - now dynamically loaded from global config
    DEFAULT_TIMEZONE = "UTC"  # Safe fallback if global config fails
    
    # Cache for timezone objects and user settings
    _timezone_cache: Dict[str, Any] = {}
    _user_timezone_cache: Optional[str] = None
    _cache_lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize TimezoneManager with library checks."""
        if not hasattr(self, '_initialized'):
            self._validate_libraries()
            self._initialized = True
            logger.debug("TimezoneManager initialized successfully")
    
    def _validate_libraries(self):
        """Validate that at least one timezone library is available."""
        if not ZONEINFO_AVAILABLE and not PYTZ_AVAILABLE:
            raise TimezoneError(
                "No timezone library available. Please install Python 3.9+ "
                "(for zoneinfo) or install pytz package."
            )
        
        if ZONEINFO_AVAILABLE:
            logger.debug("Using zoneinfo for timezone operations")
        else:
            logger.debug("Using pytz fallback for timezone operations")
    
    def _get_timezone_object(self, timezone_name: str):
        """
        Get timezone object with caching for performance.
        
        Args:
            timezone_name: Timezone identifier (e.g., 'Asia/Ho_Chi_Minh')
            
        Returns:
            Timezone object (ZoneInfo or pytz timezone)
            
        Raises:
            TimezoneError: If timezone is invalid
        """
        with self._cache_lock:
            if timezone_name in self._timezone_cache:
                return self._timezone_cache[timezone_name]
            
            try:
                if ZONEINFO_AVAILABLE:
                    tz_obj = ZoneInfo(timezone_name)
                elif PYTZ_AVAILABLE:
                    tz_obj = pytz.timezone(timezone_name)
                else:
                    raise TimezoneError("No timezone library available")
                
                # Cache the timezone object
                self._timezone_cache[timezone_name] = tz_obj
                return tz_obj
                
            except Exception as e:
                logger.error(f"Invalid timezone '{timezone_name}': {e}")
                raise TimezoneError(f"Invalid timezone '{timezone_name}': {e}")
    
    def _get_user_timezone(self) -> str:
        """
        Get user's configured timezone from global configuration with caching.
        
        Returns:
            Timezone identifier string
        """
        with self._cache_lock:
            if self._user_timezone_cache is not None:
                return self._user_timezone_cache
        
        try:
            # Use global timezone configuration
            from modules.config.global_timezone_config import global_timezone_config
            timezone_str = global_timezone_config.get_global_timezone()
            
            # Validate timezone
            try:
                self._get_timezone_object(timezone_str)
                with self._cache_lock:
                    self._user_timezone_cache = timezone_str
                return timezone_str
            except TimezoneError:
                logger.warning(f"Invalid global timezone: {timezone_str}")
                
        except Exception as e:
            logger.warning(f"Failed to get global timezone: {e}")
        
        # Fallback to database for backward compatibility
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT timezone FROM general_info WHERE id = 1")
                result = cursor.fetchone()
                
                if result and result[0]:
                    timezone_str = result[0].strip()
                    
                    # Convert UTC+7 format to IANA timezone
                    if timezone_str == "UTC+7":
                        timezone_str = "Asia/Ho_Chi_Minh"  # Backward compatibility
                    
                    # Validate timezone
                    try:
                        self._get_timezone_object(timezone_str)
                        with self._cache_lock:
                            self._user_timezone_cache = timezone_str
                        return timezone_str
                    except TimezoneError:
                        logger.warning(f"Invalid timezone in database: {timezone_str}")
                
        except Exception as e:
            logger.debug(f"Database fallback failed: {e}")
        
        # Return default timezone as final fallback
        return self.DEFAULT_TIMEZONE
    
    def clear_cache(self):
        """Clear timezone cache (useful for testing or timezone updates)."""
        with self._cache_lock:
            self._timezone_cache.clear()
            self._user_timezone_cache = None
        logger.debug("Timezone cache cleared")
    
    def now_utc(self) -> datetime:
        """
        Get current datetime in UTC.
        
        Returns:
            UTC datetime with timezone info
        """
        return datetime.now(timezone.utc)
    
    def now_local(self) -> datetime:
        """
        Get current datetime in user's local timezone.
        
        Returns:
            Local datetime with timezone info
        """
        user_tz = self._get_user_timezone()
        tz_obj = self._get_timezone_object(user_tz)
        
        if ZONEINFO_AVAILABLE:
            return datetime.now(tz_obj)
        else:  # pytz
            return datetime.now(tz_obj)
    
    def to_utc(self, dt: datetime) -> datetime:
        """
        Convert datetime to UTC.
        
        Args:
            dt: Datetime object (naive or timezone-aware)
            
        Returns:
            UTC datetime with timezone info
            
        Raises:
            TimezoneError: If conversion fails
        """
        try:
            if dt.tzinfo is None:
                # Assume naive datetime is in user's local timezone
                user_tz = self._get_user_timezone()
                tz_obj = self._get_timezone_object(user_tz)
                
                if ZONEINFO_AVAILABLE:
                    dt = dt.replace(tzinfo=tz_obj)
                else:  # pytz - has localize method
                    dt = tz_obj.localize(dt)
            
            return dt.astimezone(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to convert datetime to UTC: {e}")
            raise TimezoneError(f"Failed to convert datetime to UTC: {e}")
    
    def to_local(self, dt: datetime) -> datetime:
        """
        Convert datetime to user's local timezone.
        
        Args:
            dt: Datetime object (naive or timezone-aware)
            
        Returns:
            Local datetime with timezone info
            
        Raises:
            TimezoneError: If conversion fails
        """
        try:
            user_tz = self._get_user_timezone()
            tz_obj = self._get_timezone_object(user_tz)
            
            if dt.tzinfo is None:
                # Assume naive datetime is in UTC
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt.astimezone(tz_obj)
            
        except Exception as e:
            logger.error(f"Failed to convert datetime to local timezone: {e}")
            raise TimezoneError(f"Failed to convert datetime to local timezone: {e}")
    
    def format_for_db(self, dt: datetime) -> str:
        """
        Format datetime for database storage (always as UTC ISO format).
        
        Args:
            dt: Datetime object (naive or timezone-aware)
            
        Returns:
            ISO format string in UTC
        """
        try:
            utc_dt = self.to_utc(dt)
            return utc_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Remove microseconds to 3 digits
        except Exception as e:
            logger.error(f"Failed to format datetime for database: {e}")
            raise TimezoneError(f"Failed to format datetime for database: {e}")
    
    def parse_from_db(self, dt_str: str) -> datetime:
        """
        Parse datetime from database (assumes UTC) and convert to local timezone.
        
        Args:
            dt_str: Datetime string from database
            
        Returns:
            Local datetime with timezone info
            
        Raises:
            TimezoneError: If parsing fails
        """
        try:
            # Parse datetime string (database stores as UTC)
            if '.' in dt_str:
                utc_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S.%f')
            else:
                utc_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            
            # Add UTC timezone info
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            
            # Convert to local timezone
            return self.to_local(utc_dt)
            
        except Exception as e:
            logger.error(f"Failed to parse datetime from database: {e}")
            raise TimezoneError(f"Failed to parse datetime from database: {e}")
    
    def get_timezone_offset(self, dt: Optional[datetime] = None) -> str:
        """
        Get timezone offset string (e.g., '+07:00').
        
        Args:
            dt: Datetime to get offset for (defaults to now)
            
        Returns:
            Offset string in format '+HH:MM' or '-HH:MM'
        """
        if dt is None:
            dt = self.now_local()
        elif dt.tzinfo is None:
            dt = self.to_local(dt)
        
        offset = dt.utcoffset()
        if offset is None:
            return "+00:00"
        
        total_seconds = int(offset.total_seconds())
        hours, remainder = divmod(abs(total_seconds), 3600)
        minutes = remainder // 60
        sign = '+' if total_seconds >= 0 else '-'
        
        return f"{sign}{hours:02d}:{minutes:02d}"
    
    def get_user_timezone_name(self) -> str:
        """
        Get user's configured timezone name.
        
        Returns:
            Timezone identifier string
        """
        return self._get_user_timezone()
    
    def get_user_timezone(self):
        """
        Get user's configured timezone object.
        
        Returns:
            Timezone object (ZoneInfo or pytz timezone)
        """
        user_tz_name = self._get_user_timezone()
        return self._get_timezone_object(user_tz_name)
    
    def get_timezone_object(self, timezone_str: str = None):
        """
        Get timezone object for the specified timezone string.
        
        Args:
            timezone_str: IANA timezone name (e.g., 'Asia/Ho_Chi_Minh')
                         If None, uses user's configured timezone
                         
        Returns:
            Timezone object (ZoneInfo or pytz timezone)
            
        Raises:
            TimezoneError: If timezone is invalid
        """
        if timezone_str is None:
            timezone_str = self._get_user_timezone()
        
        return self._get_timezone_object(timezone_str)
    
    def set_user_timezone(self, timezone_name: str) -> bool:
        """
        Update user's timezone in database.
        
        Args:
            timezone_name: Valid timezone identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate timezone first
            self._get_timezone_object(timezone_name)
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE general_info SET timezone = ? WHERE id = 1",
                    (timezone_name,)
                )
                conn.commit()
                
                if cursor.rowcount > 0:
                    # Clear cache to force reload
                    with self._cache_lock:
                        self._user_timezone_cache = None
                    logger.info(f"User timezone updated to: {timezone_name}")
                    return True
                else:
                    logger.warning("No rows updated when setting user timezone")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to set user timezone: {e}")
            return False
    
    @contextmanager
    def temporary_timezone(self, timezone_name: str):
        """
        Context manager for temporarily changing timezone.
        
        Args:
            timezone_name: Temporary timezone identifier
        """
        original_timezone = self._user_timezone_cache
        try:
            # Validate timezone
            self._get_timezone_object(timezone_name)
            
            # Temporarily override cache
            with self._cache_lock:
                self._user_timezone_cache = timezone_name
            
            yield self
            
        finally:
            # Restore original timezone
            with self._cache_lock:
                self._user_timezone_cache = original_timezone
    
    def to_utc_timestamp(self, dt: datetime) -> int:
        """
        Convert datetime to UTC timestamp (milliseconds since epoch).
        
        Args:
            dt: Datetime object (naive or timezone-aware)
            
        Returns:
            UTC timestamp in milliseconds
        """
        try:
            # Convert to UTC first
            utc_dt = self.to_utc(dt)
            
            # Convert to timestamp (seconds) then to milliseconds
            timestamp_ms = int(utc_dt.timestamp() * 1000)
            
            return timestamp_ms
            
        except Exception as e:
            logger.error(f"Error converting datetime to UTC timestamp: {e}")
            raise TimezoneError(f"Failed to convert to UTC timestamp: {e}")
    
    def from_utc_timestamp(self, timestamp_ms: int) -> datetime:
        """
        Convert UTC timestamp (milliseconds) to local datetime.
        
        Args:
            timestamp_ms: UTC timestamp in milliseconds
            
        Returns:
            Local datetime with timezone info
        """
        try:
            # Convert milliseconds to seconds
            timestamp_s = timestamp_ms / 1000
            
            # Create UTC datetime from timestamp
            utc_dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
            
            # Convert to local timezone
            local_dt = self.to_local(utc_dt)
            
            return local_dt
            
        except Exception as e:
            logger.error(f"Error converting UTC timestamp to datetime: {e}")
            raise TimezoneError(f"Failed to convert from UTC timestamp: {e}")
    
    def now_utc_timestamp(self) -> int:
        """
        Get current UTC timestamp in milliseconds.
        
        Returns:
            Current UTC timestamp in milliseconds
        """
        return self.to_utc_timestamp(self.now_utc())
    
    def now_local_timestamp(self) -> int:
        """
        Get current local timestamp in milliseconds.
        
        Returns:
            Current local timestamp in milliseconds
        """
        return self.to_utc_timestamp(self.now_local())


# Global instance for easy access
timezone_manager = TimezoneManager()

# Convenience functions for common operations
def now_utc() -> datetime:
    """Get current UTC datetime."""
    return timezone_manager.now_utc()

def now_local() -> datetime:
    """Get current local datetime."""
    return timezone_manager.now_local()

def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC."""
    return timezone_manager.to_utc(dt)

def to_local(dt: datetime) -> datetime:
    """Convert datetime to local timezone."""
    return timezone_manager.to_local(dt)

def format_for_db(dt: datetime) -> str:
    """Format datetime for database storage."""
    return timezone_manager.format_for_db(dt)

def parse_from_db(dt_str: str) -> datetime:
    """Parse datetime from database."""
    return timezone_manager.parse_from_db(dt_str)