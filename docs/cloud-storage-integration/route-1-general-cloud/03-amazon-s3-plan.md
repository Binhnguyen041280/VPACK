# 📘 Amazon S3 Integration - Detailed Implementation Plan

**Provider**: Amazon S3 (Simple Storage Service)
**Lộ trình**: 1 - General Cloud Storage
**Priority**: Medium (implement sau OneDrive và Dropbox)
**Timeline**: 4-5 ngày làm việc
**Độ khó**: ⭐⭐⭐ Hard
**Status**: Planning
**Last Updated**: 2025-11-21

---

## 1. TỔNG QUAN & MỤC TIÊU

### 1.1 Use Case
- User có AWS account và sử dụng S3 để lưu trữ video camera
- Doanh nghiệp sử dụng S3 làm storage backend cho camera system
- Video đã được upload lên S3 buckets (manual hoặc automated)
- Cần download video về VPACK để phân tích batch

### 1.2 Ưu Điểm Amazon S3
- ✅ **Industry standard** cho cloud storage
- ✅ Durability cực cao (99.999999999% - 11 nines)
- ✅ Phù hợp cho video streaming và large files
- ✅ Lifecycle policies để manage costs
- ✅ SDK mature (`boto3`)
- ✅ Integration tốt với AWS ecosystem (CloudFront, Lambda, etc.)
- ✅ Free tier: 5GB storage + 20,000 GET requests/month (12 tháng đầu)

### 1.3 Technical Specs
- **API**: AWS S3 REST API
- **Authentication**: IAM Access Key + Secret Key (không dùng OAuth2)
- **SDK**: `boto3` (AWS SDK for Python)
- **Permissions Required**:
  - `s3:ListBucket` - List objects trong bucket
  - `s3:GetObject` - Download files
  - `s3:GetBucketLocation` - Get bucket region
  - (Optional) `s3:ListAllMyBuckets` - List all buckets

### 1.4 Deliverables
1. ✅ IAM-based authentication
2. ✅ Bucket listing và selection
3. ✅ Folder/prefix navigation (S3 "folders")
4. ✅ Video file download
5. ✅ Auto-sync integration
6. ✅ Frontend React component
7. ✅ Tests (unit + integration)
8. ✅ Documentation

---

## 2. PREREQUISITES & SETUP

### 2.1 Tài Khoản Cần Có
- [ ] **AWS Account** - Đăng ký tại https://aws.amazon.com
  - Free tier: 12 tháng đầu
  - 5GB S3 storage
  - 20,000 GET requests/month
  - 2,000 PUT requests/month

### 2.2 IAM User Creation & Permissions
**Bước cần User làm:**

#### **Step 1: Tạo IAM User**

1. Đăng nhập **AWS Console**: https://console.aws.amazon.com

2. Vào **IAM** service (search "IAM")

3. Click **Users** → **Add users**

4. User details:
   - **User name**: `vpack-s3-integration`
   - **Access type**: ✅ Programmatic access (Access key - không cần console access)
   - Click **Next: Permissions**

5. Set permissions:
   - **Option 1 (Recommended - Least Privilege)**:
     - Click **Attach existing policies directly**
     - Click **Create policy**
     - Chọn JSON tab, paste policy này:
       ```json
       {
         "Version": "2012-10-17",
         "Statement": [
           {
             "Effect": "Allow",
             "Action": [
               "s3:ListBucket",
               "s3:GetBucketLocation",
               "s3:ListAllMyBuckets"
             ],
             "Resource": "*"
           },
           {
             "Effect": "Allow",
             "Action": [
               "s3:GetObject"
             ],
             "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
           }
         ]
       }
       ```
     - Thay `YOUR_BUCKET_NAME` bằng tên bucket thực tế
     - Policy name: `VPACKReadOnlyPolicy`
     - Click **Create policy**

   - **Option 2 (Easier - Broader Access)**:
     - Attach policy: `AmazonS3ReadOnlyAccess` (AWS managed policy)

6. Click **Next: Tags** → Skip tags

7. Click **Next: Review** → **Create user**

8. **LƯU LẠI CREDENTIALS** (chỉ hiện 1 lần!):
   - **Access key ID**: `AKIA...`
   - **Secret access key**: `abc123...`
   - Click **Download .csv** để lưu

#### **Step 2: Tạo S3 Bucket (nếu chưa có)**

