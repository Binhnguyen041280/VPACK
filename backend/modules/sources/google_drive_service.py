#!/usr/bin/env python3

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GoogleDriveFolderService:
    """Service class for Google Drive folder operations with lazy loading support"""
    
    def __init__(self, credentials: Credentials):
        """Initialize service with Google Drive credentials"""
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)
        self.cache = {}
        self.cache_duration = 180  # 3 minutes cache
    
    def _get_cache_key(self, operation: str, *args) -> str:
        """Generate cache key for operations"""
        return f"{operation}:{'_'.join(str(arg) for arg in args)}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get('timestamp', 0)
        return time.time() - cached_time < self.cache_duration
    
    def _set_cache(self, cache_key: str, data: any):
        """Cache data with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def _get_cache(self, cache_key: str) -> any:
        """Get cached data if valid"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        return None
    
    def get_subfolders(self, parent_id: str = 'root', max_results: int = 50) -> List[Dict]:
        """
        Get subfolders of a parent folder with caching
        
        Args:
            parent_id: Parent folder ID ('root' for root folders)
            max_results: Maximum number of folders to return
            
        Returns:
            List of folder dictionaries with id, name, parents, createdTime
        """
        cache_key = self._get_cache_key('subfolders', parent_id, max_results)
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            logger.debug(f"📋 Cache hit for subfolders: {parent_id}")
            return cached_result
        
        try:
            logger.info(f"📂 Fetching subfolders for parent: {parent_id}")
            
            # Build query for folders only
            if parent_id == 'root':
                query = "mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
            else:
                query = f"mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=min(max_results, 100),  # Google Drive max is 100
                fields="files(id, name, parents, createdTime, modifiedTime)",
                orderBy="name"
            ).execute()
            
            folders = results.get('files', [])
            
            # Format folder data
            formatted_folders = []
            for folder in folders:
                formatted_folder = {
                    'id': folder['id'],
                    'name': folder['name'],
                    'type': 'folder',
                    'parent_id': parent_id,
                    'parents': folder.get('parents', []),
                    'created': folder.get('createdTime'),
                    'modified': folder.get('modifiedTime')
                }
                formatted_folders.append(formatted_folder)
            
            # Cache the result
            self._set_cache(cache_key, formatted_folders)
            
            logger.info(f"✅ Found {len(formatted_folders)} subfolders in {parent_id}")
            return formatted_folders
            
        except HttpError as e:
            logger.error(f"❌ HTTP error getting subfolders for {parent_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error getting subfolders for {parent_id}: {e}")
            return []
    
    def calculate_folder_depth(self, folder_id: str) -> int:
        """
        Calculate the depth level of a folder (0=root, 1=level1, etc.)
        
        Args:
            folder_id: Folder ID to calculate depth for
            
        Returns:
            Integer depth level (0-based)
        """
        if folder_id == 'root':
            return 0
        
        cache_key = self._get_cache_key('depth', folder_id)
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        try:
            depth = 0
            current_id = folder_id
            
            # Traverse up the folder hierarchy
            while current_id != 'root' and depth < 10:  # Prevent infinite loops
                try:
                    folder_info = self.service.files().get(
                        fileId=current_id,
                        fields="parents"
                    ).execute()
                    
                    parents = folder_info.get('parents', [])
                    if not parents:
                        break
                    
                    current_id = parents[0]  # Use first parent
                    depth += 1
                    
                    # Root check
                    if current_id == 'root':
                        break
                        
                except HttpError as e:
                    logger.warning(f"⚠️ Cannot get parent for {current_id}: {e}")
                    break
            
            # Cache the result
            self._set_cache(cache_key, depth)
            
            logger.debug(f"📏 Folder {folder_id} is at depth {depth}")
            return depth
            
        except Exception as e:
            logger.error(f"❌ Error calculating depth for {folder_id}: {e}")
            return 0
    
    def build_folder_path(self, folder_id: str) -> str:
        """
        Build the full path string for a folder
        
        Args:
            folder_id: Folder ID to build path for
            
        Returns:
            Full folder path string (e.g., "/Project/Area/Date/Camera")
        """
        if folder_id == 'root':
            return "/My Drive"
        
        cache_key = self._get_cache_key('path', folder_id)
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        try:
            path_parts = []
            current_id = folder_id
            
            # Traverse up the hierarchy collecting names
            while current_id != 'root' and len(path_parts) < 10:
                try:
                    folder_info = self.service.files().get(
                        fileId=current_id,
                        fields="name, parents"
                    ).execute()
                    
                    folder_name = folder_info.get('name', 'Unknown')
                    path_parts.insert(0, folder_name)
                    
                    parents = folder_info.get('parents', [])
                    if not parents:
                        break
                    
                    current_id = parents[0]
                    
                except HttpError as e:
                    logger.warning(f"⚠️ Cannot get folder info for {current_id}: {e}")
                    break
            
            # Build full path
            if path_parts:
                full_path = "/My Drive/" + "/".join(path_parts)
            else:
                full_path = "/My Drive"
            
            # Cache the result
            self._set_cache(cache_key, full_path)
            
            logger.debug(f"📁 Folder path for {folder_id}: {full_path}")
            return full_path
            
        except Exception as e:
            logger.error(f"❌ Error building path for {folder_id}: {e}")
            return "/My Drive/Unknown"
    
    def is_selectable_folder(self, folder_depth: int) -> bool:
        """
        Check if a folder at given depth can be selected
        
        Args:
            folder_depth: Depth level of the folder
            
        Returns:
            True if folder can be selected (depth == 4), False otherwise
        """
        return folder_depth == 4
    
    def get_folder_info(self, folder_id: str) -> Dict:
        """
        Get comprehensive information about a folder
        
        Args:
            folder_id: Folder ID to get info for
            
        Returns:
            Dictionary with folder information
        """
        cache_key = self._get_cache_key('info', folder_id)
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        try:
            folder_info = self.service.files().get(
                fileId=folder_id,
                fields="id, name, parents, createdTime, modifiedTime, size, mimeType"
            ).execute()
            
            depth = self.calculate_folder_depth(folder_id)
            path = self.build_folder_path(folder_id)
            
            info = {
                'id': folder_info['id'],
                'name': folder_info['name'],
                'parents': folder_info.get('parents', []),
                'created': folder_info.get('createdTime'),
                'modified': folder_info.get('modifiedTime'),
                'depth': depth,
                'path': path,
                'selectable': self.is_selectable_folder(depth),
                'mime_type': folder_info.get('mimeType')
            }
            
            # Cache the result
            self._set_cache(cache_key, info)
            
            return info
            
        except HttpError as e:
            logger.error(f"❌ HTTP error getting folder info for {folder_id}: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error getting folder info for {folder_id}: {e}")
            return {}
    
    def search_folders(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Search for folders by name
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            
        Returns:
            List of matching folders
        """
        try:
            logger.info(f"🔍 Searching folders: {query}")
            
            # Escape query for Google Drive search
            escaped_query = query.replace("'", "\\'").replace("\\", "\\\\")
            
            search_query = f"mimeType='application/vnd.google-apps.folder' and name contains '{escaped_query}' and trashed=false"
            
            results = self.service.files().list(
                q=search_query,
                pageSize=min(max_results, 100),
                fields="files(id, name, parents, createdTime)",
                orderBy="name"
            ).execute()
            
            folders = results.get('files', [])
            
            # Add depth and path information
            enriched_folders = []
            for folder in folders:
                depth = self.calculate_folder_depth(folder['id'])
                path = self.build_folder_path(folder['id'])
                
                enriched_folder = {
                    'id': folder['id'],
                    'name': folder['name'],
                    'parents': folder.get('parents', []),
                    'created': folder.get('createdTime'),
                    'depth': depth,
                    'path': path,
                    'selectable': self.is_selectable_folder(depth)
                }
                enriched_folders.append(enriched_folder)
            
            logger.info(f"✅ Found {len(enriched_folders)} folders matching '{query}'")
            return enriched_folders
            
        except Exception as e:
            logger.error(f"❌ Error searching folders: {e}")
            return []
    
    def has_subfolders(self, folder_id: str) -> bool:
        """
        Check if a folder has any subfolders (for UI expand indicators)
        
        Args:
            folder_id: Folder ID to check
            
        Returns:
            True if folder has subfolders, False otherwise
        """
        cache_key = self._get_cache_key('has_subfolders', folder_id)
        cached_result = self._get_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and '{folder_id}' in parents and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1,  # Only need to know if any exist
                fields="files(id)"
            ).execute()
            
            has_folders = len(results.get('files', [])) > 0
            
            # Cache the result
            self._set_cache(cache_key, has_folders)
            
            return has_folders
            
        except Exception as e:
            logger.error(f"❌ Error checking subfolders for {folder_id}: {e}")
            return False
    
    def get_folder_statistics(self, folder_id: str) -> Dict:
        """
        Get statistics about a folder (file count, total size, etc.)
        
        Args:
            folder_id: Folder ID to get stats for
            
        Returns:
            Dictionary with folder statistics
        """
        try:
            # Get all files in folder
            query = f"'{folder_id}' in parents and trashed=false"
            
            results = self.service.files().list(
                q=query,
                pageSize=1000,  # Get more files for accurate count
                fields="files(id, name, size, mimeType)"
            ).execute()
            
            files = results.get('files', [])
            
            # Calculate statistics
            total_files = len(files)
            total_size = 0
            video_count = 0
            folder_count = 0
            
            video_mimes = [
                'video/mp4', 'video/avi', 'video/mov', 'video/mkv',
                'video/m4v', 'video/wmv', 'video/flv', 'video/webm'
            ]
            
            for file in files:
                mime_type = file.get('mimeType', '')
                size = int(file.get('size', 0))
                
                total_size += size
                
                if mime_type == 'application/vnd.google-apps.folder':
                    folder_count += 1
                elif any(vm in mime_type for vm in video_mimes):
                    video_count += 1
            
            stats = {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'video_count': video_count,
                'folder_count': folder_count,
                'other_files': total_files - video_count - folder_count
            }
            
            logger.debug(f"📊 Stats for {folder_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting folder statistics for {folder_id}: {e}")
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'video_count': 0,
                'folder_count': 0,
                'other_files': 0
            }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("🧹 Cleared Google Drive folder service cache")
    
    def get_cache_info(self) -> Dict:
        """Get information about current cache state"""
        valid_entries = 0
        expired_entries = 0
        
        current_time = time.time()
        
        for key, entry in self.cache.items():
            if current_time - entry['timestamp'] < self.cache_duration:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_duration_seconds': self.cache_duration
        }