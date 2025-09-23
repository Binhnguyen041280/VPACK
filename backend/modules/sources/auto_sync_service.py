import threading
import logging
import time
from datetime import datetime, timedelta
import json
from modules.db_utils.safe_connection import safe_db_connection
# Import PyDriveDownloader for sync status functions
from .pydrive_downloader import pydrive_downloader

logger = logging.getLogger(__name__)

class AutoSyncService:
    def __init__(self):
        self.sync_timers = {}  # Store timers for each source
        self.sync_locks = {}   # Locks to prevent concurrent syncs
        self.downloaders = {}  # Cache for different downloader types
        
    def _get_downloader_for_source(self, source_type: str):
        """Only create downloader when needed"""
        if source_type not in self.downloaders:
            if source_type == 'cloud':
                from modules.sources.cloud_manager import CloudManager
                self.downloaders[source_type] = CloudManager()
            elif source_type == 'local':
                # Local sources don't need special downloader
                self.downloaders[source_type] = None
        return self.downloaders.get(source_type)
        
    def start_auto_sync(self, source_config: dict) -> bool:
        """Start auto-sync for a source"""
        source_id = source_config.get('id')
        if not source_id:
            logger.error("Source ID required to start sync")
            return False
            
        if source_id in self.sync_timers:
            logger.warning(f"Sync already running for source {source_id}")
            return True
            
        # Initialize status if not exists
        current_status = pydrive_downloader.get_sync_status(source_id)
        if not current_status:
            pydrive_downloader.initialize_sync_status(source_id, sync_enabled=True, interval_minutes=10)
            
        self.sync_locks[source_id] = threading.Lock()
        self._schedule_next_sync(source_id)
        
        logger.info(f"Auto-sync started for source {source_id}")
        return True
        
    def stop_auto_sync(self, source_id: int) -> bool:
        """Stop auto-sync for a source"""
        try:
            if source_id not in self.sync_timers:
                logger.warning(f"No active sync for source {source_id}")
                return True
                
            # Cancel timer
            self.sync_timers[source_id].cancel()
            del self.sync_timers[source_id]
            del self.sync_locks[source_id]
            
            # Update status
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_status 
                    SET sync_enabled = 0, 
                        last_sync_status = 'stopped',
                        last_sync_message = 'Auto-sync stopped by user'
                    WHERE source_id = ?
                """, (source_id,))
            
            logger.info(f"Auto-sync stopped for source {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping sync for {source_id}: {e}")
            return False
            
    def get_sync_status(self, source_id: int) -> dict:
        """Get current sync status"""
        return pydrive_downloader.get_sync_status(source_id) or {}
        
    def _sync_latest_recordings(self, source_id: int) -> dict:
        """Perform sync of latest recordings"""
        with self.sync_locks.get(source_id, threading.Lock()):
            try:
                # Get source config and type
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT config, source_type FROM video_sources 
                        WHERE id = ?
                    """, (source_id,))
                    result = cursor.fetchone()
                
                if not result:
                    return {'success': False, 'message': 'Source not found'}
                    
                config = json.loads(result[0])
                source_type = result[1]
                
                # Update status to in_progress
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE sync_status 
                        SET last_sync_status = 'in_progress',
                            last_sync_message = 'Sync started'
                        WHERE source_id = ?
                    """, (source_id,))
                
                # Get appropriate downloader
                downloader = self._get_downloader_for_source(source_type)
                
                if not downloader:
                    return {'success': False, 'message': f'No downloader available for source type: {source_type}'}
                
                # Download last 24 hours
                time_range = {
                    'from': datetime.now() - timedelta(hours=24),
                    'to': datetime.now()
                }
                
                download_result = downloader.download_latest_recordings(config, time_range)
                
                # Update status
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE sync_status 
                        SET last_sync_timestamp = ?,
                            last_sync_status = ?,
                            last_sync_message = ?,
                            files_downloaded_count = files_downloaded_count + ?,
                            total_download_size_mb = total_download_size_mb + ?
                        WHERE source_id = ?
                    """, (
                        datetime.now().isoformat(),
                        'success' if download_result['success'] else 'failed',
                        download_result['message'],
                        download_result.get('files_downloaded', 0),
                        download_result.get('total_size_mb', 0.0),
                        source_id
                    ))
                
                return download_result
                
            except Exception as e:
                logger.error(f"Sync error for {source_id}: {e}")
                
                # Update error status
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE sync_status 
                        SET last_sync_status = 'failed',
                            last_sync_message = ?
                        WHERE source_id = ?
                    """, (str(e), source_id))
                
                return {'success': False, 'message': str(e)}
    
    def _schedule_next_sync(self, source_id: int):
        """Schedule next sync run"""
        status = self.get_sync_status(source_id)
        if not status.get('sync_enabled', True):
            return
            
        interval = status.get('sync_interval_minutes', 10)
        next_sync = datetime.now() + timedelta(minutes=interval)
        
        # Update next timestamp
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_status 
                SET next_sync_timestamp = ?
                WHERE source_id = ?
            """, (next_sync.isoformat(), source_id))
        
        # Schedule timer
        timer = threading.Timer(interval * 60, self._perform_sync, args=(source_id,))
        timer.daemon = True
        self.sync_timers[source_id] = timer
        timer.start()
        
        logger.info(f"Next sync scheduled for {source_id} at {next_sync}")
    
    def _perform_sync(self, source_id: int):
        """Perform sync and schedule next"""
        self._sync_latest_recordings(source_id)
        self._schedule_next_sync(source_id)