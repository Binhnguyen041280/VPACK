"""
Shared validation utilities for V.PACK config routes.

Provides consistent validation functions for different data types
used across the step-based configuration system.
"""

import re
import json
import os
from typing import List, Dict, Any, Optional, Union, Tuple


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, str]:
    """
    Validate that all required fields are present and not empty.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    for field in required_fields:
        if field not in data:
            return False, f"Field '{field}' is required"
        
        value = data[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, f"Field '{field}' cannot be empty"
        
        if isinstance(value, list) and len(value) == 0:
            return False, f"Field '{field}' cannot be an empty array"
    
    return True, ""


def validate_time_format(time_str: str, field_name: str = "time") -> Tuple[bool, str]:
    """
    Validate HH:MM time format.
    
    Args:
        time_str: Time string to validate
        field_name: Name of the field for error messages
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not time_str or not isinstance(time_str, str):
        return False, f"{field_name} must be a non-empty string"
    
    # Pattern for HH:MM format (24-hour)
    time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
    
    if not re.match(time_pattern, time_str.strip()):
        return False, f"{field_name} must be in HH:MM format (24-hour)"
    
    return True, ""


def validate_brand_name(brand_name: str) -> Tuple[bool, str]:
    """
    Validate brand name format and constraints.
    
    Args:
        brand_name: Brand name to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not brand_name or not isinstance(brand_name, str):
        return False, "Brand name must be a non-empty string"
    
    brand_name = brand_name.strip()
    
    if not brand_name:
        return False, "Brand name cannot be empty"
    
    if len(brand_name) > 100:
        return False, "Brand name cannot exceed 100 characters"
    
    # Allow letters, numbers, underscore, hyphen, and spaces
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', brand_name):
        return False, "Brand name can only contain letters, numbers, underscore, hyphen, and spaces"
    
    return True, ""


def validate_working_days(working_days: List[str]) -> Tuple[bool, str]:
    """
    Validate working days array.
    
    Args:
        working_days: List of day names
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not isinstance(working_days, list):
        return False, "Working days must be an array"
    
    if len(working_days) == 0:
        return False, "At least one working day must be selected"
    
    valid_days = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
    
    for day in working_days:
        if not isinstance(day, str) or day not in valid_days:
            return False, f"Invalid day name: {day}. Must be one of: {', '.join(sorted(valid_days))}"
    
    return True, ""


