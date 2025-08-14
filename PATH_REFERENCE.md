# V_Track Project Path Reference Guide

## Cấu trúc đường dẫn chuẩn

### Project Root
```
/Users/annhu/vtrack_app/V_Track/
```

### Backend Structure (Python)
```
backend/
├── app.py                          # Main Flask application entry point
├── database.py                     # SQLite database initialization
├── start.sh                        # Startup script for backend + frontend
├── requirements.txt                # Python dependencies
├── config.json                     # Application configuration
├── add_test_data.py               # Test data generation
├── modules/                        # Core business logic
│   ├── __init__.py
│   ├── config/                     # Configuration management
│   │   ├── __init__.py
│   │   ├── config.py              # Main configuration
│   │   ├── config_manager.py      # Configuration manager
│   │   ├── logging_config.py      # Logging setup
│   │   ├── security_config.py     # Security settings
│   │   ├── utils.py               # Config utilities
│   │   ├── config.json            # ROI camera settings
│   │   └── routes/                # Configuration API routes
│   │       ├── camera_routes.py
│   │       ├── config_routes.py
│   │       └── source_routes.py
│   ├── db_utils/                   # Database utilities
│   │   ├── __init__.py
│   │   ├── db_utils.py            # Thread-safe DB operations
│   │   └── TG.py                  # Additional DB utilities
│   ├── license/                    # Original license system
│   │   ├── __init__.py
│   │   ├── license_checker.py     # License validation
│   │   ├── license_config.py      # License configuration
│   │   ├── license_manager.py     # Main license management
│   │   ├── license_ui.py          # License UI components
│   │   └── machine_fingerprint.py # Hardware fingerprinting
│   ├── licensing/                  # Enhanced licensing system
│   │   ├── __init__.py
│   │   ├── license_models.py      # Database models
│   │   ├── repositories/          # Repository pattern
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py
│   │   │   └── license_repository.py
│   │   └── services/              # Business logic layer
│   │       └── license_service.py
│   ├── payments/                   # Payment processing
│   │   ├── __init__.py
│   │   ├── cloud_function_client.py # Google Cloud Functions
│   │   ├── email_sender.py        # Email delivery
│   │   ├── license_generator.py   # License key generation
│   │   ├── payment_routes.py      # Payment API endpoints
│   │   └── zalopay_handler.py     # ZaloPay integration (legacy)
│   ├── scheduler/                  # Task scheduling system
│   │   ├── __init__.py
│   │   ├── batch_scheduler.py     # Batch processing
│   │   ├── db_sync.py            # Database synchronization
│   │   ├── file_lister.py        # File listing service
│   │   ├── program.py            # Main program logic
│   │   ├── program_runner.py     # Program execution
│   │   ├── system_monitor.py     # System monitoring
│   │   └── config/               # Scheduler configuration
│   │       ├── __init__.py
│   │       └── scheduler_config.py
│   ├── sources/                    # Video sources management
│   │   ├── __init__.py
│   │   ├── auto_sync_service.py   # Automatic synchronization
│   │   ├── cloud_auth.py          # Cloud authentication
│   │   ├── cloud_endpoints.py     # Cloud API endpoints
│   │   ├── cloud_lazy_folder_routes.py # Lazy folder loading
│   │   ├── cloud_manager.py       # Cloud storage management
│   │   ├── google_drive_client.py # Google Drive client
│   │   ├── google_drive_service.py # Google Drive service
│   │   ├── nvr_client.py          # Network Video Recorder
│   │   ├── nvr_downloader.py      # NVR download functionality
│   │   ├── onvif_client.py        # ONVIF camera integration
│   │   ├── path_manager.py        # Path management utilities
│   │   ├── pydrive_core.py        # PyDrive core functionality
│   │   ├── pydrive_downloader.py  # PyDrive downloads
│   │   ├── sync_endpoints.py      # Sync API endpoints
│   │   ├── credentials/           # OAuth credentials
│   │   │   ├── google_drive_credentials.json
│   │   │   └── google_drive_credentials_web.json
│   │   └── tokens/                # Active OAuth tokens
│   │       └── google_drive_2146a5516664cebd.json
│   ├── technician/                 # Video processing pipeline
│   │   ├── __init__.py
│   │   ├── hand_detection.py      # MediaPipe hand detection
│   │   ├── qr_detector.py         # QR code detection
│   │   ├── event_detector.py      # Event detection logic
│   │   ├── frame_sampler_no_trigger.py # Continuous sampling
│   │   ├── frame_sampler_trigger.py # Triggered sampling
│   │   ├── roi_preview.py         # ROI preview functionality
│   │   ├── trigger_processor.py   # Trigger processing
│   │   ├── IdleMonitor.py         # Idle state monitoring
│   │   └── cutter/                # Video cutting module
│   │       ├── cutter_complete.py
│   │       ├── cutter_incomplete.py
│   │       └── cutter_utils.py
│   ├── system/                     # System monitoring
│   │   ├── AuditLogger.py         # Audit logging
│   │   ├── LicenseGuard.py        # License protection
│   │   ├── SystemCalendar.py      # Calendar functionality
│   │   └── SystemMonitor.py       # System monitoring
│   ├── account/                    # User account management
│   │   ├── __init__.py
│   │   └── account.py
│   ├── query/                      # Query processing
│   │   ├── __init__.py
│   │   └── query.py
│   ├── utils/                      # Utilities
│   │   ├── __init__.py
│   │   ├── file_parser.py
│   │   └── path_validator.py
│   └── webhooks/                   # Webhook handlers
│       ├── __init__.py
│       └── zalopay_webhook.py
├── blueprints/                     # Flask blueprints (API routes)
│   ├── __init__.py
│   ├── cutter_bp.py               # Video cutting API
│   ├── hand_detection_bp.py       # Hand detection API
│   ├── qr_detection_bp.py         # QR detection API
│   └── roi_bp.py                  # ROI management API
├── keys/                           # Security keys
│   ├── license_fernet_key.key     # Fernet encryption
│   ├── license_private_key.pem    # RSA private key
│   └── license_public_key.pem     # RSA public key
├── database/                       # SQLite database files
│   ├── events.db                  # Main database
│   ├── events.db-shm             # Shared memory
│   └── events.db-wal             # Write-ahead log
├── models/                         # AI/ML models
│   └── wechat_qr/                 # WeChat QR detection models
│       ├── detect.caffemodel
│       ├── detect.prototxt
│       ├── sr.caffemodel
│       └── sr.prototxt
├── templates/                      # HTML templates
│   ├── email/
│   │   └── license_delivery.html
│   └── payment_redirect.html
├── wsdl/                          # ONVIF WSDL files
│   ├── devicemgmt.wsdl
│   ├── media.wsdl
│   └── ver10/
└── tests/                         # Test suites
    ├── __init__.py
    ├── backend/
    └── config/
```

