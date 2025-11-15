"""
Step 2 Location/Time Configuration Routes for V.PACK.

RESTful endpoints for managing location and time configuration with
enhanced timezone validation and working days management.
FIXED: Removes Vietnamese day name conversion bug.
"""

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin

from ...services.step2_location_time_service import step2_location_time_service
from ...shared import (
    create_error_response,
    create_success_response,
    format_step_response,
    handle_database_error,
    handle_general_error,
    handle_validation_error,
    log_step_operation,
    validate_request_data,
)

# Create blueprint for Step 2 routes
step2_bp = Blueprint("step2_location_time", __name__, url_prefix="/step")


@step2_bp.route("/location-time", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_step_location_time():
    """
    Get current location/time configuration for Step 2.
    Includes enhanced timezone data when available.

    Returns:
        JSON response with current location/time configuration
    """
    try:
        log_step_operation("2", "GET location-time request")

        # Get configuration from service
        config = step2_location_time_service.get_location_time_config()

        if "error" in config:
            # Service returned error but with fallback data
            response_data = {k: v for k, v in config.items() if k != "error"}
            response = create_success_response(
                response_data, "Configuration retrieved with fallback"
            )
            response["warning"] = config["error"]
        else:
            response = create_success_response(
                config, "Location/time configuration retrieved successfully"
            )

        log_step_operation(
            "2",
            "GET location-time success",
            {
                "country": config.get("country"),
                "timezone": config.get("timezone"),
                "working_days_count": len(config.get("working_days", [])),
                "enhanced_timezone": "timezone_enhanced" in config,
            },
        )

        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get location-time", "step2")
        return jsonify(error_response), status_code


@step2_bp.route("/location-time", methods=["PUT"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def update_step_location_time():
    """
    Update location/time configuration for Step 2.
    Only updates if values have actually changed.
    FIXED: No Vietnamese day conversion - frontend sends English directly.

    Request Body:
        {
            "country": "string" (required),
            "timezone": "string" (required),
            "language": "string" (required),
            "working_days": ["array"] (required),
            "from_time": "HH:MM" (required),
            "to_time": "HH:MM" (required)
        }

    Returns:
        JSON response with update result and change status
    """
    try:
        log_step_operation("2", "PUT location-time request")

        # Validate request data
        data = request.json
        required_fields = [
            "country",
            "timezone",
            "language",
            "working_days",
            "from_time",
            "to_time",
        ]
        is_valid, error_msg = validate_request_data(data, required_fields)
        if not is_valid:
            error_response = create_error_response(error_msg, "step2")
            return jsonify(error_response), 400

        # Update configuration via service
        success, result = step2_location_time_service.update_location_time_if_changed(data)

        if not success:
            # Service returned validation or database error
            if "error" in result:
                error_response = create_error_response(result["error"], "step2")
                return jsonify(error_response), 400

        # Format successful response
        response_data = {
            "country": result["country"],
            "timezone": result["timezone"],
            "language": result["language"],
            "working_days": result["working_days"],
            "from_time": result["from_time"],
            "to_time": result["to_time"],
            "changed": result["changed"],
        }

        # Include enhanced timezone data if available
        if "timezone_enhanced" in result:
            response_data["timezone_enhanced"] = result["timezone_enhanced"]

        response = create_success_response(
            response_data,
            result.get("message", "Location/time configuration operation completed"),
            changed=result["changed"],
        )

        log_step_operation(
            "2",
            "PUT location-time success",
            {
                "changed": result["changed"],
                "timezone": result["timezone"],
                "working_days_count": len(result["working_days"]),
            },
        )

        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "update location-time", "step2")
        return jsonify(error_response), status_code


@step2_bp.route("/location-time/validate-timezone", methods=["POST"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def validate_step_timezone():
    """
    Validate timezone without saving.
    Useful for real-time validation in frontend forms.

    Request Body:
        {
            "timezone": "string" (required)
        }

    Returns:
        JSON response with timezone validation result and enhanced data
    """
    try:
        log_step_operation("2", "POST timezone validate request")

        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=["timezone"])
        if not is_valid:
            error_response = create_error_response(error_msg, "step2", "timezone")
            return jsonify(error_response), 400

        timezone_input = data["timezone"]

        # Validate via service
        is_valid, validation_message, timezone_data = (
            step2_location_time_service.validate_timezone_enhanced(timezone_input)
        )

        if is_valid:
            response = {
                "success": True,
                "valid": True,
                "message": "Timezone is valid",
                "data": {"timezone": timezone_input, "timezone_enhanced": timezone_data},
            }
            status_code = 200
        else:
            response = {
                "success": True,
                "valid": False,
                "error": validation_message,
                "data": {"timezone": timezone_input},
            }
            status_code = 200  # 200 for validation endpoint, even with invalid data

        log_step_operation(
            "2", "POST timezone validate", {"valid": is_valid, "timezone": timezone_input}
        )
        return jsonify(response), status_code

    except Exception as e:
        error_response, status_code = handle_general_error(e, "validate timezone", "step2")
        return jsonify(error_response), status_code


@step2_bp.route("/location-time/validate-working-days", methods=["POST"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def validate_step_working_days():
    """
    Validate working days array without saving.
    FIXED: Expects English day names directly from frontend.

    Request Body:
        {
            "working_days": ["array"] (required)
        }

    Returns:
        JSON response with working days validation result
    """
    try:
        log_step_operation("2", "POST working-days validate request")

        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=["working_days"])
        if not is_valid:
            error_response = create_error_response(error_msg, "step2", "working_days")
            return jsonify(error_response), 400

        working_days = data["working_days"]

        # Import validation function directly
        from ...shared.validation import validate_working_days

        is_valid, validation_message = validate_working_days(working_days)

        if is_valid:
            response = {
                "success": True,
                "valid": True,
                "message": "Working days are valid",
                "data": {
                    "working_days": working_days,
                    "days_count": len(working_days),
                    "note": "No Vietnamese conversion needed - English days expected",
                },
            }
            status_code = 200
        else:
            response = {
                "success": True,
                "valid": False,
                "error": validation_message,
                "data": {"working_days": working_days},
            }
            status_code = 200  # 200 for validation endpoint, even with invalid data

        log_step_operation(
            "2", "POST working-days validate", {"valid": is_valid, "count": len(working_days)}
        )
        return jsonify(response), status_code

    except Exception as e:
        error_response, status_code = handle_general_error(e, "validate working days", "step2")
        return jsonify(error_response), status_code


@step2_bp.route("/location-time/defaults", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_step_location_time_defaults():
    """
    Get default values for location/time configuration.
    Useful for resetting forms or showing initial values.

    Returns:
        JSON response with default location/time values
    """
    try:
        log_step_operation("2", "GET location-time defaults request")

        defaults = {
            "country": step2_location_time_service.DEFAULT_COUNTRY,
            "timezone": step2_location_time_service.DEFAULT_TIMEZONE,
            "language": step2_location_time_service.DEFAULT_LANGUAGE,
            "working_days": step2_location_time_service.DEFAULT_WORKING_DAYS,
            "from_time": step2_location_time_service.DEFAULT_FROM_TIME,
            "to_time": step2_location_time_service.DEFAULT_TO_TIME,
        }

        response = create_success_response(defaults, "Default values retrieved successfully")

        log_step_operation("2", "GET location-time defaults success")
        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get location-time defaults", "step2")
        return jsonify(error_response), status_code
