# VTrack Video Input Sources - Roadmap Chi Tiết

## 📊 **Tình trạng hiện tại**

### ✅ **Đã hoàn thành**
- **Local Path Processing**: VTrack đã hỗ trợ quét và xử lý video từ folder local trên PC
- **Core Video Processing**: Engine xử lý video đã hoàn thiện
- **File Management**: Quét tự động, xử lý file hoàn tất (không tham gia quá trình ghi file)

### 🎯 **Mục tiêu mở rộng**
Mở rộng khả năng xử lý video từ nhiều nguồn khác nhau thông qua **Universal Path Management System**

---

## 🔍 **Phân tích các loại Video Input Sources**

### **1. Local Paths** ✅ **ĐÃ HOÀN THÀNH**
- **Định nghĩa**: Ổ cứng PC nơi cài VTrack (C:, D:, etc.)
- **Trạng thái**: Đã implement hoàn tất
- **Access method**: Direct file system access

### **2. USB/External Paths** ✅ **KHÔNG CẦN CODE THÊM**
- **Định nghĩa**: Thiết bị lưu trữ gắn ngoài (USB, HDD external)
- **Trạng thái**: Tự động work với code hiện tại
- **Access method**: Giống Local paths (E:, F:, G:, etc.)
- **Lưu ý**: OS tự handle device detection, VTrack chỉ cần point đến đường dẫn

### **3. Network Paths** 🚧 **CẦN PHÁT TRIỂN**
- **Định nghĩa**: Ổ mạng LAN (SMB shares, FTP servers)
- **Khác biệt**: Cần authentication, connection handling
- **Ưu tiên**: **Cao** (phổ biến trong doanh nghiệp)

### **4. Camera/NVR Paths** 🚧 **CẦN PHÁT TRIỂN**
- **Định nghĩa**: Đầu ghi mạng có kết nối trực tiếp hoặc qua mạng
- **Khác biệt**: Cần file completion detection
- **Ưu tiên**: **Cao** (use case chính của surveillance)

### **5. Cloud Paths** 🚧 **CẦN PHÁT TRIỂN**
- **Định nghĩa**: Cloud storage của user (Google Drive, Dropbox)
- **Khác biệt**: Cần API integration, OAuth
- **Ưu tiên**: **Thấp** (chậm, phức tạp)

---

## 🛣️ **Roadmap Phát Triển**

### **Phase 1: Network Storage Support** (Ưu tiên cao)
> **Timeline**: 4-6 tuần

#### **1.1 SMB/CIFS Support**
**Mục tiêu**: Hỗ trợ Windows shared folders và NAS devices

**Technical Implementation**:
```python
# Dependencies cần thêm
pip install smbprotocol pysmb
```

**Core Features**:
- **Authentication Management**:
  - UI form để nhập credentials (username, password, domain)
  - Secure credential storage (keyring hoặc encrypted config)
  - Support guest access và anonymous login
  
- **Connection Handling**:
  - Auto-reconnect khi connection drop
  - Connection pooling để optimize performance
  - Timeout configuration (5-30s)
  
- **Path Management**:
  - Browse SMB shares qua UI
  - Validate SMB paths trước khi add
  - Support UNC paths (\\server\share\folder)

**File Operations**:
- Extend `file_lister.py` để support SMB paths
- Implement SMB file reading cho video processing
- Handle large file transfers efficiently

**Error Handling**:
- Network timeout scenarios
- Authentication failures
- Permission denied cases
- Server unavailable situations

#### **1.2 FTP/SFTP Support**
**Mục tiêu**: Hỗ trợ FTP servers và SFTP (secure FTP)

**Technical Implementation**:
```python
# Dependencies cần thêm
pip install ftplib paramiko
```

**Core Features**:
- **Protocol Support**:
  - FTP (port 21) - passive/active modes
  - SFTP (port 22) - SSH-based secure transfer
  - FTPS (FTP over SSL/TLS)
  
- **Authentication**:
  - Username/password authentication
  - SSH key authentication cho SFTP
  - Anonymous FTP support
  
- **Connection Management**:
  - Persistent connections với keepalive
  - Multi-threaded downloads
  - Resume interrupted transfers

**Implementation Steps**:
1. Tạo `network_manager.py` module
2. Implement FTP/SFTP client classes
3. Integrate với existing file_lister
4. Add UI configuration cho FTP settings
5. Testing với popular FTP servers

---

### **Phase 2: Camera/NVR Integration** (Ưu tiên cao)
> **Timeline**: 3-4 tuần

