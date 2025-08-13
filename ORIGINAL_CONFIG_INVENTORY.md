# ORIGINAL CONFIG INVENTORY

## 1. ORIGINAL ROUTES MAPPING

### Blueprint: `config_bp = Blueprint('config', __name__)`
**URL Prefix:** `/api/config`

| Route Path | HTTP Method | Function Name | Line Number |
|------------|-------------|---------------|-------------|
| `/debug-cameras` | GET | `debug_cameras()` | 735 |
| `/detect-cameras` | POST | `detect_cameras()` | 772 |
| `/update-source-cameras` | POST | `update_source_cameras()` | 811 |
| `/get-cameras` | GET | `get_cameras()` | 841 |
| `/save-config` | POST | `save_config()` | 891 |
| `/save-general-info` | POST | `save_general_info()` | 1047 |
| `/save-sources` | POST | `save_video_sources()` | 1089 |
| `/test-source` | POST | `test_source_connection()` | 1225 |
| `/get-sources` | GET | `get_video_sources()` | 1314 |
| `/update-source/<int:source_id>` | PUT | `update_video_source(source_id)` | 1326 |
| `/delete-source/<int:source_id>` | DELETE | `delete_video_source(source_id)` | 1357 |
| `/toggle-source/<int:source_id>` | POST | `toggle_source_status(source_id)` | 1397 |
| `/get-processing-cameras` | GET | `get_processing_cameras()` | 1469 |
| `/sync-cloud-cameras` | POST | `sync_cloud_cameras()` | 1496 |
| `/refresh-cameras` | POST | `refresh_cameras()` | 1556 |
| `/camera-status` | GET | `get_camera_status()` | 1635 |

### Test Route (Main App)
| Route Path | HTTP Method | Function Name | Line Number |
|------------|-------------|---------------|-------------|
| `/api/test` | GET | `test()` | 1762 |

## 2. FUNCTION SIGNATURES

### Core Configuration Functions

#### `save_config()` - Line 891
- **Parameters:** Request JSON with keys:
  - `video_root` (string) - Main input path
  - `output_path` (string) - Output directory
  - `default_days` (int) - Storage duration
  - `min_packing_time` (int) - Minimum packing time
  - `max_packing_time` (int) - Maximum packing time  
  - `frame_rate` (int) - Frame rate setting
  - `frame_interval` (int) - Frame interval setting
  - `video_buffer` (int) - Video buffer size
  - `selected_cameras` (list) - Selected camera names
  - `run_default_on_start` (int) - Auto-start flag
- **Returns:** JSON response with message and saved data

#### `save_general_info()` - Line 1047
- **Parameters:** Request JSON with keys:
  - `country` (string)
  - `timezone` (string)
  - `brand_name` (string)
  - `working_days` (list) - Vietnamese day names
  - `from_time` (string) - Start time (HH:MM format)
  - `to_time` (string) - End time (HH:MM format)
- **Returns:** JSON response with success message

#### `save_video_sources()` - Line 1089
- **Parameters:** Request JSON with keys:
  - `sources` (list) - Array of source objects
    - Each source: `{source_type, name, path, config, overwrite}`
- **Returns:** JSON with source creation details

### Camera Management Functions

#### `detect_cameras()` - Line 772
- **Parameters:** Request JSON with keys:
  - `path` (string) - Directory path to scan
- **Returns:** JSON with detected cameras and count

#### `get_cameras()` - Line 841
- **Parameters:** None (GET request)
- **Returns:** JSON with camera list and metadata

#### `update_source_cameras()` - Line 811
- **Parameters:** Request JSON with keys:
  - `source_id` (int) - Source identifier
  - `selected_cameras` (list) - Camera names list
- **Returns:** JSON with update confirmation

### Source Management Functions

#### `test_source_connection()` - Line 1225
- **Parameters:** Request JSON with keys:
  - `source_type` (string) - "local", "cloud"
  - `path` (string) - Source path/URL
  - `config` (object) - Additional configuration
- **Returns:** JSON with accessibility status

#### `get_video_sources()` - Line 1314
- **Parameters:** None (GET request)
- **Returns:** JSON with all active sources

### Helper Functions

#### `detect_camera_folders(path)` - Line 625
- **Parameters:** `path` (string) - Directory to scan
- **Returns:** List of camera folder names

#### `get_working_path_for_source(source_type, source_name, source_path)` - Line 675
- **Parameters:** 
  - `source_type` (string)
  - `source_name` (string) 
  - `source_path` (string)
- **Returns:** String - Working directory path

## 3. REQUEST/RESPONSE FORMATS

### `/save-config` Request Format
```json
{
  "video_root": "/path/to/video/directory",
  "output_path": "/path/to/output",
  "default_days": 30,
  "min_packing_time": 10,
  "max_packing_time": 120,
  "frame_rate": 30,
  "frame_interval": 5,
  "video_buffer": 2,
  "selected_cameras": ["Camera1", "Camera2"],
  "run_default_on_start": 1
}
```

