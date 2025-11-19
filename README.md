# ePACK - Intelligent Video Processing & Tracking System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.1.6-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-Commercial-red.svg)](LICENSE)

## 📋 Overview

ePACK is an advanced desktop application for automated video processing, event detection, and tracking code analysis. It processes video files from multiple sources (local storage, cloud storage) and automatically detects packing events using AI-powered computer vision techniques.

### Key Features

- **🎥 Multi-Source Video Processing**: Support for local storage and Google Drive cloud integration
- **🤖 AI-Powered Detection**: Automated hand detection and QR code recognition for packing event identification
- **📊 Intelligent Event Detection**: Smart tracking code detection with configurable ROI (Region of Interest)
- **⚡ Multi-Mode Processing**: First Run, Default (auto-scan), and Custom processing modes
- **🌐 Cloud Sync**: Automatic synchronization with Google Drive for seamless video access
- **💳 License Management**: Integrated payment system with PayOS and license activation
- **🔐 OAuth Security**: Secure Google authentication with encrypted credential storage
- **🌍 Multi-Timezone Support**: IANA timezone management with DST awareness

## 🏗️ Architecture

### Technology Stack

#### Frontend
- **Framework**: Next.js 15.1.6 with App Router
- **UI Library**: Chakra UI 2.8.2
- **Language**: TypeScript 4.9.5
- **State Management**: React Context API
- **Styling**: Emotion + Tailwind CSS
- **Animation**: Framer Motion

#### Backend
- **Framework**: Flask 3.0.0 (Python)
- **Database**: SQLite with WAL mode
- **Computer Vision**: MediaPipe, OpenCV, pyzbar
- **Cloud Integration**: PyDrive2 1.15.4
- **Authentication**: Google OAuth 2.0
- **Scheduling**: APScheduler for batch processing
- **License System**: Cryptography-based license validation

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                       │
│  ┌─────────────┬──────────────┬─────────────────────────┐  │
│  │ Dashboard   │ ROI Config   │ Trace Tracking          │  │
│  │ (Program)   │ (Step 4)     │ (Real-time Analysis)    │  │
│  └─────────────┴──────────────┴─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API (CORS enabled)
┌────────────────────────────▼────────────────────────────────┐
│                    Backend (Flask)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ API Blueprints                                       │  │
│  │ • program_bp: Processing control                     │  │
│  │ • roi_bp: ROI configuration                          │  │
│  │ • hand_detection_bp: AI detection                    │  │
│  │ • qr_detection_bp: QR code scanning                  │  │
│  │ • cloud_bp: Cloud sync                               │  │
│  │ • payment_bp: License management                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Core Modules                                         │  │
│  │ • scheduler: BatchScheduler, program_runner          │  │
│  │ • technician: event_detector, frame_sampler          │  │
│  │ • sources: pydrive_downloader, cloud_endpoints       │  │
│  │ • config: logging_config, config loader              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   SQLite Database (WAL)      │
              │ • events: Detected events    │
              │ • file_list: Video queue     │
              │ • packing_profiles: ROI data │
              │ • video_sources: Sources     │
              │ • sync_status: Cloud sync    │
              └──────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8 or higher
- **Node.js**: 18.x or higher
- **Operating System**: Windows, macOS, or Linux
- **Disk Space**: Minimum 5GB for application and video storage
- **RAM**: Minimum 8GB recommended

### Installation

#### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py

# Start backend server
python app.py
```

Backend will run on `http://localhost:8080`

#### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on `http://localhost:3000`

### First-Time Configuration

After installation, complete the 5-step Configuration Wizard:

1. **Open Application**: Navigate to `http://localhost:3000`
2. **Configuration Wizard**: Follow guided setup:
   - **Step 1**: Brand Name (company/organization)
   - **Step 2**: Location & Time (country, timezone, working days)
   - **Step 3**: Video Source (Local storage or Google Drive)
   - **Step 4**: ROI Configuration (packing area detection zones)
   - **Step 5**: Timing & Storage (packing times, frame rates)