1. Vào **S3** service

2. Click **Create bucket**:
   - **Bucket name**: `vpack-camera-videos` (phải unique globally)
   - **Region**: `us-east-1` (hoặc region gần VN: `ap-southeast-1` Singapore)
   - **Block Public Access**: ✅ Keep all blocked (security)
   - Click **Create bucket**

3. Upload test videos:
   - Vào bucket vừa tạo
   - Click **Upload** → Add files
   - Upload vài video test (.mp4)

#### **Step 3: Lưu Credentials vào File**

```bash
# File: backend/modules/sources/credentials/s3_credentials.json
{
  "access_key_id": "AKIA...",
  "secret_access_key": "abc123...",
  "region": "us-east-1",
  "default_bucket": "vpack-camera-videos"
}
```

**⚠️ QUAN TRỌNG**: File này phải được encrypt hoặc không commit lên git!

### 2.3 Dependencies Installation
```bash
pip install boto3==1.34.10
```

### 2.4 Environment Variables (Alternative)
```bash
# .env file
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=abc123...
AWS_DEFAULT_REGION=us-east-1
AWS_DEFAULT_BUCKET=vpack-camera-videos
```

---

## 3. KIẾN TRÚC & IMPLEMENTATION

### 3.1 File Structure
```
backend/modules/sources/
├── s3_auth.py                 # IAM credential management
├── s3_client.py               # S3 operations với boto3
├── credentials/
│   └── s3_credentials.json
└── tokens/
    └── s3_{user_hash}.json    # Encrypted credentials per user
```

### 3.2 Authentication Flow (Khác với OAuth2)

```
User → Nhập AWS Access Key + Secret Key
  → Backend validates credentials (test S3 connection)
  → Encrypt và store credentials
  → Return session token
  → User can browse buckets/folders
```

**Lưu ý**: S3 không dùng OAuth2, dùng long-lived Access Keys!

### 3.3 S3 "Folder" Concept

**Quan trọng**: S3 không có folders thực sự! Chỉ có:
- **Buckets**: Top-level containers
- **Objects**: Files với keys (paths)
- **Prefixes**: Simulated folders bằng `/` trong object keys

Example:
```
Bucket: vpack-camera-videos
Objects:
  - camera1/2024/01/video001.mp4
  - camera1/2024/01/video002.mp4
  - camera2/2024/01/video003.mp4

Prefixes (simulated folders):
  - camera1/
  - camera1/2024/
  - camera1/2024/01/
```

### 3.4 Core Components