### `/save-config` Response Format
```json
{
  "message": "Configuration saved successfully",
  "saved_path": "/verified/path",
  "saved_cameras": ["Camera1", "Camera2"],
  "frame_settings": {
    "frame_rate": 30,
    "frame_interval": 5
  }
}
```

### `/detect-cameras` Request Format
```json
{
  "path": "/path/to/scan"
}
```

### `/detect-cameras` Response Format
```json
{
  "cameras": ["Cam1", "Cam2", "Cam3"],
  "selected_cameras": ["Cam1"],
  "path": "/path/to/scan",
  "count": 3
}
```

### `/save-sources` Request Format  
```json
{
  "sources": [{
    "source_type": "local",
    "name": "MainCamera",
    "path": "/video/directory",
    "config": {},
    "overwrite": false
  }]
}
```

### `/test-source` Request Format
```json
{
  "source_type": "local",
  "path": "/test/path",
  "config": {}
}
```

### `/test-source` Response Format
```json
{
  "accessible": true,
  "message": "Path accessible",
  "source_type": "local"
}
```

## 4. DATABASE OPERATIONS

### Tables Used
- `processing_config` - Main configuration table
- `general_info` - General application settings  
- `video_sources` - Video source definitions

### `processing_config` Table Columns
- `id` (INTEGER PRIMARY KEY) - Always 1
- `input_path` (TEXT) - Main video input directory
- `output_path` (TEXT) - Output directory for clips
- `storage_duration` (INTEGER) - Days to keep data
- `min_packing_time` (INTEGER) - Minimum packing time
- `max_packing_time` (INTEGER) - Maximum packing time
- `frame_rate` (INTEGER) - Video frame rate
- `frame_interval` (INTEGER) - Frame sampling interval
- `video_buffer` (INTEGER) - Video buffer size
- `default_frame_mode` (TEXT) - Frame mode setting
- `selected_cameras` (TEXT) - JSON string of camera names
- `db_path` (TEXT) - Database file path
- `run_default_on_start` (INTEGER) - Auto-start flag

### `general_info` Table Columns
- `id` (INTEGER PRIMARY KEY) - Always 1
- `country` (TEXT)
- `timezone` (TEXT)
- `brand_name` (TEXT)
- `working_days` (TEXT) - JSON string of day names (English)
- `from_time` (TEXT) - Start time
- `to_time` (TEXT) - End time

### `video_sources` Table Columns  
- `id` (INTEGER PRIMARY KEY)
- `source_type` (TEXT) - "local", "cloud", "camera"
- `name` (TEXT) - Source display name
- `path` (TEXT) - Source path/URL
- `config` (TEXT) - JSON configuration string
- `active` (INTEGER) - Active status (0/1)
- `created_at` (DATETIME)

### SQL Query Patterns

#### Insert/Update processing_config
```sql
INSERT OR REPLACE INTO processing_config (
    id, input_path, output_path, storage_duration, min_packing_time,
    max_packing_time, frame_rate, frame_interval, video_buffer, 
    default_frame_mode, selected_cameras, db_path, run_default_on_start
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

#### Update cameras only
```sql
UPDATE processing_config 
SET selected_cameras = ? 
WHERE id = 1
```

#### Get current config
```sql
SELECT input_path, output_path, frame_rate, frame_interval 
FROM processing_config WHERE id = 1
```

## 5. IMPORT STATEMENTS & DEPENDENCIES

### Direct Imports
```python
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Flask, g
from flask_cors import CORS
import os, json, sqlite3, logging, time
```

### Module Imports
```python
from modules.db_utils import find_project_root, get_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.sources.path_manager import PathManager
from database import update_database, DB_PATH, initialize_sync_status
from modules.sources.cloud_endpoints import cloud_bp
from modules.sources.sync_endpoints import sync_bp
```

### Security & Authentication
```python
import jwt
from cryptography.fernet import Fernet
import base64, hashlib
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple
from google.oauth2.credentials import Credentials
import google.auth.exceptions
```

### Classes Defined
- `SecurityConfig()` - Line 67
- `ConfigManager()` - Line 236

### Global Variables
- `config_bp` - Blueprint instance
- `BASE_DIR` - Project root directory
- `CONFIG_FILE` - Config file path  
- `config_manager` - Global config manager instance

## 6. KEY CONSTANTS & CONFIGURATIONS

### File Paths
- `BASE_DIR` = Project root (4 levels up from config.py)
- `CONFIG_FILE` = `{BASE_DIR}/config.json`
- `DB_PATH` = `{BASE_DIR}/database/events.db`

### CORS Configuration
```python
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
```

### Session Configuration
- `PERMANENT_SESSION_LIFETIME` = 90 days
- `SESSION_REFRESH_EACH_REQUEST` = True
- `BACKGROUND_SERVICE_MODE` = True

This inventory captures the complete API contract, database schema, and function signatures from the original config.py file.