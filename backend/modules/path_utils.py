import os
import sys


def find_project_root(file_path):
    """Find the project root directory starting from file_path."""
    current_path = os.path.dirname(os.path.abspath(file_path))
    while current_path != os.path.dirname(current_path):
        if "backend" in os.listdir(current_path):
            return current_path
        current_path = os.path.dirname(current_path)
    raise RuntimeError("Project root directory not found.")


def get_deployment_mode():
    """
    Detect deployment mode

    Returns:
        str: 'development', 'docker', 'production', or 'installed'
    """
    # 1. Check environment variable (highest priority)
    env_mode = os.getenv("VTRACK_DEPLOYMENT_MODE")
    if env_mode in ['development', 'docker', 'production', 'installed']:
        return env_mode

    # 2. Detect Docker environment
    if os.path.exists("/.dockerenv") or os.getenv("VTRACK_IN_DOCKER") == "true":
        return 'docker'

    # 3. Check if running from source (has backend/ subfolder structure)
    try:
        base_dir = find_project_root(__file__)
        if os.path.exists(os.path.join(base_dir, "backend")):
            return 'development'
    except RuntimeError:
        pass

    # 4. Check if frozen (PyInstaller/cx_Freeze)
    if getattr(sys, 'frozen', False):
        return 'production'

    # 5. Default to installed mode
    return 'installed'


def is_development_mode():
    """
    Legacy function for backward compatibility
    Returns True if in development or docker mode (uses var/ directory)
    """
    mode = get_deployment_mode()
    return mode in ['development', 'docker']


def get_paths():
    """
    Get application paths with unified structure across all deployment modes

    All modes use the same relative structure:
        {BASE_DIR}/
        ├── database/
        │   └── events.db
        └── var/
            ├── cache/
            │   ├── cloud_downloads/    # Cloud file staging
            │   └── roi_legacy/          # Legacy ROI images (deprecated)
            ├── logs/
            │   └── application/         # App & event processing logs
            ├── tmp/                     # Temporary files
            └── uploads/                 # User uploaded files

    Only BASE_DIR differs per mode:
    - development: /path/to/V_Track/ (project root, so var/ is at root)
    - docker: /app/
    - production: /path/to/executable/
    - installed: ~/.local/share/vtrack/ (or platform equivalent)

    Returns:
        dict: Path configuration for current deployment mode
    """
    mode = get_deployment_mode()

    # Determine BASE_DIR based on deployment mode
    if mode == 'development':
        # Development: Use backend/ as base (var/ at backend/var/)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    elif mode == 'docker':
        # Docker: Use /app/ or custom base
        base_dir = os.getenv("VTRACK_BASE_DIR", "/app")

    elif mode == 'production':
        # Production EXE: Directory containing executable
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.getcwd()

    else:  # installed
        # Installed: Use XDG/platform-specific directory
        try:
            from platformdirs import user_data_dir
            base_dir = user_data_dir("vtrack", "VTrack")
        except ImportError:
            base_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "vtrack")

    # Build unified path structure
    var_dir = os.path.join(base_dir, "var")

    # Database location depends on mode
    if mode == 'development':
        # Development: database is in backend/database/ (base_dir is already backend/)
        db_path = os.path.join(base_dir, "database", "events.db")
        backend_dir = base_dir
        frontend_dir = os.path.join(os.path.dirname(base_dir), "frontend")
    else:
        # Docker/Production/Installed: database at base_dir/database/
        db_path = os.path.join(base_dir, "database", "events.db")
        backend_dir = base_dir
        frontend_dir = base_dir

    return {
        "BASE_DIR": base_dir,
        "DEPLOYMENT_MODE": mode,
        # Database
        "DB_PATH": db_path,
        # Code directories (for compatibility)
        "BACKEND_DIR": backend_dir,
        "FRONTEND_DIR": frontend_dir,
        # Var subdirectories (unified structure)
        "VAR_DIR": var_dir,
        "CACHE_DIR": os.path.join(var_dir, "cache"),
        "LOGS_DIR": os.path.join(var_dir, "logs"),
        "TMP_DIR": os.path.join(var_dir, "tmp"),
        "UPLOADS_DIR": os.path.join(var_dir, "uploads"),
        # Specific paths
        "CLOUD_STAGING_DIR": os.path.join(var_dir, "cache", "cloud_downloads"),
        # Legacy paths (kept for backward compatibility with old code)
        # DEPRECATED: CameraROI not used in current implementation
        "CAMERA_ROI_DIR": os.path.join(var_dir, "cache", "roi_legacy"),
        # Legacy flag
        "IS_DEVELOPMENT": mode in ['development', 'docker']
    }


def get_cloud_staging_path(source_name=None):
    """
    Get cloud staging directory path (auto-managed by application)

    Follows web app best practices:
    - Development: {project}/var/cache/cloud_downloads/
    - Production: ~/.cache/vtrack/cloud_downloads/ (Linux)
                  ~/Library/Caches/VTrack/cloud_downloads/ (macOS)
                  %LOCALAPPDATA%\VTrack\Cache\cloud_downloads\ (Windows)

    This is intermediate storage for cloud downloads before processing.
    Files here are expendable and can be cleaned up automatically.

    Args:
        source_name (str, optional): Source name for subdirectory

    Returns:
        str: Full path to cloud staging directory
    """
    paths = get_paths()
    staging_dir = paths["CLOUD_STAGING_DIR"]

    # Create base staging directory if not exists
    os.makedirs(staging_dir, exist_ok=True)

    # If source name provided, create source subdirectory
    if source_name:
        source_dir = os.path.join(staging_dir, source_name)
        os.makedirs(source_dir, exist_ok=True)
        return source_dir

    return staging_dir


def get_logs_dir():
    """Get application logs directory"""
    paths = get_paths()
    logs_dir = paths["LOGS_DIR"]
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def get_tmp_dir():
    """Get application temporary directory"""
    paths = get_paths()
    tmp_dir = paths["TMP_DIR"]
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir
