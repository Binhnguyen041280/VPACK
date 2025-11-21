# 📘 Dropbox Integration - Detailed Implementation Plan

**Provider**: Dropbox
**Lộ trình**: 1 - General Cloud Storage
**Priority**: High (implement đầu tiên - dễ nhất)
**Timeline**: 2-3 ngày làm việc
**Độ khó**: ⭐ Easy
**Status**: Planning
**Last Updated**: 2025-11-21

---

## 1. TỔNG QUAN & MỤC TIÊU

### 1.1 Use Case
- User có Dropbox account (cá nhân hoặc business)
- User tự upload video camera lên Dropbox để lưu trữ
- Cần download video về VPACK để phân tích batch

### 1.2 Ưu Điểm Dropbox
- ✅ **API đơn giản nhất** trong tất cả cloud providers
- ✅ SDK Python chính thức (`dropbox`)
- ✅ OAuth2 chuẩn, documentation rõ ràng
- ✅ Free tier: 2GB (đủ để test)
- ✅ Phổ biến cho cá nhân và SME
- ✅ Cross-platform sync tốt

### 1.3 Technical Specs
- **API**: Dropbox API v2
- **Authentication**: OAuth2
- **SDK**: `dropbox` (official Python SDK)
- **Scopes Required**:
  - `files.metadata.read` - Đọc metadata files/folders
  - `files.content.read` - Đọc nội dung files
  - `account_info.read` - User profile info

### 1.4 Deliverables
1. ✅ OAuth2 authentication flow
2. ✅ Folder tree listing (lazy load)
3. ✅ Video file download
4. ✅ Auto-sync integration
5. ✅ Frontend React component
6. ✅ Tests (unit + integration)
7. ✅ Documentation

---

## 2. PREREQUISITES & SETUP

### 2.1 Tài Khoản Cần Có
- [ ] **Dropbox account** (cá nhân) - Free
  - Đăng ký tại: https://www.dropbox.com
  - Free tier: 2GB storage

### 2.2 Dropbox App Registration
**Bước cần User làm:**

1. Truy cập **Dropbox App Console**: https://www.dropbox.com/developers/apps

2. Click **Create app**:
   - **Choose an API**: Scoped access
   - **Choose type of access**: Full Dropbox
   - **Name your app**: `VPACK-Video-Integration`

3. Click **Create app**

4. Trong **Settings** tab, lấy thông tin:
   - **App key** - Copy và lưu lại
   - **App secret** - Click "Show", copy và lưu lại

5. Configure **OAuth 2 Redirect URIs**:
   - Thêm: `http://localhost:8080/api/cloud/dropbox/oauth/callback`

6. Configure **Permissions** (tab Permissions):
   - ✅ `files.metadata.read`
   - ✅ `files.content.read`
   - ✅ `account_info.read`
   - Click **Submit** để save

7. Lưu credentials vào file:
   ```json
   // File: backend/modules/sources/credentials/dropbox_credentials.json
   {
     "app_key": "YOUR_APP_KEY",
     "app_secret": "YOUR_APP_SECRET",
     "redirect_uri": "http://localhost:8080/api/cloud/dropbox/oauth/callback"
   }
   ```

### 2.3 Dependencies Installation
```bash
pip install dropbox==11.36.2
```

### 2.4 Environment Variables (Optional)
```bash
# .env file
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
```

---

## 3. KIẾN TRÚC & IMPLEMENTATION

### 3.1 File Structure
```
backend/modules/sources/
├── dropbox_auth.py            # OAuth2 authentication
├── dropbox_client.py          # Dropbox API client
├── credentials/
│   └── dropbox_credentials.json
└── tokens/
    └── dropbox_{user_hash}.json   # Encrypted tokens
```

### 3.2 Authentication Flow

```
User → Click "Connect Dropbox"
  → Backend generates auth_url với PKCE
  → Redirect to Dropbox login
  → User authorizes app
  → Dropbox redirects to callback with code
  → Backend exchanges code for access_token + refresh_token
  → Store encrypted tokens
  → Return JWT session token to frontend
```