#### **Component 1: `s3_auth.py`**
```python
import boto3
import json
import os
import hashlib
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class S3AuthManager:
    """S3 Authentication and Credential Management"""

    def __init__(self):
        self.credentials_dir = os.path.join(os.path.dirname(__file__), 'credentials')
        self.tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
        os.makedirs(self.credentials_dir, exist_ok=True)
        os.makedirs(self.tokens_dir, exist_ok=True)

    def validate_credentials(self, access_key_id: str, secret_access_key: str,
                           region: str = 'us-east-1') -> Dict:
        """Validate AWS credentials by testing S3 connection"""
        try:
            # Create S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region
            )

            # Test connection: list buckets
            response = s3_client.list_buckets()

            # Get AWS account info
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region
            )
            identity = sts_client.get_caller_identity()

            user_info = {
                'account_id': identity['Account'],
                'user_arn': identity['Arn'],
                'user_id': identity['UserId'],
                'bucket_count': len(response['Buckets']),
                'buckets': [b['Name'] for b in response['Buckets']]
            }

            logger.info(f"✅ S3 credentials validated for account: {user_info['account_id']}")

            return {
                'success': True,
                'user_info': user_info,
                'region': region
            }

        except Exception as e:
            logger.error(f"❌ S3 credential validation failed: {e}")
            return {
                'success': False,
                'message': f'Invalid credentials: {str(e)}'
            }

    def store_credentials(self, user_email: str, credentials: Dict) -> Dict:
        """Store encrypted S3 credentials"""
        try:
            # Encrypt credentials (reuse CloudAuthManager encryption)
            from .cloud_auth import CloudAuthManager
            auth_manager = CloudAuthManager('s3')
            encrypted_data = auth_manager.encrypt_credentials(credentials)

            if not encrypted_data:
                return {'success': False, 'message': 'Encryption failed'}

            # Generate filename
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            filename = f"s3_{email_hash}.json"
            filepath = os.path.join(self.tokens_dir, filename)

            # Store
            storage = {
                'encrypted_data': encrypted_data,
                'user_email': user_email,
                'created_at': datetime.now().isoformat(),
                'encryption_version': '1.0',
                'provider': 's3'
            }

            with open(filepath, 'w') as f:
                json.dump(storage, f, indent=2)

            os.chmod(filepath, 0o600)  # Restrict permissions

            logger.info(f"✅ S3 credentials stored for: {user_email}")

            return {'success': True, 'filepath': filepath}

        except Exception as e:
            logger.error(f"❌ Credential storage error: {e}")
            return {'success': False, 'message': str(e)}

    def load_credentials(self, user_email: str) -> Optional[Dict]:
        """Load and decrypt S3 credentials"""
        try:
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            filename = f"s3_{email_hash}.json"
            filepath = os.path.join(self.tokens_dir, filename)

            if not os.path.exists(filepath):
                logger.warning(f"No credentials found for: {user_email}")
                return None

            with open(filepath, 'r') as f:
                storage = json.load(f)

            # Decrypt
            from .cloud_auth import CloudAuthManager
            auth_manager = CloudAuthManager('s3')
            credentials = auth_manager.decrypt_credentials(storage['encrypted_data'])

            if not credentials:
                logger.error(f"❌ Failed to decrypt credentials for: {user_email}")
                return None

            logger.info(f"✅ Loaded S3 credentials for: {user_email}")
            return credentials

        except Exception as e:
            logger.error(f"❌ Credential loading error: {e}")
            return None

    def get_s3_client(self, user_email: str) -> Optional[boto3.client]:
        """Get authenticated S3 client for user"""
        credentials = self.load_credentials(user_email)
        if not credentials:
            return None

        return boto3.client(
            's3',
            aws_access_key_id=credentials['access_key_id'],
            aws_secret_access_key=credentials['secret_access_key'],
            region_name=credentials.get('region', 'us-east-1')
        )

    def revoke_credentials(self, user_email: str) -> Dict:
        """Delete stored credentials"""
        try:
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            filename = f"s3_{email_hash}.json"
            filepath = os.path.join(self.tokens_dir, filename)

            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"🔌 Revoked S3 credentials for: {user_email}")
                return {'success': True}
            else:
                return {'success': False, 'message': 'Credentials not found'}

        except Exception as e:
            return {'success': False, 'message': str(e)}
```

