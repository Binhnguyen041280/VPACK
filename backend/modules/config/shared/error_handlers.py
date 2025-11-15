"""
Shared error handling utilities for V.PACK config routes.

Provides consistent error response formatting and logging
for the step-based configuration system.
"""

import traceback
from typing import Any, Dict, Optional, Tuple

from flask import jsonify


def format_step_response(
    success: bool,
    data: Optional[Dict[str, Any]] = None,
    message: str = "",
    error: str = "",
    step_name: str = "",
) -> Tuple[Dict[str, Any], int]:
    """
    Format consistent response for step endpoints.

    Args:
        success: Whether the operation was successful
        data: Response data (for success cases)
        message: Success message
        error: Error message (for error cases)
        step_name: Name of the step for context

    Returns:
        Tuple of (response_dict, status_code)
    """
    if success:
        response = {"success": True}
        if data is not None:
            response["data"] = data
        if message:
            response["message"] = message
        return response, 200
    else:
        response = {"success": False, "error": error}
        if step_name:
            response["step"] = step_name
        return response, 400


def handle_database_error(
    error: Exception, operation: str = "database operation"
) -> Tuple[Dict[str, Any], int]:
    """
    Handle database errors with consistent logging and response format.

    Args:
        error: Exception that occurred
        operation: Description of the operation that failed

    Returns:
        Tuple of (error_response_dict, status_code)
    """
    error_msg = f"Database error during {operation}: {str(error)}"
    print(f"❌ {error_msg}")

    # Log full traceback for debugging
    if hasattr(error, "__traceback__"):
        traceback.print_exc()

    return {
        "success": False,
        "error": f"Database operation failed: {str(error)}",
        "operation": operation,
    }, 500


def handle_validation_error(
    error_message: str, field: str = "", step_name: str = ""
) -> Tuple[Dict[str, Any], int]:
    """
    Handle validation errors with consistent response format.

    Args:
        error_message: Validation error message
        field: Name of the field that failed validation
        step_name: Name of the step for context

    Returns:
        Tuple of (error_response_dict, status_code)
    """
    response = {"success": False, "error": error_message, "error_type": "validation_error"}

    if field:
        response["field"] = field
    if step_name:
        response["step"] = step_name

    print(f"⚠️ Validation error in {step_name or 'config'}: {error_message}")

    return response, 400


def handle_general_error(
    error: Exception, operation: str = "operation", step_name: str = ""
) -> Tuple[Dict[str, Any], int]:
    """
    Handle general application errors with consistent logging and response format.

    Args:
        error: Exception that occurred
        operation: Description of the operation that failed
        step_name: Name of the step for context

    Returns:
        Tuple of (error_response_dict, status_code)
    """
    error_msg = f"Error during {operation}: {str(error)}"
    print(f"❌ {error_msg}")

    # Log full traceback for debugging
    traceback.print_exc()

    response = {"success": False, "error": str(error), "operation": operation}

    if step_name:
        response["step"] = step_name

    return response, 500


def handle_compatibility_error(
    error: Exception, fallback_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle backward compatibility errors gracefully.

    Args:
        error: Compatibility error that occurred
        fallback_data: Fallback data to use if available

    Returns:
        Dict with compatibility error information
    """
    error_info = {"compatibility_error": str(error), "error_type": "backward_compatibility"}

    if fallback_data:
        error_info["fallback_used"] = True
        error_info["fallback_data"] = fallback_data

    print(f"⚠️ Backward compatibility warning: {str(error)}")

    return error_info


def log_step_operation(
    step_name: str, operation: str, data: Optional[Dict[str, Any]] = None, success: bool = True
):
    """
    Log step operations for debugging and monitoring.

    Args:
        step_name: Name of the step
        operation: Operation being performed
        data: Optional data related to the operation
        success: Whether the operation was successful
    """
    status_icon = "✅" if success else "❌"
    print(f"{status_icon} Step {step_name} - {operation}")

    if data and isinstance(data, dict):
        # Log key information without overwhelming detail
        if "changed" in data:
            print(f"   Changes detected: {data['changed']}")
        if "error" in data:
            print(f"   Error: {data['error']}")
        if len(str(data)) < 200:  # Only log small data objects
            print(f"   Data: {data}")


def create_success_response(
    data: Dict[str, Any], message: str = "", changed: bool = True
) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Success message
        changed: Whether data was changed

    Returns:
        Formatted success response
    """
    response = {"success": True, "data": {**data, "changed": changed}}

    if message:
        response["message"] = message
    elif changed:
        response["message"] = "Configuration updated successfully"
    else:
        response["message"] = "No changes detected"

    return response


def create_error_response(error_msg: str, step_name: str = "", field: str = "") -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        error_msg: Error message
        step_name: Name of the step for context
        field: Name of the field that caused error

    Returns:
        Formatted error response
    """
    response = {"success": False, "error": error_msg}

    if step_name:
        response["step"] = step_name
    if field:
        response["field"] = field

    return response


def validate_request_data(data: Any, required_fields: list = None) -> Tuple[bool, str]:
    """
    Basic request data validation.

    Args:
        data: Request data to validate
        required_fields: List of required fields

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not data:
        return False, "Request data is required"

    if not isinstance(data, dict):
        return False, "Request data must be a JSON object"

    if required_fields:
        for field in required_fields:
            if field not in data:
                return False, f"Field '{field}' is required"
            if data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                return False, f"Field '{field}' cannot be empty"

    return True, ""
