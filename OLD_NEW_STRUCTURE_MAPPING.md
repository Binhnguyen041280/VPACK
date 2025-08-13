# OLD → NEW STRUCTURE MAPPING

## 1. FILE ORGANIZATION MAPPING

### Original Structure (WORKING)
```
backend/modules/config/config.py  (1,789 lines)
├── SecurityConfig class (Lines 67-235)
├── ConfigManager class (Lines 236-491)  
├── Helper functions (Lines 492-733)
├── 18 Route handlers (Lines 734-1,722)
└── Main app initialization (Lines 1,726-1,789)
```

### New Structure (BROKEN)
```
backend/modules/config/
├── __init__.py (1 line - EMPTY)
├── config_manager.py (1 line - EMPTY)
├── security_config.py (1 line - EMPTY)
├── config.py (1,789 lines - ORIGINAL FILE)
└── routes/
    ├── camera_routes.py (1 line - EMPTY)
    ├── config_routes.py (1 line - EMPTY)  
    └── source_routes.py (1 line - EMPTY)
```

## 2. CLASS AND FUNCTION REDISTRIBUTION PLAN

### SecurityConfig Class (Lines 67-235)
**MOVE TO:** `modules/config/security_config.py`
```python
# Classes to extract:
- SecurityConfig (Lines 67-235)
  - __init__ (Lines 70-98)
  - _generate_jwt_secret (Lines 99-104)
  - _generate_encryption_key (Lines 106-110)
  - encrypt_credentials (Lines 112-120)
  - decrypt_credentials (Lines 122-130)
  - generate_session_token (Lines 132-142)
  - generate_token_pair (Lines 144-174)
  - should_refresh_token (Lines 176-188)
  - refresh_access_token (Lines 190-212)
  - get_token_time_remaining (Lines 214-222)
  - validate_session_token (Lines 224-234)
```

### ConfigManager Class (Lines 236-491)
**MOVE TO:** `modules/config/config_manager.py`
```python
# Classes to extract:
- ConfigManager (Lines 236-491)
  - __init__ (Lines 239-247)
  - require_session decorator (Lines 250-277)
  - validate_cloud_source (Lines 280-319)
  - get_cloud_credentials (Lines 322-372)
  - refresh_cloud_credentials (Lines 374-413)
  - proxy_cloud_operation (Lines 415-469)
  - cleanup_expired_sessions (Lines 471-490)
```

### Route Handlers Redistribution

#### Camera-Related Routes → `routes/camera_routes.py`
```python
# Routes to move:
- /debug-cameras (Lines 735-770)
- /detect-cameras (Lines 772-809)
- /update-source-cameras (Lines 811-839)
- /get-cameras (Lines 841-889)
- /get-processing-cameras (Lines 1469-1492)
- /sync-cloud-cameras (Lines 1496-1554)
- /refresh-cameras (Lines 1556-1633)
- /camera-status (Lines 1635-1722)
```

#### Configuration Routes → `routes/config_routes.py`
```python
# Routes to move:
- /save-config (Lines 891-1045)
- /save-general-info (Lines 1047-1085)
```

#### Source Management Routes → `routes/source_routes.py`
```python
# Routes to move:
- /save-sources (Lines 1089-1223)
- /test-source (Lines 1225-1312)
- /get-sources (Lines 1314-1324)
- /update-source/<int:source_id> (Lines 1326-1355)
- /delete-source/<int:source_id> (Lines 1357-1395)
- /toggle-source/<int:source_id> (Lines 1397-1467)
```

### Helper Functions Redistribution

#### Keep in main config.py:
```python
# Core functions (Lines 492-733):
- get_config_manager (Lines 495-500)
- init_config (Lines 502-507)
- init_app_and_config (Lines 509-598)
- load_config (Lines 601-623)
- detect_camera_folders (Lines 625-649)
- has_video_files (Lines 651-672)
- get_working_path_for_source (Lines 675-700)
- extract_cameras_from_cloud_folders (Lines 703-732)
```

## 3. IMPORT RESTRUCTURING

### New Import Structure

#### security_config.py imports:
```python
from datetime import datetime, timedelta
import jwt
from cryptography.fernet import Fernet
import base64, hashlib
import os, secrets, json
import logging
from typing import Dict, List, Any, Optional
from google.oauth2.credentials import Credentials
import google.auth.exceptions
```

