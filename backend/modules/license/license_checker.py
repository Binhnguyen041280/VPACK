"""
License validation for app startup
"""
import logging
from typing import Dict, Any, Optional
from .license_manager import LicenseManager
from .license_config import AUTO_CHECK_ON_STARTUP

logger = logging.getLogger(__name__)

class LicenseChecker:
    """Handles license checking during app startup"""
    
    def __init__(self):
        self.license_manager = LicenseManager()
    
    def startup_license_check(self) -> Dict[str, Any]:
        """
        Main license check for app startup
        Returns action to take based on license status
        """
        try:
            if not AUTO_CHECK_ON_STARTUP:
                return {'action': 'continue', 'message': 'License check disabled'}
            
            logger.info("Starting license validation...")
            
            # Get license status
            status_result = self.license_manager.get_license_status()
            
            # Determine action based on status
            if status_result['status'] == 'no_license':
                return {
                    'action': 'show_license_input',
                    'status': 'no_license',
                    'message': 'Please enter license key to continue',
                    'ui_component': 'license_input_dialog'
                }
            
            elif status_result['status'] == 'invalid':
                reason = status_result.get('reason', 'unknown')
                
                if reason == 'expired':
                    return {
                        'action': 'show_expired_warning',
                        'status': 'expired',
                        'message': 'License has expired. Please renew.',
                        'ui_component': 'license_renewal_dialog',
                        'license': status_result.get('license')
                    }
                else:
                    return {
                        'action': 'show_invalid_warning',
                        'status': 'invalid',
                        'message': f'License is invalid: {reason}',
                        'ui_component': 'license_error_dialog'
                    }
            
            elif status_result['status'] == 'valid':
                # Check if approaching expiry
                license_data = status_result.get('license')
                if license_data:
                    expiry_warning = self._check_expiry_warning(license_data)
                    
                    if expiry_warning:
                        return {
                            'action': 'show_expiry_warning',
                            'status': 'valid_expiring',
                            'message': expiry_warning['message'],
                            'ui_component': 'expiry_warning_dialog',
                            'days_remaining': expiry_warning['days_remaining']
                        }
                
                return {
                    'action': 'continue',
                    'status': 'valid',
                    'message': 'License valid - continuing startup',
                    'license': status_result.get('license')
                }
            
            else:
                return {
                    'action': 'show_error',
                    'status': 'error',
                    'message': 'Unknown license status',
                    'ui_component': 'license_error_dialog'
                }
                
        except Exception as e:
            logger.error(f"Startup license check failed: {e}")
            return {
                'action': 'show_error',
                'status': 'error',
                'message': f'License check failed: {str(e)}',
                'ui_component': 'license_error_dialog'
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