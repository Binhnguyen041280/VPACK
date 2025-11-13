"""
Shared utilities for V.PACK config routes.

This package provides common functionality used across all step-based configuration routes,
including database operations, validation, and error handling.
"""

from .db_operations import (
    safe_connection_wrapper,
    execute_with_change_detection,
    sync_processing_config,
    validate_table_exists,
    ensure_column_exists,
)

from .validation import (
    validate_required_fields,
    validate_time_format,
    validate_brand_name,
    validate_working_days,
    validate_video_source_config,
    validate_packing_area_config,
    validate_timing_config,
    validate_output_path,
    sanitize_input,
)

from .error_handlers import (
    format_step_response,
    handle_database_error,
    handle_validation_error,
    handle_general_error,
    create_success_response,
    create_error_response,
    log_step_operation,
    validate_request_data,
)

__all__ = [
    # Database operations
    "safe_connection_wrapper",
    "execute_with_change_detection",
    "sync_processing_config",
    "validate_table_exists",
    "ensure_column_exists",
    # Validation functions
    "validate_required_fields",
    "validate_time_format",
    "validate_brand_name",
    "validate_working_days",
    "validate_video_source_config",
    "validate_packing_area_config",
    "validate_timing_config",
    "validate_output_path",
    "sanitize_input",
    # Error handling
    "format_step_response",
    "handle_database_error",
    "handle_validation_error",
    "handle_general_error",
    "create_success_response",
    "create_error_response",
    "log_step_operation",
    "validate_request_data",
]