📖 **Detailed Guide**: [Configuration Wizard](docs/vtrack-official/for-users/configuration-wizard.md)

## 📖 User Guide

### Processing Modes

#### 1. First Run Mode
Initial processing mode for new installations:
- Scans videos from the past N days (configurable)
- Creates baseline event database
- Automatically transitions to Default mode when complete
- **Usage**: Set number of days → Click "Run" → Wait for completion

#### 2. Default Mode (Auto-Scan)
Continuous processing mode:
- Automatically scans for new videos every 2 minutes
- Processes videos from all configured sources
- Runs 24/7 in the background
- **Usage**: Activated automatically after First Run

#### 3. Custom Mode
Process specific files on demand:
- Select any video file or directory
- One-time processing
- Returns to Default mode after completion
- **Usage**: Enter file path → Click "Run Custom"

### ROI Configuration

ROI (Region of Interest) defines where the system looks for packing events:

1. **Packing Area**: Where hand detection occurs
   - Drawn by AI using hand landmark detection
   - Automatically saved as `packing_area` in database
   - Format: `[x, y, width, height]`

2. **QR Trigger Area**: Where QR codes are scanned
   - Optional trigger zone for advanced detection
   - Saved as `qr_trigger_area`
   - Enables multi-stage event detection

**Configuration Process**:
```bash
# Endpoint: POST /run-select-roi
{
  "video_path": "/path/to/video.mp4",
  "camera_id": "Cam1",
  "step": "packing"  # or "trigger"
}

# Response: ROI coordinates saved to packing_profiles table
```

### Cloud Integration

#### Google Drive Setup

1. Navigate to "Step 2: Video Source" in configuration
2. Select "Google Drive" option
3. Authenticate with Google account
4. Select folder containing video files
5. Configure auto-sync interval (default: 15 minutes)

#### Auto-Sync Features

- **Recursive Folder Scanning**: Scans all subfolders
- **Incremental Downloads**: Only downloads new files
- **Camera Detection**: Auto-detects camera folders (e.g., Cam1, Cam2)
- **Status Tracking**: Real-time sync status in UI
- **Error Recovery**: Automatic retry with exponential backoff

## 🔌 API Reference

### Processing Control

```bash
# Start/Stop Processing Programs
POST /api/program
{
  "card": "First Run|Default|Custom",
  "action": "run|stop",
  "days": 7,  # For First Run
  "custom_path": "/path/to/video"  # For Custom
}

# Get Processing Status
GET /api/program

# Get Real-time Progress
GET /api/program-progress
```

### ROI Configuration

```bash
# Run ROI Selection
POST /run-select-roi
{
  "video_path": "/path/to/video.mp4",
  "camera_id": "Cam1",
  "step": "packing"
}

# Finalize ROI
POST /finalize-roi
{
  "videoPath": "/path/to/video.mp4",
  "cameraId": "Cam1",
  "rois": [{"type": "packing", "x": 100, "y": 200, "w": 300, "h": 400}]
}

# Get ROI Preview Images
GET /get-roi-frame?camera_id=Cam1&file=roi_packing.jpg
GET /get-final-roi-frame?camera_id=Cam1
```

### Cloud Sync

```bash
# Start Auto-Sync
POST /api/sync/start/{source_id}

# Force Sync Now
POST /api/sync/force/{source_id}

# Get Sync Status
GET /api/sync/status/{source_id}

# List Downloaded Files
GET /api/sync/files/{source_id}
```

### Event Query

```bash
# Get Events by Tracking Code
POST /query/get_events
{
  "tracking_code": "TRACK123",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31"
}

# Export Events to CSV
POST /export_csv
{
  "tracking_code": "TRACK123"
}
```

For complete API documentation, see [docs/api/endpoints.md](docs/api/endpoints.md)

## 📦 Database Schema

### Core Tables

