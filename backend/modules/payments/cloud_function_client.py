# backend/modules/payments/cloud_function_client.py
"""
V_Track CloudFunction Client
Replaces local payment processing with cloud-based handlers
"""

import requests
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VTrackCloudClient:
    """Client for V_Track CloudFunctions"""
    
    def __init__(self):
        # CloudFunction URLs (update after deployment)
        self.base_url = os.getenv('VTRACK_CLOUD_BASE_URL', 'https://asia-southeast1-vtrack-payments.cloudfunctions.net')
        self.endpoints = {
            'create_payment': f"{self.base_url}/create-payment",
            'webhook_handler': f"{self.base_url}/webhook-handler", 
            'license_service': f"{self.base_url}/license-service"
        }
        
        # Request timeout
        self.timeout = 30
        
        logger.info("VTrack CloudFunction client initialized")
    
    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create payment via CloudFunction
        
        Args:
            payment_data: {
                'customer_email': str,
                'package_type': str,
                'provider': str (optional, defaults to 'payos')
            }
            
        Returns:
            dict: Payment creation result
        """
        try:
            logger.info(f"Creating payment for {payment_data.get('customer_email')}")
            
            response = requests.post(
                self.endpoints['create_payment'],
                json=payment_data,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Payment created successfully: {result.get('order_code')}")
                return {
                    'success': True,
                    'data': result
                }
            else:
                error_msg = f"Payment creation failed: {response.status_code}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Payment creation timeout"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"Payment creation error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def validate_license(self, license_key: str) -> Dict[str, Any]:
        """
        Validate license via CloudFunction
        
        Args:
            license_key: License key to validate
            
        Returns:
            dict: License validation result
        """
        try:
            logger.info(f"Validating license: {license_key[:10]}...")
            
            response = requests.get(
                self.endpoints['license_service'],
                params={'action': 'validate', 'license_key': license_key},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"License validation completed")
                return {
                    'success': True,
                    'valid': result.get('valid', False),
                    'data': result
                }
            else:
                error_msg = f"License validation failed: {response.status_code}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'valid': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"License validation error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'valid': False, 'error': error_msg}
    
    def get_user_licenses(self, customer_email: str) -> Dict[str, Any]:
        """
        Get all licenses for a user
        
        Args:
            customer_email: User email address
            
        Returns:
            dict: User licenses
        """
        try:
            logger.info(f"Getting licenses for {customer_email}")
            
            response = requests.post(
                self.endpoints['license_service'],
                json={'action': 'get_licenses', 'customer_email': customer_email},
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Retrieved {len(result.get('licenses', []))} licenses")
                return {
                    'success': True,
                    'data': result
                }
            else:
                error_msg = f"License retrieval failed: {response.status_code}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"License retrieval error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def health_check(self) -> Dict[str, Any]:
        """Check CloudFunction health status"""
        try:
            # Check all endpoints
            health_status = {}
            
            for service, url in self.endpoints.items():
                try:
                    response = requests.get(f"{url}?action=health", timeout=10)
                    health_status[service] = {
                        'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                        'status_code': response.status_code
                    }
                except:
                    health_status[service] = {
                        'status': 'unreachable',
                        'status_code': 0
                    }
            
            all_healthy = all(s['status'] == 'healthy' for s in health_status.values())
            
            return {
                'success': True,
                'all_healthy': all_healthy,
                'services': health_status
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Singleton instance
_cloud_client = None

def get_cloud_client() -> VTrackCloudClient:
    """Get singleton CloudFunction client"""
    global _cloud_client
    if _cloud_client is None:
        _cloud_client = VTrackCloudClient()
    return _cloud_client