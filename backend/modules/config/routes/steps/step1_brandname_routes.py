"""
Step 1 Brandname Configuration Routes for V.PACK.

RESTful endpoints for managing brandname configuration with change detection
and validation. Part of the modular step-based configuration system.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from ...services.step1_brandname_service import step1_brandname_service
from ...shared import (
    format_step_response,
    handle_database_error,
    handle_validation_error,
    handle_general_error,
    create_success_response,
    create_error_response,
    validate_request_data,
    log_step_operation
)


# Create blueprint for Step 1 routes
step1_bp = Blueprint('step1_brandname', __name__, url_prefix='/step')


@step1_bp.route('/brandname', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_brandname():
    """
    Get current brandname configuration for Step 1.
    
    Returns:
        JSON response with current brandname data
    """
    try:
        log_step_operation("1", "GET brandname request")
        
        # Get brandname data from service
        result = step1_brandname_service.get_current_brandname()
        
        if "error" in result:
            # Service returned error but with fallback data
            response_data = {
                "brand_name": result["brand_name"]
            }
            response = create_success_response(response_data, "Brandname retrieved with fallback")
            response["warning"] = result["error"]
        else:
            response_data = {
                "brand_name": result["brand_name"]
            }
            response = create_success_response(response_data, "Brandname retrieved successfully")
        
        log_step_operation("1", "GET brandname success", response_data)
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "get brandname", "step1")
        return jsonify(error_response), status_code


@step1_bp.route('/brandname', methods=['PUT'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def update_step_brandname():
    """
    Update brandname configuration for Step 1.
    Only updates if the value has actually changed.
    
    Request Body:
        {
            "brand_name": "string" (required)
        }
    
    Returns:
        JSON response with update result and change status
    """
    try:
        log_step_operation("1", "PUT brandname request")
        
        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=['brand_name'])
        if not is_valid:
            error_response = create_error_response(error_msg, "step1", "brand_name")
            return jsonify(error_response), 400
        
        new_brand_name = data['brand_name']
        
        # Update brandname via service
        success, result = step1_brandname_service.update_brandname_if_changed(new_brand_name)
        
        if not success:
            # Service returned validation or database error
            if "error" in result:
                error_response = create_error_response(result["error"], "step1", "brand_name")
                return jsonify(error_response), 400
        
        # Format successful response
        response_data = {
            "brand_name": result["brand_name"],
            "changed": result["changed"]
        }
        
        response = create_success_response(
            response_data, 
            result.get("message", "Brandname operation completed"),
            changed=result["changed"]
        )
        
        log_step_operation("1", "PUT brandname success", response_data)
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "update brandname", "step1")
        return jsonify(error_response), status_code


@step1_bp.route('/brandname/validate', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def validate_step_brandname():
    """
    Validate brandname without saving.
    Useful for real-time validation in frontend forms.
    
    Request Body:
        {
            "brand_name": "string" (required)
        }
    
    Returns:
        JSON response with validation result
    """
    try:
        log_step_operation("1", "POST brandname validate request")
        
        # Validate request data
        data = request.json
        is_valid, error_msg = validate_request_data(data, required_fields=['brand_name'])
        if not is_valid:
            error_response = create_error_response(error_msg, "step1", "brand_name")
            return jsonify(error_response), 400
        
        brand_name = data['brand_name']
        
        # Validate via service
        is_valid, validation_message = step1_brandname_service.validate_brandname(brand_name)
        
        if is_valid:
            response = {
                "success": True,
                "valid": True,
                "message": "Brand name is valid",
                "data": {
                    "brand_name": brand_name,
                    "character_count": len(brand_name)
                }
            }
            status_code = 200
        else:
            response = {
                "success": True,
                "valid": False,
                "error": validation_message,
                "data": {
                    "brand_name": brand_name
                }
            }
            status_code = 200  # 200 for validation endpoint, even with invalid data
        
        log_step_operation("1", "POST brandname validate", {"valid": is_valid})
        return jsonify(response), status_code
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "validate brandname", "step1")
        return jsonify(error_response), status_code


@step1_bp.route('/brandname/statistics', methods=['GET'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def get_step_brandname_statistics():
    """
    Get brandname configuration statistics.
    Useful for monitoring and debugging.
    
    Returns:
        JSON response with brandname statistics
    """
    try:
        log_step_operation("1", "GET brandname statistics request")
        
        # Get statistics from service
        stats = step1_brandname_service.get_brandname_statistics()
        
        if "error" in stats:
            error_response = create_error_response(stats["error"], "step1")
            return jsonify(error_response), 500
        
        response = create_success_response(stats, "Statistics retrieved successfully")
        
        log_step_operation("1", "GET brandname statistics success")
        return jsonify(response), 200
        
    except Exception as e:
        error_response, status_code = handle_general_error(e, "get brandname statistics", "step1")
        return jsonify(error_response), status_code