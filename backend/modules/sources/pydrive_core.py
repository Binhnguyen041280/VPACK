#!/usr/bin/env python3
"""
PyDriveCore - Pure Business Logic for VTrack
Phase 1: Clean separation of core download functionality
No error handling, no retry logic - just clean business operations
"""

import os
from pathlib import Path
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)

class PyDriveCore:
    """
    Core business logic for PyDrive operations
    Pure functionality without error handling complexity
    """
    
    def __init__(self):
        self.drive_clients = {}  # Cache authenticated clients
        logger.info("🔧 PyDriveCore initialized - Pure business logic")
    
    # ==================== AUTHENTICATION ====================
    
    def get_drive_client(self, source_id: int) -> Optional[Any]:
        """Get authenticated PyDrive client - với auto-refresh token"""
        # Return cached client if available và valid
        if source_id in self.drive_clients:
            client = self.drive_clients[source_id]
            if self._is_client_valid(client):
                return client
            else:
                # Client expired, remove from cache
                del self.drive_clients[source_id]
        
        # Get credentials and create client
        credential_data = self._load_credentials(source_id)
        if not credential_data:
            logger.error(f"❌ No credentials found for source {source_id}")
            return None
        
        # Convert to oauth2client format với refresh token
        oauth2client_creds = self._create_oauth2client_credentials(credential_data)
        if not oauth2client_creds:
            logger.error(f"❌ Failed to create oauth2client credentials for source {source_id}")
            return None
        
        # Create PyDrive client
        drive_client = self._create_pydrive_client(oauth2client_creds)
        if drive_client:
            # Cache and return
            self.drive_clients[source_id] = drive_client
            logger.info(f"✅ Drive client created and cached for source {source_id}")
        
        return drive_client
    
    def _is_client_valid(self, client) -> bool:
        """Check if Drive client is still valid"""
        try:
            # Test với simple API call
            client.GetAbout()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Client validation failed: {e}")
            return False
    
    def _load_credentials(self, source_id: int) -> Optional[dict]:
        """Load credential data from storage - ENHANCED"""
        try:
            # Get source config to extract user email
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT config FROM video_sources 
                    WHERE id = ? AND source_type = 'cloud' AND active = 1
                """, (source_id,))
                result = cursor.fetchone()
            
            if not result or not result[0]:
                logger.error(f"❌ No source config found for ID {source_id}")
                return None
            
            # Parse config to get user email
            config_data = json.loads(result[0])
            user_email = config_data.get('user_email')
            if not user_email:
                logger.error(f"❌ No user_email in config for source {source_id}")
                return None
            
            # Load from encrypted file
            tokens_dir = str(Path(__file__).parent / 'tokens')
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            token_filename = f"google_drive_{email_hash}.json"
            token_filepath = str(Path(tokens_dir) / token_filename)
            
            if not Path(token_filepath).exists():
                logger.error(f"❌ Token file not found: {token_filepath}")
                return None
            
            # Load and decrypt
            with open(token_filepath, 'r') as f:
                encrypted_storage = json.load(f)
            
            from modules.sources.cloud_endpoints import decrypt_credentials
            credential_data = decrypt_credentials(encrypted_storage['encrypted_data'])
            
            if not credential_data:
                logger.error(f"❌ Failed to decrypt credentials for source {source_id}")
                return None
                
            logger.info(f"✅ Credentials loaded for {user_email}")
            return credential_data
            
        except Exception as e:
            logger.error(f"❌ Error loading credentials: {e}")
            return None
    
    def _create_oauth2client_credentials(self, credential_data: Dict) -> Optional[Any]:
        """Convert to oauth2client credentials - ENHANCED với auto-refresh"""
        try:
            from oauth2client import client
            import httplib2
            
            # Extract data
            access_token = credential_data.get('token')
            refresh_token = credential_data.get('refresh_token')
            client_id = credential_data.get('client_id')
            client_secret = credential_data.get('client_secret')
            token_uri = credential_data.get('token_uri', "https://oauth2.googleapis.com/token")
            
            # Validate required fields
            if not all([refresh_token, client_id, client_secret]):
                logger.error("❌ Missing required credential fields")
                return None
            
            # Handle token expiry - FIXED parsing
            token_expiry = None
            if credential_data.get('expires_at'):
                expires_at_str = credential_data['expires_at']
                try:
                    # Try multiple formats
                    if expires_at_str.endswith('Z'):
                        expires_at_str = expires_at_str[:-1] + '+00:00'
                    
                    # Parse ISO format
                    if 'T' in expires_at_str:
                        if '+' not in expires_at_str and '-' not in expires_at_str[-6:]:
                            expires_at_str += '+00:00'
                        token_expiry = datetime.fromisoformat(expires_at_str).replace(tzinfo=None)
                    else:
                        # Try timestamp format
                        token_expiry = datetime.fromtimestamp(float(expires_at_str))
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Could not parse expiry time: {e}")
                    # Set as expired to force refresh
                    token_expiry = datetime.now() - timedelta(hours=1)
            
            # Create credentials
            oauth2client_creds = client.OAuth2Credentials(
                access_token=access_token,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
                token_uri=token_uri,
                user_agent="VTrack-PyDrive2-Client/1.0"
            )
            
            # Auto-refresh if expired
            if oauth2client_creds.access_token_expired:
                logger.info("🔄 Token expired, refreshing...")
                try:
                    http = httplib2.Http(timeout=30)
                    oauth2client_creds.refresh(http)
                    logger.info("✅ Token refreshed successfully")
                    
                    # Save updated token
                    self._update_saved_token(credential_data, oauth2client_creds)
                    
                except Exception as refresh_error:
                    logger.error(f"❌ Token refresh failed: {refresh_error}")
                    return None
            
            return oauth2client_creds
            
        except Exception as e:
            logger.error(f"❌ Failed to create oauth2client credentials: {e}")
            return None
    
    def _update_saved_token(self, original_data: Dict, new_creds):
        """Update saved token after refresh"""
        try:
            # Update credential data
            original_data['token'] = new_creds.access_token
            if new_creds.token_expiry:
                original_data['expires_at'] = new_creds.token_expiry.isoformat()
            
            # Get email for file path
            user_email = original_data.get('user_info', {}).get('email')
            if not user_email:
                return
            
            # Encrypt and save
            from modules.sources.cloud_endpoints import encrypt_credentials
            encrypted_data = encrypt_credentials(original_data)
            
            if encrypted_data:
                tokens_dir = str(Path(__file__).parent / 'tokens')
                email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
                token_filepath = str(Path(tokens_dir) / f"google_drive_{email_hash}.json")
                
                storage_data = {
                    'encrypted_data': encrypted_data,
                    'user_email': user_email,
                    'updated_at': datetime.now().isoformat(),
                    'encryption_version': '1.0'
                }
                
                with open(token_filepath, 'w') as f:
                    json.dump(storage_data, f, indent=2)
                
                logger.info(f"✅ Updated token saved for {user_email}")
                
        except Exception as e:
            logger.error(f"❌ Failed to save updated token: {e}")
    
    def _create_pydrive_client(self, oauth2client_creds) -> Optional[Any]:
        """Create PyDrive client from credentials with timeout configuration"""
        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive
            
            # Create GoogleAuth với settings
            gauth = GoogleAuth()
            
            # Configure settings để tránh tìm client_secrets.json
            gauth.settings = {
                'client_config_backend': 'service',
                'client_config': {
                    'client_id': oauth2client_creds.client_id,
                    'client_secret': oauth2client_creds.client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uri': 'http://localhost:8080/api/cloud/oauth/callback'
                },
                'save_credentials': False,
                'save_credentials_backend': 'file',
                'save_credentials_file': None,
                'get_refresh_token': True,
                'oauth_scope': [
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/drive.metadata.readonly'
                ]
            }
            
            # Set credentials trực tiếp
            gauth.credentials = oauth2client_creds
            
            # Configure timeout - 3 minutes
            gauth.http_timeout = 180
            
            # Create Drive instance
            drive = GoogleDrive(gauth)
            
            # Test connection
            about = drive.GetAbout()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            logger.info(f"✅ PyDrive2 connection successful: {user_email}")
            
            return drive
            
        except Exception as e:
            logger.error(f"❌ Failed to create PyDrive client: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ==================== FILE OPERATIONS ====================
    
    def list_folder_files(self, drive, folder_id: str, recursive: bool = True,
                          max_depth: int = 3, current_depth: int = 0,
                          relative_path: str = "") -> List[Dict]:
        """
        List video files in a Google Drive folder with recursive scanning.

        Args:
            drive: PyDrive client
            folder_id: Google Drive folder ID
            recursive: Enable recursive folder scanning (default: True)
            max_depth: Maximum depth for recursive scan (default: 3)
            current_depth: Current recursion depth (internal use)
            relative_path: Relative path from root folder (internal use)

        Returns:
            List of file info dicts with 'relative_path' and 'drive_file_id' keys
        """
        try:
            video_mime_types = [
                'video/mp4', 'video/avi', 'video/mov', 'video/mkv',
                'video/flv', 'video/wmv', 'video/m4v', 'video/quicktime'
            ]

            all_files = []

            # List video files in current folder
            mime_conditions = ' or '.join([f"mimeType='{mime}'" for mime in video_mime_types])
            query = f"'{folder_id}' in parents and ({mime_conditions}) and trashed=false"

            files = drive.ListFile({
                'q': query,
                'maxResults': 100,
                'supportsAllDrives': True,
                'includeItemsFromAllDrives': True
            }).GetList()

            # Add metadata to each file
            for file in files:
                file['relative_path'] = relative_path
                file['drive_file_id'] = file['id']  # Ensure drive_file_id is set

            all_files.extend(files)
            logger.info(f"📁 Found {len(files)} video files in folder (depth {current_depth})")

            # If recursive enabled and within depth limit, scan subfolders
            if recursive and current_depth < max_depth:
                folder_query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

                subfolders = drive.ListFile({
                    'q': folder_query,
                    'supportsAllDrives': True,
                    'includeItemsFromAllDrives': True
                }).GetList()

                logger.info(f"📂 Found {len(subfolders)} subfolders (depth {current_depth})")

                for subfolder in subfolders:
                    subfolder_name = subfolder['title']
                    subfolder_id = subfolder['id']

                    # Build relative path
                    new_relative_path = str(Path(relative_path) / subfolder_name) if relative_path else subfolder_name

                    logger.info(f"🔍 Scanning subfolder: {new_relative_path}")

                    # Recursive call
                    subfolder_files = self.list_folder_files(
                        drive=drive,
                        folder_id=subfolder_id,
                        recursive=True,
                        max_depth=max_depth,
                        current_depth=current_depth + 1,
                        relative_path=new_relative_path
                    )

                    all_files.extend(subfolder_files)

            return all_files

        except Exception as e:
            logger.error(f"❌ Error listing files: {e}")
            return []
    
    def download_single_file(self, drive, file_info: Dict, local_path: str) -> bool:
        """Download a single file - simple version"""
        try:
            file_name = file_info['title']
            file_size_mb = int(file_info.get('fileSize', 0)) / (1024 * 1024)
            
            logger.info(f"⬇️ Downloading: {file_name} ({file_size_mb:.1f}MB)")
            
            file_obj = drive.CreateFile({'id': file_info['id']})
            file_obj.GetContentFile(local_path)
            
            logger.info(f"✅ Downloaded: {file_name} - Success")
            return True
            
        except Exception as e:
            logger.error(f"❌ Download failed for {file_info.get('title')}: {e}")
            return False
    
    def check_file_exists_locally(self, source_id: int, drive_file_id: str, filename: str = None) -> bool:
        """
        Check if file already downloaded using unique drive_file_id.
        Falls back to filename check if drive_file_id not available.

        Args:
            source_id: Video source ID
            drive_file_id: Unique Google Drive file ID (preferred)
            filename: Filename as fallback

        Returns:
            True if file exists, False otherwise
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Primary check: by drive_file_id (most reliable)
                if drive_file_id:
                    cursor.execute("""
                        SELECT COUNT(*) FROM downloaded_files
                        WHERE source_id = ? AND drive_file_id = ?
                    """, (source_id, drive_file_id))

                    count = cursor.fetchone()[0]
                    if count > 0:
                        return True

                # Fallback check: by filename (for backward compatibility)
                if filename:
                    cursor.execute("""
                        SELECT COUNT(*) FROM downloaded_files
                        WHERE source_id = ? AND original_filename = ?
                    """, (source_id, filename))

                    count = cursor.fetchone()[0]
                    return count > 0

                return False

        except Exception as e:
            logger.error(f"❌ Error checking file existence: {e}")
            return False
    
    def track_downloaded_file(self, source_id: int, camera_name: str, file_info: Dict, local_path: str):
        """Track downloaded file in database with recursive folder support"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Extract metadata from file_info
                drive_file_id = file_info.get('drive_file_id') or file_info.get('id')
                relative_path = file_info.get('relative_path', '')

                cursor.execute("""
                    INSERT INTO downloaded_files (
                        source_id, camera_name, original_filename, local_file_path,
                        file_size_bytes, download_timestamp, file_format,
                        drive_file_id, relative_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_id,
                    camera_name,
                    file_info['title'],
                    local_path,
                    int(file_info.get('fileSize', 0)),
                    datetime.now().isoformat(),
                    Path(file_info['title']).suffix,
                    drive_file_id,
                    relative_path
                ))

                logger.debug(f"📝 Tracked: {file_info['title']} (path: {relative_path})")

        except Exception as e:
            logger.error(f"❌ Error tracking downloaded file: {e}")
    
    # ==================== SYNC OPERATIONS ====================
    
    def sync_folder(self, drive, folder_info: Dict, base_path: str, source_id: int) -> Dict:
        """Sync a single folder - simple version"""
        try:
            # Enhanced type validation for folder_id
            if isinstance(folder_info, dict):
                folder_id = folder_info.get('id')
            else:
                folder_id = folder_info
            
            # Validate folder_id is valid string
            if not folder_id or not isinstance(folder_id, str):
                return {'success': False, 'message': f'Invalid folder_id: {folder_id}'}
            
            folder_name = folder_info.get('name', f'folder_{folder_id}') if isinstance(folder_info, dict) else f'folder_{folder_id}'
            
            logger.info(f"📂 SYNC [{source_id}] Starting folder: {folder_name}")
            
            # Get files with recursive scanning enabled
            files = self.list_folder_files(drive, folder_id, recursive=True, max_depth=3)

            logger.info(f"📦 Total files found (including subfolders): {len(files)}")

            if not files:
                logger.info(f"📂 No video files in folder: {folder_name}")
                return {'success': True, 'files_downloaded': 0, 'total_size': 0}

            # Create folder path
            folder_path = str(Path(base_path) / self._sanitize_filename(folder_name))
            os.makedirs(folder_path, exist_ok=True)

            # Download new files
            downloaded_count = 0
            total_size = 0

            for file_info in files:
                filename = file_info['title']
                drive_file_id = file_info.get('drive_file_id') or file_info.get('id')
                relative_path = file_info.get('relative_path', '')

                # Skip if already downloaded (check by drive_file_id)
                if self.check_file_exists_locally(source_id, drive_file_id, filename):
                    logger.debug(f"⏭️ Skipping {filename} (already downloaded)")
                    continue

                # Build full path preserving folder structure
                if relative_path:
                    # Nested file: folder_path/relative_path/filename
                    file_dir = str(Path(folder_path) / relative_path)
                    os.makedirs(file_dir, exist_ok=True)
                    file_path = str(Path(file_dir) / self._sanitize_filename(filename))
                    logger.info(f"📥 Downloading to nested path: {relative_path}/{filename}")
                else:
                    # Root level file: folder_path/filename
                    file_path = str(Path(folder_path) / self._sanitize_filename(filename))
                    logger.info(f"📥 Downloading to root: {filename}")

                # Download file
                if self.download_single_file(drive, file_info, file_path):
                    file_size = int(file_info.get('fileSize', 0))
                    downloaded_count += 1
                    total_size += file_size

                    # Track in database with nested path info
                    self.track_downloaded_file(source_id, folder_name, file_info, file_path)
            
            logger.info(f"✅ SYNC [{source_id}] Folder completed: {downloaded_count} files, {total_size/1024/1024:.1f}MB")
            
            return {
                'success': True,
                'files_downloaded': downloaded_count,
                'total_size': total_size,
                'folder_name': folder_name
            }
            
        except Exception as e:
            logger.error(f"❌ Error syncing folder: {e}")
            return {'success': False, 'message': str(e)}
    
    def sync_source(self, source_id: int) -> Dict:
        """Sync entire source - simple version"""
        try:
            logger.info(f"🚀 Starting sync for source {source_id}")

            # Get source configuration
            source_config = self._get_source_config(source_id)
            if not source_config:
                return {'success': False, 'message': f'Source {source_id} not found'}

            # Get Drive client
            drive = self.get_drive_client(source_id)
            if not drive:
                return {'success': False, 'message': 'Failed to get Drive client - check authentication'}

            # Get cloud staging directory (auto-managed by application)
            from modules.path_utils import get_cloud_staging_path
            source_name = source_config['name']
            base_path = get_cloud_staging_path(source_name)
            logger.info(f"📁 Using cloud staging path: {base_path}")
            
            # Get selected folders from config
            config_data = json.loads(source_config.get('config', '{}'))
            selected_folders = config_data.get('selected_folders', [])
            tree_folders = config_data.get('selected_tree_folders', [])
            all_folders = selected_folders + tree_folders
            
            if not all_folders:
                return {'success': False, 'message': 'No folders selected for sync'}
            
            # Sync each folder
            total_files = 0
            total_size = 0
            synced_folders = []
            failed_folders = []
            
            for folder_info in all_folders:
                folder_result = self.sync_folder(drive, folder_info, base_path, source_id)
                
                if folder_result.get('success'):
                    total_files += folder_result.get('files_downloaded', 0)
                    total_size += folder_result.get('total_size', 0)
                    folder_name = folder_result.get('folder_name', 'unknown')
                    if folder_result.get('files_downloaded', 0) > 0:
                        synced_folders.append(folder_name)
                else:
                    failed_folders.append(folder_info.get('name', 'unknown') if isinstance(folder_info, dict) else str(folder_info))
            
            total_size_mb = total_size / (1024 * 1024) if total_size > 0 else 0

            # Build result message
            if total_files > 0:
                message = f'Downloaded {total_files} files ({total_size_mb:.1f} MB)'
            elif failed_folders:
                message = f'Sync failed for folders: {", ".join(failed_folders)}'
            else:
                message = 'No new files to download'

            # PHASE 3: Files ready for batch_scheduler processing
            if total_files > 0:
                logger.info(f"📥 {total_files} files downloaded to {base_path}")
                logger.info(f"⏳ Files will be scanned by batch_scheduler within 60s")

            logger.info(f"🎯 SYNC [{source_id}] COMPLETED: {message}")

            return {
                'success': True if not failed_folders else False,
                'message': message,
                'files_downloaded': total_files,
                'total_size_mb': total_size_mb,
                'synced_folders': synced_folders,
                'failed_folders': failed_folders
            }
            
        except Exception as e:
            logger.error(f"❌ Sync failed for source {source_id}: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    def mark_file_processed(self, local_file_path: str, success: bool = True) -> bool:
        """
        Mark downloaded file as processed after video analysis completes.
        Enables automatic cleanup of old processed files.

        Args:
            local_file_path: Full path to processed video file
            success: Whether processing was successful

        Returns:
            True if marked successfully, False otherwise
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE downloaded_files
                    SET is_processed = 1,
                        processing_timestamp = ?,
                        processing_status = ?
                    WHERE local_file_path = ?
                """, (
                    datetime.now().isoformat(),
                    'success' if success else 'failed',
                    local_file_path
                ))

                if cursor.rowcount > 0:
                    logger.info(f"✅ Marked as processed: {Path(local_file_path).name}")
                    return True
                else:
                    logger.warning(f"⚠️ File not found in database: {local_file_path}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error marking file as processed: {e}")
            return False

    # ==================== HELPER METHODS ====================

    def _get_source_config(self, source_id: int) -> Optional[Dict]:
        """Get source configuration from database"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT source_type, name, path, config FROM video_sources 
                    WHERE id = ? AND active = 1
                """, (source_id,))
                result = cursor.fetchone()
                
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
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename for file system"""
        import re
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return sanitized.strip()