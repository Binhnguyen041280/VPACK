#!/usr/bin/env python3
"""
Global Timezone Configuration System for V_Track

Provides centralized timezone management for the entire application, replacing
per-camera timezone settings and hardcoded timezone values throughout the system.

Features:
- Single source of truth for application timezone
- Automatic fallback to system/user timezone detection
- Database-backed configuration with caching
- Migration support from per-camera to global settings
- Thread-safe operations
- Configuration validation and error handling

Usage:
    from modules.config.global_timezone_config import global_timezone_config
    
    # Get global timezone
    tz = global_timezone_config.get_global_timezone()
    
    # Set global timezone
    global_timezone_config.set_global_timezone("Asia/Tokyo")
    
    # Get timezone info for UI
    info = global_timezone_config.get_timezone_info()
"""

import threading
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

from modules.db_utils.safe_connection import safe_db_connection
from modules.utils.timezone_validator import timezone_validator, TimezoneValidationResult
from modules.config.logging_config import get_logger

logger = get_logger(__name__, {"module": "global_timezone_config"})

@dataclass
class GlobalTimezoneInfo:
    """Global timezone configuration information."""
    timezone_iana: str
    timezone_display: str
    utc_offset_hours: float
    is_validated: bool
    last_updated: datetime
    warnings: list
    source: str  # 'database', 'system', 'fallback'

