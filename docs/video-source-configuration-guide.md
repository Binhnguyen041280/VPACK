# Hướng dẫn Cấu hình Nguồn Video - VTrack System

## Tổng quan
VTrack hỗ trợ nhiều loại nguồn video khác nhau để đáp ứng nhu cầu đa dạng của người dùng:

## 1. Các Loại Nguồn Video Được Hỗ Trợ

### 1.1 Local Files (Tệp Cục Bộ)
- **Mô tả**: Truy cập trực tiếp các thư mục chứa video trên hệ thống
- **Hỗ trợ**:
  - Thư mục local trên server
  - Ổ đĩa mạng đã mount (NAS, SMB, NFS)
  - File shares từ NVR đã mount
  - Bất kỳ đường dẫn thư mục nào có thể truy cập

#### Cấu hình Local Source:
```json
{
  "source_type": "local",
  "name": "local_camera_folder",
  "path": "/path/to/video/folder",
  "config": {}
}
```

#### Ví dụ Mount Network Storage:
```bash
# Mount SMB/CIFS (Windows shares, NAS)
mount -t cifs //192.168.1.100/camera_recordings /mnt/nas_storage -o username=user,password=pass

# Mount NFS
mount -t nfs 192.168.1.100:/export/cameras /mnt/nfs_storage

# Permanent mount trong /etc/fstab
//192.168.1.100/cameras /mnt/nas cifs credentials=/etc/samba/credentials,uid=1000,gid=1000 0 0
```

### 1.2 Cloud Storage (Google Drive)
- **Mô tả**: Đồng bộ video từ Google Drive
- **Tính năng**:
  - OAuth2 authentication an toàn
  - Chọn thư mục với giao diện tree view
  - Tự động sync định kỳ
  - Download videos về server để xử lý
  - Hỗ trợ cấu trúc thư mục phức tạp

#### Cấu hình Cloud Source:
```json
{
  "source_type": "cloud", 
  "name": "google_drive_cameras",
  "path": "google_drive://selected_folders",
  "config": {
    "provider": "google_drive",
    "session_token": "jwt_token_here",
    "user_email": "user@gmail.com",
    "selected_folders": [
      {"id": "folder_id_1", "name": "Camera_01"},
      {"id": "folder_id_2", "name": "Camera_02"}
    ],
    "sync_settings": {
      "interval_minutes": 15,
      "auto_sync_enabled": true,
      "sync_only_new": true,
      "skip_duplicates": true
    }
  }
}
```

### 1.3 Network Cameras (ONVIF/NVR) - Backend Ready
- **Mô tả**: Kết nối trực tiếp với camera IP hoặc NVR
- **Hỗ trợ**:
  - ONVIF protocol cho camera IP chuẩn
  - ZoneMinder NVR integration
  - Multi-camera discovery
  - Authentication support

#### Cấu hình ONVIF Camera:
```json
{
  "source_type": "camera",
  "name": "onvif_camera_system", 
  "path": "onvif://192.168.1.50:1000",
  "config": {
    "protocol": "onvif",
    "ip": "192.168.1.50",
    "ports": [1000, 1001, 1002],
    "username": "admin",
    "password": "encrypted_password",
    "cameras": [
      {"port": 1000, "name": "Front_Door"},
      {"port": 1001, "name": "Back_Yard"},
      {"port": 1002, "name": "Garage"}
    ]
  }
}
```

#### Cấu hình NVR (ZoneMinder):
```json
{
  "source_type": "camera",
  "name": "zoneminder_nvr",
  "path": "zm://192.168.1.100/zm",
  "config": {
    "protocol": "zoneminder",
    "url": "http://192.168.1.100/zm",
    "username": "admin",
    "password": "encrypted_password",
    "monitors": [
      {"id": 1, "name": "Camera_1"},
      {"id": 2, "name": "Camera_2"}
    ]
  }
}
```

## 2. Cấu trúc Database

### 2.1 Bảng video_sources
```sql
CREATE TABLE video_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,  -- 'local', 'cloud', 'camera'
    name TEXT UNIQUE NOT NULL,
    path TEXT NOT NULL,         -- Physical path or connection URL
    config TEXT,                -- JSON configuration
    active INTEGER DEFAULT 1,   -- Single active source policy
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Bảng processing_config  
```sql
CREATE TABLE processing_config (
    id INTEGER PRIMARY KEY,
    input_path TEXT,          -- Working directory for video processing
    output_path TEXT,
    selected_cameras TEXT,    -- JSON array of camera names
    -- other processing settings...
);
```

### 2.3 Bảng cloud_sync_status
```sql
CREATE TABLE cloud_sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    folder_id TEXT,
    folder_name TEXT,
    last_sync TIMESTAMP,
    files_synced INTEGER DEFAULT 0,
    sync_status TEXT,
    FOREIGN KEY (source_id) REFERENCES video_sources(id)
);
```

## 3. Workflow Thêm Nguồn Video

### 3.1 Local Source Workflow
1. User chọn "Browse Files Directly"
2. Nhập đường dẫn thư mục
3. System kiểm tra quyền truy cập
4. Tự động detect camera folders
5. Lưu cấu hình và set active

### 3.2 Cloud Source Workflow  
1. User chọn "Google Drive Integration"
2. Xác thực OAuth2 với Google
3. Chọn folders từ tree view
4. Cấu hình sync settings
5. System tạo local sync directory
6. Khởi động background sync service

### 3.3 Camera Source Workflow (Planned)
1. User chọn "IP Camera/NVR"
2. Nhập IP và credentials
3. System discover cameras
4. User chọn cameras cần monitor
5. Cấu hình recording settings

## 4. API Endpoints

### 4.1 Source Management
```javascript
// Test connection
POST /api/config/test-source
{
  "source_type": "local|cloud|camera",
  "path": "path_or_url",
  "config": {...}
}

