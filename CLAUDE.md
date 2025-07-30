# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

V_Track is a comprehensive video monitoring and processing system with the following key components:

### System Architecture
- **Backend**: Flask-based Python API server (port 8080)
- **Frontend**: React application (port 3000) with Tailwind CSS
- **Database**: SQLite with WAL mode for concurrent access
- **Video Processing**: OpenCV, MediaPipe for hand detection, QR detection, ROI analysis
- **Cloud Integration**: Google Drive OAuth2 integration for cloud storage sync
- **Camera Support**: ONVIF-compatible IP cameras and NVR systems

### Core Functionality
- Multi-source video processing (local files, cloud storage, IP cameras)
- Real-time hand detection and QR code recognition
- Event detection and logging system
- Scheduled batch processing with auto-sync capabilities
- OAuth2-secured cloud storage integration
- Background service model designed for "set it and forget it" operation

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
# Use the startup script
./backend/start.sh
# This starts both backend and frontend concurrently
```

## Code Architecture

### Backend Structure
- `app.py` - Main Flask application with CORS, OAuth session management
- `modules/` - Core business logic organized by domain:
  - `config/` - System configuration and OAuth security
  - `sources/` - Video source management (local, cloud, camera)
  - `technician/` - Video processing (hand detection, QR, ROI)
  - `scheduler/` - Batch processing and auto-sync
  - `query/` - Database query operations
- `blueprints/` - Flask route handlers for specific features
- `database.py` - SQLite database initialization and connection management

### Frontend Structure
- `src/App.js` - Main React application entry point
- `src/Dashboard.js` - Primary dashboard interface
- `src/components/` - Reusable UI components
- `src/hooks/` - Custom React hooks for business logic
- `src/VtrackConfig.js` - Configuration management interface

### Key Integration Points
- **OAuth2 Flow**: Long-term background service authentication (90-day sessions)
- **Video Source Management**: Unified interface for local/cloud/camera sources
- **Real-time Processing**: WebSocket integration for live updates
- **Database Concurrency**: WAL mode with read/write locks for thread safety

## Important Configuration

### Session & Security
- OAuth sessions designed for background service (90-day duration)
- Encryption keys auto-generated if not provided in environment
- CORS configured for localhost development (ports 3000, 8080)
- Flask sessions stored in filesystem for persistence

### Database
- SQLite with WAL journal mode for concurrent access
- Automatic retry logic for locked database scenarios
- Connection pooling with 60-second timeout
- Foreign key constraints enabled

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
- `file_list` - Video files to be processed
- `events` - Detected events with timestamps
- `program_status` - System state tracking
- `processing_config` - User configuration settings
- `video_sources` - Configured video source definitions

### Testing
- Test files located in backend root (test_*.py)
- Mock data generation available via add_test_data.py
- No formal test framework currently configured

### Logging
- Structured logging with context-aware loggers
- Log levels configurable per module
- TensorFlow/MediaPipe logs suppressed for cleaner output

## Development Environment Setup

1. Ensure Python 3.8+ and Node.js 16+ are installed
2. Install backend dependencies: `pip install -r backend/requirements.txt`
3. Install frontend dependencies: `cd frontend && npm install`
4. Initialize database: `python3 backend/database.py`
5. Start development: `./backend/start.sh`

The system will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080

# V_track Desktop Application

## Project Overview

V_track là ứng dụng desktop video monitoring và processing cho người dùng phổ thông, được phát triển bằng phương pháp nocode-friendly. Ứng dụng cung cấp giải pháp monitoring video toàn diện với khả năng phát hiện chuyển động, hand detection, QR code recognition, và đồng bộ multi-source.

### Core Features
- **Multi-Source Video Processing**: Local files, Cloud storage (Google Drive), IP cameras (ONVIF)
- **Real-time Detection**: Hand detection (MediaPipe), QR code recognition (OpenCV), ROI analysis
- **Event Detection & Logging**: Automated event tracking với timestamps
- **Cloud Integration**: Google Drive OAuth2 sync với folder picker
- **Scheduled Processing**: Background batch processing với auto-sync
- **Camera Support**: ONVIF-compatible IP cameras và NVR systems
- **Desktop UI**: React interface thân thiện người dùng

### System Architecture
- **Backend**: Flask API server (port 8080) 
- **Frontend**: React SPA với Tailwind CSS (port 3000)
- **Database**: SQLite với WAL mode cho concurrent access
- **Video Processing**: OpenCV + MediaPipe
- **Authentication**: OAuth2 (Google APIs) với 90-day sessions
- **Background Service**: "Set it and forget it" operation model

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
# Use the startup script
./backend/start.sh
# This starts both backend and frontend concurrently
```

## Codebase Structure