#### **Component 2: `s3_client.py`**
```python
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List, Dict, Optional
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class S3Client:
    """S3 Operations Client"""

    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']

    def __init__(self, s3_client: boto3.client):
        self.s3 = s3_client

    def list_buckets(self) -> List[Dict]:
        """List all S3 buckets"""
        try:
            response = self.s3.list_buckets()
            buckets = []

            for bucket in response['Buckets']:
                buckets.append({
                    'name': bucket['Name'],
                    'created': bucket['CreationDate'].isoformat(),
                    'type': 'bucket'
                })

            logger.info(f"📦 Found {len(buckets)} buckets")
            return buckets

        except Exception as e:
            logger.error(f"❌ List buckets error: {e}")
            return []

    def list_objects(self, bucket: str, prefix: str = '', delimiter: str = '/') -> Dict:
        """
        List objects in bucket with prefix
        Returns both 'folders' (common prefixes) and 'files' (objects)
        """
        try:
            response = self.s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                Delimiter=delimiter,
                MaxKeys=1000
            )

            folders = []
            files = []

            # Common Prefixes = "Folders"
            if 'CommonPrefixes' in response:
                for cp in response['CommonPrefixes']:
                    folder_prefix = cp['Prefix']
                    folder_name = folder_prefix.rstrip('/').split('/')[-1]

                    folders.append({
                        'name': folder_name,
                        'prefix': folder_prefix,
                        'type': 'folder',
                        'bucket': bucket
                    })

            # Contents = Files
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip "folder" objects (keys ending with /)
                    if obj['Key'].endswith('/'):
                        continue

                    # Skip if same as prefix (folder itself)
                    if obj['Key'] == prefix:
                        continue

                    file_name = obj['Key'].split('/')[-1]

                    files.append({
                        'name': file_name,
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'modified': obj['LastModified'].isoformat(),
                        'type': 'file',
                        'bucket': bucket,
                        'etag': obj['ETag'].strip('"')  # For dedup
                    })

            logger.info(f"📁 Listed {len(folders)} folders, {len(files)} files in {bucket}/{prefix}")

            return {
                'folders': folders,
                'files': files,
                'bucket': bucket,
                'prefix': prefix
            }

        except ClientError as e:
            logger.error(f"❌ List objects error: {e}")
            return {'folders': [], 'files': []}

    def list_videos(self, bucket: str, prefix: str = '', recursive: bool = True) -> List[Dict]:
        """List only video files in bucket/prefix"""
        videos = []

        if recursive:
            # Recursive scan
            paginator = self.s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    if self._is_video(obj['Key']):
                        videos.append({
                            'name': os.path.basename(obj['Key']),
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'modified': obj['LastModified'].isoformat(),
                            'bucket': bucket,
                            'etag': obj['ETag'].strip('"')
                        })
        else:
            # Non-recursive
            result = self.list_objects(bucket, prefix)
            videos = [f for f in result['files'] if self._is_video(f['key'])]

        logger.info(f"🎥 Found {len(videos)} video files")
        return videos

    def download_file(self, bucket: str, key: str, local_path: str) -> bool:
        """Download S3 object to local file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download with progress
            self.s3.download_file(bucket, key, local_path)

            logger.info(f"✅ Downloaded: s3://{bucket}/{key} -> {local_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            return False

    def get_object_metadata(self, bucket: str, key: str) -> Optional[Dict]:
        """Get metadata for an object"""
        try:
            response = self.s3.head_object(Bucket=bucket, Key=key)

            return {
                'size': response['ContentLength'],
                'modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType'),
                'etag': response['ETag'].strip('"'),
                'metadata': response.get('Metadata', {})
            }

        except Exception as e:
            logger.error(f"❌ Get metadata error: {e}")
            return None

    def get_bucket_region(self, bucket: str) -> str:
        """Get bucket region"""
        try:
            response = self.s3.get_bucket_location(Bucket=bucket)
            # Note: us-east-1 returns None
            region = response['LocationConstraint'] or 'us-east-1'
            return region
        except Exception:
            return 'us-east-1'

    def _is_video(self, key: str) -> bool:
        """Check if object key is a video file"""
        ext = os.path.splitext(key)[1].lower()
        return ext in self.VIDEO_EXTENSIONS
```

#### **Component 3: API Endpoints**
```python
# Add to cloud_endpoints.py

@app.route('/api/cloud/s3-connect', methods=['POST'])
@limiter.limit("10 per minute")
def s3_connect():
    """Connect to S3 with IAM credentials"""
    data = request.get_json()

    access_key_id = data.get('access_key_id')
    secret_access_key = data.get('secret_access_key')
    region = data.get('region', 'us-east-1')
    user_email = data.get('user_email')  # From frontend session

    if not all([access_key_id, secret_access_key, user_email]):
        return jsonify({'success': False, 'message': 'Missing credentials'})

    auth_manager = S3AuthManager()

    # Validate credentials
    result = auth_manager.validate_credentials(access_key_id, secret_access_key, region)

    if not result['success']:
        return jsonify(result)

    # Store credentials
    credentials = {
        'access_key_id': access_key_id,
        'secret_access_key': secret_access_key,
        'region': region,
        'user_info': result['user_info']
    }

    store_result = auth_manager.store_credentials(user_email, credentials)

    if store_result['success']:
        # Generate session token
        session_token = generate_session_token(user_email, result['user_info'])

        return jsonify({
            'success': True,
            'user_info': result['user_info'],
            'session_token': session_token
        })
    else:
        return jsonify(store_result)

@app.route('/api/cloud/s3/list_buckets', methods=['GET'])
@limiter.limit("15 per minute")
def s3_list_buckets():
    """List S3 buckets"""
    user_email = get_user_email_from_session()

    auth_manager = S3AuthManager()
    s3_client = auth_manager.get_s3_client(user_email)

    if not s3_client:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    client = S3Client(s3_client)
    buckets = client.list_buckets()

    return jsonify({
        'success': True,
        'buckets': buckets
    })

@app.route('/api/cloud/s3/list_objects', methods=['POST'])
@limiter.limit("20 per minute")
def s3_list_objects():
    """List objects in bucket/prefix"""
    data = request.get_json()
    bucket = data.get('bucket')
    prefix = data.get('prefix', '')

    user_email = get_user_email_from_session()
    auth_manager = S3AuthManager()
    s3_client = auth_manager.get_s3_client(user_email)

    if not s3_client:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    client = S3Client(s3_client)
    result = client.list_objects(bucket, prefix)

    return jsonify({
        'success': True,
        **result
    })

@app.route('/api/cloud/s3/disconnect', methods=['POST'])
def s3_disconnect():
    """Disconnect S3 and delete credentials"""
    user_email = get_user_email_from_session()
    auth_manager = S3AuthManager()
    result = auth_manager.revoke_credentials(user_email)
    return jsonify(result)
```