### Frontend Structure (React)
```
frontend/
├── package.json                    # Node.js dependencies and scripts
├── tailwind.config.js             # Tailwind CSS configuration
├── postcss.config.js              # PostCSS configuration
├── src/
│   ├── App.js                     # Main React application
│   ├── Dashboard.js               # Primary dashboard interface
│   ├── VtrackConfig.js            # Configuration management interface
│   ├── Account.js                 # Account management
│   ├── QueryComponent.js          # Query interface
│   ├── Sidebar.js                 # Navigation sidebar
│   ├── Title.js                   # Title component
│   ├── api.js                     # API communication layer
│   ├── index.js                   # React app entry point
│   ├── App.css                    # Application styles
│   ├── index.css                  # Global styles
│   ├── components/
│   │   ├── auth/                  # Authentication components
│   │   │   └── GoogleSignupScreen.js
│   │   ├── config/                # Configuration components
│   │   │   ├── AddSourceModal.js
│   │   │   ├── CameraDialog.js
│   │   │   ├── CloudConfigurationForm.js
│   │   │   ├── CloudSyncSettings.js
│   │   │   ├── ConfigForm.js
│   │   │   ├── GeneralInfoForm.js
│   │   │   ├── GoogleDriveAuthButton.js
│   │   │   ├── GoogleDriveFolderSelector.js
│   │   │   ├── GoogleDriveFolderTree.js
│   │   │   ├── InstructionsPanel.js
│   │   │   ├── ProcessingRegionForm.js
│   │   │   └── SourceCard.js
│   │   ├── license/               # License management components
│   │   │   ├── LicensePurchase.js
│   │   │   └── UpgradePlan.js
│   │   ├── program/               # Program management components
│   │   │   ├── FileList.js
│   │   │   └── ProgramTab.js
│   │   ├── query/                 # Query interface components
│   │   │   ├── ColumnSelectorModal.js
│   │   │   ├── FileInputSection.js
│   │   │   ├── TextInputSection.js
│   │   │   └── TimeAndQuerySection.js
│   │   ├── result/                # Results and video cutting
│   │   │   ├── CutVideoSection.js
│   │   │   ├── ResultList.js
│   │   │   └── VideoCutter.js
│   │   └── ui/                    # Reusable UI components
│   │       ├── Button.js
│   │       ├── Card.js
│   │       └── SearchModeSelector.js
│   └── hooks/                     # Custom React hooks
│       ├── useAuthState.js        # Authentication state management
│       ├── useProgramLogic.js     # Program logic hooks
│       └── useVtrackConfig.js     # Configuration state management
└── public/                        # Static assets
    ├── index.html                 # Main HTML template
    ├── favicon.ico
    ├── logo192.png
    ├── logo512.png
    ├── manifest.json
    └── robots.txt
```

### Additional Infrastructure Directories
```
# Project Root Level Directories
├── cloud_sync/                    # Synchronized cloud storage
│   └── google_drive_cloud_storage/
│       ├── Cloud_Cam1/
│       ├── Cloud_Cam2/
│       └── Cloud_Cam3/
├── resources/                      # Input data and assets
│   ├── Inputvideo/                # Sample video files by camera
│   │   ├── Cam1D/
│   │   ├── Cam2N/
│   │   ├── CamLocal/
│   │   └── Hik_recorde/
│   ├── CSV\ folder/               # Event data and logs
│   └── output_clips/
├── output_clips/                   # Generated clips and analysis
│   ├── CameraROI/                 # ROI configuration images
│   └── LOG/                       # Application logs and frame data
├── flask_session/                  # Flask session storage
├── service/                        # Development and testing tools
│   ├── onvif-camera-mocking/      # ONVIF camera simulation
│   ├── happytime-onvif-server/    # ONVIF server for testing
│   └── Linh_tinh/                 # Development utilities
├── docs/                          # Project documentation
│   ├── backup\ code/              # Version backups
│   └── Noidung\ tien\ do/         # Progress documentation
├── scripts/                       # Setup and utility scripts
└── environment/                   # Environment configuration
```

### Key Configuration Files (Project Root)
```
├── CLAUDE.md                      # Project instructions for Claude Code
├── PATH_REFERENCE.md              # This file - path reference guide
├── DATABASE_REALITY.md            # Database schema documentation
├── DEPLOYMENT_CHECKLIST.md        # Deployment guidelines
├── REFACTORING_SUCCESS_REPORT.md  # Refactoring documentation
├── pyrightconfig.json             # Python type checking config
└── emergency_rollback.sh          # Emergency rollback script
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