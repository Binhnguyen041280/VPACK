#!/usr/bin/env python3
"""
Simplified PyDriveDownloader for VTrack
Focus: Reliability + Simplicity for end users
No over-engineering, no complex notifications
"""

import os
import sys
import json
import logging
import socket
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Core components (keep separation of concerns)
from .pydrive_core import PyDriveCore
from .pydrive_error_manager import PyDriveErrorManager

# Existing VTrack infrastructure  
from modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)

# Simple configuration
DEFAULT_SYNC_INTERVAL_MINUTES = 15
MAX_ERROR_COUNT_BEFORE_SLOWDOWN = 3

class PyDriveDownloader:
    """
    Simplified integration layer for VTrack PyDrive operations
    Focus: Reliable sync with minimal user intervention needed
    """
    
    def __init__(self):
        # Essential components only
        self.sync_timers = {}
        self.sync_locks = {}
        
        # Core components (still good separation)
        self.core = PyDriveCore()
        self.error_manager = PyDriveErrorManager()
        
        logger.info("🚀 PyDriveDownloader initialized - Simple & Reliable")
    
    # ==================== DATABASE HELPER FUNCTIONS ====================
    
    def get_sync_status(self, source_id: int):
        """Get sync status for a source - local implementation"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM sync_status WHERE source_id = ?
                """, (source_id,))
                
                result = cursor.fetchone()
                
                if result:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return None
    
    def initialize_sync_status(self, source_id: int, sync_enabled: bool = True, interval_minutes: int = 10):
        """Initialize sync status for a new source - local implementation"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now()
                next_sync = now + timedelta(minutes=interval_minutes)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO sync_status (
                        source_id, sync_enabled, last_sync_timestamp, next_sync_timestamp,
                        sync_interval_minutes, last_sync_status, last_sync_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_id, 
                    1 if sync_enabled else 0,
                    now.isoformat(),
                    next_sync.isoformat(),
                    interval_minutes,
                    'initialized',
                    'Auto-sync initialized'
                ))
            return True
        except Exception as e:
            logger.error(f"Error initializing sync status: {e}")
            return False
    
    # ==================== CORE API (Simplified) ====================
    
    def start_auto_sync(self, source_id: int) -> bool:
        """Start auto-sync - simple success/failure"""
        try:
            if source_id in self.sync_timers:
                return True  # Already running
            
            # Validate source
            if not self.core._get_source_config(source_id):
                return False
            
            # Initialize if needed
            if not self.get_sync_status(source_id):
                self.initialize_sync_status(source_id, sync_enabled=True, interval_minutes=DEFAULT_SYNC_INTERVAL_MINUTES)
            
            # Create lock and schedule
            self.sync_locks[source_id] = threading.Lock()
            self._schedule_next_sync(source_id)
            
            logger.info(f"✅ Auto-sync started for source {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start auto-sync: {e}")
            return False
    
    def stop_auto_sync(self, source_id: int) -> bool:
        """Stop auto-sync - simple success/failure"""
        try:
            if source_id in self.sync_timers:
                self.sync_timers[source_id].cancel()
                del self.sync_timers[source_id]
                del self.sync_locks[source_id]
            
            self._update_simple_status(source_id, 'stopped', 'Đã dừng bởi người dùng')
            logger.info(f"✅ Auto-sync stopped for source {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping sync: {e}")
            return False
    
    def force_sync_now(self, source_id: int) -> Dict:
        """Force sync with simple result"""
        logger.info(f"🚀 Manual sync requested for source {source_id}")
        return self._perform_sync(source_id)
    
    def get_simple_status(self, source_id: int) -> Dict:
        """Get user-friendly status - 3 states only"""
        try:
            status = self.get_sync_status(source_id)
            if not status:
                return {'status': 'not_configured', 'message': 'Chưa cấu hình'}
            
            # Map complex status to simple user states
            last_status = status.get('last_sync_status', 'unknown')
            error_count = status.get('error_count', 0)
            
            if last_status == 'success' and error_count == 0:
                return {
                    'status': 'working',
                    'message': 'Đang hoạt động bình thường',
                    'last_sync': status.get('last_sync_timestamp', ''),
                    'files_count': status.get('files_downloaded_count', 0)
                }
            elif error_count > 0 and error_count < 5:
                return {
                    'status': 'retrying', 
                    'message': 'Đang thử lại do lỗi tạm thời',
                    'next_retry': status.get('next_sync_timestamp', '')
                }
            else:
                return {
                    'status': 'stopped',
                    'message': 'Cần kiểm tra cài đặt',
                    'error_message': status.get('last_sync_message', '')
                }
                
        except Exception as e:
            return {'status': 'error', 'message': f'Lỗi: {str(e)}'}
    
    # ==================== SYNC OPERATIONS (Simplified) ====================
    
    def _perform_sync(self, source_id: int) -> Dict:
        """Enhanced với timeout detection"""
        # Get lock
        if source_id not in self.sync_locks:
            self.sync_locks[source_id] = threading.Lock()
        
        if not self.sync_locks[source_id].acquire(blocking=False):
            return {'success': False, 'message': 'Sync đang chạy'}
        
        try:
            logger.info(f"🔄 Starting sync for source {source_id}")
            
            # ✅ SIMPLE: Basic network check
            try:
                socket.gethostbyname('google.com')
            except Exception:
                return {
                    'success': False, 
                    'message': 'No network connectivity',
                    'retry_suggested': True
                }
            
            # Perform actual sync
            result = self.core.sync_source(source_id)
            
            if result.get('success'):
                self._update_simple_status(source_id, 'active', 'Đang hoạt động bình thường')
            else:
                # ✅ SIMPLE: Check if timeout error
                error_msg = result.get('message', '').lower()
                if any(keyword in error_msg for keyword in ['timeout', 'connection', 'network']):
                    self._update_simple_status(source_id, 'retrying', 'Đang thử lại do lỗi tạm thời')
                else:
                    self._update_simple_status(source_id, 'error', f'Lỗi: {result.get("message")}')
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Sync failed for source {source_id}: {e}")
            
            # ✅ SIMPLE: Classify error type
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
                self._update_simple_status(source_id, 'retrying', 'Đang thử lại do mất kết nối')
                return {'success': False, 'message': 'Network timeout', 'retry_suggested': True}
            else:
                self._update_simple_status(source_id, 'error', f'Lỗi hệ thống: {str(e)}')
                return {'success': False, 'message': str(e)}
        
        finally:
            self.sync_locks[source_id].release()
    
    # ==================== DATABASE OPERATIONS (Minimal) ====================
    
    def _update_success_status(self, source_id: int, result: Dict):
        """Update status after successful sync"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_status 
                    SET last_sync_timestamp = ?,
                        last_sync_status = 'success',
                        last_sync_message = ?,
                        files_downloaded_count = files_downloaded_count + ?,
                        total_download_size_mb = total_download_size_mb + ?,
                        error_count = 0,
                        last_error_type = NULL
                    WHERE source_id = ?
                """, (
                    datetime.now().isoformat(),
                    result.get('message', 'Sync completed'),
                    result.get('files_downloaded', 0),
                    result.get('total_size_mb', 0.0),
                    source_id
                ))
        except Exception as e:
            logger.error(f"❌ Error updating success status: {e}")
    
    def _update_error_status(self, source_id: int, error_message: str):
        """Update status after failed sync"""
        try:
            # Simple error classification
            error_type = 'unknown'
            if 'network' in error_message.lower() or 'timeout' in error_message.lower():
                error_type = 'network'
            elif 'oauth' in error_message.lower() or 'token' in error_message.lower():
                error_type = 'auth'
            elif 'quota' in error_message.lower() or 'limit' in error_message.lower():
                error_type = 'quota'
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_status 
                    SET last_sync_timestamp = ?,
                        last_sync_status = 'failed',
                        last_sync_message = ?,
                        error_count = error_count + 1,
                        last_error_type = ?
                    WHERE source_id = ?
                """, (
                    datetime.now().isoformat(),
                    error_message,
                    error_type,
                    source_id
                ))
        except Exception as e:
            logger.error(f"❌ Error updating error status: {e}")
    
    def _update_simple_status(self, source_id: int, status: str, message: str):
        """Simple status update"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_status 
                    SET last_sync_timestamp = ?,
                        last_sync_status = ?,
                        last_sync_message = ?
                    WHERE source_id = ?
                """, (datetime.now().isoformat(), status, message, source_id))
        except Exception as e:
            logger.error(f"❌ Error updating status: {e}")
    
    # ==================== TIMER MANAGEMENT (Simplified) ====================
    
    def _schedule_next_sync(self, source_id: int):
        """Schedule next sync with simple backoff"""
        try:
            status = self.get_sync_status(source_id)
            if not status or not status.get('sync_enabled', True):
                return
            
            # Simple interval calculation
            base_interval = status.get('sync_interval_minutes', DEFAULT_SYNC_INTERVAL_MINUTES)
            error_count = status.get('error_count', 0)
            
            # Simple backoff: more errors = longer wait
            if error_count >= MAX_ERROR_COUNT_BEFORE_SLOWDOWN:
                interval = min(base_interval * 2, 60)  # Max 1 hour
            else:
                interval = base_interval
            
            next_sync_time = datetime.now() + timedelta(minutes=interval)
            
            # Update database
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_status 
                    SET next_sync_timestamp = ?
                    WHERE source_id = ?
                """, (next_sync_time.isoformat(), source_id))
            
            # Schedule timer
            timer = threading.Timer(interval * 60, self._timer_callback, args=(source_id,))
            timer.daemon = True
            self.sync_timers[source_id] = timer
            timer.start()
            
            logger.info(f"⏰ Next sync scheduled for source {source_id} in {interval} minutes")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling sync: {e}")
    
    def _timer_callback(self, source_id: int):
        """Enhanced timer callback - never dies"""
        try:
            # Update heartbeat
            logger.debug(f"⏰ Timer callback for source {source_id}")
            
            # Perform sync
            sync_result = self._perform_sync(source_id)
            
            if sync_result.get('success'):
                logger.info(f"✅ Timer sync completed for source {source_id}")
            else:
                logger.warning(f"⚠️ Timer sync failed: {sync_result.get('message')}")
                
        except Exception as e:
            logger.error(f"❌ Timer callback error: {e}")
        
        finally:
            # ✅ CRITICAL: ALWAYS reschedule - never let timer die
            try:
                status = self.get_sync_status(source_id)
                if status and status.get('sync_enabled', True):
                    # Normal rescheduling
                    interval = 2  # minutes
                    timer = threading.Timer(interval * 60, self._timer_callback, args=(source_id,))
                    timer.daemon = True
                    self.sync_timers[source_id] = timer
                    timer.start()
                    logger.debug(f"⏰ Next sync scheduled for source {source_id} in {interval} minutes")
                else:
                    # Remove if disabled
                    self.sync_timers.pop(source_id, None)
                    
            except Exception as schedule_error:
                logger.error(f"❌ CRITICAL: Failed to reschedule timer: {schedule_error}")
                
                # ✅ EMERGENCY FALLBACK: Force reschedule
                emergency_timer = threading.Timer(5 * 60, self._timer_callback, args=(source_id,))
                emergency_timer.daemon = True
                self.sync_timers[source_id] = emergency_timer
                emergency_timer.start()
                logger.warning(f"🚨 Emergency timer scheduled for source {source_id}")
    
    # ==================== BULK OPERATIONS (Essential only) ====================
    
    def auto_start_all_enabled_sources(self) -> Dict:
        """Start all enabled sources - simple reporting"""
        try:
            logger.info("🚀 Auto-starting enabled cloud sources...")
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT vs.id, vs.name, ss.sync_enabled 
                    FROM video_sources vs
                    LEFT JOIN sync_status ss ON vs.id = ss.source_id
                    WHERE vs.active = 1 AND vs.source_type = 'cloud'
                """)
                sources = cursor.fetchall()
            
            started_count = 0
            for source_id, name, sync_enabled in sources:
                if sync_enabled or sync_enabled is None:
                    if self.start_auto_sync(source_id):
                        started_count += 1
            
            logger.info(f"🎉 Auto-started {started_count}/{len(sources)} sources")
            return {'success': True, 'started_count': started_count, 'total_sources': len(sources)}
            
        except Exception as e:
            logger.error(f"❌ Auto-start failed: {e}")
            return {'success': False, 'error': str(e)}

# ==================== GLOBAL INSTANCE ====================

# Global instance for backward compatibility
pydrive_downloader = PyDriveDownloader()

# Simple convenience functions
def start_source_sync(source_id: int) -> bool:
    return pydrive_downloader.start_auto_sync(source_id)

def stop_source_sync(source_id: int) -> bool:
    return pydrive_downloader.stop_auto_sync(source_id)

def force_sync_source(source_id: int) -> Dict:
    return pydrive_downloader.force_sync_now(source_id)

def get_source_status(source_id: int) -> Dict:
    return pydrive_downloader.get_simple_status(source_id)