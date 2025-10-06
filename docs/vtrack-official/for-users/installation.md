# V_Track Installation Guide

This comprehensive guide will walk you through installing and setting up V_Track on your system.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Backend Installation](#backend-installation)
4. [Frontend Installation](#frontend-installation)
5. [Database Initialization](#database-initialization)
6. [First-Time Configuration](#first-time-configuration)
7. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **Operating System**:
  - Windows 10/11 (64-bit)
  - macOS 10.15 (Catalina) or newer
  - Ubuntu 20.04 LTS or newer

- **Hardware**:
  - CPU: Intel Core i5 or equivalent (4 cores)
  - RAM: 8 GB
  - Storage: 10 GB free space (SSD recommended)
  - Network: Stable internet connection for cloud sync

- **Software**:
  - Python 3.8 or higher
  - Node.js 18.x or higher
  - Git (for cloning repository)
  - SQLite 3.x (included in Python)

### Recommended Requirements

- **Hardware**:
  - CPU: Intel Core i7 or equivalent (8 cores)
  - RAM: 16 GB
  - Storage: 50 GB free space (NVMe SSD)
  - GPU: Optional (for faster video processing)

## Pre-Installation Checklist

Before installing V_Track, ensure you have:

- [ ] Python 3.8+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] npm installed (`npm --version`)
- [ ] Git installed (`git --version`)
- [ ] Administrator/sudo privileges (for installing packages)
- [ ] Google account (for OAuth authentication)
- [ ] Google Drive access (if using cloud storage)

### Installing Prerequisites

#### Windows

```powershell
# Install Python from python.org or via Chocolatey
choco install python --version=3.11.0

# Install Node.js via Chocolatey
choco install nodejs --version=18.16.0

# Verify installations
python --version
node --version
npm --version
```

#### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install Node.js
brew install node@18

# Verify installations
python3 --version
node --version
npm --version
```

#### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python
sudo apt install python3.11 python3.11-venv python3-pip

# Install Node.js via NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installations
python3 --version
node --version
npm --version
```

## Backend Installation

### Step 1: Clone Repository (or Extract Archive)

```bash
# If using Git
git clone https://github.com/your-org/V_Track.git
cd V_Track

# If using downloaded archive
unzip V_Track.zip
cd V_Track
```

### Step 2: Navigate to Backend Directory

```bash
cd backend
```

### Step 3: Create Python Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal.

### Step 4: Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed Flask-3.0.0 mediapipe-0.10.x opencv-python-4.8.x ...
```

### Step 5: Verify Backend Installation

```bash
python -c "import flask, cv2, mediapipe; print('Backend dependencies OK')"
```

**Expected output:**
```
Backend dependencies OK
```

### Step 6: Configure Environment Variables

Create `.env` file in `backend/` directory:

```bash
# Create .env file
touch .env  # macOS/Linux
# or
type nul > .env  # Windows
```

Add the following content to `.env`:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-this
FLASK_ENV=production
FLASK_DEBUG=False

# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Cloud Functions (if using payment system)
CLOUD_PAYMENT_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/create-payment
CLOUD_WEBHOOK_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler
CLOUD_LICENSE_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/license-service

# Database Path (auto-generated)
DB_PATH=backend/database/events.db
```

**Important**: Replace placeholder values with actual credentials.

## Frontend Installation

### Step 1: Navigate to Frontend Directory

```bash
# From project root
cd frontend
```

### Step 2: Install Node Dependencies

```bash
npm install
```

**Expected output:**
```
added 1234 packages in 30s
```

### Step 3: Configure Frontend Environment

Create `.env.local` file in `frontend/` directory:

```bash
# Create .env.local file
touch .env.local  # macOS/Linux
# or
type nul > .env.local  # Windows
```

Add the following content:

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8080

# Frontend URL
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Step 4: Verify Frontend Installation

```bash
npm run build
```

**Expected output:**
```
✓ Compiled successfully
✓ Collecting page data
✓ Generating static pages
```

## Database Initialization

### Step 1: Initialize SQLite Database

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment (if not already active)
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

# Run database initialization
python database.py
```

**Expected output:**
```
🎉 Database updated successfully at /path/to/V_Track/backend/database/events.db
✅ All 23 tables created successfully
✅ Platform management system implemented
✅ Enhanced timezone management system implemented
✅ All indexes created for optimal performance
✅ All views created for efficient queries
✅ All triggers created for timestamp management
```

### Step 2: Verify Database Creation

```bash
# Check database file exists
ls -lh backend/database/events.db

# List all tables
sqlite3 backend/database/events.db ".tables"
```

**Expected tables:**
```
active_cameras            frame_settings            processing_config
auth_audit                general_info              program_status
camera_configs            last_downloaded_file      sync_dashboard
camera_configurations     license_activations       sync_status
camera_sync_status        licenses                  timezone_metadata
downloaded_files          packing_profiles          user_profiles
email_logs                payment_transactions      user_sessions
events                    platform_column_mappings  video_sources
file_list                 processed_logs
```

### Step 3: Verify Default Configuration

```bash
# Check default configuration
sqlite3 backend/database/events.db "SELECT * FROM processing_config;"
```

**Expected output:**
```
1|/Users/username/Movies/VTrack/Input|/Users/username/Movies/VTrack/Output|30|10|120|30|5|2|default|[]|/path/to/events.db|0|0.1|1.0|0|{}
```

## First-Time Configuration

### Step 1: Start Backend Server

```bash
# In backend directory with venv activated
python app.py
```

**Expected output:**
```
🚀 V_Track Desktop App Starting...
📡 Server: http://0.0.0.0:8080
🔧 Core Features:
   ✅ Computer Vision Processing
   ✅ Video File Batch Processing
   ✅ Cloud Storage Sync
   ✅ Cloud Payment Processing
   ✅ License Management System
```

**Keep this terminal open.**

### Step 2: Start Frontend Server

Open a **new terminal**:

```bash
# Navigate to frontend directory
cd frontend

# Start development server
npm run dev
```

**Expected output:**
```
▲ Next.js 15.1.6
- Local:        http://localhost:3000
- Ready in 2.5s
```

### Step 3: Access Application

1. Open browser and navigate to `http://localhost:3000`
2. You should see the V_Track login/dashboard page

### Step 4: Google Authentication Setup

#### First-Time Login

1. Click "Sign in with Google" button
2. Select your Google account
3. Grant permissions:
   - View your email address
   - View your basic profile info
   - (Optional) Access Google Drive for cloud sync
4. You'll be redirected back to V_Track

**Note**: Your Google account credentials are encrypted and stored securely in the database.

### Step 5: Configuration Wizard

After authentication, you'll be guided through a 5-step configuration wizard:

#### Step 1: General Information

Configure basic system settings:

- **Country**: Select your country (for timezone detection)
- **Timezone**: Auto-detected based on country (e.g., `Asia/Ho_Chi_Minh`)
- **Brand Name**: Your company/brand name
- **Working Days**: Select operational days (default: Mon-Sun)
- **Working Hours**: Set operational time range (default: 00:00-00:00 for 24/7)
- **Language**: Select UI language (Vietnamese or English)

**Click "Next" to proceed.**

#### Step 2: Video Source Configuration

Choose video source type:

**Option A: Local Storage**
1. Select "Local Storage"
2. Enter input video directory path:
   - Windows: `C:\Users\YourName\Videos\VTrack\Input`
   - macOS: `/Users/YourName/Movies/VTrack/Input`
   - Linux: `/home/YourName/Videos/VTrack/Input`
3. Enter output clips directory path (auto-suggested)
4. Click "Add Camera" to configure camera folders:
   - Camera Name: e.g., "Cam1", "Cam2"
   - Folder Path: Subfolder name in input directory
   - Select cameras to enable
5. Click "Save" and "Next"

**Option B: Google Drive Storage**
1. Select "Google Drive"
2. Click "Authorize Google Drive Access"
3. Grant Drive permissions
4. Select parent folder containing video files
5. System will scan for camera subfolders automatically
6. Configure sync interval (default: 15 minutes)
7. Click "Save" and "Next"

#### Step 3: Processing Settings

Configure frame processing parameters:

- **Frame Rate**: FPS for video analysis (default: 30)
- **Frame Interval**: Seconds between frame samples (default: 5)
- **Video Buffer**: Seconds of buffer before/after event (default: 2)
- **Motion Threshold**: Sensitivity for motion detection (default: 0.1)
- **Stable Duration**: Seconds of stability required (default: 1.0)

**Click "Next" to proceed.**

#### Step 4: ROI Configuration

Define Region of Interest for each camera:

1. **Select Camera**: Choose camera from dropdown
2. **Upload Sample Video**:
   - Click "Select Video File"
   - Choose a representative video file
   - Video should show typical packing activity
3. **Run Hand Detection**:
   - Click "Detect Packing Area"
   - System analyzes video and detects hand movements
   - Preview image shows detected ROI
4. **(Optional) QR Trigger Area**:
   - Enable "QR Trigger Detection"
   - Click "Detect Trigger Area"
   - System detects QR code scanning zone
5. **Verify ROI**:
   - Review generated ROI preview image
   - Ensure packing area covers work zone
6. **Save ROI**:
   - Click "Finalize ROI"
   - ROI saved to `packing_profiles` table
7. **Repeat for all cameras**

**Click "Next" when all cameras configured.**

#### Step 5: Packing Profile

Configure packing time thresholds:

- **Min Packing Time**: Minimum seconds for valid event (default: 10)
- **Max Packing Time**: Maximum seconds for single event (default: 120)
- **Jump Time Ratio**: Time ratio for event splitting (default: 0.5)
- **Scan Mode**: Detection mode (default: "full")
- **Fixed Threshold**: QR detection threshold (default: 20)
- **Margin**: Detection margin in pixels (default: 60)

**Click "Complete Setup" to finish.**

### Step 6: Verify Configuration

After completing the wizard:

1. **Check General Info**:
   ```bash
   sqlite3 backend/database/events.db "SELECT * FROM general_info;"
   ```

2. **Check Video Sources**:
   ```bash
   sqlite3 backend/database/events.db "SELECT * FROM video_sources;"
   ```

3. **Check ROI Profiles**:
   ```bash
   sqlite3 backend/database/events.db "SELECT profile_name, packing_area, qr_trigger_area FROM packing_profiles;"
   ```

## Running V_Track

### Development Mode

**Backend** (Terminal 1):
```bash
cd backend
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows
python app.py
```

**Frontend** (Terminal 2):
```bash
cd frontend
npm run dev
```

Access: `http://localhost:3000`

### Production Mode

**Backend**:
```bash
cd backend
source venv/bin/activate
python app.py  # Configure with gunicorn for production
```

**Frontend**:
```bash
cd frontend
npm run build
npm start
```

Access: `http://localhost:3000`

### Running as Service (Linux/macOS)

Create systemd service file `/etc/systemd/system/vtrack-backend.service`:

```ini
[Unit]
Description=V_Track Backend Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/V_Track/backend
Environment="PATH=/path/to/V_Track/backend/venv/bin"
ExecStart=/path/to/V_Track/backend/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vtrack-backend
sudo systemctl start vtrack-backend
sudo systemctl status vtrack-backend
```

## Troubleshooting

### Backend Issues

#### Port 8080 Already in Use
```bash
# Find process using port 8080
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

#### Database Locked Error
```bash
# Check database file permissions
ls -la backend/database/events.db

# Fix permissions
chmod 664 backend/database/events.db  # macOS/Linux
```

#### Import Errors
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Should be 3.8+
```

### Frontend Issues

#### Port 3000 Already in Use
```bash
# Kill process on port 3000
npx kill-port 3000

# Or use different port
PORT=3001 npm run dev
```

#### npm Install Fails
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Build Errors
```bash
# Check Node.js version
node --version  # Should be 18.x+

# Update Next.js
npm install next@latest react@latest react-dom@latest
```

### Google OAuth Issues

#### Redirect URI Mismatch
- Ensure `http://localhost:3000/api/auth/callback` is registered in Google Cloud Console
- Check OAuth client credentials in `.env` file

#### Drive Access Denied
- Verify Google Drive API is enabled in Google Cloud Console
- Re-authorize access in application settings

### Database Issues

#### Tables Not Created
```bash
# Re-run database initialization
python database.py

# Check SQLite version
sqlite3 --version  # Should be 3.x
```

#### Migration Errors
```bash
# Backup database
cp backend/database/events.db backend/database/events.db.backup

# Drop and recreate (WARNING: Data loss)
rm backend/database/events.db
python database.py
```

### Cloud Sync Issues

#### Sync Not Starting
1. Check sync_status table:
   ```bash
   sqlite3 backend/database/events.db "SELECT * FROM sync_status;"
   ```
2. Verify source_id exists in video_sources
3. Check backend logs for error messages

#### Downloads Failing
1. Check Google Drive permissions
2. Verify network connectivity
3. Check available disk space

## Next Steps

After successful installation:

1. **Run First Run Program**: Process initial video batch (see [Processing Modes](processing-modes.md))
2. **Configure ROI**: Set up detection zones (see [ROI Configuration](roi-configuration.md))
3. **Test Event Detection**: Process sample videos and verify events
4. **Setup Cloud Sync**: Configure automatic downloads (if using Google Drive)
5. **Review API Docs**: Understand available endpoints (see [API Endpoints](../api/endpoints.md))

## Additional Resources

- [Processing Modes Guide](processing-modes.md)
- [ROI Configuration Guide](roi-configuration.md)
- [API Documentation](../api/endpoints.md)
- [Architecture Overview](../architecture/overview.md)
- [Troubleshooting Guide](troubleshooting.md)

## Support

For installation support:
- Email: support@vtrack.com
- Documentation: `/docs` folder
- Health Check: `http://localhost:8080/health`

---

**Last Updated**: 2025-10-06