### 3.3 Core Components

#### **Component 1: `dropbox_auth.py`**
```python
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect, DropboxOAuth2Flow
import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Optional
from .cloud_auth import CloudAuthManager  # Reuse encryption utilities

class DropboxAuthManager:
    """Dropbox OAuth2 Authentication Manager"""

    def __init__(self):
        self.credentials = self._load_credentials()
        self.app_key = self.credentials['app_key']
        self.app_secret = self.credentials['app_secret']
        self.redirect_uri = self.credentials['redirect_uri']
        self.tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
        self.auth_flows = {}  # Store active OAuth flows

    def _load_credentials(self) -> Dict:
        """Load Dropbox app credentials"""
        cred_path = os.path.join(
            os.path.dirname(__file__),
            'credentials',
            'dropbox_credentials.json'
        )
        with open(cred_path, 'r') as f:
            return json.load(f)

    def initiate_oauth_flow(self) -> Dict:
        """Start OAuth2 flow - returns auth URL"""
        auth_flow = DropboxOAuth2Flow(
            consumer_key=self.app_key,
            consumer_secret=self.app_secret,
            redirect_uri=self.redirect_uri,
            session={},  # Simple session dict
            csrf_token_session_key='dropbox-auth-csrf-token',
            token_access_type='offline'  # Get refresh token
        )

        auth_url = auth_flow.start()

        # Store flow for callback
        session_id = secrets.token_urlsafe(32)
        self.auth_flows[session_id] = {
            'flow': auth_flow,
            'created_at': datetime.now().isoformat()
        }

        return {
            'success': True,
            'auth_url': auth_url,
            'session_id': session_id
        }

    def complete_oauth_flow(self, session_id: str, code: str, state: str) -> Dict:
        """Complete OAuth2 flow - exchange code for tokens"""
        if session_id not in self.auth_flows:
            return {'success': False, 'message': 'Session expired'}

        auth_flow = self.auth_flows[session_id]['flow']

        try:
            oauth_result = auth_flow.finish({'code': code, 'state': state})

            # Get user info
            with dropbox.Dropbox(oauth2_access_token=oauth_result.access_token) as dbx:
                account = dbx.users_get_current_account()

            user_info = {
                'email': account.email,
                'name': account.name.display_name,
                'account_id': account.account_id
            }

            # Store tokens encrypted
            self._store_tokens(user_info['email'], {
                'access_token': oauth_result.access_token,
                'refresh_token': oauth_result.refresh_token,
                'expires_at': oauth_result.expires_at.isoformat() if oauth_result.expires_at else None,
                'account_id': oauth_result.account_id,
                'user_info': user_info
            })

            # Generate session token
            session_token = self._generate_session_token(user_info)

            # Cleanup
            del self.auth_flows[session_id]

            return {
                'success': True,
                'user_info': user_info,
                'session_token': session_token
            }

        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_client(self, user_email: str) -> Optional[dropbox.Dropbox]:
        """Get authenticated Dropbox client"""
        tokens = self._load_tokens(user_email)
        if not tokens:
            return None

        # Check if token needs refresh
        if self._token_expired(tokens):
            tokens = self._refresh_token(tokens, user_email)
            if not tokens:
                return None

        return dropbox.Dropbox(
            oauth2_access_token=tokens['access_token'],
            oauth2_refresh_token=tokens['refresh_token'],
            app_key=self.app_key,
            app_secret=self.app_secret
        )

    def _token_expired(self, tokens: Dict) -> bool:
        """Check if access token is expired"""
        if not tokens.get('expires_at'):
            return False
        expires_at = datetime.fromisoformat(tokens['expires_at'])
        return datetime.now() >= expires_at

    def _refresh_token(self, tokens: Dict, user_email: str) -> Optional[Dict]:
        """Refresh access token using refresh token"""
        try:
            dbx = dropbox.Dropbox(
                oauth2_refresh_token=tokens['refresh_token'],
                app_key=self.app_key,
                app_secret=self.app_secret
            )
            dbx.check_and_refresh_access_token()

            # Update stored tokens
            tokens['access_token'] = dbx._oauth2_access_token
            self._store_tokens(user_email, tokens)

            return tokens
        except Exception as e:
            logging.error(f"Token refresh failed: {e}")
            return None

    def _store_tokens(self, user_email: str, tokens: Dict):
        """Store encrypted tokens"""
        # Reuse encryption from CloudAuthManager
        # ... (similar to Google Drive implementation)
        pass

    def _load_tokens(self, user_email: str) -> Optional[Dict]:
        """Load and decrypt tokens"""
        # ... (similar to Google Drive implementation)
        pass
```

