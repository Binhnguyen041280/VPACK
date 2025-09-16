# backend/modules/payments/payment_routes.py
"""
V_Track Payment Routes - CloudFunction Integration Blueprint with Offline Fallback
Handles all payment-related API endpoints
Updated: 2025-08-11 - Enhanced offline fallback for license validation and activation
"""

from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime
from .cloud_function_client import get_cloud_client
from modules.pricing.cloud_pricing_client import get_cloud_pricing_client

def is_obviously_invalid_license(license_key: str) -> bool:
    """Reject obviously invalid license keys"""
    invalid_patterns = ['INVALID-', 'invalid', 'test', 'fake', 'demo']
    return any(license_key.upper().startswith(pattern.upper()) for pattern in invalid_patterns)

def extract_package_from_license_key(license_key: str) -> dict:
    """
    Extract package information from license key format: VTRACK-P1M-...
    Returns package type and duration based on license key pattern
    """
    try:
        # Default values
        default_package = {
            'product_type': 'desktop',
            'expires_days': 365,
            'package_name': 'Desktop Standard'
        }
        
        if not license_key or '-' not in license_key:
            return default_package
        
        parts = license_key.split('-')
        if len(parts) < 3:
            return default_package
        
        # Extract package code (e.g., P1M, P1Y, B1M, B1Y, T24H)
        package_code = parts[1] if len(parts) > 1 else ''
        
        # ✅ UPDATED: Enhanced package mapping with trial support
        package_mapping = {
            'P1M': {
                'product_type': 'personal_1m',
                'expires_days': 30,
                'package_name': 'Personal Monthly'
            },
            'P1Y': {
                'product_type': 'personal_1y', 
                'expires_days': 365,
                'package_name': 'Personal Annual'
            },
            'B1M': {
                'product_type': 'business_1m',
                'expires_days': 30,
                'package_name': 'Business Monthly'
            },
            'B1Y': {
                'product_type': 'business_1y',
                'expires_days': 365,
                'package_name': 'Business Annual'
            },
            'T24H': {  # ✅ NEW: Trial 24h package
                'product_type': 'trial_24h',
                'expires_days': 1,
                'package_name': '24 Hours Trial Extension'
            }
        }
        
        return package_mapping.get(package_code, default_package)
        
    except Exception as e:
        # Logger might not be available yet, use print as fallback
        print(f"Error extracting package from license key: {e}")
        return {
            'product_type': 'desktop',
            'expires_days': 365,
            'package_name': 'Desktop Standard'
        }

# Import database utilities
try:
    from modules.db_utils.safe_connection import safe_db_connection
except ImportError:
    # Fallback import path
    from backend.modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)

# Create payment blueprint
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

