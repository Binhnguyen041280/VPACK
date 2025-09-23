# backend/modules/utils/path_validator.py
import os
import shutil
import json
import logging
from typing import Dict, List, Tuple
from pathlib import Path
import stat

logger = logging.getLogger(__name__)

class PathValidator:
    """
    Path validation and directory management for VTrack video sources
    Handles directory creation, permission checks, and disk space validation
    """
    
    def __init__(self, base_path: str = None):
        """
        Initialize PathValidator with base path for video storage
        
        Args:
            base_path: Base directory for all video sources (default: project root)
        """
        if base_path is None:
            # Default to project root + storage directories
            from modules.db_utils import find_project_root
            project_root = find_project_root(os.path.abspath(__file__))
            base_path = project_root
        
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
        
        # Default storage directories
        self.cloud_sync_dir = self.base_path / "cloud_sync"
        self.output_clips_dir = self.base_path / "output_clips"
        
        self.logger.info(f"PathValidator initialized with base_path: {self.base_path}")
    
    def validate_source_path(self, source_type: str, source_name: str) -> Dict:
        """
        Validate and prepare working path for a video source
        
        Args:
            source_type: Type of source ('local', 'cloud')
            source_name: Unique name for the source
            
        Returns:
            Dict with validation results and working path
        """
        try:
            self.logger.info(f"🔍 Validating source path: {source_type}/{source_name}")
            
            # Determine working directory based on source type
            if source_type == 'cloud':
                working_path = self.cloud_sync_dir / source_name
            elif source_type == 'local':
                # Local sources use their own paths, no validation needed
                return {
                    'success': True,
                    'working_path': None,
                    'message': 'Local source uses existing path',
                    'disk_space_gb': self._get_disk_space_gb(str(self.base_path)),
                    'permissions': 'read-only'
                }
            else:
                return {
                    'success': False,
                    'message': f'Unknown source type: {source_type}',
                    'working_path': None
                }
            
            # Create working directory if it doesn't exist
            working_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✅ Working directory ready: {working_path}")
            
            # Validate permissions and disk space
            permissions_check = self.check_permissions(str(working_path))
            disk_check = self.check_disk_space(str(working_path), required_gb=1.0)
            
            if not permissions_check['writable']:
                return {
                    'success': False,
                    'message': f'Directory not writable: {working_path}',
                    'working_path': str(working_path),
                    'permissions': permissions_check
                }
            
            if not disk_check['sufficient']:
                return {
                    'success': False,
                    'message': f'Insufficient disk space: {disk_check["available_gb"]:.1f} GB available',
                    'working_path': str(working_path),
                    'disk_space': disk_check
                }
            
            return {
                'success': True,
                'working_path': str(working_path),
                'message': f'Source path validated successfully',
                'disk_space_gb': disk_check['available_gb'],
                'permissions': 'read-write',
                'created_directories': [str(working_path)]
            }
            
        except Exception as e:
            self.logger.error(f"❌ Path validation failed: {e}")
            return {
                'success': False,
                'message': f'Path validation error: {str(e)}',
                'working_path': None
            }
    
    def create_camera_directories(self, source_path: str, camera_names: List[str]) -> Dict:
        """
        Create individual directories for each camera under source path
        
        Args:
            source_path: Working directory for the source
            camera_names: List of camera names to create directories for
            
        Returns:
            Dict with created directories and camera path mapping
        """
        try:
            self.logger.info(f"📁 Creating camera directories in: {source_path}")
            self.logger.info(f"📹 Cameras: {camera_names}")
            
            if not camera_names:
                return {
                    'success': True,
                    'camera_paths': {},
                    'created_directories': [],
                    'message': 'No cameras to create directories for'
                }
            
            source_dir = Path(source_path)
            if not source_dir.exists():
                source_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"✅ Created source directory: {source_dir}")
            
            camera_paths = {}
            created_directories = []
            
            for camera_name in camera_names:
                # Sanitize camera name for file system
                safe_name = self._sanitize_directory_name(camera_name)
                camera_dir = source_dir / safe_name
                
                # Create camera directory
                camera_dir.mkdir(parents=True, exist_ok=True)
                
                # Store mapping
                camera_paths[camera_name] = str(camera_dir)
                created_directories.append(str(camera_dir))
                
                self.logger.info(f"✅ Created camera directory: {camera_name} → {camera_dir}")
            
            return {
                'success': True,
                'camera_paths': camera_paths,
                'created_directories': created_directories,
                'message': f'Created {len(camera_paths)} camera directories',
                'total_cameras': len(camera_names)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Camera directory creation failed: {e}")
            return {
                'success': False,
                'message': f'Camera directory creation error: {str(e)}',
                'camera_paths': {},
                'created_directories': []
            }
    
    def check_disk_space(self, path: str, required_gb: float = 1.0) -> Dict:
        """
        Check available disk space at given path
        
        Args:
            path: Path to check disk space for
            required_gb: Minimum required space in GB
            
        Returns:
            Dict with disk space information
        """
        try:
            # Get disk usage statistics
            statvfs = shutil.disk_usage(path)
            
            # Convert to GB
            total_gb = statvfs.total / (1024**3)
            used_gb = (statvfs.total - statvfs.free) / (1024**3)
            available_gb = statvfs.free / (1024**3)
            
            usage_percent = (used_gb / total_gb) * 100
            sufficient = available_gb >= required_gb
            
            return {
                'sufficient': sufficient,
                'available_gb': available_gb,
                'used_gb': used_gb,
                'total_gb': total_gb,
                'usage_percent': usage_percent,
                'required_gb': required_gb,
                'path': path
            }
            
        except Exception as e:
            self.logger.error(f"❌ Disk space check failed: {e}")
            return {
                'sufficient': False,
                'available_gb': 0,
                'error': str(e),
                'path': path
            }
    
    def check_permissions(self, path: str) -> Dict:
        """
        Check read/write permissions for given path
        
        Args:
            path: Path to check permissions for
            
        Returns:
            Dict with permission information
        """
        try:
            path_obj = Path(path)
            
            # Check if path exists
            if not path_obj.exists():
                # Try to create it to test permissions
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
                    created = True
                except Exception:
                    return {
                        'readable': False,
                        'writable': False,
                        'executable': False,
                        'error': 'Cannot create directory',
                        'path': path
                    }
            else:
                created = False
            
            # Test permissions
            readable = os.access(path, os.R_OK)
            writable = os.access(path, os.W_OK)
            executable = os.access(path, os.X_OK)
            
            # Get file mode
            try:
                stat_info = path_obj.stat()
                file_mode = stat.filemode(stat_info.st_mode)
            except Exception:
                file_mode = 'unknown'
            
            return {
                'readable': readable,
                'writable': writable,
                'executable': executable,
                'file_mode': file_mode,
                'created': created,
                'path': path
            }
            
        except Exception as e:
            self.logger.error(f"❌ Permission check failed: {e}")
            return {
                'readable': False,
                'writable': False,
                'executable': False,
                'error': str(e),
                'path': path
            }
    
    def get_camera_paths(self, source_path: str, camera_names: List[str]) -> Dict:
        """
        Get mapping of camera names to their directory paths
        
        Args:
            source_path: Working directory for the source
            camera_names: List of camera names
            
        Returns:
            Dict mapping camera names to directory paths
        """
        try:
            source_dir = Path(source_path)
            camera_paths = {}
            
            for camera_name in camera_names:
                safe_name = self._sanitize_directory_name(camera_name)
                camera_dir = source_dir / safe_name
                camera_paths[camera_name] = str(camera_dir)
            
            return {
                'success': True,
                'camera_paths': camera_paths,
                'source_path': source_path
            }
            
        except Exception as e:
            self.logger.error(f"❌ Get camera paths failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'camera_paths': {}
            }
    
    def cleanup_unused_directories(self, source_path: str, active_cameras: List[str]) -> Dict:
        """
        Remove directories for cameras that are no longer active
        
        Args:
            source_path: Working directory for the source
            active_cameras: List of currently active camera names
            
        Returns:
            Dict with cleanup results
        """
        try:
            self.logger.info(f"🧹 Cleaning up unused directories in: {source_path}")
            
            source_dir = Path(source_path)
            if not source_dir.exists():
                return {
                    'success': True,
                    'removed_directories': [],
                    'message': 'Source directory does not exist'
                }
            
            # Get all existing directories
            existing_dirs = [d for d in source_dir.iterdir() if d.is_dir()]
            
            # Sanitize active camera names
            active_safe_names = [self._sanitize_directory_name(name) for name in active_cameras]
            
            removed_directories = []
            
            for dir_path in existing_dirs:
                if dir_path.name not in active_safe_names:
                    try:
                        shutil.rmtree(dir_path)
                        removed_directories.append(str(dir_path))
                        self.logger.info(f"🗑️ Removed unused directory: {dir_path}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to remove directory {dir_path}: {e}")
            
            return {
                'success': True,
                'removed_directories': removed_directories,
                'message': f'Cleaned up {len(removed_directories)} unused directories',
                'active_cameras': active_cameras,
                'remaining_directories': len(existing_dirs) - len(removed_directories)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Directory cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'removed_directories': []
            }
    
    def get_directory_health_status(self, path: str) -> Dict:
        """
        Get comprehensive health status of a directory
        
        Args:
            path: Directory path to check
            
        Returns:
            Dict with health status information
        """
        try:
            path_obj = Path(path)
            
            if not path_obj.exists():
                return {
                    'healthy': False,
                    'exists': False,
                    'message': 'Directory does not exist',
                    'path': path
                }
            
            # Check permissions
            permissions = self.check_permissions(path)
            
            # Check disk space
            disk_space = self.check_disk_space(path, required_gb=0.5)
            
            # Count files and subdirectories
            try:
                files_count = len([f for f in path_obj.rglob('*') if f.is_file()])
                dirs_count = len([d for d in path_obj.rglob('*') if d.is_dir()])
            except Exception:
                files_count = 0
                dirs_count = 0
            
            # Calculate directory size
            try:
                total_size = sum(f.stat().st_size for f in path_obj.rglob('*') if f.is_file())
                size_mb = total_size / (1024**2)
            except Exception:
                size_mb = 0
            
            # Determine overall health
            healthy = (
                permissions.get('readable', False) and
                permissions.get('writable', False) and
                disk_space.get('sufficient', False)
            )
            
            return {
                'healthy': healthy,
                'exists': True,
                'permissions': permissions,
                'disk_space': disk_space,
                'files_count': files_count,
                'directories_count': dirs_count,
                'size_mb': size_mb,
                'path': path,
                'message': 'Directory health check complete'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Directory health check failed: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'path': path
            }
    
    def _sanitize_directory_name(self, name: str) -> str:
        """
        Sanitize camera name to be safe for file system directory names
        
        Args:
            name: Original camera name
            
        Returns:
            Sanitized directory name
        """
        # Replace problematic characters
        import re
        
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = re.sub(r'\s+', '_', sanitized)
        
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip('_.')
        
        # Ensure not empty
        if not sanitized:
            sanitized = 'camera'
        
        # Limit length to 50 characters
        if len(sanitized) > 50:
            sanitized = sanitized[:50].rstrip('_')
        
        return sanitized
    
    def _get_disk_space_gb(self, path: str) -> float:
        """
        Helper method to get available disk space in GB
        
        Args:
            path: Path to check
            
        Returns:
            Available space in GB
        """
        try:
            statvfs = shutil.disk_usage(path)
            return statvfs.free / (1024**3)
        except Exception:
            return 0.0
    
    def get_base_directories(self) -> Dict:
        """
        Get all base directories managed by PathValidator
        
        Returns:
            Dict with base directory paths and their status
        """
        directories = {
            'base_path': str(self.base_path),
            'cloud_sync': str(self.cloud_sync_dir),
            'output_clips': str(self.output_clips_dir)
        }
        
        status = {}
        for name, path in directories.items():
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
                status[name] = {
                    'path': path,
                    'exists': True,
                    'writable': os.access(path, os.W_OK)
                }
            except Exception as e:
                status[name] = {
                    'path': path,
                    'exists': False,
                    'error': str(e)
                }
        
        return {
            'directories': directories,
            'status': status,
            'all_healthy': all(s.get('exists', False) and s.get('writable', False) 
                             for s in status.values())
        }

# Global instance for easy import
path_validator = PathValidator()