```
V_Track/
├── backend/                    # Python Flask backend
│   ├── app.py                 # Main Flask application với CORS, OAuth
│   ├── database.py            # SQLite database init và connection management
│   ├── start.sh              # System startup script
│   ├── requirements.txt       # Python dependencies
│   ├── test_*.py             # Test files
│   ├── add_test_data.py      # Mock data generation
│   ├── database/              # SQLite database và schema
│   │   └── events.db         # Main database file (WAL mode)
│   ├── modules/               # Core business logic
│   │   ├── config/           # System configuration và OAuth security
│   │   ├── db_utils/         # Database utilities với thread-safe operations
│   │   ├── scheduler/        # Background tasks, batch processing, auto-sync
│   │   ├── sources/          # Video source management (local/cloud/camera)
│   │   ├── technician/       # Video processing (hand detection, QR, ROI)
│   │   ├── query/            # Database query operations
│   │   └── utils/            # Helper utilities
│   ├── blueprints/           # Flask route handlers cho specific features
│   └── resources/            # Static resources
│       ├── Inputvideo/       # Input video directory
│       └── output_clips/     # Processed output
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── App.js           # Main React application entry point
│   │   ├── Dashboard.js     # Primary dashboard interface
│   │   ├── VtrackConfig.js  # Configuration management interface
│   │   ├── components/      # Reusable UI components
│   │   ├── hooks/           # Custom React hooks cho business logic
│   │   └── Sidebar.js       # Main navigation
│   ├── package.json          # NPM dependencies
│   └── tailwind.config.js    # Tailwind CSS config
└── claude.mi                 # This file
```

### Key Modules

#### Backend Core Modules
- **`app.py`**: Main Flask application với CORS, OAuth session management
- **`modules/config/`**: System configuration, OAuth2 security, encryption keys
- **`modules/sources/`**: Unified video source management (local/cloud/camera)
- **`modules/technician/`**: Video processing engine (MediaPipe hands, OpenCV QR codes)
- **`modules/scheduler/`**: Background batch processing và auto-sync capabilities
- **`modules/query/`**: Database query operations với thread safety
- **`blueprints/`**: Flask route handlers organized by features

#### Frontend Components
- **`Dashboard.js`**: Primary dashboard interface với real-time updates
- **`VtrackConfig.js`**: Configuration management interface
- **`Sidebar.js`**: Navigation menu với 4 sections chính
- **`hooks/`**: Custom React hooks cho business logic
- **Styling**: Tailwind CSS với custom color scheme

### Database Schema
Key tables:
- **`file_list`**: Video files to be processed
- **`events`**: Detected events với timestamps  
- **`program_status`**: System state tracking
- **`processing_config`**: User configuration settings
- **`video_sources`**: Configured video source definitions

## Technical Context

### Backend Dependencies
```python
# Core Framework
flask>=2.0.0
flask-cors

# Video Processing
opencv-python>=4.5.0
mediapipe

# Database & Storage
sqlite3 (built-in)
pandas

# Google APIs & Auth
google-auth
google-auth-oauthlib
google-auth-httplib2
pydrive2

# Security & Encryption
cryptography
pyjwt

# Utilities
python-dotenv
pathlib
```

### Frontend Dependencies
```json
{
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "tailwindcss": "^3.0.0",
    "lucide-react": "latest"
  }
}
```

### Key Integration Points
- **OAuth2 Flow**: Long-term background service authentication (90-day sessions)
- **Video Source Management**: Unified interface cho local/cloud/camera sources
- **Real-time Processing**: WebSocket integration cho live updates
- **Database Concurrency**: WAL mode với read/write locks cho thread safety

### Video Source Types
1. **Local**: Direct file system access, including mounted network drives
2. **Cloud**: Google Drive integration với OAuth2 và folder picker
3. **Camera**: ONVIF-compatible IP cameras (backend implemented, frontend pending)

## Key Patterns & Conventions

### Database Access Pattern
```python
# Thread-safe database operations với WAL mode
from modules.scheduler.db_sync import db_rwlock
from modules.db_utils import get_db_connection

with db_rwlock.gen_wlock():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Database operations với automatic retry logic
    conn.commit()
    conn.close()
```

### Path Management Pattern
```python
from modules.path_utils import get_paths

paths = get_paths()
# paths["BASE_DIR"], paths["DB_PATH"], etc.
```

### Video Processing Pattern
```python
# OpenCV + MediaPipe integration
import cv2
import mediapipe as mp

# Hand detection với MediaPipe
mp_hands = mp.solutions.hands
# QR detection với OpenCV
# ROI coordinates cho focused processing
trigger_roi_coords_for_state_check = [(x1,y1), (x2,y2), ...]
```

