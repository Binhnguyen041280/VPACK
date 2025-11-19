# Empty Event Tracking & AI Enhancement System

**Version:** 1.1 (REVISED)
**Date:** January 2025 (Revised: October 23, 2025)
**Status:** ⚠️ **PARTIALLY DEPRECATED** - Strategy Revised

## ⚠️ IMPORTANT UPDATE - October 23, 2025

**Original Phase 1 (Empty Event Boundary Extraction) - DEPRECATED**

The initial implementation strategy for Phase 1 was based on an **incorrect assumption** about WeChat QR `detectAndDecode()` behavior and has been **removed**.

### What Was Wrong:
- **Assumption:** WeChat QR returns boundary points when detection succeeds but decoding fails
- **Reality:** When decode fails, BOTH `texts` AND `points` are empty (verified from OpenCV source code)

### What Was Removed:
- ❌ `convergence_detector.py` (288 lines) - boundary stability detection
- ❌ Boundary buffering logic in `frame_sampler_trigger.py` (221 lines)
- ❌ Methods: `_calculate_bbox_from_points`, `_should_buffer_boundary`, `_process_empty_event`, `_log_boundary`

### What Was Kept:
- ✅ Database schema changes (`expected_mvd_qr_size`, `expected_trigger_qr_size`, `decode_success`)
- ✅ AI configuration infrastructure (`ai_config`, `ai_recovery_logs` tables)
- ✅ AI routes and services (`ai_routes.py`, `ai_service.py`)
- ✅ QR size tracking and adaptive updates

