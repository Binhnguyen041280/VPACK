# V_Track Project Overview

## Project Purpose
V_Track is a comprehensive video monitoring and processing desktop application designed for general users. It's a "set it and forget it" background monitoring system that processes video from multiple sources using AI-powered detection capabilities.

## Core Functionality
- **Multi-Source Video Processing**: Local files, Google Drive cloud storage, ONVIF IP cameras
- **AI-Powered Detection**: Hand detection (MediaPipe), QR code recognition (OpenCV), ROI analysis
- **Event Detection & Logging**: Automated event tracking with timestamps
- **Cloud Integration**: Google Drive OAuth2 sync with 90-day sessions
- **Scheduled Processing**: Background batch processing with auto-sync capabilities
- **Camera Support**: ONVIF-compatible IP cameras and NVR systems
- **Desktop UI**: React-based user-friendly interface

## System Architecture
- **Backend**: Flask API server (Python, port 8080)
- **Frontend**: React SPA with Tailwind CSS (port 3000)
- **Database**: SQLite with WAL mode for concurrent access
- **Video Processing**: OpenCV + MediaPipe
- **Authentication**: OAuth2 (Google APIs) with long-term sessions
- **Background Service**: Designed for unattended operation

## Target Users
- General users (non-technical)
- Small businesses needing video monitoring
- Anyone requiring automated video analysis
- Users who want "set and forget" monitoring solutions

## Development Philosophy
- **No-code friendly**: Focus on simplicity over feature richness
- **Reliability first**: Emphasize stability and error handling
- **Library-based**: Use existing libraries rather than custom implementations
- **User-centric**: Prioritize user experience for non-technical users
- **Research-driven**: Always check official documentation before implementation