@payment_bp.route('/create', methods=['POST'])
def create_payment():
    """Create payment via CloudFunction with unified redirect URLs"""
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
        
        # ✅ NEW: Validate package_type exists in CloudFunction
        package_type = data.get('package_type')
        
        try:
            pricing_client = get_cloud_pricing_client()
            pricing_data = pricing_client.fetch_pricing_for_upgrade()
            
            if pricing_data.get('success'):
                available_packages = pricing_data.get('packages', {})
                if package_type not in available_packages:
                    logger.error(f"❌ Invalid package type: {package_type}. Available: {list(available_packages.keys())}")
                    return jsonify({
                        'success': False,
                        'error': f'Invalid package type: {package_type}',
                        'available_packages': list(available_packages.keys())
                    }), 400
                
                logger.info(f"✅ Package type validated: {package_type}")
            else:
                logger.warning(f"⚠️ Cannot validate package {package_type} - pricing service unavailable")
                # Continue without validation (fallback behavior)
                
        except Exception as validation_error:
            logger.warning(f"⚠️ Package validation failed: {str(validation_error)} - continuing anyway")
            # Continue without validation (fallback behavior)
        
        # FIXED: Ensure unified redirect URLs are set
        # This ensures both success and cancel scenarios are handled consistently
        unified_redirect_url = "http://localhost:8080/payment/redirect"
        
        # Enhanced data with unified redirect URLs
        enhanced_data = data.copy()
        enhanced_data.update({
            'return_url': unified_redirect_url,     # Success redirect
            'cancel_url': unified_redirect_url,     # Cancel redirect  
            'unified_redirect': True                # Flag for tracking
        })
        
        logger.info(f"🔄 Creating payment with unified redirects: {unified_redirect_url}")
        logger.debug(f"📤 Enhanced payment data: {enhanced_data}")
        
        # Create payment using CloudFunction client
        cloud_client = get_cloud_client()
        result = cloud_client.create_payment(enhanced_data)
        
        if result.get('success'):
            logger.info(f"✅ Payment created successfully: {result['data'].get('order_code')}")
            return jsonify({
                'success': True,
                'payment_url': result['data'].get('payment_url'),
                'order_code': result['data'].get('order_code'),
                'amount': result['data'].get('amount'),
                'redirect_urls': {
                    'success': unified_redirect_url,
                    'cancel': unified_redirect_url
                }
            })
        else:
            logger.error(f"❌ Payment creation failed: {result.get('error')}")
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
    """Get packages from CloudFunction - unified endpoint"""
    try:
        # Check if this is for upgrade action
        for_upgrade = request.args.get('for_upgrade', 'false').lower() == 'true'
        force_fresh = request.args.get('fresh', 'false').lower() == 'true'
        
        pricing_client = get_cloud_pricing_client()
        
        if for_upgrade or force_fresh:
            # User clicked upgrade or explicit fresh request
            logger.info("📦 Fetching fresh pricing for upgrade")
            pricing_data = pricing_client.fetch_pricing_for_upgrade()
        else:
            # Normal display - use cached if available
            pricing_data = pricing_client.get_cached_pricing()
            
            if not pricing_data:
                # No cache available, fetch fresh
                logger.info("📦 No cache available, fetching fresh pricing")
                pricing_data = pricing_client.fetch_pricing_for_upgrade()
        
        # Add server metadata
        pricing_data['server_timestamp'] = datetime.now().isoformat()
        pricing_data['request_type'] = 'upgrade' if for_upgrade else 'display'
        
        return jsonify(pricing_data)
        
    except Exception as e:
        logger.error(f"❌ Get packages failed: {str(e)}")
        
        # Try to return cached data as fallback
        try:
            pricing_client = get_cloud_pricing_client()
            fallback_data = pricing_client.get_cached_pricing()
            if fallback_data:
                fallback_data['fallback'] = True
                fallback_data['error'] = str(e)
                return jsonify(fallback_data)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e),
            'packages': {}
        }), 500

