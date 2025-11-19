# ePACK Features Catalog

**Generated**: August 15, 2025
**Project**: ePACK v2.1.0
**Status**: Production Ready

---

## 📊 Overview

ePACK is a comprehensive desktop video monitoring and processing application with integrated licensing and payment systems. The project includes **18 major feature areas** organized into **11 categories**.

### Quick Statistics
- ✅ **18 Total Features**
- 🟢 **16 High Confidence**
- 🟡 **2 Medium Confidence**
- 📁 **11 Feature Categories**

---

## 🎯 Core Processing Features

### 1. Video Processing Engine
**Status**: ✅ Production
**Confidence**: HIGH

AI-powered multi-source video processing with hand detection, QR code recognition, and ROI analysis.

**Key Files**:
- `backend/modules/technician/hand_detection.py`
- `backend/modules/technician/qr_detector.py`
- `backend/modules/technician/event_detector.py`
- `backend/modules/technician/frame_sampler_trigger.py`
- `backend/modules/technician/frame_sampler_no_trigger.py`

**API Routes**:
- `POST /select-qr-roi`
- `POST /run-qr-detector`
- `POST /api/hand-detection`
- `POST /api/roi`

**Features**:
- 🎯 Hand landmark detection using MediaPipe
- 📱 QR code scanning and decoding
- 🎬 Frame sampling with trigger support
- 🔍 Region of Interest (ROI) configuration

---

### 2. Region of Interest (ROI) Management
**Status**: ✅ Production
**Confidence**: HIGH

Visual ROI configuration for focused video processing areas.

**Key Files**:
- `backend/modules/technician/roi_preview.py`
- `frontend/src/components/config/ProcessingRegionForm.js`
- `backend/blueprints/roi_bp.py`

**API Routes**:
- `GET /get-roi-frame`
- `GET /get-final-roi-frame`

---

### 3. Event Detection and Logging
**Status**: ✅ Production
**Confidence**: HIGH

Comprehensive event detection and logging system with start/end timestamps.

**Key Files**:
- `backend/modules/technician/event_detector.py`
- `backend/modules/technician/trigger_processor.py`

---

## 🔐 Authentication & Security

### 4. User Authentication
**Status**: ✅ Production
**Confidence**: HIGH

Google OAuth2 integration with 90-day background service sessions.

**Key Files**:
- `backend/modules/sources/cloud_auth.py`
- `frontend/src/components/auth/GoogleSignupScreen.js`
- `frontend/src/hooks/useAuthState.js`

**API Routes**:
- `POST /register`
- `POST /auth`

**Features**:
- 🔐 Google OAuth 2.0 authentication
- 📝 User session management
- 🔄 90-day refresh cycles

---

## 💳 Licensing & Payments

### 5. License Management System
**Status**: ✅ Production
**Confidence**: HIGH

RSA-encrypted license system with machine fingerprinting and cloud verification.

**Key Files**:
- `backend/modules/license/license_manager.py`
- `backend/modules/license/license_checker.py`
- `backend/modules/license/machine_fingerprint.py`
- `backend/modules/licensing/license_models.py`

**API Routes**:
- `GET /api/license-status`

**Features**:
- 🔒 RSA-2048 encryption
- 👤 Machine fingerprinting
- ☁️ Cloud verification
- ✅ License validation

---

### 6. Payment Processing
**Status**: ✅ Production
**Confidence**: HIGH

PayOS gateway integration with automated license delivery and webhook handling.

**Key Files**:
- `backend/modules/payments/payment_routes.py`
- `backend/modules/payments/cloud_function_client.py`
- `backend/modules/payments/license_generator.py`
- `backend/modules/payments/email_sender.py`

**API Routes**:
- `POST /payment`
- `POST /api/payment/create`
- `GET /payment/redirect`

**Features**:
- 💰 PayOS payment gateway
- 🎁 Automated license generation
- 📧 Email notifications
- 🔗 Webhook handling

---

### 7. License Upgrade System
**Status**: ✅ Production
**Confidence**: HIGH

License upgrade interface with package selection and purchase flow.

**Key Files**:
- `frontend/src/components/license/UpgradePlan.js`
- `frontend/src/components/license/LicensePurchase.js`

---

## 📹 Video Management

### 8. Video Source Management
**Status**: ✅ Production
**Confidence**: HIGH

Unified interface for local files, Google Drive cloud storage, and ONVIF cameras.

**Key Files**:
- `backend/modules/sources/google_drive_client.py`
- `backend/modules/sources/cloud_manager.py`
- `backend/modules/sources/auto_sync_service.py`
- `backend/modules/sources/path_manager.py`

**API Routes**:
- `GET /api/config/sources`
- `POST /api/sync`

**Features**:
- 📂 Local file support
- ☁️ Google Drive integration
- 📹 ONVIF camera support
- 🔄 Auto-sync functionality

---

### 9. Video Cutting and Export
**Status**: ✅ Production
**Confidence**: HIGH

Video cutting and export functionality for detected events.

**Key Files**:
- `frontend/src/components/result/VideoCutter.js`
- `frontend/src/components/result/CutVideoSection.js`
- `backend/modules/technician/cutter/cutter_complete.py`
- `backend/blueprints/cutter_bp.py`

**API Routes**:
- `POST /api/cut-video`

**Features**:
- ✂️ Precise video clipping
- 📤 Export functionality
- ⏱️ Timestamp-based cutting

---

## ⚙️ Configuration & Administration

### 10. Configuration Management
**Status**: ✅ Production
**Confidence**: HIGH

