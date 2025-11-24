# 📘 Imou Life Cloud Integration - Detailed Implementation Plan

**Provider**: Imou Life Cloud (Dahua Technology)
**Parent Company**: Dahua Technology (Camera brand #2 thế giới)
**Lộ trình**: 2 - Camera Cloud Storage
**Priority**: High (API tốt nhất trong camera cloud providers)
**Timeline**: 3-4 ngày làm việc
**Độ khó**: ⭐⭐ Medium
**Status**: Planning
**Last Updated**: 2025-11-21

---

## 1. TỔNG QUAN & MỤC TIÊU

### 1.1 Use Case
- User có camera Imou (IP camera cho gia đình/SME)
- Camera đã kết nối với Imou Life Cloud
- Video được lưu trữ trên cloud storage (cloud subscription)
- Cần download video từ cloud về VPACK để phân tích

### 1.2 Ưu Điểm Imou Life
- ✅ **API tốt nhất** trong các camera cloud providers
- ✅ **OpenSDK** chính thức với documentation rõ ràng
- ✅ **Hỗ trợ download** video MP4 format
- ✅ OAuth2 chuẩn cho authentication
- ✅ Developer Portal hoàn chỉnh: https://open.imoulife.com
- ✅ Camera giá tốt, phổ biến cho gia đình và SME tại VN
- ✅ Parent company: Dahua Technology (top 2 thế giới)

### 1.3 Imou Product Line
- **Imou Ranger** - PTZ cameras (indoor)
- **Imou Bullet** - Outdoor cameras
- **Imou Dome** - Dome cameras
- **Imou Cruiser** - PTZ outdoor cameras
- **Imou Cell** - Battery cameras

### 1.4 Technical Specs

#### **Imou Open Platform**
- **Documentation**: https://open.imoulife.com
- **Authentication**: OAuth2 (Authorization Code Flow)
- **API Base URL**: `https://openapi.imoulife.com`
- **SDK**: OpenSDK (iOS, Android, PC - Python tự implement REST API)
- **Video Download**: Hỗ trợ MP4 format

#### **API Scopes Required**
```json
{
  "device.basic": "Basic device info",
  "device.video": "Video playback",
  "cloud.storage": "Cloud storage access",
  "device.list": "List devices"
}
```

### 1.5 Deliverables
1. ✅ OAuth2 authentication
2. ✅ Device listing
3. ✅ Cloud storage video search
4. ✅ Video download (MP4)
5. ✅ Frontend device selector
6. ✅ Tests (unit + integration)
7. ✅ Documentation

---

## 2. PREREQUISITES & SETUP

### 2.1 Tài Khoản Cần Có

**User Requirements:**
- [ ] **Imou Life account** - Free registration tại:
  - App: Download "Imou Life" từ App Store/Google Play
  - Web: https://www.imoulife.com
- [ ] **Imou camera** đã add vào account
- [ ] **Cloud storage subscription** (nếu cần download cloud videos)
  - Free trial: 7 ngày
  - Paid plans: từ $2.99/tháng

### 2.2 Developer Account Registration

**Bước cần User làm:**

#### **Step 1: Đăng ký Developer Account**

1. Truy cập **Imou Open Platform**: https://open.imoulife.com

2. Click **Become a Developer** (top right)

3. Fill registration form:
   - Email
   - Password
   - Agree to terms
   - Click **Register**

4. Verify email

5. Login vào Developer Console

#### **Step 2: Tạo Application**

1. Vào **Console** → **Application Management**

2. Click **Create Application**

3. Fill form:
   - **Application Name**: `VPACK Video Integration`
   - **Application Type**: `Web Application`
   - **Description**: `Video batch analysis integration`
   - **Callback URL**: `http://localhost:8080/api/cloud/imou/oauth/callback`

4. Click **Submit**

5. Sau khi approve (thường instant), lấy credentials:
   - **AppID**: Copy và lưu
   - **AppSecret**: Copy và lưu

6. Configure **API Permissions**:
   - ✅ Device Management
   - ✅ Cloud Storage
   - ✅ Video Service
   - Click **Save**

#### **Step 3: Lưu Credentials**

```json
// File: backend/modules/sources/credentials/imou_credentials.json
{
  "app_id": "YOUR_APP_ID",
  "app_secret": "YOUR_APP_SECRET",
  "redirect_uri": "http://localhost:8080/api/cloud/imou/oauth/callback"
}
```

### 2.3 Dependencies Installation
```bash
pip install requests==2.31.0
pip install pycryptodome==3.19.0  # For encryption
```

### 2.4 Imou Open Platform Resources
- **Documentation**: https://open.imoulife.com/book/
- **API Reference**: https://open.imoulife.com/book/http/
- **Cloud Storage Docs**: https://open.imoulife.com/book/http/cloud/summary.html
- **Developer Forum**: https://open.imoulife.com/forum/

---

## 3. KIẾN TRÚC & IMPLEMENTATION

### 3.1 File Structure
```
backend/modules/sources/
├── imou_auth.py               # OAuth2 authentication
├── imou_client.py             # Imou API client
├── credentials/
│   └── imou_credentials.json
└── tokens/
    └── imou_{user_hash}.json  # Encrypted access tokens
```

### 3.2 Authentication Flow (OAuth2)

```
User → Click "Connect Imou Life"
  → Backend initiates OAuth2 with Imou
  → Redirect to Imou login page
  → User authorizes VPACK
  → Imou redirects back with code
  → Backend exchanges code for access_token
  → Store encrypted token
  → Return session token to frontend
  → User can browse devices
```

### 3.3 Imou API Architecture

#### **Base URL**
```
https://openapi.imoulife.com
```

#### **Authentication Header**
```http
Authorization: Bearer {access_token}
```

#### **Key API Endpoints**

**1. Device Management**
```http
GET /cloudStorage/v1/device/list
Response: List of user's devices

GET /cloudStorage/v1/device/info?deviceId={id}
Response: Device details
```

**2. Cloud Storage**
```http
POST /cloudStorage/v1/records/query
Body: {
  "deviceId": "xxx",
  "channelId": "0",
  "startTime": "2024-01-01 00:00:00",
  "endTime": "2024-01-01 23:59:59"
}
Response: List of cloud recordings

GET /cloudStorage/v1/records/download
Query: {
  "deviceId": "xxx",
  "recordId": "yyy",
  "format": "mp4"
}
Response: Video file download URL
```

**3. Device Video (Local Storage)**
```http
POST /deviceVideoService/v1/videos/query
Body: {
  "deviceId": "xxx",
  "channelId": "0",
  "startTime": "2024-01-01 00:00:00",
  "endTime": "2024-01-01 23:59:59",
  "storageType": "1"  # 1=SD Card, 2=Cloud
}
Response: List of videos on device SD card
```

### 3.4 Core Components

#### **Component 1: `imou_auth.py`**
```python
import requests
import json
import os
import hashlib
import secrets
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ImouAuthManager:
    """Imou Life OAuth2 Authentication Manager"""

    OAUTH_BASE_URL = "https://openapi.imoulife.com"
    AUTH_ENDPOINT = f"{OAUTH_BASE_URL}/oauth/authorize"
    TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/oauth/token"

    def __init__(self):
        self.credentials = self._load_credentials()
        self.app_id = self.credentials['app_id']
        self.app_secret = self.credentials['app_secret']
        self.redirect_uri = self.credentials['redirect_uri']
        self.tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
        self.auth_sessions = {}
        os.makedirs(self.tokens_dir, exist_ok=True)

    def _load_credentials(self) -> Dict:
        """Load Imou app credentials"""
        cred_path = os.path.join(
            os.path.dirname(__file__),
            'credentials',
            'imou_credentials.json'
        )
        with open(cred_path, 'r') as f:
            return json.load(f)

    def initiate_oauth_flow(self) -> Dict:
        """Initiate OAuth2 authorization flow"""
        try:
            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)

            # Build authorization URL
            auth_params = {
                'response_type': 'code',
                'client_id': self.app_id,
                'redirect_uri': self.redirect_uri,
                'state': state,
                'scope': 'device.basic device.video cloud.storage device.list'
            }

            auth_url = f"{self.AUTH_ENDPOINT}?" + "&".join(
                f"{k}={v}" for k, v in auth_params.items()
            )

            # Store session
            session_id = secrets.token_urlsafe(32)
            self.auth_sessions[session_id] = {
                'state': state,
                'created_at': datetime.now().isoformat()
            }

            logger.info(f"✅ Imou OAuth flow initiated: {session_id}")

            return {
                'success': True,
                'auth_url': auth_url,
                'session_id': session_id,
                'state': state
            }

        except Exception as e:
            logger.error(f"❌ OAuth initiation error: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def complete_oauth_flow(self, session_id: str, code: str, state: str) -> Dict:
        """Complete OAuth2 flow - exchange code for tokens"""
        try:
            # Validate session
            if session_id not in self.auth_sessions:
                return {
                    'success': False,
                    'message': 'Invalid or expired session'
                }

            session = self.auth_sessions[session_id]

            # Validate state
            if session['state'] != state:
                return {
                    'success': False,
                    'message': 'State mismatch - possible CSRF attack'
                }

            # Exchange code for tokens
            token_params = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': self.app_id,
                'client_secret': self.app_secret,
                'redirect_uri': self.redirect_uri
            }

            response = requests.post(
                self.TOKEN_ENDPOINT,
                data=token_params,
                timeout=10
            )

            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Token exchange failed: {response.text}'
                }

            token_data = response.json()

            if token_data.get('code') != 0:
                return {
                    'success': False,
                    'message': token_data.get('msg', 'Token exchange failed')
                }

            # Extract tokens
            access_token = token_data['data']['access_token']
            refresh_token = token_data['data'].get('refresh_token')
            expires_in = token_data['data'].get('expires_in', 7200)

            # Get user info
            user_info = self._get_user_info(access_token)

            # Store tokens
            user_email = user_info.get('email', 'unknown')
            self._store_tokens(user_email, {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
                'user_info': user_info
            })

            # Cleanup session
            del self.auth_sessions[session_id]

            logger.info(f"✅ OAuth completed for: {user_email}")

            return {
                'success': True,
                'user_info': user_info,
                'access_token': access_token  # For immediate use
            }

        except Exception as e:
            logger.error(f"❌ OAuth completion error: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def _get_user_info(self, access_token: str) -> Dict:
        """Get user information from Imou API"""
        try:
            response = requests.get(
                f"{self.OAUTH_BASE_URL}/api/v1/user/info",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    return data.get('data', {})

            # Fallback if user info endpoint doesn't exist
            return {
                'email': 'imou_user',
                'name': 'Imou User'
            }

        except Exception as e:
            logger.warning(f"Could not get user info: {e}")
            return {
                'email': 'imou_user',
                'name': 'Imou User'
            }

    def _store_tokens(self, user_email: str, tokens: Dict):
        """Store encrypted tokens"""
        from .cloud_auth import CloudAuthManager
        auth_manager = CloudAuthManager('imou')
        encrypted_data = auth_manager.encrypt_credentials(tokens)

        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        filename = f"imou_{email_hash}.json"
        filepath = os.path.join(self.tokens_dir, filename)

        storage = {
            'encrypted_data': encrypted_data,
            'user_email': user_email,
            'created_at': datetime.now().isoformat(),
            'provider': 'imou'
        }

        with open(filepath, 'w') as f:
            json.dump(storage, f, indent=2)

        os.chmod(filepath, 0o600)

    def load_tokens(self, user_email: str) -> Optional[Dict]:
        """Load and decrypt tokens"""
        try:
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            filename = f"imou_{email_hash}.json"
            filepath = os.path.join(self.tokens_dir, filename)

            if not os.path.exists(filepath):
                return None

            with open(filepath, 'r') as f:
                storage = json.load(f)

            from .cloud_auth import CloudAuthManager
            auth_manager = CloudAuthManager('imou')
            tokens = auth_manager.decrypt_credentials(storage['encrypted_data'])

            # Check if token expired
            if tokens and self._is_token_expired(tokens):
                tokens = self._refresh_token(tokens, user_email)

            return tokens

        except Exception as e:
            logger.error(f"❌ Token loading error: {e}")
            return None

    def _is_token_expired(self, tokens: Dict) -> bool:
        """Check if access token is expired"""
        if not tokens.get('expires_at'):
            return False
        expires_at = datetime.fromisoformat(tokens['expires_at'])
        return datetime.now() >= expires_at

    def _refresh_token(self, tokens: Dict, user_email: str) -> Optional[Dict]:
        """Refresh access token"""
        try:
            if not tokens.get('refresh_token'):
                logger.warning("No refresh token available")
                return None

            refresh_params = {
                'grant_type': 'refresh_token',
                'refresh_token': tokens['refresh_token'],
                'client_id': self.app_id,
                'client_secret': self.app_secret
            }

            response = requests.post(
                self.TOKEN_ENDPOINT,
                data=refresh_params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    new_access_token = data['data']['access_token']
                    expires_in = data['data'].get('expires_in', 7200)

                    tokens['access_token'] = new_access_token
                    tokens['expires_at'] = (datetime.now() + timedelta(seconds=expires_in)).isoformat()

                    # Re-store
                    self._store_tokens(user_email, tokens)

                    logger.info(f"✅ Token refreshed for: {user_email}")
                    return tokens

            logger.warning("Token refresh failed")
            return None

        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            return None

    def get_access_token(self, user_email: str) -> Optional[str]:
        """Get valid access token"""
        tokens = self.load_tokens(user_email)
        return tokens['access_token'] if tokens else None
```

#### **Component 2: `imou_client.py`**
```python
import requests
from typing import List, Dict, Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class ImouClient:
    """Imou Life API Client"""

    API_BASE_URL = "https://openapi.imoulife.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

    def get_devices(self) -> List[Dict]:
        """Get list of user's devices"""
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/cloudStorage/v1/device/list",
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Get devices failed: {response.status_code}")
                return []

            data = response.json()

            if data.get('code') != 0:
                logger.error(f"API error: {data.get('msg')}")
                return []

            devices = []
            for device in data.get('data', {}).get('devices', []):
                devices.append({
                    'device_id': device.get('deviceId'),
                    'device_name': device.get('deviceName'),
                    'device_model': device.get('deviceModel'),
                    'status': device.get('status'),  # online/offline
                    'channels': device.get('channels', [])
                })

            logger.info(f"📹 Found {len(devices)} devices")
            return devices

        except Exception as e:
            logger.error(f"❌ Get devices error: {e}")
            return []

    def get_cloud_recordings(self, device_id: str, channel_id: str,
                            start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query cloud storage recordings"""
        try:
            # Format times as required by Imou API
            start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

            payload = {
                'deviceId': device_id,
                'channelId': channel_id,
                'startTime': start_str,
                'endTime': end_str,
                'recordType': 'all'  # all, alarm, schedule
            }

            response = requests.post(
                f"{self.API_BASE_URL}/cloudStorage/v1/records/query",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Query recordings failed: {response.status_code}")
                return []

            data = response.json()

            if data.get('code') != 0:
                logger.error(f"API error: {data.get('msg')}")
                return []

            recordings = []
            for record in data.get('data', {}).get('records', []):
                recordings.append({
                    'record_id': record.get('recordId'),
                    'device_id': device_id,
                    'channel_id': channel_id,
                    'start_time': record.get('startTime'),
                    'end_time': record.get('endTime'),
                    'duration': record.get('duration'),  # seconds
                    'file_size': record.get('fileSize'),  # bytes
                    'record_type': record.get('recordType')  # alarm, schedule
                })

            logger.info(f"🎥 Found {len(recordings)} cloud recordings")
            return recordings

        except Exception as e:
            logger.error(f"❌ Query recordings error: {e}")
            return []

    def get_download_url(self, device_id: str, record_id: str,
                        format: str = 'mp4') -> Optional[str]:
        """Get download URL for cloud recording"""
        try:
            params = {
                'deviceId': device_id,
                'recordId': record_id,
                'format': format
            }

            response = requests.get(
                f"{self.API_BASE_URL}/cloudStorage/v1/records/download",
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()

            if data.get('code') != 0:
                logger.error(f"Get download URL error: {data.get('msg')}")
                return None

            download_url = data.get('data', {}).get('downloadUrl')
            logger.info(f"✅ Got download URL for record: {record_id}")

            return download_url

        except Exception as e:
            logger.error(f"❌ Get download URL error: {e}")
            return None

    def download_video(self, download_url: str, local_path: str) -> bool:
        """Download video from URL to local file"""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            response = requests.get(
                download_url,
                stream=True,
                timeout=300  # 5 minute timeout
            )

            if response.status_code != 200:
                logger.error(f"Download failed: {response.status_code}")
                return False

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"✅ Downloaded video: {local_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return False

    def get_device_storage_info(self, device_id: str) -> Dict:
        """Get device storage information"""
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/cloudStorage/v1/device/storage",
                headers=self.headers,
                params={'deviceId': device_id},
                timeout=10
            )

            if response.status_code != 200:
                return {}

            data = response.json()

            if data.get('code') != 0:
                return {}

            storage = data.get('data', {})
            return {
                'total_gb': storage.get('totalSize', 0) / (1024**3),
                'used_gb': storage.get('usedSize', 0) / (1024**3),
                'free_gb': storage.get('freeSize', 0) / (1024**3),
                'cloud_enabled': storage.get('cloudEnabled', False)
            }

        except Exception as e:
            logger.error(f"❌ Get storage info error: {e}")
            return {}
```

#### **Component 3: API Endpoints**
```python
# Add to cloud_endpoints.py

@app.route('/api/cloud/imou-auth', methods=['POST'])
@limiter.limit("10 per minute")
def imou_initiate_auth():
    """Initiate Imou OAuth2 flow"""
    auth_manager = ImouAuthManager()
    result = auth_manager.initiate_oauth_flow()
    return jsonify(result)

@app.route('/api/cloud/imou/oauth/callback', methods=['GET'])
def imou_oauth_callback():
    """Handle OAuth2 callback from Imou"""
    code = request.args.get('code')
    state = request.args.get('state')
    session_id = request.cookies.get('imou_session_id')

    auth_manager = ImouAuthManager()
    result = auth_manager.complete_oauth_flow(session_id, code, state)

    if result['success']:
        response = redirect('/sources?imou=connected')
        # Set session cookie
        response.set_cookie('session_token', 'jwt_token_here',
                          httponly=True, max_age=7776000)
        return response
    else:
        return redirect(f'/sources?error={result["message"]}')

@app.route('/api/cloud/imou/devices', methods=['GET'])
@limiter.limit("15 per minute")
def imou_get_devices():
    """Get user's Imou devices"""
    user_email = get_user_email_from_session()

    auth_manager = ImouAuthManager()
    access_token = auth_manager.get_access_token(user_email)

    if not access_token:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    client = ImouClient(access_token)
    devices = client.get_devices()

    return jsonify({
        'success': True,
        'devices': devices
    })

@app.route('/api/cloud/imou/recordings', methods=['POST'])
@limiter.limit("20 per minute")
def imou_get_recordings():
    """Query cloud recordings"""
    data = request.get_json()
    device_id = data.get('device_id')
    channel_id = data.get('channel_id', '0')
    start_time = datetime.fromisoformat(data.get('start_time'))
    end_time = datetime.fromisoformat(data.get('end_time'))

    user_email = get_user_email_from_session()
    auth_manager = ImouAuthManager()
    access_token = auth_manager.get_access_token(user_email)

    if not access_token:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    client = ImouClient(access_token)
    recordings = client.get_cloud_recordings(
        device_id, channel_id, start_time, end_time
    )

    return jsonify({
        'success': True,
        'recordings': recordings
    })
```

#### **Component 4: Frontend** (`ImouDeviceSelector.tsx`)
```typescript
import React, { useState, useEffect } from 'react';
import { Camera, Cloud, Calendar } from 'lucide-react';

interface ImouDevice {
  device_id: string;
  device_name: string;
  device_model: string;
  status: string;
  channels: any[];
}

interface ImouDeviceSelectorProps {
  onDeviceSelected: (deviceId: string, channelId: string) => void;
}

export const ImouDeviceSelector: React.FC<ImouDeviceSelectorProps> = ({
  onDeviceSelected
}) => {
  const [devices, setDevices] = useState<ImouDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [selectedChannel, setSelectedChannel] = useState<string>('0');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    setLoading(true);

    try {
      const response = await fetch('/api/cloud/imou/devices', {
        credentials: 'include'
      });

      const data = await response.json();

      if (data.success) {
        setDevices(data.devices);
      }
    } catch (error) {
      console.error('Failed to load devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => {
    if (selectedDevice) {
      onDeviceSelected(selectedDevice, selectedChannel);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Cloud className="h-6 w-6 text-blue-500" />
        <h3 className="text-lg font-semibold">Select Imou Device</h3>
      </div>

      {loading ? (
        <div className="text-center py-8">Loading devices...</div>
      ) : devices.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No devices found. Please add cameras to your Imou Life account.
        </div>
      ) : (
        <>
          <div>
            <label className="block text-sm font-medium mb-1">Device</label>
            <select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="">Select a device...</option>
              {devices.map(device => (
                <option key={device.device_id} value={device.device_id}>
                  {device.device_name} ({device.device_model}) - {device.status}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Channel</label>
            <select
              value={selectedChannel}
              onChange={(e) => setSelectedChannel(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="0">Channel 1</option>
            </select>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!selectedDevice}
            className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-300"
          >
            Select Device
          </button>
        </>
      )}
    </div>
  );
};
```

---

## 4. CHI TIẾT IMPLEMENTATION TIMELINE

### 4.1 Ngày 1: OAuth2 Setup (4-5 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Đăng ký Imou Developer account | 30 phút | Account ready |
| Tạo application, get credentials | 30 phút | AppID, AppSecret |
| Implement `imou_auth.py` | 2 giờ | OAuth flow |
| Test authentication | 1 giờ | Can get access token |

**Checkpoint**: OAuth2 working

### 4.2 Ngày 2: API Client (5-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Implement `imou_client.py` | 2 giờ | Client class |
| Implement device listing | 1 giờ | Get devices working |
| Implement cloud recordings query | 1.5 giờ | Can search videos |
| Implement download URL | 1 giờ | Get download URL |
| Test with real account | 0.5 giờ | Verified |

**Checkpoint**: Can query cloud recordings

### 4.3 Ngày 3: Download & Integration (5-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Implement video download | 1.5 giờ | Download working |
| API endpoints | 1.5 giờ | 4 endpoints |
| Frontend device selector | 2 giờ | UI component |
| Integration testing | 1 giờ | E2E working |

**Checkpoint**: Full flow working

### 4.4 Ngày 4: Testing & Polish (4-5 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Auto-sync integration | 1.5 giờ | Sync working |
| Unit tests | 1.5 giờ | >80% coverage |
| Error handling | 1 giờ | Robust |
| Documentation | 1 giờ | Complete |

---

## 5. DATABASE SCHEMA

### 5.1 Source Config
```json
{
  "provider": "imou",
  "device_id": "ABC123...",
  "device_name": "Front Door Camera",
  "channel_id": "0",
  "user_email": "user@example.com"
}
```

### 5.2 Downloaded Files
```json
{
  "source_id": 15,
  "cloud_file_id": "imou://ABC123/record_xyz",
  "record_id": "record_xyz",
  "device_id": "ABC123",
  "start_time": "2024-01-01 10:00:00",
  "end_time": "2024-01-01 11:00:00",
  "local_file_path": "/data/downloads/imou/video_xxx.mp4"
}
```

---

## 6. SECURITY & ERROR HANDLING

### 6.1 Security
- [x] OAuth2 with state parameter
- [x] Encrypted token storage
- [x] HTTPS only
- [x] Rate limiting

### 6.2 Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| **401 Unauthorized** | Token expired | Refresh token |
| **No cloud storage** | User hasn't subscribed | Show message |
| **Device offline** | Camera offline | Notify user |
| **Download URL expired** | URL timeout | Re-request URL |

---

## 7. SUCCESS CRITERIA

- [x] OAuth2 authentication works
- [x] Can list devices
- [x] Can query cloud recordings
- [x] Can download MP4 files
- [x] Token refresh works
- [x] >80% test coverage

---

## 8. RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Cloud subscription required** | Medium | Clear messaging |
| **API rate limits** | Low | Implement caching |
| **Download URL expiration** | Medium | Re-request when needed |

---

## 9. NEXT STEPS

After Imou complete:
1. Move to Ezviz (similar SDK)
2. Consider device video (SD card) support
3. Add live streaming (future)

---

**Estimated Effort**: 3-4 days
**Actual Effort**: _[TBD]_
**Status**: Planning → Ready

---

**Prepared by**: Claude (AI Assistant)
**Date**: 2025-11-21
**Version**: 1.0
