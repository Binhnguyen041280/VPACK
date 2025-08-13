# CODEBASE DEPENDENCIES ANALYSIS

## 1. FRONTEND API CALLS

### Direct API Client Imports (api.js)
**File:** `frontend/src/api.js`
- Line 12: `export const getCameras = () => api.get("/get-cameras");`
- Line 23: `export const addSources = (sourcesData) => api.post("/save-sources", sourcesData);`
- Line 30: `export const detectCameras = (pathData) => api.post("/detect-cameras", pathData);`

### VtrackConfig.js Direct Calls
**File:** `frontend/src/VtrackConfig.js`
- Line 101: `fetch('http://localhost:8080/api/config/get-sources')`
- Line 143: `fetch('http://localhost:8080/api/config/get-processing-cameras')`
- Line 185: `fetch('http://localhost:8080/api/config/get-sources')`  
- Line 474: `fetch('http://localhost:8080/api/config/debug-cameras')`
- Line 501: `fetch('http://localhost:8080/api/config/get-sources')`
- Line 506: `fetch('http://localhost:8080/api/config/get-processing-cameras')`

### QueryComponent.js
**File:** `frontend/src/QueryComponent.js`
- Line 66: `api.get("/get-cameras")`

### Processing Region Form
**File:** `frontend/src/components/config/ProcessingRegionForm.js`
- Line 35: `api.get("/get-cameras")`

### Hooks - useVtrackConfig.js
**File:** `frontend/src/hooks/useVtrackConfig.js`
- Line 123: References `/api/config/save-general-info`
- Line 174: References `/save-config`
- Line 176: `fetch("http://localhost:8080/api/config/save-config")`
- Line 186: `fetch("http://localhost:8080/get-cameras")`

### ConfigForm.js (Main Configuration Component)
**File:** `frontend/src/components/config/ConfigForm.js`
- Line 56: `fetch('/api/config/save-sources')`
- Line 65: `fetch('/api/config/delete-source/${sourceId}')`
- Line 72: `fetch('/api/config/test-source')`
- Line 81: `fetch('/api/config/update-source-cameras')`
- Line 107: `fetch('/api/config/detect-cameras')`
- Line 136: `fetch('/api/config/save-sources')`
- Line 153: `fetch('/api/config/save-sources')` (overwrite mode)
- Line 178: `fetch('http://localhost:8080/api/config/get-processing-cameras')`
- Line 277: `fetch('/api/config/get-sources')`
- Line 689: `fetch('/api/config/get-camera-folders')` (MISSING ENDPOINT)

## 2. BACKEND IMPORTS AND REFERENCES

### App.py Main Entry Point
**File:** `backend/app.py`
- Line 28: `from modules.config.logging_config import setup_logging, get_logger`
- Line 29: `from modules.config.config import config_bp, init_app_and_config`

### Technician Modules
**File:** `backend/modules/technician/event_detector.py`
- Line 8: `from modules.config.logging_config import get_logger`

**File:** `backend/modules/technician/frame_sampler_trigger.py`
- Line 13: `from modules.config.logging_config import get_logger`
- Line 39: `cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")`
- Line 42: `cursor.execute("SELECT output_path FROM processing_config WHERE id = 1")`
- Line 47: `cursor.execute("SELECT timezone FROM general_info WHERE id = 1")`
- Line 51: `cursor.execute("SELECT frame_rate, frame_interval, min_packing_time FROM processing_config WHERE id = 1")`

**File:** `backend/modules/technician/frame_sampler_no_trigger.py`
- Line 15: `from modules.config.logging_config import get_logger`
- Line 61: `cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")`
- Line 64: `cursor.execute("SELECT output_path FROM processing_config WHERE id = 1")`
- Line 69: `cursor.execute("SELECT timezone FROM general_info WHERE id = 1")`
- Line 73: `cursor.execute("SELECT frame_rate, frame_interval, min_packing_time, motion_threshold, stable_duration_sec FROM processing_config WHERE id = 1")`

### Scheduler Modules
**File:** `backend/modules/scheduler/batch_scheduler.py`
- Line 32: `from modules.config.logging_config import get_logger`
- Line 36: `from .config.scheduler_config import SchedulerConfig`

**File:** `backend/modules/scheduler/program.py`
- Line 41: `from modules.config.logging_config import get_logger`

**File:** `backend/modules/scheduler/program_runner.py`
- Line 42: `from .config.scheduler_config import SchedulerConfig`
- Line 44: `from modules.config.logging_config import get_logger`

