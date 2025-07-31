#!/usr/bin/env python3
"""
Simplified PyDriveDownloader for VTrack
Focus: Reliability + Simplicity for end users
No over-engineering, no complex notifications
"""

import os
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Core components (keep separation of concerns)
from .pydrive_core import PyDriveCore
from .pydrive_error_manager import PyDriveErrorManager

# Existing VTrack infrastructure
from modules.db_utils import get_db_connection
from database import get_sync_status, initialize_sync_status

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
            if not get_sync_status(source_id):
                initialize_sync_status(source_id, sync_enabled=True, interval_minutes=DEFAULT_SYNC_INTERVAL_MINUTES)
            
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
            status = get_sync_status(source_id)
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
        """Simplified sync with basic error handling"""
        # Get lock
        if source_id not in self.sync_locks:
            self.sync_locks[source_id] = threading.Lock()
        
        if not self.sync_locks[source_id].acquire(blocking=False):
            return {'success': False, 'message': 'Sync đang chạy'}
        
        try:
            logger.info(f"🔄 Starting sync for source {source_id}")
            
            # Use core with simple error wrapper
            def sync_operation():
                return self.core.sync_source(source_id)
            
            # Simple retry logic (no complex error management)
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    result = sync_operation()
                    
                    if result['success']:
                        # Success - reset error count
                        self._update_success_status(source_id, result)
                        return result
                    else:
                        if attempt < max_attempts - 1:
                            logger.warning(f"⚠️ Sync attempt {attempt + 1} failed, retrying...")
                            continue
                        else:
                            # Final failure
                            self._update_error_status(source_id, result.get('message', 'Sync failed'))
                            return result
                            
                except Exception as e:
                    if attempt < max_attempts - 1:
                        logger.warning(f"⚠️ Sync error attempt {attempt + 1}: {e}")
                        continue
                    else:
                        # Final error
                        self._update_error_status(source_id, str(e))
                        return {'success': False, 'message': str(e)}
            
        finally:
            self.sync_locks[source_id].release()
    
    # ==================== DATABASE OPERATIONS (Minimal) ====================
    
    def _update_success_status(self, source_id: int, result: Dict):
        """Update status after successful sync"""
        try:
            conn = get_db_connection()
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
            conn.commit()
            conn.close()
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
            
            conn = get_db_connection()
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
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Error updating error status: {e}")
    
    def _update_simple_status(self, source_id: int, status: str, message: str):
        """Simple status update"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_status 
                SET last_sync_timestamp = ?,
                    last_sync_status = ?,
                    last_sync_message = ?
                WHERE source_id = ?
            """, (datetime.now().isoformat(), status, message, source_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Error updating status: {e}")
    
    # ==================== TIMER MANAGEMENT (Simplified) ====================
    
    def _schedule_next_sync(self, source_id: int):
        """Schedule next sync with simple backoff"""
        try:
            status = get_sync_status(source_id)
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
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_status 
                SET next_sync_timestamp = ?
                WHERE source_id = ?
            """, (next_sync_time.isoformat(), source_id))
            conn.commit()
            conn.close()
            
            # Schedule timer
            timer = threading.Timer(interval * 60, self._timer_callback, args=(source_id,))
            timer.daemon = True
            self.sync_timers[source_id] = timer
            timer.start()
            
            logger.info(f"⏰ Next sync scheduled for source {source_id} in {interval} minutes")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling sync: {e}")
    
    def _timer_callback(self, source_id: int):
        """Simple timer callback - always schedules next sync"""
        try:
            logger.debug(f"⏰ Timer callback for source {source_id}")
            
            # Perform sync
            sync_result = self._perform_sync(source_id)
            
            if sync_result.get('success'):
                logger.info(f"✅ Timer sync completed for source {source_id}")
            else:
                logger.warning(f"⚠️ Timer sync failed for source {source_id}: {sync_result.get('message')}")
            
        except Exception as e:
            logger.error(f"❌ Timer callback error: {e}")
        
        finally:
            # ALWAYS schedule next sync (never let timer die)
            try:
                current_status = get_sync_status(source_id)
                if current_status and current_status.get('sync_enabled', True):
                    self._schedule_next_sync(source_id)
                else:
                    # Remove from timers if disabled
                    self.sync_timers.pop(source_id, None)
            except Exception as schedule_error:
                logger.error(f"❌ Error scheduling next sync: {schedule_error}")
                # Emergency fallback: restart in 30 minutes
                timer = threading.Timer(30 * 60, self._timer_callback, args=(source_id,))
                timer.daemon = True
                self.sync_timers[source_id] = timer
                timer.start()
    
    # ==================== BULK OPERATIONS (Essential only) ====================
    
    def auto_start_all_enabled_sources(self) -> Dict:
        """Start all enabled sources - simple reporting"""
        try:
            logger.info("🚀 Auto-starting enabled cloud sources...")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT vs.id, vs.name, ss.sync_enabled 
                FROM video_sources vs
                LEFT JOIN sync_status ss ON vs.id = ss.source_id
                WHERE vs.active = 1 AND vs.source_type = 'cloud'
            """)
            sources = cursor.fetchall()
            conn.close()
            
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