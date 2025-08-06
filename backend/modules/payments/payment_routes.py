# backend/modules/payments/payment_routes.py
"""
V_Track Payment Routes - CloudFunction Integration Blueprint
Handles all payment-related API endpoints
"""

from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime
from .cloud_function_client import get_cloud_client

def is_obviously_invalid_license(license_key: str) -> bool:
    """Reject obviously invalid license keys"""
    invalid_patterns = ['INVALID-', 'invalid', 'test', 'fake', 'demo']
    return any(license_key.upper().startswith(pattern.upper()) for pattern in invalid_patterns)

# Import database utilities
try:
    from modules.db_utils import get_db_connection
except ImportError:
    # Fallback import path
    from backend.modules.db_utils import get_db_connection

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

@payment_bp.route('/activate-license', methods=['POST'])
def activate_license():
    """Activate license and save to local database"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        
        if not license_key:
            return jsonify({
                'success': False,
                'error': 'Missing license_key'
            }), 400
        # Pre-validation: Reject obviously invalid keys
        if is_obviously_invalid_license(license_key):
            return jsonify({
                'success': False,
                'valid': False,
                'error': 'Invalid license key format'
            })
        # Step 1: Validate license via CloudFunction
        cloud_client = get_cloud_client()
        validation_result = cloud_client.validate_license(license_key)
        
        # FIXED: Separate validation checks for better error handling
        if not validation_result.get('success'):
            return jsonify({
                'success': False,
                'valid': False,
                'error': validation_result.get('error', 'License validation failed')
            })

        if not validation_result.get('valid'):
            return jsonify({
                'success': False,  
                'valid': False,
                'error': 'Invalid or expired license key'
            })
        
        # Step 2: Save license to local database
        license_data = validation_result.get('data', {})
        
        # Import license models
        try:
            from modules.licensing.license_models import License, init_license_db
        except ImportError:
            from backend.modules.licensing.license_models import License, init_license_db
        
        # Initialize license database if not exists
        init_license_db()
        
        # Check if license already activated locally
        existing_license = License.get_by_key(license_key)
        if existing_license and existing_license.get('id'):
            return jsonify({
                'success': True,
                'valid': True,
                'data': {
                    'license_key': license_key,
                    'customer_email': existing_license.get('customer_email', 'unknown'),
                    'package_name': existing_license.get('product_type', 'desktop'),
                    'expires_at': existing_license.get('expires_at'),
                    'status': 'already_activated'
                }
            })
        
        # Create new license record
        license_id = License.create(
            license_key=license_key,
            customer_email=license_data.get('customer_email', 'unknown@email.com'),
            payment_transaction_id=None,  # No local payment transaction
            product_type=license_data.get('product_type', 'desktop'),
            features=license_data.get('features', ['full_access']),
            expires_days=365  # Default 1 year
        )
        
        if license_id:
            # Get the created license for response
            created_license = License.get_by_key(license_key)
            
            logger.info(f"✅ License {license_key[:12]}... activated locally")
            
            features_list = []
            if created_license and created_license.get('features'):
                try:
                    features_list = json.loads(created_license.get('features', '[]'))
                except (json.JSONDecodeError, TypeError):
                    features_list = ['full_access']
            
            return jsonify({
                'success': True,
                'valid': True,
                'data': {
                    'license_key': license_key,
                    'customer_email': created_license.get('customer_email', 'unknown') if created_license else 'unknown',
                    'package_name': created_license.get('product_type', 'desktop') if created_license else 'desktop',
                    'expires_at': created_license.get('expires_at') if created_license else None,
                    'status': 'activated',
                    'features': features_list
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save license to local database'
            }), 500
            
    except Exception as e:
        logger.error(f"License activation failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@payment_bp.route('/license-status', methods=['GET'])
def get_license_status():
    """Get current active license status from local database"""
    try:
        # Import license models
        try:
            from modules.licensing.license_models import License
        except ImportError:
            from backend.modules.licensing.license_models import License
        
        # Get all active licenses from local database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM licenses 
                WHERE status = 'active' 
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                LIMIT 1
            """, (datetime.now(),))
            
            license_row = cursor.fetchone()
            
            if license_row:
                # Get column names
                cursor.execute("PRAGMA table_info(licenses)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Convert to dict
                license_data = dict(zip(columns, license_row))
                
                # Parse features safely
                features_list = []
                if license_data.get('features'):
                    try:
                        features_list = json.loads(license_data.get('features', '[]'))
                    except (json.JSONDecodeError, TypeError):
                        features_list = ['full_access']
                
                return jsonify({
                    'success': True,
                    'license': {
                        'license_key': license_data.get('license_key', ''),
                        'customer_email': license_data.get('customer_email', ''),
                        'package_name': license_data.get('product_type', 'desktop'),
                        'expires_at': license_data.get('expires_at'),
                        'status': license_data.get('status', 'active'),
                        'features': features_list,
                        'activated_at': license_data.get('activated_at')
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'license': None,
                    'message': 'No active license found'
                })
                
    except Exception as e:
        logger.error(f"License status check failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500