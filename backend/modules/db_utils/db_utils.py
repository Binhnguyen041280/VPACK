import sqlite3
import os

# Hàm tìm thư mục gốc dự án dựa trên tên thư mục
def find_project_root(start_path):
    current_path = os.path.abspath(start_path)

    # Check Docker first - if running in Docker, /app will be the root
    # We check if the current working directory is /app or we're under /app
    if current_path.startswith("/app") and os.path.exists("/app/modules"):
        return "/app"

    # Try to find V_Track folder (development mode on host)
    while os.path.basename(current_path) != "V_Track":
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:  # Reached filesystem root
            break
        current_path = parent_path

    # If V_Track found, return it
    if os.path.basename(current_path) == "V_Track":
        return current_path

    # Fallback: If /app/modules exists (Docker structure)
    if os.path.exists("/app/modules"):
        return "/app"

    # Last resort: use current working directory if ./backend exists
    if os.path.exists("./backend"):
        return os.getcwd()

    # If we're in the backend directory itself (local development)
    if os.path.exists("./modules"):
        return os.path.dirname(os.path.dirname(os.path.abspath(start_path)))

    raise ValueError("Could not find project root (V_Track directory or /app)")

# Use centralized path configuration
from modules.path_utils import get_paths
paths = get_paths()
BASE_DIR = paths["BASE_DIR"]
DEFAULT_DB_PATH = paths["DB_PATH"]
# Debug print to help diagnose path issues
print(f"DEBUG db_utils.py: __file__={__file__}, BASE_DIR={BASE_DIR}, DB_PATH={DEFAULT_DB_PATH}")
os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)  # Tạo thư mục database nếu chưa có

# Hàm lấy DB_PATH từ processing_config
def get_db_path():
    try:
        conn = sqlite3.connect(DEFAULT_DB_PATH)  # Kết nối tạm thời để truy vấn
        cursor = conn.cursor()
        cursor.execute("SELECT db_path FROM processing_config WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        # If we have a db_path from config, use it only if it exists
        # Otherwise use DEFAULT_DB_PATH (works for both Docker and dev)
        if result and os.path.exists(result[0]):
            return result[0]
        return DEFAULT_DB_PATH
    except Exception as e:
        print(f"Error getting DB_PATH from database: {e}")
        return DEFAULT_DB_PATH

DB_PATH = get_db_path()

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")
    if not os.access(DB_PATH, os.R_OK):
        raise PermissionError(f"No read permission for database: {DB_PATH}")
    if not os.access(DB_PATH, os.W_OK):
        raise PermissionError(f"No write permission for database: {DB_PATH}")
    return sqlite3.connect(DB_PATH, check_same_thread=False)
