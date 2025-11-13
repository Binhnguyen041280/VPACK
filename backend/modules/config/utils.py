"""
Shared utility functions for V_Track config module.

This module contains common functions used across multiple config route modules
to avoid code duplication and maintain DRY principle.
"""

import os
import json
from typing import List, Dict, Any, Optional
from modules.path_utils import get_paths


def get_working_path_for_source(source_type: str, source_name: str, source_path: str) -> str:
    """
    Map source connection info to actual working directory.

    Args:
        source_type: Type of source ('local', 'cloud', etc.)
        source_name: Name of the source
        source_path: Path or URL of the source

    Returns:
        Working path for the source
    """
    if source_type == "local":
        # Local: source_path is actual file system path
        working_path = source_path
        print(f"Local Path Mapping: {source_path} -> {working_path}")
        return working_path

    elif source_type == "cloud":
        # Cloud: source_path is cloud URL, working path is staging directory
        from modules.path_utils import get_cloud_staging_path

        working_path = get_cloud_staging_path(source_name)
        print(f"Cloud Path Mapping: {source_path} -> {working_path}")
        print(f"✅ Using var/cache staging directory")

        return working_path

    else:
        # Unknown source type: use as-is
        print(f"Unknown source type '{source_type}', using path as-is: {source_path}")
        return source_path


def detect_camera_folders(path: str) -> List[str]:
    """
    Detect camera folders in the given path.

    Args:
        path: Directory path to scan for camera folders

    Returns:
        List of camera folder names
    """
    cameras = []

    if not os.path.exists(path):
        return cameras

    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                # Check if this looks like a camera folder
                # Common camera folder patterns: Cam*, Camera*, Channel*, etc.
                item_lower = item.lower()
                if any(pattern in item_lower for pattern in ["cam", "camera", "channel", "ch"]):
                    cameras.append(item)
                # Also include any directory that contains video files
                elif has_video_files(item_path):
                    cameras.append(item)

        cameras.sort()  # Sort alphabetically
        return cameras
    except Exception as e:
        print(f"Error detecting cameras in {path}: {e}")
        return cameras


def scan_subdirectories_as_cameras(path: str) -> Dict[str, Any]:
    """
    Enhanced function to scan subdirectories and return structured camera folder data.

    Args:
        path: Directory path to scan for subdirectories

    Returns:
        Dict with success status, folders list, and error message if any
    """
    result = {"success": False, "folders": [], "message": ""}

    # Validate input path
    if not path or not isinstance(path, str):
        result["message"] = "Invalid path provided"
        return result

    path = path.strip()
    if not path:
        result["message"] = "Empty path provided"
        return result

    # Check if path exists
    if not os.path.exists(path):
        result["message"] = f"Path does not exist: {path}"
        return result

    # Check if it's a directory
    if not os.path.isdir(path):
        result["message"] = f"Path is not a directory: {path}"
        return result

    try:
        # Check read permissions
        os.listdir(path)
    except PermissionError:
        result["message"] = f"Permission denied accessing path: {path}"
        return result
    except Exception as e:
        result["message"] = f"Error accessing path: {str(e)}"
        return result

    folders = []
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)

            # Only include directories (ignore files)
            if os.path.isdir(item_path):
                try:
                    # Test if we can access the directory
                    os.listdir(item_path)

                    folders.append({"name": item, "path": item_path})
                except PermissionError:
                    # Skip directories we can't access, but don't fail the entire operation
                    print(f"Skipping directory due to permissions: {item_path}")
                    continue
                except Exception as e:
                    # Skip problematic directories
                    print(f"Skipping directory due to error: {item_path} - {e}")
                    continue

        # Sort folders alphabetically by name
        folders.sort(key=lambda x: x["name"].lower())

        result["success"] = True
        result["folders"] = folders

        if not folders:
            result["message"] = "No subdirectories found in the specified path"
        else:
            result["message"] = f"Found {len(folders)} subdirectory(ies)"

    except Exception as e:
        result["message"] = f"Error scanning directory: {str(e)}"

    return result


def has_video_files(path: str, max_depth: int = 2) -> bool:
    """
    Check if directory contains video files (recursive up to max_depth).

    Args:
        path: Directory path to check
        max_depth: Maximum recursion depth

    Returns:
        True if video files are found, False otherwise
    """
    video_extensions = (".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".m4v", ".mpg", ".mpeg")

    def check_directory(dir_path: str, depth: int) -> bool:
        if depth > max_depth:
            return False

        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path) and item.lower().endswith(video_extensions):
                    return True
                elif os.path.isdir(item_path) and depth < max_depth:
                    if check_directory(item_path, depth + 1):
                        return True
        except (PermissionError, OSError):
            pass

        return False

    return check_directory(path, 0)


def extract_cameras_from_cloud_folders(folders: List[Dict[str, Any]]) -> List[str]:
    """
    Extract camera names from cloud folders.

    Args:
        folders: List of folder objects with metadata

    Returns:
        List of extracted camera names
    """
    cameras = []

    for folder in folders:
        if isinstance(folder, dict):
            # Folder object with metadata
            camera_name = folder.get("name", "Unknown_Folder")

            # If it's a deep folder, use parent names for context
            if folder.get("depth", 1) > 2:
                path_parts = folder.get("path", "").split("/")
                # Use second-to-last part as camera name (skip filename)
                if len(path_parts) >= 2:
                    camera_name = path_parts[-2] or path_parts[-1]
        else:
            # Simple string name
            camera_name = str(folder)

        # Clean and standardize camera name
        camera_name = camera_name.replace(" ", "_").replace("/", "_").replace("\\", "_").strip("_")

        if camera_name and camera_name not in cameras:
            cameras.append(camera_name)

    return cameras


def load_config() -> Dict[str, str]:
    """
    Load configuration from config.json file or environment variables.

    Returns:
        Configuration dictionary with default values
    """
    # Use centralized path configuration
    paths = get_paths()
    default_config = {
        "db_path": paths["DB_PATH"],
        "input_path": os.path.join(paths["BASE_DIR"], "Inputvideo"),
        "output_path": os.path.join(paths["BASE_DIR"], "output_clips"),
    }

    CONFIG_FILE = os.path.join(paths["BASE_DIR"], "config.json")
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
            return default_config

    return {
        "db_path": os.getenv("DB_PATH", default_config["db_path"]),
        "input_path": os.getenv("INPUT_PATH", default_config["input_path"]),
        "output_path": os.getenv("OUTPUT_PATH", default_config["output_path"]),
    }
