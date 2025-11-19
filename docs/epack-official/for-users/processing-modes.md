# Processing Modes Guide

ePACK offers three distinct processing modes to handle different operational scenarios. This guide explains when and how to use each mode effectively.

## Table of Contents

1. [Overview](#overview)
2. [First Run Mode](#first-run-mode)
3. [Default Mode](#default-mode)
4. [Custom Mode](#custom-mode)
5. [Mode Transitions](#mode-transitions)
6. [API Reference](#api-reference)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

### Processing Modes Comparison

| Feature | First Run | Default (Auto-Scan) | Custom |
|---------|-----------|---------------------|--------|
| **Purpose** | Initial historical processing | Continuous monitoring | On-demand processing |
| **Trigger** | Manual (one-time) | Automatic (periodic) | Manual (ad-hoc) |
| **Scope** | Past N days | New files only | Specific file/folder |
| **Duration** | Hours (depending on data) | Continuous (24/7) | Minutes (single batch) |
| **Transition** | → Default after completion | Stays in Default | → Default after completion |
| **Use Case** | New installation | Production operation | Debug/reprocessing |

### Processing Flow

```
┌─────────────────┐
│   INSTALL       │
│   V_TRACK       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FIRST RUN      │  ← Process historical videos (1-30 days)
│  MODE           │     • Scans all videos in date range
└────────┬────────┘     • Creates initial event database
         │              • One-time execution
         │
         ▼
┌─────────────────┐
│  DEFAULT        │  ← Continuous processing (24/7)
│  MODE           │     • Auto-scans every 2 minutes
└────────┬────────┘     • Processes new videos only
         │              • Runs indefinitely
         │
         ▼              ┌──────────────────┐
    Production    ←────→│  CUSTOM MODE     │  ← On-demand processing
    Operations           │  (when needed)   │     • Process specific files
                         └──────────────────┘     • Debug/reprocess
                                                  • Returns to Default
```

## First Run Mode

### Purpose

**First Run Mode** is designed for initial setup to process historical video data and establish a baseline event database.

### When to Use

- ✅ **New ePACK installation**: Process past videos before going live
- ✅ **After configuration changes**: Reprocess videos with new ROI settings
- ✅ **Data migration**: Import events from previous system
- ✅ **System recovery**: Rebuild event database after data loss

### How It Works

**Step-by-Step Process**:

1. **User Initiates**:
   - Sets number of days to process (1-30)
   - Clicks "Run First Run" button

2. **File Discovery**:
   ```python
   # System scans video sources for files within date range
   scan_start_date = today - days_specified
   scan_end_date = today

   # Collects all video files matching:
   for camera in configured_cameras:
       files = find_videos_in_date_range(
           camera_path,
           scan_start_date,
           scan_end_date
       )
   ```

3. **Batch Processing**:
   ```
   For each video file:
   ├── Extract frames at configured interval
   ├── Run hand detection on frames
   ├── Detect QR codes (if enabled)
   ├── Identify packing events
   ├── Save events to database
   └── Mark file as processed
   ```

4. **Completion**:
   - Sets `first_run_completed = true` in database
   - Automatically transitions to Default Mode
   - Background processing continues

### Configuration

**Via UI**:
1. Navigate to Program Dashboard (`http://localhost:3000/program`)
2. Locate "First Run" card
3. Enter number of days (e.g., 7)
4. Click "Run First Run"
5. Monitor progress bar

**Via API**:
```bash
curl -X POST http://localhost:8080/api/program \
  -H "Content-Type: application/json" \
  -d '{
    "card": "First Run",
    "action": "run",
    "days": 7
  }'
```

### Execution Flow

```
┌────────────────────────────────────────────┐
│           FIRST RUN EXECUTION              │
├────────────────────────────────────────────┤
│                                            │
│  1. Validate Configuration                 │
│     ├── Check first_run_completed status   │
│     ├── Verify days parameter (1-30)       │
│     └── Ensure video sources configured    │
│                                            │
│  2. File Discovery                         │
│     ├── Calculate date range               │
│     ├── Scan all camera folders            │
│     ├── Filter by video extensions         │
│     └── Sort by creation time              │
│                                            │
│  3. Database Preparation                   │
│     ├── Clear file_list table              │
│     ├── Insert discovered files            │
│     ├── Set program_type = 'First Run'     │
│     └── Mark all as is_processed = 0       │
│                                            │
│  4. Batch Scheduling                       │
│     ├── Start BatchScheduler               │
│     ├── Process files sequentially         │
│     ├── Update progress in database        │
│     └── Log processing results             │
│                                            │
│  5. Frame Processing (per file)            │
│     ├── Run frame_sampler_trigger.py       │
│     ├── Detect hand/QR in ROI              │
│     ├── Generate log file                  │
│     └── Mark file is_processed = 1         │
│                                            │
│  6. Event Detection (per file)             │
│     ├── Run event_detector.py              │
│     ├── Parse frame sampler logs           │
│     ├── Identify packing events            │
│     ├── Save to events table               │
│     └── Mark log as processed              │
│                                            │
│  7. Completion                             │
│     ├── Set first_run_completed = true     │
│     ├── Transition to Default Mode         │
│     ├── Log summary statistics             │
│     └── Send completion notification       │
│                                            │
└────────────────────────────────────────────┘
```

### Progress Monitoring

**Check Progress via API**:
```bash
GET http://localhost:8080/api/program-progress

Response:
{
  "current_running": "First Run",
  "days": 7,
  "total_files": 350,
  "processed_files": 142,
  "progress_percentage": 40.6,
  "current_file": "Cam1_20251001_143000.mp4",
  "estimated_completion": "2025-10-06 18:30:00"
}
```

**Check in UI**:
- Progress bar shows percentage complete
- Real-time file counter (142/350)
- Current processing file name
- Estimated time remaining

### Expected Duration

**Factors Affecting Duration**:
- Number of days: More days = more videos
- Video count per day: Varies by camera/activity
- Video length: Longer videos take more time
- System resources: CPU/RAM affects speed
- ROI complexity: Larger ROI = more processing

**Typical Duration Examples**:

| Days | Videos | Avg Duration | Total Time |
|------|--------|--------------|------------|
| 1 | 50 | 2 min/video | ~1.5 hours |
| 7 | 350 | 2 min/video | ~12 hours |
| 14 | 700 | 2 min/video | ~24 hours |
| 30 | 1500 | 2 min/video | ~50 hours |

**Performance Tips**:
- Run overnight for large datasets
- Use SSD for faster I/O
- Allocate sufficient RAM (16GB+)
- Close unnecessary applications

### Post-Completion

**Automatic Actions**:
1. ✅ `first_run_completed` set to `true`
2. ✅ Default Mode activated automatically
3. ✅ Scheduler starts background scanning
4. ✅ System ready for production use

**Verification Steps**:
```bash
# Check completion status
sqlite3 backend/database/events.db \
  "SELECT value FROM program_status WHERE key='first_run_completed';"
# Should return: true

# Count processed events
sqlite3 backend/database/events.db \
  "SELECT COUNT(*) FROM events;"
# Should return: > 0

# Check scheduler status
curl http://localhost:8080/api/program
# Should show: "current_running": "Default"
```

## Default Mode

### Purpose

**Default Mode** provides continuous, automatic video processing for ongoing operations. It runs 24/7 in the background, detecting and processing new videos as they arrive.

### When to Use

- ✅ **Production environment**: Normal daily operations
- ✅ **After First Run**: Automatically activated
- ✅ **Continuous monitoring**: 24/7 event detection
- ✅ **Cloud sync integration**: Process newly downloaded videos

### How It Works

**Auto-Scan Cycle** (Every 2 minutes):

```python
while True:
    # 1. Scan for new videos
    new_files = scan_video_sources()

    # 2. Filter unprocessed files
    pending_files = [f for f in new_files if not f.is_processed]

    # 3. Add to processing queue
    for file in pending_files:
        add_to_file_list(file, program_type='Default')

    # 4. Process batch
    process_batch(pending_files)

    # 5. Wait for next cycle
    sleep(120)  # 2 minutes
```

**Processing Pipeline**:

```
┌──────────────────────────────────────────┐
│         DEFAULT MODE PIPELINE            │
├──────────────────────────────────────────┤
│                                          │
│  Every 2 Minutes:                        │
│  ┌────────────────────────────────────┐ │
│  │ 1. File Discovery                  │ │
│  │    ├── Scan configured sources     │ │
│  │    ├── Check modification times    │ │
│  │    └── Identify new videos         │ │
│  └────────────────────────────────────┘ │
│              │                           │
│              ▼                           │
│  ┌────────────────────────────────────┐ │
│  │ 2. Database Check                  │ │
│  │    ├── Query file_list table       │ │
│  │    ├── Filter is_processed = 0     │ │
│  │    └── Exclude duplicates          │ │
│  └────────────────────────────────────┘ │
│              │                           │
│              ▼                           │
│  ┌────────────────────────────────────┐ │
│  │ 3. Batch Processing                │ │
│  │    ├── Frame sampling              │ │
│  │    ├── Hand/QR detection           │ │
│  │    ├── Event identification        │ │
│  │    └── Database update             │ │
│  └────────────────────────────────────┘ │
│              │                           │
│              ▼                           │
│  ┌────────────────────────────────────┐ │
│  │ 4. Wait Next Cycle (120s)          │ │
│  └────────────────────────────────────┘ │
│              │                           │
│              └──────────────────────────┤
│                        (Loop)            │
└──────────────────────────────────────────┘
```

### Automatic Activation

**Default Mode starts automatically when**:

1. **After First Run completes**:
   ```sql
   -- System checks this condition
   SELECT value FROM program_status
   WHERE key = 'first_run_completed';

   -- If 'true', auto-start Default Mode
   ```

2. **On application restart** (if First Run completed):
   ```python
   # In app.py startup
   def init_default_program():
       if first_run_completed and not scheduler.running:
           start_default_mode()
   ```

3. **After Custom Mode completes**:
   ```python
   # After custom processing
   complete_custom_processing()
   transition_to_default_mode()
   ```

### Monitoring Default Mode

**Check Status**:
```bash
GET http://localhost:8080/api/program

Response:
{
  "current_running": "Default",
  "scheduler_running": true,
  "last_scan": "2025-10-06 14:35:00",
  "next_scan": "2025-10-06 14:37:00",
  "pending_files": 3,
  "recent_events": 15
}
```

**View Processing Activity**:
```bash
# Check recent file processing
sqlite3 backend/database/events.db \
  "SELECT file_path, status, created_at
   FROM file_list
   WHERE program_type='Default'
   ORDER BY created_at DESC
   LIMIT 10;"

# Check recent events
sqlite3 backend/database/events.db \
  "SELECT event_id, video_file, packing_time_start, tracking_codes
   FROM events
   ORDER BY event_id DESC
   LIMIT 10;"
```

### Performance Characteristics

**Resource Usage**:
- **Idle State** (no new files):
  - CPU: < 1%
  - RAM: ~200 MB
  - Disk I/O: Minimal

- **Active Processing**:
  - CPU: 30-50% (per video)
  - RAM: ~2 GB
  - Disk I/O: Moderate (reading videos, writing logs)

**Scan Efficiency**:
```
Scan Interval: 120 seconds
Scan Duration: < 5 seconds (typical)
Processing Pause: Minimal
Overhead: < 5% of total time
```

### Stopping Default Mode

**When to Stop**:
- System maintenance
- Configuration changes
- Troubleshooting
- Resource management

**How to Stop**:

**Via UI**:
1. Navigate to Program Dashboard
2. Click "Stop Default" button
3. Confirm action

**Via API**:
```bash
curl -X POST http://localhost:8080/api/program \
  -H "Content-Type: application/json" \
  -d '{
    "card": "Default",
    "action": "stop"
  }'
```

**Result**:
- Scheduler pauses
- Current file finishes processing
- No new files queued
- System remains ready for Custom Mode

## Custom Mode

### Purpose

**Custom Mode** allows on-demand processing of specific video files or directories, useful for debugging, reprocessing, or handling special cases.

### When to Use

- ✅ **Debug specific videos**: Troubleshoot detection issues
- ✅ **Reprocess files**: Re-run with updated ROI/config
- ✅ **Process old videos**: Handle videos outside First Run range
- ✅ **Test configuration**: Validate settings before production
- ✅ **Manual intervention**: Process problematic files

### How It Works

**Single-File Processing**:
```python
# User provides specific video path
video_path = "/path/to/specific/video.mp4"

# System:
1. Validates file exists
2. Adds to file_list with program_type='Custom'
3. Processes immediately (high priority)
4. Returns to Default Mode after completion
```

**Directory Processing**:
```python
# User provides directory path
directory_path = "/path/to/video/folder"

# System:
1. Scans directory recursively
2. Identifies all video files
3. Adds batch to file_list
4. Processes sequentially
5. Returns to Default Mode when done
```

### Configuration

**Via UI**:
1. Navigate to Program Dashboard
2. Locate "Custom" card
3. Enter file/folder path:
   ```
   /Users/username/Movies/VTrack/Input/Cam1/video_20251006.mp4
   ```
   OR
   ```
   /Users/username/Movies/VTrack/Input/Cam1/
   ```
4. Click "Run Custom"
5. Monitor progress

**Via API**:

**Single File**:
```bash
curl -X POST http://localhost:8080/api/program \
  -H "Content-Type: application/json" \
  -d '{
    "card": "Custom",
    "action": "run",
    "custom_path": "/path/to/video.mp4"
  }'
```

**Directory**:
```bash
curl -X POST http://localhost:8080/api/program \
  -H "Content-Type: application/json" \
  -d '{
    "card": "Custom",
    "action": "run",
    "custom_path": "/path/to/videos/folder/"
  }'
```

### Execution Flow

```
┌───────────────────────────────────────────┐
│        CUSTOM MODE EXECUTION              │
├───────────────────────────────────────────┤
│                                           │
│  1. Input Validation                      │
│     ├── Check path exists                 │
│     ├── Verify read permissions           │
│     └── Validate file type (video)        │
│                                           │
│  2. Scheduler Pause                       │
│     ├── Stop Default Mode temporarily     │
│     ├── Wait for current file to finish   │
│     └── Clear processing queue            │
│                                           │
│  3. File Preparation                      │
│     ├── If file: Add to file_list         │
│     ├── If directory: Scan and add all    │
│     ├── Set program_type = 'Custom'       │
│     └── Set priority = HIGH               │
│                                           │
│  4. Processing                            │
│     ├── Frame sampling                    │
│     ├── Detection (hand/QR)               │
│     ├── Event extraction                  │
│     └── Database update                   │
│                                           │
│  5. Completion                            │
│     ├── Mark file(s) as processed         │
│     ├── Resume Default Mode               │
│     └── Return to background scanning     │
│                                           │
└───────────────────────────────────────────┘
```

### Use Cases

#### Use Case 1: Debug Detection Issue

**Scenario**: Camera 1 missed events on 2025-10-05

**Steps**:
1. Locate problematic video:
   ```bash
   find /path/to/videos -name "*Cam1*20251005*"
   ```

2. Run Custom Mode:
   ```bash
   curl -X POST http://localhost:8080/api/program \
     -d '{"card":"Custom","action":"run","custom_path":"/path/to/Cam1_20251005_140000.mp4"}'
   ```

3. Check logs:
   ```bash
   tail -f var/logs/frame_processing/Cam1/*20251005*
   ```

4. Verify events:
   ```sql
   SELECT * FROM events WHERE video_file LIKE '%20251005%';
   ```

#### Use Case 2: Reprocess with New ROI

**Scenario**: Updated Cam2 ROI, need to reprocess today's videos

**Steps**:
1. Update ROI configuration (see ROI guide)

2. Find today's videos:
   ```bash
   TODAY=$(date +%Y%m%d)
   find /path/to/videos -name "*Cam2*${TODAY}*"
   ```

3. Reprocess directory:
   ```bash
   curl -X POST http://localhost:8080/api/program \
     -d '{"card":"Custom","action":"run","custom_path":"/path/to/videos/Cam2/"}'
   ```

4. Compare results:
   ```sql
   SELECT COUNT(*) FROM events
   WHERE camera_name='Cam2'
   AND DATE(packing_time_start/1000, 'unixepoch') = DATE('now');
   ```

#### Use Case 3: Process Old Archive

**Scenario**: Found old videos from before First Run period

**Steps**:
1. Copy videos to accessible location:
   ```bash
   cp -r /archive/2024-videos/ /tmp/old-videos/
   ```

2. Process archive:
   ```bash
   curl -X POST http://localhost:8080/api/program \
     -d '{"card":"Custom","action":"run","custom_path":"/tmp/old-videos/"}'
   ```

3. Wait for completion

4. Verify imported events:
   ```sql
   SELECT COUNT(*), MIN(packing_time_start), MAX(packing_time_start)
   FROM events;
   ```

### Limitations

**File Validation**:
- ❌ Non-video files skipped (with warning)
- ❌ Corrupted videos logged as errors
- ❌ Unsupported codecs fail gracefully

**Concurrency**:
- Only one Custom Mode session at a time
- Pauses Default Mode during execution
- No parallel processing of custom batches

**Performance**:
- Same processing time as Default Mode
- No priority queue (sequential processing)
- Large directories may take hours

## Mode Transitions

### State Diagram

```
┌─────────────┐
│   INITIAL   │
│   STATE     │
└──────┬──────┘
       │
       │ User runs First Run
       ▼
┌─────────────┐
│  FIRST RUN  │◄────────────┐
│   RUNNING   │             │
└──────┬──────┘             │
       │                    │
       │ Completion         │
       ▼                    │
┌─────────────┐             │
│   DEFAULT   │             │ User stops
│   RUNNING   │─────────────┤ & reruns
└──────┬──────┘             │ First Run
       │                    │
       │ User runs Custom   │
       ▼                    │
┌─────────────┐             │
│   CUSTOM    │             │
│   RUNNING   │             │
└──────┬──────┘             │
       │                    │
       │ Completion         │
       └────────────────────┘
```

### Transition Rules

**From First Run**:
- ✅ → Default: Automatic on completion
- ❌ → Custom: Not allowed while First Run active
- ❌ → First Run: Cannot run twice (unless reset)

**From Default**:
- ✅ → Custom: Pauses Default, runs Custom, resumes Default
- ❌ → First Run: Not allowed (first_run_completed=true)
- ✅ → Stopped: Manual stop, pauses all processing

**From Custom**:
- ✅ → Default: Automatic on completion
- ❌ → First Run: Not allowed
- ❌ → Custom: Cannot queue multiple Custom sessions

### Database State Tracking

**program_status table**:
```sql
SELECT * FROM program_status;

-- Key-value pairs:
| key                  | value   |
|----------------------|---------|
| first_run_completed  | true    |
| current_running      | Default |
| last_stop_time       | 2025-10-06 14:30:00 |
```

**file_list table**:
```sql
SELECT program_type, COUNT(*)
FROM file_list
GROUP BY program_type;

-- Results:
| program_type | COUNT(*) |
|--------------|----------|
| First Run    | 350      |
| Default      | 47       |
| Custom       | 5        |
```

## API Reference

### Start Program

**POST /api/program**

Start a processing program.

**Request**:
```json
{
  "card": "First Run" | "Default" | "Custom",
  "action": "run",
  "days": 7,                          // First Run only
  "custom_path": "/path/to/file.mp4"  // Custom only
}
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

### Stop Program

**POST /api/program**

Stop current processing.

**Request**:
```json
{
  "card": "Default" | "Custom",
  "action": "stop"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Default mode stopped",
  "current_running": null
}
```

### Get Status

**GET /api/program**

Get current program status.

**Response**:
```json
{
  "current_running": "Default",
  "scheduler_running": true,
  "first_run_completed": true,
  "last_scan": "2025-10-06 14:35:00"
}
```

### Get Progress

**GET /api/program-progress**

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

**GET /api/check-first-run**

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

## Best Practices

### First Run Best Practices

1. **Choose Appropriate Days**:
   - 1-3 days: Quick validation
   - 7 days: Standard setup
   - 30 days: Comprehensive baseline

2. **Run During Off-Hours**:
   - Schedule for overnight
   - Avoid peak system usage
   - Minimize user disruption

3. **Monitor Progress**:
   - Check logs regularly
   - Verify event counts
   - Watch for errors

### Default Mode Best Practices

1. **Let It Run Continuously**:
   - Don't stop unnecessarily
   - Trust auto-scan mechanism
   - System self-regulates

2. **Monitor Resource Usage**:
   ```bash
   # Check CPU/RAM
   top -pid $(pgrep -f "python app.py")

   # Check disk space
   df -h
   ```

3. **Review Logs Periodically**:
   ```bash
   # Daily log review
   tail -100 var/logs/app_latest.log | grep ERROR
   ```

### Custom Mode Best Practices

1. **Validate Paths First**:
   ```bash
   # Before running Custom Mode
   test -f /path/to/video.mp4 && echo "File exists" || echo "Not found"
   ```

2. **Use for Specific Purposes**:
   - Debugging only
   - Don't use for routine processing
   - Return to Default Mode quickly

3. **Document Custom Runs**:
   - Keep log of what was reprocessed
   - Note reasons for custom processing
   - Track results

## Troubleshooting

### First Run Not Starting

**Symptoms**:
- Button click has no effect
- API returns error

**Solutions**:
1. Check first_run_completed status:
   ```sql
   SELECT value FROM program_status WHERE key='first_run_completed';
   ```

2. If 'true', reset if needed (CAUTION):
   ```sql
   UPDATE program_status SET value='false' WHERE key='first_run_completed';
   ```

3. Verify video sources configured:
   ```sql
   SELECT * FROM video_sources WHERE active=1;
   ```

### Default Mode Not Auto-Starting

**Symptoms**:
- First Run completes but Default doesn't start
- Scheduler remains stopped

**Solutions**:
1. Check app.py logs:
   ```bash
   grep "Initializing default program" var/logs/app_latest.log
   ```

2. Manually start Default:
   ```bash
   curl -X POST http://localhost:8080/api/program \
     -d '{"card":"Default","action":"run"}'
   ```

3. Restart application:
   ```bash
   # Stop backend
   pkill -f "python app.py"

   # Start backend
   cd backend && python app.py
   ```

### Custom Mode File Not Found

**Symptoms**:
- 404 error for specified path
- "File does not exist" message

**Solutions**:
1. Verify absolute path:
   ```bash
   readlink -f /path/to/video.mp4
   ```

2. Check file permissions:
   ```bash
   ls -la /path/to/video.mp4
   ```

3. Use correct path format:
   - macOS: `/Users/username/...`
   - Linux: `/home/username/...`
   - Windows: `C:/Users/username/...` (forward slashes)

## Next Steps

After understanding processing modes:

1. **Configure Video Sources**: Set up local or cloud storage
2. **Run First Run**: Process initial video batch
3. **Monitor Default Mode**: Ensure continuous operation
4. **Use Custom Mode**: For debugging and special cases
5. **Review Event Data**: Analyze detected packing events

## Related Documentation

- [Installation Guide](installation.md)
- [ROI Configuration](roi-configuration.md)
- [API Endpoints](../api/endpoints.md)
- [Architecture Overview](../architecture/overview.md)

---

**Last Updated**: 2025-10-06