#### **Component 4: Frontend** (`S3BucketTree.tsx`)
```typescript
import React, { useState, useEffect } from 'react';
import { Database, Folder, ChevronRight, ChevronDown, Lock } from 'lucide-react';

interface S3Item {
  name: string;
  type: 'bucket' | 'folder' | 'file';
  bucket?: string;
  prefix?: string;
  key?: string;
}

interface S3BucketTreeProps {
  onPathSelected: (bucket: string, prefix: string) => void;
}

export const S3BucketTree: React.FC<S3BucketTreeProps> = ({ onPathSelected }) => {
  const [buckets, setBuckets] = useState<S3Item[]>([]);
  const [expanded, setExpanded] = useState<Map<string, boolean>>(new Map());
  const [children, setChildren] = useState<Map<string, S3Item[]>>(new Map());
  const [loading, setLoading] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState<{bucket: string, prefix: string} | null>(null);

  // Load buckets on mount
  useEffect(() => {
    loadBuckets();
  }, []);

  const loadBuckets = async () => {
    try {
      const response = await fetch('/api/cloud/s3/list_buckets', {
        credentials: 'include'
      });
      const data = await response.json();

      if (data.success) {
        setBuckets(data.buckets);
      }
    } catch (error) {
      console.error('Failed to load buckets:', error);
    }
  };

  const loadFolders = async (bucket: string, prefix: string = '') => {
    const key = `${bucket}/${prefix}`;
    setLoading(prev => new Set(prev).add(key));

    try {
      const response = await fetch('/api/cloud/s3/list_objects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ bucket, prefix })
      });

      const data = await response.json();

      if (data.success) {
        setChildren(prev => new Map(prev).set(key, data.folders));
      }
    } catch (error) {
      console.error('Failed to load folders:', error);
    } finally {
      setLoading(prev => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  const toggleExpand = (item: S3Item) => {
    const key = item.type === 'bucket'
      ? item.name
      : `${item.bucket}/${item.prefix}`;

    const newExpanded = new Map(expanded);
    const isExpanded = expanded.get(key);

    if (isExpanded) {
      newExpanded.set(key, false);
    } else {
      newExpanded.set(key, true);

      // Load children if not loaded
      if (!children.has(key)) {
        if (item.type === 'bucket') {
          loadFolders(item.name, '');
        } else if (item.type === 'folder') {
          loadFolders(item.bucket!, item.prefix!);
        }
      }
    }

    setExpanded(newExpanded);
  };

  const selectPath = (item: S3Item) => {
    if (item.type === 'bucket') {
      setSelectedPath({ bucket: item.name, prefix: '' });
      onPathSelected(item.name, '');
    } else if (item.type === 'folder') {
      setSelectedPath({ bucket: item.bucket!, prefix: item.prefix! });
      onPathSelected(item.bucket!, item.prefix!);
    }
  };

  const renderItem = (item: S3Item, depth: number = 0) => {
    const key = item.type === 'bucket'
      ? item.name
      : `${item.bucket}/${item.prefix}`;

    const isExpanded = expanded.get(key);
    const isLoading = loading.has(key);
    const itemChildren = children.get(key) || [];

    const isSelected = selectedPath?.bucket === (item.bucket || item.name) &&
                      selectedPath?.prefix === (item.prefix || '');

    return (
      <div key={key}>
        <div
          className={`flex items-center gap-2 p-2 hover:bg-gray-100 rounded cursor-pointer
            ${isSelected ? 'bg-blue-100' : ''}`}
          style={{ paddingLeft: `${depth * 20 + 8}px` }}
          onClick={() => selectPath(item)}
        >
          {/* Expand button */}
          <button onClick={(e) => { e.stopPropagation(); toggleExpand(item); }}>
            {isLoading ? (
              <span className="animate-spin">⏳</span>
            ) : isExpanded ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
          </button>

          {/* Icon */}
          {item.type === 'bucket' ? (
            <Database size={16} className="text-orange-500" />
          ) : (
            <Folder size={16} className="text-blue-500" />
          )}

          {/* Name */}
          <span>{item.name}</span>
        </div>

        {/* Children */}
        {isExpanded && (
          <div>
            {itemChildren.map(child => renderItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="border rounded-lg p-4 max-h-96 overflow-y-auto">
      <div className="flex items-center gap-2 mb-4">
        <Database className="h-6 w-6 text-orange-500" />
        <span className="font-medium">Amazon S3 Buckets</span>
      </div>

      {buckets.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No buckets found</div>
      ) : (
        buckets.map(bucket => renderItem(bucket))
      )}
    </div>
  );
};
```

