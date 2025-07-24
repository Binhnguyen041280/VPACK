import sqlite3
import os

# Hàm tìm thư mục gốc dự án dựa trên tên thư mục
def find_project_root(start_path):
    current_path = os.path.abspath(start_path)
    while os.path.basename(current_path) != "V_Track":
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:  # Đã đến thư mục gốc của hệ thống (/)
            raise ValueError("Could not find project root (V_Track directory)")
        current_path = parent_path
    return current_path

# Xác định thư mục gốc của dự án
BASE_DIR = find_project_root(os.path.abspath(__file__))

# Định nghĩa DB_PATH mặc định dựa trên BASE_DIR
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "backend/database", "events.db")
os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)  # Tạo thư mục database nếu chưa có

# Hàm lấy DB_PATH từ processing_config
def get_db_path():
    try:
        conn = sqlite3.connect(DEFAULT_DB_PATH)  # Kết nối tạm thời để truy vấn
        cursor = conn.cursor()
        cursor.execute("SELECT db_path FROM processing_config WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else DEFAULT_DB_PATH
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
