# 📘 Hikvision ISAPI Integration - Detailed Implementation Plan

**Provider**: Hikvision (Hik-Connect + NVR/DVR ISAPI)
**Lộ trình**: 2 - Camera Cloud Storage
**Priority**: Very High (Camera brand #1 tại VN - >50% market share)
**Timeline**: 5-7 ngày làm việc
**Độ khó**: ⭐⭐⭐⭐ Very Hard
**Status**: Planning
**Last Updated**: 2025-11-21

---

## 1. TỔNG QUAN & MỤC TIÊU

### 1.1 Use Case
- **Doanh nghiệp** có hệ thống camera Hikvision với NVR/DVR
- Video được record tự động lên NVR local storage hoặc Hik-Connect Cloud
- Cần download video từ NVR/Cloud về VPACK để phân tích batch
- User có credentials: NVR IP + username/password hoặc Hik-Connect account

### 1.2 Ưu Điểm Hikvision
- ✅ **Thương hiệu #1** camera tại VN và thế giới
- ✅ Hầu hết doanh nghiệp VN dùng Hikvision
- ✅ ISAPI protocol documented (sau khi register partner)
- ✅ Support rất nhiều dòng sản phẩm (IP camera, NVR, DVR)
- ✅ Có cả cloud storage (Hik-Connect) và local NVR
- ✅ Video quality cao, compression tốt

### 1.3 Technical Specs

#### **ISAPI (Internet Server Application Programming Interface)**
- **Protocol**: HTTP/HTTPS REST API
- **Authentication**: HTTP Digest Authentication
- **Base URL**: `http://{nvr_ip}` hoặc `https://{nvr_ip}`
- **SDK**: Hikvision Device Network SDK (optional)
- **Documentation**: Requires Hikvision Technology Partner Program registration

#### **2 Modes of Operation**

**Mode 1: Direct NVR/DVR Access** (Recommended)
- Connect trực tiếp tới NVR IP address
- Dùng NVR admin credentials
- Download từ local NVR storage
- Faster, no cloud limits

**Mode 2: Hik-Connect Cloud** (Alternative)
- User có Hik-Connect account
- Camera đã kết nối với Hik-Connect
- Download từ cloud storage
- Có bandwidth limits

### 1.4 Deliverables
1. ✅ Digest Authentication implementation
2. ✅ NVR discovery và connection test
3. ✅ Channel/camera listing
4. ✅ Video search by time range
5. ✅ Video download via ISAPI
6. ✅ Frontend NVR configuration UI
7. ✅ Tests (unit + integration)
8. ✅ Documentation

---

## 2. PREREQUISITES & SETUP

### 2.1 Hardware/Account Requirements

**Option 1: Direct NVR Access** (Recommended)
- [ ] Hikvision NVR/DVR hoặc IP Camera với ISAPI enabled
- [ ] NVR IP address (LAN hoặc WAN với port forward)
- [ ] Admin username/password
- [ ] Network access tới NVR (same LAN hoặc VPN)

**Option 2: Hik-Connect Cloud**
- [ ] Hik-Connect account (register tại https://www.hik-connect.com)
- [ ] Camera đã add vào Hik-Connect
- [ ] Cloud storage subscription (nếu cần)

### 2.2 Hikvision Technology Partner Program (Optional)

**Để access full ISAPI documentation:**

1. Truy cập: https://tpp.hikvision.com

2. Click **Register** → Fill form:
   - Company name (có thể dùng personal project)
   - Contact info
   - Purpose: Integration/Development

3. Sau khi approve (2-3 ngày), download:
   - **ISAPI Protocol Specification**
   - **Device Network SDK**
   - Code examples

**Lưu ý**: Có thể implement mà không cần SDK, chỉ dùng HTTP requests!

### 2.3 Test Environment Setup

#### **Option A: Real NVR**
```
1. NVR IP: 192.168.1.64 (example)
2. ISAPI Port: 80 (HTTP) hoặc 443 (HTTPS)
3. Username: admin
4. Password: Admin123
5. Test command:
   curl --digest -u admin:Admin123 http://192.168.1.64/ISAPI/System/deviceInfo
```

#### **Option B: IP Camera (nếu không có NVR)**
```
- IP Camera cũng support ISAPI
- Có storage card (SD card) để record
- Connect giống như NVR
```

### 2.4 Dependencies Installation
```bash
pip install requests==2.31.0
# requests library có sẵn Digest Authentication support
# Không cần SDK nếu dùng pure HTTP approach
```

---

## 3. KIẾN TRÚC & IMPLEMENTATION

### 3.1 File Structure
```
backend/modules/sources/
├── hikvision_auth.py          # Digest Auth implementation
├── hikvision_isapi.py         # ISAPI client
├── hikvision_nvr_scanner.py   # Network NVR discovery (optional)
├── credentials/
│   └── hikvision_credentials.json  # NVR presets (optional)
└── tokens/
    └── hikvision_{nvr_id}.json     # Encrypted NVR credentials
```

### 3.2 ISAPI Authentication Flow

```python
# Hikvision uses HTTP Digest Authentication (RFC 2617)

import requests
from requests.auth import HTTPDigestAuth

# Example ISAPI call
response = requests.get(
    'http://192.168.1.64/ISAPI/System/deviceInfo',
    auth=HTTPDigestAuth('admin', 'Admin123')
)
```

**Security**: Digest Auth is more secure than Basic Auth
- Password không được gửi plain text
- Challenge-response mechanism
- MD5 hashing

### 3.3 ISAPI Key Endpoints

#### **System Info**
```http
GET /ISAPI/System/deviceInfo
Response: NVR model, firmware, serial number

GET /ISAPI/System/status
Response: CPU, memory, disk usage
```

#### **Channel Management**
```http
GET /ISAPI/System/Video/inputs/channels
Response: List of camera channels (CH1, CH2, ...)

GET /ISAPI/ContentMgmt/InputProxy/channels
Response: Channel details with names
```

#### **Video Search**
```http
POST /ISAPI/ContentMgmt/search
Body:
<CMSearchDescription>
  <searchID>{uuid}</searchID>
  <trackList>
    <trackID>101</trackID> <!-- Channel 1 -->
  </trackList>
  <timeSpanList>
    <timeSpan>
      <startTime>2024-01-01T00:00:00Z</startTime>
      <endTime>2024-01-01T23:59:59Z</endTime>
    </timeSpan>
  </timeSpanList>
  <maxResults>100</maxResults>
  <searchResultPostion>0</searchResultPostion>
</CMSearchDescription>

Response: List of video files with playbackURI
```

#### **Video Download**
```http
GET /ISAPI/ContentMgmt/download
Query params:
  - playbackURI: rtsp://... (from search result)
  - format: MP4

Response: Video file stream
```

### 3.4 Core Components

#### **Component 1: `hikvision_auth.py`**
```python
import hashlib
import json
import os
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HikvisionAuthManager:
    """Hikvision NVR Credential Management"""

    def __init__(self):
        self.credentials_dir = os.path.join(os.path.dirname(__file__), 'credentials')
        self.tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
        os.makedirs(self.tokens_dir, exist_ok=True)

    def validate_nvr_credentials(self, host: str, username: str, password: str,
                                port: int = 80, use_https: bool = False) -> Dict:
        """Validate NVR credentials by testing ISAPI connection"""
        try:
            import requests
            from requests.auth import HTTPDigestAuth

            protocol = 'https' if use_https else 'http'
            base_url = f"{protocol}://{host}:{port}"

            # Test endpoint: Get device info
            response = requests.get(
                f"{base_url}/ISAPI/System/deviceInfo",
                auth=HTTPDigestAuth(username, password),
                timeout=10,
                verify=False  # Often self-signed cert
            )

            if response.status_code == 200:
                # Parse XML response
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)

                device_info = {
                    'model': root.findtext('.//model', 'Unknown'),
                    'serial_number': root.findtext('.//serialNumber', 'Unknown'),
                    'firmware': root.findtext('.//firmwareVersion', 'Unknown'),
                    'device_name': root.findtext('.//deviceName', 'Unknown'),
                    'device_type': root.findtext('.//deviceType', 'Unknown')
                }

                logger.info(f"✅ NVR connected: {device_info['model']} ({device_info['serial_number']})")

                return {
                    'success': True,
                    'device_info': device_info,
                    'host': host,
                    'port': port,
                    'use_https': use_https
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Invalid credentials (401 Unauthorized)'
                }
            else:
                return {
                    'success': False,
                    'message': f'Connection failed: HTTP {response.status_code}'
                }

        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Cannot connect to NVR (check IP address and network)'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Connection timeout (NVR not responding)'
            }
        except Exception as e:
            logger.error(f"❌ NVR validation error: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }

    def store_nvr_credentials(self, nvr_id: str, credentials: Dict) -> Dict:
        """Store encrypted NVR credentials"""
        try:
            # Encrypt
            from .cloud_auth import CloudAuthManager
            auth_manager = CloudAuthManager('hikvision')
            encrypted_data = auth_manager.encrypt_credentials(credentials)

            if not encrypted_data:
                return {'success': False, 'message': 'Encryption failed'}

            # Store
            filename = f"hikvision_{nvr_id}.json"
            filepath = os.path.join(self.tokens_dir, filename)

            storage = {
                'encrypted_data': encrypted_data,
                'nvr_id': nvr_id,
                'created_at': datetime.now().isoformat(),
                'provider': 'hikvision'
            }

            with open(filepath, 'w') as f:
                json.dump(storage, f, indent=2)

            os.chmod(filepath, 0o600)

            logger.info(f"✅ NVR credentials stored: {nvr_id}")
            return {'success': True}

        except Exception as e:
            logger.error(f"❌ Credential storage error: {e}")
            return {'success': False, 'message': str(e)}

    def load_nvr_credentials(self, nvr_id: str) -> Optional[Dict]:
        """Load and decrypt NVR credentials"""
        try:
            filename = f"hikvision_{nvr_id}.json"
            filepath = os.path.join(self.tokens_dir, filename)

            if not os.path.exists(filepath):
                return None

            with open(filepath, 'r') as f:
                storage = json.load(f)

            # Decrypt
            from .cloud_auth import CloudAuthManager
            auth_manager = CloudAuthManager('hikvision')
            credentials = auth_manager.decrypt_credentials(storage['encrypted_data'])

            return credentials

        except Exception as e:
            logger.error(f"❌ Credential loading error: {e}")
            return None
```

#### **Component 2: `hikvision_isapi.py`**
```python
import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import os
import logging

logger = logging.getLogger(__name__)

class HikvisionISAPI:
    """Hikvision ISAPI Client"""

    def __init__(self, host: str, username: str, password: str,
                 port: int = 80, use_https: bool = False):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.protocol = 'https' if use_https else 'http'
        self.base_url = f"{self.protocol}://{host}:{port}"
        self.auth = HTTPDigestAuth(username, password)
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for self-signed certs

    def get_device_info(self) -> Dict:
        """Get NVR device information"""
        try:
            response = self.session.get(
                f"{self.base_url}/ISAPI/System/deviceInfo",
                auth=self.auth,
                timeout=10
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            return {
                'model': root.findtext('.//model', 'Unknown'),
                'serial_number': root.findtext('.//serialNumber', 'Unknown'),
                'firmware': root.findtext('.//firmwareVersion', 'Unknown'),
                'device_name': root.findtext('.//deviceName', 'Unknown')
            }

        except Exception as e:
            logger.error(f"❌ Get device info error: {e}")
            return {}

    def get_channels(self) -> List[Dict]:
        """Get list of camera channels"""
        try:
            response = self.session.get(
                f"{self.base_url}/ISAPI/ContentMgmt/InputProxy/channels",
                auth=self.auth,
                timeout=10
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            channels = []

            for channel in root.findall('.//InputProxyChannel'):
                channel_id = channel.findtext('.//id', '')
                channel_name = channel.findtext('.//name', f'Channel {channel_id}')
                enabled = channel.findtext('.//enabled', 'true') == 'true'

                if enabled:
                    channels.append({
                        'id': channel_id,
                        'name': channel_name,
                        'enabled': enabled
                    })

            logger.info(f"📹 Found {len(channels)} enabled channels")
            return channels

        except Exception as e:
            logger.error(f"❌ Get channels error: {e}")
            return []

    def search_videos(self, channel_id: str, start_time: datetime,
                     end_time: datetime, max_results: int = 100) -> List[Dict]:
        """Search for video recordings in time range"""
        try:
            search_id = str(uuid.uuid4())

            # ISAPI expects trackID format: 101 for Channel 1, 201 for Channel 2, etc.
            track_id = f"{channel_id}01"

            # Format times as ISO8601
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Build XML request
            xml_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<CMSearchDescription>
    <searchID>{search_id}</searchID>
    <trackList>
        <trackID>{track_id}</trackID>
    </trackList>
    <timeSpanList>
        <timeSpan>
            <startTime>{start_str}</startTime>
            <endTime>{end_str}</endTime>
        </timeSpan>
    </timeSpanList>
    <maxResults>{max_results}</maxResults>
    <searchResultPostion>0</searchResultPostion>
    <metadataList>
        <metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor>
    </metadataList>
</CMSearchDescription>"""

            response = self.session.post(
                f"{self.base_url}/ISAPI/ContentMgmt/search",
                auth=self.auth,
                data=xml_body,
                headers={'Content-Type': 'application/xml'},
                timeout=30
            )
            response.raise_for_status()

            # Parse response
            root = ET.fromstring(response.content)
            videos = []

            for match in root.findall('.//searchMatchItem'):
                playback_uri = match.findtext('.//playbackURI', '')
                start_time_str = match.findtext('.//timeSpan/startTime', '')
                end_time_str = match.findtext('.//timeSpan/endTime', '')

                if playback_uri:
                    videos.append({
                        'playback_uri': playback_uri,
                        'start_time': start_time_str,
                        'end_time': end_time_str,
                        'channel_id': channel_id,
                        'source': 'nvr'
                    })

            logger.info(f"🎥 Found {len(videos)} video files for channel {channel_id}")
            return videos

        except Exception as e:
            logger.error(f"❌ Search videos error: {e}")
            return []

    def download_video(self, playback_uri: str, local_path: str,
                      format: str = 'MP4') -> bool:
        """Download video file from NVR"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download endpoint
            response = self.session.get(
                f"{self.base_url}/ISAPI/ContentMgmt/download",
                auth=self.auth,
                params={
                    'playbackURI': playback_uri,
                    'format': format
                },
                stream=True,  # Stream large files
                timeout=300  # 5 minute timeout for large videos
            )
            response.raise_for_status()

            # Write to file
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"✅ Downloaded video: {local_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Download video error: {e}")
            return False

    def get_storage_status(self) -> Dict:
        """Get NVR storage status"""
        try:
            response = self.session.get(
                f"{self.base_url}/ISAPI/ContentMgmt/Storage",
                auth=self.auth,
                timeout=10
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)

            total_gb = 0
            free_gb = 0

            for hdd in root.findall('.//hdd'):
                capacity = int(hdd.findtext('.//capacity', '0'))
                free_space = int(hdd.findtext('.//freeSpace', '0'))

                total_gb += capacity / (1024**3)
                free_gb += free_space / (1024**3)

            return {
                'total_gb': round(total_gb, 2),
                'free_gb': round(free_gb, 2),
                'used_gb': round(total_gb - free_gb, 2)
            }

        except Exception as e:
            logger.error(f"❌ Get storage status error: {e}")
            return {}
```

#### **Component 3: API Endpoints**
```python
# Add to cloud_endpoints.py

@app.route('/api/cloud/hikvision-connect', methods=['POST'])
@limiter.limit("10 per minute")
def hikvision_connect():
    """Connect to Hikvision NVR"""
    data = request.get_json()

    host = data.get('host')
    username = data.get('username')
    password = data.get('password')
    port = data.get('port', 80)
    use_https = data.get('use_https', False)

    if not all([host, username, password]):
        return jsonify({'success': False, 'message': 'Missing credentials'})

    auth_manager = HikvisionAuthManager()

    # Validate credentials
    result = auth_manager.validate_nvr_credentials(
        host, username, password, port, use_https
    )

    if not result['success']:
        return jsonify(result)

    # Store credentials
    nvr_id = f"{host}_{port}"
    credentials = {
        'host': host,
        'username': username,
        'password': password,
        'port': port,
        'use_https': use_https,
        'device_info': result['device_info']
    }

    store_result = auth_manager.store_nvr_credentials(nvr_id, credentials)

    if store_result['success']:
        return jsonify({
            'success': True,
            'nvr_id': nvr_id,
            'device_info': result['device_info']
        })
    else:
        return jsonify(store_result)

@app.route('/api/cloud/hikvision/channels', methods=['POST'])
@limiter.limit("15 per minute")
def hikvision_get_channels():
    """Get NVR channels"""
    data = request.get_json()
    nvr_id = data.get('nvr_id')

    auth_manager = HikvisionAuthManager()
    credentials = auth_manager.load_nvr_credentials(nvr_id)

    if not credentials:
        return jsonify({'success': False, 'message': 'NVR not found'})

    isapi = HikvisionISAPI(
        credentials['host'],
        credentials['username'],
        credentials['password'],
        credentials['port'],
        credentials['use_https']
    )

    channels = isapi.get_channels()

    return jsonify({
        'success': True,
        'channels': channels
    })

@app.route('/api/cloud/hikvision/search', methods=['POST'])
@limiter.limit("20 per minute")
def hikvision_search_videos():
    """Search videos in time range"""
    data = request.get_json()
    nvr_id = data.get('nvr_id')
    channel_id = data.get('channel_id')
    start_time = datetime.fromisoformat(data.get('start_time'))
    end_time = datetime.fromisoformat(data.get('end_time'))

    auth_manager = HikvisionAuthManager()
    credentials = auth_manager.load_nvr_credentials(nvr_id)

    if not credentials:
        return jsonify({'success': False, 'message': 'NVR not found'})

    isapi = HikvisionISAPI(
        credentials['host'],
        credentials['username'],
        credentials['password'],
        credentials['port'],
        credentials['use_https']
    )

    videos = isapi.search_videos(channel_id, start_time, end_time)

    return jsonify({
        'success': True,
        'videos': videos
    })
```

#### **Component 4: Frontend** (`HikvisionNVRConfig.tsx`)
```typescript
import React, { useState } from 'react';
import { Server, Camera, AlertCircle } from 'lucide-react';

interface HikvisionNVRConfigProps {
  onConnected: (nvrId: string, deviceInfo: any) => void;
}

export const HikvisionNVRConfig: React.FC<HikvisionNVRConfigProps> = ({
  onConnected
}) => {
  const [host, setHost] = useState('');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [port, setPort] = useState(80);
  const [useHttps, setUseHttps] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleConnect = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/cloud/hikvision-connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          host,
          username,
          password,
          port,
          use_https: useHttps
        })
      });

      const data = await response.json();

      if (data.success) {
        onConnected(data.nvr_id, data.device_info);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('Connection failed. Please check your inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Server className="h-6 w-6 text-blue-600" />
        <h3 className="text-lg font-semibold">Connect to Hikvision NVR</h3>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium mb-1">
          NVR IP Address or Hostname
        </label>
        <input
          type="text"
          placeholder="192.168.1.64"
          value={host}
          onChange={(e) => setHost(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Port</label>
          <input
            type="number"
            value={port}
            onChange={(e) => setPort(parseInt(e.target.value))}
            className="w-full border rounded px-3 py-2"
          />
        </div>

        <div className="flex items-center pt-6">
          <input
            type="checkbox"
            id="use-https"
            checked={useHttps}
            onChange={(e) => setUseHttps(e.target.checked)}
            className="mr-2"
          />
          <label htmlFor="use-https" className="text-sm">Use HTTPS</label>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Username</label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <button
        onClick={handleConnect}
        disabled={loading || !host || !username || !password}
        className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-300"
      >
        {loading ? 'Connecting...' : 'Connect to NVR'}
      </button>

      <div className="text-sm text-gray-500 mt-4">
        <p><strong>Note:</strong></p>
        <ul className="list-disc ml-5 mt-2 space-y-1">
          <li>Ensure VPACK can reach NVR (same network or VPN)</li>
          <li>ISAPI must be enabled on NVR</li>
          <li>Default HTTP port: 80, HTTPS port: 443</li>
        </ul>
      </div>
    </div>
  );
};
```

---

## 4. CHI TIẾT IMPLEMENTATION TIMELINE

### 4.1 Ngày 1-2: ISAPI Research & Auth (8-10 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Research ISAPI documentation | 2 giờ | Understand endpoints |
| Register TPP (if needed) | 1 giờ | Access docs |
| Setup test NVR/camera | 1 giờ | Test environment ready |
| Implement Digest Auth | 2 giờ | `hikvision_auth.py` |
| Test connection to real NVR | 2 giờ | Can connect |

**Checkpoint**: Có thể authenticate với NVR

### 4.2 Ngày 3: ISAPI Client (6-8 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Implement `get_device_info()` | 1 giờ | Device info working |
| Implement `get_channels()` | 1.5 giờ | Channel listing |
| Implement `search_videos()` | 2 giờ | Video search working |
| Test with real recordings | 1.5 giờ | Can find videos |
| Handle XML parsing edge cases | 1 giờ | Robust parsing |

**Checkpoint**: Có thể search videos

### 4.3 Ngày 4: Video Download (6-8 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Implement `download_video()` | 2 giờ | Download function |
| Test với videos nhỏ | 1 giờ | Small files OK |
| Test với videos lớn (>1GB) | 1.5 giờ | Streaming works |
| Add progress tracking | 1 giờ | Progress bars |
| Error handling | 1.5 giờ | Robust downloads |

**Checkpoint**: Có thể download videos successfully

### 4.4 Ngày 5: API & Frontend (6-8 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Implement API endpoints | 2 giờ | 4 endpoints |
| Create NVR config UI | 2 giờ | Connection form |
| Create channel selector | 1.5 giờ | Channel list UI |
| Time range picker | 1 giờ | Date/time input |
| Test full flow | 1.5 giờ | E2E working |

**Checkpoint**: Full UI flow working

### 4.5 Ngày 6-7: Testing & Polish (8-10 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Integration với auto-sync | 2 giờ | Sync working |
| Unit tests | 2 giờ | >70% coverage |
| Test với multiple NVRs | 2 giờ | Multi-NVR support |
| Error scenarios testing | 1 giờ | Error handling |
| Documentation | 2 giờ | User guide |
| Bug fixes | 1 giờ | Polish |

**Checkpoint**: Production ready

---

## 5. DATABASE SCHEMA

### 5.1 Source Config
```json
{
  "provider": "hikvision",
  "nvr_id": "192.168.1.64_80",
  "nvr_host": "192.168.1.64",
  "nvr_port": 80,
  "use_https": false,
  "device_info": {
    "model": "DS-7616NI-K2",
    "serial_number": "DS-7616NI-K2...",
    "firmware": "V4.61.105"
  },
  "selected_channels": ["1", "2", "3"],  // Which channels to sync
  "time_range_hours": 24  // Download last N hours
}
```

### 5.2 Downloaded Files
```json
{
  "source_id": 10,
  "cloud_file_id": "hik://192.168.1.64/ch1/2024-01-01T10:00:00",
  "playback_uri": "rtsp://192.168.1.64/...",
  "channel_id": "1",
  "channel_name": "Front Door",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T11:00:00Z",
  "local_file_path": "/data/downloads/hikvision/ch1_20240101_100000.mp4"
}
```

---

## 6. SECURITY & ERROR HANDLING

### 6.1 Security Checklist
- [x] NVR credentials stored encrypted
- [x] Use HTTPS when possible (self-signed cert OK)
- [x] No credentials in logs
- [x] Digest Auth (more secure than Basic)
- [x] Network access restricted (firewall rules)
- [x] Warn user about exposing NVR to internet

### 6.2 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| **Connection refused** | NVR không accessible | Check IP, firewall, VPN |
| **401 Unauthorized** | Wrong credentials | Verify username/password |
| **ISAPI disabled** | ISAPI service off | Enable trong NVR settings |
| **Channel not found** | Invalid channel ID | List channels first |
| **No recordings** | Time range has no videos | Verify NVR is recording |
| **Download timeout** | Large file, slow network | Increase timeout, use streaming |

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests
```python
def test_digest_auth():
    # Test Digest Authentication mechanism
    pass

def test_parse_device_info_xml():
    # Test XML parsing
    xml = '<DeviceInfo><model>DS-7616NI-K2</model></DeviceInfo>'
    # ...

def test_search_videos():
    # Mock ISAPI search response
    pass
```

### 7.2 Integration Tests
- Test với real NVR (if available)
- Test với Hikvision simulator
- Test various firmware versions

---

## 8. SUCCESS CRITERIA

- [x] Can connect to NVR
- [x] Can list channels
- [x] Can search videos by time
- [x] Can download videos
- [x] Digest Auth working
- [x] XML parsing robust
- [x] Error handling complete

---

## 9. RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| **ISAPI version differences** | High | Test multiple firmware versions |
| **Network access issues** | High | Clear documentation, VPN guide |
| **Large file downloads** | Medium | Streaming, progress tracking |
| **NVR storage full** | Low | Check storage status first |

---

## 10. NEXT STEPS

After Hikvision complete:
1. Move to Imou Life (easier API)
2. Consider Hik-Connect Cloud integration
3. Add NVR auto-discovery (SADP protocol)

---

**Estimated Effort**: 5-7 days
**Actual Effort**: _[TBD]_
**Status**: Planning → Ready

---

**Prepared by**: Claude (AI Assistant)
**Date**: 2025-11-21
**Version**: 1.0
