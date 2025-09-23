# Scheduler Module Documentation

## V_Track Video Post-Processing System

**Important: V_Track is NOT a live surveillance system**

V_Track processes **existing video files** from:
- Local storage directories
- Google Drive cloud storage

**What V_Track does:**
✅ Batch video file analysis
✅ Computer vision processing (hand detection, QR codes)
✅ Automated result storage
✅ Cloud sync for processed files

**What V_Track does NOT do:**
❌ Live camera streaming
❌ Real-time surveillance monitoring
❌ Video recording from cameras
❌ Live video streaming operations

---

The scheduler module is the central orchestration component of the V_Track video post-processing system. It manages the entire video analysis pipeline from file discovery to event detection, with dynamic resource optimization and robust error handling.

## Architecture Overview

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   File Scanner  │    │  Batch Scheduler │    │ Program Manager │
│                 │    │                  │    │                 │
│ - Periodic scan │ -> │ - Resource mgmt  │ <- │ - API endpoints │
│ - FFprobe meta  │    │ - Thread pools   │    │ - State tracking│
│ - Filter logic  │    │ - Coordination   │    │ - Mode control  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         v                        v                        v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   File Lister   │    │ Program Runner   │    │   DB Sync       │
│                 │    │                  │    │                 │
│ - Video discovery│    │ - Frame sampling │    │ - RW locks      │
│ - Metadata extract│   │ - Event detection│    │ - Thread events │
│ - Database storage│   │ - Pipeline coord │    │ - Synchronization│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Thread Architecture

```
Main Thread
├── File Scanner Thread (periodic scanning)
├── Batch Processor Thread (coordination)
├── Frame Sampler Threads (1-N, dynamic sizing)
└── Event Detector Thread (single instance)
```

## Module Files

### 1. `batch_scheduler.py`
**Purpose**: Main scheduler coordinator with dynamic resource management

**Key Classes**:
- `SystemMonitor`: Monitors CPU/memory usage, calculates optimal batch sizes
- `BatchScheduler`: Orchestrates entire processing pipeline

**Key Features**:
- Dynamic batch size adjustment based on system resources
- Timeout handling for stalled processing jobs
- Thread lifecycle management (start/stop/pause/resume)
- Coordinated file scanning and processing

### 2. `program.py` 
**Purpose**: Flask REST API for controlling video processing programs

**API Endpoints**:
- `POST /program`: Execute processing programs (First/Default/Custom)
- `GET /program`: Get current program status
- `POST /confirm-run`: Confirm program execution
- `GET /program-progress`: Real-time processing progress
- `GET /check-first-run`: Check first run completion status
- `GET /get-cameras`: Get configured cameras
- `GET /get-camera-folders`: Get camera directories

**Processing Modes**:
- **First Run (Lần đầu)**: Initial processing for specified days
- **Default (Mặc định)**: Continuous background processing
- **Custom (Chỉ định)**: Process specific file/directory

### 3. `program_runner.py`
**Purpose**: Manages video processing threads and pipeline coordination

**Key Functions**:
- `start_frame_sampler_thread()`: Creates frame sampler thread pool
- `run_frame_sampler()`: Main frame sampling logic
- `start_event_detector_thread()`: Creates event detector thread
- `run_event_detector()`: Event detection and log analysis

**Processing Pipeline**:
1. **IdleMonitor**: Detects active periods in video
2. **FrameSampler**: Extracts frames, performs hand/QR detection
3. **EventDetector**: Analyzes logs for significant events
4. **Database Updates**: Tracks status throughout pipeline

### 4. `file_lister.py`
**Purpose**: Video file discovery and metadata extraction

**Key Functions**:
- `get_file_creation_time()`: FFprobe-based timestamp extraction
- `scan_files()`: Directory scanning with advanced filtering
- `save_files_to_db()`: Batch database insertion
- `cleanup_stale_jobs()`: Recovery from failed processing
- `run_file_scan()`: Main scanning coordinator

**Scanning Strategies**:
- **First Run**: Scan specified number of days for initial setup
- **Default**: Continuous scanning with incremental filtering
- **Custom**: Target specific files/directories

### 5. `db_sync.py`
**Purpose**: Thread synchronization and database access coordination

**Synchronization Objects**:
- `db_rwlock`: Reader-writer lock for database access
- `frame_sampler_event`: Signals when videos are ready
- `event_detector_event`: Signals when logs are ready
- `event_detector_done`: Signals event detection completion

**Classes**:
- `LoggedEvent`: Enhanced event wrapper with debug logging

