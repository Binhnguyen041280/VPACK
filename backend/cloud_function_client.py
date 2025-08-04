"""
Cloud Functions Client for V_track Desktop App
Replaces local payment processing with Cloud Function calls
"""
import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint for Cloud Function integration
cloud_payment_bp = Blueprint('cloud_payment', __name__)

class CloudFunctionClient:
    """Client to interact with V_track Cloud Functions"""
    
    def __init__(self):
        """Initialize Cloud Function client with URLs from environment"""
        self.payment_url = os.getenv('CLOUD_FUNCTION_PAYMENT_URL', '')
        self.webhook_url = os.getenv('CLOUD_FUNCTION_WEBHOOK_URL', '')
        self.license_url = os.getenv('CLOUD_FUNCTION_LICENSE_URL', '')
        
        # Request timeout settings
        self.timeout = 30
        self.retry_count = 3
        
        # Validate configuration
        if not self.payment_url:
            logger.warning("CLOUD_FUNCTION_PAYMENT_URL not configured")
        
        logger.info("Cloud Function client initialized")
        logger.info(f"Payment URL: {self.payment_url}")
        logger.info(f"Webhook URL: {self.webhook_url}")
        logger.info(f"License URL: {self.license_url}")
    
    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create payment via Cloud Function
        
        Args:
            payment_data: {
                'customer_email': str,
                'package_type': str,
                'callback_url': str (optional)
            }
            
        Returns:
            dict: Payment creation result
        """
        try:
            logger.info(f"Creating payment via Cloud Function: {payment_data.get('customer_email')}")
            
            if not self.payment_url:
                return {
                    'success': False,
                    'error': 'Cloud Function payment URL not configured'
                }
            
            # Make request to Cloud Function
            response = requests.post(
                self.payment_url,
                json=payment_data,
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'V_track-Desktop/1.0'
                }
            )
            
            # Parse response
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
            else:
                result = {'success': False, 'error': f'Invalid response format: {response.text}'}
            
            # Add metadata
            result['_meta'] = {
                'status_code': response.status_code,
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'timestamp': datetime.now().isoformat()
            }
            
            if response.status_code == 200 and result.get('success'):
                logger.info(f"Payment created successfully: {result.get('app_trans_id')}")
            else:
                logger.error(f"Payment creation failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error("Payment creation timeout")
            return {
                'success': False,
                'error': 'Request timeout - please try again'
            }
        except requests.exceptions.ConnectionError:
            logger.error("Payment creation connection error")
            return {
                'success': False,
                'error': 'Connection error - please check internet connection'
            }
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
            return {
                'success': False,
                'error': f'Payment creation failed: {str(e)}'
            }
    
    def get_license(self, license_id: str) -> Dict[str, Any]:
        """
        Get license from Cloud Function
        
        Args:
            license_id: License ID to retrieve
            
        Returns:
            dict: License data
        """
        try:
            if not self.license_url:
                return {
                    'success': False,
                    'error': 'Cloud Function license URL not configured'
                }
            
            url = f"{self.license_url}/{license_id}"
            
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'User-Agent': 'V_track-Desktop/1.0'}
            )
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {'success': False, 'error': 'Invalid response format'}
                
        except Exception as e:
            logger.error(f"License retrieval error: {str(e)}")
            return {
                'success': False,
                'error': f'License retrieval failed: {str(e)}'
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all Cloud Functions
        
        Returns:
            dict: Health status of all functions
        """
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_healthy': True,
            'functions': {}
        }
        
        # Check each function
        functions_to_check = [
            ('payment', self.payment_url),
            ('webhook', self.webhook_url),
            ('license', self.license_url)
        ]
        
        for name, url in functions_to_check:
            if not url:
                health_status['functions'][name] = {
                    'healthy': False,
                    'error': 'URL not configured'
                }
                health_status['overall_healthy'] = False
                continue
            
            try:
                # Try to reach health endpoint
                health_url = f"{url}?action=health" if '?' not in url else f"{url}&action=health"
                
                response = requests.get(health_url, timeout=5)
                
                if response.status_code == 200:
                    health_status['functions'][name] = {
                        'healthy': True,
                        'status_code': response.status_code,
                        'response_time_ms': response.elapsed.total_seconds() * 1000
                    }
                else:
                    health_status['functions'][name] = {
                        'healthy': False,
                        'status_code': response.status_code,
                        'error': f'HTTP {response.status_code}'
                    }
                    health_status['overall_healthy'] = False
                    
            except Exception as e:
                health_status['functions'][name] = {
                    'healthy': False,
                    'error': str(e)
                }
                health_status['overall_healthy'] = False
        
        return health_status

# Global client instance
_cloud_client = None

def get_cloud_client() -> CloudFunctionClient:
    """Get singleton Cloud Function client"""
    global _cloud_client
    if _cloud_client is None:
        _cloud_client = CloudFunctionClient()
    return _cloud_client

# ===== FLASK ROUTES FOR DESKTOP APP =====