---

## 4. CHI TIẾT IMPLEMENTATION TIMELINE

### 4.1 Ngày 1: Setup & Authentication (5-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Tạo AWS account + IAM user | 1 giờ | Access keys ready |
| Tạo S3 bucket + upload test videos | 30 phút | Test data ready |
| Install boto3 | 15 phút | Dependencies installed |
| Implement `s3_auth.py` | 2 giờ | Auth manager complete |
| Implement credential validation | 1 giờ | Connection test working |
| Test authentication | 1 giờ | Can list buckets |

**Checkpoint**: Có thể connect S3 và list buckets

### 4.2 Ngày 2: S3 Client Implementation (5-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Implement `s3_client.py` | 2.5 giờ | Client class complete |
| Implement `list_objects()` với prefixes | 1.5 giờ | Folder navigation working |
| Implement `list_videos()` | 1 giờ | Video filtering working |
| Implement `download_file()` | 1 giờ | Download working |
| Test all methods | 1 giờ | Verified |

**Checkpoint**: Có thể navigate folders và download videos

### 4.3 Ngày 3: API Endpoints (4-5 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Add S3 to `cloud_manager.py` | 30 phút | Provider registered |
| Implement `/s3-connect` endpoint | 1 giờ | Auth endpoint working |
| Implement `/s3/list_buckets` | 30 phút | Bucket listing API |
| Implement `/s3/list_objects` | 1 giờ | Object listing API |
| Implement `/s3/disconnect` | 30 phút | Disconnect API |
| Test với Postman | 1.5 giờ | All endpoints verified |

**Checkpoint**: API endpoints working

### 4.4 Ngày 4: Frontend (5-6 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Create `S3BucketTree.tsx` | 2.5 giờ | Component complete |
| Create S3 connection form | 1 giờ | Credential input form |
| Add to source selector | 30 phút | UI integration |
| Test UI flow | 1 giờ | UI working |
| Polish UX | 1 giờ | Smooth experience |

**Checkpoint**: Full UI working

### 4.5 Ngày 5: Testing & Integration (4-5 giờ)

| Task | Thời gian | Output |
|------|-----------|--------|
| Integrate with auto-sync | 1.5 giờ | Sync working |
| Write unit tests | 1.5 giờ | >80% coverage |
| E2E testing | 1 giờ | All flows tested |
| Bug fixes | 1 giờ | Issues resolved |

**Checkpoint**: Production ready

---

## 5. DATABASE SCHEMA

### 5.1 Source Config Format
```json
// video_sources.config (JSON)
{
  "provider": "s3",
  "bucket": "vpack-camera-videos",
  "prefix": "camera1/2024/",
  "region": "us-east-1",
  "user_email": "user@example.com"
}
```

### 5.2 Downloaded Files Tracking
```json
// downloaded_files
{
  "source_id": 7,
  "cloud_file_id": "s3://vpack-camera-videos/camera1/2024/01/video001.mp4",
  "s3_etag": "abc123...",  // For dedup
  "bucket": "vpack-camera-videos",
  "key": "camera1/2024/01/video001.mp4",
  "original_filename": "video001.mp4",
  "local_file_path": "/data/downloads/s3/video001.mp4"
}
```

---

## 6. SECURITY & ERROR HANDLING

### 6.1 Security Best Practices