@payment_bp.route('/validate-license', methods=['POST'])
def validate_license():
    """
    Validate license via CloudFunction with offline fallback
    Enhanced with dual validation path and status indicators
    """
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
                'error': 'Invalid license key format',
                'source': 'local_validation'
            })
        
        logger.info(f"🔍 Validating license with dual path: {license_key[:12]}...")
        
        # Get cloud client and validate license (with automatic fallback)
        cloud_client = get_cloud_client()
        result = cloud_client.validate_license(license_key)
        
        # Enhanced response with source indication and warnings
        validation_source = result.get('source', 'unknown')
        
        if result.get('success') and result.get('valid'):
            response_data = {
                'success': True,
                'valid': True,
                'data': result.get('data', {}),
                'validation': {
                    'source': validation_source,
                    'method': 'cloud' if validation_source == 'cloud' else 'offline',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Add warning messages for offline validation
            if validation_source == 'offline':
                response_data['warning'] = {
                    'message': 'License validated offline - some features may be limited',
                    'reason': result.get('reason', 'cloud_unavailable'),
                    'recommendation': 'Please check internet connection for full validation'
                }
                logger.warning(f"⚠️ Offline validation used for {license_key[:12]}... - {result.get('reason')}")
            else:
                logger.info(f"✅ Online validation successful for {license_key[:12]}...")
            
            return jsonify(response_data)
            
        elif result.get('success') and not result.get('valid'):
            # Invalid license
            response_data = {
                'success': False,
                'valid': False,
                'error': result.get('error', 'Invalid or expired license'),
                'validation': {
                    'source': validation_source,
                    'method': 'cloud' if validation_source == 'cloud' else 'offline',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            if validation_source == 'offline':
                response_data['warning'] = {
                    'message': 'License validation performed offline',
                    'recommendation': 'Connect to internet for authoritative validation'
                }
            
            return jsonify(response_data)
            
        else:
            # Validation failed completely
            logger.error(f"❌ License validation failed completely: {result.get('error')}")
            return jsonify({
                'success': False,
                'valid': False,
                'error': result.get('error', 'License validation failed'),
                'validation': {
                    'source': 'none',
                    'method': 'failed',
                    'timestamp': datetime.now().isoformat()
                }
            }), 500
        
    except Exception as e:
        logger.error(f"License validation failed: {str(e)}")
        return jsonify({
            'success': False,
            'valid': False,
            'error': str(e),
            'validation': {
                'source': 'error',
                'method': 'exception',
                'timestamp': datetime.now().isoformat()
            }
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

@payment_bp.route('/pricing/test', methods=['GET'])
def test_pricing_connection():
    """Test connection to pricing service"""
    try:
        pricing_client = get_cloud_pricing_client()
        result = pricing_client.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'connected': False,
            'error': str(e)
        }), 500

@payment_bp.route('/activate-license', methods=['POST'])
def activate_license():
    """
    Activate license and save to local database with offline fallback
    Enhanced with database-only activation when cloud is down
    """
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
            
        logger.info(f"🔑 Activating license with fallback support: {license_key[:12]}...")
        
        # Step 1: Try cloud validation first (with automatic fallback in cloud_client)
        cloud_client = get_cloud_client()
        validation_result = cloud_client.validate_license(license_key)
        
        validation_source = validation_result.get('source', 'unknown')
        cloud_unavailable = validation_source in ['offline', 'none']
        
        # Enhanced validation checks with fallback handling
        if not validation_result.get('success'):
            error_msg = validation_result.get('error', 'License validation failed')
            
            # If cloud is completely unavailable, try database-only activation
            if cloud_unavailable:
                logger.warning(f"⚠️ Cloud unavailable, attempting database-only activation...")
                return _database_only_activation(license_key, error_msg)
            
            return jsonify({
                'success': False,
                'valid': False,
                'error': error_msg,
                'activation': {
                    'source': validation_source,
                    'method': 'cloud_validation_failed'
                }
            })

        if not validation_result.get('valid'):
            error_msg = validation_result.get('error', 'Invalid or expired license key')
            
            return jsonify({
                'success': False,
                'valid': False,
                'error': error_msg,
                'activation': {
                    'source': validation_source,
                    'method': 'license_invalid'
                }
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
        
        # Check if license already exists locally and reuse instead of creating duplicate
        existing_license = License.get_by_key(license_key)
        license_id = None
        license_record = None
        
        if existing_license and existing_license.get('id'):
            logger.info(f"📋 Reusing existing license record: {existing_license['id']}")
            license_id = existing_license['id']
            license_record = existing_license
        else:
            # Extract package info from license key format: VTRACK-P1M-...
            package_info = extract_package_from_license_key(license_key)
            
            # Create new license record with correct package data
            logger.info(f"📝 Creating new license record for key: {license_key[:12]}...")
            license_id = License.create(
                license_key=license_key,
                customer_email=license_data.get('customer_email') or 'trial@vtrack.com',
                payment_transaction_id=None,  # No local payment transaction
                product_type=package_info.get('product_type', license_data.get('product_type', 'desktop')),
                features=license_data.get('features', ['full_access']),
                expires_days=package_info.get('expires_days', 365)
            )
            
            if license_id:
                license_record = License.get_by_key(license_key)
        
        if not license_id:
            return jsonify({
                'success': False,
                'error': 'Failed to get or create license record'
            }), 500
        
        # Check activation records for this license
        from modules.license.machine_fingerprint import generate_machine_fingerprint
        current_fingerprint = generate_machine_fingerprint()
        
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT machine_fingerprint, activation_time, status 
                    FROM license_activations 
                    WHERE license_id = ? AND status = 'active'
                """, (license_id,))
                
                activations = cursor.fetchall()
                
                # Check if current machine is already activated
                for activation in activations:
                    if activation[0] == current_fingerprint:
                        logger.info(f"✅ License already activated on this machine")
                        
                        # Return existing activation info with source indication
                        features_list = []
                        if license_record and license_record.get('features'):
                            try:
                                features_list = json.loads(license_record.get('features', '[]'))
                            except (json.JSONDecodeError, TypeError):
                                features_list = ['full_access']
                        
                        response_data = {
                            'success': True,
                            'valid': True,
                            'data': {
                                'license_key': license_key,
                                'customer_email': license_record.get('customer_email', 'unknown') if license_record else 'unknown',
                                'package_name': license_record.get('product_type', 'desktop') if license_record else 'desktop',
                                'expires_at': license_record.get('expires_at') if license_record else None,
                                'status': 'already_activated_this_machine',
                                'features': features_list,
                                'machine_fingerprint': current_fingerprint[:16] + "...",
                                'activated_at': activation[1]
                            },
                            'activation': {
                                'source': validation_source,
                                'method': 'existing_activation',
                                'timestamp': datetime.now().isoformat()
                            }
                        }
                        
                        # Add offline warning if applicable
                        if cloud_unavailable:
                            response_data['warning'] = {
                                'message': 'License activated offline - sync recommended',
                                'reason': validation_result.get('reason', 'cloud_unavailable'),
                                'recommendation': 'Connect to internet to sync license status'
                            }
                        
                        return jsonify(response_data)
                
                # Check if license is activated on another machine
                if activations:
                    logger.warning(f"❌ License already activated on another device")
                    return jsonify({
                        'success': False,
                        'valid': False,
                        'error': f'License already activated on another device. Activation time: {activations[0][1]}',
                        'data': {
                            'license_key': license_key,
                            'status': 'activated_elsewhere',
                            'other_device_activated_at': activations[0][1]
                        },
                        'activation': {
                            'source': validation_source,
                            'method': 'blocked_multi_device'
                        }
                    })
                    
        except Exception as check_error:
            logger.error(f"❌ Failed to check activation records: {check_error}")
            return jsonify({
                'success': False,
                'error': f'Database error checking activation: {str(check_error)}'
            }), 500
        
        # CRITICAL: Create activation record - this MUST succeed for security
        try:
            activation_time = datetime.now().isoformat()
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO license_activations 
                    (license_id, machine_fingerprint, activation_time, status, device_info)
                    VALUES (?, ?, ?, 'active', ?)
                """, (
                    license_id, 
                    current_fingerprint, 
                    activation_time,
                    json.dumps({
                        "activated_via": "desktop_app", 
                        "timestamp": activation_time,
                        "endpoint": "/activate-license",
                        "validation_source": validation_source
                    })
                ))
                conn.commit()
                logger.info(f"✅ Activation record created for license {license_id} with fingerprint {current_fingerprint[:16]}...")
                
        except Exception as activation_error:
            logger.error(f"❌ CRITICAL: Failed to create activation record: {activation_error}")
            return jsonify({
                'success': False,
                'error': f'Failed to create activation record: {str(activation_error)}. License not activated for security reasons.'
            }), 500
        
        # SUCCESS: Activation record created successfully
        logger.info(f"✅ License {license_key[:12]}... activated successfully on this device")
        
        # Prepare features list for response
        features_list = []
        if license_record and license_record.get('features'):
            try:
                features_list = json.loads(license_record.get('features', '[]'))
            except (json.JSONDecodeError, TypeError):
                features_list = ['full_access']
        
        # Return successful activation response with enhanced metadata
        response_data = {
            'success': True,
            'valid': True,
            'data': {
                'license_key': license_key,
                'customer_email': license_record.get('customer_email', 'unknown') if license_record else 'unknown',
                'package_name': license_record.get('product_type', 'desktop') if license_record else 'desktop',
                'expires_at': license_record.get('expires_at') if license_record else None,
                'status': 'activated',
                'features': features_list,
                'machine_fingerprint': current_fingerprint[:16] + "...",
                'activated_at': activation_time
            },
            'activation': {
                'source': validation_source,
                'method': 'cloud' if validation_source == 'cloud' else 'offline',
                'timestamp': activation_time
            }
        }
        
        # Add appropriate warnings based on validation source
        if validation_source == 'offline':
            response_data['warning'] = {
                'message': 'License activated offline - some features may be limited',
                'reason': validation_result.get('reason', 'cloud_unavailable'),
                'recommendation': 'Connect to internet for full license synchronization'
            }
        elif validation_source == 'none':
            response_data['warning'] = {
                'message': 'License activated in local-only mode',
                'reason': 'Cloud validation completely unavailable',
                'recommendation': 'Ensure internet connection for cloud features'
            }
        
        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"License activation failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'activation': {
                'source': 'error',
                'method': 'exception'
            }
        }), 500

def _database_only_activation(license_key: str, original_error: str):
    """
    Database-only activation when cloud is completely unavailable
    This is a fallback method for existing licenses in local database
    """
    try:
        logger.info(f"🔄 Attempting database-only activation for {license_key[:12]}...")
        
        # Import license models
        try:
            from modules.licensing.license_models import License, init_license_db
        except ImportError:
            from backend.modules.licensing.license_models import License, init_license_db
        
        # Check if license exists in local database
        existing_license = License.get_by_key(license_key)
        
        if not existing_license:
            logger.warning(f"❌ License not found in local database: {license_key[:12]}...")
            return jsonify({
                'success': False,
                'valid': False,
                'error': f'License not found locally and cloud unavailable. Original error: {original_error}',
                'activation': {
                    'source': 'database_only',
                    'method': 'not_found'
                },
                'warning': {
                    'message': 'Cloud validation unavailable - only local database checked',
                    'recommendation': 'Connect to internet for authoritative license validation'
                }
            }), 404
        
        # Check if license is expired locally
        if existing_license.get('expires_at'):
            try:
                expiry_date = datetime.fromisoformat(existing_license['expires_at'])
                if datetime.now() > expiry_date:
                    logger.warning(f"❌ License expired locally: {existing_license['expires_at']}")
                    return jsonify({
                        'success': False,
                        'valid': False,
                        'error': f'License expired on {existing_license["expires_at"]}',
                        'activation': {
                            'source': 'database_only',
                            'method': 'expired'
                        }
                    }), 400
            except Exception as date_error:
                logger.warning(f"⚠️ Could not parse expiry date: {date_error}")
        
        # License exists and appears valid - proceed with database-only activation
        from modules.license.machine_fingerprint import generate_machine_fingerprint
        current_fingerprint = generate_machine_fingerprint()
        
        license_id = existing_license['id']
        
        # Check existing activations
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT machine_fingerprint, activation_time, status 
                FROM license_activations 
                WHERE license_id = ? AND status = 'active'
            """, (license_id,))
            
            activations = cursor.fetchall()
            
            # Check if current machine already activated
            for activation in activations:
                if activation[0] == current_fingerprint:
                    logger.info(f"✅ Database-only: License already activated on this machine")
                    
                    features_list = []
                    if existing_license.get('features'):
                        try:
                            features_list = json.loads(existing_license.get('features', '[]'))
                        except:
                            features_list = ['full_access']
                    
                    response = jsonify({
                        'success': True,
                        'valid': True,
                        'data': {
                            'license_key': license_key,
                            'customer_email': existing_license.get('customer_email', 'unknown'),
                            'package_name': existing_license.get('product_type', 'desktop'),
                            'expires_at': existing_license.get('expires_at'),
                            'status': 'already_activated_this_machine',
                            'features': features_list,
                            'machine_fingerprint': current_fingerprint[:16] + "...",
                            'activated_at': activation[1]
                        },
                        'activation': {
                            'source': 'database_only',
                            'method': 'existing_local_activation',
                            'timestamp': datetime.now().isoformat()
                        },
                        'warning': {
                            'message': 'License verified from local database only',
                            'reason': 'cloud_unavailable',
                            'recommendation': 'Connect to internet to sync with cloud services'
                        }
                    })
                    return response
            
            # Check if activated on another machine
            if activations:
                logger.warning(f"❌ Database-only: License already activated on another device")
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': f'License already activated on another device (local database). Activation time: {activations[0][1]}',
                    'activation': {
                        'source': 'database_only',
                        'method': 'blocked_multi_device'
                    }
                }), 400
        
        # Create new activation record
        activation_time = datetime.now().isoformat()
        
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO license_activations 
                (license_id, machine_fingerprint, activation_time, status, device_info)
                VALUES (?, ?, ?, 'active', ?)
            """, (
                license_id, 
                current_fingerprint, 
                activation_time,
                json.dumps({
                    "activated_via": "database_only", 
                    "timestamp": activation_time,
                    "endpoint": "/activate-license",
                    "validation_source": "database_only",
                    "cloud_error": original_error
                })
            ))
            conn.commit()
            
        logger.info(f"✅ Database-only activation successful for {license_key[:12]}...")
        
        # Prepare response
        features_list = []
        if existing_license.get('features'):
            try:
                features_list = json.loads(existing_license.get('features', '[]'))
            except:
                features_list = ['full_access']
        
        response = jsonify({
            'success': True,
            'valid': True,
            'data': {
                'license_key': license_key,
                'customer_email': existing_license.get('customer_email', 'unknown'),
                'package_name': existing_license.get('product_type', 'desktop'),
                'expires_at': existing_license.get('expires_at'),
                'status': 'activated',
                'features': features_list,
                'machine_fingerprint': current_fingerprint[:16] + "...",
                'activated_at': activation_time
            },
            'activation': {
                'source': 'database_only',
                'method': 'local_activation',
                'timestamp': activation_time
            },
            'warning': {
                'message': 'License activated from local database only - limited functionality',
                'reason': 'cloud_completely_unavailable',
                'recommendation': 'Connect to internet for full cloud synchronization and feature access',
                'limitations': ['Payment features unavailable', 'License updates may be delayed', 'Cloud sync disabled']
            }
        })
        return response
        
    except Exception as e:
        logger.error(f"❌ Database-only activation failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Database-only activation failed: {str(e)}. Original cloud error: {original_error}',
            'activation': {
                'source': 'database_only',
                'method': 'failed'
            }
        }), 500

