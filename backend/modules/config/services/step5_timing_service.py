"""
Step 5 Timing/Storage Service Layer for V.PACK Configuration.

Wrapper service for existing timing and storage configuration logic.
Uses existing processing_config table and save_config validation.
"""

import json
import os
from typing import Dict, Any, Tuple, Optional
from ..shared import (
    safe_connection_wrapper,
    execute_with_change_detection,
    validate_timing_config,
    sanitize_input,
    log_step_operation
)


class Step5TimingService:
    """Service class for Step 5 Timing/Storage configuration operations."""
    
    # Default values matching existing save_config logic
    DEFAULT_MIN_PACKING_TIME = 10
    DEFAULT_MAX_PACKING_TIME = 120
    DEFAULT_VIDEO_BUFFER = 2
    DEFAULT_STORAGE_DURATION = 30
    DEFAULT_FRAME_RATE = 30
    DEFAULT_FRAME_INTERVAL = 5
    DEFAULT_OUTPUT_PATH = "/default/output"
    
    def get_timing_config(self) -> Dict[str, Any]:
        """
        Get current timing and storage configuration from processing_config table.
        
        Returns:
            Dict containing current timing configuration
        """
        try:
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT min_packing_time, max_packing_time, video_buffer, storage_duration,
                           frame_rate, frame_interval, output_path
                    FROM processing_config WHERE id = 1
                """)
                
                row = cursor.fetchone()
                
                if row:
                    min_packing_time, max_packing_time, video_buffer, storage_duration, \
                    frame_rate, frame_interval, output_path = row
                    
                    config = {
                        "min_packing_time": min_packing_time or self.DEFAULT_MIN_PACKING_TIME,
                        "max_packing_time": max_packing_time or self.DEFAULT_MAX_PACKING_TIME,
                        "video_buffer": video_buffer or self.DEFAULT_VIDEO_BUFFER,
                        "storage_duration": storage_duration or self.DEFAULT_STORAGE_DURATION,
                        "frame_rate": frame_rate or self.DEFAULT_FRAME_RATE,
                        "frame_interval": frame_interval or self.DEFAULT_FRAME_INTERVAL,
                        "output_path": output_path or self.DEFAULT_OUTPUT_PATH
                    }
                else:
                    # No record exists - return defaults
                    config = {
                        "min_packing_time": self.DEFAULT_MIN_PACKING_TIME,
                        "max_packing_time": self.DEFAULT_MAX_PACKING_TIME,
                        "video_buffer": self.DEFAULT_VIDEO_BUFFER,
                        "storage_duration": self.DEFAULT_STORAGE_DURATION,
                        "frame_rate": self.DEFAULT_FRAME_RATE,
                        "frame_interval": self.DEFAULT_FRAME_INTERVAL,
                        "output_path": self.DEFAULT_OUTPUT_PATH
                    }
                
                log_step_operation("5", "get_timing", {
                    "min_packing_time": config["min_packing_time"],
                    "max_packing_time": config["max_packing_time"]
                })
                
                return config
                
        except Exception as e:
            log_step_operation("5", "get_timing", {"error": str(e)}, False)
            
            # Return safe defaults on error
            return {
                "min_packing_time": self.DEFAULT_MIN_PACKING_TIME,
                "max_packing_time": self.DEFAULT_MAX_PACKING_TIME,
                "video_buffer": self.DEFAULT_VIDEO_BUFFER,
                "storage_duration": self.DEFAULT_STORAGE_DURATION,
                "frame_rate": self.DEFAULT_FRAME_RATE,
                "frame_interval": self.DEFAULT_FRAME_INTERVAL,
                "output_path": self.DEFAULT_OUTPUT_PATH,
                "error": str(e)
            }
    
    def update_timing_config(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Update timing and storage configuration using existing processing_config logic.
        Reuses validation from save_config function.
        
        Args:
            data: Timing configuration data
            
        Returns:
            Tuple of (success: bool, result_data: dict)
        """
        try:
            # Extract and sanitize data
            sanitized_data = {
                "min_packing_time": data.get('min_packing_time', self.DEFAULT_MIN_PACKING_TIME),
                "max_packing_time": data.get('max_packing_time', self.DEFAULT_MAX_PACKING_TIME),
                "video_buffer": data.get('video_buffer', self.DEFAULT_VIDEO_BUFFER),
                "storage_duration": data.get('storage_duration', self.DEFAULT_STORAGE_DURATION),
                "frame_rate": data.get('frame_rate', self.DEFAULT_FRAME_RATE),
                "frame_interval": data.get('frame_interval', self.DEFAULT_FRAME_INTERVAL),
                "output_path": sanitize_input(data.get('output_path', self.DEFAULT_OUTPUT_PATH), 500)
            }
            
            # Validate data using shared validation
            is_valid, validation_error = validate_timing_config(sanitized_data)
            if not is_valid:
                return False, {"error": validation_error}
            
            # Additional business logic validation
            business_valid, business_error = self._validate_business_rules(sanitized_data)
            if not business_valid:
                return False, {"error": business_error}
            
            # Check for changes using shared utility
            changed, current_data = execute_with_change_detection(
                table_name="processing_config",
                record_id=1,
                new_data=sanitized_data
            )
            
            if not changed:
                # No changes detected
                log_step_operation("5", "update_timing", {"changed": False})
                
                return True, {
                    **sanitized_data,
                    "changed": False,
                    "message": "No changes detected"
                }
            
            # Perform update with preservation of existing data
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()
                
                # Get DB_PATH using same logic as save_config
                try:
                    from modules.db_utils import find_project_root
                    BASE_DIR = find_project_root(os.path.abspath(__file__))
                    DB_PATH = os.path.join(BASE_DIR, "backend/database/events.db")
                except ImportError:
                    # Fallback to default database path
                    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                    DB_PATH = os.path.join(BASE_DIR, "database", "events.db")
                
                # Update using same pattern as save_config
                cursor.execute("""
                    INSERT OR REPLACE INTO processing_config (
                        id, min_packing_time, max_packing_time, video_buffer, storage_duration,
                        frame_rate, frame_interval, output_path, db_path,
                        input_path, selected_cameras, camera_paths, default_frame_mode, run_default_on_start
                    ) VALUES (
                        1, ?, ?, ?, ?, ?, ?, ?, ?,
                        COALESCE((SELECT input_path FROM processing_config WHERE id = 1), ''),
                        COALESCE((SELECT selected_cameras FROM processing_config WHERE id = 1), '[]'),
                        COALESCE((SELECT camera_paths FROM processing_config WHERE id = 1), '{}'),
                        COALESCE((SELECT default_frame_mode FROM processing_config WHERE id = 1), 'default'),
                        COALESCE((SELECT run_default_on_start FROM processing_config WHERE id = 1), 1)
                    )
                """, (
                    sanitized_data["min_packing_time"],
                    sanitized_data["max_packing_time"],
                    sanitized_data["video_buffer"],
                    sanitized_data["storage_duration"],
                    sanitized_data["frame_rate"],
                    sanitized_data["frame_interval"],
                    sanitized_data["output_path"],
                    DB_PATH
                ))
                
                conn.commit()
                
                log_step_operation("5", "update_timing", {
                    "min_packing_time": sanitized_data["min_packing_time"],
                    "max_packing_time": sanitized_data["max_packing_time"],
                    "frame_rate": sanitized_data["frame_rate"],
                    "changed": True
                })
                
                result = {
                    **sanitized_data,
                    "changed": True,
                    "message": "Timing configuration updated successfully"
                }
                
                return True, result
                
        except Exception as e:
            log_step_operation("5", "update_timing", {"error": str(e)}, False)
            return False, {"error": f"Failed to update timing configuration: {str(e)}"}
    
    def _validate_business_rules(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Apply business validation rules similar to save_config.
        
        Args:
            data: Configuration data to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Validate output path exists or can be created
        output_path = data.get("output_path", "")
        if output_path and output_path != self.DEFAULT_OUTPUT_PATH:
            try:
                # Create directory if it doesn't exist
                os.makedirs(output_path, exist_ok=True)
                
                # Check if we can write to the directory
                if not os.access(output_path, os.W_OK):
                    return False, f"Output directory is not writable: {output_path}"
                    
            except Exception as e:
                return False, f"Cannot create or access output directory: {str(e)}"
        
        # Validate timing relationships
        min_time = data.get("min_packing_time", 0)
        max_time = data.get("max_packing_time", 0)
        
        if min_time >= max_time:
            return False, "Minimum packing time must be less than maximum packing time"
        
        # Validate frame settings
        frame_rate = data.get("frame_rate", 30)
        frame_interval = data.get("frame_interval", 5)
        
        if frame_interval > frame_rate:
            return False, "Frame interval cannot be greater than frame rate"
        
        return True, ""
    
    def get_timing_statistics(self) -> Dict[str, Any]:
        """
        Get timing configuration statistics for monitoring.
        
        Returns:
            Dict with timing statistics
        """
        try:
            config = self.get_timing_config()
            
            stats = {
                "current_config": config,
                "packing_time_range": {
                    "min": config["min_packing_time"],
                    "max": config["max_packing_time"],
                    "range_seconds": config["max_packing_time"] - config["min_packing_time"]
                },
                "performance_settings": {
                    "frame_rate": config["frame_rate"],
                    "frame_interval": config["frame_interval"],
                    "frames_per_second_processed": config["frame_rate"] / max(1, config["frame_interval"])
                },
                "storage_settings": {
                    "storage_duration_days": config["storage_duration"],
                    "video_buffer_seconds": config["video_buffer"],
                    "output_path": config["output_path"]
                }
            }
            
            # Add validation status
            is_valid, _ = validate_timing_config(config)
            stats["validation_status"] = "valid" if is_valid else "invalid"
            
            return stats
            
        except Exception as e:
            return {"error": f"Failed to get timing statistics: {str(e)}"}
    
    def validate_timing_settings(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate timing settings without saving.
        
        Args:
            data: Timing configuration data to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str, validation_details: dict)
        """
        validation_details = {
            "basic_validation": "pending",
            "business_rules": "pending",
            "field_checks": {}
        }
        
        try:
            # Basic validation
            is_valid, validation_error = validate_timing_config(data)
            validation_details["basic_validation"] = "passed" if is_valid else "failed"
            
            if not is_valid:
                validation_details["basic_error"] = validation_error
                return False, validation_error, validation_details
            
            # Business rules validation
            business_valid, business_error = self._validate_business_rules(data)
            validation_details["business_rules"] = "passed" if business_valid else "failed"
            
            if not business_valid:
                validation_details["business_error"] = business_error
                return False, business_error, validation_details
            
            # Field-by-field validation details
            for field in ["min_packing_time", "max_packing_time", "video_buffer", 
                         "storage_duration", "frame_rate", "frame_interval"]:
                if field in data:
                    value = data[field]
                    validation_details["field_checks"][field] = {
                        "value": value,
                        "type": type(value).__name__,
                        "valid": isinstance(value, int) and value > 0
                    }
            
            return True, "All validations passed", validation_details
            
        except Exception as e:
            validation_details["exception"] = str(e)
            return False, f"Validation error: {str(e)}", validation_details


# Create singleton instance for import
step5_timing_service = Step5TimingService()