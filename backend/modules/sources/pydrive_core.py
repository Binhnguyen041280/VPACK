#!/usr/bin/env python3
"""
PyDriveCore - Pure Business Logic for VTrack
Phase 1: Clean separation of core download functionality
No error handling, no retry logic - just clean business operations
"""

import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

from modules.db_utils import get_db_connection

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
        """Get authenticated PyDrive client - simple version"""
        # Return cached client if available
        if source_id in self.drive_clients:
            return self.drive_clients[source_id]
        
        # Get credentials and create client
        credential_data = self._load_credentials(source_id)
        if not credential_data:
            return None
        
        # Convert to oauth2client format
        oauth2client_creds = self._create_oauth2client_credentials(credential_data)
        if not oauth2client_creds:
            return None
        
        # Create PyDrive client
        drive_client = self._create_pydrive_client(oauth2client_creds)
        if drive_client:
            # Cache and return
            self.drive_clients[source_id] = drive_client
            logger.info(f"✅ Drive client created and cached for source {source_id}")
        
        return drive_client
    
    def _load_credentials(self, source_id: int) -> Optional[dict]:
        """Load credential data from storage"""
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
            return None
        
        # Parse config to get user email
        config_data = json.loads(result[0])
        user_email = config_data.get('user_email')
        if not user_email:
            return None
        
        # Load from encrypted file
        tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        token_filename = f"google_drive_{email_hash}.json"
        token_filepath = os.path.join(tokens_dir, token_filename)
        
        if not os.path.exists(token_filepath):
            return None
        
        # Load and decrypt
        with open(token_filepath, 'r') as f:
            encrypted_storage = json.load(f)
        
        from modules.sources.cloud_endpoints import decrypt_credentials
        credential_data = decrypt_credentials(encrypted_storage['encrypted_data'])
        return credential_data
    
    def _create_oauth2client_credentials(self, credential_data: Dict) -> Optional[Any]:
        """Convert to oauth2client credentials - simple version"""
        try:
            from oauth2client import client
            import httplib2
            
            # Extract data
            access_token = credential_data.get('token')
            refresh_token = credential_data.get('refresh_token')
            client_id = credential_data.get('client_id')
            client_secret = credential_data.get('client_secret')
            token_uri = credential_data.get('token_uri', "https://oauth2.googleapis.com/token")
            
            # Handle token expiry
            token_expiry = None
            if credential_data.get('expires_at'):
                from datetime import datetime
                expires_at_str = credential_data['expires_at']
                if expires_at_str.endswith('Z'):
                    expires_at_str = expires_at_str[:-1] + '+00:00'
                elif '+' not in expires_at_str and 'T' in expires_at_str:
                    expires_at_str += '+00:00'
                
                try:
                    token_expiry = datetime.fromisoformat(expires_at_str).replace(tzinfo=None)
                except ValueError:
                    token_expiry = None
            
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
            
            # Refresh if expired
            if oauth2client_creds.access_token_expired and refresh_token:
                http = httplib2.Http()
                oauth2client_creds.refresh(http)
                logger.info("🔄 Token refreshed successfully")
            
            return oauth2client_creds
            
        except Exception as e:
            logger.error(f"❌ Failed to create oauth2client credentials: {e}")
            return None
    
    def _create_pydrive_client(self, oauth2client_creds) -> Optional[Any]:
        """Create PyDrive client from credentials with timeout configuration"""
        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive
            
            gauth = GoogleAuth()
            gauth.credentials = oauth2client_creds
            
            # ✅ FIX: Configure timeout - 3 minutes (industry standard)
            # Set http_timeout for network resilience - prevents 5-minute infrastructure timeout
            gauth.http_timeout = 180  # 3 minutes
            
            drive = GoogleDrive(gauth)
            
            # Test connection
            about = drive.GetAbout()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            logger.info(f"✅ PyDrive2 connection successful with 3-minute timeout: {user_email}")
            
            return drive
            
        except Exception as e:
            logger.error(f"❌ Failed to create PyDrive client: {e}")
            return None
    
    # ==================== FILE OPERATIONS ====================
    
    def list_folder_files(self, drive, folder_id: str) -> List[Dict]:
        """List video files in a Google Drive folder - simple version"""
        video_mime_types = [
            'video/mp4', 'video/avi', 'video/mov', 'video/mkv',
            'video/flv', 'video/wmv', 'video/m4v', 'video/quicktime'
        ]
        
        mime_conditions = ' or '.join([f"mimeType='{mime}'" for mime in video_mime_types])
        query = f"'{folder_id}' in parents and ({mime_conditions}) and trashed=false"
        
        files = drive.ListFile({
            'q': query,
            'maxResults': 100,
            'supportsAllDrives': True,
            'includeItemsFromAllDrives': True
        }).GetList()
        
        logger.info(f"📁 Found {len(files)} video files in folder {folder_id}")
        return files
    
    def download_single_file(self, drive, file_info: Dict, local_path: str) -> bool:
        """Download a single file - simple version"""
        file_name = file_info['title']
        file_size_mb = int(file_info.get('fileSize', 0)) / (1024 * 1024)
        
        logger.info(f"⬇️ Downloading: {file_name} ({file_size_mb:.1f}MB)")
        
        file_obj = drive.CreateFile({'id': file_info['id']})
        file_obj.GetContentFile(local_path)
        
        logger.info(f"✅ Downloaded: {file_name} - Success")
        return True
    
    def check_file_exists_locally(self, source_id: int, filename: str) -> bool:
        """Check if file already downloaded"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM downloaded_files 
            WHERE source_id = ? AND (original_filename = ? OR local_file_path LIKE ?)
        """, (source_id, filename, f'%{filename}'))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def track_downloaded_file(self, source_id: int, camera_name: str, file_info: Dict, local_path: str):
        """Track downloaded file in database"""
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
    
    # ==================== SYNC OPERATIONS ====================
    
    def sync_folder(self, drive, folder_info: Dict, base_path: str, source_id: int) -> Dict:
        """Sync a single folder - simple version"""
        # Enhanced type validation for folder_id
        if isinstance(folder_info, dict):
            folder_id = folder_info.get('id')
        else:
            folder_id = folder_info
        
        # Validate folder_id is valid string
        if not folder_id or not isinstance(folder_id, str):
            return {'success': False, 'message': f'Invalid folder_id: {folder_id}'}
        
        folder_name = folder_info.get('name', f'folder_{folder_id}') if isinstance(folder_info, dict) else f'folder_{folder_id}'
        
        logger.info(f"🔄 SYNC [{source_id}] Starting folder: {folder_name}")
        
        # Get files in folder
        files = self.list_folder_files(drive, folder_id)
        if not files:
            return {'success': True, 'files_downloaded': 0, 'total_size': 0}
        
        # Create folder path
        folder_path = os.path.join(base_path, self._sanitize_filename(folder_name))
        os.makedirs(folder_path, exist_ok=True)
        
        # Download new files
        downloaded_count = 0
        total_size = 0
        
        for file_info in files:
            filename = file_info['title']
            
            # Skip if already downloaded
            if self.check_file_exists_locally(source_id, filename):
                logger.debug(f"⏭️ Skipping {filename} (already downloaded)")
                continue
            
            # Download file
            file_path = os.path.join(folder_path, self._sanitize_filename(filename))
            
            if self.download_single_file(drive, file_info, file_path):
                file_size = int(file_info.get('fileSize', 0))
                downloaded_count += 1
                total_size += file_size
                
                # Track in database
                self.track_downloaded_file(source_id, folder_name, file_info, file_path)
        
        logger.info(f"✅ SYNC [{source_id}] Folder completed: {downloaded_count} files, {total_size/1024/1024:.1f}MB")
        
        return {
            'success': True,
            'files_downloaded': downloaded_count,
            'total_size': total_size,
            'folder_name': folder_name
        }
    
    def sync_source(self, source_id: int) -> Dict:
        """Sync entire source - simple version"""
        logger.info(f"🚀 Starting sync for source {source_id}")
        
        # Get source configuration
        source_config = self._get_source_config(source_id)
        if not source_config:
            return {'success': False, 'message': f'Source {source_id} not found'}
        
        # Get Drive client
        drive = self.get_drive_client(source_id)
        if not drive:
            return {'success': False, 'message': 'Failed to get Drive client'}
        
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
        
        # Sync each folder
        total_files = 0
        total_size = 0
        synced_folders = []
        
        for folder_info in all_folders:
            folder_result = self.sync_folder(drive, folder_info, base_path, source_id)
            
            if folder_result['success']:
                total_files += folder_result['files_downloaded']
                total_size += folder_result['total_size']
                synced_folders.append(folder_result['folder_name'])
        
        total_size_mb = total_size / (1024 * 1024)
        
        logger.info(f"🎯 SYNC [{source_id}] COMPLETED: {total_files} files, {total_size_mb:.1f}MB")
        
        return {
            'success': True,
            'message': f'Downloaded {total_files} files ({total_size_mb:.1f} MB)',
            'files_downloaded': total_files,
            'total_size_mb': total_size_mb,
            'synced_folders': synced_folders
        }
    
    # ==================== HELPER METHODS ====================
    
    def _get_source_config(self, source_id: int) -> Optional[Dict]:
        """Get source configuration from database"""
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
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename for file system"""
        import re
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return sanitized.strip()