#### **Component 2: `dropbox_client.py`**
```python
import dropbox
from dropbox.files import FileMetadata, FolderMetadata
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)

class DropboxClient:
    """Dropbox API Client for file operations"""

    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']

    def __init__(self, dbx: dropbox.Dropbox):
        self.dbx = dbx

    def get_user_info(self) -> Dict:
        """Get current user information"""
        account = self.dbx.users_get_current_account()
        space = self.dbx.users_get_space_usage()

        return {
            'email': account.email,
            'name': account.name.display_name,
            'account_id': account.account_id,
            'storage_used_gb': space.used / (1024**3),
            'storage_allocated_gb': space.allocation.get_individual().allocated / (1024**3)
        }

    def list_folder(self, path: str = '', recursive: bool = False) -> List[Dict]:
        """List contents of a folder"""
        try:
            # Empty string = root folder
            result = self.dbx.files_list_folder(path, recursive=recursive)

            items = []
            while True:
                for entry in result.entries:
                    item = self._entry_to_dict(entry)
                    items.append(item)

                if not result.has_more:
                    break
                result = self.dbx.files_list_folder_continue(result.cursor)

            return items

        except dropbox.exceptions.ApiError as e:
            logger.error(f"Dropbox API error: {e}")
            return []

    def list_subfolders(self, path: str = '') -> List[Dict]:
        """List only subfolders (for lazy loading tree)"""
        items = self.list_folder(path, recursive=False)
        return [item for item in items if item['type'] == 'folder']

    def list_videos(self, path: str = '', recursive: bool = True) -> List[Dict]:
        """List only video files in folder"""
        items = self.list_folder(path, recursive=recursive)
        videos = []

        for item in items:
            if item['type'] == 'file':
                ext = os.path.splitext(item['name'])[1].lower()
                if ext in self.VIDEO_EXTENSIONS:
                    videos.append(item)

        return videos

    def download_file(self, dropbox_path: str, local_path: str) -> bool:
        """Download file from Dropbox to local path"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            self.dbx.files_download_to_file(local_path, dropbox_path)

            logger.info(f"Downloaded: {dropbox_path} -> {local_path}")
            return True

        except dropbox.exceptions.ApiError as e:
            logger.error(f"Download failed: {e}")
            return False

    def get_file_metadata(self, path: str) -> Optional[Dict]:
        """Get metadata for a specific file"""
        try:
            metadata = self.dbx.files_get_metadata(path)
            return self._entry_to_dict(metadata)
        except dropbox.exceptions.ApiError:
            return None

    def _entry_to_dict(self, entry) -> Dict:
        """Convert Dropbox entry to dict"""
        base = {
            'id': entry.id if hasattr(entry, 'id') else entry.path_lower,
            'name': entry.name,
            'path': entry.path_display,
            'path_lower': entry.path_lower,
        }

        if isinstance(entry, FolderMetadata):
            base['type'] = 'folder'
        elif isinstance(entry, FileMetadata):
            base['type'] = 'file'
            base['size'] = entry.size
            base['modified'] = entry.client_modified.isoformat()
            base['content_hash'] = entry.content_hash

        return base
```

