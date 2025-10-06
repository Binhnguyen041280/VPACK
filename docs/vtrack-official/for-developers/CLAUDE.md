# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

V_Track is a comprehensive desktop video monitoring and processing application with integrated licensing and payment systems. The system is designed for end-users requiring automated video analysis with commercial licensing.

### System Architecture
- **Backend**: Flask-based Python API server (port 8080)
- **Frontend**: React application (port 3000) with Tailwind CSS
- **Database**: SQLite with WAL mode for concurrent access
- **Video Processing**: OpenCV, MediaPipe for hand detection, QR detection, ROI analysis
- **Cloud Integration**: Google Drive OAuth2 integration + Google Cloud Functions
- **License System**: RSA encryption with machine fingerprinting
- **Payment Integration**: PayOS gateway with webhook handling
- **Camera Support**: ONVIF-compatible IP cameras

### Core Functionality
- **Video Processing**: Multi-source video processing (local files, cloud storage, IP cameras)
- **Detection Systems**: Real-time hand detection and QR code recognition with ROI support
- **License Management**: Device activation, cloud verification, and local license storage
- **Payment Processing**: PayOS integration with automated license delivery
- **Background Service**: "Set it and forget it" operation with 90-day OAuth sessions
- **Event Logging**: Comprehensive event detection and logging system

## Development Commands

### Backend (Python Flask)
```bash
# Start backend server
cd backend
python3 app.py

# Install dependencies
pip install -r requirements.txt

# Database initialization
python3 database.py

# Run specific tests
python3 test_fixes.py
python3 add_test_data.py
```

### Frontend (React)
```bash
# Start development server
cd frontend
npm start

# Install dependencies
npm install

# Build for production
npm run build

# Run tests
npm test
```

### Full System Startup
```bash
# Use the startup script (updates database schema first)
./backend/start.sh
# This runs update_database.py then starts both backend and frontend concurrently
```

### License System Commands
```bash
# Test license validation
cd backend
python3 -c "from modules.license.license_manager import LicenseManager; print(LicenseManager().validate_current_license())"

# Generate machine fingerprint
python3 -c "from modules.license.machine_fingerprint import generate_machine_fingerprint; print(generate_machine_fingerprint())"

# Test payment integration
curl -X POST http://localhost:8080/api/payment/create \
  -H "Content-Type: application/json" \
  -d '{"customer_email":"test@example.com","package_type":"desktop_standard"}'
```

## Code Architecture

### Backend Structure
- `app.py` - Main Flask application with CORS, OAuth session management
- `database.py` - SQLite database initialization and schema updates
- `modules/` - Core business logic organized by domain:
  - `license/` - License validation, activation, and machine fingerprinting
  - `payments/` - PayOS integration and cloud function client
  - `sources/` - Video source management (local, cloud, camera)
  - `technician/` - Video processing (hand detection, QR, ROI)
  - `scheduler/` - Background batch processing and auto-sync
  - `config/` - System configuration and OAuth security
  - `db_utils/` - Thread-safe database operations with retry logic
- `blueprints/` - Flask route handlers for specific features
- `keys/` - RSA keypairs and encryption keys for license system

### Frontend Structure
- `src/App.js` - Main React application entry point
- `src/Dashboard.js` - Primary dashboard interface
- `src/components/` - Reusable UI components
- `src/hooks/` - Custom React hooks for business logic
- `src/VtrackConfig.js` - Configuration management interface

### Key Integration Points
- **License System**: RSA-encrypted license keys with cloud verification via Google Cloud Functions
- **Payment Flow**: PayOS webhook integration for automated license delivery
- **OAuth2 Flow**: Long-term background service authentication (90-day sessions)
- **Video Source Management**: Unified interface for local/cloud/camera sources
- **Database Concurrency**: WAL mode with read/write locks and retry logic for thread safety
- **Machine Fingerprinting**: Hardware-based device identification for license binding

## Important Configuration

### License & Security
- RSA keypairs auto-generated in `backend/keys/` if not present
- Fernet encryption keys for local license storage
- Machine fingerprinting combines CPU, MAC address, and system info
- Cloud Functions deployed in asia-southeast1 region
- License validation occurs on app startup and every 24 hours

### Payment Integration
- PayOS webhook endpoints for payment completion
- Automatic license generation and email delivery
- Transaction logging with status tracking
- Support for multiple package types (desktop_standard, desktop_premium)

### Database
- SQLite with WAL journal mode for concurrent access
- Automatic retry logic with exponential backoff for locked scenarios
- Connection pooling with 60-second timeout
- Foreign key constraints enabled
- Thread-safe operations using db_rwlock

### Session & OAuth
- OAuth sessions designed for background service (90-day duration)
- Aggressive token refresh to prevent expiry
- CORS configured for localhost development (ports 3000, 8080)
- Flask sessions stored in filesystem for persistence

### Video Processing
- Multiple detection engines: MediaPipe (hands), OpenCV (QR codes)
- ROI (Region of Interest) configuration for focused processing
- Frame sampling with trigger-based and continuous modes
- Event logging with start/end timestamps

## Development Notes

### Video Sources
The system supports three main video source types:
1. **Local**: Direct file system access, including mounted network drives
2. **Cloud**: Google Drive integration with OAuth2 and folder picker
3. **Camera**: ONVIF-compatible IP cameras (backend implemented, frontend pending)

### Background Service Philosophy
V_Track is designed as a "set it and forget it" monitoring system:
- Long authentication sessions (90 days)
- Aggressive auto-refresh to prevent expiry
- Silent operation without user popups
- Graceful degradation on authentication failures

