import sqlite3
import os
from modules.path_utils import get_paths


def get_processing_config():
    """
    Trả về INPUT_VIDEO_DIR và LOG_DIR từ bảng processing_config.
    Nếu thiếu, fallback về path mặc định.
    """
    paths = get_paths()
    db_path = paths["DB_PATH"]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT input_path, output_path FROM processing_config LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "INPUT_VIDEO_DIR": row[0],
                "LOG_DIR": row[1],
            }
    except Exception as e:
        print(f"[!] Lỗi đọc cấu hình DB: {e}")

    # fallback nếu lỗi hoặc DB trống
    return {
        "INPUT_VIDEO_DIR": os.path.join(paths["BASE_DIR"], "resources/Inputvideo"),
        "LOG_DIR": os.path.join(paths["BASE_DIR"], "resources/output_clips/LOG"),
    }


def get_log_path(file_name: str) -> str:
    """Trả về đường dẫn đầy đủ đến file trong LOG_DIR."""
    log_dir = get_processing_config()["LOG_DIR"]
    return os.path.join(log_dir, file_name)


def get_input_path(file_name: str) -> str:
    """Trả về đường dẫn đầy đủ đến file trong INPUT_VIDEO_DIR."""
    input_dir = get_processing_config()["INPUT_VIDEO_DIR"]
    return os.path.join(input_dir, file_name)