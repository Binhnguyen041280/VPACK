# backend/modules/payments/payment_routes.py
"""
V_Track Payment Routes - CloudFunction Integration Blueprint
Handles all payment-related API endpoints
"""

from flask import Blueprint, request, jsonify
import logging
from .cloud_function_client import get_cloud_client

logger = logging.getLogger(__name__)

# Create payment blueprint
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

@payment_bp.route('/create', methods=['POST'])
def create_payment():
    """Create payment via CloudFunction"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['customer_email', 'package_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create payment using CloudFunction client
        cloud_client = get_cloud_client()
        result = cloud_client.create_payment(data)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'payment_url': result['data'].get('payment_url'),
                'order_code': result['data'].get('order_code'),
                'amount': result['data'].get('amount')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Payment creation failed')
            }), 400
            
    except Exception as e:
        logger.error(f"Payment creation failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@payment_bp.route('/packages', methods=['GET'])
def get_packages():
    """Get available payment packages - Testing pricing"""
    try:
        # Testing packages with scaled pricing (÷100)
        packages = {
            'personal_1m': {
                'name': 'Personal Monthly',
                'price': 2000,  # 2k VND for testing
                'duration_days': 30,
                'features': ['Unlimited cameras', 'Basic analytics', 'Email support'],
                'description': 'Gói cá nhân cho hộ gia đình'
            },
            'personal_1y': {
                'name': 'Personal Annual',
                'price': 20000,  # 20k VND for testing (save 16%)
                'duration_days': 365,
                'features': ['Unlimited cameras', 'Advanced analytics', 'Priority support'],
                'description': 'Gói cá nhân tiết kiệm (Save 16%)'
            },
            'business_1m': {
                'name': 'Business Monthly',
                'price': 5000,  # 5k VND for testing
                'duration_days': 30,
                'features': ['Multi-location support', 'Advanced analytics', 'API access', 'Priority support'],
                'description': 'Gói doanh nghiệp cho văn phòng'
            },
            'business_1y': {
                'name': 'Business Annual',
                'price': 50000,  # 50k VND for testing (save 16%)
                'duration_days': 365,
                'features': ['Multi-location support', 'Advanced analytics', 'API access', 'Dedicated support'],
                'description': 'Gói doanh nghiệp tiết kiệm (Save 16%)'
            }
        }
        
        return jsonify({
            'success': True,
            'packages': packages
        })
        
    except Exception as e:
        logger.error(f"Error fetching packages: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@payment_bp.route('/validate-license', methods=['POST'])
def validate_license():
    """Validate license via CloudFunction"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        
        if not license_key:
            return jsonify({
                'success': False,
                'error': 'Missing license_key'
            }), 400
        
        # Get cloud client and validate license
        cloud_client = get_cloud_client()
        result = cloud_client.validate_license(license_key)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"License validation failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@payment_bp.route('/licenses/<customer_email>', methods=['GET'])
def get_user_licenses(customer_email):
    """Get user licenses via CloudFunction"""
    try:
        # Get cloud client and fetch licenses
        cloud_client = get_cloud_client()
        result = cloud_client.get_user_licenses(customer_email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"License retrieval failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@payment_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for payment services"""
    try:
        cloud_client = get_cloud_client()
        result = cloud_client.health_check()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500