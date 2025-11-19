# Configuration Wizard Guide

The Configuration Wizard is your first step to setting up ePACK. This 5-step guided process collects all essential information needed for the system to start detecting and tracking packing events.

## Table of Contents

1. [Overview](#overview)
2. [When the Wizard Appears](#when-the-wizard-appears)
3. [Prerequisites](#prerequisites)
4. [Step-by-Step Guide](#step-by-step-guide)
   - [Step 1: Brand Name](#step-1-brand-name)
   - [Step 2: Location & Time](#step-2-location--time)
   - [Step 3: Video Source](#step-3-video-source)
   - [Step 4: ROI Configuration](#step-4-roi-configuration)
   - [Step 5: Timing & Storage](#step-5-timing--storage)
5. [After Wizard Completion](#after-wizard-completion)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)

## Overview

The Configuration Wizard is a **first-time setup process** that:

- Appears automatically when ePACK is launched for the first time
- Guides you through 5 sequential configuration steps
- Must be completed before the system can process videos
- Saves all settings to the database (general_info and processing_config tables)
- Can only be run once during initial setup

**Total Time**: 10-15 minutes (depending on video upload and ROI configuration)

**Steps Overview**:
```
Step 1: Brand Name         → Company/Organization identifier
Step 2: Location & Time    → Timezone, working hours, working days
Step 3: Video Source       → Local storage OR Google Drive
Step 4: ROI Configuration  → Hand detection zones for packing areas
Step 5: Timing & Storage   → Event detection parameters and storage paths
```

## When the Wizard Appears

The wizard appears when:

**First Launch**:
- Fresh installation with no prior configuration
- Database `general_info` table is empty
- No brand name has been set

**Not Triggered When**:
- Configuration already exists in database
- Wizard has been completed previously
- User navigates to VtrackConfig page for modifications

**Access URL**: `http://localhost:3000` (automatically redirects to wizard if needed)

## Prerequisites

Before starting the wizard, prepare:

### Required Items

**1. Company/Organization Name**
- Your business name or department identifier
- Example: "ABC Logistics", "Warehouse Team A"

**2. Location Information**
- Country name (e.g., "Vietnam", "United States")
- IANA timezone (e.g., "Asia/Ho_Chi_Minh", "America/New_York")
- Working days (Monday-Sunday selection)
- Working hours (e.g., 08:00-17:00)

**3. Video Source Setup**

Choose **ONE** of the following:

**Option A: Local Storage**
- Root directory path where videos are stored
- Example: `/Users/username/Videos/Packing`
- Camera folders organized under root path
- Folder structure:
  ```
  /Users/username/Videos/Packing/
  ├── Camera1/
  │   ├── video1.mp4
  │   └── video2.mp4
  ├── Camera2/
  │   └── video1.mp4
  └── Camera3/
      └── video1.mp4
  ```

**Option B: Google Drive**
- Google account with OAuth access
- Google Drive folder containing camera subfolders
- Browser access to complete OAuth authentication

**4. Sample Videos for ROI Configuration**
- **Duration**: 30-60 seconds per camera
- **Content**: Typical packing activity with clear hand movements
- **Quality**: Clear visibility, consistent lighting
- **Format**: .mp4, .mov, .avi, or .mkv
- One sample video per camera

**5. Timing Requirements**
- Minimum packing time (seconds): Shortest acceptable event duration
- Maximum packing time (seconds): Longest acceptable event duration
- Frame rate (fps): Video processing rate
- Storage preferences: Input/output directory paths

## Step-by-Step Guide

### Step 1: Brand Name

**Route**: `/step/brandname`

**Purpose**: Set your company or organization name to identify this ePACK installation.

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `brand_name` | String | Yes | Company/organization name | "ABC Logistics" |

**Validation Rules**:
- Minimum length: 1 character
- Maximum length: 100 characters
- No special validation required

**UI Instructions**:

1. **Enter Brand Name**:
   ```
   Field label: "Organization Name"
   Placeholder: "Enter your company or organization name"
   ```

2. **Validation Feedback**:
   - Real-time validation as you type
   - Character count displayed
   - Instant error messages if invalid

3. **Save and Continue**:
   - Click "Next" button
   - System saves to `general_info.brand_name`
   - Automatically proceeds to Step 2

**API Example**:

```bash
# GET current brand name
curl -X GET http://localhost:8080/step/brandname

# UPDATE brand name
curl -X PUT http://localhost:8080/step/brandname \
  -H "Content-Type: application/json" \
  -d '{"brand_name": "ABC Logistics"}'
```

**Response**:
```json
{
  "success": true,
  "message": "Brandname updated successfully",
  "data": {
    "brand_name": "ABC Logistics",
    "changed": true
  }
}
```

**Tips**:
- Use your official business name for consistency
- This name appears in reports and UI headers
- Can be changed later in VtrackConfig page

**Common Mistakes**:
- Leaving field empty
- Using temporary test names
- Including special characters that may cause encoding issues

---

### Step 2: Location & Time

**Route**: `/step/location-time`

**Purpose**: Configure regional settings, timezone, and working schedule for accurate event timestamping and filtering.

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `country` | String | Yes | Country name | "Vietnam" |
| `timezone` | String | Yes | IANA timezone identifier | "Asia/Ho_Chi_Minh" |
| `language` | String | Yes | Interface language code | "en" or "vi" |
| `working_days` | Array | Yes | Days of the week | ["Monday", "Tuesday", ...] |
| `from_time` | String | Yes | Work start time (24h) | "08:00" |
| `to_time` | String | Yes | Work end time (24h) | "17:00" |

**Validation Rules**:
- `country`: Non-empty string
- `timezone`: Must be valid IANA timezone (validated against pytz database)
- `working_days`: Array with 1-7 English day names (Monday, Tuesday, etc.)
- `from_time`/`to_time`: HH:MM format, 24-hour clock

**UI Instructions**:

1. **Select Country**:
   ```
   Dropdown or text input
   → Filters available timezones
   ```

2. **Select Timezone**:
   ```
   Searchable dropdown with timezone names
   Example: "Asia/Ho_Chi_Minh (GMT+7)"

   Enhanced display shows:
   - Timezone name
   - UTC offset
   - Current time in that timezone
   ```

3. **Choose Language**:
   ```
   Radio buttons or dropdown
   Options: English (en) | Vietnamese (vi)
   ```

4. **Select Working Days**:
   ```
   Checkboxes for each day:
   ☑ Monday
   ☑ Tuesday
   ☑ Wednesday
   ☑ Thursday
   ☑ Friday
   ☐ Saturday
   ☐ Sunday

   → Select all days when packing operations occur
   ```

5. **Set Working Hours**:
   ```
   From Time: [08:00] (time picker)
   To Time:   [17:00] (time picker)

   → Defines operational hours for event detection
   ```

6. **Save and Continue**:
   - Click "Next"
   - System validates timezone against IANA database
   - Saves to `general_info` table
   - Proceeds to Step 3

**API Example**:

```bash
# GET current location/time config
curl -X GET http://localhost:8080/step/location-time

# UPDATE location/time config
curl -X PUT http://localhost:8080/step/location-time \
  -H "Content-Type: application/json" \
  -d '{
    "country": "Vietnam",
    "timezone": "Asia/Ho_Chi_Minh",
    "language": "en",
    "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "from_time": "08:00",
    "to_time": "17:00"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Location/time configuration updated successfully",
  "data": {
    "country": "Vietnam",
    "timezone": "Asia/Ho_Chi_Minh",
    "timezone_enhanced": {
      "name": "Asia/Ho_Chi_Minh",
      "offset": "+07:00",
      "current_time": "2025-10-06 14:30:00"
    },
    "language": "en",
    "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "from_time": "08:00",
    "to_time": "17:00",
    "changed": true
  }
}
```

**Tips**:
- Use your actual business location's timezone
- Working days filter determines which events are shown in reports
- Working hours help identify regular vs. overtime events
- Timezone affects all event timestamps in the system

**Common Mistakes**:
- Selecting wrong timezone (use IANA format, not abbreviations like "PST")
- Not selecting all operational days
- Setting working hours that don't match actual operations
- Using 12-hour format instead of 24-hour (e.g., "5:00 PM" instead of "17:00")

**Timezone Validation**:

The system validates timezones against the IANA Time Zone Database:

```bash
# Validate timezone before saving
curl -X POST http://localhost:8080/step/location-time/validate-timezone \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Asia/Ho_Chi_Minh"}'
```

**Valid Timezone Examples**:
- "Asia/Ho_Chi_Minh" (Vietnam)
- "America/New_York" (US East Coast)
- "Europe/London" (UK)
- "Asia/Tokyo" (Japan)
- "Australia/Sydney" (Australia)

---

### Step 3: Video Source

**Route**: `/step/video-source`

**Purpose**: Configure where ePACK should read video files from - either local storage or Google Drive cloud storage.

**Source Options**:

**Option A: Local Storage**

Use when videos are stored on the same machine or accessible network drive.

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `sourceType` | String | Yes | Must be "local_storage" | "local_storage" |
| `inputPath` | String | Yes | Root directory path | "/Users/john/Videos/Packing" |
| `selectedCameras` | Array | Yes | Camera folder names | ["Camera1", "Camera2"] |
| `detectedFolders` | Array | No | Auto-detected folders | (read-only) |

**Option B: Google Drive**

Use when videos are uploaded to Google Drive folders.

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `sourceType` | String | Yes | Must be "cloud_storage" | "cloud_storage" |
| `selected_tree_folders` | Array | Yes | Google Drive folder IDs | ["1a2b3c4d5e", "6f7g8h9i0j"] |

**UI Instructions - Local Storage**:

1. **Select Source Type**:
   ```
   Radio buttons:
   ○ Local Storage (videos on this computer/network)
   ○ Google Drive (videos in cloud)
   ```

2. **Browse for Input Path**:
   ```
   Click "Browse" button
   → System file picker opens
   → Navigate to root video directory
   → Select folder containing camera subdirectories

   Example structure:
   /Users/john/Videos/Packing/
   ├── Camera1/
   ├── Camera2/
   └── Camera3/
   ```

3. **Auto-Detect Cameras**:
   ```
   After selecting input path:
   → System scans directory for subdirectories
   → Displays detected camera folders in checklist

   Detected Cameras:
   ☑ Camera1 (15 videos)
   ☑ Camera2 (12 videos)
   ☑ Camera3 (18 videos)
   ```

4. **Select Active Cameras**:
   ```
   Check cameras you want to process
   → Minimum: 1 camera
   → Maximum: All detected cameras
   ```

5. **Save and Continue**:
   - Click "Next"
   - System creates video source entry in database
   - Saves to `video_sources` and `processing_config` tables
   - Proceeds to Step 4

**UI Instructions - Google Drive**:

1. **Select Source Type**:
   ```
   Radio button:
   ● Google Drive
   ```

2. **Authenticate with Google**:
   ```
   Click "Connect Google Drive" button
   → Opens OAuth consent screen in new tab
   → Sign in to Google account
   → Grant permission to ePACK
   → Returns to wizard with success message
   ```

3. **Select Folders**:
   ```
   Tree view of Google Drive folders appears:

   📁 My Drive
   ├── 📁 Packing Videos
   │   ├── ☑ Camera1_Folder
   │   ├── ☑ Camera2_Folder
   │   └── ☐ Archive
   └── 📁 Other Documents

   → Check folders containing camera videos
   → Each folder = one camera source
   ```

4. **Confirm Selection**:
   ```
   Selected: 2 folders
   - Camera1_Folder (ID: 1a2b3c4d5e)
   - Camera2_Folder (ID: 6f7g8h9i0j)
   ```

5. **Auto-Sync Configuration**:
   ```
   After saving:
   → System automatically starts background sync
   → Downloads videos to local cache
   → Monitors folders for new uploads
   ```

**API Example - Local Storage**:

```bash
# UPDATE video source (local)
curl -X PUT http://localhost:8080/step/video-source \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "local_storage",
    "inputPath": "/Users/john/Videos/Packing",
    "selectedCameras": ["Camera1", "Camera2", "Camera3"],
    "detectedFolders": ["Camera1", "Camera2", "Camera3", "Archive"]
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Video source configuration updated successfully (ID: 1)",
  "data": {
    "sourceType": "local_storage",
    "inputPath": "/Users/john/Videos/Packing",
    "selectedCameras": ["Camera1", "Camera2", "Camera3"],
    "cameraPathsCount": 3,
    "videoSourceId": 1,
    "changed": true
  }
}
```

**API Example - Google Drive**:

```bash
# UPDATE video source (cloud)
curl -X PUT http://localhost:8080/step/video-source \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "cloud_storage",
    "selected_tree_folders": [
      {"id": "1a2b3c4d5e", "name": "Camera1_Folder"},
      {"id": "6f7g8h9i0j", "name": "Camera2_Folder"}
    ]
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Video source configuration updated successfully (ID: 2)",
  "data": {
    "sourceType": "cloud_storage",
    "selectedTreeFoldersCount": 2,
    "videoSourceId": 2,
    "auto_sync_started": true,
    "changed": true
  }
}
```

**Tips**:

**Local Storage**:
- Use absolute paths (e.g., `/Users/john/Videos` not `~/Videos`)
- Ensure ePACK has read permissions on directory
- Organize videos in camera-named subdirectories
- Keep folder names consistent (e.g., "Camera1", not "Cam1", "Camera_1", etc.)

**Google Drive**:
- Use a dedicated Google account for ePACK
- Organize one folder per camera for clean sync
- Monitor sync status in dashboard after wizard
- Initial sync may take time depending on video count

**Common Mistakes**:

Local Storage:
- Selecting file instead of directory
- Using relative paths
- Missing camera subdirectories
- Incorrect folder permissions

Google Drive:
- Not completing OAuth authentication
- Selecting root "My Drive" instead of specific folders
- Revoking permissions after setup
- Selecting folders with nested subfolders (flat structure recommended)

**Data Storage**:

Configuration is saved to:
- `video_sources` table: Source metadata and folder paths
- `processing_config` table: Backward compatibility for legacy code

**Post-Step Actions**:

For Google Drive:
- Auto-sync starts immediately
- Downloads begin in background
- Monitor progress in VtrackConfig → Cloud Sync tab

---

### Step 4: ROI Configuration

**Routes**: `/step/packing-area`, `/step/roi`

**Purpose**: Define detection zones (Regions of Interest) where hand movements indicate packing activity. This is the most critical and complex step of the wizard.

**What is ROI?**

ROI (Region of Interest) defines **where** in the video frame the system should look for packing events. Properly configured ROIs ensure:
- Accurate detection of packing activities
- Reduced false positives from background motion
- Optimized processing performance

**ROI Types**:

| ROI Type | Required | Description | Detection Method |
|----------|----------|-------------|------------------|
| **Packing Area** | Yes | Hand movement detection zone | AI hand landmark detection (MediaPipe) |
| **QR Trigger Area** | No | QR code scanning zone | QR code detection (pyzbar) |

**Important**: For detailed ROI concepts, coordinate systems, and advanced configuration, see [ROI Configuration Guide](roi-configuration.md).

**Prerequisites for This Step**:

Before starting Step 4, you must have:
- Completed Steps 1-3 (wizard enforces sequential completion)
- **Sample videos ready** for each camera
- Sample video requirements:
  - Duration: 30-60 seconds
  - Content: Typical packing activity with clear hand movements
  - Quality: Clear visibility, consistent lighting
  - Format: .mp4, .mov, .avi, or .mkv

**UI Instructions**:

**1. Camera Selection**:

```
Select Camera: [Dropdown ▼]
Options: Camera1, Camera2, Camera3

→ Choose camera to configure ROI for
→ Each camera requires separate ROI configuration
```

**2. Upload Sample Video**:

```
Sample Video for ROI Detection

[Drag & Drop Area]
or
[Browse Files] button

Supported formats: MP4, MOV, AVI, MKV
Recommended: 30-60 seconds of typical packing activity

After upload:
✓ Video uploaded: sample_cam1.mp4 (1.2 MB)
Duration: 45 seconds
Resolution: 1920x1080
```

**3. Video Preview**:

```
[Video Player]
→ Scrub through video to verify content
→ Ensure hands are clearly visible
→ Check lighting and camera angle
```

**4. Detect Packing Area** (Required):

```
Packing Area Configuration

Method: ○ Automatic Detection  ○ Manual Drawing

[Detect Packing Area] button

Progress:
→ Analyzing video...
→ Detecting hand landmarks...
→ Calculating bounding box...
→ ROI detected! ✓

Preview:
[Image showing video frame with green ROI box]

Detected ROI:
- Position: (100, 150)
- Size: 800 x 600 pixels
- Coverage: 25% of frame

[Adjust ROI] [Accept ROI] buttons
```

**Detection Process** (Automatic):
1. System processes sample video frame by frame
2. MediaPipe AI detects hand landmarks (21 points per hand)
3. Calculates bounding box around all detected hand positions
4. Expands box with margin (default: 60 pixels)
5. Returns ROI coordinates in [x, y, width, height] format

**5. Detect QR Trigger Area** (Optional):

```
QR Trigger Area (Optional)
Toggle: ☐ Enable QR Trigger Detection

When enabled:

[Detect QR Trigger Area] button

Progress:
→ Scanning video for QR codes...
→ QR code detected at frame 120
→ Trigger area calculated ✓

Preview:
[Image showing video frame with blue QR trigger box]

Detected QR Trigger:
- Position: (50, 100)
- Size: 400 x 300 pixels
```

**6. Review Combined ROI**:

```
Final ROI Preview

[Image showing both ROIs overlaid]
Green Box: Packing Area (800x600)
Blue Box: QR Trigger Area (400x300)

Cameras Configured: 1 of 3
- ✓ Camera1
- ✗ Camera2 (pending)
- ✗ Camera3 (pending)
```

**7. Save ROI Configuration**:

```
[Save & Configure Next Camera] button
or
[Save & Continue to Step 5] button (if all cameras configured)
```

**Repeat for Each Camera**:
- Configure ROI for each camera individually
- Each camera can have different ROI sizes based on view angle
- All cameras must have at least Packing Area configured

**API Example - ROI Detection**:

**Step 4a: Detect Packing Area**

```bash
# Detect ROI from video
curl -X POST http://localhost:8080/step/packing-area/roi-selection \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample_cam1.mp4",
    "camera_id": "Camera1",
    "step": "packing"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "ROI selection completed successfully",
  "data": {
    "roi": {
      "x": 100,
      "y": 150,
      "w": 800,
      "h": 600
    },
    "preview_path": "/resources/output_clips/CameraROI/camera_Camera1_roi_packing.jpg",
    "metadata": {
      "video_duration": 45,
      "frames_analyzed": 1350,
      "hands_detected": 423
    }
  }
}
```

**Step 4b: Finalize ROI**

```bash
# Save ROI to database
curl -X POST http://localhost:8080/step/packing-area/roi-finalization \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample_cam1.mp4",
    "camera_id": "Camera1",
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
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "ROI finalization completed successfully",
  "data": {
    "camera_id": "Camera1",
    "profile_name": "Camera1",
    "packing_area": [100, 150, 800, 600],
    "qr_trigger_area": [50, 100, 400, 300],
    "saved_to_database": true,
    "database_table": "packing_profiles"
  }
}
```

**Step 4c: Check All Cameras Status**

```bash
# Get ROI status for all cameras
curl -X GET http://localhost:8080/step/packing-area/cameras/status
```

**Response**:
```json
{
  "success": true,
  "data": {
    "cameras": [
      {
        "camera_name": "Camera1",
        "has_roi": true,
        "profile_name": "Camera1",
        "packing_area_configured": true,
        "qr_trigger_configured": true
      },
      {
        "camera_name": "Camera2",
        "has_roi": false,
        "profile_name": null
      },
      {
        "camera_name": "Camera3",
        "has_roi": false,
        "profile_name": null
      }
    ]
  }
}
```

**New ROI Endpoints (Web-Based)**:

For modern web-based ROI configuration:

```bash
# Get video metadata
curl -X GET "http://localhost:8080/api/config/step4/roi/video-info?video_path=/tmp/sample.mp4"

# Stream video for preview
curl -X GET "http://localhost:8080/api/config/step4/roi/stream-video?video_path=/tmp/sample.mp4"

# Extract frame at timestamp
curl -X POST http://localhost:8080/api/config/step4/roi/extract-frame \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample.mp4",
    "timestamp": 15.5,
    "format": "jpg",
    "quality": 85
  }'

# Validate ROI coordinates
curl -X POST http://localhost:8080/api/config/step4/roi/validate-roi \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample.mp4",
    "roi_data": [
      {"x": 100, "y": 150, "w": 800, "h": 600, "type": "packing_area"}
    ]
  }'

# Save ROI configuration
curl -X POST http://localhost:8080/api/config/step4/roi/save-roi-config \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "Camera1",
    "video_path": "/tmp/sample.mp4",
    "roi_data": [
      {"x": 100, "y": 150, "w": 800, "h": 600, "type": "packing_area"}
    ],
    "packing_method": "traditional"
  }'
```

**Tips**:

**Sample Video Best Practices**:
- Show multiple complete packing cycles (3-5 cycles)
- Ensure hands are clearly visible throughout
- Use consistent lighting matching production environment
- Avoid camera shake or movement
- Include typical worker movements

**ROI Size Guidelines**:
- Packing Area: 800x600 pixels typical for standard workstation
- QR Trigger: 400x300 pixels typical for QR scanner zone
- ROI should cover work zone but exclude background

**Multiple Cameras**:
- Each camera needs individual ROI configuration
- Camera angles affect ROI size (overhead vs. side view)
- Configure all cameras before proceeding to Step 5

**Common Mistakes**:

- **No hands detected**: Video too short, hands not visible, poor lighting
- **ROI too large**: Background motion included, use more focused sample
- **ROI too small**: Hands move outside box, use video with full range of motion
- **Wrong camera selected**: Always verify camera name before upload
- **Skipping QR trigger**: Required if your workflow uses QR scanning

**Data Storage**:

ROI configuration saved to `packing_profiles` table:

```sql
-- Example entry
INSERT INTO packing_profiles (
  profile_name,        -- "Camera1"
  packing_area,        -- "[100,150,800,600]"
  qr_trigger_area,     -- "[50,100,400,300]" or NULL
  min_packing_time,    -- 5 (default)
  scan_mode,           -- "traditional" or "qr"
  additional_params    -- JSON metadata
) VALUES (...);
```

**ROI Format**:

Coordinates stored as JSON array: `[x, y, width, height]`

```
x: Distance from left edge to ROI left edge (pixels)
y: Distance from top edge to ROI top edge (pixels)
width: ROI box width (pixels)
height: ROI box height (pixels)

Example: [100, 150, 800, 600]
→ Top-left at (100, 150)
→ Size: 800px wide × 600px tall
```

**Proceeding to Step 5**:

Wizard only allows proceeding when:
- All selected cameras have ROI configured
- At least Packing Area is set for each camera
- ROI data successfully saved to database

**Related Documentation**:
- [ROI Configuration Guide](roi-configuration.md) - Detailed ROI concepts and troubleshooting
- [Processing Modes](processing-modes.md) - How ROI affects event detection

---

### Step 5: Timing & Storage

**Route**: `/step/timing`

**Purpose**: Configure event detection timing parameters and storage paths for processed videos.

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `min_packing_time` | Integer | No | 5 | Minimum event duration (seconds) |
| `max_packing_time` | Integer | No | 300 | Maximum event duration (seconds) |
| `video_buffer` | Integer | No | 5 | Buffer before/after event (seconds) |
| `storage_duration` | Integer | No | 30 | Days to retain videos |
| `frame_rate` | Integer | No | 30 | Video frame rate (fps) |
| `frame_interval` | Integer | No | 1 | Process every N frames |
| `output_path` | String | No | "resources/output_clips" | Output directory path |

**Field Descriptions**:

**1. Minimum Packing Time**:
```
Purpose: Filter out brief movements that aren't real packing events
Range: 1-60 seconds
Default: 5 seconds

Example:
- Set to 5s: Ignores hand movements lasting < 5 seconds
- Set to 10s: Only detects events lasting 10+ seconds
- Use case: Higher value = fewer false positives
```

**2. Maximum Packing Time**:
```
Purpose: Split long continuous work into separate events
Range: 60-3600 seconds
Default: 300 seconds (5 minutes)

Example:
- Set to 300s: Events longer than 5 minutes are split
- Set to 600s: Events up to 10 minutes counted as single event
- Use case: Prevents extremely long events from skewing metrics
```

**3. Video Buffer**:
```
Purpose: Include extra frames before/after detected event
Range: 0-30 seconds
Default: 5 seconds

Example:
Event detected: 10:00:00 - 10:01:00 (60 seconds)
Buffer: 5 seconds
Saved video: 09:59:55 - 10:01:05 (70 seconds)

Use case: Captures context around events
```

**4. Storage Duration**:
```
Purpose: Auto-delete old videos after N days
Range: 1-365 days
Default: 30 days

Example:
- Set to 30 days: Videos deleted after 1 month
- Set to 90 days: Videos retained for 3 months
- Use case: Manage disk space automatically
```

**5. Frame Rate**:
```
Purpose: Video processing frame rate
Range: 1-60 fps
Default: 30 fps

Example:
- 30 fps: Process 30 frames per second
- 15 fps: Lower processing load
- 60 fps: Higher accuracy, more processing
```

**6. Frame Interval**:
```
Purpose: Skip frames to reduce processing load
Range: 1-30
Default: 1 (process every frame)

Example:
- Interval = 1: Process every frame (100% accuracy)
- Interval = 2: Process every 2nd frame (50% load)
- Interval = 5: Process every 5th frame (20% load)

Performance Impact:
Frame Rate: 30 fps, Interval: 1 → 30 frames/sec processed
Frame Rate: 30 fps, Interval: 5 → 6 frames/sec processed
```

**7. Output Path**:
```
Purpose: Directory for saving event video clips
Default: "resources/output_clips"

Example:
- "resources/output_clips" (default)
- "/data/vtrack/events"
- "/mnt/storage/packing_events"

Note: Must have write permissions
```

**UI Instructions**:

**1. Event Duration Settings**:

```
Event Detection Parameters

Minimum Packing Time: [5] seconds
→ Slider: 1 ←→ 60 seconds
→ Description: Ignore movements shorter than this

Maximum Packing Time: [300] seconds (5 minutes)
→ Slider: 60 ←→ 3600 seconds
→ Description: Split events longer than this

Video Buffer: [5] seconds
→ Slider: 0 ←→ 30 seconds
→ Description: Extra footage before/after event
```

**2. Performance Settings**:

```
Processing Performance

Frame Rate: [30] fps
→ Dropdown: 15, 20, 25, 30, 60
→ Description: Original video frame rate

Frame Interval: [1]
→ Slider: 1 ←→ 30
→ Description: Process every Nth frame
→ Current load: 100% (30 frames/sec)

Performance Estimate:
Daily frames processed: 2,592,000
Storage reduction: 0%
Category: High Accuracy

[Calculate Performance] button
```

**3. Storage Settings**:

```
Storage Configuration

Output Directory: [resources/output_clips]
[Browse...] button
→ Description: Where event clips will be saved

Storage Duration: [30] days
→ Slider: 1 ←→ 365 days
→ Description: Auto-delete videos older than this

Estimated Storage:
- Daily videos: ~10 GB
- 30-day retention: ~300 GB
```

**4. Review Summary**:

```
Configuration Summary

Event Detection:
- Min event: 5 seconds
- Max event: 300 seconds
- Buffer: 5 seconds

Performance:
- Frame rate: 30 fps
- Frame interval: 1 (100% accuracy)
- Processing load: High

Storage:
- Output: resources/output_clips
- Retention: 30 days
- Estimated: 300 GB/month

[Back] [Finish Setup] buttons
```

**5. Complete Wizard**:

```
Click "Finish Setup" button

Progress:
→ Saving timing configuration...
→ Updating processing_config table...
→ Triggering cloud sync (if Google Drive configured)...
→ Configuration complete! ✓

[Go to Dashboard] button
```

**API Example**:

```bash
# GET current timing config
curl -X GET http://localhost:8080/step/timing

# UPDATE timing config
curl -X PUT http://localhost:8080/step/timing \
  -H "Content-Type: application/json" \
  -d '{
    "min_packing_time": 5,
    "max_packing_time": 300,
    "video_buffer": 5,
    "storage_duration": 30,
    "frame_rate": 30,
    "frame_interval": 1,
    "output_path": "resources/output_clips"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Timing configuration updated successfully",
  "data": {
    "min_packing_time": 5,
    "max_packing_time": 300,
    "video_buffer": 5,
    "storage_duration": 30,
    "frame_rate": 30,
    "frame_interval": 1,
    "output_path": "resources/output_clips",
    "changed": true,
    "cloud_sync_triggered": true,
    "cloud_sync_results": [
      {
        "source_id": 1,
        "name": "Google Drive Camera Folders",
        "success": true
      }
    ]
  }
}
```

**Performance Estimation API**:

```bash
# Calculate performance estimates
curl -X POST http://localhost:8080/step/timing/performance-estimate \
  -H "Content-Type: application/json" \
  -d '{
    "frame_rate": 30,
    "frame_interval": 5,
    "video_duration_hours": 24
  }'
```

**Response**:
```json
{
  "success": true,
  "data": {
    "frame_processing": {
      "frames_per_second_original": 30,
      "frames_per_second_processed": 6.0,
      "processing_load_percentage": 20.0,
      "frames_skipped_percentage": 80.0
    },
    "daily_estimates": {
      "total_frames_24h": 2592000,
      "processed_frames_24h": 518400,
      "estimated_storage_reduction": "80.0%"
    },
    "performance_category": "high_performance",
    "recommendations": []
  }
}
```

**Tips**:

**Minimum Packing Time**:
- Start with default (5s)
- Increase if too many false positives
- Decrease if missing short genuine events
- Monitor first week and adjust

**Maximum Packing Time**:
- 300s (5 min) works for most workflows
- Increase for complex multi-step packing
- Decrease for rapid assembly lines

**Frame Interval Tuning**:
```
High Accuracy (Interval = 1):
- 100% frame processing
- Best detection accuracy
- High CPU/disk usage
- Use for: critical quality control

Balanced (Interval = 3-5):
- 20-33% frame processing
- Good detection accuracy
- Moderate resource usage
- Use for: standard operations

Performance (Interval = 10+):
- <10% frame processing
- Lower detection accuracy
- Minimal resource usage
- Use for: high-volume, less critical monitoring
```

**Storage Planning**:
```
Estimate formula:
Daily storage = (events/day) × (avg_duration + 2×buffer) × (bitrate/8)

Example:
- 100 events/day
- Average 60s duration
- 5s buffer → 70s total
- 5 Mbps bitrate
= 100 × 70s × (5Mbps/8) = 4,375 MB ≈ 4.3 GB/day

30-day retention: 4.3 GB × 30 = 129 GB
```

**Common Mistakes**:

- **Frame interval too high**: Missing events due to skipped frames
- **Min packing time too low**: Too many false positives
- **Output path without permissions**: Save fails, check write access
- **Storage duration too short**: Videos deleted before review
- **Buffer too large**: Excessive storage usage

**Post-Step Actions**:

After completing Step 5:

1. **Google Drive Auto-Sync**:
   - If cloud source configured in Step 3
   - System triggers initial sync immediately
   - Downloads videos from selected folders
   - Monitor sync progress in dashboard

2. **Configuration Saved**:
   - All settings written to `processing_config` table
   - Wizard marked as completed
   - User redirected to main dashboard

3. **System Ready**:
   - ePACK is now fully configured
   - Video processing can begin
   - Access VtrackConfig page for adjustments

**Data Storage**:

Configuration saved to `processing_config` table:

```sql
-- Single row in processing_config
UPDATE processing_config SET
  min_packing_time = 5,
  max_packing_time = 300,
  video_buffer = 5,
  storage_duration = 30,
  frame_rate = 30,
  frame_interval = 1,
  output_path = 'resources/output_clips'
WHERE id = 1;
```

---

## After Wizard Completion

Once you complete all 5 steps:

### Immediate Actions

**1. Dashboard Access**:
```
Wizard redirects to: http://localhost:3000/dashboard

Dashboard shows:
- Configuration status: ✓ Complete
- Active cameras: 3
- Video sources: 1 (Local Storage or Google Drive)
- ROI configured: 3/3 cameras
- System status: Ready
```

**2. Cloud Sync Status** (if Google Drive configured):
```
Navigate to: VtrackConfig → Cloud Sync Tab

Displays:
- Sync status: Active
- Last sync: 2025-10-06 14:30:00
- Files synced: 45 videos
- Next sync: 2025-10-06 15:30:00
- Storage used: 2.3 GB

[Force Sync Now] [Pause Sync] buttons
```

**3. First Video Processing**:
```
Option A: Automatic Processing
→ If videos already in source directory/Google Drive
→ System begins processing automatically
→ Monitor in Dashboard → Recent Events

Option B: Manual Upload
→ Add new videos to configured source folders
→ Wait for next scan cycle (every 15 minutes)
→ Or trigger manual scan in dashboard

Option C: Custom Processing
→ Dashboard → Custom Processing tab
→ Select specific videos to process
→ Set custom date range or camera filter
```

### Modifying Configuration

You **cannot** re-run the wizard, but you can modify all settings:

**Access**: `http://localhost:3000/vtrack-config`

**Available Modifications**:

**General Settings Tab**:
- Brand name
- Country, timezone, language
- Working days and hours

**Video Source Tab**:
- Add/remove cameras
- Change input path (local)
- Add/remove Google Drive folders (cloud)
- Switch between local and cloud (advanced)

**ROI Configuration Tab**:
- View current ROI for each camera
- Re-run ROI detection with new sample video
- Adjust ROI coordinates manually
- Add/remove QR trigger areas

**Processing Settings Tab**:
- Min/max packing time
- Video buffer
- Frame rate and interval
- Storage duration
- Output path

**Cloud Sync Tab** (if applicable):
- Sync frequency
- Folder mappings
- OAuth re-authentication
- Force sync or pause sync

### Verification Checklist

After wizard, verify:

- [ ] Brand name displayed correctly in UI header
- [ ] Timezone shows correct local time
- [ ] All cameras listed in dashboard
- [ ] ROI preview images accessible for each camera
- [ ] Video source shows correct folder paths
- [ ] Cloud sync running (if Google Drive configured)
- [ ] Output directory exists and is writable
- [ ] First test video processed successfully

### Next Steps

**1. Process Test Videos**:
```bash
# If local storage, add test video
cp /path/to/test.mp4 /configured/input/path/Camera1/

# Wait 15 minutes or trigger scan
# Check dashboard for new events
```

**2. Monitor First Events**:
```
Dashboard → Recent Events

Verify:
- Events detected correctly
- Timestamps accurate
- ROI boxes appear in preview
- Event clips saved to output path
```

**3. Fine-Tune Settings**:
```
Based on first week of operation:

Too many false positives?
→ Increase min_packing_time
→ Adjust ROI to exclude background

Missing events?
→ Decrease min_packing_time
→ Expand ROI to cover full work zone
→ Decrease frame_interval

Performance issues?
→ Increase frame_interval
→ Reduce frame_rate
```

**4. Production Deployment**:
```
After successful testing:
- Configure all production cameras
- Set up regular video upload workflow
- Train staff on system usage
- Set up monitoring and alerts
```

---

## Troubleshooting

### Wizard Not Appearing

**Symptoms**:
- Navigate to `http://localhost:3000`, wizard doesn't load
- Redirected to login or dashboard instead

**Solutions**:

1. **Check Database**:
   ```bash
   sqlite3 /Users/annhu/vtrack_app/ePACK/backend/database/events.db

   SELECT brand_name FROM general_info LIMIT 1;

   # If returns a value, wizard already completed
   # If empty or error, wizard should appear
   ```

2. **Clear Browser Cache**:
   ```bash
   # Clear browser cache and cookies
   # Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   ```

3. **Check Frontend Logs**:
   ```bash
   # Open browser console (F12)
   # Look for routing errors or API call failures
   ```

### Cannot Proceed to Next Step

**Symptoms**:
- "Next" button disabled
- Validation errors persist

**Solutions**:

**Step 1**:
- Ensure brand name is not empty
- Check for special characters causing issues

**Step 2**:
- Verify timezone is valid IANA format
- Ensure at least 1 working day selected
- Check from_time < to_time

**Step 3**:
- Local: Verify input path exists and has read permissions
- Local: At least 1 camera must be selected
- Cloud: Complete OAuth authentication
- Cloud: At least 1 folder selected

**Step 4**:
- All selected cameras must have ROI configured
- At least Packing Area required for each camera
- Verify ROI detection completed successfully

**Step 5**:
- All fields have valid values
- Output path is writable

### ROI Detection Fails

**Symptoms**:
- "No hands detected" error
- ROI detection times out
- Empty ROI returned

**Solutions**:

1. **Check Sample Video**:
   ```bash
   # Verify video is readable
   ffprobe /path/to/sample.mp4

   # Should show:
   # - Valid codec (h264, etc.)
   # - Resolution
   # - Duration > 30 seconds
   ```

2. **Improve Video Quality**:
   - Use longer sample (60-90 seconds)
   - Ensure hands clearly visible
   - Improve lighting in video
   - Avoid camera shake

3. **Check Backend Logs**:
   ```bash
   tail -f /Users/annhu/vtrack_app/ePACK/backend/var/logs/app_latest.log | grep "ROI"

   # Look for:
   # - MediaPipe errors
   # - Hand detection failures
   # - File access errors
   ```

4. **Manual ROI Configuration**:
   ```bash
   # If automatic detection fails, set ROI manually in database
   sqlite3 backend/database/events.db

   INSERT INTO packing_profiles (
     profile_name, packing_area, min_packing_time
   ) VALUES (
     'Camera1', '[100,150,800,600]', 5
   );
   ```

### Google Drive Authentication Fails

**Symptoms**:
- OAuth popup blocked
- "Authentication failed" error
- Cannot see Google Drive folders

**Solutions**:

1. **Check Browser Popup Blocker**:
   ```
   Allow popups for localhost:3000
   Try authentication again
   ```

2. **Re-authenticate**:
   ```
   VtrackConfig → Cloud Sync Tab
   [Disconnect Google Drive] button
   [Connect Google Drive] button
   Complete OAuth flow again
   ```

3. **Verify OAuth Credentials**:
   ```bash
   # Check client_secrets.json exists
   ls -la backend/modules/sources/tokens/client_secrets.json

   # Verify credentials valid in Google Cloud Console
   # Project → APIs & Services → Credentials
   ```

4. **Check Permissions**:
   ```
   OAuth consent screen should request:
   - Google Drive API access
   - Read files permissions

   Ensure permissions granted during OAuth flow
   ```

### Configuration Not Saving

**Symptoms**:
- Click "Next" but settings not saved
- Error message on save
- Settings reset after refresh

**Solutions**:

1. **Check Database Permissions**:
   ```bash
   # Verify database is writable
   ls -la /Users/annhu/vtrack_app/ePACK/backend/database/events.db

   # Should show: -rw-r--r-- (at minimum)
   # If read-only: chmod 644 events.db
   ```

2. **Check Backend Logs**:
   ```bash
   tail -f backend/var/logs/app_latest.log | grep "ERROR"

   # Look for:
   # - Database connection errors
   # - SQL syntax errors
   # - Permission denied errors
   ```

3. **Verify API Endpoints**:
   ```bash
   # Test Step 1 endpoint
   curl -X GET http://localhost:8080/step/brandname

   # Should return JSON response
   # If 404 or 500: backend not running or routes not registered
   ```

4. **Check Network Tab**:
   ```
   Browser DevTools (F12) → Network tab
   Monitor API calls during wizard
   Look for:
   - 400/500 status codes
   - CORS errors
   - Timeout errors
   ```

### Cannot Complete Step 4 (All Cameras)

**Symptoms**:
- Some cameras configured, others showing errors
- "Next" button disabled
- Cannot proceed to Step 5

**Solutions**:

1. **Check Camera Status**:
   ```bash
   curl -X GET http://localhost:8080/step/packing-area/cameras/status

   # Shows which cameras have ROI configured
   # Identify cameras without configuration
   ```

2. **Configure Missing Cameras**:
   ```
   For each camera without ROI:
   1. Upload sample video
   2. Run detection
   3. Save ROI
   4. Verify in status API
   ```

3. **Skip Problematic Cameras** (temporary):
   ```
   Go back to Step 3
   Deselect cameras that cannot be configured
   Proceed with configured cameras only
   Add problematic cameras later via VtrackConfig
   ```

### Wizard Hangs or Freezes

**Symptoms**:
- UI unresponsive
- Infinite loading spinner
- Browser tab frozen

**Solutions**:

1. **Check Backend Status**:
   ```bash
   # Verify backend is running
   ps aux | grep "python.*app.py"

   # Check backend logs for errors
   tail -f backend/var/logs/app_latest.log
   ```

2. **Restart Backend**:
   ```bash
   # Stop backend
   pkill -f "python.*app.py"

   # Start backend
   cd /Users/annhu/vtrack_app/ePACK/backend
   python app.py
   ```

3. **Clear Frontend Cache**:
   ```
   Hard refresh: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)
   Clear browser cache completely
   Restart browser
   ```

4. **Check System Resources**:
   ```bash
   # Check CPU/memory usage
   top

   # ROI detection is CPU-intensive
   # Ensure sufficient resources available
   ```

---

## API Reference

### Step 1: Brand Name

**GET /step/brandname**
```bash
curl -X GET http://localhost:8080/step/brandname
```

**PUT /step/brandname**
```bash
curl -X PUT http://localhost:8080/step/brandname \
  -H "Content-Type: application/json" \
  -d '{"brand_name": "ABC Logistics"}'
```

**POST /step/brandname/validate**
```bash
curl -X POST http://localhost:8080/step/brandname/validate \
  -H "Content-Type: application/json" \
  -d '{"brand_name": "Test Name"}'
```

**GET /step/brandname/statistics**
```bash
curl -X GET http://localhost:8080/step/brandname/statistics
```

### Step 2: Location & Time

**GET /step/location-time**
```bash
curl -X GET http://localhost:8080/step/location-time
```

**PUT /step/location-time**
```bash
curl -X PUT http://localhost:8080/step/location-time \
  -H "Content-Type: application/json" \
  -d '{
    "country": "Vietnam",
    "timezone": "Asia/Ho_Chi_Minh",
    "language": "en",
    "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "from_time": "08:00",
    "to_time": "17:00"
  }'
```

**POST /step/location-time/validate-timezone**
```bash
curl -X POST http://localhost:8080/step/location-time/validate-timezone \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Asia/Ho_Chi_Minh"}'
```

**POST /step/location-time/validate-working-days**
```bash
curl -X POST http://localhost:8080/step/location-time/validate-working-days \
  -H "Content-Type: application/json" \
  -d '{"working_days": ["Monday", "Tuesday"]}'
```

**GET /step/location-time/defaults**
```bash
curl -X GET http://localhost:8080/step/location-time/defaults
```

### Step 3: Video Source

**GET /step/video-source**
```bash
curl -X GET http://localhost:8080/step/video-source
```

**PUT /step/video-source**
```bash
# Local storage
curl -X PUT http://localhost:8080/step/video-source \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "local_storage",
    "inputPath": "/path/to/videos",
    "selectedCameras": ["Camera1", "Camera2"]
  }'

# Cloud storage
curl -X PUT http://localhost:8080/step/video-source \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "cloud_storage",
    "selected_tree_folders": [
      {"id": "1a2b3c", "name": "Camera1"}
    ]
  }'
```

**POST /step/video-source/validate**
```bash
curl -X POST http://localhost:8080/step/video-source/validate \
  -H "Content-Type: application/json" \
  -d '{
    "sourceType": "local_storage",
    "inputPath": "/path/to/videos",
    "selectedCameras": ["Camera1"]
  }'
```

**GET /step/video-source/cameras**
```bash
curl -X GET http://localhost:8080/step/video-source/cameras
```

**GET /step/video-source/sync-status**
```bash
curl -X GET http://localhost:8080/step/video-source/sync-status
```

### Step 4: ROI Configuration

**GET /step/packing-area**
```bash
curl -X GET http://localhost:8080/step/packing-area
```

**PUT /step/packing-area**
```bash
curl -X PUT http://localhost:8080/step/packing-area \
  -H "Content-Type: application/json" \
  -d '{
    "detection_zones": [
      {
        "camera_name": "Camera1",
        "packing_area": [100, 150, 800, 600],
        "trigger_area": [50, 100, 400, 300]
      }
    ]
  }'
```

**GET /step/packing-area/cameras/status**
```bash
curl -X GET http://localhost:8080/step/packing-area/cameras/status
```

**GET /step/packing-area/camera/{camera_name}**
```bash
curl -X GET http://localhost:8080/step/packing-area/camera/Camera1
```

**POST /step/packing-area/roi-selection**
```bash
curl -X POST http://localhost:8080/step/packing-area/roi-selection \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample.mp4",
    "camera_id": "Camera1",
    "step": "packing"
  }'
```

**POST /step/packing-area/roi-finalization**
```bash
curl -X POST http://localhost:8080/step/packing-area/roi-finalization \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample.mp4",
    "camera_id": "Camera1",
    "rois": [
      {"type": "packing", "x": 100, "y": 150, "w": 800, "h": 600}
    ]
  }'
```

**GET /step/packing-area/statistics**
```bash
curl -X GET http://localhost:8080/step/packing-area/statistics
```

**Web-Based ROI Endpoints**:

**GET /api/config/step4/roi/video-info**
```bash
curl -X GET "http://localhost:8080/api/config/step4/roi/video-info?video_path=/tmp/sample.mp4"
```

**GET /api/config/step4/roi/stream-video**
```bash
curl -X GET "http://localhost:8080/api/config/step4/roi/stream-video?video_path=/tmp/sample.mp4"
```

**POST /api/config/step4/roi/extract-frame**
```bash
curl -X POST http://localhost:8080/api/config/step4/roi/extract-frame \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample.mp4",
    "timestamp": 15.5,
    "format": "jpg",
    "quality": 85
  }'
```

**POST /api/config/step4/roi/validate-roi**
```bash
curl -X POST http://localhost:8080/api/config/step4/roi/validate-roi \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/sample.mp4",
    "roi_data": [
      {"x": 100, "y": 150, "w": 800, "h": 600, "type": "packing_area"}
    ]
  }'
```

**POST /api/config/step4/roi/save-roi-config**
```bash
curl -X POST http://localhost:8080/api/config/step4/roi/save-roi-config \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "Camera1",
    "video_path": "/tmp/sample.mp4",
    "roi_data": [
      {"x": 100, "y": 150, "w": 800, "h": 600, "type": "packing_area"}
    ],
    "packing_method": "traditional"
  }'
```

**POST /api/config/step4/roi/upload-video**
```bash
curl -X POST http://localhost:8080/api/config/step4/roi/upload-video \
  -F "video=@/path/to/sample.mp4"
```

### Step 5: Timing & Storage

**GET /step/timing**
```bash
curl -X GET http://localhost:8080/step/timing
```

**PUT /step/timing**
```bash
curl -X PUT http://localhost:8080/step/timing \
  -H "Content-Type: application/json" \
  -d '{
    "min_packing_time": 5,
    "max_packing_time": 300,
    "video_buffer": 5,
    "storage_duration": 30,
    "frame_rate": 30,
    "frame_interval": 1,
    "output_path": "resources/output_clips"
  }'
```

**POST /step/timing/validate**
```bash
curl -X POST http://localhost:8080/step/timing/validate \
  -H "Content-Type: application/json" \
  -d '{
    "min_packing_time": 5,
    "max_packing_time": 300
  }'
```

**GET /step/timing/statistics**
```bash
curl -X GET http://localhost:8080/step/timing/statistics
```

**GET /step/timing/defaults**
```bash
curl -X GET http://localhost:8080/step/timing/defaults
```

**POST /step/timing/performance-estimate**
```bash
curl -X POST http://localhost:8080/step/timing/performance-estimate \
  -H "Content-Type: application/json" \
  -d '{
    "frame_rate": 30,
    "frame_interval": 5,
    "video_duration_hours": 24
  }'
```

### Common Response Format

All wizard endpoints return responses in this format:

**Success Response**:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    "field1": "value1",
    "field2": "value2",
    "changed": true
  }
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Error description",
  "step": "step1",
  "field": "brand_name",
  "timestamp": "2025-10-06T14:30:00"
}
```

**Validation Response**:
```json
{
  "success": true,
  "valid": true,
  "message": "Validation passed",
  "data": {
    "validated_field": "value"
  }
}
```

---

## Related Documentation

- [Installation Guide](installation.md) - Set up ePACK before running wizard
- [ROI Configuration Guide](roi-configuration.md) - Detailed ROI concepts and troubleshooting
- [Cloud Sync Advanced](cloud-sync-advanced.md) - Google Drive integration details
- [Processing Modes](processing-modes.md) - How configuration affects video processing
- [Trace Tracking](trace-tracking.md) - Event tracking features after setup

---

**Last Updated**: 2025-10-06
**Version**: 1.0
**Guide Type**: User Documentation
