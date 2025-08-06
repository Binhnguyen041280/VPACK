# V_Track Technology Stack

## Backend Stack
- **Framework**: Flask 3.0.0 (Python web framework)
- **Database**: SQLite with WAL (Write-Ahead Logging) mode for concurrent access
- **Video Processing**: 
  - OpenCV (computer vision)
  - MediaPipe (hand detection)
  - PyZbar (QR code detection)
- **Cloud Integration**:
  - Google APIs (google-auth, google-auth-oauthlib, google-api-python-client)
  - PyDrive2 for Google Drive integration
  - OAuth2 for authentication
- **Camera Support**:
  - ONVIF-Zeep for IP camera integration
  - WSDiscovery for camera discovery
  - Netifaces for network interface management
- **Background Processing**:
  - APScheduler for task scheduling
  - Flask-Sockets with Gevent for WebSocket support
- **Security**: Cryptography library for encryption
- **Utilities**: 
  - Requests for HTTP clients
  - Python-dotenv for environment management
  - Tenacity for retry logic
  - PSUtil for system monitoring

## Frontend Stack
- **Framework**: React 19.0.0
- **Styling**: Tailwind CSS 3.3.0
- **Icons**: Lucide React (icon library)
- **HTTP Client**: Axios for API communication
- **UI Components**: React DatePicker
- **Testing**: React Testing Library, Jest
- **WebSocket**: WS library for real-time communication
- **Fonts**: Fontsource Montserrat

## Development Tools
- **Build Tools**: React Scripts, PostCSS, Autoprefixer
- **Code Quality**: ESLint, Depcheck, Knip
- **Development Server**: React dev server with proxy to backend

## Database Schema
- **SQLite**: Single file database with WAL mode
- **Key Tables**:
  - `file_list`: Video files to be processed
  - `events`: Detected events with timestamps
  - `program_status`: System state tracking
  - `processing_config`: User configuration settings
  - `video_sources`: Configured video source definitions

## Deployment Architecture
- **Development**: Dual server setup (React dev server + Flask)
- **Production**: Flask serves both API and static React build
- **Ports**: Frontend (3000), Backend (8080)
- **Startup**: Automated via start.sh script