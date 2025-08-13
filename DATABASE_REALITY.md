# DATABASE REALITY CHECK

## 1. ACTUAL TABLE SCHEMAS

### processing_config Table
```sql
CREATE TABLE processing_config (
    id INTEGER PRIMARY KEY,
    input_path TEXT,
    output_path TEXT,
    storage_duration INTEGER,
    min_packing_time INTEGER,
    max_packing_time INTEGER,
    frame_rate INTEGER,
    frame_interval INTEGER,
    video_buffer INTEGER,
    default_frame_mode TEXT,
    selected_cameras TEXT,
    db_path TEXT NOT NULL,
    run_default_on_start INTEGER DEFAULT 0,
    motion_threshold FLOAT DEFAULT 0.1,
    stable_duration_sec FLOAT DEFAULT 1,
    camera_paths TEXT DEFAULT '{}',
    multiple_sources_enabled INTEGER DEFAULT 0
)
```

### general_info Table
```sql
CREATE TABLE general_info (
    id INTEGER PRIMARY KEY,
    country TEXT,
    timezone TEXT,
    brand_name TEXT,
    working_days TEXT,
    from_time TEXT,
    to_time TEXT
)
```

### video_sources Table
```sql
CREATE TABLE video_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK(source_type IN ('local', 'cloud')),
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    config TEXT,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    folder_depth INTEGER DEFAULT 0,
    parent_folder_id TEXT
)
```

## 2. REAL COLUMN INFORMATION

### processing_config Columns
| Column Name | Type | Nullable | Default Value |
|-------------|------|----------|---------------|
| id | INTEGER | No | PRIMARY KEY |
| input_path | TEXT | Yes | NULL |
| output_path | TEXT | Yes | NULL |
| storage_duration | INTEGER | Yes | NULL |
| min_packing_time | INTEGER | Yes | NULL |
| max_packing_time | INTEGER | Yes | NULL |
| frame_rate | INTEGER | Yes | NULL |
| frame_interval | INTEGER | Yes | NULL |
| video_buffer | INTEGER | Yes | NULL |
| default_frame_mode | TEXT | Yes | NULL |
| selected_cameras | TEXT | Yes | NULL |
| db_path | TEXT | No | NULL |
| run_default_on_start | INTEGER | Yes | 0 |
| motion_threshold | FLOAT | Yes | 0.1 |
| stable_duration_sec | FLOAT | Yes | 1 |
| camera_paths | TEXT | Yes | '{}' |
| multiple_sources_enabled | INTEGER | Yes | 0 |

### general_info Columns
| Column Name | Type | Nullable | Default Value |
|-------------|------|----------|---------------|
| id | INTEGER | No | PRIMARY KEY |
| country | TEXT | Yes | NULL |
| timezone | TEXT | Yes | NULL |
| brand_name | TEXT | Yes | NULL |
| working_days | TEXT | Yes | NULL |
| from_time | TEXT | Yes | NULL |
| to_time | TEXT | Yes | NULL |

### video_sources Columns
| Column Name | Type | Nullable | Default Value |
|-------------|------|----------|---------------|
| id | INTEGER | No | AUTOINCREMENT |
| source_type | TEXT | No | CHECK constraint |
| name | TEXT | No | NULL |
| path | TEXT | No | NULL |
| config | TEXT | Yes | NULL |
| active | INTEGER | Yes | 1 |
| created_at | TIMESTAMP | Yes | CURRENT_TIMESTAMP |
| folder_depth | INTEGER | Yes | 0 |
| parent_folder_id | TEXT | Yes | NULL |

## 3. SAMPLE DATA FORMATS

### processing_config Sample Data
```
ID: 1
Input Path: /Users/annhu/vtrack_app/V_Track/cloud_sync/google_drive_cloud_storage
Selected Cameras: ["Cloud_Cam1", "Cloud_Cam2", "Cloud_Cam3"]
Frame Rate: 30
Frame Interval: 5
```

### JSON String Patterns Found

#### selected_cameras Format
- **Type:** TEXT column storing JSON array
- **Format:** `["Camera1", "Camera2", "Camera3"]`
- **Real Example:** `["Cloud_Cam1", "Cloud_Cam2", "Cloud_Cam3"]`

#### camera_paths Format  
- **Type:** TEXT column storing JSON object
- **Default:** `'{}' `
- **Expected Format:** `{"Camera1": "/path1", "Camera2": "/path2"}`

#### working_days Format (general_info)
- **Type:** TEXT column storing JSON array
- **Format:** `["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]`
- **Note:** Stored in English, converted from Vietnamese input

#### config Format (video_sources)
- **Type:** TEXT column storing JSON object
- **Format:** Complex nested structure depending on source_type
- **Cloud Example:**
```json
{
  "provider": "google_drive",
  "selected_folders": [...],
  "selected_tree_folders": [...],
  "session_token": "...",
  "folder_paths": {...}
}
```

## 4. CRITICAL FINDINGS

### Database Schema Evolution
1. **Additional Columns Added:** The actual schema has MORE columns than the original config.py expects
   - `motion_threshold` (FLOAT)
   - `stable_duration_sec` (FLOAT)  
   - `camera_paths` (TEXT)
   - `multiple_sources_enabled` (INTEGER)
   - `folder_depth` (INTEGER) in video_sources
   - `parent_folder_id` (TEXT) in video_sources

2. **Data Type Consistency:** All JSON data stored as TEXT strings, requiring `json.loads()` and `json.dumps()`

3. **Constraint Validation:** video_sources has CHECK constraint for source_type

### Current Data State
- **processing_config:** Contains real data with cloud source configuration
- **Active Source:** Google Drive cloud storage with 3 cameras configured
- **JSON Serialization:** All complex data structures stored as JSON strings

### Data Format Requirements
1. **selected_cameras:** Must be valid JSON array of strings
2. **camera_paths:** Must be valid JSON object (dictionary)
3. **working_days:** Must be JSON array of English day names
4. **config:** Must be valid JSON object, structure varies by source_type

## 5. COMPATIBILITY REQUIREMENTS

### For Zero-Breakage Migration:
1. **Column Preservation:** All existing columns must remain
2. **Data Type Consistency:** JSON serialization patterns must be maintained
3. **ID Constraints:** processing_config.id must remain 1, general_info.id must remain 1
4. **Foreign Key Integrity:** video_sources references must be preserved
5. **CHECK Constraints:** source_type validation must be maintained

### Critical SQL Patterns to Preserve:
```sql
-- Standard config read
SELECT input_path, selected_cameras FROM processing_config WHERE id = 1

-- Camera update  
UPDATE processing_config SET selected_cameras = ? WHERE id = 1

-- JSON serialization required
json.dumps(camera_list)  # Before INSERT/UPDATE
json.loads(camera_string)  # After SELECT
```

### Migration Safety Checklist:
- [ ] All 17 columns in processing_config preserved
- [ ] All 7 columns in general_info preserved  
- [ ] All 9 columns in video_sources preserved
- [ ] JSON serialization format maintained
- [ ] PRIMARY KEY constraints preserved
- [ ] CHECK constraints preserved
- [ ] DEFAULT values preserved
- [ ] Foreign key relationships intact