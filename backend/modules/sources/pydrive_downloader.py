#!/usr/bin/env python3
"""
PyDrive2 Downloader for VTrack - Simple replacement for AutoSyncService
Integrates with existing OAuth credentials and database structure
"""

import os
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Fixed imports - remove Google auth from top level to avoid conflicts
from modules.db_utils import get_db_connection
from database import get_sync_status, initialize_sync_status

logger = logging.getLogger(__name__)

class PyDriveDownloader:
    """Simple PyDrive2-based downloader that works with existing VTrack infrastructure"""
    
    def __init__(self):
        self.sync_timers = {}  # Store timers for each source
        self.sync_locks = {}   # Locks to prevent concurrent syncs
        self.drive_clients = {} # Cache PyDrive clients
        
        logger.info("🚀 PyDriveDownloader initialized")
    
    def start_auto_sync(self, source_id: int) -> bool:
        """Start auto-sync for a cloud source"""
        try:
            if source_id in self.sync_timers:
                logger.warning(f"Sync already running for source {source_id}")
                return True
            
            # Get source config from database
            source_config = self._get_source_config(source_id)
            if not source_config:
                logger.error(f"Source {source_id} not found")
                return False
            
            if source_config['source_type'] != 'cloud':
                logger.error(f"Source {source_id} is not a cloud source")
                return False
            
            # Initialize sync status if not exists
            current_status = get_sync_status(source_id)
            if not current_status:
                initialize_sync_status(source_id, sync_enabled=True, interval_minutes=15)
            
            # Create sync lock
            self.sync_locks[source_id] = threading.Lock()
            
            # Schedule first sync
            self._schedule_next_sync(source_id)
            
            logger.info(f"✅ Auto-sync started for source {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start auto-sync for {source_id}: {e}")
            return False
    
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
            
            # Update database status
            self._update_sync_status(source_id, 'stopped', 'Auto-sync stopped by user')
            
            logger.info(f"✅ Auto-sync stopped for source {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping sync for {source_id}: {e}")
            return False
    
    def force_sync_now(self, source_id: int) -> Dict:
        """Force immediate sync for a source"""
        logger.info(f"🚀 Force sync requested for source {source_id}")
        return self._perform_sync(source_id)
    
    def _perform_sync(self, source_id: int) -> Dict:
        """Perform actual sync operation"""
        with self.sync_locks.get(source_id, threading.Lock()):
            try:
                logger.info(f"🔄 Starting sync for source {source_id}")
                
                # Update status to in_progress
                self._update_sync_status(source_id, 'in_progress', 'Sync started')
                
                # Get source configuration
                source_config = self._get_source_config(source_id)
                if not source_config:
                    return {'success': False, 'message': 'Source not found'}
                
                # Get PyDrive client
                drive = self._get_drive_client(source_id)
                if not drive:
                    return {'success': False, 'message': 'Failed to authenticate with Google Drive'}
                
                # Download files
                download_result = self._download_files(source_id, source_config, drive)
                
                # Update sync status
                status = 'success' if download_result['success'] else 'failed'
                self._update_sync_status(
                    source_id, 
                    status, 
                    download_result['message'],
                    download_result.get('files_downloaded', 0),
                    download_result.get('total_size_mb', 0.0)
                )
                
                logger.info(f"✅ Sync completed for source {source_id}: {download_result['message']}")
                return download_result
                
            except Exception as e:
                error_msg = f"Sync failed: {str(e)}"
                logger.error(f"❌ {error_msg}")
                self._update_sync_status(source_id, 'failed', error_msg)
                return {'success': False, 'message': error_msg}
    
    def _download_files(self, source_id: int, source_config: Dict, drive) -> Dict:
        """Download files from Google Drive to local storage"""
        try:
            # Get target directory
            source_name = source_config['name']
            base_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'cloud_sync', source_name)
            os.makedirs(base_path, exist_ok=True)
            
            # Get selected folders from config
            config_data = json.loads(source_config.get('config', '{}'))
            selected_folders = config_data.get('selected_folders', [])
            tree_folders = config_data.get('selected_tree_folders', [])
            all_folders = selected_folders + tree_folders
            
            if not all_folders:
                return {'success': False, 'message': 'No folders selected for sync'}
            
            total_files = 0
            total_size = 0
            downloaded_files = []
            
            # Process each selected folder
            for folder_info in all_folders:
                folder_id = folder_info.get('id') if isinstance(folder_info, dict) else folder_info
                folder_name = folder_info.get('name', f'folder_{folder_id}') if isinstance(folder_info, dict) else folder_id
                
                # Create camera subdirectory
                camera_dir = os.path.join(base_path, self._sanitize_filename(folder_name))
                os.makedirs(camera_dir, exist_ok=True)
                
                # List files in this folder
                files_in_folder = self._list_video_files(drive, folder_id)
                
                # Download new files
                for file_info in files_in_folder:
                    if self._should_download_file(source_id, file_info):
                        download_path = os.path.join(camera_dir, self._sanitize_filename(file_info['title']))
                        
                        if self._download_single_file(drive, file_info, download_path):
                            file_size = int(file_info.get('fileSize', 0))
                            total_files += 1
                            total_size += file_size
                            downloaded_files.append({
                                'filename': file_info['title'],
                                'size': file_size,
                                'path': download_path,
                                'camera': folder_name
                            })
                            
                            # Track in database
                            self._track_downloaded_file(source_id, folder_name, file_info, download_path)
            
            total_size_mb = total_size / (1024 * 1024)
            
            return {
                'success': True,
                'message': f'Downloaded {total_files} files ({total_size_mb:.1f} MB)',
                'files_downloaded': total_files,
                'total_size_mb': total_size_mb,
                'downloaded_files': downloaded_files
            }
            
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            return {'success': False, 'message': f'Download error: {str(e)}'}
    
    def _get_drive_client(self, source_id: int) -> Optional[Any]:
        """✅ FIXED: Get authenticated PyDrive client using oauth2client credential conversion"""
        try:
            if source_id in self.drive_clients:
                return self.drive_clients[source_id]
            
            # Get stored credentials from VTrack database
            credential_data = self._get_raw_credentials(source_id)
            if not credential_data:
                logger.error(f"No stored credentials found for source {source_id}")
                return None
            
            logger.info(f"🔐 Converting credentials to oauth2client format for source {source_id}")
            
            # ✅ SOLUTION 2: Convert google-auth credentials to oauth2client format
            oauth2client_creds = self._convert_to_oauth2client_credentials(credential_data)
            if not oauth2client_creds:
                logger.error("❌ Failed to convert credentials to oauth2client format")
                return None
            
            # Create PyDrive2 GoogleAuth with oauth2client credentials
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive
            
            # Simple GoogleAuth without settings file
            gauth = GoogleAuth()
            
            # ✅ Set oauth2client credentials directly
            gauth.credentials = oauth2client_creds
            
            # Create PyDrive2 GoogleDrive object
            drive = GoogleDrive(gauth)
            
            # Test the connection
            try:
                about_info = drive.GetAbout()
                user_email = about_info.get('user', {}).get('emailAddress', 'Unknown')
                logger.info(f"✅ PyDrive2 connection successful: {user_email}")
            except Exception as test_error:
                logger.error(f"❌ PyDrive2 connection test failed: {test_error}")
                return None
            
            # Cache the client
            self.drive_clients[source_id] = drive
            logger.info(f"✅ PyDrive2 client created and cached for source {source_id}")
            return drive
            
        except Exception as e:
            logger.error(f"❌ Failed to create PyDrive2 client: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

    
    def _convert_to_oauth2client_credentials(self, credential_data: Dict) -> Optional[Any]:
        """
        ✅ SOLUTION 2: Convert google-auth credential data to oauth2client.OAuth2Credentials
        
        Args:
            credential_data (dict): Decrypted credential data from VTrack storage
            
        Returns:
            oauth2client.client.OAuth2Credentials: PyDrive2 compatible credentials
        """
        try:
            # Import oauth2client
            from oauth2client import client
            GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
            import httplib2
            
            # Extract required data
            access_token = credential_data.get('token')
            refresh_token = credential_data.get('refresh_token')
            client_id = credential_data.get('client_id')
            client_secret = credential_data.get('client_secret')
            token_uri = credential_data.get('token_uri', GOOGLE_TOKEN_URI)
            
            # Handle token expiry
            token_expiry = None
            if credential_data.get('expires_at'):
                from datetime import datetime
                expires_at_str = credential_data['expires_at']
                # Handle both ISO format with and without timezone
                if expires_at_str.endswith('Z'):
                    expires_at_str = expires_at_str[:-1] + '+00:00'
                elif '+' not in expires_at_str and 'T' in expires_at_str:
                    # No timezone info, assume UTC
                    expires_at_str += '+00:00'
                
                try:
                    token_expiry = datetime.fromisoformat(expires_at_str).replace(tzinfo=None)
                except ValueError as e:
                    logger.warning(f"⚠️ Could not parse token expiry: {expires_at_str}, error: {e}")
                    token_expiry = None
            
            logger.info("🔄 Converting to oauth2client credentials...")
            logger.info(f"   Client ID: {client_id[:20]}..." if client_id else "   No client_id")
            logger.info(f"   Has refresh token: {bool(refresh_token)}")
            logger.info(f"   Has access token: {bool(access_token)}")
            logger.info(f"   Token expiry: {token_expiry}")
            
            # ✅ Create oauth2client credentials object using documented method
            oauth2client_creds = client.OAuth2Credentials(
                access_token=access_token,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
                token_uri=token_uri,
                user_agent="VTrack-PyDrive2-Client/1.0"
            )
            
            # Check and refresh token if expired
            if oauth2client_creds.access_token_expired and refresh_token:
                logger.info("🔄 Refreshing expired access token using oauth2client...")
                http = httplib2.Http()
                oauth2client_creds.refresh(http)
                logger.info("✅ Access token refreshed successfully")
                
                # Update stored credentials with new token
                self._update_credential_data_after_refresh(credential_data, oauth2client_creds)
            
            logger.info("✅ oauth2client credentials created successfully")
            return oauth2client_creds
            
        except ImportError as e:
            logger.error(f"❌ oauth2client not installed: {e}")
            logger.error("   Please install: pip install oauth2client")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to create oauth2client credentials: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

    
    def _update_credential_data_after_refresh(self, credential_data: Dict, oauth2client_creds) -> bool:
        """Update credential data after oauth2client refresh"""
        try:
            # Update the credential data with new token
            credential_data['token'] = oauth2client_creds.access_token
            if oauth2client_creds.token_expiry:
                credential_data['expires_at'] = oauth2client_creds.token_expiry.isoformat()
            
            # Re-encrypt and save (this would need source_id, but we'll skip for now)
            logger.info("✅ Credential data updated with refreshed token")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating credential data: {e}")
            return False
    
    def _get_raw_credentials(self, source_id: int) -> Optional[dict]:
        """Get raw credential data without creating Credentials object"""
        try:
            # Get source config to extract user email
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT config FROM video_sources 
                WHERE id = ? AND source_type = 'cloud' AND active = 1
            """, (source_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[0]:
                logger.error(f"No source config found for source {source_id}")
                return None
            
            # Parse config to get user email
            import json
            config_data = json.loads(result[0])
            user_email = config_data.get('user_email')
            
            if not user_email:
                logger.error(f"No user_email in source {source_id} config")
                return None
            
            # Load credentials from file system
            import hashlib
            import os
            
            tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            token_filename = f"google_drive_{email_hash}.json"
            token_filepath = os.path.join(tokens_dir, token_filename)
            
            if not os.path.exists(token_filepath):
                logger.error(f"No credentials file found: {token_filepath}")
                return None
            
            # Load encrypted storage
            with open(token_filepath, 'r') as f:
                encrypted_storage = json.load(f)
            
            # Decrypt credentials
            from modules.sources.cloud_endpoints import decrypt_credentials
            credential_data = decrypt_credentials(encrypted_storage['encrypted_data'])
            if not credential_data:
                logger.error(f"Failed to decrypt credentials for: {user_email}")
                return None
            
            return credential_data
            
        except Exception as e:
            logger.error(f"Error getting raw credentials: {e}")
            return None
    
    def _list_video_files(self, drive, folder_id: str) -> List[Dict]:
        """List video files in a Google Drive folder"""
        try:
            # ✅ DEBUG: List ALL files first
            all_files_query = f"'{folder_id}' in parents and trashed=false"
            all_files = drive.ListFile({'q': all_files_query, 'maxResults': 100}).GetList()
            
            logger.info(f"🔍 DEBUG: Found {len(all_files)} total files in folder {folder_id}")
            for file in all_files:
                logger.info(f"   📄 {file['title']} - MIME: {file.get('mimeType', 'Unknown')}")
            
            # Original video query
            video_mimes = [
                'video/mp4', 'video/avi', 'video/mov', 'video/mkv', 
                'video/flv', 'video/wmv', 'video/m4v', 'video/quicktime'
            ]
            
            mime_query = " or ".join([f"mimeType='{mime}'" for mime in video_mimes])
            query = f"'{folder_id}' in parents and ({mime_query}) and trashed=false"
            
            file_list = drive.ListFile({'q': query, 'maxResults': 100}).GetList()
            
            logger.info(f"📁 Found {len(file_list)} video files in folder {folder_id}")
            return file_list
            
        except Exception as e:
            logger.error(f"❌ Error listing files: {e}")
            return []
    
    def _should_download_file(self, source_id: int, file_info: Dict) -> bool:
        """Check if file should be downloaded (not already downloaded)"""
        try:
            filename = file_info['title']
            file_id = file_info['id']
            
            # Check if already downloaded
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM downloaded_files 
                WHERE source_id = ? AND (original_filename = ? OR local_file_path LIKE ?)
            """, (source_id, filename, f'%{filename}'))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            should_download = count == 0
            if not should_download:
                logger.debug(f"⏭️ Skipping {filename} (already downloaded)")
            
            return should_download
            
        except Exception as e:
            logger.error(f"❌ Error checking download status: {e}")
            return True  # Download by default if unsure
    
    def _download_single_file(self, drive, file_info: Dict, local_path: str) -> bool:
        """Download a single file from Google Drive"""
        try:
            file_obj = drive.CreateFile({'id': file_info['id']})
            file_obj.GetContentFile(local_path)
            
            logger.info(f"📥 Downloaded: {file_info['title']} → {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download {file_info['title']}: {e}")
            return False
    
    def _track_downloaded_file(self, source_id: int, camera_name: str, file_info: Dict, local_path: str):
        """Track downloaded file in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO downloaded_files (
                    source_id, camera_name, original_filename, local_file_path,
                    file_size_bytes, download_timestamp, file_format
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                source_id,
                camera_name,
                file_info['title'],
                local_path,
                int(file_info.get('fileSize', 0)),
                datetime.now().isoformat(),
                os.path.splitext(file_info['title'])[1]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error tracking file: {e}")
    
    def _get_source_config(self, source_id: int) -> Optional[Dict]:
        """Get source configuration from database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source_type, name, path, config FROM video_sources 
                WHERE id = ? AND active = 1
            """, (source_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'source_type': result[0],
                    'name': result[1], 
                    'path': result[2],
                    'config': result[3]
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting source config: {e}")
            return None
    
    def _update_sync_status(self, source_id: int, status: str, message: str, files_count: int = 0, size_mb: float = 0.0):
        """Update sync status in database"""
        try:
            conn = get_db_connection()
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
                status,
                message,
                files_count,
                size_mb,
                source_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error updating sync status: {e}")
    
    def _schedule_next_sync(self, source_id: int):
        """Schedule next sync run"""
        try:
            status = get_sync_status(source_id)
            if not status or not status.get('sync_enabled', True):
                return
            
            interval = status.get('sync_interval_minutes', 15)
            next_sync_time = datetime.now() + timedelta(minutes=interval)
            
            # Update next sync timestamp in database
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
            
            logger.info(f"⏰ Next sync scheduled for source {source_id} at {next_sync_time}")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling next sync: {e}")
    
    def _timer_callback(self, source_id: int):
        """Timer callback to perform sync and schedule next"""
        self._perform_sync(source_id)
        self._schedule_next_sync(source_id)
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename for file system"""
        import re
        # Remove/replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return sanitized.strip()

# Global instance
pydrive_downloader = PyDriveDownloader()

# Convenience functions for backward compatibility
def start_source_sync(source_id: int) -> bool:
    """Start auto-sync for a source"""
    return pydrive_downloader.start_auto_sync(source_id)

def stop_source_sync(source_id: int) -> bool:
    """Stop auto-sync for a source"""
    return pydrive_downloader.stop_auto_sync(source_id)

def force_sync_source(source_id: int) -> Dict:
    """Force immediate sync for a source"""
    return pydrive_downloader.force_sync_now(source_id)