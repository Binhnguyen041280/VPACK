# ROI Configuration Guide

Region of Interest (ROI) configuration is a critical step in ePACK setup. This guide explains how to properly configure detection zones for accurate event detection.

## Table of Contents

1. [Understanding ROI](#understanding-roi)
2. [ROI Types](#roi-types)
3. [ROI Configuration Workflow](#roi-configuration-workflow)
4. [Coordinate System](#coordinate-system)
5. [Best Practices](#best-practices)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)

## Understanding ROI

ROI (Region of Interest) defines **where** the system should look for packing events in your video footage. Properly configured ROIs ensure:

- **Accurate Detection**: Only relevant areas are analyzed
- **Performance Optimization**: Reduced processing time
- **False Positive Reduction**: Ignore irrelevant motion outside work zones

### Why ROI Matters

Without ROI configuration:
- ❌ System processes entire video frame (slow)
- ❌ Detects irrelevant movements (false positives)
- ❌ Misses events due to background noise

With ROI configuration:
- ✅ Focused analysis on work zones (fast)
- ✅ Accurate event detection (high precision)
- ✅ Reduced false positives (clean data)

## ROI Types

ePACK supports two types of ROI:

### 1. Packing Area (Required)

**Purpose**: Define where hand movements indicate packing activity.

**Detection Method**: AI-powered hand landmark detection using MediaPipe.

**How it works**:
1. System analyzes sample video
2. Detects hand movements using 21-point hand landmarks
3. Calculates bounding box around detected hand positions
4. Expands box with configurable margin
5. Saves as `packing_area` in database

**Use Case**: Primary detection zone for all packing events.

**Example**:
```json
{
  "packing_area": [100, 150, 800, 600]
  // Format: [x, y, width, height]
  // x=100, y=150: Top-left corner
  // width=800, height=600: Box dimensions
}
```

### 2. QR Trigger Area (Optional)

**Purpose**: Define where QR code scanning occurs to trigger event detection.

**Detection Method**: QR code detection using pyzbar library.

**How it works**:
1. Scans video for QR codes
2. Identifies QR code locations
3. Creates bounding box around QR zones
4. Saves as `qr_trigger_area` in database

**Use Case**: Advanced workflow where QR scanning initiates packing sequence.

**Example**:
```json
{
  "qr_trigger_area": [50, 100, 400, 300]
  // Format: [x, y, width, height]
}
```

## ROI Configuration Workflow

### Step-by-Step Process

#### 1. Prepare Sample Video

**Requirements**:
- **Duration**: 30-60 seconds minimum
- **Content**: Typical packing activity
- **Quality**: Clear visibility of hands/QR codes
- **Lighting**: Consistent with production environment
- **Camera Angle**: Same as operational setup

**Best Sample Video Characteristics**:
```
✅ Multiple packing cycles shown
✅ Clear hand movements visible
✅ QR code scanning visible (if applicable)
✅ Representative of typical workflow
✅ No obstructions or glare
```

#### 2. Access ROI Configuration (UI Method)

**Via Configuration Wizard**:
1. Navigate to `http://localhost:3000`
2. Complete Steps 1-3 of setup wizard
3. Reach "Step 4: ROI Configuration"
4. Select camera from dropdown
5. Upload sample video

**Via Direct Access**:
1. Go to Settings → ROI Configuration
2. Select camera
3. Upload video

#### 3. Configure Packing Area

**Automatic Detection (Recommended)**:

1. **Upload Video**:
   ```
   Click "Select Video File"
   → Choose .mp4/.mov/.avi file
   → Wait for upload confirmation
   ```

2. **Run Detection**:
   ```
   Click "Detect Packing Area" button
   → System analyzes video (15-30 seconds)
   → Hand landmarks detected automatically
   → ROI calculated and displayed
   ```

3. **Review Preview**:
   ```
   Preview image shows:
   - Original frame
   - Detected ROI box (green)
   - Hand landmarks (if visible)
   ```

4. **Adjust if Needed**:
   - If ROI too small: Use video with more hand movement
   - If ROI too large: Check for background motion
   - If no ROI detected: Ensure hands clearly visible

#### 4. Configure QR Trigger Area (Optional)

**When to Use**:
- Workflow includes QR code scanning step
- QR scanning triggers packing sequence
- Need multi-stage event detection

**Steps**:

1. **Enable QR Detection**:
   ```
   Toggle "Enable QR Trigger Area" switch
   ```

2. **Run QR Detection**:
   ```
   Click "Detect Trigger Area" button
   → System scans video for QR codes
   → QR locations identified
   → Trigger area calculated
   ```

3. **Review QR Preview**:
   ```
   Preview shows:
   - QR code positions
   - Trigger zone box (blue)
   - Detected QR data (if readable)
   ```

#### 5. Finalize ROI

**Save Configuration**:

1. **Verify Both ROIs**:
   ```
   Review combined preview showing:
   - Packing Area (green box)
   - QR Trigger Area (blue box, if enabled)
   - Original video frame
   ```

2. **Click "Finalize ROI"**:
   ```
   System performs:
   → Saves ROI to packing_profiles table
   → Creates preview images in resources/output_clips/CameraROI/
   → Returns success confirmation
   ```

3. **Database Entry Created**:
   ```sql
   INSERT INTO packing_profiles (
     profile_name,
     packing_area,
     qr_trigger_area,
     min_packing_time,
     ...
   ) VALUES (
     'Cam1',
     '[100,150,800,600]',
     '[50,100,400,300]',
     10,
     ...
   );
   ```

### Step-by-Step Process (API Method)

For programmatic configuration:

#### 1. Upload Video to Server

```bash
# Copy video to accessible location
cp /path/to/sample.mp4 /tmp/roi_sample.mp4
```

#### 2. Call ROI Detection API

**Detect Packing Area**:
```bash
curl -X POST http://localhost:8080/run-select-roi \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/roi_sample.mp4",
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

**Detect QR Trigger Area** (Optional):
```bash
curl -X POST http://localhost:8080/run-select-roi \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/tmp/roi_sample.mp4",
    "camera_id": "Cam1",
    "step": "trigger"
  }'
```

#### 3. Finalize ROI Configuration

```bash
curl -X POST http://localhost:8080/finalize-roi \
  -H "Content-Type: application/json" \
  -d '{
    "videoPath": "/tmp/roi_sample.mp4",
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

## Coordinate System

### Understanding ROI Format

ePACK uses two coordinate formats:

#### Format 1: [x, y, width, height] (Database Storage)

**Used in**: `packing_profiles` table

```json
{
  "packing_area": "[100, 150, 800, 600]"
}
```

**Meaning**:
- `x = 100`: Distance from left edge to ROI left edge
- `y = 150`: Distance from top edge to ROI top edge
- `width = 800`: ROI box width in pixels
- `height = 600`: ROI box height in pixels

**Example**:
```
Video Resolution: 1920x1080
ROI: [100, 150, 800, 600]

┌─────────────────────────┐ 1920px
│                         │
│  (100,150)              │
│    ┌──────800px────┐    │
│    │               │    │
│    │   PACKING     │    │
│    │     AREA      │600px
│    │               │    │
│    └───────────────┘    │
│                         │
└─────────────────────────┘
           1080px
```

#### Format 2: [x1, y1, x2, y2] (Legacy/Temporary)

**Used in**: Some intermediate processing

```json
{
  "roi": "[100, 150, 900, 750]"
}
```

**Meaning**:
- `x1 = 100`: Top-left X coordinate
- `y1 = 150`: Top-left Y coordinate
- `x2 = 900`: Bottom-right X coordinate (100 + 800)
- `y2 = 750`: Bottom-right Y coordinate (150 + 600)

**Conversion**:
```python
# [x1, y1, x2, y2] → [x, y, width, height]
x = x1
y = y1
width = x2 - x1
height = y2 - y1

# [x, y, width, height] → [x1, y1, x2, y2]
x1 = x
y1 = y
x2 = x + width
y2 = y + height
```

### Coordinate Origin

```
(0,0) ─────────────────→ X-axis (width)
  │
  │    ┌─────────────┐
  │    │   VIDEO     │
  │    │   FRAME     │
  │    └─────────────┘
  ↓
Y-axis (height)
```

- **Origin**: Top-left corner (0, 0)
- **X-axis**: Increases rightward
- **Y-axis**: Increases downward

## Best Practices

### Sample Video Selection

**DO ✅**:
- Use video with clear, unobstructed hand movements
- Ensure consistent lighting
- Include multiple packing cycles
- Use video from actual production environment
- Keep video length 30-90 seconds

**DON'T ❌**:
- Use video with camera shake or blur
- Include videos with changing lighting
- Use test videos with unrealistic movements
- Upload excessively long videos (>5 minutes)

### ROI Size Guidelines

**Packing Area**:
```
Minimum: 400x300 pixels (small work zone)
Optimal: 800x600 pixels (standard packing table)
Maximum: 1600x1200 pixels (large work area)

Too Small → Misses movements outside box
Too Large → Includes irrelevant background motion
```

**QR Trigger Area**:
```
Minimum: 200x150 pixels (single QR code)
Optimal: 400x300 pixels (QR scanning zone)
Maximum: 800x600 pixels (multi-code area)

Should be smaller than packing area
Should cover typical QR scanning positions
```

### Multiple Cameras

**Strategy 1: Individual Configuration**
```
Camera 1 (Overhead): Large packing area (1200x900)
Camera 2 (Side view): Medium packing area (800x600)
Camera 3 (QR scanner): Small QR trigger area (400x300)

→ Each camera optimized for its view angle
```

**Strategy 2: Consistent Configuration**
```
All cameras: Same ROI dimensions (800x600)
→ Easier to manage, consistent detection
→ Requires similar camera positioning
```

### ROI Validation

**After configuration, verify**:

1. **Check Preview Images**:
   ```bash
   ls resources/output_clips/CameraROI/
   # Should contain:
   # camera_Cam1_roi_packing.jpg
   # camera_Cam1_roi_trigger.jpg (if configured)
   # camera_Cam1_roi_final_timestamp.jpg
   ```

2. **Verify Database Entry**:
   ```bash
   sqlite3 backend/database/events.db \
     "SELECT profile_name, packing_area, qr_trigger_area FROM packing_profiles WHERE profile_name='Cam1';"
   ```

3. **Test with Sample Video**:
   - Run custom processing on sample video
   - Check if events are detected correctly
   - Verify event timestamps match expected packing times

## API Reference

### ROI Detection Endpoints

#### POST /run-select-roi

Detect ROI from sample video.

**Request**:
```json
{
  "video_path": "/path/to/video.mp4",
  "camera_id": "Cam1",
  "step": "packing" | "trigger"
}
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
  "preview_path": "/resources/output_clips/CameraROI/camera_Cam1_roi_packing.jpg"
}
```

#### POST /finalize-roi

Save ROI configuration to database.

**Request**:
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
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "profile_name": "Cam1",
  "packing_area": [100, 150, 800, 600],
  "message": "ROI saved to packing_profiles"
}
```

#### GET /get-roi-frame

Retrieve ROI preview image.

**Request**:
```
GET /get-roi-frame?camera_id=Cam1&file=roi_packing.jpg
```

**Response**: JPEG image (binary)

#### GET /get-final-roi-frame

Retrieve combined ROI preview.

**Request**:
```
GET /get-final-roi-frame?camera_id=Cam1
```

**Response**: JPEG image with all ROIs overlaid (binary)

### Database Schema

**packing_profiles table**:

```sql
CREATE TABLE packing_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_name TEXT NOT NULL,           -- Camera ID
  packing_area TEXT,                    -- [x, y, width, height]
  qr_trigger_area TEXT,                 -- [x, y, width, height]
  min_packing_time INTEGER,             -- Minimum event duration (seconds)
  jump_time_ratio REAL,                 -- Event splitting ratio
  mvd_jump_ratio REAL,                  -- MVD detection ratio
  scan_mode TEXT,                       -- "full" or "partial"
  fixed_threshold INTEGER,              -- QR detection threshold
  margin INTEGER,                       -- ROI expansion margin (pixels)
  additional_params TEXT                -- JSON for extra config
);
```

**Example Entry**:
```sql
INSERT INTO packing_profiles VALUES (
  1,
  'Cam1',
  '[100,150,800,600]',
  '[50,100,400,300]',
  10,
  0.5,
  NULL,
  'full',
  20,
  60,
  '{}'
);
```

## Troubleshooting

### No ROI Detected

**Symptoms**:
- ROI detection returns empty/null
- Preview image shows no bounding box

**Solutions**:
1. **Check Video Quality**:
   ```bash
   ffprobe /path/to/video.mp4
   # Verify resolution, codec, duration
   ```

2. **Verify Hand Visibility**:
   - Ensure hands clearly visible in frame
   - Check for sufficient lighting
   - Remove obstructions

3. **Adjust Detection Parameters**:
   - Increase motion threshold
   - Use longer video sample
   - Try different camera angle

### ROI Too Large/Small

**Symptoms**:
- ROI covers entire frame
- ROI misses packing area

**Solutions**:
1. **Reconfigure with Better Video**:
   - Use video with focused packing activity
   - Avoid videos with camera movement

2. **Manual ROI Adjustment** (Advanced):
   ```bash
   # Update ROI manually in database
   sqlite3 backend/database/events.db

   UPDATE packing_profiles
   SET packing_area = '[200,250,600,400]'
   WHERE profile_name = 'Cam1';
   ```

### Preview Image Not Loading

**Symptoms**:
- API returns 404 for preview images
- UI shows "Image not found"

**Solutions**:
1. **Check Image Path**:
   ```bash
   ls -la resources/output_clips/CameraROI/
   # Verify image files exist
   ```

2. **Verify File Permissions**:
   ```bash
   chmod 644 resources/output_clips/CameraROI/*.jpg
   ```

3. **Check Backend Logs**:
   ```bash
   tail -f var/logs/app_latest.log | grep "GET-ROI-FRAME"
   ```

### Database ROI Format Issues

**Symptoms**:
- ROI stored in wrong format
- Event detection fails due to ROI parsing errors

**Solutions**:
1. **Verify ROI Format**:
   ```sql
   SELECT profile_name, packing_area FROM packing_profiles;
   -- Should return: '[100,150,800,600]' format
   ```

2. **Fix Format if Incorrect**:
   ```python
   # Python script to fix format
   import sqlite3
   import json

   conn = sqlite3.connect('backend/database/events.db')
   cursor = conn.cursor()

   # Get all ROIs
   cursor.execute("SELECT id, packing_area FROM packing_profiles")
   for row_id, roi_str in cursor.fetchall():
       # Parse and reformat
       roi = json.loads(roi_str)
       if len(roi) == 4:
           formatted = json.dumps(roi)  # Ensure [x,y,w,h] format
           cursor.execute("UPDATE packing_profiles SET packing_area = ? WHERE id = ?",
                         (formatted, row_id))

   conn.commit()
   ```

## Next Steps

After ROI configuration:

1. **Run First Run Program**: Process initial video batch with configured ROIs
2. **Monitor Event Detection**: Check if events are detected correctly
3. **Fine-tune ROI**: Adjust based on detection results
4. **Configure Additional Cameras**: Repeat process for all cameras
5. **Test with Production Videos**: Validate configuration with real footage

## Related Documentation

- [Installation Guide](installation.md)
- [Processing Modes](processing-modes.md)
- [API Endpoints](../api/endpoints.md)
- [Architecture Overview](../architecture/overview.md)

---

**Last Updated**: 2025-10-06
