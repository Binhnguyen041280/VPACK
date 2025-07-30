#!/usr/bin/env python3
"""
Quick test to add mock data for sync testing
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

def add_test_bug_data():
    """Add mock sync data to test sync functionality"""
    try:
        from modules.db_utils import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add mock cloud sync data
        source_id = 87  # Update with actual new source ID
        
        # Insert mock downloaded files để test
        test_files = [
            {
                'camera_name': 'Cloud_Cam1',
                'filename': 'test_video_1.mp4',
                'size': 1024000,  # 1MB
                'path': '/test/path/test_video_1.mp4'
            },
            {
                'camera_name': 'Cloud_Cam2', 
                'filename': 'test_video_2.mp4',
                'size': 2048000,  # 2MB
                'path': '/test/path/test_video_2.mp4'
            },
            {
                'camera_name': 'Cloud_Cam3',
                'filename': 'test_video_3.mp4', 
                'size': 1536000,  # 1.5MB
                'path': '/test/path/test_video_3.mp4'
            }
        ]
        
        from datetime import datetime
        
        for file_info in test_files:
            try:
                cursor.execute("""
                    INSERT INTO downloaded_files (
                        source_id, camera_name, original_filename, local_file_path,
                        file_size_bytes, download_timestamp, recording_start_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_id,
                    file_info['camera_name'],
                    file_info['filename'],
                    file_info['path'],
                    file_info['size'],
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                print(f"✅ Added mock file: {file_info['filename']}")
            except Exception as e:
                print(f"❌ Failed to add {file_info['filename']}: {e}")
        
        # Update sync status với mock data
        cursor.execute("""
            UPDATE sync_status 
            SET files_downloaded_count = ?, 
                total_download_size_mb = ?,
                last_sync_status = 'success',
                last_sync_message = 'Mock data added for testing'
            WHERE source_id = ?
        """, (len(test_files), sum(f['size'] for f in test_files) / (1024*1024), source_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Added {len(test_files)} mock files for testing")
        print("📊 Test sync dashboard với:")
        print("curl http://localhost:8080/api/sync/sync-dashboard")
        
    except Exception as e:
        print(f"❌ Error adding test data: {e}")

if __name__ == "__main__":
    add_test_bug_data()