#### config_manager.py imports:
```python
from datetime import datetime, timedelta
from flask import request, jsonify, g
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple
from google.oauth2.credentials import Credentials
import google.auth.exceptions
import logging
from .security_config import SecurityConfig
```

#### camera_routes.py imports:
```python
from flask import Blueprint, request, jsonify
from datetime import datetime
import json, os
from modules.db_utils import get_db_connection
from modules.sources.path_manager import PathManager
```

#### config_routes.py imports:
```python
from flask import Blueprint, request, jsonify
import json, os, sqlite3
from modules.db_utils import get_db_connection
from modules.scheduler.db_sync import db_rwlock
```

#### source_routes.py imports:
```python
from flask import Blueprint, request, jsonify
import json
from modules.db_utils import get_db_connection
from modules.sources.path_manager import PathManager
```

### Required __init__.py Structure
```python
# modules/config/__init__.py
from .config import config_bp, init_app_and_config, get_config_manager, init_config
from .security_config import SecurityConfig
from .config_manager import ConfigManager

# For backward compatibility
from .routes.camera_routes import camera_bp
from .routes.config_routes import config_bp as config_routes_bp  
from .routes.source_routes import source_bp

__all__ = [
    'config_bp', 'init_app_and_config', 'get_config_manager', 'init_config',
    'SecurityConfig', 'ConfigManager',
    'camera_bp', 'config_routes_bp', 'source_bp'
]
```

## 4. BLUEPRINT REGISTRATION CHANGES

### Original Registration (app.py):
```python
from modules.config.config import config_bp, init_app_and_config
app.register_blueprint(config_bp, url_prefix='/api/config')
```

### New Registration Options:

#### Option 1: Single Blueprint (RECOMMENDED)
```python
from modules.config.config import config_bp, init_app_and_config
app.register_blueprint(config_bp, url_prefix='/api/config')
# All routes remain under /api/config/* - NO BREAKING CHANGES
```

#### Option 2: Multiple Blueprints (RISKY)
```python
from modules.config import camera_bp, config_routes_bp, source_bp
app.register_blueprint(camera_bp, url_prefix='/api/config')
app.register_blueprint(config_routes_bp, url_prefix='/api/config') 
app.register_blueprint(source_bp, url_prefix='/api/config')
# Routes split across blueprints but same URL prefix
```

## 5. ZERO-BREAKAGE MIGRATION STRATEGY

### Phase 1: Keep Original Blueprint
- **DON'T CHANGE:** config_bp registration in app.py
- **DON'T CHANGE:** Route paths (/api/config/*)
- **DON'T CHANGE:** Function signatures
- **PRESERVE:** All imports from `modules.config.config`

### Phase 2: Internal Reorganization  
- Move classes to separate files
- Keep original config.py as aggregator
- Use import redirections for backward compatibility

### Phase 3: Route Organization
```python
# config.py becomes router aggregator:
from .routes.camera_routes import camera_bp as camera_routes
from .routes.config_routes import config_routes_bp as config_routes  
from .routes.source_routes import source_bp as source_routes

# Register sub-routes to main blueprint
config_bp.register_blueprint(camera_routes)
config_bp.register_blueprint(config_routes)
config_bp.register_blueprint(source_routes)
```

## 6. CRITICAL PRESERVATION REQUIREMENTS

### API Endpoints (MUST NOT CHANGE):
- All route paths: `/api/config/*`
- All HTTP methods: GET, POST, PUT, DELETE
- All function names in routes
- All request/response formats

### Import Statements (MUST REMAIN FUNCTIONAL):
```python
# These MUST continue to work:
from modules.config.config import config_bp, init_app_and_config
from modules.config.logging_config import get_logger
```

### Database Operations (MUST NOT CHANGE):
- All SQL queries and table names
- All column references
- All JSON serialization patterns

### Class Interfaces (MUST REMAIN COMPATIBLE):
```python
# These instantiations MUST work:
config_manager = ConfigManager()
security = SecurityConfig()
```

## 7. IMPLEMENTATION ORDER

1. **Create new files with extracted code**
2. **Update imports in new files** 
3. **Create backward compatibility layer in config.py**
4. **Test all API endpoints**
5. **Verify frontend functionality**
6. **Run full integration tests**

### Success Criteria:
- [ ] All 18 routes respond correctly
- [ ] Frontend loads without errors
- [ ] Database operations function normally
- [ ] No import errors in any module
- [ ] All existing tests pass