// Save source (single active)
POST /api/config/save-sources
{
  "sources": [{
    "source_type": "local",
    "name": "auto_generated_name",
    "path": "/path/to/videos",
    "config": {},
    "overwrite": false
  }]
}

// Get all sources
GET /api/config/get-sources

// Update source
PUT /api/config/update-source/{source_id}

// Delete source  
DELETE /api/config/delete-source/{source_id}

// Toggle active status
POST /api/config/toggle-source/{source_id}
```

### 4.2 Camera Management
```javascript
// Detect cameras in path
POST /api/config/detect-cameras
{
  "path": "/path/to/check"  
}

// Update selected cameras
POST /api/config/update-source-cameras
{
  "source_id": 1,
  "selected_cameras": ["Camera_01", "Camera_02"]
}

// Get processing cameras
GET /api/config/get-processing-cameras

// Sync cloud cameras
POST /api/config/sync-cloud-cameras

// Refresh camera list
POST /api/config/refresh-cameras

// Get camera status
GET /api/config/camera-status
```

### 4.3 Cloud Specific
```javascript
// Authenticate Google Drive
POST /api/cloud/auth/google
{
  "auth_code": "4/0AX4XfWh..."
}

// List folders (lazy loading)
GET /api/cloud/folders/{folder_id}/children

// Manual sync trigger
POST /api/cloud/sync/trigger
{
  "source_id": 1
}

// Get sync status
GET /api/cloud/sync/status/{source_id}
```

## 5. Path Management

### 5.1 Path Mapping Logic
```python
def get_working_path_for_source(source_type, source_name, source_path):
    if source_type == 'local':
        # Direct file system path
        return source_path
        
    elif source_type == 'cloud':
        # Create sync directory
        return os.path.join(BASE_DIR, "cloud_sync", source_name)
        
    elif source_type == 'camera':
        # Create recording directory  
        return os.path.join(BASE_DIR, "nvr_downloads", source_name)
```

### 5.2 Camera Detection
```python
def detect_camera_folders(path):
    """Auto-detect camera folders by pattern or video content"""
    cameras = []
    patterns = ['cam', 'camera', 'channel', 'ch']
    
    for item in os.listdir(path):
        if os.path.isdir(item_path):
            # Check naming patterns
            if any(p in item.lower() for p in patterns):
                cameras.append(item)
            # Check for video files
            elif has_video_files(item_path):
                cameras.append(item)
    
    return sorted(cameras)
```

## 6. Security & Best Practices

### 6.1 Authentication Security
- OAuth2 tokens được mã hóa trước khi lưu
- Session-based authentication với JWT
- Credentials không bao giờ lưu plaintext
- Token refresh tự động

### 6.2 Path Security  
- Validate all user-provided paths
- Prevent directory traversal attacks
- Check read permissions before access
- Sanitize filenames

### 6.3 Network Security
- HTTPS cho cloud connections
- Encrypted password storage
- Rate limiting cho sync operations
- Timeout handling

## 7. Cấu hình Nâng cao

### 7.1 Environment Variables
```bash
# Cloud encryption
export JWT_SECRET_KEY="your-secret-key"
export ENCRYPTION_KEY="your-encryption-key"

# Google OAuth
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"

# File paths
export BASE_DIR="/opt/vtrack"
export CLOUD_SYNC_DIR="/opt/vtrack/cloud_sync"
export NVR_DOWNLOAD_DIR="/opt/vtrack/nvr_downloads"
```

### 7.2 Sync Configuration
```json
{
  "sync_settings": {
    "interval_minutes": 15,      // Sync frequency
    "auto_sync_enabled": true,   // Enable auto sync
    "sync_only_new": true,       // Skip existing files
    "skip_duplicates": true,     // Check file hashes
    "max_file_size_mb": 1000,    // Max file size
    "allowed_extensions": [".mp4", ".avi", ".mov", ".mkv"],
    "bandwidth_limit_mbps": 10,  // Bandwidth throttling
    "retry_attempts": 3,         // Failed download retries
    "retention_days": 30         // Local cache retention
  }
}
```

### 7.3 Camera Folder Structure
```
/video_root/
├── Camera_01/
│   ├── 2024-01-15/
│   │   ├── 08-30-00.mp4
│   │   └── 09-00-00.mp4
│   └── 2024-01-16/
├── Camera_02/
└── Camera_03/
```

## 8. Troubleshooting

### 8.1 Common Issues
1. **Permission Denied**: Check folder permissions and user access
2. **Network Mount Failed**: Verify network connectivity and credentials
3. **Cloud Sync Stuck**: Check internet connection and token validity
4. **Camera Not Found**: Ensure correct IP and ONVIF enabled

### 8.2 Debug Tools
```bash
# Check mount status
mount | grep /mnt/

# Test network path
smbclient -L //server/share -U username

# Verify folder permissions
ls -la /path/to/videos

# Check sync logs
tail -f logs/cloud_sync.log
```

## 9. Future Enhancements

### 9.1 Planned Features
- Direct RTSP streaming support
- AWS S3 / Azure Blob storage
- FTP/SFTP server integration  
- Dropbox/OneDrive support
- Multi-source aggregation
- Real-time camera preview

### 9.2 UI Improvements
- Drag-drop folder selection
- Visual sync progress
- Camera health monitoring
- Bandwidth usage graphs
- Storage analytics dashboard

This configuration guide will be continuously updated as new features are added to the VTrack system.