# V_Track - Tech Stack & Architecture

## Frontend Stack
- **Framework**: React 19.0.0
- **Styling**: Tailwind CSS 3.3.0 + PostCSS + Autoprefixer
- **Icons**: Lucide React 0.483.0
- **HTTP Client**: Axios 1.8.4
- **Real-time**: WebSocket (ws 8.14.2)
- **UI Components**: React DatePicker
- **Testing**: Jest + React Testing Library

## Backend Stack
- **Framework**: Flask (Python)
- **WebSocket**: Flask-Sockets + Gevent
- **Computer Vision**: 
  - OpenCV (image/video processing)
  - MediaPipe (advanced CV)
  - pyzbar (QR/barcode detection)
- **Camera Integration**: 
  - onvif-zeep 0.2.12 (ONVIF cameras)
  - WSDiscovery 2.0.0 (camera discovery)
- **Scheduler**: APScheduler (background tasks)
- **Network**: netifaces 0.11.0

## Database
- SQLite (events.db)
- Database utils và sync modules

## Development Ports
- Frontend: http://localhost:3000
- Backend: http://127.0.0.1:8080 (proxy từ frontend)