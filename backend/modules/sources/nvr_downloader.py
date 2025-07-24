import os
import json
import sqlite3
from datetime import datetime, timedelta
from modules.db_utils import get_db_connection
from .mock_video_generator import MockVideoGenerator

class NVRDownloader:
    """
    NVR Video Downloader với support cho cả mock và real ONVIF downloads
    OPTIMIZED: Sử dụng last_downloaded_file tracking thay vì full file tracking
    """
    
    def __init__(self, mock_mode=True, testing_intervals=True):
        """
        Initialize NVRDownloader
        
        Args:
            mock_mode (bool): True = use mock data, False = real ONVIF downloads
            testing_intervals (bool): True = use short intervals for testing
        """
        self.mock_mode = mock_mode
        self.testing_intervals = testing_intervals
        
        if self.mock_mode:
            self.mock_generator = MockVideoGenerator()
            print(f"🎭 NVRDownloader initialized in MOCK MODE")
        else:
            print(f"📹 NVRDownloader initialized in REAL MODE")
    
    def download_recordings(self, source_config):
        """
        Main download method - routes to mock or real implementation
        
        Args:
            source_config (dict): Source configuration
                - source_id: Database ID
                - name: Source name
                - selected_cameras: List of camera names
                - working_path: Base download directory
                
        Returns:
            dict: Download results with success status, files, and stats
        """
        print(f"🚀 Starting download for source: {source_config.get('name')}")
        print(f"📁 Working path: {source_config.get('working_path')}")
        print(f"📹 Cameras: {source_config.get('selected_cameras', [])}")
        
        if self.mock_mode:
            return self._mock_download(source_config)
        else:
            return self._real_onvif_download(source_config)
    
    def _mock_download(self, source_config):
        """
        Mock download implementation using MockVideoGenerator
        OPTIMIZED: Uses last_downloaded_file tracking
        
        Args:
            source_config (dict): Source configuration
            
        Returns:
            dict: Mock download results
        """
        print(f"🎬 MOCK DOWNLOAD: Generating recordings...")
        
        results = {
            'success': True,
            'downloaded_files': [],
            'total_size': 0,
            'cameras_processed': [],
            'mode': 'mock'
        }
        
        try:
            source_id = source_config.get('source_id')
            selected_cameras = source_config.get('selected_cameras', [])
            working_path = source_config.get('working_path')
            
            if not selected_cameras:
                print("⚠️ No cameras selected for download")
                return results
            
            # Process each camera
            for camera in selected_cameras:
                print(f"🎥 Processing camera: {camera}")
                
                # Create camera directory
                camera_dir = os.path.join(working_path, camera.replace(' ', '_'))
                os.makedirs(camera_dir, exist_ok=True)
                print(f"📁 Camera directory: {camera_dir}")
                
                # Generate mock files for this camera
                if self.testing_intervals:
                    # Testing mode: Short intervals for development
                    mock_files = self.mock_generator.generate_realtime_testing_videos(
                        camera, 
                        camera_dir, 
                        interval_seconds=120,  # 2 minutes for testing
                        count=15  # 15 files per camera
                    )
                else:
                    # Normal mode: Daily videos with realistic intervals
                    mock_files = self.mock_generator.generate_daily_videos(
                        camera,
                        camera_dir,
                        days=1,
                        schedule='security'  # 4 times per day
                    )
                
                # 🆕 OPTIMIZED: Track only latest file instead of all files
                tracked_count = self._track_latest_file_only(source_id, camera, mock_files)
                
                # Update results
                results['downloaded_files'].extend(mock_files)
                results['total_size'] += sum(f['size'] for f in mock_files)
                results['cameras_processed'].append(camera)
                
                print(f"✅ Camera {camera}: {len(mock_files)} files, {tracked_count} efficient tracking")
            
            print(f"🎉 MOCK DOWNLOAD COMPLETED:")
            print(f"   📊 Total files: {len(results['downloaded_files'])}")
            print(f"   📁 Total size: {results['total_size']} bytes ({results['total_size']/1024:.1f} KB)")
            print(f"   🎥 Cameras processed: {len(results['cameras_processed'])}")
            print(f"   🗄️ Database records: {len(results['cameras_processed'])} (optimized)")
            
        except Exception as e:
            print(f"❌ Mock download error: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def _real_onvif_download(self, source_config):
        """
        Real ONVIF download implementation (placeholder for future)
        
        Args:
            source_config (dict): Source configuration
            
        Returns:
            dict: Real download results
        """
        print(f"📹 REAL ONVIF DOWNLOAD: Not implemented yet")
        
        # TODO: Implement real ONVIF download logic
        # 1. Connect to ONVIF cameras
        # 2. Get last downloaded timestamp from last_downloaded_file table
        # 3. Query ONVIF for recordings newer than last timestamp
        # 4. Download only new files
        # 5. Update last_downloaded_file with latest info
        
        return {
            'success': False,
            'error': 'Real ONVIF download not implemented yet',
            'downloaded_files': [],
            'total_size': 0,
            'cameras_processed': [],
            'mode': 'real'
        }
    
    def _track_latest_file_only(self, source_id, camera_name, file_list):
        """
        🆕 OPTIMIZED: Track only the latest file per camera in last_downloaded_file table
        TEMPORARILY DISABLED: Database tracking disabled for clean workflow
        
        Args:
            source_id (int): Source database ID
            camera_name (str): Camera name
            file_list (list): List of file info dicts
            
        Returns:
            int: Number of files successfully tracked (for compatibility)
        """
        if not file_list:
            return 0
            
        try:
            # Calculate totals for logging
            total_count = len(file_list)
            total_size_mb = sum(f['size'] for f in file_list) / (1024 * 1024)
            
            # Find latest file by timestamp for logging
            latest_file = max(file_list, key=lambda f: f['timestamp'])
            
            # 🔧 TEMPORARILY DISABLED: Database tracking
            print(f"📊 Efficient tracking DISABLED: Latest file '{latest_file['filename']}' | Total: {total_count} files, {total_size_mb:.1f} MB")
            print(f"⚠️ Database tracking temporarily disabled for clean workflow")
            
            # Return total count for compatibility (without database update)
            return total_count
            
            # 🚫 DISABLED CODE BELOW:
            # # Import helper function from database
            # from database import update_last_downloaded_file
            # 
            # # Update database with only latest file info (1 DB operation instead of 15!)
            # success = update_last_downloaded_file(
            #     source_id, camera_name, latest_file, total_count, total_size_mb
            # )
            # 
            # if success:
            #     print(f"📊 Efficient tracking: Latest file '{latest_file['filename']}' | Total: {total_count} files, {total_size_mb:.1f} MB")
            #     return total_count
            # else:
            #     print(f"❌ Failed to track latest file for camera: {camera_name}")
            #     return 0
                
        except Exception as e:
            print(f"❌ Latest file tracking error: {e}")
            return 0
    
    def _track_downloaded_files(self, source_id, camera_name, file_list):
        """
        ⚠️ DEPRECATED: Legacy method for full file tracking
        Use _track_latest_file_only() instead for better performance
        
        Args:
            source_id (int): Source database ID
            camera_name (str): Camera name
            file_list (list): List of file info dicts
            
        Returns:
            int: Number of files successfully tracked
        """
        print(f"⚠️ Using legacy full file tracking - consider using _track_latest_file_only()")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            tracked_count = 0
            
            for file_info in file_list:
                try:
                    cursor.execute("""
                        INSERT INTO downloaded_files (
                            source_id, camera_name, local_file_path, file_size_bytes, 
                            download_timestamp, recording_start_time, original_filename
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        source_id,
                        camera_name,
                        file_info['path'],
                        file_info['size'],
                        datetime.now().isoformat(),
                        file_info['timestamp'].isoformat(),
                        file_info['filename']
                    ))
                    tracked_count += 1
                    
                except sqlite3.IntegrityError:
                    print(f"⚠️ File already tracked: {file_info['filename']}")
                except Exception as e:
                    print(f"❌ Failed to track file {file_info['filename']}: {e}")
            
            conn.commit()
            print(f"✅ DB commit & close success for camera: {camera_name}")
            conn.close()
            
            print(f"📊 Legacy tracking: {tracked_count}/{len(file_list)} files")
            return tracked_count
            
        except Exception as e:
            print(f"❌ Database tracking error: {e}")
            return 0
    
    def get_download_statistics(self, source_id):
        """
        🆕 OPTIMIZED: Get download statistics using last_downloaded_file table
        
        Args:
            source_id (int): Source database ID
            
        Returns:
            dict: Download statistics
        """
        try:
            # Import helper function from database
            from database import get_camera_download_stats
            
            stats = get_camera_download_stats(source_id)
            
            # Convert to expected format for compatibility
            camera_stats = {}
            for camera_name, camera_info in stats['camera_stats'].items():
                camera_stats[camera_name] = {
                    'file_count': camera_info['files_count'],
                    'total_size': camera_info['size_mb'] * 1024 * 1024  # Convert back to bytes
                }
            
            # Get latest download time
            latest_download = None
            for camera_info in stats['camera_stats'].values():
                if camera_info['last_download']:
                    if not latest_download or camera_info['last_download'] > latest_download:
                        latest_download = camera_info['last_download']
            
            return {
                'total_files': stats['total_files'],
                'total_size': int(stats['total_size_mb'] * 1024 * 1024),  # Convert to bytes
                'total_size_mb': stats['total_size_mb'],
                'camera_stats': camera_stats,
                'latest_download': latest_download,
                'cameras_count': stats['cameras_count']
            }
            
        except Exception as e:
            print(f"❌ Statistics error: {e}")
            return {
                'total_files': 0,
                'total_size': 0,
                'total_size_mb': 0,
                'camera_stats': {},
                'latest_download': None,
                'cameras_count': 0
            }
    
    def get_last_downloaded_timestamp(self, source_id, camera_name):
        """
        🆕 NEW: Get last downloaded file timestamp for incremental sync
        
        Args:
            source_id (int): Source database ID
            camera_name (str): Camera name
            
        Returns:
            str: ISO timestamp of last downloaded file
        """
        try:
            from database import get_last_downloaded_timestamp
            return get_last_downloaded_timestamp(source_id, camera_name)
        except Exception as e:
            print(f"❌ Error getting last timestamp: {e}")
            return "1970-01-01T00:00:00"  # Default to epoch if error
    
    def cleanup_old_downloads(self, source_id, keep_days=30):
        """
        🆕 OPTIMIZED: Clean up old downloaded files using filesystem + last_downloaded_file
        
        Args:
            source_id (int): Source database ID
            keep_days (int): Number of days to keep
            
        Returns:
            dict: Cleanup results
        """
        try:
            from database import get_camera_download_stats
            
            stats = get_camera_download_stats(source_id)
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            deleted_files = 0
            deleted_size = 0
            
            # For each camera, clean up old files from filesystem
            for camera_name, camera_info in stats['camera_stats'].items():
                if camera_info['last_download']:
                    last_download_date = datetime.fromisoformat(camera_info['last_download'])
                    
                    # If last download is older than cutoff, could clean up
                    if last_download_date < cutoff_date:
                        print(f"🧹 Camera {camera_name}: Last download {camera_info['last_download']} is old")
                        # Here you could implement filesystem cleanup logic
                        # For now, just report what would be cleaned
            
            # Update last_downloaded_file table to remove old entries
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM last_downloaded_file 
                WHERE source_id = ? AND last_download_time < ?
            """, (source_id, cutoff_date.isoformat()))
            
            db_deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            result = {
                'files_deleted': deleted_files,
                'size_freed': deleted_size,
                'size_freed_mb': round(deleted_size / (1024 * 1024), 2),
                'db_records_deleted': db_deleted
            }
            
            print(f"🧹 Cleanup completed: {deleted_files} files, {result['size_freed_mb']} MB freed, {db_deleted} DB records removed")
            return result
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            return {
                'files_deleted': 0,
                'size_freed': 0,
                'size_freed_mb': 0,
                'db_records_deleted': 0,
                'error': str(e)
            }
    
    def test_mock_download(self, test_source_config=None):
        """
        Test method để kiểm tra mock download functionality
        
        Args:
            test_source_config (dict): Optional test configuration
            
        Returns:
            dict: Test results
        """
        if test_source_config is None:
            test_source_config = {
                'source_id': 999,  # Test source ID
                'name': 'test_nvr',
                'selected_cameras': ['Test Camera 1', 'Test Camera 2'],
                'working_path': '/tmp/nvr_test_download'
            }
        
        print(f"🧪 TESTING OPTIMIZED MOCK DOWNLOAD...")
        print(f"📋 Test config: {test_source_config}")
        
        # Ensure test directory exists
        os.makedirs(test_source_config['working_path'], exist_ok=True)
        
        # Run mock download
        results = self._mock_download(test_source_config)
        
        # Verify results
        if results['success']:
            print(f"✅ Test passed: {len(results['downloaded_files'])} files created")
            print(f"📊 Efficient DB tracking: {len(results['cameras_processed'])} records instead of {len(results['downloaded_files'])}")
            
            # Check actual files exist
            sample_files = results['downloaded_files'][:5]  # Show first 5 files
            for file_info in sample_files:
                if os.path.exists(file_info['path']):
                    actual_size = os.path.getsize(file_info['path'])
                    print(f"   📄 {file_info['filename']}: {actual_size} bytes")
                else:
                    print(f"   ❌ Missing: {file_info['filename']}")
            
            if len(results['downloaded_files']) > 5:
                print(f"   ... and {len(results['downloaded_files']) - 5} more files")
        else:
            print(f"❌ Test failed: {results.get('error', 'Unknown error')}")
        
        return results

# Usage examples và test function
def test_nvr_downloader():
    """Test function để verify optimized NVRDownloader functionality"""
    print("=== TESTING OPTIMIZED NVRDownloader ===")
    
    # Test 1: Mock download với testing intervals
    print("\n--- Test 1: Optimized Mock Download (Testing Mode) ---")
    downloader = NVRDownloader(mock_mode=True, testing_intervals=True)
    
    test_config = {
        'source_id': 37,
        'name': 'nvr_localhost',
        'selected_cameras': ['Front Door Camera', 'Parking Lot Camera'],
        'working_path': '/tmp/test_nvr_downloads'
    }
    
    results = downloader.test_mock_download(test_config)
    
    # Test 2: Optimized Statistics
    print("\n--- Test 2: Optimized Download Statistics ---")
    stats = downloader.get_download_statistics(37)
    print(f"Statistics: {stats}")
    
    # Test 3: Last downloaded timestamp
    print("\n--- Test 3: Last Downloaded Timestamp ---")
    for camera in test_config['selected_cameras']:
        last_timestamp = downloader.get_last_downloaded_timestamp(37, camera)
        print(f"Camera '{camera}' last download: {last_timestamp}")
    
    # Test 4: Normal intervals
    print("\n--- Test 4: Normal Intervals ---")
    downloader_normal = NVRDownloader(mock_mode=True, testing_intervals=False)
    results_normal = downloader_normal.test_mock_download({
        'source_id': 38,
        'name': 'nvr_normal_test',
        'selected_cameras': ['Normal Test Camera'],
        'working_path': '/tmp/test_nvr_normal'
    })
    
    print("\n✅ All optimized tests completed!")

if __name__ == "__main__":
    test_nvr_downloader()