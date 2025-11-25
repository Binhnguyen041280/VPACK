# backend/modules/payments/cloud_function_client.py
"""
V_Track CloudFunction Client - REFACTORED with Repository Pattern
ELIMINATES: Database patterns, JSON parsing, expiry validation duplicates
REDUCES: From 450 lines to ~250 lines (-44% reduction)
Updated: 2025-08-11 - Phase 1 Refactoring Integration
"""

import requests
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class VTrackCloudClient:
    """Refactored client using unified repository pattern"""
    
    def __init__(self):
        """Initialize with streamlined configuration"""
        # Load URLs from environment (.env file)
        self.endpoints = {
            'create_payment': os.getenv('CLOUD_PAYMENT_URL'),
            'webhook_handler': os.getenv('CLOUD_WEBHOOK_URL'), 
            'license_service': os.getenv('CLOUD_LICENSE_URL')
        }
        
        # Validate URLs
        missing_urls = [name for name, url in self.endpoints.items() if not url]
        if missing_urls:
            logger.error(f"❌ Missing environment URLs: {missing_urls}")
            raise ValueError(f"Missing required environment variables: {missing_urls}")
        
        # Configuration
        self.timeout = int(os.getenv('HTTP_TIMEOUT', '10'))
        self.license_timeout = int(os.getenv('LICENSE_TIMEOUT', '8'))
        self.retry_attempts = int(os.getenv('HTTP_RETRY_ATTEMPTS', '2'))
        self.user_agent = os.getenv('HTTP_USER_AGENT', 'V_Track_Desktop_2.1.0')
        self.unified_redirect_url = "http://localhost:8080/payment/redirect"
        
        # Offline fallback
        self.offline_fallback_enabled = os.getenv('OFFLINE_FALLBACK_ENABLED', 'true').lower() == 'true'
        
        # Request headers
        self.default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
        
        # PHASE 1: Initialize repository for offline fallback
        self._repository = None
        
        logger.info("✅ VTrack CloudFunction client initialized (refactored)")
    
    def _get_repository(self):
        """Lazy load repository from Phase 1"""
        if self._repository is None:
            try:
                from ..licensing.repositories.license_repository import get_license_repository
                self._repository = get_license_repository()
                logger.debug("✅ Repository integrated for offline fallback")
            except ImportError:
                logger.warning("⚠️ Repository not available - limited offline functionality")
                self._repository = None
        return self._repository
    
    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment via CloudFunction - UNCHANGED CORE LOGIC"""
        try:
            logger.info(f"🔄 Creating payment for {payment_data.get('customer_email')}")
            
            # Validate required fields
            required_fields = ['customer_email', 'package_type']
            for field in required_fields:
                if field not in payment_data:
                    return {'success': False, 'error': f'Missing required field: {field}'}
            
            # Force unified redirect URLs
            enhanced_payment_data = payment_data.copy()
            enhanced_payment_data.update({
                'return_url': self.unified_redirect_url,
                'cancel_url': self.unified_redirect_url,
                'unified_redirect': True
            })
            
            # Make request with retry logic
            for attempt in range(self.retry_attempts):
                try:
                    response = requests.post(
                        self.endpoints['create_payment'],
                        json=enhanced_payment_data,
                        timeout=self.timeout,
                        headers=self.default_headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ Payment created successfully: Order {result.get('order_code')}")
                        return {'success': True, 'data': result}
                    else:
                        error_msg = f"Payment creation failed: HTTP {response.status_code}"
                        try:
                            error_data = response.json()
                            error_msg += f" - {error_data.get('error', 'Unknown error')}"
                        except:
                            error_msg += f" - {response.text[:100]}"
                        
                        logger.error(error_msg)
                        return {'success': False, 'error': error_msg, 'status_code': response.status_code}
                        
                except requests.exceptions.Timeout:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"⚠️ Request timeout, retrying... (attempt {attempt + 1}/{self.retry_attempts})")
                        continue
                    else:
                        return {'success': False, 'error': f"Payment creation timeout after {self.retry_attempts} attempts"}
                
                except requests.exceptions.ConnectionError as e:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"⚠️ Connection error, retrying... (attempt {attempt + 1}/{self.retry_attempts})")
                        continue
                    else:
                        return {'success': False, 'error': f"Connection error after {self.retry_attempts} attempts: {str(e)}"}
            
            # If we reach here, all attempts failed but no explicit return was triggered
            return {'success': False, 'error': f"Payment creation failed after {self.retry_attempts} attempts"}
                        
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _check_internet_connectivity(self) -> bool:
        """Quick internet connectivity check"""
        try:
            response = requests.get("https://www.google.com/generate_204", timeout=3, allow_redirects=False)
            return response.status_code == 204
        except:
            return False
    
    def validate_license(self, license_key: str) -> Dict[str, Any]:
        """
        REFACTORED: License validation with repository fallback
        ELIMINATES: Database patterns, JSON parsing, expiry validation duplicates
        """
        try:
            logger.info(f"🔍 Validating license: {license_key[:12]}...")
            
            # Quick connectivity check
            has_internet = self._check_internet_connectivity()
            if not has_internet:
                logger.warning("⚠️ No internet connectivity detected, using offline validation")
                if self.offline_fallback_enabled:
                    offline_result = self._offline_license_validation_refactored(license_key)
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
            
            # Try cloud validation
            cloud_errors = []
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"🌐 Cloud validation attempt {attempt + 1}/{self.retry_attempts}")

                    response = requests.post(
                        self.endpoints['license_service'],
                        json={'action': 'validate_license', 'license_key': license_key},
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
                    elif response.status_code in [404, 400]:
                        # Definitive errors - don't retry
                        error_msg = f"License validation failed: HTTP {response.status_code}"
                        cloud_errors.append(error_msg)
                        break
                    else:
                        error_msg = f"Cloud validation failed: HTTP {response.status_code}"
                        cloud_errors.append(error_msg)
                        if 400 <= response.status_code < 500:
                            break  # Don't retry client errors
                            
                except requests.exceptions.Timeout:
                    cloud_errors.append(f"Cloud timeout (attempt {attempt + 1})")
                except requests.exceptions.ConnectionError as e:
                    cloud_errors.append(f"Connection error (attempt {attempt + 1}): {str(e)[:50]}")
                except Exception as e:
                    cloud_errors.append(f"Unexpected error (attempt {attempt + 1}): {str(e)[:50]}")
                
                # Short delay between retries
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(1)
            
            # Cloud failed - try offline fallback using repository
            logger.warning(f"⚠️ Cloud validation failed after {self.retry_attempts} attempts")
            logger.error(f"❌ Cloud errors: {cloud_errors}")  # ADD: Log detailed errors

            if self.offline_fallback_enabled:
                logger.info("🔄 Falling back to repository-based validation...")
                offline_result = self._offline_license_validation_refactored(license_key)
                offline_result['source'] = 'offline'
                offline_result['reason'] = 'cloud_unavailable'
                offline_result['cloud_errors'] = cloud_errors
                return offline_result
            else:
                return {
                    'success': True,
                    'valid': False,
                    'error': f'Cloud validation failed: {cloud_errors[-1] if cloud_errors else "Unknown error"}',
                    'source': 'none',
                    'cloud_errors': cloud_errors
                }
                
        except Exception as e:
            logger.error(f"License validation error: {str(e)}")
            
            # Try offline fallback on unexpected errors
            if self.offline_fallback_enabled:
                logger.info("🔄 Unexpected error, trying repository validation...")
                try:
                    offline_result = self._offline_license_validation_refactored(license_key)
                    offline_result['source'] = 'offline'
                    offline_result['reason'] = 'exception_fallback'
                    offline_result['original_error'] = str(e)
                    return offline_result
                except Exception as offline_error:
                    logger.error(f"❌ Repository fallback also failed: {str(offline_error)}")
            
            return {'success': False, 'valid': False, 'error': str(e)}
    
    def _offline_license_validation_refactored(self, license_key: str) -> Dict[str, Any]:
        """
        REFACTORED: Use repository instead of raw database queries
        ELIMINATES: Database patterns, JSON parsing, expiry validation
        """
        try:
            logger.info("🔄 Starting repository-based offline validation...")
            
            # Use repository from Phase 1
            repository = self._get_repository()
            if not repository:
                logger.error("❌ Repository not available for offline validation")
                return {
                    'success': False,
                    'valid': False,
                    'error': 'Repository unavailable for offline validation'
                }
            
            # Get license using unified repository method
            license_data = repository.get_license_by_key(license_key)
            
            if not license_data:
                logger.info(f"❌ License not found in repository: {license_key[:12]}...")
                return {
                    'success': True,
                    'valid': False,
                    'error': 'License not found in local database'
                }
            
            # Use repository's unified expiry validation
            expiry_result = repository.check_license_expiry(license_data)
            
            if expiry_result['expired']:
                logger.warning(f"❌ License found but expired: {expiry_result.get('expired_date')}")
                return {
                    'success': True,
                    'valid': False,
                    'error': f"License expired: {expiry_result.get('message', 'Unknown date')}",
                    'data': {
                        'customer_email': license_data.get('customer_email'),
                        'product_type': license_data.get('product_type'),
                        'expires_at': license_data.get('expires_at'),
                        'status': 'expired'
                    }
                }
            
            # License is valid - return structured data
            logger.info(f"✅ License validated offline via repository")
            return {
                'success': True,
                'valid': True,
                'data': {
                    'customer_email': license_data.get('customer_email'),
                    'product_type': license_data.get('product_type'),
                    'features': license_data.get('features', []),  # Already parsed by repository
                    'expires_at': license_data.get('expires_at'),
                    'license_key': license_key,
                    'status': 'active',
                    'validation_method': 'repository'
                }
            }
                
        except Exception as e:
            logger.error(f"❌ Repository validation error: {str(e)}")
            return {
                'success': False,
                'valid': False,
                'error': f'Repository validation failed: {str(e)}'
            }
    
    def get_user_licenses(self, customer_email: str) -> Dict[str, Any]:
        """Get user licenses - UNCHANGED"""
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
                return {'success': True, 'data': result}
            else:
                error_msg = f"License retrieval failed: HTTP {response.status_code}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"License retrieval error: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def get_packages(self) -> Dict[str, Any]:
        """Get packages from CloudFunction pricing service instead of hardcode"""
        try:
            logger.info("📦 Fetching packages from CloudFunction pricing service...")
            
            # Use CloudFunction pricing service as single source
            from modules.pricing.cloud_pricing_client import get_cloud_pricing_client
            pricing_client = get_cloud_pricing_client()
            pricing_data = pricing_client.fetch_pricing_for_upgrade()
            
            if pricing_data.get('success'):
                packages = pricing_data.get('packages', {})
                logger.info(f"✅ Retrieved {len(packages)} packages from CloudFunction")
                return {'success': True, 'packages': packages}
            else:
                logger.error(f"❌ CloudFunction pricing failed: {pricing_data.get('error')}")
                return {'success': False, 'error': pricing_data.get('error', 'Pricing service unavailable')}
                
        except Exception as e:
            logger.error(f"❌ Package retrieval error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection - SIMPLIFIED"""
        try:
            logger.info("🔌 Testing cloud function connectivity...")
            
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
            return {'success': False, 'status': 'timeout', 'error': 'Request timeout (>5s)'}
        except requests.exceptions.ConnectionError as e:
            return {'success': False, 'status': 'disconnected', 'error': f'Connection error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'status': 'error', 'error': str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status including environment configuration"""
        try:
            logger.info("🔍 Getting system status...")
            
            return {
                'success': True,
                'environment': {
                    'unified_redirect_url': self.unified_redirect_url,
                    'timeout': self.timeout,
                    'retry_attempts': self.retry_attempts,
                    'offline_fallback_enabled': self.offline_fallback_enabled,
                    'endpoints_configured': all(url for url in self.endpoints.values())
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ System status failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Health check - STREAMLINED"""
        try:
            logger.info("🏥 Running health check...")
            
            health_status = {}
            overall_healthy = True
            
            for service, url in self.endpoints.items():
                try:
                    health_url = f"{url}?action=health"
                    response = requests.get(health_url, timeout=10)
                    
                    if response.status_code == 200:
                        health_status[service] = {
                            'status': 'healthy',
                            'response_time_ms': int(response.elapsed.total_seconds() * 1000)
                        }
                    else:
                        health_status[service] = {
                            'status': 'unhealthy',
                            'status_code': response.status_code
                        }
                        overall_healthy = False
                        
                except requests.exceptions.Timeout:
                    health_status[service] = {'status': 'timeout'}
                    overall_healthy = False
                except Exception as e:
                    health_status[service] = {'status': 'unreachable', 'error': str(e)}
                    overall_healthy = False
            
            healthy_count = sum(1 for s in health_status.values() if s.get('status') == 'healthy')
            total_count = len(health_status)
            
            return {
                'success': True,
                'overall_status': 'healthy' if overall_healthy else 'degraded',
                'services_healthy': f"{healthy_count}/{total_count}",
                'services': health_status,
                'timestamp': datetime.now().isoformat(),
                'offline_fallback_enabled': self.offline_fallback_enabled
            }
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== TRIAL SYSTEM METHODS ====================

    def check_trial_eligibility(self, machine_fingerprint: str) -> Dict[str, Any]:
        """
        Check if machine is eligible for trial

        Args:
            machine_fingerprint: Unique machine identifier

        Returns:
            Trial eligibility result
        """
        try:
            logger.info(f"🔍 Checking trial eligibility for: {machine_fingerprint[:16]}...")

            # Quick connectivity check
            has_internet = self._check_internet_connectivity()
            if not has_internet:
                logger.warning("⚠️ No internet connectivity - trial check unavailable")
                return {
                    'success': False,
                    'data': {
                        'eligible': False,
                        'reason': 'no_internet',
                        'message': 'No internet connection - trial check unavailable'
                    }
                }

            # Prepare request data
            request_data = {
                'action': 'check_trial_eligibility',
                'machine_fingerprint': machine_fingerprint,
                'app_version': self.user_agent,
                'timestamp': datetime.now().isoformat()
            }

            # Try trial eligibility check with retry logic
            trial_errors = []
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"🌐 Trial eligibility attempt {attempt + 1}/{self.retry_attempts}")

                    response = requests.post(
                        self.endpoints['license_service'],
                        json=request_data,
                        timeout=self.license_timeout,
                        headers=self.default_headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ Trial eligibility check completed")
                        return {
                            'success': True,
                            'data': {
                                'eligible': result.get('eligible', False),
                                'reason': result.get('reason'),
                                'trial_data': result.get('trial_data', {}),
                                'message': result.get('message', '')
                            }
                        }
                    else:
                        error_msg = f"Trial eligibility check failed: HTTP {response.status_code}"
                        trial_errors.append(error_msg)
                        if 400 <= response.status_code < 500:
                            break  # Don't retry client errors

                except requests.exceptions.Timeout:
                    trial_errors.append(f"Trial check timeout (attempt {attempt + 1})")
                except requests.exceptions.ConnectionError as e:
                    trial_errors.append(f"Connection error (attempt {attempt + 1}): {str(e)[:50]}")
                except Exception as e:
                    trial_errors.append(f"Unexpected error (attempt {attempt + 1}): {str(e)[:50]}")

                # Short delay between retries
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(1)

            # All attempts failed
            logger.warning(f"⚠️ Trial eligibility check failed after {self.retry_attempts} attempts")
            return {
                'success': False,
                'data': {
                    'eligible': False,
                    'reason': 'cloud_failed',
                    'message': f'Trial eligibility check failed: {trial_errors[-1] if trial_errors else "Unknown error"}'
                }
            }

        except Exception as e:
            logger.error(f"Trial eligibility check error: {str(e)}")
            return {
                'success': False,
                'data': {
                    'eligible': False,
                    'reason': 'exception',
                    'message': str(e)
                }
            }

    def generate_trial_license(self, machine_fingerprint: str) -> Dict[str, Any]:
        """
        Generate trial license for eligible machine

        Args:
            machine_fingerprint: Unique machine identifier

        Returns:
            Generated trial license data
        """
        try:
            logger.info(f"🔄 Generating trial license for: {machine_fingerprint[:16]}...")

            # Quick connectivity check
            has_internet = self._check_internet_connectivity()
            if not has_internet:
                logger.warning("⚠️ No internet connectivity - trial generation unavailable")
                return {
                    'success': False,
                    'error': 'No internet connection - trial generation unavailable'
                }

            # Get current user email for proper trial attribution
            try:
                from modules.db_utils.safe_connection import safe_db_connection
                user_email = None

                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT gmail_address FROM user_profiles ORDER BY last_login DESC LIMIT 1")
                    row = cursor.fetchone()
                    if row:
                        user_email = row[0]
            except Exception as e:
                logger.warning(f"Failed to get user email: {e}")
                user_email = None

            # Prepare request data
            request_data = {
                'action': 'generate_trial_license',
                'machine_fingerprint': machine_fingerprint,
                'customer_email': user_email,  # Add real user email
                'app_version': self.user_agent,
                'timestamp': datetime.now().isoformat(),
                'trial_duration_days': 14  # Match Cloud Function: 14-day trial
            }

            # Try trial license generation with retry logic
            generation_errors = []
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"🌐 Trial generation attempt {attempt + 1}/{self.retry_attempts}")

                    response = requests.post(
                        self.endpoints['license_service'],
                        json=request_data,
                        timeout=self.license_timeout,
                        headers=self.default_headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if result.get('success'):
                            logger.info(f"✅ Trial license generated: {result.get('trial_license_key', 'unknown')[:12]}...")
                            return {
                                'success': True,
                                'data': {
                                    'trial_license_key': result.get('trial_license_key'),
                                    'license_key': result.get('trial_license_key'),  # Alias for compatibility
                                    'license_data': result.get('license_data', {}),
                                    'expires_at': result.get('expires_at'),
                                    'trial_duration_days': result.get('trial_duration_days', 14),
                                    'message': result.get('message', '')
                                }
                            }
                        else:
                            error_msg = result.get('error', 'Trial generation failed')
                            generation_errors.append(error_msg)
                            break  # Don't retry if server says it failed
                    else:
                        error_msg = f"Trial generation failed: HTTP {response.status_code}"
                        generation_errors.append(error_msg)
                        if 400 <= response.status_code < 500:
                            break  # Don't retry client errors

                except requests.exceptions.Timeout:
                    generation_errors.append(f"Trial generation timeout (attempt {attempt + 1})")
                except requests.exceptions.ConnectionError as e:
                    generation_errors.append(f"Connection error (attempt {attempt + 1}): {str(e)[:50]}")
                except Exception as e:
                    generation_errors.append(f"Unexpected error (attempt {attempt + 1}): {str(e)[:50]}")

                # Short delay between retries
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(1)

            # All attempts failed
            logger.warning(f"⚠️ Trial license generation failed after {self.retry_attempts} attempts")
            return {
                'success': False,
                'error': f'Trial license generation failed: {generation_errors[-1] if generation_errors else "Unknown error"}'
            }

        except Exception as e:
            logger.error(f"Trial license generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    # ==================== ACTIVATION TRACKING METHODS ====================

    def check_activation(self, license_key: str, machine_fingerprint: str) -> Dict[str, Any]:
        """
        Check if license can be activated on this machine.
        Calls Cloud Function as source of truth.

        Args:
            license_key: License key to check
            machine_fingerprint: Unique machine identifier

        Returns:
            {
                'success': bool,
                'can_activate': bool,
                'reason': str,
                'license_data': dict,
                'error': str (if failed)
            }
        """
        try:
            logger.info(f"🔍 Checking activation for: {license_key[:12]}... on {machine_fingerprint[:16]}...")

            # Check internet connectivity
            has_internet = self._check_internet_connectivity()
            if not has_internet:
                logger.warning("⚠️ No internet connectivity - activation check unavailable")
                return {
                    'success': False,
                    'can_activate': False,
                    'error': 'No internet connection - please check your internet connection'
                }

            # Prepare request data
            request_data = {
                'action': 'check_activation',
                'license_key': license_key,
                'machine_fingerprint': machine_fingerprint
            }

            # Try activation check with retry logic
            activation_errors = []
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"🌐 Activation check attempt {attempt + 1}/{self.retry_attempts}")

                    response = requests.post(
                        self.endpoints['license_service'],
                        json=request_data,
                        timeout=self.license_timeout,
                        headers=self.default_headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ Activation check completed: {result.get('reason')}")
                        return {
                            'success': True,
                            **result
                        }
                    else:
                        error_msg = f"Activation check failed: HTTP {response.status_code}"
                        activation_errors.append(error_msg)
                        if 400 <= response.status_code < 500:
                            try:
                                error_data = response.json()
                                return {
                                    'success': False,
                                    'can_activate': False,
                                    'error': error_data.get('error', error_msg),
                                    'status_code': response.status_code
                                }
                            except:
                                pass
                            break  # Don't retry client errors

                except requests.exceptions.Timeout:
                    activation_errors.append(f"Activation check timeout (attempt {attempt + 1})")
                except requests.exceptions.ConnectionError as e:
                    activation_errors.append(f"Connection error (attempt {attempt + 1}): {str(e)[:50]}")
                except Exception as e:
                    activation_errors.append(f"Unexpected error (attempt {attempt + 1}): {str(e)[:50]}")

                # Short delay between retries
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(1)

            # All attempts failed
            logger.warning(f"⚠️ Activation check failed after {self.retry_attempts} attempts")
            return {
                'success': False,
                'can_activate': False,
                'error': f'Connection timeout - please check your internet connection'
            }

        except Exception as e:
            logger.error(f"Activation check error: {str(e)}")
            return {
                'success': False,
                'can_activate': False,
                'error': str(e)
            }

    def record_activation(self, license_key: str, machine_fingerprint: str, device_info: Dict = None) -> Dict[str, Any]:
        """
        Record activation on Cloud.
        Calls Cloud Function as source of truth.

        Args:
            license_key: License key to activate
            machine_fingerprint: Unique machine identifier
            device_info: Optional device information

        Returns:
            {
                'success': bool,
                'activation_id': str,
                'error': str (if failed)
            }
        """
        try:
            logger.info(f"🔄 Recording activation for: {license_key[:12]}... on {machine_fingerprint[:16]}...")

            # Check internet connectivity
            has_internet = self._check_internet_connectivity()
            if not has_internet:
                logger.warning("⚠️ No internet connectivity - activation recording unavailable")
                return {
                    'success': False,
                    'error': 'No internet connection - please check your internet connection'
                }

            # Prepare device info if not provided
            if device_info is None:
                device_info = self._get_device_info()

            # Prepare request data
            request_data = {
                'action': 'record_activation',
                'license_key': license_key,
                'machine_fingerprint': machine_fingerprint,
                'device_info': device_info
            }

            # Try recording with retry logic
            record_errors = []
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"🌐 Record activation attempt {attempt + 1}/{self.retry_attempts}")

                    response = requests.post(
                        self.endpoints['license_service'],
                        json=request_data,
                        timeout=self.license_timeout,
                        headers=self.default_headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ Activation recorded: {result.get('activation_id', 'unknown')}")
                        return {
                            'success': True,
                            **result
                        }
                    elif response.status_code == 403:
                        # Activation denied
                        try:
                            error_data = response.json()
                            return {
                                'success': False,
                                'error': error_data.get('error', 'Activation denied'),
                                'details': error_data.get('details')
                            }
                        except:
                            return {
                                'success': False,
                                'error': 'Activation denied by server'
                            }
                    else:
                        error_msg = f"Record activation failed: HTTP {response.status_code}"
                        record_errors.append(error_msg)
                        if 400 <= response.status_code < 500:
                            break  # Don't retry client errors

                except requests.exceptions.Timeout:
                    record_errors.append(f"Record activation timeout (attempt {attempt + 1})")
                except requests.exceptions.ConnectionError as e:
                    record_errors.append(f"Connection error (attempt {attempt + 1}): {str(e)[:50]}")
                except Exception as e:
                    record_errors.append(f"Unexpected error (attempt {attempt + 1}): {str(e)[:50]}")

                # Short delay between retries
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(1)

            # All attempts failed
            logger.warning(f"⚠️ Record activation failed after {self.retry_attempts} attempts")
            return {
                'success': False,
                'error': f'Connection timeout - please check your internet connection'
            }

        except Exception as e:
            logger.error(f"Record activation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def deactivate(self, license_key: str, machine_fingerprint: str) -> Dict[str, Any]:
        """
        Deactivate license on this machine.
        Calls Cloud Function to remove activation.

        Args:
            license_key: License key to deactivate
            machine_fingerprint: Unique machine identifier

        Returns:
            {
                'success': bool,
                'error': str (if failed)
            }
        """
        try:
            logger.info(f"🔄 Deactivating license: {license_key[:12]}... on {machine_fingerprint[:16]}...")

            # Check internet connectivity
            has_internet = self._check_internet_connectivity()
            if not has_internet:
                logger.warning("⚠️ No internet connectivity - deactivation unavailable")
                return {
                    'success': False,
                    'error': 'No internet connection - please check your internet connection'
                }

            # Prepare request data
            request_data = {
                'action': 'deactivate',
                'license_key': license_key,
                'machine_fingerprint': machine_fingerprint
            }

            # Try deactivation with retry logic
            deactivate_errors = []
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"🌐 Deactivation attempt {attempt + 1}/{self.retry_attempts}")

                    response = requests.post(
                        self.endpoints['license_service'],
                        json=request_data,
                        timeout=self.license_timeout,
                        headers=self.default_headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ License deactivated successfully")
                        return {
                            'success': True,
                            **result
                        }
                    else:
                        error_msg = f"Deactivation failed: HTTP {response.status_code}"
                        deactivate_errors.append(error_msg)
                        if 400 <= response.status_code < 500:
                            try:
                                error_data = response.json()
                                return {
                                    'success': False,
                                    'error': error_data.get('error', error_msg)
                                }
                            except:
                                pass
                            break  # Don't retry client errors

                except requests.exceptions.Timeout:
                    deactivate_errors.append(f"Deactivation timeout (attempt {attempt + 1})")
                except requests.exceptions.ConnectionError as e:
                    deactivate_errors.append(f"Connection error (attempt {attempt + 1}): {str(e)[:50]}")
                except Exception as e:
                    deactivate_errors.append(f"Unexpected error (attempt {attempt + 1}): {str(e)[:50]}")

                # Short delay between retries
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(1)

            # All attempts failed
            logger.warning(f"⚠️ Deactivation failed after {self.retry_attempts} attempts")
            return {
                'success': False,
                'error': f'Connection timeout - please check your internet connection'
            }

        except Exception as e:
            logger.error(f"Deactivation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information for activation record."""
        import platform
        import socket
        import uuid

        try:
            return {
                'os': f"{platform.system()} {platform.release()}",
                'hostname': socket.gethostname(),
                'mac_address': ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                                        for ele in range(0, 48, 8)][::-1]),
                'app_version': self.user_agent,
                'python_version': platform.python_version()
            }
        except Exception as e:
            logger.warning(f"Failed to get device info: {e}")
            return {
                'os': 'unknown',
                'hostname': 'unknown',
                'app_version': self.user_agent
            }

# Singleton management - UNCHANGED
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

def validate_cloud_integration() -> tuple[bool, list[str]]:
    """Validate cloud integration setup - SIMPLIFIED"""
    issues = []
    
    try:
        required_urls = ['CLOUD_PAYMENT_URL', 'CLOUD_WEBHOOK_URL', 'CLOUD_LICENSE_URL']
        for url_name in required_urls:
            if not os.getenv(url_name):
                issues.append(f"Missing environment variable: {url_name}")
        
        if not issues:
            try:
                client = get_cloud_client()
                logger.info("✅ Cloud client initialized successfully (refactored)")
            except Exception as e:
                issues.append(f"Client initialization failed: {str(e)}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Validation error: {str(e)}")
        return False, issues