# backend/modules/payments/cloud_function_client.py
"""
V_Track CloudFunction Client - Complete Version
Handles all communication between desktop app and Cloud Functions
Updated: 2025-08-05 - Fixed payment redirect URLs to unify success/cancel handling
"""

import requests
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class VTrackCloudClient:
    """Complete client for V_Track CloudFunctions integration"""
    
    def __init__(self):
        """Initialize with individual URLs from environment variables"""
        
        # Load URLs from environment (.env file)
        self.endpoints = {
            'create_payment': os.getenv('CLOUD_PAYMENT_URL'),
            'webhook_handler': os.getenv('CLOUD_WEBHOOK_URL'), 
            'license_service': os.getenv('CLOUD_LICENSE_URL')
        }
        
        # Validate all URLs are loaded
        missing_urls = []
        for name, url in self.endpoints.items():
            if not url:
                missing_urls.append(name)
                logger.warning(f"❌ Missing {name.upper()}_URL in environment")
            else:
                logger.info(f"✅ Loaded {name}: {url}")
        
        if missing_urls:
            logger.error(f"❌ Missing environment URLs: {missing_urls}")
            raise ValueError(f"Missing required environment variables: {missing_urls}")
        
        # Health check URLs
        self.health_endpoints = {
            'payment_health': f"{self.endpoints['create_payment']}?action=health",
            'webhook_health': f"{self.endpoints['webhook_handler']}?action=health"
        }
        
        # Request configuration
        self.timeout = int(os.getenv('HTTP_TIMEOUT', '30'))
        self.retry_attempts = int(os.getenv('HTTP_RETRY_ATTEMPTS', '3'))
        self.user_agent = os.getenv('HTTP_USER_AGENT', 'V_Track_Desktop_2.1.0')
        
        # FIXED: Unified redirect URLs - both success and cancel go to same endpoint
        self.unified_redirect_url = "http://localhost:8080/payment/redirect"
        
        # Request headers
        self.default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
        
        logger.info("✅ VTrack CloudFunction client initialized successfully")
        logger.info(f"🔗 Payment endpoint: {self.endpoints['create_payment']}")
        logger.info(f"🔄 Unified redirect URL: {self.unified_redirect_url}")
        logger.info(f"⏱️ Request timeout: {self.timeout}s")
    
    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]: # type: ignore
        """
        Create payment via CloudFunction with unified redirect URLs
        
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
            logger.info(f"🔄 Creating payment for {payment_data.get('customer_email')}")
            logger.debug(f"📤 Payment data: {payment_data}")
            
            # Validate required fields
            required_fields = ['customer_email', 'package_type']
            for field in required_fields:
                if field not in payment_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # FIXED: Force unified redirect URLs regardless of input
            # This ensures both success and cancel scenarios go to the same endpoint
            enhanced_payment_data = payment_data.copy()
            enhanced_payment_data.update({
                'return_url': self.unified_redirect_url,    # Success redirect
                'cancel_url': self.unified_redirect_url,    # Cancel redirect
                'unified_redirect': True                    # Flag for cloud function
            })
            
            logger.info(f"🔄 Using unified redirect URLs: {self.unified_redirect_url}")
            
            # Make request with retry logic
            for attempt in range(self.retry_attempts):
                try:
                    response = requests.post(
                        self.endpoints['create_payment'],
                        json=enhanced_payment_data,
                        timeout=self.timeout,
                        headers=self.default_headers
                    )
                    
                    logger.debug(f"📥 Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ Payment created successfully: Order {result.get('order_code')}")
                        logger.debug(f"📋 Payment URL: {result.get('payment_url', 'N/A')[:50]}...")
                        
                        return {
                            'success': True,
                            'data': result
                        }
                    else:
                        error_msg = f"Payment creation failed: HTTP {response.status_code}"
                        try:
                            error_data = response.json()
                            error_msg += f" - {error_data.get('error', 'Unknown error')}"
                        except:
                            error_msg += f" - {response.text[:100]}"
                        
                        logger.error(error_msg)
                        return {
                            'success': False,
                            'error': error_msg,
                            'status_code': response.status_code
                        }
                        
                except requests.exceptions.Timeout:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"⚠️ Request timeout, retrying... (attempt {attempt + 1}/{self.retry_attempts})")
                        continue
                    else:
                        error_msg = f"Payment creation timeout after {self.retry_attempts} attempts"
                        logger.error(error_msg)
                        return {'success': False, 'error': error_msg}
                
                except requests.exceptions.ConnectionError as e:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"⚠️ Connection error, retrying... (attempt {attempt + 1}/{self.retry_attempts})")
                        continue
                    else:
                        error_msg = f"Connection error after {self.retry_attempts} attempts: {str(e)}"
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
            logger.info(f"🔍 Validating license: {license_key[:12]}...")
            
            # Try cloud validation first
            try:
                response = requests.get(
                    self.endpoints['license_service'],
                    params={'action': 'validate', 'license_key': license_key},
                    timeout=15,  # Shorter timeout for validation
                    headers=self.default_headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ License validation completed via cloud")
                    return {
                        'success': True,
                        'valid': result.get('valid', False),
                        'data': result,
                        'source': 'cloud'
                    }
                else:
                    logger.warning(f"⚠️ Cloud validation failed: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Cloud validation error: {str(e)}")
            
            # DISABLED: Fallback to offline validation for testing
            # logger.info("🔄 Falling back to offline validation...")
            # offline_result = self._offline_license_validation(license_key)
            # offline_result['source'] = 'offline'
            # return offline_result

            # Return proper failure for invalid keys
            logger.info("❌ Cloud validation failed, offline fallback disabled")
            return {
                'success': True,
                'valid': False,
                'error': 'Cloud validation failed and offline fallback disabled',
                'source': 'none'
            }
                
        except Exception as e:
            error_msg = f"License validation error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'valid': False, 'error': error_msg}
    
    def _offline_license_validation(self, license_key: str) -> Dict[str, Any]:
        """
        Offline license validation fallback
        Uses local cryptographic verification
        """
        try:
            # Import license generator for offline validation
            from .license_generator import LicenseGenerator
            
            license_gen = LicenseGenerator()
            license_data = license_gen.verify_license(license_key)
            
            if license_data:
                logger.info("✅ License validated offline")
                return {
                    'success': True,
                    'valid': True,
                    'data': {
                        'customer_email': license_data.get('customer_email'),
                        'product_type': license_data.get('product_type'),
                        'features': license_data.get('features', []),
                        'expiry_date': license_data.get('expiry_date'),
                        'license_id': license_data.get('license_id')
                    }
                }
            else:
                logger.warning("❌ License validation failed offline")
                return {
                    'success': True,
                    'valid': False,
                    'error': 'Invalid license or expired'
                }
                
        except Exception as e:
            logger.error(f"❌ Offline validation error: {str(e)}")
            return {
                'success': False,
                'valid': False,
                'error': f'Offline validation failed: {str(e)}'
            }
    
    def get_user_licenses(self, customer_email: str) -> Dict[str, Any]:
        """
        Get all licenses for a user
        
        Args:
            customer_email: User email address
            
        Returns:
            dict: User licenses
        """
        try:
            logger.info(f"📋 Getting licenses for {customer_email}")
            
            response = requests.post(
                self.endpoints['license_service'],
                json={'action': 'get_licenses', 'customer_email': customer_email},
                timeout=self.timeout,
                headers=self.default_headers
            )
            
            if response.status_code == 200:
                result = response.json()
                license_count = len(result.get('licenses', []))
                logger.info(f"✅ Retrieved {license_count} licenses for {customer_email}")
                return {
                    'success': True,
                    'data': result
                }
            else:
                error_msg = f"License retrieval failed: HTTP {response.status_code}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"License retrieval error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def get_packages(self) -> Dict[str, Any]:
        """
        Get available payment packages
        
        Returns:
            dict: Available packages with pricing
        """
        try:
            # Local package configuration (can be moved to cloud later)
            packages = {
                'personal_1m': {
                    'name': 'Personal Monthly',
                    'price': int(os.getenv('PERSONAL_1M_PRICE', '2000')),
                    'duration_days': 30,
                    'features': os.getenv('PERSONAL_1M_FEATURES', 'unlimited_cameras,basic_analytics,email_support').split(','),
                    'description': 'Gói cá nhân cho hộ gia đình'
                },
                'personal_1y': {
                    'name': 'Personal Annual',
                    'price': int(os.getenv('PERSONAL_1Y_PRICE', '20000')),
                    'duration_days': 365,
                    'features': os.getenv('PERSONAL_1Y_FEATURES', 'unlimited_cameras,advanced_analytics,priority_support').split(','),
                    'description': 'Gói cá nhân tiết kiệm (Save 16%)'
                },
                'business_1m': {
                    'name': 'Business Monthly',
                    'price': int(os.getenv('BUSINESS_1M_PRICE', '5000')),
                    'duration_days': 30,
                    'features': os.getenv('BUSINESS_1M_FEATURES', 'unlimited_cameras,advanced_analytics,api_access,priority_support').split(','),
                    'description': 'Gói doanh nghiệp cho văn phòng'
                },
                'business_1y': {
                    'name': 'Business Annual',
                    'price': int(os.getenv('BUSINESS_1Y_PRICE', '50000')),
                    'duration_days': 365,
                    'features': os.getenv('BUSINESS_1Y_FEATURES', 'unlimited_cameras,advanced_analytics,api_access,dedicated_support').split(','),
                    'description': 'Gói doanh nghiệp tiết kiệm (Save 16%)'
                }
            }
            
            logger.info(f"📦 Retrieved {len(packages)} packages")
            return {
                'success': True,
                'packages': packages
            }
            
        except Exception as e:
            error_msg = f"Package retrieval error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test basic connectivity to cloud functions
        
        Returns:
            dict: Connection test result
        """
        try:
            logger.info("🔌 Testing cloud function connectivity...")
            
            # Quick ping to payment endpoint
            response = requests.get(
                f"{self.endpoints['create_payment']}?action=health",
                timeout=5,
                headers=self.default_headers
            )
            
            response_time_ms = int(response.elapsed.total_seconds() * 1000)
            
            if response.status_code == 200:
                logger.info(f"✅ Cloud functions reachable ({response_time_ms}ms)")
                return {
                    'success': True,
                    'status': 'connected',
                    'response_time_ms': response_time_ms,
                    'endpoint': self.endpoints['create_payment']
                }
            else:
                logger.warning(f"⚠️ Cloud functions responding with {response.status_code}")
                return {
                    'success': False,
                    'status': 'degraded',
                    'status_code': response.status_code,
                    'response_time_ms': response_time_ms
                }
                
        except requests.exceptions.Timeout:
            logger.error("❌ Connection test timeout")
            return {
                'success': False,
                'status': 'timeout',
                'error': 'Request timeout (>5s)'
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection test failed: {str(e)}")
            return {
                'success': False,
                'status': 'disconnected',
                'error': f'Connection error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"❌ Connection test error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for all cloud functions
        
        Returns:
            dict: Detailed health status
        """
        try:
            logger.info("🏥 Running comprehensive health check...")
            
            # Check all endpoints
            health_status = {}
            overall_healthy = True
            
            for service, url in self.endpoints.items():
                try:
                    health_url = f"{url}?action=health"
                    response = requests.get(health_url, timeout=10)
                    
                    if response.status_code == 200:
                        try:
                            health_data = response.json()
                            health_status[service] = {
                                'status': 'healthy',
                                'status_code': response.status_code,
                                'response_time_ms': int(response.elapsed.total_seconds() * 1000),
                                'details': health_data
                            }
                            logger.info(f"✅ {service}: healthy ({response.elapsed.total_seconds():.2f}s)")
                        except:
                            health_status[service] = {
                                'status': 'healthy',
                                'status_code': response.status_code,
                                'response_time_ms': int(response.elapsed.total_seconds() * 1000)
                            }
                    else:
                        health_status[service] = {
                            'status': 'unhealthy',
                            'status_code': response.status_code,
                            'error': f'HTTP {response.status_code}'
                        }
                        overall_healthy = False
                        logger.warning(f"⚠️ {service}: unhealthy (HTTP {response.status_code})")
                        
                except requests.exceptions.Timeout:
                    health_status[service] = {
                        'status': 'timeout',
                        'status_code': 0,
                        'error': 'Request timeout'
                    }
                    overall_healthy = False
                    logger.warning(f"⚠️ {service}: timeout")
                    
                except Exception as e:
                    health_status[service] = {
                        'status': 'unreachable',
                        'status_code': 0,
                        'error': str(e)
                    }
                    overall_healthy = False
                    logger.warning(f"⚠️ {service}: unreachable - {str(e)}")
            
            # Overall health summary
            healthy_count = sum(1 for s in health_status.values() if s['status'] == 'healthy')
            total_count = len(health_status)
            
            result = {
                'success': True,
                'overall_status': 'healthy' if overall_healthy else 'degraded',
                'services_healthy': f"{healthy_count}/{total_count}",
                'services': health_status,
                'timestamp': datetime.now().isoformat(),
                'endpoints': self.endpoints
            }
            
            if overall_healthy:
                logger.info(f"✅ All services healthy ({healthy_count}/{total_count})")
            else:
                logger.warning(f"⚠️ Some services degraded ({healthy_count}/{total_count})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status for debugging
        
        Returns:
            dict: Complete system information
        """
        try:
            # Basic connection test
            connection = self.test_connection()
            
            # Package availability
            packages = self.get_packages()
            
            # Environment configuration
            environment = {
                'urls_configured': all(url for url in self.endpoints.values()),
                'endpoints': self.endpoints,
                'unified_redirect_url': self.unified_redirect_url,  # Added for debugging
                'timeout': self.timeout,
                'retry_attempts': self.retry_attempts,
                'user_agent': self.user_agent
            }
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'connection': connection,
                'packages': {
                    'available': packages.get('success', False),
                    'count': len(packages.get('packages', {}))
                },
                'environment': environment,
                'client_version': '2.1.0'
            }
            
        except Exception as e:
            logger.error(f"❌ System status error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Singleton instance
_cloud_client: Optional[VTrackCloudClient] = None

def get_cloud_client() -> VTrackCloudClient:
    """Get singleton CloudFunction client"""
    global _cloud_client
    if _cloud_client is None:
        _cloud_client = VTrackCloudClient()
    return _cloud_client

def reset_cloud_client():
    """Reset singleton (for testing)"""
    global _cloud_client
    _cloud_client = None

# Validation function for app.py startup
def validate_cloud_integration() -> tuple[bool, list[str]]:
    """
    Validate cloud integration setup
    
    Returns:
        tuple: (is_valid, list_of_issues)
    """
    issues = []
    
    try:
        # Check environment variables
        required_urls = ['CLOUD_PAYMENT_URL', 'CLOUD_WEBHOOK_URL', 'CLOUD_LICENSE_URL']
        for url_name in required_urls:
            if not os.getenv(url_name):
                issues.append(f"Missing environment variable: {url_name}")
        
        # Try to initialize client
        if not issues:
            try:
                client = get_cloud_client()
                logger.info("✅ Cloud client initialized successfully")
            except Exception as e:
                issues.append(f"Client initialization failed: {str(e)}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Validation error: {str(e)}")
        return False, issues