**File:** `backend/modules/scheduler/db_sync.py`
- Line 36: `from modules.config.logging_config import get_logger`

**File:** `backend/modules/scheduler/file_lister.py`
- Line 38: `from modules.config.logging_config import get_logger`
- Line 40: `from .config.scheduler_config import SchedulerConfig`

### License Modules  
**File:** `backend/modules/license/license_manager.py`
- Line 13: `from .license_config import *`

**File:** `backend/modules/license/license_checker.py`
- Line 10: `from .license_config import AUTO_CHECK_ON_STARTUP, GRACE_PERIOD_DAYS, CLOUD_VALIDATION_TIMEOUT`

### Blueprints
**File:** `backend/blueprints/cutter_bp.py`
- Line 18: `cursor.execute("SELECT output_path FROM processing_config LIMIT 1")`
- Line 37: `cursor.execute("SELECT video_buffer, max_packing_time FROM processing_config LIMIT 1")`

## 3. DATABASE REFERENCES IN CODE

### Processing Config Table Usage
- `backend/modules/technician/frame_sampler_trigger.py`: Lines 39, 42, 51
- `backend/modules/technician/frame_sampler_no_trigger.py`: Lines 61, 64, 73  
- `backend/blueprints/cutter_bp.py`: Lines 18, 37
- `backend/database.py`: Lines 82, 102, 104, 113, 117, 118, 121

### General Info Table Usage
- `backend/modules/technician/frame_sampler_trigger.py`: Line 47
- `backend/modules/technician/frame_sampler_no_trigger.py`: Line 69
- `backend/database.py`: Lines 386, 388, 398, 402

### Video Sources Table Usage
- `backend/database.py`: Lines 458, 460, 475
- Referenced in foreign key constraints: Lines 313, 336, 354

## 4. CRITICAL DEPENDENCY MAPPING

### API Endpoint Dependencies
1. **Frontend → Backend Route Mapping:**
   - `/get-cameras` → `config_bp.route('/get-cameras')`
   - `/save-sources` → `config_bp.route('/save-sources')`
   - `/detect-cameras` → `config_bp.route('/detect-cameras')`
   - `/save-config` → `config_bp.route('/save-config')`
   - `/get-processing-cameras` → `config_bp.route('/get-processing-cameras')`

2. **Missing/Broken Endpoints:**
   - `/api/config/get-camera-folders` (referenced in ConfigForm.js:689)

### Module Import Dependencies
1. **Logging Config:** 8+ modules depend on `modules.config.logging_config`
2. **Config Module:** `app.py` imports from `modules.config.config`
3. **Scheduler Config:** 4+ modules import from `.config.scheduler_config`

### Database Schema Dependencies
1. **processing_config table:** 
   - 6+ modules directly query this table
   - Used for: input_path, output_path, frame settings, cameras
   
2. **general_info table:**
   - 2+ modules query for timezone, working days
   
3. **video_sources table:**
   - Core table for source management
   - Referenced by foreign keys in 3 other tables

## 5. REFACTORING IMPACT ANALYSIS

### HIGH RISK Changes
1. **Route Path Changes:** Any change to `/api/config/*` paths breaks frontend
2. **Function Name Changes:** Breaks blueprint registration
3. **Request/Response Format Changes:** Breaks API contracts
4. **Database Table/Column Changes:** Breaks 10+ modules

### MEDIUM RISK Changes  
1. **Import Path Changes:** Affects 15+ files
2. **Config Class Changes:** Affects initialization
3. **Blueprint Organization:** May break registration

### LOW RISK Changes
1. **Internal helper functions:** Limited scope impact
2. **Code organization within files:** No external dependencies
3. **Documentation changes:** No functional impact

## 6. ZERO-BREAKAGE MIGRATION STRATEGY

### Phase 1: Maintain Original Imports
- Keep `from modules.config.config import config_bp, init_app_and_config`
- Ensure all original functions remain callable

### Phase 2: Database Schema Compatibility  
- Maintain exact table schemas
- Keep all column names and types
- Preserve foreign key relationships

### Phase 3: API Contract Preservation
- Keep all route paths identical: `/api/config/*`
- Maintain exact request/response formats
- Preserve function signatures

### Phase 4: Import Redirection
- Use `__init__.py` files to redirect imports
- Gradually migrate modules to new structure
- Maintain backward compatibility layers