#### **2.1 File Completion Detection**
**Vấn đề cốt lõi**: Đảm bảo chỉ xử lý video files đã được ghi hoàn tất

**Detection Methods**:

1. **File Size Stability Check**:
```python
def is_file_complete(filepath, stability_duration=30):
    """Check if file size stable for X seconds"""
    initial_size = get_file_size(filepath)
    time.sleep(stability_duration)
    final_size = get_file_size(filepath)
    return initial_size == final_size
```

2. **File Lock Detection**:
```python
def is_file_locked(filepath):
    """Check if file is being written by another process"""
    try:
        with open(filepath, 'r+b'):
            return False
    except IOError:
        return True
```

3. **Timestamp-based Detection**:
```python
def is_recording_complete(filepath, age_threshold=300):
    """File older than 5 minutes = likely complete"""
    file_age = time.time() - os.path.getmtime(filepath)
    return file_age > age_threshold
```

#### **2.2 Camera-specific Patterns**
**Common Camera File Patterns**:
- **Hikvision**: `YYYYMMDD_HHMMSS_001.mp4`
- **Dahua**: `YYYY-MM-DD_HH-MM-SS.mp4`
- **Axis**: `axis-YYYYMMDDTHHMMSS.mkv`
- **Generic**: `recording_TIMESTAMP.avi`

**Implementation**:
```python
def detect_camera_pattern(filename):
    """Detect camera brand from filename pattern"""
    patterns = {
        'hikvision': r'\d{8}_\d{6}_\d{3}\.(mp4|avi)',
        'dahua': r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.(mp4|avi)',
        'axis': r'axis-\d{8}T\d{6}\.(mkv|mp4)'
    }
    # Return camera type and extraction logic
```

#### **2.3 NVR Storage Access**
**Access Methods**:
1. **Direct Network Access**: NVR expose storage qua SMB/FTP
2. **API Access**: Sử dụng manufacturer APIs
3. **Mounted Storage**: NVR storage mounted như network drive

**Popular NVR Integrations**:
- **Hikvision**: SDK hoặc ISAPI
- **Dahua**: SDK hoặc REST API  
- **Axis**: VAPIX API
- **Generic**: SMB/FTP access

---

### **Phase 3: Cloud Storage Support** (Ưu tiên thấp)
> **Timeline**: 6-8 tuần

#### **3.1 Google Drive Integration**
**Technical Implementation**:
```python
# Dependencies
pip install google-api-python-client google-auth-oauthlib
```

**Core Features**:
- OAuth2 authentication flow
- Incremental sync (chỉ download files mới)
- Handle API rate limits (1000 requests/100s/user)
- Parallel downloads cho large files

#### **3.2 Dropbox Integration**
**Technical Implementation**:
```python
# Dependencies  
pip install dropbox
```

**Core Features**:
- OAuth2 flow
- Delta sync API
- Chunked uploads/downloads
- Webhook notifications cho file changes

#### **3.3 OneDrive Integration**
**Technical Implementation**:
```python
# Dependencies
pip install onedrivesdk
```

**Features tương tự Google Drive và Dropbox**

---

## 🏗️ **Implementation Architecture**

### **Core Components Update**

#### **1. Path Manager (`path_manager.py`)**
```python
class PathManager:
    def __init__(self):
        self.local_paths = []
        self.network_paths = []
        self.camera_paths = []
        self.cloud_paths = []
    
    def add_path(self, path_type, config):
        """Universal method to add any path type"""
        
    def validate_path(self, path_config):
        """Validate path accessibility"""
        
    def get_all_paths(self):
        """Return all configured paths"""
```

#### **2. File Lister Updates (`file_lister.py`)**
```python
class UniversalFileLister:
    def __init__(self, path_manager):
        self.path_manager = path_manager
        
    def scan_all_sources(self):
        """Scan files from all configured sources"""
        
    def scan_network_path(self, network_config):
        """Handle SMB/FTP scanning"""
        
    def scan_camera_path(self, camera_config):
        """Handle camera scanning with completion check"""
        
    def scan_cloud_path(self, cloud_config):
        """Handle cloud API scanning"""
```

#### **3. Configuration UI Updates (`config_bp.py`)**
**New UI Components**:
- Path type selector (Local/Network/Camera/Cloud)
- Network credentials form
- Camera settings (completion check intervals)
- Cloud OAuth flow integration
- Path testing và validation

