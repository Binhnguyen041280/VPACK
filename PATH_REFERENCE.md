# V_Track Project Path Reference Guide

## Cấu trúc đường dẫn chuẩn

### Project Root
```
/Users/annhu/vtrack_app/V_Track/
```

### Backend Structure (Python)
```
backend/
├── app.py                          # Main Flask app
├── modules/                        # Core business logic
│   ├── __init__.py
│   ├── config/                     # Configuration
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── logging_config.py
│   ├── db_utils/                   # Database utilities
│   │   ├── __init__.py
│   │   └── db_utils.py
│   ├── license/                    # License management
│   │   ├── __init__.py
│   │   ├── license_checker.py
│   │   ├── license_manager.py
│   │   └── machine_fingerprint.py
│   ├── licensing/                  # New licensing system
│   │   ├── __init__.py
│   │   ├── license_models.py
│   │   ├── repositories/
│   │   └── services/
│   ├── payments/                   # Payment processing
│   │   ├── __init__.py
│   │   ├── cloud_function_client.py
│   │   └── payment_routes.py
│   ├── scheduler/                  # Task scheduling
│   │   ├── __init__.py
│   │   ├── batch_scheduler.py
│   │   ├── db_sync.py
│   │   └── config/
│   ├── sources/                    # Video sources
│   │   ├── __init__.py
│   │   ├── google_drive_client.py
│   │   └── cloud_manager.py
│   └── technician/                 # Video processing
│       ├── __init__.py
│       ├── hand_detection.py
│       └── qr_detector.py
└── blueprints/                     # Flask blueprints
    ├── __init__.py
    └── *.py
```

### Frontend Structure (React)
```
frontend/
├── src/
│   ├── App.js
│   ├── Dashboard.js
│   ├── components/
│   │   ├── auth/
│   │   ├── config/
│   │   ├── license/
│   │   └── ui/
│   └── hooks/
└── public/
```

## Import Patterns - KHÔNG LÀM

### ❌ TRÁNH - Relative imports phức tạp
```python
# Không dùng
from ..licensing.repositories.license_repository import get_license_repository
from ...payments.cloud_function_client import get_cloud_client
```

### ❌ TRÁNH - sys.path manipulation
```python
# Không dùng
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
```

### ❌ TRÁNH - Dynamic imports trong try/except
```python
# Không dùng
try:
    from ..licensing.repositories.license_repository import get_license_repository
except ImportError:
    # fallback logic
```

## Import Patterns - NÊN LÀM

### ✅ DÙNG - Absolute imports từ modules/
```python
# Chạy từ backend/ directory
from modules.config.logging_config import get_logger
from modules.db_utils import get_db_connection
from modules.license.license_manager import LicenseManager
from modules.payments.cloud_function_client import get_cloud_client
from modules.scheduler.db_sync import db_rwlock
```

### ✅ DÙNG - Local relative imports (cùng package)
```python
# Trong cùng thư mục hoặc sub-package
from .config.scheduler_config import SchedulerConfig
from .db_sync import db_rwlock, frame_sampler_event
```

## Các lệnh chạy đúng cách

### Backend Development
```bash
# Luôn chạy từ backend/ directory
cd /Users/annhu/vtrack_app/V_Track/backend
python3 app.py
python3 database.py
python3 add_test_data.py
```

### Frontend Development  
```bash
# Chạy từ frontend/ directory
cd /Users/annhu/vtrack_app/V_Track/frontend
npm start
npm test
```

### Testing
```bash
# Backend tests - từ backend/
cd /Users/annhu/vtrack_app/V_Track/backend
python3 -m modules.license.license_checker
python3 -c "from modules.license.license_manager import LicenseManager; print(LicenseManager().validate_current_license())"
```

## Environment Setup

### Python Path (Backend)
Luôn chạy từ `backend/` directory để đảm bảo:
- `modules/` package được Python nhận diện
- Relative imports hoạt động đúng
- Database paths đúng (`database/events.db`)

### Working Directory
```bash
# Đúng
cd /Users/annhu/vtrack_app/V_Track/backend && python3 app.py

# Sai - sẽ gây lỗi import
cd /Users/annhu/vtrack_app/V_Track && python3 backend/app.py
```

## Troubleshooting Common Errors

### "No module named 'modules'"
```bash
# Nguyên nhân: Chạy từ sai directory
# Giải pháp: 
cd /Users/annhu/vtrack_app/V_Track/backend
```

### "not a known attribute" 
```python
# Nguyên nhân: Import module thay vì class/function cụ thể
# Sai:
import modules.license.license_manager
result = modules.license.license_manager.LicenseManager()  # AttributeError

# Đúng:
from modules.license.license_manager import LicenseManager
result = LicenseManager()
```

### ModuleNotFoundError với relative imports
```python
# Nguyên nhân: Relative import từ script được chạy trực tiếp
# Sai:
from ..config.logging_config import get_logger  # ValueError: attempted relative import beyond top-level package

# Đúng:
from modules.config.logging_config import get_logger
```

## Quick Commands Reference

### Start Development
```bash
# Full system
cd /Users/annhu/vtrack_app/V_Track/backend && ./start.sh

# Backend only
cd /Users/annhu/vtrack_app/V_Track/backend && python3 app.py

# Frontend only  
cd /Users/annhu/vtrack_app/V_Track/frontend && npm start
```

### Database Operations
```bash
cd /Users/annhu/vtrack_app/V_Track/backend
python3 database.py                    # Initialize/update schema
python3 add_test_data.py              # Add test data
```

### License Testing
```bash
cd /Users/annhu/vtrack_app/V_Track/backend
python3 -c "from modules.license.machine_fingerprint import generate_machine_fingerprint; print(generate_machine_fingerprint())"
```

---

**Quy tắc vàng**: Luôn chạy Python scripts từ `backend/` directory và dùng absolute imports với prefix `modules.*`