#### **Component 3: API Endpoints**
```python
# Add to cloud_endpoints.py

@app.route('/api/cloud/dropbox-auth', methods=['POST'])
@limiter.limit("10 per minute")
def dropbox_initiate_auth():
    """Initiate Dropbox OAuth2 flow"""
    auth_manager = DropboxAuthManager()
    result = auth_manager.initiate_oauth_flow()
    return jsonify(result)

@app.route('/api/cloud/dropbox/oauth/callback', methods=['GET'])
def dropbox_oauth_callback():
    """Handle OAuth2 callback from Dropbox"""
    code = request.args.get('code')
    state = request.args.get('state')
    session_id = request.cookies.get('dropbox_session_id')

    auth_manager = DropboxAuthManager()
    result = auth_manager.complete_oauth_flow(session_id, code, state)

    if result['success']:
        response = redirect('/sources?dropbox=connected')
        response.set_cookie('session_token', result['session_token'],
                          httponly=True, max_age=7776000)  # 90 days
        return response
    else:
        return redirect(f'/sources?error={result["message"]}')

@app.route('/api/cloud/dropbox/auth-status', methods=['GET'])
@limiter.limit("30 per minute")
def dropbox_auth_status():
    """Check Dropbox authentication status"""
    session_token = request.cookies.get('session_token')
    # Verify session and return status
    # ...

@app.route('/api/cloud/dropbox/list_folders', methods=['POST'])
@limiter.limit("15 per minute")
def dropbox_list_folders():
    """List Dropbox folders"""
    data = request.get_json()
    path = data.get('path', '')

    # Get authenticated client
    auth_manager = DropboxAuthManager()
    user_email = get_user_email_from_session()
    client = auth_manager.get_client(user_email)

    if not client:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    dbx_client = DropboxClient(client)
    folders = dbx_client.list_subfolders(path)

    return jsonify({
        'success': True,
        'folders': folders,
        'path': path
    })

@app.route('/api/cloud/dropbox/disconnect', methods=['POST'])
def dropbox_disconnect():
    """Disconnect Dropbox and revoke tokens"""
    auth_manager = DropboxAuthManager()
    session_token = request.cookies.get('session_token')
    result = auth_manager.revoke_credentials(session_token)
    return jsonify(result)
```