### Revised Strategy for Empty Event Detection:
Implement alternative QR detection methods that don't rely on WeChat decode failures:
1. **Template Matching** - Use expected_qr_size to match QR finder patterns
2. **Edge Detection + Size Filtering** - Detect rectangular patterns of expected size
3. **YOLO Object Detection** - Train lightweight model for QR presence detection

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Solution Architecture](#solution-architecture)
4. [Implementation Plan](#implementation-plan)
5. [Database Schema](#database-schema)
6. [API Endpoints](#api-endpoints)
7. [AI Batch Processing](#ai-batch-processing)
8. [Quality Monitoring Dashboard](#quality-monitoring-dashboard)
9. [Testing Strategy](#testing-strategy)
10. [Backup & Recovery](#backup--recovery)
11. [Deployment Plan](#deployment-plan)

---

## Overview

### Goal
Track ALL packing events (including those with failed QR detection), export frames for AI review, and provide quality monitoring dashboard for system health.

### Key Features
- ✅ Track empty events (QR detection failed but event exists)
- ✅ Export top 5 frames ranked by QR bbox size for AI processing
- ✅ AI batch processing tool (OpenAI/Claude Vision API)
- ✅ Quality monitoring dashboard with real-time metrics
- ✅ Automatic alerts for quality issues

### Expected Results
- **Before:** 8/10 events tracked (20% lost)
- **After:** 10/10 events tracked (100% coverage)
- **After AI:** 95%+ events with decoded QR (AI recovers failed detections)

---

## Problem Statement

### Current Issue

```
Video thực tế có 10 packing events (dựa vào On→Off transitions)

Frame Sampler hiện tại:
├─ Event 1: TimeGo detected → QR decoded ✅ → Save to DB
├─ Event 2: TimeGo detected → QR decoded ✅ → Save to DB
├─ Event 3: TimeGo detected → QR FAILED ❌ → SKIP (không save DB)
├─ Event 4: TimeGo detected → QR decoded ✅ → Save to DB
├─ Event 5: TimeGo detected → QR FAILED ❌ → SKIP (không save DB)
└─ ...

Database: Chỉ có 8 events → THIẾU 2 events!
```

### Consequences
- ❌ Manager không thấy đủ events trong dashboard (data incomplete)
- ❌ Không track được quality issues (blind spot)
- ❌ Mất data để analyze và improve system
- ❌ Không biết QR detection rate thực tế

### Root Cause
Frame sampler chỉ lưu events khi QR decode thành công. Events có On→Off transition nhưng QR fail → bị bỏ qua hoàn toàn.

---

## Solution Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Frame Sampling (Real-time)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Detect On→Off transition                                    │
│         ↓                                                    │
│ Look backward for MVD in 10s window                         │
│         ↓                                                    │
│ MVD found?                                                   │
│    ├─ YES → Save normal event (status='completed') ✅       │
│    │                                                         │
│    └─ NO  → Save empty event (status='qr_failed') ⚠️        │
│              ↓                                               │
│         Extract frames ±2s around transition                 │
│              ↓                                               │
│         WeChat detect to find QR boundaries                  │
│              ↓                                               │
│         Rank frames by bbox area (larger = better)          │
│              ↓                                               │
│         Export top 5 to ai_review_queue/event_{id}/         │
│              ↓                                               │
│         Save frames path to DB                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: AI Batch Processing (Offline)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Scan ai_review_queue/ directory                             │
│         ↓                                                    │
│ For each pending event:                                     │
│    ├─ Load top 3 frames (rank 1-3)                         │
│    ├─ Upload to ChatGPT-4 Vision / Claude                  │
│    ├─ Prompt: "Read QR code text 'TimeGo'"                 │
│    └─ Parse response                                        │
│         ↓                                                    │
│ If AI success:                                              │
│    ├─ Update DB: status='ai_completed', mvd='TimeGo'       │
│    └─ Archive event to ai_review_archive/                  │
│         ↓                                                    │
│ If AI fail:                                                 │
│    └─ Mark status='ai_failed' (needs manual entry)         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Quality Monitoring (Dashboard)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Display real-time metrics:                                  │
│  • Empty event rate (threshold: 30%)                       │
│  • Frame export success rate (threshold: 90%)              │
│  • AI batch status (threshold: 24h)                        │
│  • Pending review count                                     │
│         ↓                                                    │
│ Alert if thresholds exceeded                                │
│         ↓                                                    │
│ Show camera-specific breakdown                              │
│         ↓                                                    │
│ Display 7-day trends chart                                  │
└─────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
Backend:
├── modules/technician/
│   ├── frame_sampler_trigger.py (MODIFIED)
│   │   └─ Add empty event tracking logic
│   │   └─ Call QRFrameExporter when MVD not found
│   │
│   ├── qr_frame_exporter.py (NEW)
│   │   └─ Extract frames around transition
│   │   └─ WeChat detect to find QR boundaries
│   │   └─ Rank by bbox area, export top 5
│   │
│   └── log_parser.py (NEW - optional)
│       └─ Parse transitions from log files
│
├── blueprints/
│   └── quality_monitoring_bp.py (NEW)
│       ├─ GET /api/quality/metrics
│       ├─ GET /api/quality/alerts
│       ├─ GET /api/quality/camera-metrics
│       ├─ GET /api/quality/trends
│       └─ GET /api/quality/pending-events
│
└── tools/
    ├── batch_ai_review.py (NEW)
    │   └─ Process queue with OpenAI/Claude API
    │   └─ Update DB with results
    │   └─ Archive processed events
    │
    └── monitor_quality.py (NEW)
        └─ Check thresholds periodically
        └─ Log alerts to database

Frontend:
└── src/
    ├── pages/Quality/
    │   └── QualityMonitor.tsx (NEW)
    │       ├─ Display metrics cards
    │       ├─ Show pending review queue
    │       ├─ Recent alerts list
    │       └─ Historical trend charts
    │
    └── components/quality/ (NEW)
        ├── QualityMetricsCard.tsx
        ├── MetricRow.tsx
        ├── PendingReviewCard.tsx
        ├── RecentAlertsCard.tsx
        ├── CameraMetricsTable.tsx
        └── HistoricalTrendChart.tsx

Database:
├── packing_events (MODIFIED)
│   ├── status (NEW: 'completed', 'qr_failed', 'ai_completed', 'ai_failed')
│   ├── needs_ai_review (NEW: BOOLEAN)
│   ├── ai_review_frames_path (NEW: TEXT)
│   └── created_at (NEW: DATETIME)
│
└── quality_alerts (NEW TABLE)
    ├── id (PRIMARY KEY)
    ├── alert_type ('empty_rate', 'export_fail', 'ai_batch_overdue')
    ├── severity ('warning', 'critical')
    ├── message (TEXT)
    ├── camera_name (TEXT)
    ├── data (JSON)
    ├── created_at (DATETIME)
    └── resolved_at (DATETIME)

File System:
├── resources/
│   ├── ai_review_queue/ (NEW)
│   │   └── event_{id}/
│   │       ├── rank1_area_{size}.jpg
│   │       ├── rank2_area_{size}.jpg
│   │       ├── rank3_area_{size}.jpg
│   │       ├── rank4_area_{size}.jpg
│   │       ├── rank5_area_{size}.jpg
│   │       └── metadata.json
│   │
│   └── ai_review_archive/ (NEW)
│       └── event_{id}/ (processed events)
│
└── var/logs/
    └── ai_batch/
        └── last_run.txt (timestamp of last AI batch)
```

---

## Implementation Plan

### Phase 1: Backend Core Features (4 hours)

#### Task 1.1: Database Backup & Schema Update (1 hour)

**Backup Commands:**
```bash
# Create backup directory
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 database.db ".backup '$BACKUP_DIR/database_before_empty_events.db'"

# Backup critical code
cp backend/modules/technician/frame_sampler_trigger.py "$BACKUP_DIR/"

# Git tag
git add -A
git commit -m "backup: before empty event tracking implementation"
git tag backup-before-empty-events-$(date +%Y%m%d)

# Log backup
echo "$(date): Backup before empty events implementation" >> backup/backup_log.txt
```

**Schema Migration:**
```sql
-- File: backend/migrations/001_add_empty_event_tracking.sql

-- Add columns to packing_events table
ALTER TABLE packing_events ADD COLUMN status TEXT DEFAULT 'completed';
ALTER TABLE packing_events ADD COLUMN needs_ai_review BOOLEAN DEFAULT 0;
ALTER TABLE packing_events ADD COLUMN ai_review_frames_path TEXT;
ALTER TABLE packing_events ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Create quality_alerts table
CREATE TABLE IF NOT EXISTS quality_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    camera_name TEXT,
    data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME
);

-- Create indexes for performance
CREATE INDEX idx_packing_events_status ON packing_events(status);
CREATE INDEX idx_packing_events_created_at ON packing_events(created_at);
CREATE INDEX idx_quality_alerts_created_at ON quality_alerts(created_at);

-- Status values:
-- 'completed': Event với QR decoded thành công (WeChat)
-- 'qr_failed': Event không detect được QR (cần AI review)
-- 'ai_pending': Đang chờ AI xử lý
-- 'ai_completed': AI đã xử lý thành công
-- 'ai_failed': AI cũng thất bại (cần manual entry)
-- 'manual_entry': Admin nhập tay
```

**Run Migration:**
```python
# backend/migrations/run_migration.py
import sqlite3
import sys

def run_migration(db_path, migration_file):
    with open(migration_file) as f:
        sql = f.read()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
        print(f"✅ Migration completed: {migration_file}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration('database.db', 'backend/migrations/001_add_empty_event_tracking.sql')
```

#### Task 1.2: Create qr_frame_exporter.py (1.5 hours)

**Key Features:**
- Scan ±2s window around transition
- WeChat detect on each frame to find QR boundaries
- Rank frames by bbox area (larger = better quality)
- Export top 5 frames to ai_review_queue/
- Generate metadata.json with event info

**Implementation:** (See full code in appendix)

Key algorithm:
```python
# For each frame in window:
texts, points = qr_detector.detectAndDecode(roi_frame)

# Check if QR detected but decode failed
num_detected = len(points) if points else 0
num_decoded = len(texts) if texts else 0

if num_detected > num_decoded:
    # Found failed QR!
    # Calculate bbox area from points
    bbox_area = bbox_w * bbox_h

    # Crop QR region with padding
    qr_crop = roi_frame[y:y+h, x:x+w]

    # Add to candidates
    failed_frames.append({
        'bbox_area': bbox_area,
        'qr_crop': qr_crop,
        'timestamp': current_time
    })

# Sort by bbox_area descending
failed_frames.sort(key=lambda x: x['bbox_area'], reverse=True)

# Export top 5
export_frames(failed_frames[:5])
```

#### Task 1.3: Modify frame_sampler_trigger.py (1.5 hours)

**Key Changes:**

```python
class FrameSamplerTrigger:
    def __init__(self):
        # ... existing code ...

        # Initialize QR frame exporter
        try:
            self.qr_exporter = QRFrameExporter()
            self.logger.info("✅ QR frame exporter initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to init QR exporter: {e}")
            self.qr_exporter = None

        # Feature flag
        self.empty_event_tracking_enabled = os.getenv('ENABLE_EMPTY_EVENTS', 'false') == 'true'

    def process_video(self, ...):
        # ... existing frame processing loop ...

        # At On→Off transition:
        if last_state == "On" and final_state == "Off":
            transition_time = current_second

            # Look backward for MVD
            mvd = self._find_mvd_in_window(
                mvd_list=mvd_list,
                window_start=max(0, transition_time - 10),
                window_end=transition_time
            )

            if mvd:
                # Normal event - QR decoded successfully
                self._save_normal_event(transition_time, mvd)
            else:
                # Empty event - QR detection failed
                if self.empty_event_tracking_enabled:
                    self._handle_empty_event(
                        video_file=video_file,
                        camera_name=camera_name,
                        transition_time=transition_time,
                        qr_trigger_area=qr_trigger_area
                    )

    def _handle_empty_event(self, video_file, camera_name, transition_time, qr_trigger_area):
        """Handle empty event - save to DB and export frames"""
        try:
            # 1. Save empty event to DB first (even if frame export fails)
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO packing_events
                        (video_path, camera_name, transition_time, mvd, status, needs_ai_review)
                        VALUES (?, ?, ?, NULL, 'qr_failed', 1)
                    """, (video_file, camera_name, transition_time))
                    event_id = cursor.lastrowid

            self.logger.warning(f"⚠️  Empty event {event_id} at {transition_time}s")

            # 2. Export frames (if exporter available)
            if self.qr_exporter:
                result = self.qr_exporter.export_top_5_frames_for_event(
                    event_id=event_id,
                    video_path=video_file,
                    transition_time=transition_time,
                    roi_config={
                        'x': qr_trigger_area[0],
                        'y': qr_trigger_area[1],
                        'w': qr_trigger_area[2],
                        'h': qr_trigger_area[3]
                    }
                )

                if result['success'] and result.get('frames_exported', 0) > 0:
                    # Update DB with frames path
                    with db_rwlock.gen_wlock():
                        with safe_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE packing_events
                                SET ai_review_frames_path = ?
                                WHERE id = ?
                            """, (result['output_dir'], event_id))

                    self.logger.info(f"✅ Exported {result['frames_exported']} frames for event {event_id}")
                else:
                    self.logger.warning(f"⚠️  No frames exported for event {event_id}")

        except Exception as e:
            self.logger.error(f"❌ Error handling empty event: {e}")
            # Event still saved to DB, just without frames
```

---

### Phase 2A: Real-time AI QR Recovery (5 hours)

**Purpose:** Enable automatic real-time AI processing when QR decode fails (instead of batch processing later)

#### Task 2A.1: Database Schema for AI Recovery (30 minutes)

**New Tables:**

**Table: `ai_config`**
```sql
CREATE TABLE IF NOT EXISTS ai_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    ai_enabled BOOLEAN DEFAULT 0,
    api_provider TEXT DEFAULT 'claude',  -- 'claude' or 'openai'
    api_key_encrypted TEXT,              -- Encrypted API key
    use_vtrack_key BOOLEAN DEFAULT 1,    -- TRUE = use ePACK's key, FALSE = use customer's key
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `ai_recovery_logs`**
```sql
CREATE TABLE IF NOT EXISTS ai_recovery_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    camera_name TEXT,
    frames_sent INTEGER,                 -- Number of frames sent to AI
    ai_provider TEXT,                    -- 'claude' or 'openai'
    prompt_tokens INTEGER,               -- Input tokens used
    completion_tokens INTEGER,           -- Output tokens used
    response_time_ms INTEGER,            -- Response time in milliseconds
    success BOOLEAN,                     -- TRUE if AI recovered QR successfully
    decoded_text TEXT,                   -- Tracking codes recovered
    confidence_score REAL,               -- AI confidence (0.0-1.0)
    cost_usd REAL,                       -- API cost in USD
    error_message TEXT,                  -- Error message if failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);

CREATE INDEX idx_ai_recovery_event ON ai_recovery_logs(event_id);
CREATE INDEX idx_ai_recovery_created ON ai_recovery_logs(created_at);
CREATE INDEX idx_ai_recovery_success ON ai_recovery_logs(success);
```

**Purpose:**
- `ai_config`: Store user's AI configuration and preferences
- `ai_recovery_logs`: Track every AI recovery attempt for monitoring and billing

---

#### Task 2A.2: Create AI Recovery Service (2 hours)

**File:** `backend/modules/ai/ai_qr_recovery.py`

**Key Functions:**

**1. `recover_qr_code(frame_paths, max_frames=3)`**
- Input: List of frame image paths (sorted by quality)
- Process:
  - Load top N frames (default 3)
  - Encode to base64
  - Build AI prompt
  - Call Claude/OpenAI Vision API
  - Parse response
  - Calculate cost
- Output: Structured dict with:
  ```python
  {
      'success': bool,
      'tracking_codes': ['TRACK123', ...],
      'confidence': 0.9,
      'tokens': {'prompt': 1580, 'completion': 25},
      'cost_usd': 0.018,
      'response_time_ms': 3200,
      'raw_response': 'TRACK123'
  }
  ```

**2. AI Prompt Template:**
```
Read the QR code(s) in these images and extract the tracking number(s).

The QR code contains a tracking number with format: TRACK followed by numbers/letters.

Instructions:
1. Analyze all provided images
2. Decode the QR code(s)
3. Return ONLY the tracking number(s), one per line
4. If multiple codes visible, return all
5. If cannot decode, return: UNABLE_TO_DECODE

Expected format: TRACK##### (e.g., TRACK12345)

Return only the decoded text, nothing else.
```

**3. Cost Calculation:**
- Claude 3.5 Sonnet pricing:
  - Input: $3 per 1M tokens
  - Output: $15 per 1M tokens
- Typical cost per event: ~$0.018 (3 images)

---

#### Task 2A.3: Create AI Config Management (1 hour)

**File:** `backend/modules/ai/ai_config.py`

**Key Functions:**

**1. `is_ai_enabled() -> bool`**
- Quick check if AI recovery is enabled
- Used by frame sampler to decide whether to call AI

**2. `get_api_key() -> str`**
- Returns API key based on config:
  - If `use_vtrack_key=True`: Return ePACK managed key from env
  - If `use_vtrack_key=False`: Return customer's key (decrypted)

**3. `update_ai_config(ai_enabled, api_provider, api_key, use_vtrack_key)`**
- Save AI configuration to database
- Encrypt API key before storing

**4. API Key Encryption:**
- Use Fernet symmetric encryption
- Encryption key stored in env variable
- Customer API keys never stored in plaintext

---

#### Task 2A.4: Create AI API Routes (1 hour)

**File:** `backend/modules/ai/routes.py`

**Endpoints:**

**1. `GET /api/ai/config`**
- Get AI configuration (without exposing API key)
- Return usage statistics for current month
- Response:
  ```json
  {
    "success": true,
    "config": {
      "ai_enabled": true,
      "api_provider": "claude",
      "use_vtrack_key": true,
      "has_custom_key": false
    },
    "stats": {
      "total_recoveries": 45,
      "successful": 37,
      "success_rate": 82.2,
      "total_cost": 0.81
    }
  }
  ```

**2. `POST /api/ai/config`**
- Update AI configuration
- Request body:
  ```json
  {
    "ai_enabled": true,
    "api_provider": "claude",
    "api_key": "sk-ant-...",  // optional
    "use_vtrack_key": true
  }
  ```

**3. `POST /api/ai/test`**
- Test API key validity
- Makes simple API call to verify key works
- Response: `{"success": true, "message": "API key is valid"}`

**4. `GET /api/ai/recovery-logs?limit=50`**
- Get recent AI recovery logs
- For monitoring and debugging
- Response: List of recovery attempts with details

---

#### Task 2A.5: Integrate AI into Frame Sampler (30 minutes)

**File:** `backend/modules/technician/frame_sampler_trigger.py`

**Modifications:**

**1. In `__init__()` - Initialize AI service:**
```python
from modules.ai.ai_config import is_ai_enabled, get_api_key
from modules.ai.ai_qr_recovery import AIQRRecovery

# Initialize AI recovery (if enabled)
self.ai_recovery = None
if is_ai_enabled():
    try:
        api_key = get_api_key()
        self.ai_recovery = AIQRRecovery(api_key=api_key)
        self.logger.info("✅ AI QR Recovery enabled")
    except Exception as e:
        self.logger.warning(f"⚠️ AI QR Recovery init failed: {e}")
```

**2. In `_handle_empty_event()` - Add AI recovery call:**
```python
def _handle_empty_event(self, video_file, camera_name, transition_time, qr_trigger_area):
    # 1. Save empty event to DB
    event_id = self._save_empty_event(...)

    # 2. Export frames
    frames = self._export_frames(...)

    # 3. Try AI recovery (if enabled and frames exported)
    if self.ai_recovery and frames:
        self._try_ai_recovery(event_id, frames, camera_name)
```

**3. New method `_try_ai_recovery()`:**
```python
def _try_ai_recovery(self, event_id, frames, camera_name):
    """Try to recover QR using AI (real-time)"""
    self.logger.info(f"🤖 Trying AI recovery for event {event_id}...")

    try:
        # Call AI service
        result = self.ai_recovery.recover_qr_code(
            frame_paths=frames,
            max_frames=3
        )

        # Log to database
        self._log_ai_recovery(event_id, camera_name, frames, result)

        if result['success']:
            # Update event with AI result
            self._update_event_with_ai_result(event_id, result['tracking_codes'])
            self.logger.info(f"✅ AI recovered: {result['tracking_codes']}")
        else:
            self.logger.warning(f"❌ AI recovery failed")

    except Exception as e:
        self.logger.error(f"❌ AI recovery error: {e}")
```

**4. New method `_log_ai_recovery()`:**
```python
def _log_ai_recovery(self, event_id, camera_name, frames, result):
    """Log AI recovery attempt to database"""
    with db_rwlock.gen_wlock():
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_recovery_logs
                (event_id, camera_name, frames_sent, ai_provider,
                 prompt_tokens, completion_tokens, response_time_ms,
                 success, decoded_text, confidence_score, cost_usd, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                camera_name,
                len(frames),
                'claude',
                result['tokens']['prompt'],
                result['tokens']['completion'],
                result['response_time_ms'],
                result['success'],
                ','.join(result['tracking_codes']) if result['success'] else None,
                result['confidence'],
                result['cost_usd'],
                result.get('error')
            ))
```

**Workflow:**
```
QR Decode Failed
    ↓
Save empty event (status='qr_failed')
    ↓
Export 5 best frames
    ↓
Check: AI enabled?
    ↓ YES
Send 3 frames to Claude API (~3 seconds)
    ↓
Parse response
    ↓
Update event (status='ai_completed', tracking_codes=[...])
    ↓
Log result to ai_recovery_logs
    ↓
Continue processing
```

**Performance Impact:**
- Additional ~3-5 seconds per failed QR event
- Only impacts events with QR failures (typically 10-20%)
- Non-blocking (can be made async if needed)

---

#### Task 2A.6: Register AI Blueprint (5 minutes)

**File:** `backend/app.py`

**Add:**
```python
from modules.ai.routes import ai_bp

# Register AI blueprint
app.register_blueprint(ai_bp, url_prefix='/api')
logger.info("✅ AI blueprint registered")
```

---

### Phase 2B: Quality Monitoring API (3 hours)

#### Task 2B.1: Create quality_monitoring_bp.py (2 hours)

**API Endpoints:**

```python
# GET /api/quality/metrics?hours=24
# Returns:
{
    'empty_event_rate': 18.5,              # % events without QR
    'frame_export_success_rate': 95.2,    # % empty events with frames exported
    'last_ai_batch': '2025-01-13T12:30:00Z',
    'last_ai_batch_hours_ago': 2.5,
    'pending_review_count': 12,           # Events waiting for AI
    'total_events': 50,
    'successful_events': 41,
    'empty_events': 9,
    'status': 'healthy'  # or 'warning' or 'critical'
}

# GET /api/quality/alerts?days=7&limit=50
# Returns:
{
    'alerts': [
        {
            'id': 1,
            'type': 'empty_rate',
            'severity': 'critical',
            'message': 'Empty event rate 35% exceeded threshold 30%',
            'camera': 'Cam2N',
            'data': {...},
            'created_at': '2025-01-13T14:30:00Z',
            'resolved_at': null
        }
    ]
}

# GET /api/quality/camera-metrics
# Returns metrics breakdown per camera

# GET /api/quality/trends?days=7
# Returns 7-day historical data for charts

# GET /api/quality/pending-events
# Returns list of events in AI review queue
```

#### Task 2.2: Create AI Batch Processing Tool (1 hour)

**File:** `backend/tools/batch_ai_review.py`

**Usage:**
```bash
# Process up to 10 pending events
python3 backend/tools/batch_ai_review.py \
  --api-key $OPENAI_API_KEY \
  --batch-size 10

# Dry run (no DB updates)
python3 backend/tools/batch_ai_review.py \
  --api-key $OPENAI_API_KEY \
  --dry-run

# Use Claude instead of OpenAI
python3 backend/tools/batch_ai_review.py \
  --api-key $CLAUDE_API_KEY \
  --ai-provider claude
```

**Process Flow:**
```python
1. Query DB for events with needs_ai_review=1
2. For each event:
   - Load top 3 frames (rank 1-3)
   - Encode to base64
   - Call OpenAI Vision API with prompt
   - Parse response
   - If "TimeGo" found → Update DB with success
   - If not found → Mark as ai_failed
   - Archive event folder
3. Update last_run.txt timestamp
4. Print summary statistics
```

**AI Prompt:**
```
"Please read and decode the QR code in these images.
The QR code should contain the text 'TimeGo'.
Return only the decoded text."
```

---

### Phase 3A: Frontend AI Usage Page (3 hours)

**Purpose:** Create user interface for AI configuration and monitoring

#### Task 3A.1: Enable Usage Menu in Sidebar (15 minutes)

**File:** `frontend/src/components/sidebar/components/Content.tsx`

**Location:** Lines 207-220 (Usage menu item)

**Changes:**
1. Change cursor from `'not-allowed'` to `'pointer'`
2. Add onClick handler: `router.push('/usage')`
3. Change icon color from `gray` to `textColor`
4. Update text from "Usage" to "AI Usage"
5. Remove opacity=0.4

**Result:**
- Usage menu becomes clickable
- Routes to /usage page
- Visual style matches other active menu items (My Plan, Logout)

---

#### Task 3A.2: Create AI Usage Page (2 hours)

**File:** `frontend/src/app/usage/page.tsx` (NEW)

**Page Structure:**

**Section 1: AI Configuration Card**
- Toggle switch: Enable/Disable AI QR Recovery
- Radio buttons:
  - "ePACK Managed Key" (recommended)
  - "My Own API Key"
- Conditional input field (shows if "My Own" selected):
  - API Key input (password field)
  - Test button (validates key)
- Save button

**Section 2: Usage Statistics Card**
- Display current month stats:
  - Total Recoveries: 45
  - Successful: 37 (82%)
  - Failed: 8 (18%)
  - Total Cost: $0.81
  - Avg Response Time: 3.2s
- Progress bars for visual representation
- Auto-refresh every 60 seconds

**Section 3: Recovery History Table**
- Columns:
  - Time (e.g., "14:23 Today")
  - Camera (e.g., "Cam2N")
  - Result (✅ TRACK123 or ❌ Failed)
  - Cost (e.g., "$0.02")
  - Confidence (e.g., "92%")
- Show last 10 records
- "View Full History" button → modal with all logs
- Pagination for large datasets

**Layout:**
```
┌─────────────────────────────────────────┐
│ AI Usage                                │
├─────────────────────────────────────────┤
│                                         │
│ 🤖 AI QR Recovery Configuration         │
│ ┌─────────────────────────────────────┐ │
│ │ [✓] Enable AI QR Recovery           │ │
│ │                                     │ │
│ │ API Source:                         │ │
│ │ ○ ePACK Managed (recommended)     │ │
│ │ ● My Own API Key                    │ │
│ │                                     │ │
│ │ API Key: [sk-ant-•••••] [Test ✅]   │ │
│ │                                     │ │
│ │ [Save Configuration]                │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ 📊 This Month's Usage                   │
│ ┌─────────────────────────────────────┐ │
│ │ Total Recoveries:        45         │ │
│ │ Successful:              37 (82%)   │ │
│ │ Failed:                   8 (18%)   │ │
│ │                                     │ │
│ │ Total Cost:         $0.81           │ │
│ │ Avg Response:        3.2s           │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ 📜 Recent AI Recoveries                 │
│ ┌─────────────────────────────────────┐ │
│ │ Time    Camera  Result      Cost    │ │
│ │ ──────────────────────────────────  │ │
│ │ 14:23   Cam2N   ✅ TRACK123  $0.02  │ │
│ │ 14:15   Cam1N   ❌ Failed    $0.02  │ │
│ │ 13:45   Cam2N   ✅ TRACK124  $0.02  │ │
│ │                                     │ │
│ │ [View Full History]                 │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Components to use:**
- Chakra UI Card, Box, VStack, HStack
- Switch (toggle)
- Radio, RadioGroup
- Input (password type for API key)
- Button
- Table, Thead, Tbody, Tr, Td
- Badge (for status indicators)
- Progress (for success rate bar)

---

#### Task 3A.3: Create AI Service (30 minutes)

**File:** `frontend/src/services/aiService.ts` (NEW)

**Methods:**

**1. `getConfig()`**
- GET /api/ai/config
- Returns AI configuration + stats

**2. `updateConfig(config)`**
- POST /api/ai/config
- Save AI settings

**3. `testApiKey(apiKey)`**
- POST /api/ai/test
- Validate API key

**4. `getRecoveryLogs(limit = 50)`**
- GET /api/ai/recovery-logs
- Fetch history

**Example:**
```typescript
export class AIService {
  static async getConfig() {
    const response = await fetch('http://localhost:8080/api/ai/config');
    return response.json();
  }

  static async updateConfig(config: {
    ai_enabled: boolean;
    api_provider: string;
    api_key?: string;
    use_vtrack_key: boolean;
  }) {
    const response = await fetch('http://localhost:8080/api/ai/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return response.json();
  }

  static async testApiKey(apiKey: string) {
    const response = await fetch('http://localhost:8080/api/ai/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey })
    });
    return response.json();
  }

  static async getRecoveryLogs(limit = 50) {
    const response = await fetch(`http://localhost:8080/api/ai/recovery-logs?limit=${limit}`);
    return response.json();
  }
}
```

---

#### Task 3A.4: User Flow Testing (15 minutes)

**Test Scenarios:**

**Scenario 1: First-time Enable**
```
1. User clicks "Usage" in sidebar
2. Page loads with AI disabled
3. User toggles ON "Enable AI Recovery"
4. Selects "ePACK Managed" (default)
5. Clicks "Save Configuration"
6. Backend enables AI
7. Stats show "0 recoveries this month"
8. Success message displays
```

**Scenario 2: Custom API Key**
```
1. User selects "My Own API Key"
2. Input field appears
3. User pastes key: sk-ant-api03-...
4. Clicks "Test" button
5. Backend validates key
6. Shows "✅ Valid" or "❌ Invalid"
7. User clicks "Save"
8. Key encrypted and stored
9. Stats update with custom key usage
```

**Scenario 3: Monitor Usage**
```
1. User returns to Usage page
2. Stats auto-refresh every 60s
3. Shows updated recovery count
4. Cost accumulates
5. Table shows latest recoveries
6. User clicks "View Full History"
7. Modal opens with pagination
8. Can filter by camera/date
```

---

### Phase 3B: Frontend Quality Dashboard (4 hours)

#### Task 3B.1: Create Quality Monitoring Page (2.5 hours)

**Page Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Quality Monitoring                  Last update: 2m ago  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 📈 Key Metrics (Last 24 hours)                    ✅    ││
│ ├─────────────────────────────────────────────────────────┤│
│ │                                                          ││
│ │ Empty Event Rate                          18% ✅        ││
│ │ ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░                ││
│ │ Normal range: 0-30%                                      ││
│ │                                                          ││
│ │ Frame Export Success Rate                 95% ✅        ││
│ │ ████████████████████████████████░░░░░░░░                ││
│ │ Target: >90%                                             ││
│ │                                                          ││
│ │ AI Batch Processing                   2 hours ago ✅    ││
│ │ ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                ││
│ │ Alert threshold: 24 hours                                ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌───────────────────────┐  ┌───────────────────────────┐  │
│ │ 📦 Pending Review     │  │ 🔔 Recent Alerts          │  │
│ ├───────────────────────┤  ├───────────────────────────┤  │
│ │ 12 events in queue    │  │ Jan 13 14:30             │  │
│ │                       │  │ ⚠️  Empty rate 35%       │  │
│ │ [Process with AI]     │  │ Camera: Cam2N            │  │
│ │ [Review Manually]     │  │                           │  │
│ │                       │  │ Jan 13 10:15             │  │
│ │ Oldest: 6 hours ago   │  │ ⚠️  AI batch overdue     │  │
│ └───────────────────────┘  └───────────────────────────┘  │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 📹 Camera-Specific Metrics                              ││
│ │                                                          ││
│ │ Camera  │ Events │ Empty Rate │ Last Event │ Status    ││
│ │─────────┼────────┼────────────┼────────────┼───────────││
│ │ Cam1N   │   15   │    12%     │  10m ago   │  ✅       ││
│ │ Cam2N   │   23   │    25%     │   5m ago   │  ⚠️       ││
│ │ CamTest │    7   │     0%     │  2h ago    │  ✅       ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 📊 Historical Trends (Last 7 Days)                      ││
│ │     Empty Event Rate                                     ││
│ │ 40% │                                                    ││
│ │ 30% │                        ●                           ││
│ │ 20% │        ●───●───●───●       ●───●───●             ││
│ │ 10% │    ●                                               ││
│ │  0% └─────────────────────────────────────────          ││
│ │     Mon  Tue  Wed  Thu  Fri  Sat  Sun                   ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- `QualityMetricsCard.tsx` - Display 3 key metrics with progress bars
- `MetricRow.tsx` - Individual metric with status indicator
- `PendingReviewCard.tsx` - Queue status and action buttons
- `RecentAlertsCard.tsx` - Recent alerts list
- `CameraMetricsTable.tsx` - Per-camera breakdown
- `HistoricalTrendChart.tsx` - Line chart for trends

**Auto-refresh:** Every 60 seconds

#### Task 3.2: Add Sidebar Menu Item (1.5 hours)

**Sidebar Position:**
```
┌─────────────────────┐
│  VTrack             │
├─────────────────────┤
│ 🏠 Dashboard        │
│ 📋 Program          │
│ 🔍 Trace            │
│ 📹 Camera Config    │
│ 📊 Quality      ⚠️  │  ← NEW (with dynamic badge)
│ ⚙️  Settings        │
└─────────────────────┘
```

**Badge Logic:**
```typescript
// Fetch status every 60s
const { status } = await fetch('/api/quality/metrics');

// Set badge based on status
if (status === 'critical') badge = '🔴';
else if (status === 'warning') badge = '⚠️';
else badge = null;  // No badge when healthy
```

**Permission:** Admin + Manager only

---

### Phase 4: Testing & Deployment (2 hours)

#### Task 4.1: Feature Flag & Pilot Test (1 hour)

**Enable Feature:**
```bash
# Set environment variable
export ENABLE_EMPTY_EVENTS=true

# Add to .env
echo "ENABLE_EMPTY_EVENTS=true" >> .env

# Restart frame sampler
supervisorctl restart frame_sampler
```

**Test with Cam2N Only:**
```python
# In frame_sampler_trigger.py
if self.empty_event_tracking_enabled and camera_name == "Cam2N":
    # Use new logic
    self._handle_empty_event(...)
else:
    # Use old logic (skip empty events)
    pass
```

**Pilot Test Checklist:**
```
□ Process 1 video with Cam2N
□ Verify empty events saved:
  sqlite3 database.db "SELECT * FROM packing_events WHERE status='qr_failed' LIMIT 5;"

□ Check frames exported:
  ls -la resources/ai_review_queue/event_*/

□ Open Quality dashboard:
  http://localhost:3000/quality

□ Verify metrics correct

□ Test AI batch (dry run):
  python3 tools/batch_ai_review.py --dry-run

□ Monitor logs:
  tail -f var/logs/frame_processing/Cam2N/*.log
```

#### Task 4.2: Emergency Stop Mechanism (30 minutes)

**Implementation:**
```python
EMERGENCY_DISABLE_FILE = "/tmp/disable_empty_event_tracking"

def should_track_empty_events(self):
    # Check emergency stop
    if os.path.exists(EMERGENCY_DISABLE_FILE):
        self.logger.warning("🚨 Empty event tracking DISABLED")
        return False

    return self.empty_event_tracking_enabled
```

**Emergency Commands:**
```bash
# STOP immediately (no restart needed)
touch /tmp/disable_empty_event_tracking

# Resume
rm /tmp/disable_empty_event_tracking

# Check status
[ -f /tmp/disable_empty_event_tracking ] && echo "DISABLED" || echo "ENABLED"
```

#### Task 4.3: Integration Testing (30 minutes)

**Test Script:**
```bash
#!/bin/bash
# Test complete workflow

# 1. Process test video
# 2. Check DB for empty events
# 3. Verify frames exported
# 4. Test API endpoints
# 5. Run AI batch (dry run)
# 6. Test emergency stop

echo "✅ All tests passed"
```

---

## Database Schema

### Modified Table: packing_events

```sql
CREATE TABLE packing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_path TEXT NOT NULL,
    camera_name TEXT NOT NULL,
    transition_time INTEGER NOT NULL,
    mvd TEXT,  -- NULL for empty events

    -- NEW COLUMNS:
    status TEXT DEFAULT 'completed',
    needs_ai_review BOOLEAN DEFAULT 0,
    ai_review_frames_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Status values:
-- 'completed': Normal event (QR decoded by WeChat)
-- 'qr_failed': Empty event (QR not decoded, needs AI)
-- 'ai_completed': AI successfully decoded
-- 'ai_failed': AI also failed (needs manual entry)
-- 'manual_entry': Admin entered manually
```

### New Table: quality_alerts

```sql
CREATE TABLE quality_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,      -- 'empty_rate', 'export_fail', 'ai_batch_overdue'
    severity TEXT NOT NULL,        -- 'warning', 'critical'
    message TEXT NOT NULL,
    camera_name TEXT,
    data JSON,                     -- Additional data (rates, counts, etc.)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME
);
```

---

## AI Batch Processing

### Workflow

```
1. Scan ai_review_queue/ directory
   └─ Find event_* folders

2. For each pending event:
   ├─ Load metadata.json
   ├─ Get top 3 frames (rank 1-3)
   ├─ Encode images to base64
   └─ Call AI Vision API

3. OpenAI GPT-4 Vision API:
   ├─ Model: gpt-4-vision-preview
   ├─ Max tokens: 300
   ├─ Prompt: "Read QR code text 'TimeGo'"
   └─ Response: parsed text

4. Process response:
   ├─ If "TimeGo" found:
   │   ├─ Update DB: status='ai_completed', mvd='TimeGo'
   │   └─ Archive event to ai_review_archive/
   │
   └─ If not found:
       ├─ Update DB: status='ai_failed'
       └─ Keep in queue for manual entry

5. Update last_run.txt with timestamp

6. Print summary:
   ✅ Success: 8/10
   ❌ Failed: 2/10
```

### Cost Estimation

**OpenAI Pricing (GPT-4 Vision):**
- Input: $0.01 per image
- 3 images per event = $0.03 per event

**Monthly Cost Example:**
- 20 empty events/day × 30 days = 600 events/month
- 600 events × $0.03 = $18/month

**Cost Control:**
- User provides own API key (BYOK)
- Batch processing (not real-time)
- Only process truly failed QR codes

### AI Prompt Engineering

**Basic Prompt:**
```
Please read and decode the QR code in these images.
The QR code should contain the text 'TimeGo'.
Return only the decoded text.
```

**Enhanced Prompt (if basic fails):**
```
You are a QR code expert. I'm showing you 3 images of the same QR code
taken from different angles/lighting. The QR code should contain the
text "TimeGo" (case-insensitive).

Please:
1. Analyze all 3 images
2. Decode the QR code
3. Return ONLY the decoded text
4. If you can't decode it with certainty, return "UNABLE_TO_DECODE"

Images show a QR code that may be:
- Partially obscured
- Blurry or out of focus
- At an angle
- Poor lighting

Expected text: "TimeGo"
```

---

## Quality Monitoring Dashboard

### Metrics Explained

#### 1. Empty Event Rate

**Definition:**
```
Empty Event Rate = (Events without QR) / (Total Events) × 100%
```

**Thresholds:**
- ✅ 0-15%: Normal (good QR printing/camera quality)
- ⚠️ 15-30%: Warning (check camera/QR quality)
- 🔴 >30%: Critical (serious issue - investigate immediately)

**Common Causes of High Rate:**
- Camera out of focus
- Poor lighting conditions
- QR stickers damaged/wrinkled
- Worker covering QR with hand
- Wrong camera angle

#### 2. Frame Export Success Rate

**Definition:**
```
Export Success = (Events with frames exported) / (Total empty events) × 100%
```

**Thresholds:**
- ✅ >95%: Excellent
- ⚠️ 90-95%: Warning
- 🔴 <90%: Critical (disk/permission issues)

**Common Causes of Failure:**
- Disk space full
- Permission issues
- Video file corrupt/missing
- ROI configuration invalid

#### 3. AI Batch Status

**Definition:**
```
Hours Since Last Run = NOW - Last AI Batch Timestamp
```

**Thresholds:**
- ✅ <12h: Good (batch running regularly)
- ⚠️ 12-24h: Warning (should run soon)
- 🔴 >24h: Critical (batch not running - check cron/API key)

**Common Causes:**
- Cron job disabled/failed
- API key expired
- Network issues
- Script crash

### Alert Rules

**Alert 1: Empty Rate > 30%**
```
Trigger: (empty_events / total_events) > 0.30 in last 24h
Severity: Critical
Action: Check camera feed, QR sticker quality
```

**Alert 2: Export Fail > 10%**
```
Trigger: (failed_exports / empty_events) > 0.10 in last 24h
Severity: Critical
Action: Check disk space, logs, permissions
```

**Alert 3: AI Batch Overdue**
```
Trigger: (NOW - last_ai_batch) > 24 hours
Severity: Warning
Action: Run manual batch, check cron, verify API key
```

---

## Testing Strategy

### Unit Tests

```python
# test_qr_frame_exporter.py
def test_export_frames_success():
    """Test frame export with valid video and ROI"""
    exporter = QRFrameExporter()
    result = exporter.export_top_5_frames_for_event(
        event_id=999,
        video_path="test_videos/sample.mp4",
        transition_time=45,
        roi_config={'x': 100, 'y': 200, 'w': 300, 'h': 300}
    )
    assert result['success'] == True
    assert result['frames_exported'] == 5

def test_export_frames_no_qr():
    """Test when no failed QR found"""
    # Should return success but 0 frames
    pass

def test_export_frames_video_not_found():
    """Test with invalid video path"""
    # Should return success=False with error
    pass
```

### Integration Tests

```bash
# Full workflow test
1. Insert test video into file_list
2. Trigger frame sampling
3. Verify empty event saved to DB
4. Check frames exported to queue
5. Query Quality API endpoints
6. Run AI batch (dry run)
7. Verify UI displays correctly
```

### Manual Testing Checklist

```
□ Process video with known failures
□ Verify all events tracked (100%)
□ Check frames quality (viewable images)
□ Test Quality dashboard loads
□ Verify metrics calculations correct
□ Test auto-refresh works
□ Check sidebar badge updates
□ Test AI batch with 1 event
□ Verify emergency stop works
□ Test rollback procedure
```

---

## Backup & Recovery

### Pre-Deployment Backup

```bash
# Create comprehensive backup
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)_pre_empty_events"
mkdir -p "$BACKUP_DIR"

# 1. Backup database
sqlite3 database.db ".backup '$BACKUP_DIR/database.db'"

# 2. Backup code
cp backend/modules/technician/frame_sampler_trigger.py "$BACKUP_DIR/"

# 3. Git tag
git tag "backup-$(date +%Y%m%d-%H%M%S)"

# 4. Log
echo "$(date): Pre-deployment backup at $BACKUP_DIR" >> backup/backup_log.txt
```

### Rollback Procedure

```bash
#!/bin/bash
# rollback.sh <backup_dir>

BACKUP_DIR="$1"

# 1. Stop services
supervisorctl stop frame_sampler

# 2. Restore database
cp "$BACKUP_DIR/database.db" database.db

# 3. Restore code
cp "$BACKUP_DIR/frame_sampler_trigger.py" backend/modules/technician/

# 4. Disable feature
export ENABLE_EMPTY_EVENTS=false

# 5. Restart services
supervisorctl start frame_sampler

echo "✅ Rollback completed"
```

### Rollback Triggers

**Automatic rollback if:**
- Empty event rate > 40% for 2+ hours
- Frame export fail rate > 50%
- Performance degradation > 20%
- Database corruption detected

**Manual rollback:**
```bash
# Emergency stop (keep code, disable feature)
touch /tmp/disable_empty_event_tracking

# Full rollback (restore backup)
./backup/rollback.sh backup/20250113_140000_pre_empty_events
```

---

## Deployment Plan

### Phase 1: Pilot (Week 1)

```
Day 1-2: Deploy to Cam2N only
  □ Enable feature flag for Cam2N
  □ Monitor metrics closely
  □ Check logs every 2 hours
  □ Verify empty events saving correctly

Day 3-4: Test AI batch processing
  □ Run manual batches with small sets
  □ Verify success rate >70%
  □ Check costs are acceptable
  □ Refine prompts if needed

Day 5-7: Full monitoring
  □ Quality dashboard review
  □ Alert testing
  □ Performance monitoring
  □ Collect feedback
```

### Phase 2: Expansion (Week 2)

```
Day 8-10: Deploy to all cameras
  □ Enable for all cameras if pilot successful
  □ Monitor aggregate metrics
  □ Check for camera-specific issues

Day 11-14: Production stabilization
  □ Set up automated AI batch (cron)
  □ Configure alert notifications
  □ Document common issues
  □ Train team on dashboard
```

### Deployment Checklist

**Pre-Deployment:**
```
□ Code review completed
□ Tests passed (unit + integration)
□ Backup created (DB + code)
□ Git tagged
□ Feature flag OFF by default
□ Emergency stop tested
□ Rollback procedure documented
□ Team notified
```

**Deployment:**
```
□ Deploy code (git pull)
□ Run database migration
□ Restart services
□ Enable feature for pilot camera
□ Monitor logs (30 minutes)
□ Check Quality dashboard
□ Process test video
□ Verify empty events tracked
```

**Post-Deployment:**
```
□ Monitor metrics for 24h
□ Run AI batch manually
□ Check costs
□ Collect feedback
□ Document issues
□ Plan improvements
```

---

## Monitoring & Maintenance

### Daily Tasks

```
□ Check Quality dashboard
□ Review empty event rate
□ Verify AI batch ran
□ Check pending queue size
```

### Weekly Tasks

```
□ Review quality trends
□ Analyze camera-specific issues
□ Clean up old archives (>30 days)
□ Check disk space
□ Review AI costs
```

### Monthly Tasks

```
□ Analyze long-term trends
□ Optimize thresholds
□ Review and improve AI prompts
□ Update documentation
□ Plan improvements
```

---

## Troubleshooting Guide

### Issue: High Empty Event Rate (>30%)

**Diagnosis:**
```bash
# Check which camera has issues
sqlite3 database.db "
SELECT camera_name,
       COUNT(*) as total,
       SUM(CASE WHEN status='qr_failed' THEN 1 ELSE 0 END) as empty
FROM packing_events
WHERE created_at > datetime('now', '-24 hours')
GROUP BY camera_name;"
```

**Solutions:**
1. Check camera feed (focus, angle, lighting)
2. Inspect QR sticker quality
3. Review recent videos manually
4. Adjust camera ROI if needed

### Issue: Frame Export Failing

**Diagnosis:**
```bash
# Check disk space
df -h

# Check permissions
ls -la resources/ai_review_queue/

# Check logs
tail -f var/logs/frame_processing/*.log | grep "export"
```

**Solutions:**
1. Free up disk space
2. Fix permissions: `chmod 755 resources/ai_review_queue/`
3. Verify video files accessible
4. Check ROI configuration

### Issue: AI Batch Not Running

**Diagnosis:**
```bash
# Check cron
crontab -l | grep batch_ai_review

# Check last run
cat var/logs/ai_batch/last_run.txt

# Check API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

**Solutions:**
1. Fix cron job
2. Verify API key valid
3. Run manual batch
4. Check network connectivity

---

## Success Criteria

### Functional

✅ All packing events tracked (100% coverage)
✅ Empty events saved with correct status
✅ Top 5 frames exported for each empty event
✅ Quality dashboard displays real-time metrics
✅ Alerts trigger at thresholds
✅ AI batch processing works correctly
✅ Sidebar shows Quality menu with badge

### Performance

✅ Frame sampling speed < 5% slower
✅ Database queries < 100ms
✅ UI loads in < 2 seconds
✅ Auto-refresh no lag

### Quality

✅ Empty event rate < 30%
✅ Frame export success rate > 90%
✅ AI batch runs daily
✅ After AI: 95%+ event coverage

---

## Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Backend Core** | 4 hours | Database, frame exporter, modified frame_sampler |
| **Phase 2A: Real-time AI Recovery** | 5 hours | AI service, config management, API routes, frame sampler integration |
| **Phase 2B: Quality Monitoring API** | 3 hours | Quality API, monitoring endpoints |
| **Phase 3A: Frontend AI Usage Page** | 3 hours | AI config UI, usage stats, recovery history |
| **Phase 3B: Frontend Quality Dashboard** | 4 hours | Quality monitoring page, alerts, trends |
| **Phase 4: Testing & Deployment** | 2 hours | Feature flag, tests, emergency stop |
| **Total** | **21 hours** | **Full system with real-time AI ready** |

### Implementation Priority

**HIGH PRIORITY (Must Have):**
- Phase 1: Backend Core (empty event tracking)
- Phase 2A: Real-time AI Recovery (core AI functionality)
- Phase 3A: Frontend AI Usage Page (user configuration)

**MEDIUM PRIORITY (Should Have):**
- Phase 2B: Quality Monitoring API (system health)
- Phase 3B: Quality Dashboard (monitoring UI)

**LOW PRIORITY (Nice to Have):**
- Advanced analytics
- Custom AI prompts
- Multi-provider support (OpenAI + Claude)

---

## Appendix

### Environment Variables

```bash
# Feature flags
ENABLE_EMPTY_EVENTS=true          # Enable empty event tracking
ENABLE_AI_RECOVERY=true           # Enable real-time AI recovery

# AI Configuration (ePACK managed keys)
VTRACK_CLAUDE_API_KEY=sk-ant-api03-...    # ePACK's Claude API key
VTRACK_OPENAI_API_KEY=sk-...              # ePACK's OpenAI API key (optional)

# API key encryption
AI_KEY_ENCRYPTION_KEY=<fernet-key>        # Fernet encryption key for customer API keys

# Quality thresholds
EMPTY_EVENT_THRESHOLD=30          # percentage
EXPORT_FAIL_THRESHOLD=10          # percentage
AI_BATCH_TIMEOUT_HOURS=24         # hours (for batch processing mode)

# Performance tuning
AI_MAX_FRAMES=3                   # Max frames to send to AI per event
AI_TIMEOUT_SECONDS=30             # AI API timeout
AI_RETRY_ATTEMPTS=2               # Number of retries on failure
```

**Setup Instructions:**

1. **Generate Encryption Key:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output to AI_KEY_ENCRYPTION_KEY
```

2. **Add to .env file:**
```bash
echo "ENABLE_AI_RECOVERY=true" >> .env
echo "VTRACK_CLAUDE_API_KEY=sk-ant-api03-..." >> .env
echo "AI_KEY_ENCRYPTION_KEY=<generated-key>" >> .env
```

3. **Restart services:**
```bash
supervisorctl restart frame_sampler
supervisorctl restart backend
```

### File Structure

```
ePACK/
├── backend/
│   ├── modules/
│   │   ├── ai/  ← NEW FOLDER
│   │   │   ├── __init__.py
│   │   │   ├── ai_qr_recovery.py (NEW) - Main AI service
│   │   │   ├── ai_config.py (NEW) - Config management
│   │   │   └── routes.py (NEW) - AI API endpoints
│   │   │
│   │   └── technician/
│   │       ├── frame_sampler_trigger.py (MODIFIED) - Add AI integration
│   │       ├── qr_frame_exporter.py (NEW) - Frame export logic
│   │       └── log_parser.py (NEW - optional)
│   │
│   ├── blueprints/
│   │   └── quality_monitoring_bp.py (NEW) - Quality metrics API
│   │
│   ├── tools/
│   │   ├── batch_ai_review.py (NEW - optional) - Batch processing
│   │   └── monitor_quality.py (NEW) - Quality monitoring
│   │
│   ├── migrations/
│   │   └── 001_add_ai_recovery.sql (NEW) - Database schema
│   │
│   └── app.py (MODIFIED) - Register ai_bp blueprint
│
├── frontend/src/
│   ├── app/
│   │   └── usage/
│   │       └── page.tsx (NEW) - AI Usage page
│   │
│   ├── components/
│   │   ├── sidebar/components/
│   │   │   └── Content.tsx (MODIFIED) - Enable Usage menu
│   │   │
│   │   └── quality/ (NEW - optional)
│   │       ├── QualityMetricsCard.tsx
│   │       ├── PendingReviewCard.tsx
│   │       └── ... (other components)
│   │
│   └── services/
│       └── aiService.ts (NEW) - AI API client
│
├── resources/
│   ├── ai_review_queue/ (NEW) - Pending AI review
│   └── ai_review_archive/ (NEW) - Processed events
│
├── backup/
│   ├── create_backup.sh (NEW)
│   └── rollback.sh (NEW)
│
└── docs/
    └── empty_event_tracking_and_ai_enhancement.md (this file)
```

**Files Summary by Phase:**

**Phase 1 (4 hours):**
- ✅ `backend/modules/technician/qr_frame_exporter.py`
- ✅ `backend/modules/technician/frame_sampler_trigger.py` (partial)
- ✅ `backend/migrations/001_add_empty_event_tracking.sql`

**Phase 2A (5 hours):**
- ✅ `backend/modules/ai/ai_qr_recovery.py`
- ✅ `backend/modules/ai/ai_config.py`
- ✅ `backend/modules/ai/routes.py`
- ✅ `backend/modules/technician/frame_sampler_trigger.py` (AI integration)
- ✅ `backend/app.py` (register blueprint)
- ✅ Database: `ai_config` + `ai_recovery_logs` tables

**Phase 3A (3 hours):**
- ✅ `frontend/src/app/usage/page.tsx`
- ✅ `frontend/src/components/sidebar/components/Content.tsx` (modify)
- ✅ `frontend/src/services/aiService.ts`

**Total NEW files:** 8 files
**Total MODIFIED files:** 3 files
**Total LINES OF CODE (estimated):** ~2,000 lines

### Useful Commands

```bash
# Check empty events
sqlite3 database.db "SELECT COUNT(*) FROM packing_events WHERE status='qr_failed';"

# View pending queue
ls -d resources/ai_review_queue/event_* | wc -l

# Run AI batch
python3 backend/tools/batch_ai_review.py --api-key $OPENAI_KEY

# Emergency stop
touch /tmp/disable_empty_event_tracking

# Check metrics
curl http://localhost:5000/api/quality/metrics | jq

# Monitor logs
tail -f var/logs/frame_processing/*/log_*.txt
```

---

---

## Quick Start Guide

### For Developers (Implementation)

**Step 1: Setup Backend AI (5 hours)**
```bash
# 1. Create AI module folder
mkdir -p backend/modules/ai

# 2. Implement files (see Phase 2A tasks):
# - ai_qr_recovery.py
# - ai_config.py
# - routes.py

# 3. Add database tables
python3 backend/migrations/run_migration.py

# 4. Set environment variables
export VTRACK_CLAUDE_API_KEY=sk-ant-...
export AI_KEY_ENCRYPTION_KEY=<fernet-key>

# 5. Modify frame_sampler_trigger.py
# Add AI integration logic

# 6. Register blueprint in app.py
# Test: http://localhost:8080/api/ai/config
```

**Step 2: Setup Frontend UI (3 hours)**
```bash
# 1. Enable Usage menu
# Modify: frontend/src/components/sidebar/components/Content.tsx

# 2. Create AI Usage page
# New file: frontend/src/app/usage/page.tsx

# 3. Create AI service
# New file: frontend/src/services/aiService.ts

# 4. Test
npm run dev
# Visit: http://localhost:3000/usage
```

**Step 3: Testing (30 minutes)**
```bash
# 1. Enable AI in UI
# Go to: http://localhost:3000/usage
# Toggle ON "Enable AI Recovery"
# Select "ePACK Managed"
# Click Save

# 2. Process test video with failed QR
# Check logs for: "🤖 Trying AI recovery..."

# 3. Verify in database
sqlite3 database.db "SELECT * FROM ai_recovery_logs LIMIT 5;"

# 4. Check Usage page
# Should show: 1 recovery, cost ~$0.02
```

---

### For End Users (Usage)

**Step 1: Enable AI Recovery**
1. Click on avatar icon in sidebar (bottom left)
2. Click "AI Usage" from dropdown menu
3. Toggle ON "Enable AI QR Recovery"
4. Select "ePACK Managed Key" (recommended)
5. Click "Save Configuration"
6. Wait for success message

**Step 2: Monitor Usage**
1. Return to "AI Usage" page anytime
2. View current month statistics:
   - Total recoveries
   - Success rate
   - Cost
3. Scroll down to see recent recovery history
4. Click "View Full History" for detailed logs

**Step 3: Use Custom API Key (Optional)**
1. Get Claude API key from: https://console.anthropic.com
2. Go to "AI Usage" page
3. Select "My Own API Key"
4. Paste your key: sk-ant-api03-...
5. Click "Test" to verify
6. Click "Save" when test passes
7. Billing goes directly to your Anthropic account

---

## Cost Management

### For ePACK (Service Provider)

**Pricing Model:**
- **Pro License**: $199/month (includes 1,000 AI requests)
- **Enterprise**: $499/month (unlimited AI requests)
- Extra requests: $0.20 each (for Pro users over quota)

**Cost Structure:**
```
Revenue per Pro user: $199/month
AI cost per user (avg): $10-15/month
Profit margin: 92-95%

Break-even: ~50 AI requests/month
Typical usage: 30-100 requests/month
```

**Cost Control Measures:**
1. Monitor usage via `ai_recovery_logs` table
2. Set alerts for high-usage customers
3. Throttle requests if needed (max 10/minute per user)
4. Cache results (don't re-process same frames)

### For End Users (Customers)

**Typical Monthly Costs:**
- Small business (50 events/day, 20% fail rate): 300 recoveries = $5.40
- Medium business (200 events/day, 15% fail rate): 900 recoveries = $16.20
- Large business (500 events/day, 10% fail rate): 1,500 recoveries = $27.00

**Cost Optimization Tips:**
1. Improve QR code print quality → Less failures
2. Optimize camera setup → Better QR detection
3. Use ePACK managed key → Built into license price
4. Monitor Usage page → Track spending trends

---

**Document Version:** 2.0
**Last Updated:** January 2025
**Status:** Ready for Implementation
**Estimated Completion (Core Features):** 12 hours
**Estimated Completion (Full System):** 21 hours

---