def validate_video_source_config(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate video source configuration data.
    
    Args:
        data: Video source configuration data
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    source_type = data.get('sourceType')
    if not source_type:
        return False, "Source type is required"
    
    if source_type == 'local_storage':
        input_path = data.get('inputPath', '').strip()
        if not input_path:
            return False, "Input path is required for local storage"
        
        selected_cameras = data.get('selectedCameras', [])
        if not selected_cameras:
            return False, "At least one camera must be selected"
    
    elif source_type == 'cloud_storage':
        selected_tree_folders = data.get('selected_tree_folders', [])
        if not selected_tree_folders:
            return False, "At least one folder must be selected for cloud storage"
    
    else:
        return False, f"Unknown source type: {source_type}"
    
    return True, ""


def validate_packing_area_config(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate packing area configuration data.
    
    Args:
        data: Packing area configuration data
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    detection_zones = data.get('detection_zones', [])
    
    if not isinstance(detection_zones, list):
        return False, "Detection zones must be an array"
    
    if len(detection_zones) == 0:
        return False, "At least one detection zone must be configured"
    
    for i, zone in enumerate(detection_zones):
        if not isinstance(zone, dict):
            return False, f"Detection zone {i+1} must be an object"
        
        camera_name = zone.get('camera_name')
        if not camera_name or not isinstance(camera_name, str):
            return False, f"Detection zone {i+1} must have a valid camera_name"
        
        # Validate coordinate arrays
        for area_type in ['packing_area', 'trigger_area']:
            if area_type in zone:
                area = zone[area_type]
                if not isinstance(area, list) or len(area) != 4:
                    return False, f"Detection zone {i+1} {area_type} must be an array of 4 numbers [x, y, w, h]"
                
                if not all(isinstance(coord, (int, float)) for coord in area):
                    return False, f"Detection zone {i+1} {area_type} coordinates must be numbers"
    
    return True, ""


def validate_output_path(output_path: str, create_if_missing: bool = False) -> Tuple[bool, str]:
    """
    Enhanced validation for output path with directory creation and permissions check.
    
    Args:
        output_path: Path to validate
        create_if_missing: Whether to create directory if it doesn't exist
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not output_path or not isinstance(output_path, str):
        return False, "Output path must be a non-empty string"
    
    output_path = output_path.strip()
    
    if not output_path:
        return False, "Output path cannot be empty"
    
    # Check for invalid characters
    if any(char in output_path for char in ['<', '>', ':', '"', '|', '?', '*']):
        return False, "Output path contains invalid characters"
    
    # Check if path is too long (Windows MAX_PATH limit)
    if len(output_path) > 255:
        return False, "Output path is too long (max 255 characters)"
    
    # Check if it's an absolute path
    if not os.path.isabs(output_path):
        return False, "Output path must be an absolute path"
    
    try:
        if create_if_missing:
            # Try to create directory if it doesn't exist
            os.makedirs(output_path, exist_ok=True)
        
        # Check if path exists and is a directory
        if not os.path.exists(output_path):
            return False, f"Output directory does not exist: {output_path}"
        
        if not os.path.isdir(output_path):
            return False, f"Output path is not a directory: {output_path}"
        
        # Check write permissions
        if not os.access(output_path, os.W_OK):
            return False, f"Output directory is not writable: {output_path}"
            
    except OSError as e:
        return False, f"Cannot access output directory: {str(e)}"
    except Exception as e:
        return False, f"Output path validation error: {str(e)}"
    
    return True, ""


def validate_timing_config(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Enhanced validation for timing and storage configuration data.
    
    Args:
        data: Timing configuration data
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    # Validate integer fields with enhanced ranges and constraints
    integer_fields = {
        'min_packing_time': (1, 300, "Minimum packing time must be between 1 and 300 seconds"),
        'max_packing_time': (10, 600, "Maximum packing time must be between 10 and 600 seconds"), 
        'video_buffer': (0, 60, "Video buffer must be between 0 and 60 seconds"),
        'storage_duration': (1, 365, "Storage duration must be between 1 and 365 days"),
        'frame_rate': (1, 120, "Frame rate must be between 1 and 120 fps"),
        'frame_interval': (1, 60, "Frame interval must be between 1 and 60 seconds")
    }
    
    for field, (min_val, max_val, error_msg) in integer_fields.items():
        if field in data:
            value = data[field]
            
            # Type validation
            if not isinstance(value, int):
                return False, f"{field.replace('_', ' ').title()} must be an integer"
            
            # Range validation  
            if value < min_val or value > max_val:
                return False, error_msg
    
    # Cross-field validation: min_packing_time < max_packing_time
    min_time = data.get('min_packing_time')
    max_time = data.get('max_packing_time')
    if min_time is not None and max_time is not None:
        if min_time >= max_time:
            return False, "Minimum packing time must be less than maximum packing time"
        
        # Ensure reasonable gap between min and max
        if (max_time - min_time) < 5:
            return False, "Maximum packing time must be at least 5 seconds greater than minimum packing time"
    
    # Cross-field validation: frame_interval <= frame_rate
    frame_rate = data.get('frame_rate')
    frame_interval = data.get('frame_interval')
    if frame_rate is not None and frame_interval is not None:
        if frame_interval > frame_rate:
            return False, "Frame interval cannot be greater than frame rate"
    
    # Enhanced output path validation
    output_path = data.get('output_path')
    if output_path is not None:
        path_valid, path_error = validate_output_path(output_path, create_if_missing=False)
        if not path_valid:
            return False, path_error
    
    # Performance validation: warn about extreme settings
    if frame_rate is not None and frame_interval is not None:
        processing_load = (frame_rate / max(1, frame_interval))
        if processing_load > 30:  # Processing more than 30 fps
            # This is a warning, not an error, so we'll allow it but could log
            pass
    
    return True, ""


def sanitize_input(value: Union[str, Dict, List], max_length: Optional[int] = None) -> Union[str, Dict, List]:
    """
    Sanitize input data by trimming strings and handling special characters.
    
    Args:
        value: Input value to sanitize
        max_length: Maximum length for string values
        
    Returns:
        Sanitized value
    """
    if isinstance(value, str):
        # Strip whitespace and limit length
        sanitized = value.strip()
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized
    
    elif isinstance(value, dict):
        # Recursively sanitize dictionary values
        return {k: sanitize_input(v, max_length) for k, v in value.items()}
    
    elif isinstance(value, list):
        # Recursively sanitize list items
        return [sanitize_input(item, max_length) for item in value]
    
    else:
        # Return non-string values as-is
        return value


def validate_json_field(value: Any, field_name: str) -> Tuple[bool, str, Any]:
    """
    Validate and parse JSON field data.
    
    Args:
        value: Value that should be JSON serializable
        field_name: Name of the field for error messages
        
    Returns:
        Tuple of (is_valid: bool, error_message: str, parsed_value: Any)
    """
    try:
        if isinstance(value, str):
            # Try to parse JSON string
            parsed = json.loads(value)
            return True, "", parsed
        elif isinstance(value, (dict, list)):
            # Already a JSON-serializable object
            # Verify it can be serialized back to JSON
            json.dumps(value)
            return True, "", value
        else:
            # Try to serialize the value
            json.dumps(value)
            return True, "", value
    except (json.JSONDecodeError, TypeError) as e:
        return False, f"Invalid JSON format for {field_name}: {str(e)}", None


def validate_numeric_range(value: Any, field_name: str, min_val: Optional[float] = None, 
                         max_val: Optional[float] = None, 
                         allow_float: bool = False) -> Tuple[bool, str]:
    """
    Enhanced numeric validation with float support.
    
    Args:
        value: Value to validate
        field_name: Name of field for error messages
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        allow_float: Whether to allow float values
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if allow_float:
        if not isinstance(value, (int, float)):
            return False, f"{field_name} must be a number"
    else:
        if not isinstance(value, int):
            return False, f"{field_name} must be an integer"
    
    if min_val is not None and value < min_val:
        return False, f"{field_name} must be at least {min_val}"
    
    if max_val is not None and value > max_val:
        return False, f"{field_name} must be at most {max_val}"
    
    return True, ""