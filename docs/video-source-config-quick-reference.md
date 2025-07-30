# VTrack Video Source Configuration - Quick Reference

## Source Types Overview

| Source Type | Status | Path Format | Storage Location | Auto-Sync |
|------------|---------|-------------|------------------|-----------|
| Local | ✅ Ready | `/path/to/folder` | Original location | No |
| Cloud | ✅ Ready | `google_drive://folders` | `/cloud_sync/{name}/` | Yes |
| Camera | 🔧 Backend Ready | `onvif://ip:port` | `/nvr_downloads/{name}/` | Optional |

## Quick Configuration Examples

### 1. Local Network Storage (NAS)
```bash
# Mount NAS first
sudo mount -t cifs //192.168.1.10/recordings /mnt/nas -o username=user,password=pass

# Add source
{
  "source_type": "local",
  "path": "/mnt/nas/security_cameras"
}
```

### 2. Google Drive Sync
```javascript
// Step 1: Authenticate
POST /api/cloud/auth/google
{ "auth_code": "4/0AX4XfWh..." }

// Step 2: Add source with folders
{
  "source_type": "cloud",
  "config": {
    "provider": "google_drive",
    "selected_folders": [
      {"id": "1x2y3z", "name": "Camera_Front"},
      {"id": "4a5b6c", "name": "Camera_Back"}
    ],
    "sync_settings": {
      "interval_minutes": 15,
      "auto_sync_enabled": true
    }
  }
}
```

### 3. ONVIF Camera (Future)
```javascript
{
  "source_type": "camera",
  "config": {
    "protocol": "onvif",
    "ip": "192.168.1.100",
    "port": 80,
    "username": "admin",
    "password": "camera123"
  }
}
```

## Key API Endpoints

```bash
# Test connection
POST /api/config/test-source

# Save source (only one active)
POST /api/config/save-sources

# Get active source
GET /api/config/get-sources

# Update cameras
POST /api/config/update-source-cameras

# Delete/change source
DELETE /api/config/delete-source/{id}

# Cloud sync
POST /api/cloud/sync/trigger
GET /api/cloud/sync/status/{id}
```

## Directory Structure

```
VTrack/
├── frontend/               # React UI
├── backend/               
│   └── modules/
│       └── sources/       # Source handlers
│           ├── nvr_client.py
│           ├── onvif_client.py
│           ├── cloud_manager.py
│           └── path_manager.py
├── cloud_sync/            # Cloud downloads
│   └── {source_name}/
│       └── {camera_name}/
├── nvr_downloads/         # Camera recordings
└── database/
    └── events.db          # All configurations

```

## Camera Folder Auto-Detection

Folders are detected as cameras if they:
1. Contain camera keywords: `cam`, `camera`, `channel`, `ch`
2. Contain video files: `.mp4`, `.avi`, `.mov`, `.mkv`
3. Match pattern: `Camera_01`, `Ch01`, etc.

## Processing Configuration

When a source is activated:
1. `processing_config.input_path` → working directory
2. `processing_config.selected_cameras` → detected cameras
3. System scans for videos in: `{input_path}/{camera_name}/**/*.mp4`

## Security Best Practices

1. **OAuth Tokens**: Encrypted with Fernet
2. **Passwords**: Never stored plaintext
3. **Sessions**: JWT with 30min expiry
4. **File Access**: Path validation enabled
5. **API Auth**: Bearer token required

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Path not accessible" | Check permissions: `ls -la /path` |
| "No cameras detected" | Verify folder structure has video files |
| "Cloud sync failed" | Re-authenticate: Delete & re-add source |
| "Mount not persistent" | Add to `/etc/fstab` for auto-mount |

## Environment Variables

```bash
# Required
JWT_SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# Optional
CLOUD_SYNC_INTERVAL=15
MAX_SYNC_FILE_SIZE_MB=1000
CAMERA_DISCOVERY_TIMEOUT=10
```

## Single Active Source Policy

- Only ONE source can be active at a time
- Switching sources updates `processing_config.input_path`
- Previous source data remains but is inactive
- Use "Change" button to switch sources

## Debugging Commands

```bash
# Check active source
curl http://localhost:5050/api/config/get-sources

# View camera status  
curl http://localhost:5050/api/config/camera-status

# Test source connection
curl -X POST http://localhost:5050/api/config/test-source \
  -H "Content-Type: application/json" \
  -d '{"source_type":"local","path":"/mnt/videos"}'

# Check sync logs
tail -f backend/logs/cloud_sync.log
```

---
**Note**: Camera/NVR direct integration is backend-ready but requires frontend UI implementation. Use mounted NVR file shares with Local source type as workaround.