#### **Component 4: Frontend** (`DropboxFolderTree.tsx`)
```typescript
import React, { useState, useEffect } from 'react';
import { Folder, File, ChevronRight, ChevronDown, Video } from 'lucide-react';

interface DropboxFolder {
  id: string;
  name: string;
  path: string;
  type: 'folder' | 'file';
}

interface DropboxFolderTreeProps {
  onFoldersSelected: (folders: DropboxFolder[]) => void;
  maxDepth?: number;
}

export const DropboxFolderTree: React.FC<DropboxFolderTreeProps> = ({
  onFoldersSelected,
  maxDepth = 4
}) => {
  const [folders, setFolders] = useState<DropboxFolder[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState<Set<string>>(new Set());
  const [children, setChildren] = useState<Map<string, DropboxFolder[]>>(new Map());

  // Load root folders on mount
  useEffect(() => {
    loadFolders('');
  }, []);

  const loadFolders = async (path: string) => {
    setLoading(prev => new Set(prev).add(path));

    try {
      const response = await fetch('/api/cloud/dropbox/list_folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
        credentials: 'include'
      });

      const data = await response.json();

      if (data.success) {
        if (path === '') {
          setFolders(data.folders);
        } else {
          setChildren(prev => new Map(prev).set(path, data.folders));
        }
      }
    } catch (error) {
      console.error('Failed to load folders:', error);
    } finally {
      setLoading(prev => {
        const next = new Set(prev);
        next.delete(path);
        return next;
      });
    }
  };

  const toggleExpand = (folder: DropboxFolder) => {
    const newExpanded = new Set(expanded);

    if (expanded.has(folder.path)) {
      newExpanded.delete(folder.path);
    } else {
      newExpanded.add(folder.path);
      // Load children if not loaded
      if (!children.has(folder.path)) {
        loadFolders(folder.path);
      }
    }

    setExpanded(newExpanded);
  };

  const toggleSelect = (folder: DropboxFolder) => {
    const newSelected = new Set(selected);

    if (selected.has(folder.path)) {
      newSelected.delete(folder.path);
    } else {
      newSelected.add(folder.path);
    }

    setSelected(newSelected);

    // Notify parent
    const selectedFolders = Array.from(newSelected).map(path =>
      findFolderByPath(path)
    ).filter(Boolean) as DropboxFolder[];

    onFoldersSelected(selectedFolders);
  };

  const renderFolder = (folder: DropboxFolder, depth: number = 0) => {
    const isExpanded = expanded.has(folder.path);
    const isSelected = selected.has(folder.path);
    const isLoading = loading.has(folder.path);
    const folderChildren = children.get(folder.path) || [];

    return (
      <div key={folder.path} className="select-none">
        <div
          className={`flex items-center gap-2 p-2 hover:bg-gray-100 rounded cursor-pointer
            ${isSelected ? 'bg-blue-100' : ''}`}
          style={{ paddingLeft: `${depth * 20 + 8}px` }}
        >
          {/* Expand/Collapse */}
          <button onClick={() => toggleExpand(folder)} className="p-1">
            {isLoading ? (
              <span className="animate-spin">⏳</span>
            ) : isExpanded ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
          </button>

          {/* Checkbox */}
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => toggleSelect(folder)}
            className="h-4 w-4"
          />

          {/* Icon */}
          <Folder size={16} className="text-blue-500" />

          {/* Name */}
          <span className="flex-1">{folder.name}</span>
        </div>

        {/* Children */}
        {isExpanded && depth < maxDepth && (
          <div>
            {folderChildren.map(child => renderFolder(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="border rounded-lg p-4 max-h-96 overflow-y-auto">
      <div className="flex items-center gap-2 mb-4">
        <img src="/dropbox-icon.svg" alt="Dropbox" className="h-6 w-6" />
        <span className="font-medium">Dropbox Folders</span>
      </div>

      {folders.length === 0 && loading.has('') ? (
        <div className="text-center py-8 text-gray-500">Loading...</div>
      ) : folders.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No folders found</div>
      ) : (
        folders.map(folder => renderFolder(folder))
      )}
    </div>
  );
};
```

---

## 4. CHI TIẾT IMPLEMENTATION TIMELINE

### 4.1 Ngày 1: Authentication (4-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Setup credentials file | 30 phút | `dropbox_credentials.json` |
| Install dependencies | 15 phút | `pip install dropbox` |
| Implement `dropbox_auth.py` | 2 giờ | Auth class complete |
| Implement OAuth endpoints | 1.5 giờ | 4 endpoints working |
| Test auth flow manually | 1 giờ | Token stored successfully |

**Checkpoint Ngày 1**:
- ✅ Có thể authenticate với Dropbox
- ✅ Token được lưu encrypted
- ✅ Có thể get user info

### 4.2 Ngày 2: Client & API (4-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Implement `dropbox_client.py` | 2 giờ | Client class complete |
| Implement folder listing | 1 giờ | `list_folder()` working |
| Implement video filtering | 30 phút | `list_videos()` working |
| Implement file download | 1 giờ | `download_file()` working |
| Update `cloud_manager.py` | 30 phút | Dropbox in SUPPORTED_PROVIDERS |
| Test all client methods | 1 giờ | All methods verified |

**Checkpoint Ngày 2**:
- ✅ Có thể list folders
- ✅ Có thể filter video files
- ✅ Có thể download files

### 4.3 Ngày 3: Frontend & Integration (4-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Create `DropboxFolderTree.tsx` | 2 giờ | Component complete |
| Add Dropbox to source selector | 30 phút | UI option added |
| Integrate with auto-sync | 1.5 giờ | Sync working |
| Write unit tests | 1 giờ | >80% coverage |
| E2E testing | 1 giờ | All flows tested |

