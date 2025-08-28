"""
VideoSourceRepository - UPSERT Pattern Implementation
Implements Option B: Single active source with REPLACE logic
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from modules.db_utils.safe_connection import safe_db_connection
from modules.config.logging_config import get_logger

logger = get_logger(__name__)

class VideoSourceRepository:
    """Repository for managing single active video source with UPSERT pattern"""
    
    def __init__(self):
        self.logger = logger
    
    def get_active_source(self) -> Optional[Dict[str, Any]]:
        """Get the current active video source"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, source_type, name, path, config, active, 
                           created_at, folder_depth, parent_folder_id
                    FROM video_sources 
                    WHERE active = 1
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'source_type': row[1], 
                        'name': row[2],
                        'path': row[3],
                        'config': json.loads(row[4]) if row[4] else {},
                        'active': row[5],
                        'created_at': row[6],
                        'folder_depth': row[7],
                        'parent_folder_id': row[8]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting active source: {e}")
            return None
    
    def upsert_video_source(self, source_data: Dict[str, Any]) -> Optional[int]:
        """
        UPSERT video source using Option B pattern:
        1. DELETE all existing sources
        2. INSERT new source as the only active source
        3. CASCADE cleanup related tables
        
        Args:
            source_data: Dict containing source configuration
            
        Returns:
            source_id if successful, None if failed
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Start transaction for atomic UPSERT
                cursor.execute("BEGIN TRANSACTION")
                
                self.logger.info("🔄 Starting UPSERT operation: clearing all existing sources")
                
                # STEP 1: DELETE all existing video sources (CASCADE will handle related tables)
                cursor.execute("DELETE FROM video_sources")
                deleted_count = cursor.rowcount
                self.logger.info(f"✅ Deleted {deleted_count} existing video sources")
                
                # STEP 2: INSERT new source as the only active source
                config_json = json.dumps(source_data.get('config', {}))
                
                cursor.execute("""
                    INSERT INTO video_sources (
                        source_type, name, path, config, active, 
                        folder_depth, parent_folder_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_data.get('source_type', 'local'),
                    source_data.get('name', 'Unnamed Source'),
                    source_data.get('path', ''),
                    config_json,
                    1,  # Always active (single source)
                    source_data.get('folder_depth', 0),
                    source_data.get('parent_folder_id', ''),
                    datetime.now().isoformat()
                ))
                
                new_source_id = cursor.lastrowid
                
                # STEP 3: Initialize related tables for the new source
                self._initialize_source_relations(cursor, new_source_id, source_data)
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                self.logger.info(f"✅ UPSERT completed successfully: new source_id={new_source_id}")
                self.logger.info(f"   Type: {source_data.get('source_type')}")
                self.logger.info(f"   Name: {source_data.get('name')}")
                self.logger.info(f"   Path: {source_data.get('path')}")
                
                return new_source_id
                
        except Exception as e:
            self.logger.error(f"❌ UPSERT failed: {e}")
            try:
                cursor.execute("ROLLBACK")
                self.logger.info("🔄 Transaction rolled back")
            except:
                pass
            return None
    
    def _initialize_source_relations(self, cursor, source_id: int, source_data: Dict[str, Any]):
        """Initialize related tables for the new source"""
        try:
            source_type = source_data.get('source_type', 'local')
            
            # Initialize camera configurations if provided
            selected_cameras = source_data.get('config', {}).get('selected_cameras', [])
            camera_paths = source_data.get('config', {}).get('camera_paths', {})
            
            if selected_cameras:
                for camera_name in selected_cameras:
                    folder_path = camera_paths.get(camera_name, '')
                    cursor.execute("""
                        INSERT INTO camera_configurations (
                            source_id, camera_name, folder_path, is_selected
                        ) VALUES (?, ?, ?, ?)
                    """, (source_id, camera_name, folder_path, 1))
                
                self.logger.info(f"✅ Initialized {len(selected_cameras)} camera configurations")
            
            # Initialize sync status for cloud sources
            if source_type == 'cloud':
                from datetime import timedelta
                now = datetime.now()
                next_sync = now + timedelta(minutes=10)
                
                cursor.execute("""
                    INSERT INTO sync_status (
                        source_id, sync_enabled, last_sync_timestamp, next_sync_timestamp,
                        sync_interval_minutes, last_sync_status, last_sync_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_id, 1, now.isoformat(), next_sync.isoformat(),
                    10, 'initialized', 'Auto-sync initialized for new source'
                ))
                
                self.logger.info("✅ Initialized sync status for cloud source")
            
        except Exception as e:
            self.logger.error(f"⚠️ Error initializing source relations: {e}")
            # Don't raise - let main transaction continue
    
    def update_active_source(self, updates: Dict[str, Any]) -> bool:
        """
        Update existing active source in-place (no source switching)
        
        Args:
            updates: Dict of fields to update
            
        Returns:
            True if successful, False if failed
        """
        try:
            active_source = self.get_active_source()
            if not active_source:
                self.logger.warning("❌ No active source to update")
                return False
            
            # Build dynamic UPDATE query
            update_fields = []
            update_values = []
            
            allowed_fields = ['name', 'path', 'config', 'folder_depth', 'parent_folder_id']
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == 'config':
                        value = json.dumps(value)
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                self.logger.warning("❌ No valid fields to update")
                return False
            
            update_values.append(active_source['id'])
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                update_query = f"""
                    UPDATE video_sources 
                    SET {', '.join(update_fields)} 
                    WHERE id = ?
                """
                
                cursor.execute(update_query, update_values)
                conn.commit()
                
                updated_rows = cursor.rowcount
                
                if updated_rows > 0:
                    self.logger.info(f"✅ Updated active source: {updated_rows} rows affected")
                    return True
                else:
                    self.logger.warning("⚠️ No rows updated")
                    return False
                
        except Exception as e:
            self.logger.error(f"❌ Error updating active source: {e}")
            return False
    
    def get_source_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the current source"""
        try:
            active_source = self.get_active_source()
            if not active_source:
                return {'error': 'No active source found'}
            
            source_id = active_source['id']
            stats = {
                'source': active_source,
                'cameras': [],
                'sync_status': None,
                'download_stats': None
            }
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get camera configurations
                cursor.execute("""
                    SELECT camera_name, folder_path, is_selected
                    FROM camera_configurations 
                    WHERE source_id = ?
                    ORDER BY camera_name
                """, (source_id,))
                
                stats['cameras'] = [
                    {
                        'name': row[0],
                        'folder_path': row[1],
                        'is_selected': bool(row[2])
                    }
                    for row in cursor.fetchall()
                ]
                
                # Get sync status for cloud sources
                if active_source['source_type'] == 'cloud':
                    cursor.execute("""
                        SELECT sync_enabled, last_sync_timestamp, next_sync_timestamp,
                               sync_interval_minutes, last_sync_status, last_sync_message
                        FROM sync_status 
                        WHERE source_id = ?
                    """, (source_id,))
                    
                    sync_row = cursor.fetchone()
                    if sync_row:
                        stats['sync_status'] = {
                            'sync_enabled': bool(sync_row[0]),
                            'last_sync_timestamp': sync_row[1],
                            'next_sync_timestamp': sync_row[2], 
                            'sync_interval_minutes': sync_row[3],
                            'last_sync_status': sync_row[4],
                            'last_sync_message': sync_row[5]
                        }
                    
                    # Get download statistics
                    cursor.execute("""
                        SELECT COUNT(*) as total_files, 
                               SUM(file_size_bytes) as total_bytes
                        FROM downloaded_files 
                        WHERE source_id = ?
                    """, (source_id,))
                    
                    download_row = cursor.fetchone()
                    if download_row:
                        total_bytes = download_row[1] or 0
                        stats['download_stats'] = {
                            'total_files': download_row[0] or 0,
                            'total_size_mb': round(total_bytes / (1024*1024), 2)
                        }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Error getting source statistics: {e}")
            return {'error': str(e)}
    
    def validate_source_switch(self, new_source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if source switch is safe to perform
        
        Args:
            new_source_data: Proposed new source configuration
            
        Returns:
            Dict with validation result and warnings
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'impact_summary': {}
        }
        
        try:
            active_source = self.get_active_source()
            
            # Check for source type change
            if active_source:
                old_type = active_source['source_type']
                new_type = new_source_data.get('source_type', 'local')
                
                if old_type != new_type:
                    validation_result['warnings'].append(
                        f"Source type changing: {old_type} → {new_type}"
                    )
                    validation_result['impact_summary']['type_change'] = True
            
            # Validate path accessibility
            new_path = new_source_data.get('path', '')
            if new_path:
                import os
                if new_source_data.get('source_type') == 'local':
                    if not os.path.exists(new_path):
                        validation_result['errors'].append(f"Path not accessible: {new_path}")
                        validation_result['valid'] = False
            
            # Check camera configurations
            new_cameras = new_source_data.get('config', {}).get('selected_cameras', [])
            if active_source:
                current_cameras = len(self.get_source_statistics().get('cameras', []))
                new_camera_count = len(new_cameras)
                
                if new_camera_count != current_cameras:
                    validation_result['warnings'].append(
                        f"Camera count changing: {current_cameras} → {new_camera_count}"
                    )
                    validation_result['impact_summary']['camera_change'] = True
            
            self.logger.info(f"✅ Source validation completed: {'Valid' if validation_result['valid'] else 'Invalid'}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"❌ Error validating source switch: {e}")
            return {
                'valid': False,
                'warnings': [],
                'errors': [f"Validation failed: {str(e)}"],
                'impact_summary': {}
            }
    
    def cleanup_orphaned_data(self) -> Dict[str, int]:
        """Clean up any orphaned data from previous sources"""
        cleanup_stats = {
            'camera_configurations': 0,
            'sync_status': 0,
            'downloaded_files': 0,
            'last_downloaded_file': 0
        }
        
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Clean camera_configurations without valid source_id
                cursor.execute("""
                    DELETE FROM camera_configurations 
                    WHERE source_id NOT IN (SELECT id FROM video_sources WHERE active = 1)
                """)
                cleanup_stats['camera_configurations'] = cursor.rowcount
                
                # Clean sync_status without valid source_id
                cursor.execute("""
                    DELETE FROM sync_status 
                    WHERE source_id NOT IN (SELECT id FROM video_sources WHERE active = 1)
                """)
                cleanup_stats['sync_status'] = cursor.rowcount
                
                # Clean downloaded_files without valid source_id
                cursor.execute("""
                    DELETE FROM downloaded_files 
                    WHERE source_id NOT IN (SELECT id FROM video_sources WHERE active = 1)
                """)
                cleanup_stats['downloaded_files'] = cursor.rowcount
                
                # Clean last_downloaded_file without valid source_id
                cursor.execute("""
                    DELETE FROM last_downloaded_file 
                    WHERE source_id NOT IN (SELECT id FROM video_sources WHERE active = 1)
                """)
                cleanup_stats['last_downloaded_file'] = cursor.rowcount
                
                conn.commit()
                
                total_cleaned = sum(cleanup_stats.values())
                self.logger.info(f"✅ Cleanup completed: {total_cleaned} orphaned records removed")
                
                return cleanup_stats
                
        except Exception as e:
            self.logger.error(f"❌ Error during cleanup: {e}")
            return cleanup_stats

# Convenience functions for external use
_repository = VideoSourceRepository()

def get_active_source() -> Optional[Dict[str, Any]]:
    """Get the current active video source"""
    return _repository.get_active_source()

def upsert_video_source(source_data: Dict[str, Any]) -> Optional[int]:
    """UPSERT video source using Option B pattern"""
    return _repository.upsert_video_source(source_data)

def update_active_source(updates: Dict[str, Any]) -> bool:
    """Update existing active source in-place"""
    return _repository.update_active_source(updates)

def get_source_statistics() -> Dict[str, Any]:
    """Get comprehensive statistics about the current source"""
    return _repository.get_source_statistics()

def validate_source_switch(new_source_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate if source switch is safe to perform"""
    return _repository.validate_source_switch(new_source_data)

def cleanup_orphaned_data() -> Dict[str, int]:
    """Clean up any orphaned data from previous sources"""
    return _repository.cleanup_orphaned_data()