@cloud_payment_bp.route('/api/payment/create', methods=['POST', 'OPTIONS'])
def create_payment_proxy():
    """
    Proxy endpoint for payment creation
    Replaces the original ZaloPay handler in desktop app
    """
    try:
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            return '', 204
        
        # Get request data
        payment_data = request.get_json()
        
        if not payment_data:
            return jsonify({
                'success': False,
                'error': 'No payment data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['customer_email', 'package_type']
        missing_fields = [field for field in required_fields if not payment_data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {missing_fields}'
            }), 400
        
        # Call Cloud Function
        client = get_cloud_client()
        result = client.create_payment(payment_data)
        
        # Return result with appropriate status code
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Payment proxy error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@cloud_payment_bp.route('/api/payment/status/<app_trans_id>', methods=['GET'])
def get_payment_status(app_trans_id):
    """
    Get payment status from Cloud Function
    """
    try:
        # For now, return basic response
        # This could be enhanced to query Firestore directly
        return jsonify({
            'success': True,
            'app_trans_id': app_trans_id,
            'status': 'pending',
            'message': 'Check your email for license delivery after payment completion'
        })
        
    except Exception as e:
        logger.error(f"Payment status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get payment status'
        }), 500

@cloud_payment_bp.route('/api/license/download/<license_id>', methods=['GET'])
def download_license_proxy(license_id):
    """
    Proxy endpoint for license download
    """
    try:
        client = get_cloud_client()
        result = client.get_license(license_id)
        
        status_code = 200 if result.get('success') else 404
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"License download proxy error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'License download failed'
        }), 500

@cloud_payment_bp.route('/api/cloud/health', methods=['GET'])
def cloud_health_check():
    """
    Health check for Cloud Functions
    """
    try:
        client = get_cloud_client()
        health_status = client.health_check()
        
        status_code = 200 if health_status.get('overall_healthy') else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Cloud health check error: {str(e)}")
        return jsonify({
            'healthy': False,
            'error': str(e)
        }), 500

@cloud_payment_bp.route('/api/payment/packages', methods=['GET'])
def get_available_packages():
    """
    Get available payment packages
    """
    try:
        # Package information (should match Cloud Function configuration)
        packages = {
            'trial_30d': {
                'name': 'Trial 30 Days',
                'amount': 0,
                'duration_days': 30,
                'features': ['basic_tracking', 'limited_cameras'],
                'description': 'Free 30-day trial',
                'formatted_amount': 'Free'
            },
            'basic_1y': {
                'name': 'Basic Annual',
                'amount': 300000,
                'duration_days': 365,
                'features': ['full_tracking', 'unlimited_cameras', 'email_support'],
                'description': 'Basic annual license',
                'formatted_amount': '300,000 VND'
            },
            'professional_1y': {
                'name': 'Professional Annual',
                'amount': 500000,
                'duration_days': 365,
                'features': ['full_tracking', 'unlimited_cameras', 'priority_support', 'cloud_sync', 'advanced_analytics'],
                'description': 'Professional annual license',
                'formatted_amount': '500,000 VND'
            },
            'enterprise_1y': {
                'name': 'Enterprise Annual',
                'amount': 1000000,
                'duration_days': 365,
                'features': ['full_tracking', 'unlimited_cameras', 'dedicated_support', 'cloud_sync', 'advanced_analytics', 'custom_integration'],
                'description': 'Enterprise annual license',
                'formatted_amount': '1,000,000 VND'
            }
        }
        
        return jsonify({
            'success': True,
            'packages': packages
        })
        
    except Exception as e:
        logger.error(f"Get packages error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get packages'
        }), 500

# Configuration validation function
def validate_cloud_configuration():
    """Validate Cloud Function configuration"""
    client = get_cloud_client()
    
    issues = []
    
    if not client.payment_url:
        issues.append("CLOUD_FUNCTION_PAYMENT_URL not configured")
    
    if not client.webhook_url:
        issues.append("CLOUD_FUNCTION_WEBHOOK_URL not configured")
    
    if not client.license_url:
        issues.append("CLOUD_FUNCTION_LICENSE_URL not configured")
    
    if issues:
        logger.warning("Cloud Function configuration issues:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        return False, issues
    
    logger.info("Cloud Function configuration validated successfully")
    return True, []

# Initialization function for app.py
def init_cloud_payment_integration(app):
    """
    Initialize Cloud Function integration in main app
    Call this from app.py to register the blueprint
    """
    try:
        # Validate configuration
        valid, issues = validate_cloud_configuration()
        
        if not valid:
            logger.warning("Cloud Function integration has configuration issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        # Register blueprint
        app.register_blueprint(cloud_payment_bp)
        
        logger.info("✅ Cloud Function integration initialized")
        logger.info("📋 Available endpoints:")
        logger.info("   POST /api/payment/create")
        logger.info("   GET  /api/payment/status/<app_trans_id>")
        logger.info("   GET  /api/license/download/<license_id>")
        logger.info("   GET  /api/cloud/health")
        logger.info("   GET  /api/payment/packages")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Cloud Function integration: {str(e)}")
        return False