- **events**: Detected packing events with tracking codes
- **file_list**: Video files processing queue
- **packing_profiles**: ROI configurations per camera
- **video_sources**: Local and cloud video sources
- **sync_status**: Cloud synchronization state
- **licenses**: License activation records
- **user_profiles**: Google OAuth user data

See [docs/architecture/overview.md](docs/architecture/overview.md) for complete schema.

## 🔒 Security

- **OAuth 2.0**: Google authentication with encrypted token storage
- **Session Management**: Secure Flask sessions with HTTPOnly cookies
- **License Validation**: RSA-based license key verification
- **Credential Encryption**: Fernet symmetric encryption for sensitive data
- **Audit Logging**: Complete authentication event tracking

## 🌐 Timezone Management

ePACK uses IANA timezone database for accurate timestamp handling:

- **System Timezone**: Configured during setup (Step 1)
- **UTC Storage**: All timestamps stored in UTC (milliseconds)
- **Display Conversion**: Auto-converts to user timezone for UI
- **DST Awareness**: Handles daylight saving time transitions
- **Multi-Camera Support**: Different timezones per camera

## 📊 Monitoring & Logs

### Log Locations

```bash
# Application Logs
/var/logs/app_latest.log          # General application log
/var/logs/event_processing_latest.log  # Event detection log

# Frame Processing Logs
/var/logs/frame_processing/{camera}/{video}_log.txt

# Sync Logs
Backend logs contain sync status with source_id prefix
```

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "service": "ePACK Desktop Backend",
  "version": "2.1.0",
  "modules": {
    "computer_vision": "enabled",
    "batch_processing": "enabled",
    "cloud_sync": "enabled",
    "payment_system": "enabled"
  }
}
```

## 🛠️ Configuration Files

- **backend/config.json**: ROI configurations per camera
- **backend/database/events.db**: SQLite database
- **backend/keys/**: OAuth and license keys
- **processing_config table**: Frame rate, intervals, paths

## 📄 Documentation

📚 **[Complete Documentation Hub](docs/vtrack-official/README.md)** - Start here for organized documentation

### 👤 For Users
- [Installation Guide](docs/vtrack-official/for-users/installation.md) - Complete setup instructions
- [Configuration Wizard](docs/vtrack-official/for-users/configuration-wizard.md) - 5-step first-time setup
- [Processing Modes](docs/vtrack-official/for-users/processing-modes.md) - First Run, Default, Custom modes
- [ROI Configuration](docs/vtrack-official/for-users/roi-configuration.md) - Camera detection regions
- [Trace Tracking](docs/vtrack-official/for-users/trace-tracking.md) - Event search and analysis
- [License & Payment](docs/vtrack-official/for-users/license-payment.md) - Subscription management
- [Cloud Sync](docs/vtrack-official/for-users/cloud-sync-advanced.md) - Google Drive integration

### 👨‍💻 For Developers
- [Development Guide](docs/vtrack-official/for-developers/CLAUDE.md) - Setup and coding standards
- [Architecture Overview](docs/vtrack-official/for-developers/architecture/overview.md) - System design and database
- [API Reference](docs/vtrack-official/for-developers/api/endpoints.md) - REST API documentation

## 🤝 Contributing

This is a commercial desktop application. For feature requests or bug reports, contact the development team.

## 📞 Support

- **Email**: support@epack.com
- **Documentation**: See `/docs` folder
- **Health Check**: `http://localhost:8080/health`

## 📝 License

Commercial License - All rights reserved.

## 🔄 Version History

- **v2.1.0** (Current): Enhanced cloud sync, license management, multi-timezone support
- **v2.0.0**: Added Google Drive integration, OAuth authentication
- **v1.0.0**: Initial release with local video processing

---

**Last Updated**: 2025-10-06
**Platform**: Desktop (Windows, macOS, Linux)
**Target Users**: Warehouse operations, logistics companies, e-commerce fulfillment centers