### Database Schema
Key tables:
- `licenses` - License keys, activation status, expiration dates
- `license_activations` - Device activation records with machine fingerprints
- `payment_transactions` - PayOS payment records and status tracking
- `user_profiles` - Gmail-based user accounts and login tracking
- `email_logs` - License delivery email tracking
- `file_list` - Video files queued for processing
- `events` - Detected events with timestamps and confidence scores
- `video_sources` - Configured video source definitions
- `processing_config` - User configuration settings

### Testing
- Mock data generation available via add_test_data.py
- License system testing via direct module imports
- Payment flow testing with PayOS sandbox environment
- Frontend testing with React Testing Library (@testing-library/react)
- No formal backend test framework currently configured

### Logging
- Structured logging with context-aware loggers
- Log levels configurable per module
- TensorFlow/MediaPipe logs suppressed for cleaner output

## Development Environment Setup

1. Ensure Python 3.8+ and Node.js 16+ are installed
2. Install backend dependencies: `pip install -r backend/requirements.txt`
3. Install frontend dependencies: `cd frontend && npm install`
4. Initialize database: `python3 backend/database.py`
5. Start development: `./backend/start.sh` (handles database updates automatically)

The system will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080

### Environment Variables (Optional)
- `PAYOS_CLIENT_ID`, `PAYOS_API_KEY`, `PAYOS_CHECKSUM_KEY` - PayOS integration
- `GOOGLE_CLOUD_PROJECT` - Google Cloud Functions project ID
- `LICENSE_PRIVATE_KEY_PATH`, `LICENSE_PUBLIC_KEY_PATH` - Custom RSA key paths

## Critical Architecture Patterns

### License System Integration
```python
# License validation on app startup
from modules.license.license_manager import LicenseManager

def validate_app_license():
    license_manager = LicenseManager()
    validation_result = license_manager.validate_current_license()
    
    if not validation_result['valid']:
        # Trigger license activation UI
        return redirect('/license-activation')
```

### Payment-License Flow
```python
# Webhook handler pattern for PayOS completion
@payment_bp.route('/webhook/payos', methods=['POST'])
def handle_payment_webhook():
    # 1. Verify webhook signature
    # 2. Generate license key with RSA encryption  
    # 3. Store in licenses table
    # 4. Send email with license key
    # 5. Update transaction status
```

### Machine Fingerprinting Pattern
```python
# Hardware-based device identification
def generate_machine_fingerprint():
    # Combines: platform.machine(), MAC address, processor info
    # Creates SHA256 hash for unique device ID
    # Used for license-device binding
```

### Thread-Safe Database Operations
```python
# Required pattern for all database operations
from modules.scheduler.db_sync import db_rwlock
from modules.db_utils import get_db_connection

with db_rwlock.gen_wlock():
    conn = get_db_connection()  # Auto-retry on lock
    # Database operations here
    conn.commit()
    conn.close()
```

### Cloud Function Integration
```python
# Google Cloud Functions for license verification
def verify_license_with_cloud(license_key, email, fingerprint):
    cloud_function_url = "https://asia-southeast1-vtrack-license.cloudfunctions.net/verify-license"
    # POST request with license data
    # Returns validation result + license metadata
```

## Path Management & Import Guidelines

### CRITICAL: Always run Python from backend/ directory
```bash
# ✅ ĐÚNG - Luôn chạy từ backend/
cd /Users/annhu/vtrack_app/V_Track/backend
python3 app.py
python3 -c "from modules.license.license_manager import LicenseManager; print(LicenseManager())"

# ❌ SAI - Sẽ gây lỗi ModuleNotFoundError
cd /Users/annhu/vtrack_app/V_Track
python3 backend/app.py
```

### CRITICAL: Import Patterns
```python
# ✅ ĐÚNG - Absolute imports từ modules/
from modules.config.logging_config import get_logger
from modules.db_utils import get_db_connection
from modules.license.license_manager import LicenseManager
from modules.scheduler.db_sync import db_rwlock

# ✅ ĐÚNG - Local relative (cùng package)
from .config.scheduler_config import SchedulerConfig
from .db_sync import frame_sampler_event

# ❌ SAI - Relative imports phức tạp
from ..licensing.repositories.license_repository import get_license_repository
from ...payments.cloud_function_client import get_cloud_client

# ❌ SAI - sys.path manipulation
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
```

### CRITICAL: Common Error Fixes
```python
# "not a known attribute" - Import cụ thể class/function
# ❌ SAI:
import modules.license.license_manager
result = modules.license.license_manager.LicenseManager()  # AttributeError

# ✅ ĐÚNG:
from modules.license.license_manager import LicenseManager
result = LicenseManager()
```

### Project Root Path (for Claude reference)
```
PROJECT_ROOT: /Users/annhu/vtrack_app/V_Track/
BACKEND_ROOT: /Users/annhu/vtrack_app/V_Track/backend/
FRONTEND_ROOT: /Users/annhu/vtrack_app/V_Track/frontend/
```

## Important Notes for Development

### License System Dependencies
- RSA keypairs are auto-generated in `backend/keys/` on first run
- Fernet encryption keys for local license storage  
- Machine fingerprinting requires system access (MAC address, CPU info)
- Cloud Functions must be deployed for license verification

### Database Schema Updates
- `./backend/start.sh` automatically runs `update_database.py`
- Database migrations are handled in `database.py:update_database()`
- WAL mode enables concurrent access during video processing

### Payment Integration Requirements  
- PayOS webhook endpoint must be publicly accessible for production
- License keys are generated server-side with RSA encryption
- Email delivery requires SMTP configuration in Cloud Functions