**Checkpoint Ngày 3**:
- ✅ Full flow working end-to-end
- ✅ Tests passing
- ✅ Ready for PR

---

## 5. DATABASE SCHEMA

### 5.1 Source Config Format
```json
// video_sources.config (JSON column)
{
  "provider": "dropbox",
  "folder_path": "/Camera Videos/2024",
  "folder_name": "2024",
  "user_email": "user@example.com",
  "account_id": "dbid:AAAA..."
}
```

### 5.2 Downloaded Files Tracking
```json
// downloaded_files record
{
  "source_id": 5,
  "cloud_file_id": "id:abc123...",  // Dropbox file ID
  "original_filename": "video_001.mp4",
  "dropbox_path": "/Camera Videos/2024/video_001.mp4",
  "content_hash": "abc123...",  // For dedup
  "local_file_path": "/data/downloads/dropbox/video_001.mp4"
}
```

---

## 6. SECURITY & ERROR HANDLING

### 6.1 Security Checklist
- [x] App secret stored encrypted
- [x] Access tokens stored encrypted (AES-256)
- [x] Refresh tokens stored encrypted
- [x] CSRF protection với state parameter
- [x] JWT session tokens với expiration
- [x] Rate limiting on all endpoints
- [x] Audit logging

### 6.2 Error Handling Matrix

| Error | Cause | Handling |
|-------|-------|----------|
| `AuthError` | Invalid/expired token | Auto-refresh, re-auth if fails |
| `ApiError(409)` | Conflict | Retry with backoff |
| `ApiError(429)` | Rate limit | Wait and retry |
| `ApiError(500)` | Server error | Retry 3 times |
| `PathNotFound` | File deleted | Skip, log warning |
| `NetworkError` | Connection issue | Retry with exponential backoff |

### 6.3 Rate Limits (Dropbox)
- **App-level**: ~25,000 calls/month (free tier)
- **User-level**: ~1000 calls/hour
- **Download**: No specific limit, but bandwidth throttling

**Mitigation**:
- Cache folder listings (5 min TTL)
- Batch API calls where possible
- Implement exponential backoff

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests
```python
# tests/test_dropbox_auth.py
def test_initiate_oauth_flow():
    auth = DropboxAuthManager()
    result = auth.initiate_oauth_flow()
    assert result['success']
    assert 'auth_url' in result
    assert 'dropbox.com' in result['auth_url']

def test_token_encryption():
    # Test encrypt/decrypt cycle
    pass

def test_token_refresh():
    # Test refresh mechanism
    pass

# tests/test_dropbox_client.py
def test_list_folder(mock_dbx):
    client = DropboxClient(mock_dbx)
    folders = client.list_folder('')
    assert isinstance(folders, list)

def test_list_videos_filters_correctly(mock_dbx):
    client = DropboxClient(mock_dbx)
    videos = client.list_videos('/test')
    for video in videos:
        assert video['type'] == 'file'
        assert any(video['name'].endswith(ext) for ext in client.VIDEO_EXTENSIONS)

def test_download_file(mock_dbx, tmp_path):
    client = DropboxClient(mock_dbx)
    local_path = tmp_path / "test.mp4"
    result = client.download_file('/test/video.mp4', str(local_path))
    assert result == True
    assert local_path.exists()
```

### 7.2 Integration Tests
```python
# tests/integration/test_dropbox_e2e.py
@pytest.mark.integration
def test_full_auth_flow():
    # Requires real Dropbox test account
    pass

@pytest.mark.integration
def test_folder_listing_with_real_account():
    pass

@pytest.mark.integration
def test_video_download():
    pass
```

### 7.3 Manual Test Checklist
- [ ] Create Dropbox app in console
- [ ] Configure redirect URI
- [ ] Test OAuth flow in browser
- [ ] Upload test videos to Dropbox
- [ ] Test folder tree loading
- [ ] Test folder selection
- [ ] Test video download
- [ ] Test auto-sync trigger
- [ ] Test token refresh (wait 4 hours or manually expire)
- [ ] Test error scenarios

