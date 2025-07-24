import os


def find_project_root(file_path):
    """Tìm thư mục gốc của dự án bắt đầu từ file_path."""
    current_path = os.path.dirname(os.path.abspath(file_path))
    while current_path != os.path.dirname(current_path):
        if "backend" in os.listdir(current_path):
            return current_path
        current_path = os.path.dirname(current_path)
    raise RuntimeError("Không tìm thấy thư mục gốc dự án.")


def get_paths():
    base_dir = find_project_root(__file__)
    return {
        "BASE_DIR": base_dir,
        "DB_PATH": os.path.join(base_dir, "backend/database/events.db"),
        "BACKEND_DIR": os.path.join(base_dir, "backend"),
        "FRONTEND_DIR": os.path.join(base_dir, "frontend"),
        "CAMERA_ROI_DIR": os.path.join(base_dir, "resources", "output_clips", "CameraROI")
    }
