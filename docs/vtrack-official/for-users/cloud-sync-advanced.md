# Cloud Sync Advanced Guide

**Google Drive Integration & Auto-Sync Configuration**

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Authentication Methods](#authentication-methods)
4. [OAuth 2.0 Setup](#oauth-20-setup)
5. [Folder Selection](#folder-selection)
6. [Camera Configuration](#camera-configuration)
7. [Auto-Sync Management](#auto-sync-management)
8. [Sync Status Monitoring](#sync-status-monitoring)
9. [Downloaded Files Management](#downloaded-files-management)
10. [Error Handling](#error-handling)
11. [Performance Optimization](#performance-optimization)
12. [Troubleshooting](#troubleshooting)

---

## Overview

V_Track integrates with Google Drive to automatically download and process video files from cloud storage. The system supports lazy folder tree loading, auto-sync scheduling, and robust error recovery.

### Key Features

- **Dual Authentication**: Gmail-only or Full Google Drive access
- **OAuth 2.0 Security**: Encrypted credential storage
- **Lazy Folder Loading**: Performance-optimized tree navigation
- **Auto-Sync**: Scheduled download intervals (2-60 minutes)
- **Camera Auto-Detection**: Automatic folder structure parsing
- **Error Recovery**: Retry logic with exponential backoff
- **Bandwidth Management**: Configurable download speeds

### System Architecture

```
Frontend (Setup Wizard) → Backend OAuth → Google Drive API
                              ↓
                    Encrypted Token Storage
                              ↓
                    Auto-Sync Service (APScheduler)
                              ↓
                    Downloaded Files → Video Processing
```

---

## Prerequisites

### System Requirements

1. **Gmail Account**: Required for authentication
2. **Google Drive Storage**: Video files must be in Google Drive
3. **Internet Connection**: Minimum 5 Mbps for sync
4. **Disk Space**: At least 10GB free for downloads

### OAuth 2.0 Credentials Setup

**For Administrators Only** (End users skip this section)

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project: "VTrack Production"
3. Enable APIs:
   - Google Drive API
   - Google+ API (for userinfo)

#### Step 2: Configure OAuth Consent Screen

1. Navigate to "OAuth consent screen"
2. User Type: External
3. App Information:
   - App name: V_Track
   - User support email: support@vtrack.com
   - Developer contact: dev@vtrack.com
4. Scopes:
   ```
   https://www.googleapis.com/auth/drive.file
   https://www.googleapis.com/auth/drive.readonly
   https://www.googleapis.com/auth/drive.metadata.readonly
   https://www.googleapis.com/auth/userinfo.email
   https://www.googleapis.com/auth/userinfo.profile
   openid
   ```
5. Test users: Add your Gmail addresses

#### Step 3: Create OAuth 2.0 Credentials

1. Navigate to "Credentials"
2. Create OAuth client ID:
   - Application type: Web application
   - Name: V_Track Desktop Client
   - Authorized redirect URIs:
     ```
     http://localhost:8080/api/cloud/oauth/callback
     http://localhost:8080/api/cloud/gmail-callback
     ```
3. Download JSON credentials
4. Save as:
   - Gmail: `backend/modules/sources/credentials/gmail_credentials.json`
   - Drive: `backend/modules/sources/credentials/google_drive_credentials_web.json`

**Credentials Format**:
```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "vtrack-production",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": [
      "http://localhost:8080/api/cloud/oauth/callback"
    ]
  }
}
```

---

## Authentication Methods

V_Track supports two authentication workflows:

### Method 1: Gmail-Only Authentication

**Use Case**: User signup, no Google Drive access needed

**Scopes**:
```python
GMAIL_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
```

**Workflow**:

1. User clicks "Sign Up with Gmail"
2. Frontend calls: `POST /api/cloud/gmail-auth`
3. Backend generates OAuth URL
4. User authenticates via popup
5. Callback: `GET /api/cloud/gmail-callback`
6. Session token created (90 days validity)
7. User profile saved to database

**API Endpoint**: `POST /api/cloud/gmail-auth`

**Request**:
```json
{
  "action": "initiate_auth"
}
```

**Response**:
```json
{
  "success": true,
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "cryptographically_secure_random_state",
  "redirect_uri": "http://localhost:8080/api/cloud/gmail-callback",
  "auth_type": "gmail_only",
  "scopes": ["openid", "..."]
}
```

**Callback Response** (postMessage to parent window):
```javascript
{
  type: 'GMAIL_AUTH_SUCCESS',
  user_info: {
    email: 'user@gmail.com',
    name: 'John Doe',
    photo_url: 'https://...'
  },
  session_token: 'JWT_TOKEN',
  authentication_method: 'gmail_only',
  google_drive_connected: false
}
```

### Method 2: Full Google Drive Authentication

**Use Case**: Video source configuration (Step 3 of setup)

**Scopes**:
```python
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]
```

**Prerequisite Check**:
```python
gmail_authenticated = session.get('gmail_authenticated', False)
if not gmail_authenticated:
    return {
        'error': 'Gmail authentication required before Drive access',
        'action_required': 'complete_gmail_auth_first'
    }
```

**Workflow**:

1. User completes Gmail auth first
2. Navigate to video source setup
3. Click "Connect Google Drive"
4. Frontend calls: `POST /api/cloud/drive-auth`
5. Backend generates OAuth URL with Drive scopes
6. User authenticates via popup
7. Callback: `GET /api/cloud/oauth/callback`
8. Credentials encrypted and stored locally
9. Session token + credentials returned

**API Endpoint**: `POST /api/cloud/drive-auth`

**Response**:
```json
{
  "success": true,
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "cryptographically_secure_random_state",
  "redirect_uri": "http://localhost:8080/api/cloud/oauth/callback",
  "message": "OAuth flow initiated - open popup window"
}
```

**Callback Response** (postMessage):
```javascript
{
  type: 'OAUTH_SUCCESS',
  success: true,
  authenticated: true,
  user_email: 'user@gmail.com',
  user_info: { /* ... */ },
  session_token: 'JWT_TOKEN',
  folders: [],  // Use separate endpoint to load
  folder_loading_required: true,
  lazy_loading_enabled: true,
  authentication_method: 'google_drive',
  google_drive_connected: true,
  backend_port: 8080,
  security_mode: 'encrypted_storage'
}
```

### Security Implementation

#### Encrypted Credential Storage

**Encryption Key** (persistent):
```python
# backend/modules/sources/cloud_auth.py
from cryptography.fernet import Fernet
import os

# Generate once and store in .env
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY') or Fernet.generate_key()
```

**Encryption Process**:
```python
def encrypt_credentials(credentials_dict):
    fernet = Fernet(ENCRYPTION_KEY)
    credentials_json = json.dumps(credentials_dict).encode()
    encrypted_data = fernet.encrypt(credentials_json)
    return base64.b64encode(encrypted_data).decode()

def decrypt_credentials(encrypted_data):
    fernet = Fernet(ENCRYPTION_KEY)
    encrypted_bytes = base64.b64decode(encrypted_data.encode())
    decrypted_data = fernet.decrypt(encrypted_bytes)
    return json.loads(decrypted_data.decode())
```

**Storage Location**:
```
backend/modules/sources/tokens/
  └── google_drive_{email_hash}.json
```

**File Structure**:
```json
{
  "encrypted_data": "gAAAAABh...",
  "user_email": "user@gmail.com",
  "created_at": "2025-01-15T10:00:00Z",
  "encryption_version": "1.0"
}
```

**File Permissions**: `600` (owner read/write only)

#### JWT Session Tokens

**Token Generation**:
```python
import jwt
from datetime import datetime, timedelta

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-in-production')

def generate_session_token(user_email, user_info, expires_minutes=129600):
    """90 days = 129600 minutes"""
    payload = {
        'user_email': user_email,
        'user_name': user_info.get('name'),
        'photo_url': user_info.get('photo_url'),
        'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
        'iat': datetime.utcnow(),
        'iss': 'vtrack-background-service',
        'type': 'session'
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    return token
```

**Token Verification**:
```python
def verify_session_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token
```

**Usage in API Requests**:
```
Authorization: Bearer {session_token}
```

---

## OAuth 2.0 Setup

### OAuth Flow Diagram

```
User → Frontend → Backend → Google OAuth
  |       |          |            |
  |       |    Generate URL       |
  |       |<---------------------|
  |    Popup Window               |
  |---------------------->        |
  |           Authenticate        |
  |<------------------------->    |
  |    Authorization Code         |
  |------------------------------>|
  |       |    Token Exchange     |
  |       |<---------------------|
  |       |  Access + Refresh     |
  |       |    Encrypt & Store    |
  |       |<---------------------|
  |    Session Token (JWT)        |
  |<------------------------------|
```

### State Parameter Security

**CSRF Protection**:
```python
import secrets

# Generate cryptographically secure state
state = secrets.token_urlsafe(32)  # 256-bit entropy

# Store with timestamp
session['oauth2_state'] = state
session['oauth2_state_created'] = datetime.now().isoformat()
session['oauth2_flow_data'] = {
    'scopes': SCOPES,
    'redirect_uri': redirect_uri,
    'csrf_token': secrets.token_hex(16)  # Additional protection
}
```

**State Verification**:
```python
# In callback
stored_state = session.get('oauth2_state')
if not stored_state or state != stored_state:
    return error('State mismatch - possible CSRF attack')

# Clear state after use
session.pop('oauth2_state', None)
```

---

## Folder Selection

### Lazy Folder Tree Loading

V_Track uses lazy loading to handle large Google Drive accounts efficiently.

#### Architecture

```
Root (My Drive)
  ├── Project A (depth=1, not selectable)
  │   ├── Area 1 (depth=2, not selectable)
  │   │   ├── Location X (depth=3, not selectable)
  │   │   │   ├── Cam1 (depth=4, SELECTABLE ✓)
  │   │   │   └── Cam2 (depth=4, SELECTABLE ✓)
  │   │   └── Location Y (depth=3)
  │   └── Area 2 (depth=2)
  └── Project B (depth=1)
```

**Selection Rules**:
- **Selectable Depth**: Level 4 only (camera folders)
- **Reason**: Enforces `Project/Area/Location/Camera` structure
- **Validation**: Backend validates depth before saving

#### List Subfolders API

**Endpoint**: `POST /api/cloud/lazy-folders/list_subfolders`

**Request**:
```json
{
  "parent_id": "folder_id_or_root",
  "max_results": 50,
  "include_stats": false
}
```

**Response**:
```json
{
  "success": true,
  "folders": [
    {
      "id": "1a2b3c4d5e",
      "name": "Cam1",
      "type": "folder",
      "parent_id": "parent_folder_id",
      "depth": 4,
      "selectable": true,
      "has_subfolders": false,
      "created": "2025-01-01T00:00:00Z",
      "modified": "2025-01-15T10:00:00Z",
      "path": "/Project A/Area 1/Location X/Cam1"
    }
  ],
  "parent_info": {
    "id": "parent_folder_id",
    "name": "Location X",
    "depth": 3,
    "path": "/Project A/Area 1/Location X"
  },
  "total_count": 2,
  "has_more": false,
  "cache_info": {
    "cached_folders": 15,
    "cache_size": "2.3 KB"
  },
  "timestamp": "2025-01-15T11:00:00Z"
}
```

#### Folder Service Implementation

**Source**: `backend/modules/sources/google_drive_service.py`

**Key Methods**:

1. **Get Subfolders**:
```python
def get_subfolders(self, parent_id, max_results=50):
    query = f"mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"

    results = self.service.files().list(
        q=query,
        fields="files(id, name, parents, createdTime, modifiedTime)",
        pageSize=max_results,
        orderBy='name'
    ).execute()

    return results.get('files', [])
```

2. **Calculate Folder Depth**:
```python
def calculate_folder_depth(self, folder_id):
    depth = 0
    current_id = folder_id

    while current_id and current_id != 'root' and depth < 10:
        folder_info = self.get_folder_info(current_id)
        parents = folder_info.get('parents', [])
        current_id = parents[0] if parents else 'root'
        depth += 1

    return depth
```

3. **Build Folder Path**:
```python
def build_folder_path(self, folder_id):
    path_parts = []
    current_id = folder_id

    while current_id and current_id != 'root':
        folder_info = self.get_folder_info(current_id)
        path_parts.insert(0, folder_info.get('name', 'Unknown'))

        parents = folder_info.get('parents', [])
        current_id = parents[0] if parents else 'root'

    path_parts.insert(0, 'My Drive')
    return '/' + '/'.join(path_parts)
```

#### Frontend Integration

**React Component** (example):
```typescript
const handleFolderExpand = async (folderId: string) => {
  const response = await fetch('/api/cloud/lazy-folders/list_subfolders', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({
      parent_id: folderId,
      max_results: 50
    })
  });

  const data = await response.json();

  if (data.success) {
    // Update tree state with subfolders
    setFolderTree(prev => ({
      ...prev,
      [folderId]: data.folders
    }));
  }
};
```

#### Folder Validation

**Endpoint**: `POST /api/cloud/lazy-folders/validate_selection`

**Request**:
```json
{
  "folder_ids": ["folder1", "folder2", "folder3"]
}
```

**Response**:
```json
{
  "success": true,
  "valid_selections": [
    {
      "id": "folder1",
      "name": "Cam1",
      "depth": 4,
      "selectable": true,
      "path": "/Project A/Area 1/Location X/Cam1",
      "reason": "Valid camera folder"
    }
  ],
  "invalid_selections": [
    {
      "id": "folder2",
      "name": "Area 1",
      "depth": 2,
      "selectable": false,
      "path": "/Project A/Area 1",
      "reason": "Wrong depth (level 2, need level 4)"
    }
  ],
  "total_valid": 1,
  "total_invalid": 1
}
```

---

## Camera Configuration

### Auto-Detection from Folder Names

V_Track automatically extracts camera names from selected folders.

**Naming Convention**:
```
Acceptable Patterns:
- Cam1, Cam2, Cam3, ...
- Camera1, Camera2, ...
- Cam_01, Cam_02, ...
- Cloud_Cam1, Cloud_Cam2, ...

Extracted Camera Name:
- Folder: "Cam1" → Camera: "Cloud_Cam1" (prefixed)
- Folder: "Camera2" → Camera: "Cloud_Camera2"
```

### Database Storage

#### video_sources Table

```sql
CREATE TABLE video_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK(source_type IN ('local', 'cloud')),
    name TEXT NOT NULL,
    path TEXT NOT NULL,              -- Google Drive folder ID
    config TEXT,                      -- JSON: OAuth tokens, settings
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    folder_depth INTEGER DEFAULT 0,
    parent_folder_id TEXT
);
```

**Example Record**:
```json
{
  "id": 2,
  "source_type": "cloud",
  "name": "Google Drive - Project A",
  "path": "1a2b3c4d5e",  // Root folder ID
  "config": {
    "selected_folders": [
      {
        "id": "folder1",
        "name": "Cam1",
        "path": "/Project A/Area 1/Location X/Cam1",
        "depth": 4
      }
    ],
    "lazy_loading_enabled": true,
    "oauth_token_path": "tokens/google_drive_abc123.json"
  },
  "active": 1,
  "folder_depth": 4,
  "parent_folder_id": "parent123"
}
```

#### camera_configurations Table

```sql
CREATE TABLE camera_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    camera_name TEXT NOT NULL,
    camera_config TEXT,              -- JSON: ROI, processing settings
    is_selected INTEGER DEFAULT 1,
    folder_path TEXT,                -- Google Drive folder ID
    stream_url TEXT,
    resolution TEXT,
    codec TEXT,
    capabilities TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE,
    UNIQUE(source_id, camera_name)
);
```

**Example Record**:
```json
{
  "id": 1,
  "source_id": 2,
  "camera_name": "Cloud_Cam1",
  "camera_config": {
    "roi": null,  // Not configured yet
    "processing_enabled": true,
    "detection_threshold": 0.5
  },
  "is_selected": 1,
  "folder_path": "folder1",  // Google Drive folder ID
  "resolution": "1920x1080",
  "codec": "h264"
}
```

### Active Cameras View

**Purpose**: Single source of truth for active cameras

```sql
CREATE VIEW active_cameras AS
SELECT
    vs.id as source_id,
    vs.name as source_name,
    vs.source_type,
    vs.path as source_path,
    cc.camera_name,
    cc.folder_path,
    cc.stream_url,
    cc.resolution,
    cc.codec,
    cc.capabilities,
    cc.is_selected
FROM video_sources vs
LEFT JOIN camera_configurations cc ON vs.id = cc.source_id
WHERE vs.active = 1 AND cc.is_selected = 1;
```

**Query Usage**:
```sql
-- Get all active cameras
SELECT DISTINCT camera_name FROM active_cameras ORDER BY camera_name;
```

---

## Auto-Sync Management

### Sync Configuration

**Database Table**: `sync_status`

```sql
CREATE TABLE sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    sync_enabled INTEGER DEFAULT 1,
    last_sync_timestamp TEXT,
    next_sync_timestamp TEXT,
    sync_interval_minutes INTEGER DEFAULT 10,
    last_sync_status TEXT DEFAULT 'pending',
    last_sync_message TEXT,
    files_downloaded_count INTEGER DEFAULT 0,
    total_download_size_mb REAL DEFAULT 0.0,
    error_severity TEXT,
    error_type TEXT,
    last_timer_run TEXT,
    timer_error_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error_type TEXT DEFAULT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE,
    UNIQUE(source_id)
);
```

### Sync Intervals

**Configurable Options**:
```python
SYNC_INTERVALS = {
    'fast': 2,      # 2 minutes (testing)
    'normal': 10,   # 10 minutes (recommended)
    'slow': 30,     # 30 minutes
    'hourly': 60    # 1 hour
}
```

**Default**: 10 minutes (normal)

### APScheduler Integration

**Source**: `backend/modules/sources/auto_sync_service.py`

**Scheduler Setup**:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

def schedule_auto_sync(source_id, interval_minutes=10):
    """Schedule auto-sync for a cloud source"""

    job_id = f"sync_source_{source_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add new scheduled job
    scheduler.add_job(
        func=sync_cloud_source,
        trigger='interval',
        minutes=interval_minutes,
        id=job_id,
        args=[source_id],
        next_run_time=datetime.now() + timedelta(seconds=30)  # First run after 30s
    )

    logger.info(f"✅ Auto-sync scheduled for source {source_id}: every {interval_minutes} minutes")
```

**Sync Function**:
```python
def sync_cloud_source(source_id):
    """Download new files from Google Drive"""
    try:
        logger.info(f"🔄 Starting auto-sync for source {source_id}")

        # Update sync status
        update_sync_status(source_id, 'in_progress', 'Downloading files...')

        # Get camera configurations
        cameras = get_cameras_for_source(source_id)

        total_downloaded = 0
        for camera in cameras:
            # Download new files
            new_files = download_camera_files(source_id, camera)
            total_downloaded += len(new_files)

        # Update sync status
        update_sync_status(
            source_id,
            'success',
            f'Downloaded {total_downloaded} files',
            files_count=total_downloaded
        )

        logger.info(f"✅ Auto-sync completed: {total_downloaded} files")

    except Exception as e:
        logger.error(f"❌ Auto-sync failed: {e}")
        update_sync_status(source_id, 'error', str(e))
```

### Sync Status Update

```python
def update_sync_status(source_id, status, message, **kwargs):
    """Update sync status in database"""
    from datetime import datetime, timedelta

    with safe_db_connection() as conn:
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Calculate next sync time
        interval_minutes = kwargs.get('interval_minutes', 10)
        next_sync = (datetime.now() + timedelta(minutes=interval_minutes)).isoformat()

        cursor.execute("""
            UPDATE sync_status SET
                last_sync_timestamp = ?,
                next_sync_timestamp = ?,
                last_sync_status = ?,
                last_sync_message = ?,
                files_downloaded_count = files_downloaded_count + ?,
                updated_at = ?
            WHERE source_id = ?
        """, (
            now,
            next_sync,
            status,
            message,
            kwargs.get('files_count', 0),
            now,
            source_id
        ))

        conn.commit()
```

---

## Sync Status Monitoring

### Sync Dashboard View

**SQL View**:
```sql
CREATE VIEW sync_dashboard AS
SELECT
    vs.id as source_id,
    vs.name as source_name,
    vs.source_type,
    vs.path as source_path,
    ss.sync_enabled,
    ss.last_sync_timestamp,
    ss.next_sync_timestamp,
    ss.sync_interval_minutes,
    ss.last_sync_status,
    ss.last_sync_message,
    ss.files_downloaded_count,
    ss.total_download_size_mb,
    COUNT(df.id) as total_downloaded_files,
    SUM(df.file_size_bytes) / (1024*1024) as total_size_mb_calculated
FROM video_sources vs
LEFT JOIN sync_status ss ON vs.id = ss.source_id
LEFT JOIN downloaded_files df ON vs.id = df.source_id
WHERE vs.active = 1 AND vs.source_type = 'cloud'
GROUP BY vs.id, vs.name, vs.source_type, vs.path, ss.sync_enabled,
         ss.last_sync_timestamp, ss.next_sync_timestamp, ss.sync_interval_minutes,
         ss.last_sync_status, ss.last_sync_message, ss.files_downloaded_count, ss.total_download_size_mb;
```

### API Endpoint

**Endpoint**: `GET /api/cloud/sync-status/<source_id>`

**Response**:
```json
{
  "success": true,
  "source_id": 2,
  "source_name": "Google Drive - Project A",
  "sync_enabled": true,
  "last_sync_timestamp": "2025-01-15T10:30:00Z",
  "next_sync_timestamp": "2025-01-15T10:40:00Z",
  "sync_interval_minutes": 10,
  "last_sync_status": "success",
  "last_sync_message": "Downloaded 5 files",
  "files_downloaded_count": 125,
  "total_download_size_mb": 1250.5,
  "cameras": [
    {
      "camera_name": "Cloud_Cam1",
      "last_filename": "video_20250115_103000.mp4",
      "last_file_timestamp": "2025-01-15T10:30:00Z",
      "total_files": 65,
      "total_size_mb": 650.2
    }
  ]
}
```

---

## Downloaded Files Management

### Database Table

```sql
CREATE TABLE downloaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    camera_name TEXT NOT NULL,
    original_filename TEXT,
    local_file_path TEXT NOT NULL,
    file_size_bytes INTEGER DEFAULT 0,
    download_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    recording_start_time TEXT,
    recording_end_time TEXT,
    file_format TEXT,
    checksum TEXT,
    sync_batch_id TEXT,
    is_processed INTEGER DEFAULT 0,
    drive_file_id TEXT,                 -- Google Drive file ID
    relative_path TEXT,                 -- Path within camera folder
    processing_timestamp TEXT,
    processing_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE
);
```

### File Download Process

**Source**: `backend/modules/sources/pydrive_downloader.py`

**Workflow**:

1. **List Files**:
```python
def list_camera_files(self, folder_id):
    """List video files in camera folder"""
    file_list = self.drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false",
        'orderBy': 'createdDate'
    }).GetList()

    video_files = [
        f for f in file_list
        if f['mimeType'].startswith('video/')
    ]

    return video_files
```

2. **Check Already Downloaded**:
```python
def is_file_downloaded(self, drive_file_id):
    """Check if file already downloaded"""
    with safe_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM downloaded_files
            WHERE drive_file_id = ?
        """, (drive_file_id,))

        count = cursor.fetchone()[0]
        return count > 0
```

3. **Download File**:
```python
def download_file(self, drive_file, camera_name, source_id):
    """Download file from Google Drive"""

    # Skip if already downloaded
    if self.is_file_downloaded(drive_file['id']):
        logger.info(f"⏭️ Skipping already downloaded: {drive_file['title']}")
        return None

    # Determine local path
    local_dir = os.path.join(
        INPUT_VIDEO_DIR,
        f"source_{source_id}",
        camera_name
    )
    os.makedirs(local_dir, exist_ok=True)

    local_path = os.path.join(local_dir, drive_file['title'])

    # Download
    logger.info(f"⬇️ Downloading: {drive_file['title']} ({drive_file['fileSize']} bytes)")

    start_time = time.time()
    drive_file.GetContentFile(local_path)
    download_time = time.time() - start_time

    # Record in database
    record_downloaded_file(
        source_id=source_id,
        camera_name=camera_name,
        original_filename=drive_file['title'],
        local_file_path=local_path,
        file_size_bytes=int(drive_file['fileSize']),
        drive_file_id=drive_file['id'],
        download_time=download_time
    )

    logger.info(f"✅ Downloaded: {drive_file['title']} in {download_time:.2f}s")

    return local_path
```

### Cleanup Strategy

**Old Files Removal**:
```python
def cleanup_old_downloads(days=7):
    """Remove files older than N days"""
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    with safe_db_connection() as conn:
        cursor = conn.cursor()

        # Get old files
        cursor.execute("""
            SELECT local_file_path FROM downloaded_files
            WHERE download_timestamp < ? AND is_processed = 1
        """, (cutoff_date,))

        old_files = cursor.fetchall()

        # Delete files
        for (file_path,) in old_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Deleted old file: {file_path}")

        # Delete database records
        cursor.execute("""
            DELETE FROM downloaded_files
            WHERE download_timestamp < ? AND is_processed = 1
        """, (cutoff_date,))

        conn.commit()
        logger.info(f"✅ Cleaned up {len(old_files)} old files")
```

---

## Error Handling

### Error Types

**Database Table**: `sync_status.error_type`

```python
ERROR_TYPES = {
    'auth_expired': 'OAuth token expired',
    'quota_exceeded': 'Google Drive API quota exceeded',
    'network_error': 'Network connection failed',
    'permission_denied': 'Insufficient Google Drive permissions',
    'folder_not_found': 'Camera folder not found',
    'disk_full': 'Local disk space full',
    'download_failed': 'File download failed'
}
```

### Retry Logic

**Exponential Backoff**:
```python
def download_with_retry(drive_file, max_retries=3):
    """Download with exponential backoff"""

    for attempt in range(max_retries):
        try:
            drive_file.GetContentFile(local_path)
            return True

        except Exception as e:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"⚠️ Download failed (attempt {attempt+1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ Download failed after {max_retries} attempts")
                raise
```

### Error Recovery

**Auto-Recovery Actions**:

1. **Token Refresh**:
```python
def refresh_credentials_if_expired(credentials):
    """Auto-refresh OAuth tokens"""
    if credentials.access_token_expired:
        logger.info("🔄 Refreshing expired OAuth token...")

        import httplib2
        http = httplib2.Http()
        credentials.refresh(http)

        # Update stored credentials
        save_refreshed_credentials(credentials)

        logger.info("✅ OAuth token refreshed successfully")

    return credentials
```

2. **Quota Management**:
```python
def handle_quota_exceeded():
    """Handle Google Drive API quota exceeded"""
    logger.warning("⚠️ Google Drive API quota exceeded")

    # Increase sync interval temporarily
    update_sync_interval(source_id, interval_minutes=60)

    # Schedule quota reset check
    scheduler.add_job(
        func=check_quota_reset,
        trigger='interval',
        hours=1,
        id=f'quota_check_{source_id}'
    )
```

---

## Performance Optimization

### Bandwidth Management

**Rate Limiting**:
```python
class BandwidthThrottler:
    """Limit download speed to avoid network congestion"""

    def __init__(self, max_speed_mbps=5):
        self.max_speed_bytes_per_sec = max_speed_mbps * 1024 * 1024 / 8
        self.last_download_time = time.time()
        self.bytes_downloaded = 0

    def throttle(self, chunk_size):
        """Throttle download based on speed limit"""
        self.bytes_downloaded += chunk_size

        elapsed = time.time() - self.last_download_time
        expected_time = self.bytes_downloaded / self.max_speed_bytes_per_sec

        if expected_time > elapsed:
            sleep_time = expected_time - elapsed
            time.sleep(sleep_time)
```

### Caching Strategy

**Folder Structure Cache**:
```python
class FolderCache:
    """Cache folder structure to reduce API calls"""

    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, folder_id):
        """Get cached folder data"""
        if folder_id in self.cache:
            cached_item = self.cache[folder_id]
            if time.time() < cached_item['expires_at']:
                return cached_item['data']
            else:
                del self.cache[folder_id]
        return None

    def set(self, folder_id, data):
        """Cache folder data"""
        self.cache[folder_id] = {
            'data': data,
            'expires_at': time.time() + self.ttl
        }
```

### Parallel Downloads

**Thread Pool**:
```python
from concurrent.futures import ThreadPoolExecutor

def download_files_parallel(file_list, max_workers=3):
    """Download multiple files in parallel"""

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_file, drive_file)
            for drive_file in file_list
        ]

        results = []
        for future in futures:
            try:
                result = future.result(timeout=300)  # 5 min timeout
                results.append(result)
            except Exception as e:
                logger.error(f"Parallel download failed: {e}")

        return results
```

---

## Troubleshooting

### Common Issues

#### 1. "No valid Google Drive credentials found"

**Cause**: Session token expired or OAuth tokens not found

**Solutions**:
1. Re-authenticate via "Connect Google Drive"
2. Check token file exists: `backend/modules/sources/tokens/`
3. Verify encryption key matches in `.env`

#### 2. "Folder not found" or "Permission denied"

**Cause**: Folder deleted/moved or insufficient permissions

**Solutions**:
1. Verify folder exists in Google Drive
2. Check folder permissions (must be owner or have edit access)
3. Re-select folders in video source configuration

#### 3. "Sync not running"

**Cause**: APScheduler not started or job removed

**Diagnostics**:
```python
# Check scheduled jobs
from modules.sources.auto_sync_service import scheduler

jobs = scheduler.get_jobs()
for job in jobs:
    print(f"Job ID: {job.id}, Next Run: {job.next_run_time}")
```

**Solutions**:
1. Restart backend server
2. Re-enable auto-sync in settings
3. Check logs for scheduler errors

#### 4. "Download failed" or "Network timeout"

**Cause**: Network issues or large file sizes

**Solutions**:
1. Check internet connection
2. Increase timeout in downloader:
   ```python
   drive_file.GetContentFile(local_path, timeout=600)  # 10 min
   ```
3. Enable retry logic (automatic)

#### 5. "Disk space full"

**Cause**: Downloaded files consuming all disk space

**Solutions**:
1. Check disk usage: `df -h`
2. Run cleanup script:
   ```python
   from modules.sources.staging_cleanup import cleanup_old_downloads
   cleanup_old_downloads(days=3)
   ```
3. Configure auto-cleanup in settings

---

## Best Practices

### 1. Folder Structure Organization

**Recommended Hierarchy**:
```
My Drive/
└── V_Track Projects/
    └── Warehouse A/
        └── Packing Area 1/
            └── Zone East/
                ├── Cam1/  ← Select this (depth 4)
                │   ├── video1.mp4
                │   └── video2.mp4
                └── Cam2/  ← Select this (depth 4)
                    └── video3.mp4
```

### 2. File Naming Conventions

**Recommended Formats**:
```
video_YYYYMMDD_HHMMSS.mp4
cam1_20250115_103045.mp4
recording_2025-01-15T10-30-45.mp4
```

**Avoid**:
- Special characters: `#`, `@`, `%`, `&`
- Spaces (use underscores instead)
- Very long names (> 100 characters)

### 3. Sync Interval Selection

| Scenario | Recommended Interval | Reason |
|----------|---------------------|--------|
| Testing | 2 minutes | Quick feedback |
| Production (active) | 10 minutes | Balance speed/quota |
| Production (archival) | 60 minutes | Reduce API calls |
| Low bandwidth | 30 minutes | Network congestion |

### 4. Bandwidth Optimization

- **Peak Hours**: Increase interval to 30-60 minutes
- **Off-Hours**: Decrease to 10 minutes for faster sync
- **Large Files**: Enable parallel downloads (max 3 concurrent)

### 5. Security Best Practices

- **Encryption Key**: Store in `.env`, never commit to git
- **Token Files**: Set permissions to `600` (owner only)
- **OAuth Scopes**: Request minimum required scopes
- **Session Tokens**: Rotate every 90 days (automatic)

---

## Next Steps

- **[Trace Tracking Guide](./trace-tracking.md)**: Search and analyze events
- **[License Management](./license-payment.md)**: Activate subscription
- **[API Reference](../api/cloud-endpoints.md)**: Developer documentation

---

**Last Updated**: 2025-10-06
**Version**: 1.0.0
**Author**: V_Track Documentation Team