#### **4. Database Schema Updates**
```sql
-- New tables for path management
CREATE TABLE video_sources (
    id INTEGER PRIMARY KEY,
    source_type TEXT, -- 'local', 'network', 'camera', 'cloud'
    path TEXT,
    config JSON, -- Store credentials, settings, etc.
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP
);

CREATE TABLE file_processing_log (
    id INTEGER PRIMARY KEY,
    source_id INTEGER,
    file_path TEXT,
    processing_status TEXT,
    completion_check_method TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES video_sources(id)
);
```

---

## 📋 **Implementation Checklist**

### **Phase 1: Network Storage (4-6 tuần)**

**Week 1-2: SMB Support**
- [ ] Install và setup smbprotocol
- [ ] Tạo SMB client class
- [ ] Implement credential management
- [ ] Add SMB path validation
- [ ] Create SMB file scanning logic
- [ ] Testing với Windows shares

**Week 3-4: FTP Support**  
- [ ] Implement FTP/SFTP clients
- [ ] Add FTP configuration UI
- [ ] Handle passive/active FTP modes
- [ ] Implement secure credential storage
- [ ] Testing với popular FTP servers

**Week 5-6: Integration & Testing**
- [ ] Integrate với existing file_lister
- [ ] Update UI cho network path management
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Error handling improvement

### **Phase 2: Camera/NVR (3-4 tuần)**

**Week 1: File Completion Detection**
- [ ] Implement file size stability check
- [ ] Add file lock detection
- [ ] Create timestamp-based completion check
- [ ] Configurable completion criteria

**Week 2: Camera Pattern Recognition**
- [ ] Research common camera file patterns
- [ ] Implement pattern detection algorithms
- [ ] Add camera-specific completion logic
- [ ] Testing với real camera files

**Week 3-4: NVR Integration**
- [ ] Research major NVR APIs
- [ ] Implement direct NVR access methods
- [ ] Add NVR configuration UI
- [ ] End-to-end testing với real NVR systems

### **Phase 3: Cloud Storage (6-8 tuần)**

**Week 1-2: Google Drive**
- [ ] Setup Google Cloud Console project
- [ ] Implement OAuth2 flow
- [ ] Add Google Drive API integration
- [ ] Handle rate limits và quotas

**Week 3-4: Dropbox Integration**
- [ ] Setup Dropbox app
- [ ] Implement Dropbox API
- [ ] Add incremental sync
- [ ] Testing với large files

**Week 5-6: OneDrive Integration**  
- [ ] Similar implementation như Google Drive
- [ ] Cross-platform compatibility testing

**Week 7-8: Cloud Optimization**
- [ ] Implement caching mechanisms
- [ ] Optimize download performance
- [ ] Add progress tracking
- [ ] Error recovery mechanisms

---

## 🎯 **Success Criteria**

### **Functional Requirements**
- [ ] Support tất cả 5 loại video input sources
- [ ] Zero data loss khi connection issues
- [ ] Tự động retry failed operations
- [ ] User-friendly configuration UI
- [ ] Real-time status monitoring

### **Performance Requirements**
- [ ] Processing time không tăng >20% với multiple sources
- [ ] Network timeouts <30 seconds
- [ ] Cloud sync efficiency >80%
- [ ] Memory usage <500MB additional cho network operations

### **Quality Requirements**
- [ ] 99% uptime cho local/USB sources
- [ ] 95% uptime cho network sources  
- [ ] 90% uptime cho cloud sources
- [ ] Comprehensive error logging
- [ ] Automated testing coverage >80%

---

## 🔧 **Technical Notes**

### **Dependencies thêm vào requirements.txt**
```txt
# Network storage
smbprotocol==1.12.0
pysmb==1.2.9.1
paramiko==3.4.0

# Cloud storage  
google-api-python-client==2.108.0
google-auth-oauthlib==1.1.0
dropbox==11.36.2
onedrivesdk==1.1.8

# Utilities
keyring==24.3.0  # Secure credential storage
requests-oauthlib==1.3.1  # OAuth helpers
```

### **Configuration Management**
- Sử dụng JSON hoặc YAML cho path configurations
- Encrypt sensitive data (passwords, API keys)
- Support environment variables cho production
- Backup và restore configurations

### **Monitoring và Logging**
- Detailed logging cho tất cả network operations
- Performance metrics tracking
- Error alerting system
- Usage analytics cho optimization

---

*Tài liệu này sẽ được update theo tiến độ implementation và feedback trong quá trình phát triển.*