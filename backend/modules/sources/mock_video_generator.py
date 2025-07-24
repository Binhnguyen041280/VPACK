import os
import shutil
from datetime import datetime, timedelta
import json

class MockVideoGenerator:
    """
    Tạo mock video files để giả lập ONVIF camera recordings
    Sử dụng cho testing và development khi ONVIF Profile G không khả dụng
    """
    
    def __init__(self, base_samples_path=None):
        """
        Initialize MockVideoGenerator
        
        Args:
            base_samples_path (str): Path to sample video files (optional)
        """
        self.samples_path = base_samples_path
        self.mock_file_size = 15 * 1024  # 15KB per mock file
        
        # Common camera recording patterns
        self.recording_schedule = {
            'continuous': list(range(0, 24)),  # Every hour
            'business': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],  # Business hours
            'security': [6, 12, 18, 22],  # 4 times per day
            'minimal': [9, 15, 21],  # 3 times per day
            'testing': 'every_minute'  # 🆕 Special mode for testing
        }
    
    def generate_daily_videos(self, camera_name, target_dir, days=7, schedule='security'):
        """
        Tạo mock videos cho một camera trong X ngày
        
        Args:
            camera_name (str): Tên camera (VD: "Front Door Camera")
            target_dir (str): Thư mục đích
            days (int): Số ngày tạo videos (mặc định 7)
            schedule (str): Loại lịch recording ('continuous', 'business', 'security', 'minimal', 'testing')
            
        Returns:
            list: Danh sách các file đã tạo với metadata
        """
        print(f"🎬 Generating mock videos for {camera_name} (schedule: {schedule})...")
        
        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)
        
        videos_created = []
        
        # 🆕 TESTING MODE: Tạo files với interval ngắn
        if schedule == 'testing':
            return self._generate_testing_videos(camera_name, target_dir, days)
        
        # Original schedule logic for other modes
        hours_schedule = self.recording_schedule.get(schedule, self.recording_schedule['security'])
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            
            for hour in hours_schedule:
                # Tạo timestamp cho recording
                timestamp = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # Format filename theo convention thực tế
                safe_camera_name = camera_name.replace(' ', '_').replace('/', '_')
                filename = f"{safe_camera_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
                
                target_file = os.path.join(target_dir, filename)
                
                # Tạo mock file
                file_info = self._create_mock_video_file(
                    target_file, 
                    camera_name, 
                    timestamp
                )
                
                videos_created.append(file_info)
                
        print(f"✅ Created {len(videos_created)} mock videos for {camera_name}")
    def generate_recent_videos(self, camera_name, target_dir, hours=24):
        """
        Tạo videos cho X giờ gần đây (để simulate realtime download)
        
        Args:
            camera_name (str): Tên camera
            target_dir (str): Thư mục đích  
            hours (int): Số giờ gần đây (mặc định 24)
            
        Returns:
            list: Danh sách files được tạo
        """
        print(f"🕐 Generating recent {hours}h videos for {camera_name}...")
        
        os.makedirs(target_dir, exist_ok=True)
        videos_created = []
        
        # Tạo videos mỗi 2 giờ trong khoảng thời gian chỉ định
        for i in range(0, hours, 2):
            timestamp = datetime.now() - timedelta(hours=i)
            
            safe_camera_name = camera_name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_camera_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            target_file = os.path.join(target_dir, filename)
            
            file_info = self._create_mock_video_file(
                target_file, 
                camera_name, 
                timestamp
            )
            
            videos_created.append(file_info)
        
        print(f"✅ Created {len(videos_created)} recent videos for {camera_name}")
        return videos_created
    
    def _generate_testing_videos(self, camera_name, target_dir, days=1):
        """
        🧪 TESTING MODE: Tạo videos với interval ngắn để test nhanh
        
        Args:
            camera_name (str): Tên camera
            target_dir (str): Thư mục đích
            days (int): Số ngày (cho testing thường là 1)
            
        Returns:
            list: Danh sách files được tạo
        """
        print(f"🧪 TESTING MODE: Creating videos every 1-2 minutes for {camera_name}")
        
        videos_created = []
        base_time = datetime.now()
        
        # Tạo videos cho 30 phút gần đây, mỗi 2 phút 1 file
        for i in range(15):  # 15 files, mỗi file cách 2 phút
            timestamp = base_time - timedelta(minutes=i * 2)
            
            safe_camera_name = camera_name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_camera_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            target_file = os.path.join(target_dir, filename)
            
            file_info = self._create_mock_video_file(
                target_file, 
                camera_name, 
                timestamp
            )
            
            videos_created.append(file_info)
        
        print(f"✅ TESTING: Created {len(videos_created)} videos (2-minute intervals)")
        return videos_created
    
    def generate_realtime_testing_videos(self, camera_name, target_dir, interval_seconds=60, count=5):
        """
        🚀 REALTIME TESTING: Tạo videos với khoảng cách rất ngắn cho testing realtime
        
        Args:
            camera_name (str): Tên camera
            target_dir (str): Thư mục đích
            interval_seconds (int): Khoảng cách giữa các file (giây) - mặc định 60s
            count (int): Số lượng files tạo - mặc định 5
            
        Returns:
            list: Danh sách files được tạo
        """
        print(f"🚀 REALTIME TESTING: Creating {count} videos every {interval_seconds}s for {camera_name}")
        
        os.makedirs(target_dir, exist_ok=True)
        videos_created = []
        
        base_time = datetime.now()
        
        for i in range(count):
            # Tạo timestamp lùi lại theo interval
            timestamp = base_time - timedelta(seconds=i * interval_seconds)
            
            safe_camera_name = camera_name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_camera_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            target_file = os.path.join(target_dir, filename)
            
            file_info = self._create_mock_video_file(
                target_file, 
                camera_name, 
                timestamp
            )
            
            videos_created.append(file_info)
        
        print(f"✅ REALTIME TESTING: Created {len(videos_created)} videos ({interval_seconds}s intervals)")
        return videos_created
        """
        Tạo videos cho X giờ gần đây (để simulate realtime download)
        
        Args:
            camera_name (str): Tên camera
            target_dir (str): Thư mục đích  
            hours (int): Số giờ gần đây (mặc định 24)
            
        Returns:
            list: Danh sách files được tạo
        """
        print(f"🕐 Generating recent {hours}h videos for {camera_name}...")
        
        os.makedirs(target_dir, exist_ok=True)
        videos_created = []
        
        # Tạo videos mỗi 2 giờ trong khoảng thời gian chỉ định
        for i in range(0, hours, 2):
            timestamp = datetime.now() - timedelta(hours=i)
            
            safe_camera_name = camera_name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_camera_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            target_file = os.path.join(target_dir, filename)
            
            file_info = self._create_mock_video_file(
                target_file, 
                camera_name, 
                timestamp
            )
            
            videos_created.append(file_info)
        
        print(f"✅ Created {len(videos_created)} recent videos for {camera_name}")
        return videos_created
    
    def _create_mock_video_file(self, filepath, camera_name, timestamp):
        """
        Tạo một mock video file với metadata thực tế
        
        Args:
            filepath (str): Đường dẫn file đầy đủ
            camera_name (str): Tên camera
            timestamp (datetime): Thời gian recording
            
        Returns:
            dict: Thông tin file đã tạo
        """
        # Tạo mock video content với metadata
        video_metadata = {
            "camera": camera_name,
            "timestamp": timestamp.isoformat(),
            "duration_minutes": 60,  # Giả lập recording 1 giờ
            "resolution": "1920x1080",
            "codec": "H.264",
            "framerate": "30fps",
            "bitrate": "2000kbps",
            "file_type": "MP4",
            "mock_data": True
        }
        
        # Tạo file content
        header = f"MOCK VIDEO FILE - {camera_name}\n"
        header += f"Recording Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"Metadata: {json.dumps(video_metadata, indent=2)}\n"
        header += "=" * 50 + "\n"
        
        # Mock binary data (giả lập video data)
        mock_binary = b'\x00\x01\x02\x03' * (self.mock_file_size // 4)
        
        # Write file
        with open(filepath, 'wb') as f:
            f.write(header.encode('utf-8'))
            f.write(mock_binary)
        
        # Return file info
        file_info = {
            'filename': os.path.basename(filepath),
            'path': filepath,
            'size': os.path.getsize(filepath),
            'timestamp': timestamp,
            'camera': camera_name,
            'metadata': video_metadata
        }
        
        return file_info
    
    def simulate_continuous_recording(self, camera_name, target_dir, start_time=None, duration_hours=6):
        """
        Giả lập continuous recording với files nhỏ mỗi 30 phút
        
        Args:
            camera_name (str): Tên camera
            target_dir (str): Thư mục đích
            start_time (datetime): Thời gian bắt đầu (mặc định là 6h trước)
            duration_hours (int): Tổng thời gian recording (giờ)
            
        Returns:
            list: Danh sách files đã tạo
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=duration_hours)
        
        print(f"📹 Simulating continuous recording for {camera_name} ({duration_hours}h)")
        
        os.makedirs(target_dir, exist_ok=True)
        videos_created = []
        
        # Tạo file mỗi 30 phút
        intervals = duration_hours * 2  # 2 files per hour
        
        for i in range(intervals):
            timestamp = start_time + timedelta(minutes=i * 30)
            
            safe_camera_name = camera_name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_camera_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"
            
            target_file = os.path.join(target_dir, filename)
            
            file_info = self._create_mock_video_file(
                target_file, 
                camera_name, 
                timestamp
            )
            
            videos_created.append(file_info)
        
        print(f"✅ Created {len(videos_created)} continuous recording files for {camera_name}")
        return videos_created
    
    def cleanup_old_files(self, target_dir, keep_days=30):
        """
        Dọn dẹp các mock files cũ hơn X ngày
        
        Args:
            target_dir (str): Thư mục cần dọn dẹp
            keep_days (int): Số ngày giữ lại (mặc định 30)
            
        Returns:
            int: Số files đã xóa
        """
        if not os.path.exists(target_dir):
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        deleted_count = 0
        
        for filename in os.listdir(target_dir):
            filepath = os.path.join(target_dir, filename)
            
            if os.path.isfile(filepath):
                # Get file modification time
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff_time:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                        print(f"🗑️ Removed old mock file: {filename}")
                    except Exception as e:
                        print(f"❌ Failed to remove {filename}: {e}")
        
        if deleted_count > 0:
            print(f"✅ Cleanup completed: {deleted_count} old files removed")
        
        return deleted_count
    
    def get_mock_statistics(self, target_dir):
        """
        Lấy thống kê về mock files trong thư mục
        
        Args:
            target_dir (str): Thư mục cần thống kê
            
        Returns:
            dict: Thống kê chi tiết
        """
        if not os.path.exists(target_dir):
            return {
                'total_files': 0,
                'total_size': 0,
                'size_mb': 0,
                'date_range': None
            }
        
        files = [f for f in os.listdir(target_dir) if f.endswith('.mp4')]
        
        if not files:
            return {
                'total_files': 0,
                'total_size': 0,
                'size_mb': 0,
                'date_range': None
            }
        
        total_size = sum(
            os.path.getsize(os.path.join(target_dir, f)) 
            for f in files
        )
        
        # Extract dates from filenames for range
        dates = []
        for filename in files:
            try:
                # Extract date from filename format: CameraName_YYYYMMDD_HHMMSS.mp4
                date_part = filename.split('_')[-2]  # YYYYMMDD
                date_obj = datetime.strptime(date_part, '%Y%m%d')
                dates.append(date_obj)
            except:
                continue
        
        date_range = None
        if dates:
            date_range = {
                'earliest': min(dates).strftime('%Y-%m-%d'),
                'latest': max(dates).strftime('%Y-%m-%d')
            }
        
        return {
            'total_files': len(files),
            'total_size': total_size,
            'size_mb': round(total_size / (1024 * 1024), 2),
            'date_range': date_range,
            'files': files[:10]  # Sample of filenames
        }

# Usage example và test functions
def test_mock_generator():
    """Test function để kiểm tra MockVideoGenerator"""
    generator = MockVideoGenerator()
    
    test_dir = "/tmp/mock_camera_test"
    
    # Test 1: Testing mode (2-minute intervals)
    print("=== Test 1: Testing Mode (2-minute intervals) ===")
    testing_files = generator.generate_daily_videos(
        "Front Door Camera", 
        test_dir, 
        days=1, 
        schedule='testing'
    )
    print(f"Created {len(testing_files)} testing files")
    
    # Test 2: Realtime testing (1-minute intervals)
    print("\n=== Test 2: Realtime Testing Mode (1-minute intervals) ===")
    realtime_files = generator.generate_realtime_testing_videos(
        "Parking Camera",
        test_dir,
        interval_seconds=60,  # 1 phút
        count=10  # 10 files
    )
    print(f"Created {len(realtime_files)} realtime files")
    
    # Test 3: Ultra-fast testing (30-second intervals)
    print("\n=== Test 3: Ultra-Fast Testing (30-second intervals) ===")
    ultrafast_files = generator.generate_realtime_testing_videos(
        "Test Camera",
        test_dir,
        interval_seconds=30,  # 30 giây
        count=5  # 5 files
    )
    print(f"Created {len(ultrafast_files)} ultra-fast files")
    
    # Test 4: Statistics
    print("\n=== Test 4: Statistics ===")
    stats = generator.get_mock_statistics(test_dir)
    print(f"Statistics: {stats}")
    
    # Show actual files created
    print("\n=== Files Created ===")
    if os.path.exists(test_dir):
        files = sorted([f for f in os.listdir(test_dir) if f.endswith('.mp4')])
        for i, filename in enumerate(files[:10]):  # Show first 10
            filepath = os.path.join(test_dir, filename)
            size = os.path.getsize(filepath)
            print(f"{i+1:2d}. {filename} ({size} bytes)")
        if len(files) > 10:
            print(f"    ... and {len(files) - 10} more files")
    
    # Cleanup
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"\n✅ Cleaned up test directory: {test_dir}")

if __name__ == "__main__":
    test_mock_generator()