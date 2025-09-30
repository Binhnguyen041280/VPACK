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


def is_development_mode():
    """
    Detect if running in development mode

    Returns:
        bool: True if in development, False if in production/installed
    """
    try:
        base_dir = find_project_root(__file__)
        # If we can find project root with backend/, we're in dev mode
        return os.path.exists(os.path.join(base_dir, "backend"))
    except RuntimeError:
        # Can't find project root = probably installed
        return False


def get_paths():
    """
    Get application paths following web app best practices

    Development: Uses var/ directory in project root
    Production: Uses XDG/platform-specific directories

    Returns:
        dict: Path configuration
    """
    is_dev = is_development_mode()

    if is_dev:
        # Development mode: Use var/ directory in project
        base_dir = find_project_root(__file__)
        var_dir = os.path.join(base_dir, "var")

        return {
            "BASE_DIR": base_dir,
            "DB_PATH": os.path.join(base_dir, "backend/database/events.db"),
            "BACKEND_DIR": os.path.join(base_dir, "backend"),
            "FRONTEND_DIR": os.path.join(base_dir, "frontend"),
            "CAMERA_ROI_DIR": os.path.join(base_dir, "resources", "output_clips", "CameraROI"),
            "VAR_DIR": var_dir,
            "CACHE_DIR": os.path.join(var_dir, "cache"),
            "LOGS_DIR": os.path.join(var_dir, "logs"),
            "TMP_DIR": os.path.join(var_dir, "tmp"),
            "CLOUD_STAGING_DIR": os.path.join(var_dir, "cache", "cloud_downloads"),
            "IS_DEVELOPMENT": True
        }
    else:
        # Production mode: Use XDG/platform-specific directories
        try:
            from platformdirs import user_cache_dir, user_data_dir, user_log_dir
            app_name = "vtrack"
            app_author = "VTrack"

            cache_dir = user_cache_dir(app_name, app_author)
            data_dir = user_data_dir(app_name, app_author)
            log_dir = user_log_dir(app_name, app_author)

            return {
                "BASE_DIR": data_dir,
                "DB_PATH": os.path.join(data_dir, "events.db"),
                "BACKEND_DIR": data_dir,
                "FRONTEND_DIR": data_dir,
                "CAMERA_ROI_DIR": os.path.join(data_dir, "CameraROI"),
                "VAR_DIR": cache_dir,
                "CACHE_DIR": cache_dir,
                "LOGS_DIR": log_dir,
                "TMP_DIR": os.path.join(cache_dir, "tmp"),
                "CLOUD_STAGING_DIR": os.path.join(cache_dir, "cloud_downloads"),
                "IS_DEVELOPMENT": False
            }
        except ImportError:
            # Fallback if platformdirs not available
            import tempfile
            home = os.path.expanduser("~")

            return {
                "BASE_DIR": os.path.join(home, ".local", "share", "vtrack"),
                "DB_PATH": os.path.join(home, ".local", "share", "vtrack", "events.db"),
                "BACKEND_DIR": os.path.join(home, ".local", "share", "vtrack"),
                "FRONTEND_DIR": os.path.join(home, ".local", "share", "vtrack"),
                "CAMERA_ROI_DIR": os.path.join(home, ".local", "share", "vtrack", "CameraROI"),
                "VAR_DIR": os.path.join(home, ".cache", "vtrack"),
                "CACHE_DIR": os.path.join(home, ".cache", "vtrack"),
                "LOGS_DIR": os.path.join(home, ".local", "state", "vtrack"),
                "TMP_DIR": tempfile.gettempdir(),
                "CLOUD_STAGING_DIR": os.path.join(home, ".cache", "vtrack", "cloud_downloads"),
                "IS_DEVELOPMENT": False
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
