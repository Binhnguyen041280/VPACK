# Trace Tracking User Guide

**V_Track Event Tracking & Video Analysis**

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Search Methods](#search-methods)
4. [Understanding Search Results](#understanding-search-results)
5. [Advanced Features](#advanced-features)
6. [Platform Management](#platform-management)
7. [Export & Reporting](#export--reporting)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Overview

The Trace page is V_Track's core event tracking interface, allowing you to search for and analyze packing events captured from your camera system. It supports multiple search methods including manual tracking code entry, Excel/CSV batch uploads, and QR code image scanning.

### Key Features

- Real-time tracking code search
- Batch processing via Excel/CSV upload
- QR code image detection
- Platform-specific column mapping (Shopee, Lazada, TikTok, etc.)
- Interactive event timeline
- Video clip generation
- CSV export functionality

---

## Getting Started

### Prerequisites

Before using the Trace page, ensure:

1. Camera sources are configured (Step 3 of initial setup)
2. Video processing has run and detected events
3. Events table contains data in `events.db`

### Accessing the Trace Page

1. Navigate to the Trace page from the sidebar
2. The sidebar auto-collapses for maximum viewing space
3. Default time range: Last 3 days (configurable in header)

### Interface Components

**Header Controls** (Auto-hides after 3 seconds):
- **Time Range Selector**: From/To datetime pickers
- **Default Days Dropdown**: Quick presets (1, 3, 7, 14, 30 days)
- **Camera Filter**: Multi-select camera dropdown
- **Settings Icon**: Additional configuration options

**Chat Interface**:
- **Input Field**: Enter tracking codes or commands
- **Add Menu (+)**: Upload files/images
- **Submit Button**: Execute search

---

## Search Methods

### Method 1: Manual Tracking Code Entry

**Simple Search**:
```
TC001, TC002, TC003
```

**Supported Formats**:
- Comma-separated: `TC001, TC002, TC003`
- Space-separated: `TC001 TC002 TC003`
- Newline-separated (paste from Excel)
- Mixed formats (system auto-parses)

**API Endpoint**: `POST /query`

**Request Format**:
```json
{
  "tracking_codes": ["TC001", "TC002"],
  "from_time": "2025-01-15T00:00:00",
  "to_time": "2025-01-18T23:59:59",
  "timezone": "Asia/Ho_Chi_Minh",
  "cameras": ["Cloud_Cam1", "Cloud_Cam2"],
  "default_days": 3
}
```

**Response**:
- Returns `EventSearchResults` component
- Shows event count, timeline, and video info
- Displays tracking codes parsed from QR detection

---

### Method 2: Excel/CSV File Upload

**Workflow**:

1. **Upload File**: Click "+" menu → "Add File"
2. **Select Column**: System displays all columns (A, B, C, etc.)
3. **Choose Platform**: Select existing or create new platform mapping
4. **Auto-Query**: System extracts codes and searches automatically

**Supported File Formats**:
- Excel: `.xlsx`, `.xls`
- CSV: `.csv` (UTF-8 encoded)

**Example File Structure**:
```csv
Order ID, Tracking Code, Customer Name, Status
ORD001, TC123456, John Doe, Shipped
ORD002, TC789012, Jane Smith, Packed
```

**Platform Auto-Detection**:

If you type a platform name before uploading, the system auto-processes:
- Type: `shopee` → Upload file → Auto-maps to Shopee column
- Type: `lazada` → Upload file → Auto-maps to Lazada column
- Type: `tiktok` → Upload file → Auto-maps to TikTok column

**API Endpoints**:
- `POST /get-csv-headers`: Parse file structure
- `POST /parse-csv`: Extract tracking codes from column
- `POST /save-platform-preference`: Save column mapping

---

### Method 3: QR Code Image Upload

**Workflow**:

1. Click "+" menu → "Add Image"
2. Select image containing QR codes
3. System detects all QR codes automatically
4. Auto-queries with first detected code

**Supported Image Formats**:
- PNG, JPG, JPEG
- Maximum size: 10MB (recommended)
- Multiple QR codes supported

**API Endpoint**: `POST /api/qr-detection/detect-qr-image`

**Request**:
```json
{
  "image_content": "<base64_encoded_image>",
  "image_name": "qr_scan_001.jpg"
}
```

**Response**:
```json
{
  "success": true,
  "qr_count": 2,
  "qr_detections": ["TC123456", "TC789012"]
}
```

---

## Understanding Search Results

### Event Card Structure

Each event result displays:

**Event Header**:
- Event ID: `#12345`
- Camera Name: `Cloud_Cam1`
- Duration: `45s`

**Tracking Codes**:
- Parsed from QR detection
- Displayed as badges/chips
- Clickable for individual search

**Timeline Information**:
- **Start Time**: `2025-01-15 10:30:25`
- **End Time**: `2025-01-15 10:31:10`
- **Duration**: Calculated in seconds

**Video Information**:
- Video file path
- Frame timestamps (ts, te)
- Buffer settings applied

**Actions**:
- **View Details**: Opens event modal
- **Process Video**: Generate clip (demo mode)
- **Export**: Add to export queue

### Event Modal

Clicking an event opens detailed view:

```
Event Details - TC123456, TC789012

Camera: Cloud_Cam1
Start Time: 2025-01-15 10:30:25
End Time: 2025-01-15 10:31:10
Duration: 45s
Event ID: 12345

[Future: Video player, frame thumbnails, metadata]
```

---

## Advanced Features

### Time Range Configuration

**Manual Selection**:
1. Click time range fields in header
2. Select start and end datetime
3. System auto-updates results

**Quick Presets**:
- 1 day: Last 24 hours
- 3 days: Last 72 hours (default)
- 7 days: Last week
- 14 days: Last 2 weeks
- 30 days: Last month

**Timezone Handling**:
- All times stored in UTC (milliseconds)
- Display in `Asia/Ho_Chi_Minh` by default
- Configurable in general settings

### Camera Filtering

**Multi-Camera Selection**:
1. Click camera dropdown in header
2. Select/deselect cameras
3. Empty selection = all cameras

**API Behavior**:
```json
{
  "cameras": [],  // Empty = all cameras
  "cameras": ["Cloud_Cam1", "Cloud_Cam2"]  // Specific cameras only
}
```

**Data Source**: `active_cameras` view (database)

---

## Platform Management

### Platform Column Mappings

V_Track remembers which column contains tracking codes for each platform.

**Create New Platform**:

1. Upload file → Select column (e.g., "B")
2. System shows platform options
3. Enter new platform name: `Shopee Malaysia`
4. System saves mapping to database

**Database Table**: `platform_column_mappings`

```sql
CREATE TABLE platform_column_mappings (
    id INTEGER PRIMARY KEY,
    platform_name TEXT NOT NULL UNIQUE,
    column_letter TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

**Update Existing Platform**:
- Upload new file with same platform name
- Select different column
- System updates mapping (no duplicates)

**API Endpoints**:
- `GET /get-platform-list`: List all saved platforms
- `POST /save-platform-preference`: Create/update mapping

---

## Export & Reporting

### CSV Export

**Export Search Results**:

1. Perform search
2. Click "Export to CSV" button
3. File downloads with format:

```csv
Event ID,Tracking Codes,Camera,Start Time,End Time,Duration,Video File
12345,"TC001,TC002",Cloud_Cam1,2025-01-15 10:30:25,2025-01-15 10:31:10,45,video_001.mp4
12346,"TC003",Cloud_Cam2,2025-01-15 11:15:00,2025-01-15 11:15:30,30,video_002.mp4
```

**Filename Format**: `vtrack_export_YYYYMMDD_HHMMSS.csv`

### Video Processing (Demo Mode)

**Process Event**:

1. Click "Process" on event card
2. System simulates:
   - Download: 3 seconds (0-60% progress)
   - Cutting: 2 seconds (60-100% progress)
3. Creates demo file in output directory

**Output Location**: `/Users/annhu/Movies/VTrack/Output/`

**API Endpoints**:
- `POST /process-event`: Start processing
- `GET /process-status/<task_id>`: Check progress
- `POST /play-video`: Open output folder

---

## Troubleshooting

### No Events Found

**Possible Causes**:

1. **Time Range Too Narrow**: Expand date range
2. **Wrong Cameras Selected**: Check camera filter
3. **Tracking Code Format**: Ensure correct format
4. **No Processed Videos**: Run video processing first

**Solution**:
```sql
-- Check events table
SELECT COUNT(*) FROM events WHERE is_processed = 0;

-- Check time range
SELECT MIN(packing_time_start), MAX(packing_time_start)
FROM events;
```

### File Upload Errors

**"File CSV is empty"**:
- Ensure file has content
- Check encoding (UTF-8 recommended)

**"Column does not exist"**:
- Verify column letter matches file structure
- Column A = first column, B = second, etc.

**"Failed to parse CSV"**:
- Check file format (not corrupted)
- Try exporting to CSV again from Excel

### QR Code Detection Issues

**"No QR code found"**:
- Ensure QR code is clear and not distorted
- Image resolution: minimum 300x300px
- Try cropping to QR code area only

**API Returns Error**:
- Check image size (< 10MB)
- Verify image format (PNG/JPG)
- Check backend server status

### Platform Mapping Issues

**Duplicate Platform Names**:
- System enforces uniqueness
- Update existing platform instead

**Wrong Column Selected**:
- Re-upload file and select correct column
- System overwrites previous mapping

---

## Best Practices

### 1. Tracking Code Format

**Recommended Formats**:
- Use unique prefixes: `TC`, `TRK`, `PKG`
- Include numbers: `TC001234`
- Avoid special characters: `@`, `#`, `%`

**Good**:
```
TC001234
TRK-2025-001
PKG20250115001
```

**Avoid**:
```
TC@001  // Special characters
tc001   // Case-sensitive issues
001     // Too generic
```

### 2. Time Range Selection

- **Real-time Tracking**: Use 1-3 days
- **Weekly Reports**: Use 7 days
- **Monthly Analysis**: Use 30 days
- **Avoid**: > 60 days (performance impact)

### 3. File Upload Optimization

**Excel Files**:
- Keep files < 5MB for best performance
- Remove unnecessary columns before upload
- Use simple column names (A, B, C preferred)

**CSV Files**:
- UTF-8 encoding required
- Comma delimiter (standard)
- Remove header formatting (colors, merged cells)

### 4. Camera Configuration

- Name cameras descriptively: `Cloud_Cam1`, `Warehouse_A`
- Use consistent naming across system
- Filter cameras when searching specific areas

### 5. Performance Tips

**Large Datasets**:
- Narrow time range first
- Filter by specific cameras
- Export in batches (< 1000 events)

**Regular Maintenance**:
- Archive old events (> 90 days)
- Clean up processed videos
- Optimize database monthly

---

## Database Schema Reference

### Events Table

```sql
CREATE TABLE events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER,                    -- Start frame timestamp
    te INTEGER,                    -- End frame timestamp
    duration INTEGER,              -- Duration in seconds
    tracking_codes TEXT,           -- JSON array of codes
    video_file TEXT NOT NULL,
    packing_time_start INTEGER,   -- UTC milliseconds
    packing_time_end INTEGER,     -- UTC milliseconds
    camera_name TEXT,
    is_processed INTEGER DEFAULT 0,
    timezone_info TEXT,            -- JSON timezone metadata
    created_at_utc INTEGER,
    updated_at_utc INTEGER
);

-- Indexes for performance
CREATE INDEX idx_events_packing_time_utc
    ON events(packing_time_start, packing_time_end);
CREATE INDEX idx_events_processed_timezone
    ON events(is_processed, packing_time_start, camera_name);
```

### Active Cameras View

```sql
CREATE VIEW active_cameras AS
SELECT
    vs.id as source_id,
    vs.name as source_name,
    cc.camera_name,
    cc.folder_path,
    cc.is_selected
FROM video_sources vs
LEFT JOIN camera_configurations cc ON vs.id = cc.source_id
WHERE vs.active = 1 AND cc.is_selected = 1;
```

---

## Next Steps

- **[Cloud Sync Setup](./cloud-sync-advanced.md)**: Configure Google Drive integration
- **[License Management](./license-payment.md)**: Activate subscription
- **[API Reference](../api/query-endpoints.md)**: Developer documentation

---

**Last Updated**: 2025-10-06
**Version**: 1.0.0
**Author**: V_Track Documentation Team
