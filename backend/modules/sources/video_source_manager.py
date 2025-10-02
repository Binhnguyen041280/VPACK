import sqlite3
import os
import json
import logging
import uuid
from datetime import datetime
import pytz
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock

# Cấu hình múi giờ Việt Nam - ĐỒNG NHẤT VỚI FILE_LISTER
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

class VideoSourceManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_all_active_sources(self):
        """Get all active video sources from database"""
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, source_type, name, path, config, active, created_at 
                        FROM video_sources 
                        WHERE active = 1 
                        ORDER BY source_type, name
                    """)
                    sources = []
                    for row in cursor.fetchall():
                        source = {
                            'id': row[0],
                            'source_type': row[1],
                            'name': row[2],
                            'path': row[3],
                            'config': json.loads(row[4]) if row[4] else {},
                            'active': row[5],
                            'created_at': row[6]
                        }
                        sources.append(source)
                    return sources
        except Exception as e:
            self.logger.error(f"Error getting active sources: {e}")
            return []

    def get_current_active_source(self):
        """Get current active source (Single Active Source)"""
        sources = self.get_all_active_sources()
        return sources[0] if sources else None
    
    def get_source_by_id(self, source_id):
        """Get specific video source by ID"""
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, source_type, name, path, config, active, created_at 
                        FROM video_sources 
                        WHERE id = ?
                    """, (source_id,))
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': row[0],
                            'source_type': row[1],
                            'name': row[2],
                            'path': row[3],
                            'config': json.loads(row[4]) if row[4] else {},
                            'active': row[5],
                            'created_at': row[6]
                        }
                    return None
        except Exception as e:
            self.logger.error(f"Error getting source by id {source_id}: {e}")
            return None
    
    def get_source_id_by_name(self, source_name):
        """Get source ID by name"""
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM video_sources WHERE name = ?", (source_name,))
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting source id by name {source_name}: {e}")
            return None
    
    def set_active_source(self, source_id):
        """Set single active source (disable all others)"""
        try:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Disable all sources first
                    cursor.execute("UPDATE video_sources SET active = 0")
                    
                    # Enable the specified source
                    cursor.execute("UPDATE video_sources SET active = 1 WHERE id = ?", (source_id,))
                    
                    if cursor.rowcount == 0:
                        return False, f"No source found with id {source_id}"
                    
                    self.logger.info(f"Set source id {source_id} as active")
                    return True, "Active source updated successfully"
                
        except Exception as e:
            self.logger.error(f"Error setting active source: {e}")
            return False, str(e)
    
    def validate_source_accessibility(self, source_config):
        """Check if source is accessible based on type"""
        source_type = source_config.get('source_type')
        path = source_config.get('path')
        config = source_config.get('config', {})
        
        try:
            if source_type == 'local':
                return self._validate_local_path(path)
            elif source_type == 'camera':
                return self._validate_camera_source(path, config)
            elif source_type == 'cloud':
                return self._validate_cloud_source(path, config)
            else:
                return False, f"Unknown source type: {source_type}"
        except Exception as e:
            self.logger.error(f"Error validating source accessibility: {e}")
            return False, str(e)
    
    def _validate_local_path(self, path):
        """Validate local file system path"""
        if not path:
            return False, "Path is required"
        if not os.path.exists(path):
            return False, f"Path does not exist: {path}"
        if not os.access(path, os.R_OK):
            return False, f"No read permission for path: {path}"
        return True, "Local path is accessible"
    
    
    def _validate_camera_source(self, path, config):
        """Validate camera source"""
        if config.get('type') == 'directory':
            return self._validate_local_path(path)
        elif config.get('type') == 'api':
            api_url = config.get('api_url')
            if not api_url:
                return False, "API URL is required for camera source"
            
            try:
                import requests
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    return True, "Camera API accessible"
                else:
                    return False, f"Camera API returned status {response.status_code}"
            except ImportError:
                return False, "requests library not installed"
            except Exception as e:
                return False, f"Camera API validation failed: {e}"
        else:
            return False, "Invalid camera source type"
    
    def _validate_cloud_source(self, path, config):
        """Validate cloud storage source"""
        provider = config.get('provider', '').lower()
        
        if provider == 'google_drive':
            return self._validate_google_drive(config)
        elif provider == 'dropbox':
            return self._validate_dropbox(config)
        elif provider == 'onedrive':
            return self._validate_onedrive(config)
        else:
            return False, f"Unsupported cloud provider: {provider}"
    
    def _validate_google_drive(self, config):
        """Validate Google Drive access"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            credentials_data = config.get('credentials')
            if not credentials_data:
                return False, "Google Drive credentials not found"
            
            credentials = Credentials.from_authorized_user_info(credentials_data)
            service = build('drive', 'v3', credentials=credentials)
            service.files().list(pageSize=1).execute()
            
            return True, "Google Drive connection successful"
            
        except ImportError:
            return False, "Google API library not installed"
        except Exception as e:
            return False, f"Google Drive validation failed: {e}"
    
    def _validate_dropbox(self, config):
        """Validate Dropbox access"""
        try:
            import dropbox
            
            access_token = config.get('access_token')
            if not access_token:
                return False, "Dropbox access token not found"
            
            dbx = dropbox.Dropbox(access_token)
            dbx.users_get_current_account()
            
            return True, "Dropbox connection successful"
            
        except ImportError:
            return False, "Dropbox library not installed"
        except Exception as e:
            return False, f"Dropbox validation failed: {e}"
    
    def _validate_onedrive(self, config):
        """Validate OneDrive access"""
        return False, "OneDrive validation not implemented yet"
    
    def add_source(self, source_type, name, path, config=None):
        """Add new video source"""
        try:
            if not all([source_type, name, path]):
                return False, "source_type, name, and path are required"
            
            config_json = json.dumps(config) if config else None
            
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Check if name already exists
                    cursor.execute("SELECT COUNT(*) FROM video_sources WHERE name = ?", (name,))
                    if cursor.fetchone()[0] > 0:
                        return False, f"Source name '{name}' already exists"
                    
                    # ✅ FIXED: Use VIETNAM_TZ for created_at - ĐỒNG NHẤT VỚI FILE_LISTER
                    cursor.execute("""
                        INSERT INTO video_sources (source_type, name, path, config, active, created_at)
                        VALUES (?, ?, ?, ?, 1, ?)
                    """, (source_type, name, path, config_json, datetime.now(VIETNAM_TZ)))
                    
                    source_id = cursor.lastrowid
                    
                    self.logger.info(f"Added new video source: {name} (id: {source_id})")
                    return True, f"Source '{name}' added successfully"
                
        except Exception as e:
            self.logger.error(f"Error adding source: {e}")
            return False, str(e)
    
    def update_source(self, source_id, **kwargs):
        """Update existing video source"""
        try:
            if not source_id:
                return False, "source_id is required"
            
            # Build update query
            update_fields = []
            update_values = []
            
            for field, value in kwargs.items():
                if field in ['source_type', 'name', 'path', 'active']:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
                elif field == 'config':
                    update_fields.append("config = ?")
                    update_values.append(json.dumps(value) if value else None)
            
            if not update_fields:
                return False, "No valid fields to update"
            
            update_values.append(source_id)
            
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    query = f"UPDATE video_sources SET {', '.join(update_fields)} WHERE id = ?"
                    cursor.execute(query, update_values)
                    
                    if cursor.rowcount == 0:
                        return False, f"No source found with id {source_id}"
                    
                    self.logger.info(f"Updated video source id: {source_id}")
                    return True, "Source updated successfully"
                
        except Exception as e:
            self.logger.error(f"Error updating source: {e}")
            return False, str(e)
    
    def delete_source(self, source_id):
        """Delete video source"""
        try:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("DELETE FROM video_sources WHERE id = ?", (source_id,))
                    
                    if cursor.rowcount == 0:
                        return False, f"No source found with id {source_id}"
                    
                    self.logger.info(f"Deleted video source id: {source_id}")
                    return True, "Source deleted successfully"
                
        except Exception as e:
            self.logger.error(f"Error deleting source: {e}")
            return False, str(e)
    
    def toggle_source_status(self, source_id, active):
        """Toggle source active status"""
        try:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("UPDATE video_sources SET active = ? WHERE id = ?", (active, source_id,))
                    
                    if cursor.rowcount == 0:
                        return False, f"No source found with id {source_id}"
                    
                    status = "activated" if active else "deactivated"
                    self.logger.info(f"Source id {source_id} {status}")
                    return True, f"Source {status} successfully"
                
        except Exception as e:
            self.logger.error(f"Error toggling source status: {e}")
            return False, str(e)