System configuration including ROI setup, camera settings, and processing parameters.

**Key Files**:
- `frontend/src/VtrackConfig.js`
- `frontend/src/components/config/ConfigForm.js`
- `frontend/src/components/config/ProcessingRegionForm.js`
- `backend/modules/config/config_manager.py`

**API Routes**:
- `GET /api/config`
- `POST /settings`

**Features**:
- 🎛️ System settings
- 📷 Camera configuration
- 🎯 ROI setup wizard
- 💾 Configuration persistence

---

## 📊 Analytics & Search

### 11. Query and Search System
**Status**: ✅ Production
**Confidence**: HIGH

Event search and query system with time-based filtering and database operations.

**Key Files**:
- `frontend/src/QueryComponent.js`
- `frontend/src/components/query/TimeAndQuerySection.js`
- `backend/modules/query/query.py`

**API Routes**:
- `POST /api/query`

**Features**:
- 🔍 Advanced event search
- 📅 Date/time filtering
- 📋 Result export
- 🗄️ Database queries

---

## 🎨 User Interface

### 12. Main Dashboard
**Status**: ✅ Production
**Confidence**: HIGH

Primary user interface with sidebar navigation and main dashboard view.

**Key Files**:
- `frontend/src/Dashboard.js`
- `frontend/src/App.js`
- `frontend/src/Sidebar.js`

**Routes**:
- `/` - Main dashboard
- `/dashboard`

**Features**:
- 📊 Real-time status display
- 🗂️ Navigation sidebar
- 📱 Responsive design

---

## 🔧 Core Utilities & Infrastructure

### 13. Background Processing Scheduler
**Status**: ✅ Production
**Confidence**: HIGH

Background service for automated video processing and cloud synchronization.

**Key Files**:
- `backend/modules/scheduler/batch_scheduler.py`
- `backend/modules/scheduler/program.py`
- `backend/modules/scheduler/file_lister.py`
- `backend/modules/scheduler/system_monitor.py`

**Features**:
- ⏰ Automated scheduling
- 🔄 Batch processing
- 💾 Cloud sync
- 🖥️ System monitoring

---

### 14. Database Management
**Status**: ✅ Production
**Confidence**: HIGH

SQLite database with WAL mode, migrations, and thread-safe operations.

**Key Files**:
- `backend/database.py`
- `backend/modules/db_utils/db_utils.py`
- `backend/modules/db_utils/safe_connection.py`

**Features**:
- 🗄️ SQLite with WAL mode
- 📊 Schema management
- 🔒 Thread-safe operations
- 🔄 Database migrations

---

### 15. Timezone Management System
**Status**: ✅ Production
**Confidence**: MEDIUM

Enhanced timezone handling with UTC conversion and migration support.

**Key Files**:
- `backend/modules/utils/timezone_manager.py`
- `backend/database_timezone_migration.py`
- `backend/modules/utils/timezone_validator.py`

**Features**:
- 🌍 IANA timezone support
- 🕐 UTC conversion
- 📅 DST handling
- 🔄 Migration support

---

### 16. File List Management
**Status**: ✅ Production
**Confidence**: HIGH

File listing and management for video processing queue.

**Key Files**:
- `frontend/src/components/program/FileList.js`
- `frontend/src/components/program/ProgramTab.js`
- `backend/modules/scheduler/file_lister.py`

**Features**:
- 📋 File listing
- 🔄 Queue management
- 📊 Status tracking

---

## ☁️ Cloud Services

### 17. Google Cloud Integration
**Status**: ✅ Production
**Confidence**: HIGH

Google Drive integration with folder picker and cloud function services.

**Key Files**:
- `backend/modules/sources/google_drive_service.py`
- `frontend/src/components/config/GoogleDriveFolderTree.js`
- `frontend/src/components/config/GoogleDriveAuthButton.js`

**API Routes**:
- `GET /api/google-drive`

**Features**:
- ☁️ Google Drive sync
- 📂 Folder picker UI
- 🔐 OAuth authentication
- 🔄 Auto-sync service

---

## 📱 Specialized Features

### 18. License Upgrade System
**Status**: ✅ Production
**Confidence**: HIGH

License upgrade interface with package selection and purchase flow.

---

## 📁 Feature Categories Summary

| Category | Features | Status |
|----------|----------|--------|
| **Core Video Processing** | 3 features | ✅ Production |
| **License Management** | 2 features | ✅ Production |
| **E-commerce & Payments** | 1 feature | ✅ Production |
| **Authentication & Security** | 1 feature | ✅ Production |
| **Administration & Configuration** | 1 feature | ✅ Production |
| **Analytics & Reporting** | 1 feature | ✅ Production |
| **Content Management** | 2 features | ✅ Production |
| **Core Utilities & Infrastructure** | 4 features | ✅ Production |
| **Cloud Services** | 1 feature | ✅ Production |
| **User Interface** | 1 feature | ✅ Production |
| **Video Management** | 2 features | ✅ Production |

---

## 🔗 Related Documentation

- Backend modules: `/backend/modules/`
- Frontend components: `/frontend/src/components/`
- API blueprints: `/backend/blueprints/`
- Configuration files: `/backend/modules/config/`

---

## 📝 Notes

- All features are production-ready and tested
- The system uses SQLite with WAL mode for optimal performance
- Google OAuth 2.0 is the primary authentication mechanism
- License system uses RSA-2048 encryption
- PayOS handles all payment processing

**Last Updated**: August 15, 2025
