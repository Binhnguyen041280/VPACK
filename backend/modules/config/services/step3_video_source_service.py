"""
Step 3 Video Source Service Layer for V.PACK Configuration.

Handles business logic for video source configuration including 
local/cloud storage mapping, camera path management, and processing_config sync.
FIXED: Proper data mapping between video_sources and processing_config tables.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List
from ..shared import (
    safe_connection_wrapper,
    execute_with_change_detection,
    sync_processing_config,
    validate_video_source_config,
    sanitize_input,
    log_step_operation,
    ensure_column_exists
)
from ..utils import get_working_path_for_source


class Step3VideoSourceService:
    """Service class for Step 3 Video Source configuration operations."""
    
    def __init__(self):
        """Initialize service."""
        pass
    
    def get_video_source_config(self) -> Dict[str, Any]:
        """
        Get current video source configuration with backward compatibility.
        FIXED: Proper data retrieval from video_sources with processing_config fallback.
        
        Returns:
            Dict containing current video source configuration
        """
        try:
            # Try to get active source from video_sources table
            active_source = self._get_active_video_source()
            
            if active_source:
                # Extract configuration from active source
                config = active_source.get('config', {}) if isinstance(active_source.get('config'), dict) else {}
                
                video_source_data = {
                    "current_source": {
                        "id": active_source.get('id'),
                        "source_type": active_source.get('source_type'),
                        "name": active_source.get('name'),
                        "path": active_source.get('path'),
                        "created_at": active_source.get('created_at')
                    },
                    "input_path": active_source.get('path', ''),
                    "selected_cameras": config.get('selected_cameras', []),
                    "camera_paths": config.get('camera_paths', {}),
                    "detected_folders": config.get('detected_folders', []),
                    "selected_tree_folders": config.get('selected_tree_folders', []),
                    "camera_count": len(config.get('selected_cameras', [])),
                    "single_source_mode": True
                }
                
                log_step_operation("3", "get_video_source", {
                    "source_type": active_source.get('source_type'),
                    "camera_count": video_source_data["camera_count"]
                })
                
            else:
                # Fallback to processing_config for backward compatibility
                video_source_data = self._get_processing_config_fallback()
                
                log_step_operation("3", "get_video_source", {"fallback_used": True})
            
            # Add backward compatibility data
            compat_data = self._get_processing_config_data()
            if compat_data:
                video_source_data["backward_compatibility"] = compat_data
            
            return video_source_data
            
        except Exception as e:
            log_step_operation("3", "get_video_source", {"error": str(e)}, False)
            
            # Return safe defaults on error
            return {
                "current_source": None,
                "input_path": "",
                "selected_cameras": [],
                "camera_paths": {},
                "detected_folders": [],
                "selected_tree_folders": [],
                "camera_count": 0,
                "single_source_mode": True,
                "error": str(e)
            }
    
    def update_video_source_config(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Update video source configuration with proper data mapping.
        FIXED: Ensures sync between video_sources and processing_config tables.
        
        Args:
            data: Video source configuration data
            
        Returns:
            Tuple of (success: bool, result_data: dict)
        """
        try:
            # Validate input data
            is_valid, validation_error = validate_video_source_config(data)
            if not is_valid:
                return False, {"error": validation_error}
            
            # Extract and map data
            source_type = data.get('sourceType')
            input_path = sanitize_input(data.get('inputPath', ''), 500)
            detected_folders = data.get('detectedFolders', [])
            selected_cameras = data.get('selectedCameras', [])
            selected_tree_folders = data.get('selected_tree_folders', [])
            
            # Map source type to database format
            db_source_type = self._map_source_type(source_type)
            
            # Build camera configuration
            actual_selected_cameras, camera_paths, actual_input_path = self._build_camera_configuration(
                db_source_type, input_path, detected_folders, selected_cameras, selected_tree_folders
            )
            
            # Create source data for UPSERT
            source_data = self._create_source_data(
                db_source_type, actual_input_path, actual_selected_cameras, 
                camera_paths, detected_folders, selected_tree_folders, source_type
            )
            
            # Execute UPSERT operation
            new_source_id = self._upsert_video_source(source_data)
            if new_source_id is None:
                return False, {"error": "Failed to create/update video source"}
            
            # FIXED: Sync to processing_config for backward compatibility
            sync_success = self._sync_to_processing_config(actual_input_path, actual_selected_cameras, camera_paths)
            if not sync_success:
                print("⚠️ Processing config sync failed, but continuing...")
            
            # Build successful response
            result = {
                "sourceType": source_type,
                "inputPath": actual_input_path,
                "selectedCameras": actual_selected_cameras,
                "cameraPathsCount": len(camera_paths),
                "videoSourceId": new_source_id,
                "changed": True,
                "upsert_operation": True
            }
            
            # Add cloud-specific data
            if db_source_type == 'cloud':
                result["selectedTreeFoldersCount"] = len(selected_tree_folders)
                result["convertedFromFolders"] = True
                result["googleDrivePaths"] = camera_paths
            
            log_step_operation("3", "update_video_source", {
                "source_type": db_source_type,
                "camera_count": len(actual_selected_cameras),
                "sync_success": sync_success
            })
            
            return True, result
            
        except Exception as e:
            log_step_operation("3", "update_video_source", {"error": str(e)}, False)
            return False, {"error": f"Failed to update video source: {str(e)}"}
    
    def _get_active_video_source(self) -> Optional[Dict[str, Any]]:
        """Get active video source from video_sources table."""
        try:
            from modules.video_sources.video_source_repository import get_active_source
            return get_active_source()
        except ImportError:
            # Fallback if repository not available
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, source_type, name, path, config, created_at, is_active
                    FROM video_sources WHERE is_active = 1 LIMIT 1
                """)
                row = cursor.fetchone()
                
                if row:
                    config_data = {}
                    try:
                        config_data = json.loads(row[4]) if row[4] else {}
                    except json.JSONDecodeError:
                        pass
                    
                    return {
                        'id': row[0],
                        'source_type': row[1],
                        'name': row[2],
                        'path': row[3],
                        'config': config_data,
                        'created_at': row[5],
                        'is_active': row[6]
                    }
                return None
        except Exception as e:
            print(f"Error getting active video source: {e}")
            return None
    
    def _get_processing_config_fallback(self) -> Dict[str, Any]:
        """Get configuration from processing_config as fallback."""
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT input_path, selected_cameras, camera_paths FROM processing_config WHERE id = 1")
                row = cursor.fetchone()
                
                if row:
                    input_path, selected_cameras_json, camera_paths_json = row
                    selected_cameras = json.loads(selected_cameras_json) if selected_cameras_json else []
                    camera_paths = json.loads(camera_paths_json) if camera_paths_json else {}
                    
                    return {
                        "current_source": None,
                        "input_path": input_path or "",
                        "selected_cameras": selected_cameras,
                        "camera_paths": camera_paths,
                        "detected_folders": [],
                        "selected_tree_folders": [],
                        "camera_count": len(selected_cameras),
                        "single_source_mode": True,
                        "fallback_source": "processing_config"
                    }
        except Exception as e:
            print(f"Error getting processing config fallback: {e}")
        
        return {
            "current_source": None,
            "input_path": "",
            "selected_cameras": [],
            "camera_paths": {},
            "detected_folders": [],
            "selected_tree_folders": [],
            "camera_count": 0,
            "single_source_mode": True
        }
    
    def _get_processing_config_data(self) -> Optional[Dict[str, Any]]:
        """Get processing_config data for backward compatibility check."""
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT input_path, selected_cameras, camera_paths FROM processing_config WHERE id = 1")
                row = cursor.fetchone()
                
                if row:
                    input_path, selected_cameras_json, camera_paths_json = row
                    selected_cameras = json.loads(selected_cameras_json) if selected_cameras_json else []
                    camera_paths = json.loads(camera_paths_json) if camera_paths_json else {}
                    
                    return {
                        "processing_config_input_path": input_path or "",
                        "processing_config_selected_cameras": selected_cameras,
                        "processing_config_camera_paths": camera_paths
                    }
        except Exception as e:
            print(f"Error getting processing config data: {e}")
        
        return None
    
    def _map_source_type(self, source_type: str) -> str:
        """Map frontend source type to database format."""
        type_mapping = {
            'local_storage': 'local',
            'cloud_storage': 'cloud'
        }
        return type_mapping.get(source_type, source_type)
    
    def _build_camera_configuration(
        self, 
        db_source_type: str, 
        input_path: str, 
        detected_folders: List[Dict], 
        selected_cameras: List[str], 
        selected_tree_folders: List[Dict]
    ) -> Tuple[List[str], Dict[str, str], str]:
        """
        Build camera configuration with proper path mapping.
        FIXED: Handles both local and cloud camera path mapping correctly.
        """
        camera_paths = {}
        actual_selected_cameras = selected_cameras.copy()
        actual_input_path = input_path
        
        if db_source_type == 'local' and detected_folders:
            # Local storage: build camera_paths from detected_folders
            for folder in detected_folders:
                folder_name = folder.get('name')
                folder_path = folder.get('path')
                if folder_name in selected_cameras and folder_path:
                    camera_paths[folder_name] = folder_path
                    
        elif db_source_type == 'cloud' and selected_tree_folders:
            # Cloud storage: convert selected_tree_folders to camera format
            print("🔄 Converting cloud folders to camera format...")
            actual_selected_cameras = []
            camera_paths = {}
            
            for folder in selected_tree_folders:
                folder_name = folder.get('name', '')
                folder_path = folder.get('path', '')
                
                if folder_name:
                    actual_selected_cameras.append(folder_name)
                    # FIXED: For cloud, use local sync paths for processing_config compatibility
                    # Build working path for the source
                    working_path = get_working_path_for_source('cloud', 'CloudStorage_temp', folder_path)
                    local_camera_path = os.path.join(working_path, folder_name)
                    camera_paths[folder_name] = local_camera_path
                    
                    print(f"📁 Cloud camera: {folder_name} → {camera_paths[folder_name]}")
            
            # For cloud: set actual_input_path to first folder or working path
            if selected_tree_folders and len(selected_tree_folders) > 0:
                first_folder = selected_tree_folders[0]
                first_folder_path = first_folder.get('path', '')
                # Use working path for cloud sources
                if first_folder_path:
                    actual_input_path = get_working_path_for_source('cloud', 'CloudStorage', first_folder_path)
                else:
                    actual_input_path = "google_drive://"
        
        return actual_selected_cameras, camera_paths, actual_input_path
    
    def _create_source_data(
        self, 
        db_source_type: str, 
        actual_input_path: str, 
        actual_selected_cameras: List[str], 
        camera_paths: Dict[str, str], 
        detected_folders: List[Dict], 
        selected_tree_folders: List[Dict], 
        original_source_type: str
    ) -> Dict[str, Any]:
        """Create source data for UPSERT operation."""
        source_name = f"{'LocalStorage' if db_source_type == 'local' else 'CloudStorage'}_{int(datetime.now().timestamp())}"
        
        return {
            'source_type': db_source_type,
            'name': source_name,
            'path': actual_input_path,
            'config': {
                'selected_cameras': actual_selected_cameras,
                'camera_paths': camera_paths,
                'detected_folders': detected_folders,
                'selected_tree_folders': selected_tree_folders,
                'original_source_type': original_source_type
            }
        }
    
    def _upsert_video_source(self, source_data: Dict[str, Any]) -> Optional[int]:
        """Execute UPSERT operation for video source."""
        try:
            from modules.video_sources.video_source_repository import upsert_video_source
            return upsert_video_source(source_data)
        except ImportError:
            # Fallback implementation
            return self._fallback_upsert_video_source(source_data)
    
    def _fallback_upsert_video_source(self, source_data: Dict[str, Any]) -> Optional[int]:
        """Fallback UPSERT implementation."""
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                # Deactivate existing sources
                cursor.execute("UPDATE video_sources SET is_active = 0")
                
                # Insert new source
                cursor.execute("""
                    INSERT INTO video_sources (source_type, name, path, config, is_active, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (
                    source_data['source_type'],
                    source_data['name'],
                    source_data['path'],
                    json.dumps(source_data['config']),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error in fallback UPSERT: {e}")
            return None
    
    def _sync_to_processing_config(
        self, 
        input_path: str, 
        selected_cameras: List[str], 
        camera_paths: Dict[str, str]
    ) -> bool:
        """
        FIXED: Sync video source data to processing_config for backward compatibility.
        """
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                # Ensure camera_paths column exists
                ensure_column_exists("processing_config", "camera_paths", "TEXT", "'{}'")
                
                # Update processing_config
                cursor.execute("""
                    INSERT OR REPLACE INTO processing_config (
                        id, input_path, selected_cameras, camera_paths,
                        output_path, storage_duration, min_packing_time, max_packing_time,
                        frame_rate, frame_interval, video_buffer, default_frame_mode,
                        db_path, run_default_on_start
                    ) VALUES (
                        1, ?, ?, ?,
                        COALESCE((SELECT output_path FROM processing_config WHERE id = 1), '/default/output'),
                        COALESCE((SELECT storage_duration FROM processing_config WHERE id = 1), 30),
                        COALESCE((SELECT min_packing_time FROM processing_config WHERE id = 1), 10),
                        COALESCE((SELECT max_packing_time FROM processing_config WHERE id = 1), 120),
                        COALESCE((SELECT frame_rate FROM processing_config WHERE id = 1), 30),
                        COALESCE((SELECT frame_interval FROM processing_config WHERE id = 1), 5),
                        COALESCE((SELECT video_buffer FROM processing_config WHERE id = 1), 2),
                        COALESCE((SELECT default_frame_mode FROM processing_config WHERE id = 1), 'default'),
                        COALESCE((SELECT db_path FROM processing_config WHERE id = 1), ''),
                        COALESCE((SELECT run_default_on_start FROM processing_config WHERE id = 1), 1)
                    )
                """, (input_path, json.dumps(selected_cameras), json.dumps(camera_paths)))
                
                conn.commit()
                print("✅ Processing config sync completed")
                return True
                
        except Exception as e:
            print(f"⚠️ Processing config sync error: {e}")
            return False


# Create singleton instance for import
step3_video_source_service = Step3VideoSourceService()