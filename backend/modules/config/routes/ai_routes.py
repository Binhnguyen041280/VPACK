"""
AI Configuration Routes for V.PACK
RESTful endpoints for AI configuration, API key testing, and usage stats
Follows pattern from step1_brandname_routes.py
"""

from flask import Blueprint, jsonify, request, session
from flask_cors import cross_origin

from ..services.ai_service import AIService
from ..shared import (
    create_error_response,
    create_success_response,
    handle_general_error,
    log_step_operation,
    validate_request_data,
)

# Create blueprint for AI routes
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.route("/config", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_ai_config():
    """
    Get AI configuration for current user

    Returns:
        JSON response with current AI config
    """
    try:
        # Get user from session (reuse session pattern)
        user_email = session.get("user_email", "guest@vpack.local")

        log_step_operation("AI", f"GET config request from {user_email}")

        # Get config from service
        config = AIService.get_ai_config(user_email)

        if "error" in config:
            response = create_success_response(config, "Config retrieved with fallback")
            response["warning"] = config["error"]
        else:
            response = create_success_response(config, "Config retrieved successfully")

        log_step_operation("AI", "GET config success", config)
        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get AI config", "ai")
        return jsonify(error_response), status_code


@ai_bp.route("/config", methods=["POST"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def update_ai_config():
    """
    Update AI configuration

    Request Body:
        {
            "ai_enabled": bool (required),
            "api_provider": str (required, 'claude' or 'openai'),
            "customer_api_key": str (optional)
        }

    Returns:
        JSON response with update result
    """
    try:
        user_email = session.get("user_email", "guest@vpack.local")

        log_step_operation("AI", f"POST config request from {user_email}")

        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(
            data, required_fields=["ai_enabled", "api_provider"]
        )
        if not is_valid:
            error_response = create_error_response(error_msg, "ai", "config")
            return jsonify(error_response), 400

        ai_enabled = data["ai_enabled"]
        api_provider = data["api_provider"]
        api_key = data.get("customer_api_key", "")

        # Validate provider
        if api_provider not in ["claude", "openai"]:
            error_response = create_error_response(
                "Invalid provider. Must be 'claude' or 'openai'", "ai", "api_provider"
            )
            return jsonify(error_response), 400

        # Update config via service
        success, result = AIService.update_ai_config(user_email, ai_enabled, api_provider, api_key)

        if not success:
            error_response = create_error_response(
                result.get("error", "Update failed"), "ai", "config"
            )
            return jsonify(error_response), 400

        response = create_success_response(result, "Configuration updated successfully")

        log_step_operation("AI", "POST config success", result)
        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "update AI config", "ai")
        return jsonify(error_response), status_code


@ai_bp.route("/test", methods=["POST"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def test_api_key():
    """
    Test API key validity with actual provider API call

    Request Body:
        {
            "api_key": str (required),
            "provider": str (required, 'claude' or 'openai')
        }

    Returns:
        JSON response with test result
    """
    try:
        user_email = session.get("user_email", "guest@vpack.local")

        log_step_operation("AI", f"POST test API key request from {user_email}")

        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=["api_key", "provider"])
        if not is_valid:
            error_response = create_error_response(error_msg, "ai", "test")
            return jsonify(error_response), 400

        api_key = data["api_key"]
        provider = data["provider"]

        # Validate provider
        if provider not in ["claude", "openai"]:
            error_response = create_error_response(
                "Invalid provider. Must be 'claude' or 'openai'", "ai", "provider"
            )
            return jsonify(error_response), 400

        # Test API key via service
        if provider == "claude":
            success, message = AIService.test_claude_key(api_key)
        else:  # openai
            success, message = AIService.test_openai_key(api_key)

        if success:
            response = create_success_response({"provider": provider, "valid": True}, message)
            log_step_operation("AI", f"API key test success for {provider}")
            return jsonify(response), 200
        else:
            error_response = create_error_response(message, "ai", "api_key")
            log_step_operation("AI", f"API key test failed for {provider}: {message}")
            return jsonify(error_response), 401

    except Exception as e:
        error_response, status_code = handle_general_error(e, "test API key", "ai")
        return jsonify(error_response), status_code


@ai_bp.route("/stats", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_ai_stats():
    """
    Get AI usage statistics for current user

    Returns:
        JSON response with usage stats
    """
    try:
        user_email = session.get("user_email", "guest@vpack.local")

        log_step_operation("AI", f"GET stats request from {user_email}")

        # Get stats from service
        stats = AIService.get_usage_stats(user_email)

        if "error" in stats:
            response = create_success_response(stats, "Stats retrieved with fallback")
            response["warning"] = stats["error"]
        else:
            response = create_success_response(stats, "Stats retrieved successfully")

        log_step_operation("AI", "GET stats success")
        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get AI stats", "ai")
        return jsonify(error_response), status_code


@ai_bp.route("/recovery-logs", methods=["GET"])
@cross_origin(origins=["http://localhost:3000"], supports_credentials=True)
def get_recovery_logs():
    """
    Get recent AI recovery logs

    Query Parameters:
        limit: int (optional, default=50)

    Returns:
        JSON response with recovery logs
    """
    try:
        user_email = session.get("user_email", "guest@vpack.local")
        limit = request.args.get("limit", 50, type=int)

        log_step_operation("AI", f"GET recovery logs request from {user_email}, limit={limit}")

        # Get logs from service
        logs = AIService.get_recovery_logs(user_email, limit)

        response = create_success_response(
            {"logs": logs, "count": len(logs)}, f"Retrieved {len(logs)} recovery logs"
        )

        log_step_operation("AI", f"GET recovery logs success, count={len(logs)}")
        return jsonify(response), 200

    except Exception as e:
        error_response, status_code = handle_general_error(e, "get recovery logs", "ai")
        return jsonify(error_response), status_code
