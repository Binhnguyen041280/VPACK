"""
License validation for app startup with offline support
"""
import logging
import socket
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .license_manager import LicenseManager
from .license_config import AUTO_CHECK_ON_STARTUP, GRACE_PERIOD_DAYS, CLOUD_VALIDATION_TIMEOUT

logger = logging.getLogger(__name__)

class LicenseChecker:
    """Handles license checking during app startup with offline support"""
    
    def __init__(self):
        self.license_manager = LicenseManager()
        self._connection_cache = {'online': None, 'last_check': None}
        self._last_cloud_validation = None
    
    def startup_license_check(self) -> Dict[str, Any]:
        """
        Main license check for app startup with offline support
        Returns action to take based on license status
        """
        try:
            if not AUTO_CHECK_ON_STARTUP:
                return {'action': 'continue', 'message': 'License check disabled'}
            
            logger.info("Starting enhanced license validation with offline support...")
            
            # Check connectivity status
            is_online = self._check_internet_connectivity()
            logger.info(f"🌐 Network status: {'Online' if is_online else 'Offline'}")
            
            # Get local license status first (priority)
            status_result = self.license_manager.get_license_status()
            
            # Enhance with offline/online context
            status_result['network_status'] = 'online' if is_online else 'offline'
            status_result['validation_source'] = 'local'
            
            # Handle no license case
            if status_result['status'] == 'no_license':
                message = 'Please enter license key to continue'
                if not is_online:
                    message += ' (Offline mode - will validate when online)'
                    
                return {
                    'action': 'show_license_input',
                    'status': 'no_license',
                    'message': message,
                    'ui_component': 'license_input_dialog',
                    'network_status': status_result['network_status']
                }
            
            elif status_result['status'] == 'invalid':
                reason = status_result.get('reason', 'unknown')
                
                if reason == 'expired':
                    # Check if within grace period for offline usage
                    grace_result = self._check_grace_period(status_result.get('license'))
                    
                    if grace_result['in_grace'] and not is_online:
                        return {
                            'action': 'show_grace_warning',
                            'status': 'expired_grace_period',
                            'message': f'License expired but grace period active (offline). {grace_result["days_remaining"]} days remaining.',
                            'ui_component': 'grace_period_dialog',
                            'license': status_result.get('license'),
                            'network_status': status_result['network_status'],
                            'grace_days_remaining': grace_result['days_remaining']
                        }
                    else:
                        return {
                            'action': 'show_expired_warning',
                            'status': 'expired',
                            'message': 'License has expired. Please renew.',
                            'ui_component': 'license_renewal_dialog',
                            'license': status_result.get('license'),
                            'network_status': status_result['network_status']
                        }
                else:
                    # For other invalid reasons, allow grace period if offline
                    if not is_online and self._can_use_offline_grace(status_result):
                        return {
                            'action': 'continue_offline',
                            'status': 'offline_grace',
                            'message': 'Running in offline mode - will validate when online',
                            'network_status': status_result['network_status']
                        }
                    else:
                        return {
                            'action': 'show_invalid_warning',
                            'status': 'invalid',
                            'message': f'License is invalid: {reason}',
                            'ui_component': 'license_error_dialog',
                            'network_status': status_result['network_status']
                        }
            
            elif status_result['status'] == 'valid':
                license_data = status_result.get('license')
                
                # Try cloud validation if online for additional security
                if is_online and license_data:
                    cloud_result = self._attempt_cloud_validation(license_data.get('license_key'))
                    if cloud_result:
                        status_result['validation_source'] = 'cloud_verified'
                        status_result['last_cloud_check'] = datetime.now().isoformat()
                
                # Check if approaching expiry
                if license_data:
                    expiry_warning = self._check_expiry_warning(license_data)
                    
                    if expiry_warning:
                        message = expiry_warning['message']
                        if not is_online:
                            message += ' (Offline mode - check online for renewal)'
                            
                        return {
                            'action': 'show_expiry_warning',
                            'status': 'valid_expiring',
                            'message': message,
                            'ui_component': 'expiry_warning_dialog',
                            'days_remaining': expiry_warning['days_remaining'],
                            'network_status': status_result['network_status'],
                            'validation_source': status_result['validation_source']
                        }
                
                # Success message with network status
                success_message = 'License valid - continuing startup'
                if not is_online:
                    success_message += ' (Offline mode)'
                elif status_result.get('validation_source') == 'cloud_verified':
                    success_message += ' (Cloud verified)'
                
                return {
                    'action': 'continue',
                    'status': 'valid',
                    'message': success_message,
                    'license': status_result.get('license'),
                    'network_status': status_result['network_status'],
                    'validation_source': status_result['validation_source']
                }
            
            else:
                # Unknown status - handle gracefully based on network
                if not is_online:
                    return {
                        'action': 'continue_offline',
                        'status': 'offline_unknown',
                        'message': 'Running in offline mode - license status unclear',
                        'network_status': 'offline'
                    }
                else:
                    return {
                        'action': 'show_error',
                        'status': 'error',
                        'message': 'Unknown license status',
                        'ui_component': 'license_error_dialog',
                        'network_status': 'online'
                    }
                
        except Exception as e:
            logger.error(f"Startup license check failed: {e}")
            
            # Graceful degradation for errors
            is_online = self._check_internet_connectivity()
            if not is_online:
                logger.info("Error occurred offline - allowing degraded access")
                return {
                    'action': 'continue_offline',
                    'status': 'offline_error',
                    'message': 'Running in offline mode due to license check error',
                    'network_status': 'offline',
                    'error_details': str(e)
                }
            else:
                return {
                    'action': 'show_error',
                    'status': 'error',
                    'message': f'License check failed: {str(e)}',
                    'ui_component': 'license_error_dialog',
                    'network_status': 'online'
                }
    
    def _check_expiry_warning(self, license_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Check if license is approaching expiry"""
        if not license_data:
            return None
        
        expires_at = license_data.get('expires_at')
        if not expires_at:
            return None  # No expiry date
        
        try:
            from datetime import datetime, timedelta
            from .license_config import SHOW_EXPIRY_WARNING_DAYS
            
            expiry_date = datetime.fromisoformat(expires_at)
            warning_date = expiry_date - timedelta(days=SHOW_EXPIRY_WARNING_DAYS)
            
            if datetime.now() > warning_date:
                days_remaining = (expiry_date - datetime.now()).days
                return {
                    'warning': True,
                    'days_remaining': days_remaining,
                    'message': f'License expires in {days_remaining} days'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Expiry warning check failed: {e}")
            return None

    def _check_internet_connectivity(self) -> bool:
        """
        Check if internet connection is available
        Uses cached result for efficiency
        """
        try:
            # Check cache first (cache for 30 seconds)
            now = datetime.now()
            if self._connection_cache['last_check'] and self._connection_cache['online'] is not None:
                cache_age = (now - self._connection_cache['last_check']).total_seconds()
                if cache_age < 30:
                    return bool(self._connection_cache['online'])
            
            # Test connectivity with multiple methods
            connectivity_tests = [
                self._test_dns_resolution,
                self._test_http_connection,
                self._test_socket_connection
            ]
            
            for test in connectivity_tests:
                try:
                    if test():
                        self._connection_cache = {'online': True, 'last_check': now}
                        return True
                except Exception:
                    continue
            
            # All tests failed
            self._connection_cache = {'online': False, 'last_check': now}
            return False
            
        except Exception as e:
            logger.warning(f"Connectivity check failed: {e}")
            # Conservative approach - assume offline if check fails
            return False

    def _test_dns_resolution(self) -> bool:
        """Test DNS resolution"""
        try:
            socket.getaddrinfo('google.com', 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
            return True
        except socket.error:
            return False

    def _test_http_connection(self) -> bool:
        """Test HTTP connection"""
        try:
            response = requests.get('https://httpbin.org/status/200', timeout=3)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _test_socket_connection(self) -> bool:
        """Test raw socket connection"""
        try:
            sock = socket.create_connection(('8.8.8.8', 53), timeout=3)
            sock.close()
            return True
        except socket.error:
            return False

    def _check_grace_period(self, license_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check if license is within grace period for offline usage
        """
        try:
            if not license_data:
                return {'in_grace': False, 'days_remaining': 0}
            
            expires_at = license_data.get('expires_at')
            if not expires_at:
                return {'in_grace': False, 'days_remaining': 0}
            
            expiry_date = datetime.fromisoformat(expires_at)
            grace_end_date = expiry_date + timedelta(days=GRACE_PERIOD_DAYS)
            now = datetime.now()
            
            if now <= grace_end_date:
                days_remaining = (grace_end_date - now).days
                return {
                    'in_grace': True,
                    'days_remaining': max(0, days_remaining),
                    'grace_end_date': grace_end_date.isoformat()
                }
            else:
                return {'in_grace': False, 'days_remaining': 0}
                
        except Exception as e:
            logger.error(f"Grace period check failed: {e}")
            return {'in_grace': False, 'days_remaining': 0}

    def _can_use_offline_grace(self, status_result: Dict[str, Any]) -> bool:
        """
        Determine if offline grace period can be used
        """
        try:
            # Allow grace for certain scenarios when offline
            license_data = status_result.get('license')
            if not license_data:
                return False
            
            # Check last successful validation time
            last_validation = license_data.get('last_validation')
            if last_validation:
                last_validation_date = datetime.fromisoformat(last_validation)
                grace_cutoff = datetime.now() - timedelta(days=GRACE_PERIOD_DAYS)
                
                # Allow if last validation was within grace period
                if last_validation_date > grace_cutoff:
                    return True
            
            # Check if license was recently valid
            created_at = license_data.get('created_at') or license_data.get('activated_at')
            if created_at:
                created_date = datetime.fromisoformat(created_at)
                grace_cutoff = datetime.now() - timedelta(days=GRACE_PERIOD_DAYS)
                
                # Allow if license was created/activated recently
                if created_date > grace_cutoff:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Offline grace check failed: {e}")
            return False

    def _attempt_cloud_validation(self, license_key: str) -> bool:
        """
        Attempt cloud validation when online
        Returns True if validation succeeded
        """
        try:
            if not license_key:
                return False
            
            # Import cloud client
            try:
                from ..payments.cloud_function_client import get_cloud_client
            except ImportError:
                from backend.modules.payments.cloud_function_client import get_cloud_client
            
            cloud_client = get_cloud_client()
            result = cloud_client.validate_license(license_key)
            
            if result.get('success') and result.get('valid'):
                logger.info("✅ Cloud validation successful")
                self._last_cloud_validation = datetime.now().isoformat()
                
                # Update local database with cloud validation timestamp
                self._update_cloud_validation_timestamp(license_key)
                return True
            else:
                logger.warning(f"⚠️ Cloud validation failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.warning(f"Cloud validation attempt failed: {e}")
            return False

    def _update_cloud_validation_timestamp(self, license_key: str):
        """Update local database with cloud validation timestamp"""
        try:
            from ..db_utils import get_db_connection
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE licenses 
                    SET updated_at = ?
                    WHERE license_key = ?
                """, (datetime.now().isoformat(), license_key))
                conn.commit()
                
        except Exception as e:
            logger.warning(f"Failed to update cloud validation timestamp: {e}")

    def get_connectivity_status(self) -> Dict[str, Any]:
        """
        Get detailed connectivity status for debugging
        """
        try:
            is_online = self._check_internet_connectivity()
            
            status = {
                'online': is_online,
                'last_check': self._connection_cache.get('last_check'),
                'last_cloud_validation': self._last_cloud_validation,
                'cache_age_seconds': 0
            }
            
            if self._connection_cache['last_check']:
                cache_age = (datetime.now() - self._connection_cache['last_check']).total_seconds()
                status['cache_age_seconds'] = cache_age
            
            return status
            
        except Exception as e:
            logger.error(f"Connectivity status check failed: {e}")
            return {'online': False, 'error': str(e)}

    def force_online_validation(self, license_key: str) -> Dict[str, Any]:
        """
        Force online validation and sync
        Returns validation result with sync status
        """
        try:
            # Force connectivity check
            self._connection_cache = {'online': None, 'last_check': None}
            is_online = self._check_internet_connectivity()
            
            if not is_online:
                return {
                    'success': False,
                    'error': 'No internet connection available',
                    'network_status': 'offline'
                }
            
            # Attempt cloud validation
            cloud_result = self._attempt_cloud_validation(license_key)
            
            if cloud_result:
                return {
                    'success': True,
                    'validated': True,
                    'network_status': 'online',
                    'validation_source': 'cloud',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': True,
                    'validated': False,
                    'network_status': 'online',
                    'validation_source': 'cloud_failed',
                    'error': 'Cloud validation failed'
                }
                
        except Exception as e:
            logger.error(f"Force online validation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'network_status': 'error'
            }