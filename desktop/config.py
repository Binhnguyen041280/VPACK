"""
VPACK Desktop Configuration
Cấu hình cho phiên bản desktop (.exe/.dmg)
"""

import os
import sys
from pathlib import Path

# App Information
APP_NAME = "VPACK"
APP_VERSION = "1.0.0"
APP_AUTHOR = "VPACK Team"
APP_DESCRIPTION = "Video Processing and Analysis Toolkit"

# Ports
BACKEND_PORT = 8080
FRONTEND_PORT = 3000

# URLs
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
HEALTH_CHECK_URL = f"{BACKEND_URL}/health"

# Timeouts (seconds)
BACKEND_STARTUP_TIMEOUT = 30
FRONTEND_STARTUP_TIMEOUT = 30
HEALTH_CHECK_INTERVAL = 1

# Paths
def get_app_data_dir():
    """Get application data directory based on OS"""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return Path(base) / APP_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:  # Linux
        return Path.home() / f".{APP_NAME.lower()}"

def get_app_dir():
    """Get application installation directory"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent.parent

# Directory structure
APP_DIR = get_app_dir()
DATA_DIR = get_app_data_dir()

# Data directories
DATABASE_DIR = DATA_DIR / "database"
LOGS_DIR = DATA_DIR / "logs"
OUTPUT_DIR = DATA_DIR / "output"
SESSION_DIR = DATA_DIR / "sessions"
INPUT_DIR = DATA_DIR / "input"

# Executables (relative to APP_DIR)
if sys.platform == "win32":
    BACKEND_EXE = APP_DIR / "backend" / "vpack-backend.exe"
    NODE_EXE = APP_DIR / "frontend" / "node.exe"
else:
    BACKEND_EXE = APP_DIR / "backend" / "vpack-backend"
    NODE_EXE = APP_DIR / "frontend" / "node"

FRONTEND_SERVER = APP_DIR / "frontend" / "standalone" / "server.js"

# Environment variables for desktop mode
DESKTOP_ENV = {
    "VTRACK_IN_DOCKER": "false",
    "DEPLOYMENT_MODE": "desktop",
    "FLASK_HOST": "127.0.0.1",
    "FLASK_PORT": str(BACKEND_PORT),
    "VTRACK_DATABASE_DIR": str(DATABASE_DIR),
    "VTRACK_LOGS_DIR": str(LOGS_DIR),
    "VTRACK_OUTPUT_DIR": str(OUTPUT_DIR),
    "VTRACK_SESSION_DIR": str(SESSION_DIR),
    "VTRACK_INPUT_DIR": str(INPUT_DIR),
}

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "vpack-desktop.log"

# System tray
TRAY_ICON = APP_DIR / "resources" / "icon.ico"
TRAY_TOOLTIP = f"{APP_NAME} - Running on port {FRONTEND_PORT}"
