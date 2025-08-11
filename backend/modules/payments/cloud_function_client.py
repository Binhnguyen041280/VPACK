# backend/modules/payments/cloud_function_client.py
"""
V_Track CloudFunction Client - Complete Version with Offline Fallback
Handles all communication between desktop app and Cloud Functions
Updated: 2025-08-11 - Enabled offline fallback for production reliability
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
        
        # Request configuration - Improved for offline fallback
        self.timeout = int(os.getenv('HTTP_TIMEOUT', '10'))  # Reduced from 30 to 10
        self.license_timeout = int(os.getenv('LICENSE_TIMEOUT', '8'))  # Faster timeout for license validation
        self.retry_attempts = int(os.getenv('HTTP_RETRY_ATTEMPTS', '2'))  # Reduced retries
        self.user_agent = os.getenv('HTTP_USER_AGENT', 'V_Track_Desktop_2.1.0')
        
        # Offline fallback configuration
        self.offline_fallback_enabled = os.getenv('OFFLINE_FALLBACK_ENABLED', 'true').lower() == 'true'
        self.offline_grace_period_hours = int(os.getenv('OFFLINE_GRACE_PERIOD_HOURS', '72'))
        
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
        logger.info(f"⏱️ Request timeout: {self.timeout}s (license: {self.license_timeout}s)")
        logger.info(f"🔄 Offline fallback: {'enabled' if self.offline_fallback_enabled else 'disabled'}")
    
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
    
    def _check_internet_connectivity(self) -> bool:
        """Quick internet connectivity check"""
        try:
            # Quick ping to a reliable endpoint
            response = requests.get(
                "https://www.google.com/generate_204",
                timeout=3,
                allow_redirects=False
            )
            return response.status_code == 204
        except:
            return False
    
    def validate_license(self, license_key: str) -> Dict[str, Any]:
        """
        Validate license via CloudFunction with offline fallback
        
        Args:
            license_key: License key to validate
            
        Returns:
            dict: License validation result
        """
        try:
            logger.info(f"🔍 Validating license: {license_key[:12]}...")
            
            # Quick connectivity check
            has_internet = self._check_internet_connectivity()
            if not has_internet:
                logger.warning("⚠️ No internet connectivity detected, using offline validation")
                if self.offline_fallback_enabled:
                    offline_result = self._offline_license_validation(license_key)
                    offline_result['source'] = 'offline'
                    offline_result['reason'] = 'no_internet'
                    return offline_result
                else:
                    return {
                        'success': False,
                        'valid': False,
                        'error': 'No internet connection and offline fallback disabled',
                        'source': 'none'
                    }
            
            # Try cloud validation with improved error handling
            cloud_errors = []
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"🌐 Cloud validation attempt {attempt + 1}/{self.retry_attempts}")
                    
                    response = requests.get(
                        self.endpoints['license_service'],
                        params={'action': 'validate', 'license_key': license_key},
                        timeout=self.license_timeout,
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
                    elif response.status_code == 404:
                        # License not found - don't retry, this is definitive
                        logger.info(f"❌ License not found in cloud")
                        cloud_errors.append(f"License not found (HTTP 404)")
                        break
                    elif response.status_code == 400:
                        # Bad request - don't retry, this is definitive
                        logger.info(f"❌ Invalid license format")
                        cloud_errors.append(f"Invalid license format (HTTP 400)")
                        break
                    else:
                        error_msg = f"Cloud validation failed: HTTP {response.status_code}"
                        cloud_errors.append(error_msg)
                        logger.warning(f"⚠️ {error_msg}")
                        
                        # Don't retry on client errors (4xx)
                        if 400 <= response.status_code < 500:
                            break
                            
                except requests.exceptions.Timeout:
                    error_msg = f"Cloud timeout (attempt {attempt + 1})"
                    cloud_errors.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
                    
                except requests.exceptions.ConnectionError as e:
                    error_msg = f"Connection error (attempt {attempt + 1}): {str(e)[:50]}"
                    cloud_errors.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
                    
                except Exception as e:
                    error_msg = f"Unexpected error (attempt {attempt + 1}): {str(e)[:50]}"
                    cloud_errors.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
                
                # Short delay between retries
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(1)
            
            # All cloud attempts failed - try offline fallback
            logger.warning(f"⚠️ Cloud validation failed after {self.retry_attempts} attempts")
            logger.debug(f"📋 Cloud errors: {cloud_errors}")
            
            if self.offline_fallback_enabled:
                logger.info("🔄 Falling back to offline validation...")
                offline_result = self._offline_license_validation(license_key)
                offline_result['source'] = 'offline'
                offline_result['reason'] = 'cloud_unavailable'
                offline_result['cloud_errors'] = cloud_errors
                return offline_result
            else:
                logger.info("❌ Cloud validation failed, offline fallback disabled")
                return {
                    'success': True,
                    'valid': False,
                    'error': f'Cloud validation failed: {cloud_errors[-1] if cloud_errors else "Unknown error"}',
                    'source': 'none',
                    'cloud_errors': cloud_errors
                }
                
        except Exception as e:
            error_msg = f"License validation error: {str(e)}"
            logger.error(error_msg)
            
            # Try offline fallback on unexpected errors
            if self.offline_fallback_enabled:
                logger.info("🔄 Unexpected error, trying offline validation...")
                try:
                    offline_result = self._offline_license_validation(license_key)
                    offline_result['source'] = 'offline'
                    offline_result['reason'] = 'exception_fallback'
                    offline_result['original_error'] = error_msg
                    return offline_result
                except Exception as offline_error:
                    logger.error(f"❌ Offline fallback also failed: {str(offline_error)}")
            
            return {'success': False, 'valid': False, 'error': error_msg}
    
    def _offline_license_validation(self, license_key: str) -> Dict[str, Any]:
        """
        Enhanced offline license validation fallback
        Uses local database and basic validation
        """
        try:
            logger.info("🔄 Starting offline license validation...")
            
            # Import database utilities for local validation
            try:
                from modules.db_utils import get_db_connection
            except ImportError:
                from backend.modules.db_utils import get_db_connection
            
            # Check local database first
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Look for license in local database
                    cursor.execute("""
                        SELECT license_key, customer_email, product_type, features, 
                               status, expires_at, created_at
                        FROM licenses 
                        WHERE license_key = ? AND status = 'active'
                    """, (license_key,))
                    
                    license_row = cursor.fetchone()
                    
                    if license_row:
                        # Parse license data
                        (key, email, product_type, features_json, status, expires_at, created_at) = license_row
                        
                        # Parse features
                        import json
                        try:
                            features = json.loads(features_json) if features_json else ['full_access']
                        except:
                            features = ['full_access']
                        
                        # Check expiry if exists
                        is_expired = False
                        if expires_at:
                            try:
                                from datetime import datetime
                                expiry_date = datetime.fromisoformat(expires_at)
                                is_expired = datetime.now() > expiry_date
                            except:
                                logger.warning("⚠️ Could not parse expiry date, assuming valid")
                        
                        if is_expired:
                            logger.warning(f"❌ License found but expired: {expires_at}")
                            return {
                                'success': True,
                                'valid': False,
                                'error': f'License expired on {expires_at}',
                                'data': {
                                    'customer_email': email,
                                    'product_type': product_type,
                                    'expires_at': expires_at,
                                    'status': 'expired'
                                }
                            }
                        
                        logger.info(f"✅ License validated offline from database")
                        return {
                            'success': True,
                            'valid': True,
                            'data': {
                                'customer_email': email,
                                'product_type': product_type,
                                'features': features,
                                'expires_at': expires_at,
                                'license_key': license_key,
                                'status': 'active',
                                'validation_method': 'database'
                            }
                        }
                    else:
                        logger.info(f"❌ License not found in local database")
                        
            except Exception as db_error:
                logger.warning(f"⚠️ Database validation failed: {str(db_error)}")
            
            # Fallback to cryptographic validation if available
            try:
                logger.info("🔄 Trying cryptographic validation...")
                from .license_generator import LicenseGenerator
                
                license_gen = LicenseGenerator()
                license_data = license_gen.verify_license(license_key)
                
                if license_data:
                    logger.info("✅ License validated offline via cryptography")
                    return {
                        'success': True,
                        'valid': True,
                        'data': {
                            'customer_email': license_data.get('customer_email'),
                            'product_type': license_data.get('product_type'),
                            'features': license_data.get('features', []),
                            'expires_at': license_data.get('expiry_date'),
                            'license_id': license_data.get('license_id'),
                            'validation_method': 'cryptographic'
                        }
                    }
                else:
                    logger.warning("❌ Cryptographic validation failed")
                    
            except ImportError:
                logger.warning("⚠️ License generator not available for cryptographic validation")
            except Exception as crypto_error:
                logger.warning(f"⚠️ Cryptographic validation failed: {str(crypto_error)}")
            
            # All offline methods failed
            logger.warning("❌ All offline validation methods failed")
            return {
                'success': True,
                'valid': False,
                'error': 'License not found in local database and cryptographic validation failed'
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
                'endpoints': self.endpoints,
                'offline_fallback': {
                    'enabled': self.offline_fallback_enabled,
                    'grace_period_hours': self.offline_grace_period_hours
                }
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
                'unified_redirect_url': self.unified_redirect_url,
                'timeout': self.timeout,
                'license_timeout': self.license_timeout,
                'retry_attempts': self.retry_attempts,
                'user_agent': self.user_agent,
                'offline_fallback_enabled': self.offline_fallback_enabled,
                'offline_grace_period_hours': self.offline_grace_period_hours
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
                
                # Test offline fallback availability
                if client.offline_fallback_enabled:
                    logger.info("✅ Offline fallback enabled")
                else:
                    logger.warning("⚠️ Offline fallback disabled")
                    
            except Exception as e:
                issues.append(f"Client initialization failed: {str(e)}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Validation error: {str(e)}")
        return False, issues