### API Endpoint Pattern
```python
from flask import Blueprint, request, jsonify

bp = Blueprint('module_name', __name__)

@bp.route('/api/endpoint', methods=['POST'])
def endpoint_handler():
    try:
        # Logic here với proper error handling
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

### OAuth2 Session Pattern
```python
# Long-term background service authentication
from google.oauth2.credentials import Credentials
from modules.config.oauth_manager import OAuthManager

# 90-day sessions với aggressive auto-refresh
oauth_manager = OAuthManager()
credentials = oauth_manager.get_valid_credentials(source_id)
```

## Important Configuration

### Session & Security
- OAuth sessions designed cho background service (90-day duration)
- Encryption keys auto-generated nếu không có trong environment
- CORS configured cho localhost development (ports 3000, 8080)
- Flask sessions stored trong filesystem cho persistence

### Database Configuration
- SQLite với WAL journal mode cho concurrent access
- Automatic retry logic cho locked database scenarios
- Connection pooling với 60-second timeout
- Foreign key constraints enabled

### Video Processing Configuration
- Multiple detection engines: MediaPipe (hands), OpenCV (QR codes)
- ROI (Region of Interest) configuration cho focused processing
- Frame sampling với trigger-based và continuous modes
- Event logging với start/end timestamps

## Development Guidelines

### Code Style & Standards

#### Python Backend
- **Naming**: snake_case cho functions/variables
- **Imports**: Absolute imports từ modules/
- **Error Handling**: Always wrap database operations trong try-catch
- **Logging**: Structured logging với context-aware loggers
- **Security**: Không hardcode credentials, sử dụng environment variables

#### React Frontend  
- **Components**: Functional components với hooks
- **Styling**: Tailwind CSS classes, custom colors defined
- **Props**: Destructuring trong component parameters
- **State**: useState cho local state management

### File Organization Rules

#### Backend Files
- **API endpoints**: Organize theo features trong blueprints/
- **Database operations**: Luôn qua db_utils wrapper với thread safety
- **Configuration**: Centralize trong modules/config/
- **Processing logic**: Separate trong modules/technician/

#### Frontend Files
- **Components**: One component per file trong components/
- **Business Logic**: Extract vào custom hooks trong hooks/
- **Styling**: Inline Tailwind, no separate CSS files
- **Assets**: Store trong public/ directory

### Background Service Philosophy
V_Track được thiết kế như "set it and forget it" monitoring system:
- Long authentication sessions (90 days)
- Aggressive auto-refresh để prevent expiry
- Silent operation without user popups
- Graceful degradation on authentication failures

### Performance Considerations
- **Database**: SQLite với WAL mode cho concurrent access
- **Video Processing**: Frame sampling để optimize performance
- **Memory Management**: Proper cleanup cho OpenCV objects
- **Threading**: Use db_rwlock cho thread safety
- **Logging**: TensorFlow/MediaPipe logs suppressed cho cleaner output

### Security Best Practices
- **OAuth2**: Token refresh automation cho background service
- **File Paths**: Validate all user input paths
- **Database**: Parameterized queries, no string concatenation
- **API**: CORS properly configured cho development
- **Encryption**: Auto-generated keys với proper storage

### Testing Approach
- **Backend**: Test files located trong backend root (test_*.py)
- **Mock Data**: Generation available via add_test_data.py
- **Integration**: Test database operations với concurrent access
- **Frontend**: Component testing với React Testing Library
- **E2E**: Video processing workflow testing

## Development Environment Setup

### Prerequisites
- Python 3.8+ và Node.js 16+ installed
- Git repository cloned

### Setup Steps
1. Install backend dependencies: `pip install -r backend/requirements.txt`
2. Install frontend dependencies: `cd frontend && npm install`
3. Initialize database: `python3 backend/database.py`
4. Start development: `./backend/start.sh`

### System URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080

---

**Development Philosophy**: 
- **Research First**: Khi sử dụng thư viện có sẵn, LUÔN tìm kiếm và đọc tài liệu chính thức trên web trước để có cơ sở thực hiện chính xác
- **Library Priority**: Ưu tiên sử dụng thư viện có sẵn thay vì tự implement
- **Code Simplicity**: Maintain code đơn giản và readable  
- **User-Centric**: Focus vào user experience cho người dùng phổ thông
- **Documentation-Driven**: Base implementation trên official docs, không guess API usage

**Code Review Checklist**:
- [ ] Database operations thread-safe với WAL mode
- [ ] Error handling comprehensive với structured logging
- [ ] No hardcoded paths/credentials
- [ ] Consistent với established patterns
- [ ] Performance impact considered
- [ ] OAuth2 sessions properly managed
- [ ] Video processing optimized