#### **IAM User Permissions (Least Privilege)**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::specific-bucket-name",
        "arn:aws:s3:::specific-bucket-name/*"
      ]
    }
  ]
}
```

#### **Security Checklist**
- [x] Access keys stored encrypted (AES-256)
- [x] Never log access keys
- [x] Use IAM user (không dùng root account)
- [x] Minimum permissions (ReadOnly)
- [x] Rotate access keys định kỳ (remind user)
- [x] Enable AWS CloudTrail để audit
- [x] Restrict bucket access (block public access)

### 6.2 Error Handling

| Error | Boto3 Exception | Handling |
|-------|-----------------|----------|
| **Invalid credentials** | `NoCredentialsError` | Show error, prompt re-enter |
| **Access denied** | `ClientError(403)` | Check IAM permissions, guide user |
| **Bucket not found** | `ClientError(404)` | Verify bucket name, region |
| **Network error** | `ConnectionError` | Retry 3x with backoff |
| **Throttling** | `ClientError(503)` | Exponential backoff |
| **Region mismatch** | `ClientError` | Auto-detect bucket region |

### 6.3 Cost Optimization

**AWS Free Tier Limits** (first 12 months):
- 5GB storage
- 20,000 GET requests/month
- 2,000 PUT requests/month

**After free tier**:
- Storage: ~$0.023/GB/month
- GET requests: $0.0004/1000 requests
- Data transfer out: $0.09/GB

**Optimization strategies**:
- Cache folder listings (reduce GET requests)
- Download only new videos (dedup by ETag)
- Use S3 Lifecycle policies (move old videos to cheaper tiers)
- Monitor costs với AWS Budgets

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests
```python
# tests/test_s3_auth.py
def test_validate_credentials_success(mock_boto3):
    auth = S3AuthManager()
    result = auth.validate_credentials('AKIA...', 'secret', 'us-east-1')
    assert result['success']

def test_validate_credentials_invalid():
    auth = S3AuthManager()
    result = auth.validate_credentials('invalid', 'invalid', 'us-east-1')
    assert not result['success']

# tests/test_s3_client.py
def test_list_buckets(mock_s3_client):
    client = S3Client(mock_s3_client)
    buckets = client.list_buckets()
    assert len(buckets) > 0

def test_list_objects_with_prefix(mock_s3_client):
    client = S3Client(mock_s3_client)
    result = client.list_objects('test-bucket', 'camera1/')
    assert 'folders' in result
    assert 'files' in result

def test_list_videos_filters_correctly(mock_s3_client):
    client = S3Client(mock_s3_client)
    videos = client.list_videos('test-bucket', 'videos/')
    for video in videos:
        assert any(video['key'].endswith(ext) for ext in client.VIDEO_EXTENSIONS)

def test_download_file(mock_s3_client, tmp_path):
    client = S3Client(mock_s3_client)
    local_path = tmp_path / "test.mp4"
    result = client.download_file('bucket', 'key.mp4', str(local_path))
    assert result == True
```

### 7.2 Integration Tests (với LocalStack)
```python
# Use LocalStack to mock AWS services locally
import pytest
import boto3

@pytest.fixture
def localstack_s3():
    """LocalStack S3 for testing"""
    s3 = boto3.client(
        's3',
        endpoint_url='http://localhost:4566',  # LocalStack
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )

    # Create test bucket
    s3.create_bucket(Bucket='test-bucket')

    yield s3

    # Cleanup
    s3.delete_bucket(Bucket='test-bucket')

@pytest.mark.integration
def test_full_s3_workflow(localstack_s3):
    # Upload test video
    localstack_s3.put_object(
        Bucket='test-bucket',
        Key='test-video.mp4',
        Body=b'fake video content'
    )

    # Test client
    client = S3Client(localstack_s3)
    videos = client.list_videos('test-bucket')
    assert len(videos) == 1
```

### 7.3 Manual Testing
- [ ] Create AWS account
- [ ] Create IAM user với proper permissions
- [ ] Create S3 bucket
- [ ] Upload test videos (various formats)
- [ ] Test credential validation
- [ ] Test bucket listing
- [ ] Test folder navigation (prefixes)
- [ ] Test video download
- [ ] Test auto-sync
- [ ] Test cost monitoring

---

## 8. DOCUMENTATION

### 8.1 User Setup Guide
```markdown
# Kết Nối Amazon S3 với VPACK

