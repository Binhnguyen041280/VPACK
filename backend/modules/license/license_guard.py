# backend/modules/license/license_guard.py
"""
License Guard Decorator - Simple Trace Page Protection
Created: 2025-10-09
Purpose: Lock Trace features when license is expired or missing
Strategy: Focus on realistic attacks (dropped tables), not expert-level hacks
"""

import logging
from functools import wraps
from flask import jsonify
from typing import Callable, Any
from .license_manager import LicenseManager

logger = logging.getLogger(__name__)


def require_valid_license(f: Callable) -> Callable:
    """
    Decorator to protect API endpoints requiring valid license

    Usage:
        @app.route('/api/query', methods=['POST'])
        @require_valid_license
        def query_handler():
            # Protected endpoint logic
            pass

    Protection Strategy (Simplified):
        1. Check if licenses table exists (detect DROP TABLE attack)
        2. Check if license exists in database
        3. Check if license is valid (not expired)
        4. Block if any check fails

    Returns:
        - 403 Forbidden if license invalid with upgrade message
        - Original function result if license valid
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        try:
            # Get license manager
            license_manager = LicenseManager()

            # Get license status using existing unified method
            status_result = license_manager.get_license_status()

            # Check status
            if status_result["status"] == "valid":
                # License is valid - allow access
                logger.debug(f"✅ ALLOWED: {f.__name__} | Valid license")
                return f(*args, **kwargs)

            # License is invalid - block access
            reason = status_result.get("reason", "unknown")
            message = _get_friendly_message(status_result)

            logger.warning(
                f"🔒 BLOCKED: {f.__name__} | Status: {status_result['status']} | Reason: {reason}"
            )

            return (
                jsonify(
                    {
                        "success": False,
                        "error": "license_required",
                        "message": message,
                        "status": status_result["status"],
                        "reason": reason,
                        "upgrade_url": "/plan",
                        "blocked_endpoint": f.__name__,
                    }
                ),
                403,
            )

        except Exception as e:
            # Fail-safe: Block on error
            logger.error(f"🔒 BLOCKED: {f.__name__} | Guard error: {str(e)}")

            return (
                jsonify(
                    {
                        "success": False,
                        "error": "license_check_failed",
                        "message": "Unable to verify license. Please check your license status.",
                        "upgrade_url": "/plan",
                        "blocked_endpoint": f.__name__,
                    }
                ),
                403,
            )

    return decorated_function


def _get_friendly_message(status_result: dict) -> str:
    """
    Get user-friendly message based on license status

    Args:
        status_result: Result from LicenseManager.get_license_status()

    Returns:
        User-friendly error message
    """
    status = status_result.get("status", "unknown")
    reason = status_result.get("reason", "")

    # Map status to friendly messages
    messages = {
        "no_license": "No license found. Please activate a license to use Trace features.",
        "invalid": "Your license is invalid or expired. Please activate a valid license to continue using Trace features.",
        "error": "Unable to verify your license. Please contact support if this issue persists.",
    }

    # Check for specific reasons
    if reason == "expired":
        license_data = status_result.get("license", {})
        expiry_date = license_data.get("expires_at", "unknown")
        return f"Your license expired on {expiry_date}. Please activate a valid license to continue using Trace features."

    # Return mapped message or default
    return messages.get(
        status, "License verification failed. Please check your license status in Plan page."
    )


def check_license_status() -> dict:
    """
    Utility function to check license status without decorator

    Usage:
        status = check_license_status()
        if status['valid']:
            # Proceed with operation
        else:
            # Show upgrade prompt

    Returns:
        dict: {
            'valid': bool,
            'status': str,
            'message': str,
            'license': dict (optional)
        }
    """
    try:
        license_manager = LicenseManager()
        status_result = license_manager.get_license_status()

        return {
            "valid": status_result["status"] == "valid",
            "status": status_result["status"],
            "message": _get_friendly_message(status_result),
            "license": status_result.get("license"),
        }

    except Exception as e:
        logger.error(f"License status check failed: {str(e)}")
        return {
            "valid": False,
            "status": "error",
            "message": "Unable to verify license status",
            "error": str(e),
        }


# Optional: Feature-level protection for future use
def require_license_feature(feature_name: str) -> Callable:
    """
    Decorator to protect endpoints requiring specific license feature

    Usage:
        @require_license_feature('advanced_analytics')
        def advanced_query():
            pass

    Note: Currently simplified - checks valid license only
    Future: Can check specific features list
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            try:
                license_manager = LicenseManager()
                status_result = license_manager.get_license_status()

                if status_result["status"] != "valid":
                    logger.warning(
                        f"🔒 BLOCKED: {f.__name__} | Feature: {feature_name} | No valid license"
                    )
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "feature_requires_license",
                                "message": f'Feature "{feature_name}" requires a valid license.',
                                "feature": feature_name,
                                "upgrade_url": "/account#plans",
                            }
                        ),
                        403,
                    )

                # Future: Check if license includes specific feature
                # features = license_manager.get_license_features()
                # if feature_name not in features:
                #     return jsonify({'error': 'feature_not_included'}), 403

                logger.debug(f"✅ ALLOWED: {f.__name__} | Feature: {feature_name}")
                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"🔒 BLOCKED: {f.__name__} | Feature guard error: {str(e)}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "feature_check_failed",
                            "message": "Unable to verify license features.",
                            "feature": feature_name,
                        }
                    ),
                    403,
                )

        return decorated_function

    return decorator


if __name__ == "__main__":
    print("🧪 Testing license_guard...")

    # Test status check
    status = check_license_status()
    print(f"License status: {status}")

    print("✅ license_guard module loaded successfully")