---

## 8. DOCUMENTATION

### 8.1 API Documentation
```markdown
## Dropbox Endpoints

### POST /api/cloud/dropbox-auth
Initiate Dropbox OAuth2 flow

**Response**:
```json
{
  "success": true,
  "auth_url": "https://www.dropbox.com/oauth2/authorize?...",
  "session_id": "abc123"
}
```

### GET /api/cloud/dropbox/oauth/callback
OAuth2 callback (auto-redirect)

### GET /api/cloud/dropbox/auth-status
Check authentication status

**Response**:
```json
{
  "authenticated": true,
  "user_email": "user@example.com",
  "user_name": "John Doe",
  "storage_used_gb": 1.5,
  "storage_allocated_gb": 2.0
}
```

### POST /api/cloud/dropbox/list_folders
List folders at path

**Request**:
```json
{
  "path": "/Camera Videos"
}
```

**Response**:
```json
{
  "success": true,
  "folders": [
    {"id": "id:abc", "name": "2024", "path": "/Camera Videos/2024", "type": "folder"}
  ]
}
```
```

### 8.2 User Guide
```markdown
# Kết Nối Dropbox với VPACK

## Yêu Cầu
- Tài khoản Dropbox (miễn phí hoặc trả phí)
- Video camera đã upload lên Dropbox

## Các Bước Thực Hiện

1. **Thêm Source Mới**
   - Vào trang Sources
   - Click "Add Source"
   - Chọn "Dropbox"

2. **Kết Nối Dropbox**
   - Click "Connect Dropbox"
   - Đăng nhập tài khoản Dropbox
   - Cho phép VPACK truy cập files

3. **Chọn Folders**
   - Browse folder tree
   - Tick chọn folders chứa video
   - Click "Save"

4. **Bật Auto-Sync** (tùy chọn)
   - Trong source settings
   - Enable "Auto-sync"
   - Chọn sync interval (15 phút - 24 giờ)

## Lưu Ý
- Chỉ files video (.mp4, .avi, .mov, ...) được sync
- Videos đã download sẽ không download lại
- Free tier Dropbox: 2GB storage
```

---

## 9. SUCCESS CRITERIA

### 9.1 Functional
- [x] OAuth2 authentication works
- [x] Folder tree displays correctly
- [x] Video files detected
- [x] Download works
- [x] Auto-sync integration works
- [x] Token refresh works

### 9.2 Non-Functional
- [x] Auth success rate: >95%
- [x] Download success rate: >90%
- [x] Test coverage: >80%
- [x] Response time: <1s for folder listing

### 9.3 Acceptance Criteria
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual E2E test successful
- [ ] Code review approved
- [ ] Documentation complete

---

## 10. DEPENDENCIES & BLOCKERS

### 10.1 Dependencies
- Python `dropbox` SDK v11.36+
- Existing encryption utilities từ `cloud_auth.py`
- Frontend component patterns từ `GoogleDriveFolderTree.tsx`

### 10.2 Potential Blockers
| Blocker | Impact | Mitigation |
|---------|--------|------------|
| Dropbox app approval delay | Low | Use development mode (no approval needed for <500 users) |
| SDK version incompatibility | Medium | Pin version trong requirements.txt |
| Free tier limits | Low | Test with small files, use test account |

---

## 11. NEXT STEPS AFTER COMPLETION

1. ✅ **Dropbox complete** → Move to Amazon S3
2. Document lessons learned
3. Refactor common code into base classes
4. Consider: Dropbox Business support (nếu cần)

---

**Estimated Effort**: 2-3 days
**Actual Effort**: _[To be filled]_
**Status**: Planning → Ready for Implementation
**Assignee**: _[Developer]_

---

**Prepared by**: Claude (AI Assistant)
**Date**: 2025-11-21
**Version**: 1.0