## Bước 1: Tạo AWS Account
1. Truy cập https://aws.amazon.com
2. Click "Create an AWS Account"
3. Hoàn thành đăng ký (cần credit card, nhưng free tier không charge)

## Bước 2: Tạo IAM User
1. Vào AWS Console → IAM
2. Create User: `vpack-s3-integration`
3. Attach policy: `AmazonS3ReadOnlyAccess`
4. Lưu Access Key ID và Secret Access Key

## Bước 3: Tạo S3 Bucket (nếu chưa có)
1. Vào S3 Console
2. Create bucket: `my-camera-videos`
3. Chọn region gần bạn: `ap-southeast-1` (Singapore)
4. Upload videos vào bucket

## Bước 4: Kết Nối với VPACK
1. Vào VPACK → Add Source → Amazon S3
2. Nhập:
   - Access Key ID
   - Secret Access Key
   - Region (ví dụ: ap-southeast-1)
3. Click "Connect"
4. Chọn bucket và folder
5. Click "Save"

## Lưu Ý Bảo Mật
- ⚠️ KHÔNG share Access Keys với ai
- ⚠️ KHÔNG commit keys vào Git
- ✅ Chỉ cấp quyền ReadOnly
- ✅ Rotate keys định kỳ (mỗi 90 ngày)
```

### 8.2 API Documentation
```markdown
## S3 Endpoints

### POST /api/cloud/s3-connect
Connect với S3 credentials

**Request**:
```json
{
  "access_key_id": "AKIA...",
  "secret_access_key": "abc123...",
  "region": "us-east-1",
  "user_email": "user@example.com"
}
```

**Response**:
```json
{
  "success": true,
  "user_info": {
    "account_id": "123456789",
    "bucket_count": 5
  },
  "session_token": "jwt_token..."
}
```

### GET /api/cloud/s3/list_buckets
List tất cả buckets

### POST /api/cloud/s3/list_objects
List objects trong bucket/prefix

**Request**:
```json
{
  "bucket": "my-bucket",
  "prefix": "camera1/2024/"
}
```
```

---

## 9. SUCCESS CRITERIA

### 9.1 Functional
- [x] IAM authentication works
- [x] Bucket listing works
- [x] Folder navigation (prefixes) works
- [x] Video file filtering works
- [x] Download works
- [x] Auto-sync integration works
- [x] Credentials stored encrypted

### 9.2 Non-Functional
- [x] Auth success rate: >95%
- [x] Download success rate: >90%
- [x] Test coverage: >80%
- [x] Response time: <2s for object listing
- [x] Cost: Stay within free tier for testing

---

## 10. RISKS & MITIGATION

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **AWS costs exceed budget** | High | Medium | Monitor costs, set billing alerts, use free tier |
| **IAM permission issues** | High | High | Clear documentation, test with minimal permissions |
| **Region misconfiguration** | Medium | Medium | Auto-detect bucket region |
| **Access key rotation** | Medium | Low | Remind users to rotate keys, provide instructions |
| **Free tier expiration** | Medium | Medium | Document costs, provide cost estimation tool |
| **Large file downloads** | Low | Medium | Stream downloads, show progress |

---

## 11. ADVANCED FEATURES (FUTURE)

Sau khi complete basic integration:

1. **S3 Versioning Support**: Download specific versions of files
2. **S3 Select**: Filter videos by metadata without downloading
3. **CloudFront Integration**: Download via CDN for faster speed
4. **S3 Event Notifications**: Auto-trigger sync when new videos uploaded
5. **Glacier Support**: Download from cold storage (S3 Glacier)
6. **Multi-region Buckets**: Support buckets across regions
7. **Cost Estimator**: Show estimated costs for selected videos

---

## 12. NEXT STEPS

1. ✅ **S3 complete** → Lộ trình 1 DONE!
2. Move to Lộ trình 2: Camera Cloud Storage (Hikvision, Imou, Ezviz, Dahua, TP-Link)
3. Refactor common patterns into base classes
4. Document lessons learned từ Lộ trình 1

---

**Estimated Effort**: 4-5 days
**Actual Effort**: _[To be filled]_
**Status**: Planning → Ready for Implementation
**Assignee**: _[Developer]_

---

**Prepared by**: Claude (AI Assistant)
**Date**: 2025-11-21
**Version**: 1.0
