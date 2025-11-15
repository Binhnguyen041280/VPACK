"""
Step 5 Timing/Storage Service Layer for V.PACK Configuration.

Wrapper service for existing timing and storage configuration logic.
Uses existing processing_config table and save_config validation.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple

from modules.path_utils import get_paths

from ..shared import (
    execute_with_change_detection,
    log_step_operation,
    safe_connection_wrapper,
    sanitize_input,
    validate_output_path,
    validate_timing_config,
)

# Get centralized paths at module level
paths = get_paths()
DB_PATH = paths["DB_PATH"]


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

                cursor.execute(
                    """
                    SELECT min_packing_time, max_packing_time, video_buffer, storage_duration,
                           frame_rate, frame_interval, output_path
                    FROM processing_config WHERE id = 1
                """
                )

                row = cursor.fetchone()

                if row:
                    (
                        min_packing_time,
                        max_packing_time,
                        video_buffer,
                        storage_duration,
                        frame_rate,
                        frame_interval,
                        output_path,
                    ) = row

                    config = {
                        "min_packing_time": min_packing_time or self.DEFAULT_MIN_PACKING_TIME,
                        "max_packing_time": max_packing_time or self.DEFAULT_MAX_PACKING_TIME,
                        "video_buffer": video_buffer or self.DEFAULT_VIDEO_BUFFER,
                        "storage_duration": storage_duration or self.DEFAULT_STORAGE_DURATION,
                        "frame_rate": frame_rate or self.DEFAULT_FRAME_RATE,
                        "frame_interval": frame_interval or self.DEFAULT_FRAME_INTERVAL,
                        "output_path": output_path or self.DEFAULT_OUTPUT_PATH,
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
                        "output_path": self.DEFAULT_OUTPUT_PATH,
                    }

                log_step_operation(
                    "5",
                    "get_timing",
                    {
                        "min_packing_time": config["min_packing_time"],
                        "max_packing_time": config["max_packing_time"],
                    },
                )

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
                "error": str(e),
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
            # Extract and sanitize data with enhanced validation
            sanitized_data = {}

            # Process each field with proper defaults and sanitization
            for field in [
                "min_packing_time",
                "max_packing_time",
                "video_buffer",
                "storage_duration",
                "frame_rate",
                "frame_interval",
            ]:
                if field in data:
                    sanitized_data[field] = data[field]
                else:
                    # Use current value or default
                    current_config = self.get_timing_config()
                    sanitized_data[field] = current_config.get(
                        field, getattr(self, f"DEFAULT_{field.upper()}")
                    )

            # Handle output_path separately with enhanced validation
            output_path = data.get("output_path")
            if output_path is not None:
                sanitized_output_path = sanitize_input(output_path, 500)

                # Enhanced path validation with directory creation option
                path_valid, path_error = validate_output_path(
                    sanitized_output_path,
                    create_if_missing=True,  # Allow service to create missing directories
                )
                if not path_valid:
                    return False, {"error": path_error}

                sanitized_data["output_path"] = sanitized_output_path
            else:
                # Use current or default
                current_config = self.get_timing_config()
                sanitized_data["output_path"] = current_config.get(
                    "output_path", self.DEFAULT_OUTPUT_PATH
                )

            # Validate data using enhanced shared validation
            is_valid, validation_error = validate_timing_config(sanitized_data)
            if not is_valid:
                return False, {"error": validation_error}

            # Additional business logic validation with detailed error messages
            business_valid, business_error = self._validate_business_rules(sanitized_data)
            if not business_valid:
                return False, {"error": business_error}

            # Check for changes using shared utility
            changed, current_data = execute_with_change_detection(
                table_name="processing_config", record_id=1, new_data=sanitized_data
            )

            if not changed:
                # No changes detected
                log_step_operation("5", "update_timing", {"changed": False})

                return True, {**sanitized_data, "changed": False, "message": "No changes detected"}

            # Perform update with preservation of existing data
            with safe_connection_wrapper() as conn:
                cursor = conn.cursor()

                # Use centralized DB_PATH (already initialized at module level)

                # Update using same pattern as save_config
                cursor.execute(
                    """
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
                """,
                    (
                        sanitized_data["min_packing_time"],
                        sanitized_data["max_packing_time"],
                        sanitized_data["video_buffer"],
                        sanitized_data["storage_duration"],
                        sanitized_data["frame_rate"],
                        sanitized_data["frame_interval"],
                        sanitized_data["output_path"],
                        DB_PATH,
                    ),
                )

                conn.commit()

                log_step_operation(
                    "5",
                    "update_timing",
                    {
                        "min_packing_time": sanitized_data["min_packing_time"],
                        "max_packing_time": sanitized_data["max_packing_time"],
                        "frame_rate": sanitized_data["frame_rate"],
                        "changed": True,
                    },
                )

                result = {
                    **sanitized_data,
                    "changed": True,
                    "message": "Timing configuration updated successfully",
                }

                return True, result

        except Exception as e:
            log_step_operation("5", "update_timing", {"error": str(e)}, False)
            return False, {"error": f"Failed to update timing configuration: {str(e)}"}

    def _validate_business_rules(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Apply enhanced business validation rules similar to save_config.

        Args:
            data: Configuration data to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Enhanced output path validation (already done in main function)
        output_path = data.get("output_path", "")

        # Validate timing relationships with more detailed checks
        min_time = data.get("min_packing_time", 0)
        max_time = data.get("max_packing_time", 0)

        if min_time >= max_time:
            return (
                False,
                f"Minimum packing time ({min_time}s) must be less than maximum packing time ({max_time}s)",
            )

        # Check for reasonable gap between min and max
        time_gap = max_time - min_time
        if time_gap < 5:
            return (
                False,
                f"Time gap between min and max packing time is too small ({time_gap}s). Minimum gap should be 5 seconds.",
            )

        # Validate frame settings with performance considerations
        frame_rate = data.get("frame_rate", 30)
        frame_interval = data.get("frame_interval", 5)

        if frame_interval > frame_rate:
            return (
                False,
                f"Frame interval ({frame_interval}) cannot be greater than frame rate ({frame_rate})",
            )

        # Performance warning for high processing loads
        processing_fps = frame_rate / max(1, frame_interval)
        if processing_fps > 60:
            return (
                False,
                f"Processing load too high ({processing_fps:.1f} fps). Consider increasing frame interval to reduce load.",
            )

        # Storage duration validation
        storage_duration = data.get("storage_duration", 30)
        if storage_duration > 180:  # More than 6 months
            return (
                False,
                f"Storage duration ({storage_duration} days) exceeds recommended maximum of 180 days",
            )

        # Video buffer validation
        video_buffer = data.get("video_buffer", 2)
        if video_buffer > min_time / 2:
            return (
                False,
                f"Video buffer ({video_buffer}s) should not exceed half of minimum packing time ({min_time/2:.1f}s)",
            )

        return True, ""

    def get_timing_statistics(self) -> Dict[str, Any]:
        """
        Get enhanced timing configuration statistics for monitoring.

        Returns:
            Dict with timing statistics
        """
        try:
            config = self.get_timing_config()

            # Calculate performance metrics
            processing_fps = config["frame_rate"] / max(1, config["frame_interval"])
            processing_load_percent = (processing_fps / config["frame_rate"]) * 100

            # Categorize performance level
            if processing_load_percent < 25:
                performance_category = "low_load"
            elif processing_load_percent < 50:
                performance_category = "balanced"
            elif processing_load_percent < 75:
                performance_category = "high_accuracy"
            else:
                performance_category = "maximum_accuracy"

            stats = {
                "current_config": config,
                "packing_time_range": {
                    "min": config["min_packing_time"],
                    "max": config["max_packing_time"],
                    "range_seconds": config["max_packing_time"] - config["min_packing_time"],
                    "gap_adequate": (config["max_packing_time"] - config["min_packing_time"]) >= 5,
                },
                "performance_metrics": {
                    "frame_rate": config["frame_rate"],
                    "frame_interval": config["frame_interval"],
                    "processing_fps": round(processing_fps, 2),
                    "processing_load_percent": round(processing_load_percent, 2),
                    "performance_category": performance_category,
                    "frames_skipped_percent": round(100 - processing_load_percent, 2),
                },
                "storage_settings": {
                    "storage_duration_days": config["storage_duration"],
                    "video_buffer_seconds": config["video_buffer"],
                    "output_path": config["output_path"],
                    "output_path_exists": (
                        os.path.exists(config["output_path"]) if config["output_path"] else False
                    ),
                },
                "system_impact": {
                    "daily_storage_reduction_percent": round(100 - processing_load_percent, 2),
                    "estimated_daily_frames_processed": int(processing_fps * 86400),  # 24 hours
                    "recommended_adjustments": [],
                },
            }

            # Add recommendations based on analysis
            recommendations = []
            if processing_load_percent > 80:
                recommendations.append(
                    "Consider increasing frame_interval to reduce processing load"
                )
            if processing_load_percent < 10:
                recommendations.append(
                    "Consider decreasing frame_interval for better detection accuracy"
                )
            if config["video_buffer"] > config["min_packing_time"] / 2:
                recommendations.append(
                    "Video buffer is quite large compared to minimum packing time"
                )
            if not stats["storage_settings"]["output_path_exists"]:
                recommendations.append("Output directory does not exist and should be created")

            stats["system_impact"]["recommended_adjustments"] = recommendations

            # Add validation status
            is_valid, validation_error = validate_timing_config(config)
            stats["validation_status"] = {
                "valid": is_valid,
                "error": validation_error if not is_valid else None,
            }

            return stats

        except Exception as e:
            return {"error": f"Failed to get timing statistics: {str(e)}"}

    def validate_timing_settings(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Enhanced validation for timing settings without saving.

        Args:
            data: Timing configuration data to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str, validation_details: dict)
        """
        validation_details = {
            "basic_validation": "pending",
            "business_rules": "pending",
            "field_checks": {},
            "performance_analysis": {},
            "recommendations": [],
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

            # Enhanced field-by-field validation details
            integer_fields = [
                "min_packing_time",
                "max_packing_time",
                "video_buffer",
                "storage_duration",
                "frame_rate",
                "frame_interval",
            ]

            for field in integer_fields:
                if field in data:
                    value = data[field]
                    validation_details["field_checks"][field] = {
                        "value": value,
                        "type": type(value).__name__,
                        "valid": isinstance(value, int) and value > 0,
                        "range_check": self._check_field_range(field, value),
                    }

            # Performance analysis
            frame_rate = data.get("frame_rate", 30)
            frame_interval = data.get("frame_interval", 5)
            if frame_rate and frame_interval:
                processing_fps = frame_rate / max(1, frame_interval)
                validation_details["performance_analysis"] = {
                    "processing_fps": round(processing_fps, 2),
                    "processing_load_percent": round((processing_fps / frame_rate) * 100, 2),
                    "performance_level": self._categorize_performance(processing_fps, frame_rate),
                }

                # Add performance-based recommendations
                if processing_fps > 50:
                    validation_details["recommendations"].append(
                        "High processing load - consider increasing frame interval"
                    )
                elif processing_fps < 5:
                    validation_details["recommendations"].append(
                        "Low processing rate - consider decreasing frame interval for better accuracy"
                    )

            # Path validation details
            output_path = data.get("output_path")
            if output_path:
                path_valid, path_error = validate_output_path(output_path, create_if_missing=False)
                validation_details["path_validation"] = {
                    "valid": path_valid,
                    "error": path_error if not path_valid else None,
                    "exists": (
                        os.path.exists(output_path) if isinstance(output_path, str) else False
                    ),
                }

            return True, "All validations passed", validation_details

        except Exception as e:
            validation_details["exception"] = str(e)
            return False, f"Validation error: {str(e)}", validation_details

    def _check_field_range(self, field: str, value: Any) -> Dict[str, Any]:
        """Helper method to check if field value is in valid range."""
        ranges = {
            "min_packing_time": (1, 300),
            "max_packing_time": (10, 600),
            "video_buffer": (0, 60),
            "storage_duration": (1, 365),
            "frame_rate": (1, 120),
            "frame_interval": (1, 60),
        }

        if field in ranges and isinstance(value, int):
            min_val, max_val = ranges[field]
            return {
                "in_range": min_val <= value <= max_val,
                "min": min_val,
                "max": max_val,
                "value": value,
            }

        return {"in_range": False, "error": "Unknown field or invalid type"}

    def _categorize_performance(self, processing_fps: float, frame_rate: int) -> str:
        """Helper method to categorize performance level."""
        load_percent = (processing_fps / frame_rate) * 100

        if load_percent < 25:
            return "low_load"
        elif load_percent < 50:
            return "balanced"
        elif load_percent < 75:
            return "high_accuracy"
        else:
            return "maximum_accuracy"

    def create_output_directory(self, output_path: str) -> Tuple[bool, str]:
        """
        Create output directory with proper permissions.

        Args:
            output_path: Path to create

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Sanitize path
            clean_path = sanitize_input(output_path, 500)

            # Validate before creation
            if not clean_path:
                return False, "Output path cannot be empty"

            # Create directory
            os.makedirs(clean_path, exist_ok=True)

            # Verify creation and permissions
            path_valid, path_error = validate_output_path(clean_path, create_if_missing=False)
            if not path_valid:
                return False, path_error

            return True, f"Output directory created successfully: {clean_path}"

        except Exception as e:
            return False, f"Failed to create output directory: {str(e)}"


# Create singleton instance for import
step5_timing_service = Step5TimingService()