## Configuration

The scheduler module uses `SchedulerConfig` for configuration management:

```python
# Example configuration values
BATCH_SIZE_DEFAULT = 2          # Default number of frame sampler threads
BATCH_SIZE_MAX = 4              # Maximum batch size
CPU_THRESHOLD_LOW = 30          # CPU % below which to increase batch size
CPU_THRESHOLD_HIGH = 80         # CPU % above which to reduce batch size
MEMORY_THRESHOLD = 85           # Memory % threshold for reduction
SCAN_INTERVAL_SECONDS = 900     # File scan interval (15 minutes)
TIMEOUT_SECONDS = 900           # Processing timeout (15 minutes)
QUEUE_LIMIT = 1000              # Maximum pending files
```

## Threading Model

### Event Coordination Flow

```
1. File Scanner -> frame_sampler_event.set() -> Frame Samplers wake up
2. Frame Samplers process videos -> event_detector_event.set() -> Event Detector wakes up
3. Event Detector processes logs -> event_detector_done.set() -> Frame Samplers continue
4. Repeat cycle
```

### Database Access Patterns

```python
# Read operations (concurrent)
with db_rwlock.gen_rlock():
    conn = get_db_connection()
    # Read operations here

# Write operations (exclusive)
with db_rwlock.gen_wlock():
    conn = get_db_connection()
    # Write operations here
    conn.commit()
```

## Error Handling & Recovery

### Stale Job Cleanup
- Automatically resets jobs stuck in processing state for >59 minutes
- Prevents deadlocks from failed processing attempts

### Timeout Management
- 15-minute timeout for video processing operations
- Automatic status updates to prevent queue blocking

### Resource Monitoring
- Dynamic batch size adjustment prevents system overload
- CPU/memory thresholds with automatic scaling

### Thread Safety
- RWLocks prevent database corruption
- Event coordination prevents race conditions
- Video-level locking prevents concurrent processing

## Performance Optimizations

### Dynamic Batch Sizing
```python
# CPU < 30% AND Memory < 70% -> Increase batch size
# CPU > 80% OR Memory > 85% -> Decrease batch size
# Otherwise -> Maintain current batch size
```

### Incremental Scanning
- Time-based filtering to avoid reprocessing old files
- Camera selection filtering to focus on specific sources
- Working hours/days filtering for business logic

### Database Efficiency
- Batch insertions using `executemany()`
- Read locks for concurrent database access
- Connection pooling and timeout handling

### FFprobe Integration
- Accurate video metadata extraction
- Timezone normalization to Vietnam time
- Fallback to filesystem timestamps

## Troubleshooting

### Common Issues

1. **High CPU Usage**: Batch size will automatically reduce
2. **Stuck Processing**: Stale job cleanup runs automatically
3. **No Files Found**: Check camera selection and time filters
4. **Database Locks**: Use appropriate RWLock patterns
5. **Thread Deadlocks**: Event coordination prevents most issues

### Debug Logging

Enable debug logging to trace thread coordination:

```python
from modules.scheduler.db_sync import logged_frame_sampler_event
# Use logged events instead of raw events for debugging
```

### Monitoring

Key metrics to monitor:
- Batch size changes (indicates resource pressure)
- Processing timeouts (indicates performance issues)
- Stale job resets (indicates reliability issues)
- Scan duration (indicates filesystem performance)

## Integration Points

### Database Tables
- `file_list`: Video files queue with processing status
- `processed_logs`: Frame sampling logs for event detection
- `processing_config`: System configuration
- `packing_profiles`: Camera-specific processing parameters

### External Dependencies
- **FFprobe**: Video metadata extraction
- **MediaPipe/OpenCV**: Video processing in frame samplers
- **psutil**: System resource monitoring
- **Google Drive API**: Cloud file access (if configured)

### API Integration
The scheduler coordinates with the main Flask application through:
- Program management endpoints in `program.py`
- Status updates via database
- Event logging and progress tracking

## Best Practices

### Development
1. Always run Python from `backend/` directory
2. Use absolute imports from `modules/`
3. Test with various batch sizes and timeouts
4. Monitor resource usage during development

### Deployment
1. Configure appropriate CPU/memory thresholds for target hardware
2. Set scan intervals based on video generation frequency
3. Monitor database performance under load
4. Plan for graceful shutdown procedures

### Monitoring
1. Track batch size adjustments for capacity planning
2. Monitor processing timeouts for performance tuning
3. Watch stale job cleanup frequency for reliability assessment
4. Analyze scan durations for filesystem optimization