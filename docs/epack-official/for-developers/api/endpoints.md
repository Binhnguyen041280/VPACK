# ePACK API Documentation

Complete reference for ePACK REST API endpoints.

## Base URL

```
Backend API: http://localhost:8080
Frontend: http://localhost:3000
```

## Table of Contents

1. [Authentication](#authentication)
2. [Program Control](#program-control)
3. [ROI Configuration](#roi-configuration)
4. [Event Query](#event-query)
5. [Cloud Sync](#cloud-sync)
6. [Configuration](#configuration)
7. [System](#system)
8. [Payment & License](#payment--license)

## Authentication

### Google OAuth

ePACK uses Google OAuth 2.0 for user authentication.

#### Login Endpoint

```
GET /api/auth/google
```

Redirects to Google OAuth consent screen.

**Response**: Redirect to Google

#### OAuth Callback

```
GET /api/auth/callback
```

Google redirects here after user authentication.

**Query Parameters**:
- `code`: OAuth authorization code
- `state`: CSRF token

**Response**: Redirect to frontend with session cookie

#### Get Current User

```http
GET /api/user/latest
```

Get the latest authenticated user.

**Response**:
```json
{
  "success": true,
  "user": {
    "gmail_address": "user@example.com",
    "display_name": "John Doe",
    "photo_url": "/static/avatars/user_avatar.jpg",
    "original_photo_url": "https://lh3.googleusercontent.com/...",
    "last_login": "2025-10-06T14:30:00"
  }
}
```

#### Logout

```http
POST /api/user/logout
```

Logout and clear session.

**Response**:
```json
{
  "success": true,
  "message": "Logged out successfully - user profile cleared"
}
```

## Program Control

### Start/Stop Program

```http
POST /api/program
```

Execute or stop video processing programs.

**Request Body**:
```json
{
  "card": "First Run" | "Default" | "Custom",
  "action": "run" | "stop",
  "days": 7,                          // First Run only
  "custom_path": "/path/to/video.mp4" // Custom only
}
```

**Examples**:

**First Run**:
```bash
curl -X POST http://localhost:8080/api/program \
  -H "Content-Type: application/json" \
  -d '{
    "card": "First Run",
    "action": "run",
    "days": 7
  }'
```

**Default Mode**:
```bash
curl -X POST http://localhost:8080/api/program \
  -H "Content-Type: application/json" \
  -d '{
    "card": "Default",
    "action": "run"
  }'
```

**Custom Mode**:
```bash
curl -X POST http://localhost:8080/api/program \
  -H "Content-Type: application/json" \
  -d '{
    "card": "Custom",
    "action": "run",
    "custom_path": "/Users/user/Videos/sample.mp4"
  }'
```

**Response**:
```json
{
  "success": true,
  "current_running": "First Run",
  "message": "First Run started with 7 days",
  "files_discovered": 350
}
```

### Get Program Status

```http
GET /api/program
```

Get current program execution status.

**Response**:
```json
{
  "current_running": "Default",
  "scheduler_running": true,
  "first_run_completed": true,
  "last_scan": "2025-10-06 14:35:00",
  "pending_files": 3
}
```

### Get Processing Progress

```http
GET /api/program-progress
```

Get real-time processing progress.

**Response**:
```json
{
  "current_running": "First Run",
  "days": 7,
  "total_files": 350,
  "processed_files": 142,
  "progress_percentage": 40.6,
  "current_file": "Cam1_20251001_143000.mp4",
  "current_camera": "Cam1",
  "estimated_completion": "2025-10-06 18:30:00"
}
```

### Check First Run Status

```http
GET /api/check-first-run
```

Check if First Run has been completed.

**Response**:
```json
{
  "first_run_completed": true,
  "completion_time": "2025-10-01 16:45:00",
  "total_files_processed": 350,
  "total_events_detected": 1247
}
```

## ROI Configuration

### Run ROI Detection

```http
POST /run-select-roi
```

Detect ROI from sample video using AI.

**Request Body**:
```json
{
  "video_path": "/path/to/sample.mp4",
  "camera_id": "Cam1",
  "step": "packing" | "trigger"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/run-select-roi \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample_video.mp4",
    "camera_id": "Cam1",
    "step": "packing"
  }'
```

**Response**:
```json
{
  "success": true,
  "roi": {
    "x": 100,
    "y": 150,
    "w": 800,
    "h": 600
  },
  "preview_path": "/resources/output_clips/CameraROI/camera_Cam1_roi_packing.jpg",
  "message": "ROI detection completed successfully"
}
```

### Finalize ROI

```http
POST /finalize-roi
```

Save ROI configuration to database.

**Request Body**:
```json
{
  "videoPath": "/path/to/video.mp4",
  "cameraId": "Cam1",
  "rois": [
    {
      "type": "packing",
      "x": 100,
      "y": 150,
      "w": 800,
      "h": 600
    },
    {
      "type": "trigger",
      "x": 50,
      "y": 100,
      "w": 400,
      "h": 300
    }
  ]
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/finalize-roi \
  -H "Content-Type: application/json" \
  -d '{
    "videoPath": "/tmp/sample.mp4",
    "cameraId": "Cam1",
    "rois": [{"type":"packing","x":100,"y":150,"w":800,"h":600}]
  }'
```

**Response**:
```json
{
  "success": true,
  "profile_name": "Cam1",
  "packing_area": [100, 150, 800, 600],
  "qr_trigger_area": [50, 100, 400, 300],
  "message": "ROI saved to packing_profiles"
}
```

### Get ROI Frame

```http
GET /get-roi-frame?camera_id={camera_id}&file={file_type}
```

Retrieve ROI preview image.

**Query Parameters**:
- `camera_id`: Camera identifier (e.g., "Cam1")
- `file`: Image type - "roi_packing.jpg" | "roi_trigger.jpg" | "original.jpg"

**Example**:
```bash
curl -O http://localhost:8080/get-roi-frame?camera_id=Cam1&file=roi_packing.jpg
```

**Response**: JPEG image (binary)

### Get Final ROI Frame

```http
GET /get-final-roi-frame?camera_id={camera_id}
```

Retrieve combined ROI preview with all ROIs overlaid.

**Query Parameters**:
- `camera_id`: Camera identifier

**Example**:
```bash
curl -O http://localhost:8080/get-final-roi-frame?camera_id=Cam1
```

**Response**: JPEG image (binary)

## Event Query

### Query Events

```http
POST /query/get_events
```

Query packing events by tracking code and date range.

**Request Body**:
```json
{
  "tracking_code": "TRACK123",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "camera_name": "Cam1",        // Optional
  "limit": 100                  // Optional
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/query/get_events \
  -H "Content-Type: application/json" \
  -d '{
    "tracking_code": "TRACK123",
    "start_date": "2025-10-01",
    "end_date": "2025-10-06"
  }'
```

**Response**:
```json
{
  "success": true,
  "events": [
    {
      "event_id": 1247,
      "ts": 1234567890,
      "te": 1234567920,
      "duration": 30,
      "tracking_codes": "[\"TRACK123\"]",
      "video_file": "Cam1_20251001_143000.mp4",
      "camera_name": "Cam1",
      "packing_time_start": 1234567890000,
      "packing_time_end": 1234567920000,
      "output_video_path": "/path/to/output/TRACK123.mp4"
    }
  ],
  "count": 1
}
```

### Export Events to CSV

```http
POST /export_csv
```

Export events to CSV file.

**Request Body**:
```json
{
  "tracking_code": "TRACK123",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31"
}
```

**Response**: CSV file download

**CSV Format**:
```csv
Event ID,Tracking Code,Start Time,End Time,Duration,Camera,Video File
1247,TRACK123,2025-10-01 14:30:00,2025-10-01 14:30:30,30,Cam1,Cam1_20251001_143000.mp4
```

### Get Event Statistics

```http
GET /query/stats
```

Get event statistics summary.

**Query Parameters** (all optional):
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `camera_name`: Filter by camera

**Response**:
```json
{
  "total_events": 1247,
  "unique_tracking_codes": 356,
  "cameras": {
    "Cam1": 589,
    "Cam2": 658
  },
  "date_range": {
    "start": "2025-10-01",
    "end": "2025-10-06"
  },
  "avg_duration": 28.5
}
```

## Cloud Sync

### Start Auto-Sync

```http
POST /api/sync/start/{source_id}
```

Start automatic synchronization for a cloud source.

**Path Parameters**:
- `source_id`: Video source ID (from video_sources table)

**Example**:
```bash
curl -X POST http://localhost:8080/api/sync/start/2
```

**Response**:
```json
{
  "success": true,
  "source_id": 2,
  "message": "Auto-sync started",
  "sync_interval_minutes": 15,
  "next_sync": "2025-10-06 14:50:00"
}
```

### Stop Auto-Sync

```http
POST /api/sync/stop/{source_id}
```

Stop automatic synchronization.

**Example**:
```bash
curl -X POST http://localhost:8080/api/sync/stop/2
```

**Response**:
```json
{
  "success": true,
  "source_id": 2,
  "message": "Auto-sync stopped"
}
```

### Force Sync Now

```http
POST /api/sync/force/{source_id}
```

Force immediate synchronization.

**Example**:
```bash
curl -X POST http://localhost:8080/api/sync/force/2
```

**Response**:
```json
{
  "success": true,
  "source_id": 2,
  "files_downloaded": 5,
  "total_size_mb": 247.3,
  "cameras": ["Cam1", "Cam2"],
  "sync_duration_seconds": 12.4
}
```

### Get Sync Status

```http
GET /api/sync/status/{source_id}
```

Get synchronization status for a source.

**Example**:
```bash
curl http://localhost:8080/api/sync/status/2
```

**Response**:
```json
{
  "source_id": 2,
  "source_name": "Google Storage",
  "sync_enabled": true,
  "last_sync_timestamp": "2025-10-06 14:35:00",
  "next_sync_timestamp": "2025-10-06 14:50:00",
  "sync_interval_minutes": 15,
  "last_sync_status": "success",
  "files_downloaded_count": 47,
  "total_download_size_mb": 1247.8,
  "error_count": 0
}
```

### List Downloaded Files

```http
GET /api/sync/files/{source_id}
```

List files downloaded from cloud source.

**Query Parameters** (optional):
- `camera_name`: Filter by camera
- `limit`: Max results (default: 100)

**Example**:
```bash
curl http://localhost:8080/api/sync/files/2?camera_name=Cam1&limit=10
```

**Response**:
```json
{
  "source_id": 2,
  "files": [
    {
      "id": 1,
      "camera_name": "Cam1",
      "original_filename": "video_20251006.mp4",
      "local_file_path": "/var/cache/cloud_downloads/Cam1/video_20251006.mp4",
      "file_size_bytes": 51248640,
      "download_timestamp": "2025-10-06 14:35:00",
      "is_processed": 1
    }
  ],
  "count": 1,
  "total_size_mb": 48.9
}
```

## Configuration

### Get Camera Configurations

```http
GET /api/camera-configurations
```

Get all configured cameras.

**Response**:
```json
{
  "success": true,
  "cameras": [
    {
      "name": "Cam1",
      "path": "Cam1",
      "stream_url": null,
      "resolution": "1920x1080",
      "codec": "h264",
      "source_type": "local",
      "source_name": "Local Storage",
      "is_selected": true
    },
    {
      "name": "Cam2",
      "path": "Cam2",
      "stream_url": null,
      "resolution": "1920x1080",
      "codec": "h264",
      "source_type": "cloud",
      "source_name": "Google Storage",
      "is_selected": true
    }
  ],
  "count": 2
}
```

### Get Configuration Steps

```http
GET /api/config/steps
```

Get configuration wizard steps status.

**Response**:
```json
{
  "steps": [
    {"step": 1, "name": "General Info", "completed": true},
    {"step": 2, "name": "Video Source", "completed": true},
    {"step": 3, "name": "Processing Settings", "completed": true},
    {"step": 4, "name": "ROI Configuration", "completed": true},
    {"step": 5, "name": "Packing Profile", "completed": true}
  ],
  "all_completed": true
}
```

### Save Configuration

```http
POST /api/config/save
```

Save configuration step data.

**Request Body**:
```json
{
  "step": 1,
  "data": {
    "country": "Vietnam",
    "timezone": "Asia/Ho_Chi_Minh",
    "brand_name": "MyCompany",
    "working_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "from_time": "00:00",
    "to_time": "00:00",
    "language": "vi"
  }
}
```

**Response**:
```json
{
  "success": true,
  "step": 1,
  "message": "Configuration saved successfully"
}
```

## System

### Health Check

```http
GET /health
```

Get system health status.

**Response**:
```json
{
  "status": "healthy",
  "service": "ePACK Desktop Backend",
  "version": "2.1.0",
  "timestamp": "2025-10-06T14:35:00",
  "modules": {
    "computer_vision": "enabled",
    "batch_processing": "enabled",
    "cloud_sync": "enabled",
    "payment_system": "enabled",
    "license_management": "enabled"
  },
  "cloud_functions": {
    "configured": true,
    "healthy": true,
    "services_status": "3/3"
  }
}
```

### System Info

```http
GET /api/system-info
```

Get detailed system information.

**Response**:
```json
{
  "service": "ePACK Desktop Backend",
  "version": "2.1.0",
  "status": "running",
  "features": [
    "Computer Vision Processing",
    "Video File Batch Processing",
    "Cloud Storage Sync",
    "Payment Processing",
    "License Management"
  ],
  "endpoints": {
    "health": "/health",
    "payment": "/payment",
    "settings": "/settings",
    "analytics": "/analytics"
  }
}
```

### Get Processing Status

```http
GET /api/processing-status
```

Get current file processing status.

**Response**:
```json
{
  "success": true,
  "processing_status": {
    "is_processing": true,
    "current_file": "DonggoiN_80cm25.mov",
    "processed_files": 47,
    "total_files": 100,
    "progress_percentage": 47.0,
    "processing_program": "First Run",
    "estimated_time_remaining": "15 minutes",
    "current_camera": "Cloud_Cam1",
    "started_at": "2025-09-29T08:00:00Z"
  }
}
```

## Payment & License

### Get License Status

```http
GET /api/license-status
```

Get current license status.

**Response**:
```json
{
  "initialized": true,
  "status": "valid",
  "message": "License valid",
  "expires_at": "2026-10-06",
  "days_remaining": 365,
  "product_type": "desktop",
  "features": ["full_access"]
}
```

### Get Pricing Packages

```http
GET /api/payment/packages
```

Get available pricing packages.

**Response**:
```json
{
  "success": true,
  "packages": {
    "monthly": {
      "id": "monthly_plan",
      "name": "Monthly Plan",
      "price": 299000,
      "currency": "VND",
      "duration_days": 30,
      "features": ["Full access", "Cloud sync", "Support"]
    },
    "yearly": {
      "id": "yearly_plan",
      "name": "Yearly Plan",
      "price": 2990000,
      "currency": "VND",
      "duration_days": 365,
      "features": ["Full access", "Cloud sync", "Priority support"],
      "discount_percentage": 17
    }
  }
}
```

### Create Payment

```http
POST /api/payment/create
```

Create payment transaction.

**Request Body**:
```json
{
  "package_id": "monthly_plan",
  "customer_email": "user@example.com"
}
```

**Response**:
```json
{
  "success": true,
  "payment_url": "https://payos.vn/payment/...",
  "app_trans_id": "VTRACK_20251006143000_ABC123",
  "amount": 299000,
  "currency": "VND"
}
```

## Error Responses

All endpoints follow consistent error response format:

### 400 Bad Request

```json
{
  "success": false,
  "error": "Missing required parameters: card and action"
}
```

### 404 Not Found

```json
{
  "success": false,
  "error": "Video file not found: /path/to/video.mp4"
}
```

### 500 Internal Server Error

```json
{
  "success": false,
  "error": "System error: Database connection failed",
  "details": "..."
}
```

## Rate Limiting

Currently no rate limiting implemented. Future versions may include:

- Max 100 requests/minute per IP
- Max 1000 requests/hour per IP
- Sync endpoints: Max 10 requests/minute

## CORS Configuration

**Allowed Origins**:
- `http://localhost:3000` (Frontend dev)

**Allowed Methods**:
- GET, POST, PUT, DELETE, OPTIONS

**Allowed Headers**:
- Content-Type, Authorization, X-Requested-With, Accept, Origin
- x-timezone-version, x-timezone-detection, x-client-offset, x-client-timezone, x-client-dst

**Credentials**: Supported

## WebSocket Endpoints

Currently not implemented. Future versions may include:

- Real-time processing progress: `ws://localhost:8080/ws/progress`
- Live event stream: `ws://localhost:8080/ws/events`
- Sync status updates: `ws://localhost:8080/ws/sync`

## API Versioning

Current version: **v1** (implicit, no version prefix)

Future versions will use URL prefix:
- v2: `/api/v2/...`
- v3: `/api/v3/...`

## Related Documentation

- [Installation Guide](../user-guide/installation.md)
- [ROI Configuration](../user-guide/roi-configuration.md)
- [Processing Modes](../user-guide/processing-modes.md)
- [Architecture Overview](../architecture/overview.md)

---

**Last Updated**: 2025-10-06
**API Version**: 1.0
**Base URL**: http://localhost:8080