class GlobalTimezoneConfig:
    """
    Global timezone configuration manager.
    
    Provides centralized timezone management for the entire V_Track application,
    replacing scattered per-camera timezone settings and hardcoded values.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Fallback timezone if all else fails
    SYSTEM_FALLBACK_TIMEZONE = "UTC"
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize global timezone configuration."""
        if self._initialized:
            return
        
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Initialize the configuration
        self._ensure_schema()
        self._initialized = True
        
        logger.info("Global timezone configuration initialized")
    
    def _ensure_schema(self):
        """Ensure global timezone configuration table exists."""
        try:
            # Import db_rwlock conditionally to avoid circular imports
            try:
                from modules.scheduler.db_sync import db_rwlock
                use_rwlock = True
            except ImportError:
                use_rwlock = False
                logger.debug("db_rwlock not available, proceeding without locking")
            
            if use_rwlock:
                with db_rwlock.gen_wlock():
                    with safe_db_connection() as conn:
                        self._create_schema(conn)
            else:
                with safe_db_connection() as conn:
                    self._create_schema(conn)
                    
        except Exception as e:
            logger.error(f"Failed to ensure schema: {e}")
            # Continue without database - will use fallback
    
    def _create_schema(self, conn):
        """Create global timezone configuration schema."""
        cursor = conn.cursor()
        
        # Create global_timezone_config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_timezone_config (
                id INTEGER PRIMARY KEY DEFAULT 1,
                timezone_iana TEXT NOT NULL,
                timezone_display TEXT,
                utc_offset_hours REAL,
                is_validated INTEGER DEFAULT 0,
                validation_warnings TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT DEFAULT 'manual'
            )
        """)
        
        # Ensure only one row exists
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_global_tz_single ON global_timezone_config(id)")
        
        conn.commit()
        logger.debug("Global timezone configuration schema created")
    
    def get_global_timezone(self) -> str:
        """
        Get the global timezone IANA name.
        
        Returns:
            IANA timezone name (e.g., 'Asia/Ho_Chi_Minh')
        """
        try:
            info = self._get_cached_timezone_info()
            return info.timezone_iana
        except Exception as e:
            logger.warning(f"Failed to get global timezone: {e}, using fallback")
            return self._get_fallback_timezone()
    
    def get_timezone_info(self) -> GlobalTimezoneInfo:
        """
        Get comprehensive global timezone information.
        
        Returns:
            GlobalTimezoneInfo object with all timezone details
        """
        try:
            return self._get_cached_timezone_info()
        except Exception as e:
            logger.warning(f"Failed to get timezone info: {e}, using fallback")
            return self._create_fallback_info()
    
    def set_global_timezone(self, timezone_iana: str, source: str = 'manual') -> Tuple[bool, Optional[str]]:
        """
        Set the global timezone.
        
        Args:
            timezone_iana: IANA timezone name
            source: Source of the timezone setting ('manual', 'migration', 'auto')
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Validate timezone
            validation_result = timezone_validator.validate_timezone(timezone_iana)
            if not validation_result.is_valid:
                return False, f"Invalid timezone: {validation_result.error_message}"
            
            # Save to database
            self._save_timezone_to_db(validation_result, source)
            
            # Clear cache
            self._clear_cache()
            
            logger.info(f"Global timezone set to {timezone_iana} from {source}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to set global timezone: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def migrate_from_general_info(self) -> Dict[str, Any]:
        """
        Migrate timezone from general_info table to global configuration.
        
        Returns:
            Migration result dictionary
        """
        try:
            # Import db_rwlock conditionally
            try:
                from modules.scheduler.db_sync import db_rwlock
                use_rwlock = True
            except ImportError:
                use_rwlock = False
            
            if use_rwlock:
                with db_rwlock.gen_rlock():
                    with safe_db_connection() as conn:
                        return self._perform_migration(conn)
            else:
                with safe_db_connection() as conn:
                    return self._perform_migration(conn)
                    
        except Exception as e:
            error_msg = f"Migration failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _perform_migration(self, conn) -> Dict[str, Any]:
        """Perform the actual migration from general_info."""
        cursor = conn.cursor()
        
        # Check if global config already exists
        cursor.execute("SELECT COUNT(*) FROM global_timezone_config WHERE id = 1")
        if cursor.fetchone()[0] > 0:
            return {"success": True, "message": "Global timezone already configured", "action": "none"}
        
        # Get timezone from general_info
        cursor.execute("""
            SELECT timezone, timezone_iana_name, timezone_display_name, 
                   timezone_utc_offset_hours, timezone_validated, 
                   timezone_validation_warnings
            FROM general_info 
            WHERE id = 1
        """)
        
        result = cursor.fetchone()
        if not result:
            # No general_info found, use system detection
            return self._migrate_from_system_detection()
        
        timezone_str, iana_name, display_name, offset_hours, validated, warnings = result
        
        # Use IANA name if available, otherwise the original timezone string
        target_timezone = iana_name or timezone_str
        
        if target_timezone:
            success, error = self.set_global_timezone(target_timezone, source='migration')
            if success:
                return {
                    "success": True, 
                    "message": f"Migrated timezone from general_info: {target_timezone}",
                    "migrated_timezone": target_timezone,
                    "action": "migrated"
                }
            else:
                return {"success": False, "error": error, "action": "failed"}
        else:
            return self._migrate_from_system_detection()
    
    def _migrate_from_system_detection(self) -> Dict[str, Any]:
        """Migrate using system timezone detection."""
        try:
            # Try to detect system timezone
            import time
            import os
            
            # Try multiple methods to detect system timezone
            detected_tz = None
            
            # Method 1: TZ environment variable
            if 'TZ' in os.environ:
                detected_tz = os.environ['TZ']
            
            # Method 2: System timezone detection (Linux/macOS)
            if not detected_tz:
                try:
                    import subprocess
                    result = subprocess.run(['timedatectl', 'show', '--property=Timezone'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.startswith('Timezone='):
                                detected_tz = line.split('=', 1)[1]
                                break
                except:
                    pass
            
            # Method 3: Python timezone detection
            if not detected_tz:
                try:
                    import zoneinfo
                    detected_tz = str(zoneinfo.ZoneInfo('localtime'))
                except:
                    pass
            
            # Fallback to Asia/Ho_Chi_Minh for backward compatibility
            if not detected_tz:
                detected_tz = "Asia/Ho_Chi_Minh"
                logger.info("Using Asia/Ho_Chi_Minh as fallback for migration")
            
            success, error = self.set_global_timezone(detected_tz, source='migration')
            if success:
                return {
                    "success": True,
                    "message": f"Migrated timezone from system detection: {detected_tz}",
                    "migrated_timezone": detected_tz,
                    "action": "system_detected"
                }
            else:
                return {"success": False, "error": error, "action": "failed"}
                
        except Exception as e:
            logger.error(f"System detection migration failed: {e}")
            # Final fallback
            success, error = self.set_global_timezone(self.SYSTEM_FALLBACK_TIMEZONE, source='fallback')
            return {
                "success": success,
                "message": f"Used fallback timezone: {self.SYSTEM_FALLBACK_TIMEZONE}",
                "migrated_timezone": self.SYSTEM_FALLBACK_TIMEZONE,
                "action": "fallback",
                "error": error if not success else None
            }
    
    def _get_cached_timezone_info(self) -> GlobalTimezoneInfo:
        """Get timezone info from cache or database."""
        with self._cache_lock:
            # Check cache validity
            if (self._cache_timestamp and 
                self._cache and 
                (datetime.now() - self._cache_timestamp).total_seconds() < self._cache_ttl):
                return self._cache['timezone_info']
            
            # Load from database
            info = self._load_from_database()
            
            # Update cache
            self._cache = {'timezone_info': info}
            self._cache_timestamp = datetime.now()
            
            return info
    
    def _load_from_database(self) -> GlobalTimezoneInfo:
        """Load timezone info from database."""
        try:
            # Import db_rwlock conditionally
            try:
                from modules.scheduler.db_sync import db_rwlock
                use_rwlock = True
            except ImportError:
                use_rwlock = False
            
            if use_rwlock:
                with db_rwlock.gen_rlock():
                    with safe_db_connection() as conn:
                        return self._fetch_from_db(conn)
            else:
                with safe_db_connection() as conn:
                    return self._fetch_from_db(conn)
                    
        except Exception as e:
            logger.warning(f"Failed to load from database: {e}")
            return self._create_fallback_info()
    
    def _fetch_from_db(self, conn) -> GlobalTimezoneInfo:
        """Fetch timezone info from database connection."""
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timezone_iana, timezone_display, utc_offset_hours,
                   is_validated, validation_warnings, updated_at, source
            FROM global_timezone_config 
            WHERE id = 1
        """)
        
        result = cursor.fetchone()
        if not result:
            # No global config found, trigger migration
            migration_result = self.migrate_from_general_info()
            if migration_result.get('success'):
                # Retry after migration
                cursor.execute("""
                    SELECT timezone_iana, timezone_display, utc_offset_hours,
                           is_validated, validation_warnings, updated_at, source
                    FROM global_timezone_config 
                    WHERE id = 1
                """)
                result = cursor.fetchone()
        
        if result:
            tz_iana, tz_display, offset_hours, is_validated, warnings_json, updated_at, source = result
            
            warnings = []
            if warnings_json:
                try:
                    warnings = json.loads(warnings_json)
                except:
                    pass
            
            return GlobalTimezoneInfo(
                timezone_iana=tz_iana,
                timezone_display=tz_display or tz_iana,
                utc_offset_hours=offset_hours or 0,
                is_validated=bool(is_validated),
                last_updated=datetime.fromisoformat(updated_at) if updated_at else datetime.now(),
                warnings=warnings,
                source=source or 'database'
            )
        else:
            return self._create_fallback_info()
    
    def _save_timezone_to_db(self, validation_result: TimezoneValidationResult, source: str):
        """Save validated timezone to database."""
        # Import db_rwlock conditionally
        try:
            from modules.scheduler.db_sync import db_rwlock
            use_rwlock = True
        except ImportError:
            use_rwlock = False
        
        if use_rwlock:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    self._perform_save(conn, validation_result, source)
        else:
            with safe_db_connection() as conn:
                self._perform_save(conn, validation_result, source)
    
    def _perform_save(self, conn, validation_result: TimezoneValidationResult, source: str):
        """Perform the actual database save."""
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        warnings_json = json.dumps(validation_result.warnings or [])
        
        cursor.execute("""
            INSERT OR REPLACE INTO global_timezone_config (
                id, timezone_iana, timezone_display, utc_offset_hours,
                is_validated, validation_warnings, created_at, updated_at, source
            ) VALUES (1, ?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            validation_result.iana_name or validation_result.normalized_name,
            validation_result.display_name,
            validation_result.utc_offset_hours,
            warnings_json,
            now,
            now,
            source
        ))
        
        conn.commit()
    
    def _get_fallback_timezone(self) -> str:
        """Get fallback timezone when all else fails."""
        try:
            # Try to detect current system timezone
            import time
            import os
            
            if 'TZ' in os.environ:
                return os.environ['TZ']
            
            # Fallback to hardcoded value for backward compatibility
            return "Asia/Ho_Chi_Minh"
            
        except:
            return self.SYSTEM_FALLBACK_TIMEZONE
    
    def _create_fallback_info(self) -> GlobalTimezoneInfo:
        """Create fallback timezone info."""
        fallback_tz = self._get_fallback_timezone()
        
        return GlobalTimezoneInfo(
            timezone_iana=fallback_tz,
            timezone_display=fallback_tz,
            utc_offset_hours=7.0 if fallback_tz == "Asia/Ho_Chi_Minh" else 0.0,
            is_validated=False,
            last_updated=datetime.now(),
            warnings=["Using fallback timezone - configuration not found"],
            source='fallback'
        )
    
    def _clear_cache(self):
        """Clear the timezone cache."""
        with self._cache_lock:
            self._cache.clear()
            self._cache_timestamp = None

# Create singleton instance
global_timezone_config = GlobalTimezoneConfig()

# Convenience functions for backward compatibility
def get_global_timezone() -> str:
    """Get global timezone IANA name."""
    return global_timezone_config.get_global_timezone()

def get_global_timezone_info() -> GlobalTimezoneInfo:
    """Get global timezone information."""
    return global_timezone_config.get_timezone_info()

def set_global_timezone(timezone_iana: str) -> Tuple[bool, Optional[str]]:
    """Set global timezone."""
    return global_timezone_config.set_global_timezone(timezone_iana)