@payment_bp.route('/license-status', methods=['GET'])
def get_license_status():
    """
    Get current active license status from local database with validation source info
    Enhanced with offline indicators
    """
    try:
        # Import license models
        try:
            from modules.licensing.license_models import License
        except ImportError:
            from backend.modules.licensing.license_models import License
        
        # Get all active licenses from local database
        with safe_db_connection() as conn:
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
                
                # FIXED: Actually validate license via cloud instead of just testing connectivity
                validation_source = 'database'  # Default fallback
                is_online = False
                
                try:
                    cloud_client = get_cloud_client()
                    
                    # Actually validate the license via cloud
                    license_key = license_data.get('license_key', '')
                    if license_key:
                        validation_result = cloud_client.validate_license(license_key)
                        
                        if validation_result.get('success') and validation_result.get('source') == 'cloud':
                            validation_source = 'cloud'
                            is_online = True
                            logger.info(f"✅ License validated via cloud: {license_key[:12]}...")
                        else:
                            logger.info(f"📋 License validated via database fallback: {license_key[:12]}...")
                    else:
                        # No license key to validate, just test connection
                        connectivity_test = cloud_client.test_connection()
                        is_online = connectivity_test.get('success', False)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Cloud validation failed, using database: {str(e)}")
                    validation_source = 'database'
                    is_online = False
                
                response_data = {
                    'success': True,
                    'license': {
                        'license_key': license_data.get('license_key', ''),
                        'customer_email': license_data.get('customer_email', ''),
                        'package_name': license_data.get('product_type', 'desktop'),
                        'package_type': license_data.get('product_type', 'desktop'),
                        'expires_at': license_data.get('expires_at'),
                        'status': license_data.get('status', 'active'),
                        'features': features_list,
                        'activated_at': license_data.get('activated_at'),
                        'is_active': True,
                        'is_trial': license_data.get('product_type', '').startswith('trial')
                    },
                    'system_status': {
                        'online': is_online,
                        'source': validation_source,  # FIXED: Use actual validation source
                        'timestamp': datetime.now().isoformat()
                    }
                }

                # NEW: Add trial_status for trial licenses
                if license_data.get('product_type', '').startswith('trial'):
                    try:
                        expires_at = license_data.get('expires_at')
                        if expires_at:
                            expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            days_left = (expiry_date - datetime.now()).days

                            response_data['trial_status'] = {
                                'is_trial': True,
                                'status': 'active' if days_left > 0 else 'expired',
                                'days_left': max(0, days_left),
                                'expires_at': expires_at
                            }
                            logger.info(f"✅ Trial status added: {days_left} days left")
                    except Exception as e:
                        logger.warning(f"Failed to calculate trial days: {e}")
                        response_data['trial_status'] = {
                            'is_trial': True,
                            'status': 'unknown',
                            'days_left': 0
                        }
                
                # Add offline warning if not connected
                if not is_online:
                    response_data['warning'] = {
                        'message': 'Operating in offline mode - some features may be limited',
                        'recommendation': 'Connect to internet for full functionality'
                    }
                
                return jsonify(response_data)
            else:
                # NEW: No paid license found - check auto trial
                logger.info("💡 No paid license found, checking auto trial...")

                try:
                    # Import auto trial service
                    try:
                        from modules.trial.auto_trial import AutoTrialService
                    except ImportError:
                        from backend.modules.trial.auto_trial import AutoTrialService

                    # Check or create auto trial
                    auto_trial_result = AutoTrialService.check_auto_trial()

                    if auto_trial_result.get('type') == 'trial' and auto_trial_result.get('status') == 'active':
                        # Active trial found/created
                        trial_license_data = auto_trial_result.get('license_data', {})

                        logger.info(f"✅ Auto trial active: {auto_trial_result.get('days_left', 0)} days left")

                        return jsonify({
                            'success': True,
                            'license': {
                                'license_key': trial_license_data.get('license_key', ''),
                                'customer_email': trial_license_data.get('customer_email', 'trial@local.dev'),
                                'package_name': trial_license_data.get('product_type', 'trial_7d'),
                                'package_type': trial_license_data.get('product_type', 'trial_7d'),
                                'expires_at': trial_license_data.get('expires_at'),
                                'status': 'active',
                                'features': trial_license_data.get('features', ['trial_access']),
                                'activated_at': trial_license_data.get('activated_at'),
                                'is_trial': True
                            },
                            'trial_status': {
                                'is_trial': True,
                                'days_left': auto_trial_result.get('days_left', 0),
                                'source': auto_trial_result.get('source', 'auto_generated'),
                                'machine_id': auto_trial_result.get('machine_id', '')[:16] + "..." if auto_trial_result.get('machine_id') else ''
                            },
                            'system_status': {
                                'online': True,  # We need internet for trial generation
                                'source': 'auto_trial',
                                'timestamp': datetime.now().isoformat()
                            }
                        })

                    elif auto_trial_result.get('type') == 'trial' and auto_trial_result.get('status') == 'expired':
                        # Trial expired
                        logger.info("❌ Trial expired")

                        return jsonify({
                            'success': True,
                            'license': None,
                            'trial_status': {
                                'is_trial': False,
                                'status': 'expired',
                                'expired_at': auto_trial_result.get('expired_at'),
                                'message': 'Trial period has ended'
                            },
                            'message': 'Trial expired - please purchase a license',
                            'system_status': {
                                'online': False,
                                'source': 'trial_expired',
                                'timestamp': datetime.now().isoformat()
                            }
                        })

                    elif auto_trial_result.get('status') == 'not_eligible':
                        # Not eligible for trial (already used)
                        logger.info(f"❌ Not eligible for trial: {auto_trial_result.get('reason')}")

                        return jsonify({
                            'success': True,
                            'license': None,
                            'trial_status': {
                                'is_trial': False,
                                'eligible': False,
                                'reason': auto_trial_result.get('reason'),
                                'message': auto_trial_result.get('message', 'Trial not available')
                            },
                            'message': 'No license found and trial not available',
                            'system_status': {
                                'online': False,
                                'source': 'no_license_no_trial',
                                'timestamp': datetime.now().isoformat()
                            }
                        })

                    else:
                        # Auto trial failed or other error
                        logger.warning(f"⚠️ Auto trial check failed: {auto_trial_result.get('error')}")

                        return jsonify({
                            'success': True,
                            'license': None,
                            'trial_status': {
                                'is_trial': False,
                                'error': auto_trial_result.get('error', 'Trial check failed')
                            },
                            'message': 'No active license found',
                            'system_status': {
                                'online': False,
                                'source': 'database',
                                'timestamp': datetime.now().isoformat()
                            }
                        })

                except Exception as trial_error:
                    logger.error(f"❌ Auto trial integration failed: {str(trial_error)}")

                    # Fallback to original response if trial system fails
                    return jsonify({
                        'success': True,
                        'license': None,
                        'message': 'No active license found',
                        'trial_error': str(trial_error),
                        'system_status': {
                            'online': False,
                            'source': 'database',
                            'timestamp': datetime.now().isoformat()
                        }
                    })
                
    except Exception as e:
        logger.error(f"License status check failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'system_status': {
                'online': False,
                'source': 'error',
                'timestamp': datetime.now().isoformat()
            }
        }), 500