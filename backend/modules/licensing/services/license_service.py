# backend/modules/licensing/services/license_service.py
"""
V_Track Unified License Service - Phase 2 Refactoring
ELIMINATES: 5 validation flows, 6 database patterns, 4 JSON parsing duplicates
UNIFIES: All license operations into single service with clean API
Created: 2025-08-11 - Phase 2 Step 1
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# Import repository pattern from Phase 1
try:
    from ..repositories.license_repository import get_license_repository
except ImportError:
    try:
        from repositories.license_repository import get_license_repository
    except ImportError:
        get_license_repository = None

# Import database utilities
try:
    from modules.db_utils import get_db_connection
    from modules.db_utils.safe_connection import safe_db_connection
except ImportError:
    try:
        from backend.modules.db_utils import get_db_connection
        from backend.modules.db_utils.safe_connection import safe_db_connection
    except ImportError:
        get_db_connection = None
        safe_db_connection = None

logger = logging.getLogger(__name__)

class ValidationSource(Enum):
    """Validation source types for consistent handling"""
    CLOUD = "cloud"
    OFFLINE = "offline" 
    DATABASE_ONLY = "database_only"
    LOCAL_CACHE = "local_cache"
    NONE = "none"
    ERROR = "error"

class LicenseStatus(Enum):
    """Standardized license status values"""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    NO_LICENSE = "no_license"
    ACTIVATED_ELSEWHERE = "activated_elsewhere"
    PENDING_ACTIVATION = "pending_activation"
    ERROR = "error"

class LicenseService:
    """
    Unified License Service - Single source of truth for all license operations
    ELIMINATES duplicate patterns across payment_routes.py and license_checker.py
    """
    
    def __init__(self):
        """Initialize service with dependency injection"""
        self._repository = None
        self._cloud_client = None
        self._connectivity_checked = False
        self._last_connectivity_check = None
        self._connectivity_cache = None
        
    def _get_repository(self):
        """Lazy load repository with error handling"""
        if self._repository is None and get_license_repository:
            try:
                self._repository = get_license_repository()
                logger.debug("✅ License repository initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize repository: {str(e)}")
                self._repository = None
        return self._repository
    
    def _get_cloud_client(self):
        """Lazy load cloud client with error handling"""
        if self._cloud_client is None:
            try:
                # Import with multiple fallback paths
                try:
                    from ...payments.cloud_function_client import get_cloud_client
                except ImportError:
                    try:
                        from backend.modules.payments.cloud_function_client import get_cloud_client
                    except ImportError:
                        from payments.cloud_function_client import get_cloud_client
                
                self._cloud_client = get_cloud_client()
                logger.debug("✅ Cloud client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Cloud client unavailable: {str(e)}")
                self._cloud_client = None
        return self._cloud_client
    
    # ==================== UNIFIED JSON PARSING ====================
    
    def _parse_features(self, license_data: Dict[str, Any]) -> List[str]:
        """
        Unified features parsing - ELIMINATES 4x duplicate JSON parsing
        Replaces scattered json.loads() calls across files
        """
        try:
            features = license_data.get('features')
            if not features:
                return ['full_access']  # Default fallback
            
            # Already a list
            if isinstance(features, list):
                return features
            
            # Parse JSON string
            if isinstance(features, str):
                try:
                    parsed = json.loads(features)
                    return parsed if isinstance(parsed, list) else ['full_access']
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"⚠️ Invalid features JSON: {features}")
                    return ['full_access']
            
            # Unknown type
            logger.warning(f"⚠️ Unexpected features type: {type(features)}")
            return ['full_access']
            
        except Exception as e:
            logger.error(f"❌ Features parsing failed: {str(e)}")
            return ['full_access']
    
    def _parse_device_info(self, raw_device_info: Any) -> Dict[str, Any]:
        """
        Unified device info parsing - ELIMINATES duplicate JSON parsing
        """
        try:
            if not raw_device_info:
                return {}
            
            if isinstance(raw_device_info, dict):
                return raw_device_info
            
            if isinstance(raw_device_info, str):
                try:
                    return json.loads(raw_device_info)
                except (json.JSONDecodeError, TypeError):
                    return {}
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Device info parsing failed: {str(e)}")
            return {}
    
    # ==================== UNIFIED EXPIRY VALIDATION ====================
    
    def _validate_expiry(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified expiry validation - ELIMINATES 3x duplicate expiry checks
        Replaces scattered datetime parsing and comparison logic
        """
        try:
            expires_at = license_data.get('expires_at')
            
            # No expiry date = lifetime license
            if not expires_at:
                return {
                    'valid': True,
                    'expired': False,
                    'is_lifetime': True,
                    'message': 'Lifetime license - no expiry'
                }
            
            # Parse expiry date with multiple format support
            try:
                if isinstance(expires_at, str):
                    # Handle ISO format with timezone
                    expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                else:
                    expiry_date = expires_at
                
                current_time = datetime.now()
                
                if current_time > expiry_date:
                    # License expired
                    days_expired = (current_time - expiry_date).days
                    return {
                        'valid': False,
                        'expired': True,
                        'days_expired': days_expired,
                        'expired_date': expires_at,
                        'message': f'License expired {days_expired} days ago'
                    }
                else:
                    # License valid
                    days_remaining = (expiry_date - current_time).days
                    
                    # Check if approaching expiry
                    warning_threshold = 7  # days
                    approaching_expiry = days_remaining <= warning_threshold
                    
                    return {
                        'valid': True,
                        'expired': False,
                        'days_remaining': days_remaining,
                        'expires_at': expires_at,
                        'approaching_expiry': approaching_expiry,
                        'message': f'License valid for {days_remaining} days'
                    }
                
            except Exception as date_error:
                logger.error(f"❌ Date parsing failed: {str(date_error)}")
                return {
                    'valid': False,
                    'expired': True,
                    'error': f'Invalid expiry date format: {str(date_error)}',
                    'message': 'Cannot parse expiry date'
                }
                
        except Exception as e:
            logger.error(f"❌ Expiry validation failed: {str(e)}")
            return {
                'valid': False,
                'expired': True,
                'error': str(e),
                'message': 'Expiry validation error'
            }
    
    # ==================== UNIFIED MACHINE FINGERPRINT & ACTIVATION ====================
    
    def _get_machine_fingerprint(self) -> str:
        """
        Get machine fingerprint with fallback handling
        """
        try:
            # Import with multiple fallback paths
            try:
                from ...license.machine_fingerprint import generate_machine_fingerprint
            except ImportError:
                try:
                    from backend.modules.license.machine_fingerprint import generate_machine_fingerprint
                except ImportError:
                    from modules.license.machine_fingerprint import generate_machine_fingerprint
            
            return generate_machine_fingerprint()
            
        except Exception as e:
            logger.error(f"❌ Machine fingerprint generation failed: {str(e)}")
            # Fallback to simple machine identifier
            import platform
            import hashlib
            machine_info = f"{platform.node()}-{platform.machine()}"
            return hashlib.md5(machine_info.encode()).hexdigest()
    
    def _check_activation_status(self, license_id: int) -> Dict[str, Any]:
        """
        Unified activation status check - ELIMINATES 3x duplicate activation logic
        Replaces scattered activation queries and logic
        """
        try:
            if not get_db_connection or not safe_db_connection:
                return {'error': 'Database unavailable', 'can_activate': False}
            
            current_fingerprint = self._get_machine_fingerprint()
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT machine_fingerprint, activation_time, status, device_info
                    FROM license_activations 
                    WHERE license_id = ? AND status = 'active'
                    ORDER BY activation_time DESC
                """, (license_id,))
                
                activations = cursor.fetchall()
                
                if not activations:
                    # No activations - can activate
                    return {
                        'can_activate': True,
                        'activation_status': 'not_activated',
                        'current_machine': current_fingerprint[:16] + "...",
                        'message': 'License not activated on any device'
                    }
                
                # Check if current machine is already activated
                for activation in activations:
                    fingerprint, activation_time, status, device_info = activation
                    
                    if fingerprint == current_fingerprint:
                        # Already activated on this machine
                        parsed_device_info = self._parse_device_info(device_info)
                        
                        return {
                            'can_activate': True,  # Can continue using
                            'activation_status': 'already_activated_this_machine',
                            'current_machine': current_fingerprint[:16] + "...",
                            'activated_at': activation_time,
                            'device_info': parsed_device_info,
                            'message': 'License already activated on this machine'
                        }
                
                # Activated on other machine(s)
                other_activation = activations[0]  # Most recent
                other_fingerprint, other_activation_time, other_status, other_device_info = other_activation
                parsed_other_device_info = self._parse_device_info(other_device_info)
                
                return {
                    'can_activate': False,
                    'activation_status': 'activated_elsewhere',
                    'current_machine': current_fingerprint[:16] + "...",
                    'other_machine': other_fingerprint[:16] + "...",
                    'other_activated_at': other_activation_time,
                    'other_device_info': parsed_other_device_info,
                    'message': f'License already activated on another device at {other_activation_time}'
                }
                
        except Exception as e:
            logger.error(f"❌ Activation status check failed: {str(e)}")
            return {
                'error': str(e),
                'can_activate': False,
                'activation_status': 'error',
                'message': 'Failed to check activation status'
            }
    
    def _create_activation_record(self, license_id: int, validation_source: ValidationSource, 
                                extra_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create activation record with unified device info
        """
        try:
            if not get_db_connection:
                logger.error("❌ Database unavailable for activation")
                return False
            
            current_fingerprint = self._get_machine_fingerprint()
            activation_time = datetime.now().isoformat()
            
            # Prepare device info
            device_info = {
                "activated_via": "license_service",
                "timestamp": activation_time,
                "validation_source": validation_source.value,
                "service_version": "2.0",
                "machine_fingerprint_short": current_fingerprint[:16] + "..."
            }
            
            if extra_info:
                device_info.update(extra_info)
            
            device_info_json = json.dumps(device_info)
            
            if not safe_db_connection:
                logger.error("Database connection unavailable")
                return False
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO license_activations 
                    (license_id, machine_fingerprint, activation_time, status, device_info)
                    VALUES (?, ?, ?, 'active', ?)
                """, (license_id, current_fingerprint, activation_time, device_info_json))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ Activation record created for license {license_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to create activation record for license {license_id}")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Activation record creation failed: {str(e)}")
            return False
    
    # ==================== UNIFIED VALIDATION FLOWS ====================
    
    def validate_license_comprehensive(self, license_key: str, 
                                     strict_mode: bool = False,
                                     force_online: bool = False) -> Dict[str, Any]:
        """
        Comprehensive license validation - UNIFIES 5 validation flows
        This replaces all scattered validation logic across files
        
        Args:
            license_key: License key to validate
            strict_mode: If True, requires cloud validation when online
            force_online: If True, attempts cloud validation even if offline cached
            
        Returns:
            Unified validation result with consistent structure
        """
        try:
            logger.info(f"🔍 Starting comprehensive validation: {license_key[:12]}...")
            
            validation_result = {
                'valid': False,
                'license_data': None,
                'validation_source': ValidationSource.NONE.value,
                'checks_performed': [],
                'checks_passed': [],
                'checks_failed': [],
                'warnings': [],
                'timestamp': datetime.now().isoformat(),
                'strict_mode': strict_mode,
                'force_online': force_online
            }
            
            # Step 1: Basic format validation
            if not license_key or len(license_key) < 10:
                validation_result['checks_failed'].append('format_validation')
                validation_result['error'] = 'Invalid license key format'
                return validation_result
            
            validation_result['checks_passed'].append('format_validation')
            validation_result['checks_performed'].append('format_validation')
            
            # Step 2: Obviously invalid patterns check
            if self._is_obviously_invalid_license(license_key):
                validation_result['checks_failed'].append('obvious_invalid_check')
                validation_result['error'] = 'License key matches invalid patterns'
                return validation_result
            
            validation_result['checks_passed'].append('obvious_invalid_check')
            validation_result['checks_performed'].append('obvious_invalid_check')
            
            # Step 3: Database validation (always first)
            repository = self._get_repository()
            if repository:
                db_validation = repository.validate_license_integrity(license_key)
                validation_result['checks_performed'].append('database_integrity')
                
                if db_validation['valid']:
                    validation_result['checks_passed'].append('database_integrity')
                    validation_result['license_data'] = db_validation['license_data']
                    validation_result['validation_source'] = ValidationSource.DATABASE_ONLY.value
                    
                    # Parse features using unified parser
                    validation_result['license_data']['features'] = self._parse_features(
                        validation_result['license_data']
                    )
                    
                    # Step 4: Expiry validation using unified method
                    expiry_result = self._validate_expiry(validation_result['license_data'])
                    validation_result['checks_performed'].append('expiry_validation')
                    validation_result['expiry_details'] = expiry_result
                    
                    if expiry_result['valid']:
                        validation_result['checks_passed'].append('expiry_validation')
                    else:
                        validation_result['checks_failed'].append('expiry_validation')
                        validation_result['expired'] = True
                        
                        if strict_mode:
                            validation_result['error'] = expiry_result['message']
                            return validation_result
                        else:
                            validation_result['warnings'].append(f"License expired: {expiry_result['message']}")
                    
                else:
                    validation_result['checks_failed'].append('database_integrity')
                    if strict_mode:
                        validation_result['error'] = db_validation['error']
                        return validation_result
                    validation_result['warnings'].append(f"Database integrity issue: {db_validation['error']}")
            
            # Step 5: Cloud validation (if online and requested)
            cloud_client = self._get_cloud_client()
            if cloud_client and (force_online or strict_mode or not validation_result.get('license_data')):
                try:
                    cloud_result = cloud_client.validate_license(license_key)
                    validation_result['checks_performed'].append('cloud_validation')
                    
                    if cloud_result.get('success') and cloud_result.get('source') == 'cloud':
                        validation_result['checks_passed'].append('cloud_validation')
                        validation_result['validation_source'] = ValidationSource.CLOUD.value
                        
                        # Cloud data takes precedence if available
                        if cloud_result.get('data'):
                            validation_result['license_data'] = cloud_result['data']
                            validation_result['license_data']['features'] = self._parse_features(
                                validation_result['license_data']
                            )
                        
                        logger.info(f"✅ Cloud validation successful: {license_key[:12]}...")
                        
                    elif cloud_result.get('source') == 'offline':
                        validation_result['checks_passed'].append('cloud_validation_offline')
                        validation_result['validation_source'] = ValidationSource.OFFLINE.value
                        validation_result['warnings'].append('Cloud validation performed offline')
                        
                    else:
                        validation_result['checks_failed'].append('cloud_validation')
                        if strict_mode:
                            validation_result['error'] = f"Cloud validation failed: {cloud_result.get('error', 'Unknown')}"
                            return validation_result
                        validation_result['warnings'].append(f"Cloud validation failed: {cloud_result.get('error', 'Unknown')}")
                        
                except Exception as cloud_error:
                    validation_result['checks_failed'].append('cloud_validation')
                    validation_result['warnings'].append(f"Cloud validation error: {str(cloud_error)}")
                    logger.warning(f"⚠️ Cloud validation error: {str(cloud_error)}")
            
            # Final decision logic
            critical_failures = [check for check in ['format_validation', 'obvious_invalid_check'] 
                               if check in validation_result['checks_failed']]
            
            if critical_failures:
                validation_result['valid'] = False
                validation_result['error'] = f"Critical validation failures: {critical_failures}"
                validation_result['status'] = LicenseStatus.INVALID.value
            elif validation_result.get('license_data'):
                validation_result['valid'] = True
                
                if validation_result.get('expired'):
                    validation_result['status'] = LicenseStatus.EXPIRED.value
                    validation_result['message'] = f"License expired but data available ({validation_result['validation_source']})"
                else:
                    validation_result['status'] = LicenseStatus.VALID.value
                    validation_result['message'] = f"License valid ({validation_result['validation_source']})"
            else:
                validation_result['valid'] = False
                validation_result['status'] = LicenseStatus.NO_LICENSE.value
                validation_result['error'] = 'No valid license data found'
            
            # Add validation summary
            validation_result['validation_summary'] = {
                'total_checks': len(validation_result['checks_performed']),
                'passed_checks': len(validation_result['checks_passed']),
                'failed_checks': len(validation_result['checks_failed']),
                'warnings_count': len(validation_result['warnings']),
                'validation_score': len(validation_result['checks_passed']) / max(1, len(validation_result['checks_performed']))
            }
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Comprehensive validation failed: {str(e)}")
            return {
                'valid': False,
                'status': LicenseStatus.ERROR.value,
                'error': f'Validation process failed: {str(e)}',
                'validation_source': ValidationSource.ERROR.value,
                'timestamp': datetime.now().isoformat()
            }
    
    def _is_obviously_invalid_license(self, license_key: str) -> bool:
        """Check for obviously invalid license patterns"""
        invalid_patterns = ['INVALID-', 'invalid', 'test', 'fake', 'demo', 'DEMO-', 'TEST-']
        return any(license_key.upper().startswith(pattern.upper()) for pattern in invalid_patterns)
    
    # ==================== UNIFIED LICENSE OPERATIONS ====================
    
    def get_license_status(self) -> Dict[str, Any]:
        """
        Get current license status - UNIFIES multiple status check patterns
        Replaces scattered license status logic across files
        """
        try:
            repository = self._get_repository()
            if not repository:
                return {
                    'status': LicenseStatus.ERROR.value,
                    'error': 'Repository unavailable',
                    'license': None
                }
            
            # Get active license from repository
            license_data = repository.get_active_license()
            
            if not license_data:
                return {
                    'status': LicenseStatus.NO_LICENSE.value,
                    'message': 'No active license found',
                    'license': None
                }
            
            # Parse features using unified parser
            license_data['features'] = self._parse_features(license_data)
            
            # Validate expiry using unified method
            expiry_result = self._validate_expiry(license_data)
            
            # Determine status
            if expiry_result['valid']:
                status = LicenseStatus.VALID.value
                message = expiry_result['message']
            else:
                status = LicenseStatus.EXPIRED.value
                message = expiry_result['message']
            
            return {
                'status': status,
                'message': message,
                'license': license_data,
                'expiry_details': expiry_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ License status check failed: {str(e)}")
            return {
                'status': LicenseStatus.ERROR.value,
                'error': str(e),
                'license': None
            }
    
    def activate_license(self, license_key: str, force_offline: bool = False) -> Dict[str, Any]:
        """
        Unified license activation - COMBINES all activation flows
        Replaces scattered activation logic in payment_routes.py
        """
        try:
            logger.info(f"🔑 Starting unified license activation: {license_key[:12]}...")
            
            # Step 1: Comprehensive validation
            validation_result = self.validate_license_comprehensive(
                license_key, 
                strict_mode=not force_offline,
                force_online=not force_offline
            )
            
            if not validation_result['valid']:
                return {
                    'success': False,
                    'valid': False,
                    'error': validation_result.get('error', 'License validation failed'),
                    'activation_status': 'validation_failed',
                    'validation_details': validation_result
                }
            
            license_data = validation_result['license_data']
            license_id = license_data.get('id')
            
            if not license_id:
                return {
                    'success': False,
                    'error': 'License ID not found in validation result',
                    'activation_status': 'no_license_id'
                }
            
            # Step 2: Check activation status using unified method
            activation_check = self._check_activation_status(license_id)
            
            if activation_check.get('error'):
                return {
                    'success': False,
                    'error': activation_check['error'],
                    'activation_status': 'activation_check_failed'
                }
            
            # Handle different activation scenarios
            if activation_check['activation_status'] == 'already_activated_this_machine':
                # Already activated on this machine - return success
                return {
                    'success': True,
                    'valid': True,
                    'activation_status': 'already_activated_this_machine',
                    'data': {
                        'license_key': license_key,
                        'customer_email': license_data.get('customer_email', 'unknown'),
                        'package_name': license_data.get('product_type', 'desktop'),
                        'expires_at': license_data.get('expires_at'),
                        'status': 'already_activated',
                        'features': license_data.get('features', []),
                        'machine_fingerprint': activation_check['current_machine'],
                        'activated_at': activation_check['activated_at']
                    },
                    'validation_source': validation_result['validation_source'],
                    'timestamp': datetime.now().isoformat()
                }
            
            elif activation_check['activation_status'] == 'activated_elsewhere':
                # Activated on another machine - block activation
                return {
                    'success': False,
                    'valid': False,
                    'error': activation_check['message'],
                    'activation_status': 'blocked_multi_device',
                    'data': {
                        'license_key': license_key,
                        'status': 'activated_elsewhere',
                        'other_device_activated_at': activation_check['other_activated_at'],
                        'other_device_info': activation_check.get('other_device_info', {})
                    }
                }
            
            elif activation_check['activation_status'] == 'not_activated':
                # Can activate - create activation record
                validation_source = ValidationSource(validation_result['validation_source'])
                
                extra_info = {
                    'endpoint': '/activate-license',
                    'validation_checks_passed': validation_result['validation_summary']['passed_checks'],
                    'validation_score': validation_result['validation_summary']['validation_score']
                }
                
                activation_success = self._create_activation_record(
                    license_id, validation_source, extra_info
                )
                
                if not activation_success:
                    return {
                        'success': False,
                        'error': 'Failed to create activation record',
                        'activation_status': 'activation_record_failed'
                    }
                
                # Success - return activation details
                return {
                    'success': True,
                    'valid': True,
                    'activation_status': 'activated',
                    'data': {
                        'license_key': license_key,
                        'customer_email': license_data.get('customer_email', 'unknown'),
                        'package_name': license_data.get('product_type', 'desktop'),
                        'expires_at': license_data.get('expires_at'),
                        'status': 'activated',
                        'features': license_data.get('features', []),
                        'machine_fingerprint': activation_check['current_machine'],
                        'activated_at': datetime.now().isoformat()
                    },
                    'validation_source': validation_result['validation_source'],
                    'timestamp': datetime.now().isoformat(),
                    'warnings': validation_result.get('warnings', [])
                }
            
            else:
                return {
                    'success': False,
                    'error': f"Unknown activation status: {activation_check['activation_status']}",
                    'activation_status': 'unknown_status'
                }
                
        except Exception as e:
            logger.error(f"❌ License activation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'activation_status': 'exception_error',
                'timestamp': datetime.now().isoformat()
            }

# ==================== SERVICE INSTANCE MANAGEMENT ====================

# Singleton instance for application-wide use
_license_service_instance: Optional[LicenseService] = None

def get_license_service() -> LicenseService:
    """Get singleton license service instance"""
    global _license_service_instance
    if _license_service_instance is None:
        _license_service_instance = LicenseService()
        logger.info("✅ License service singleton created")
    return _license_service_instance

def reset_license_service():
    """Reset singleton (for testing)"""
    global _license_service_instance
    _license_service_instance = None

# ==================== TESTING AND UTILITIES ====================

if __name__ == "__main__":
    print("🧪 Testing LicenseService...")
    
    try:
        service = LicenseService()
        
        # Test JSON parsing
        test_license = {"features": '["camera_access", "analytics"]'}
        features = service._parse_features(test_license)
        print(f"✅ Features parsing test: {features}")
        
        # Test expiry validation
        test_license_expired = {"expires_at": "2024-01-01T00:00:00"}
        expiry_result = service._validate_expiry(test_license_expired)
        print(f"✅ Expiry validation test: {expiry_result['expired']}")
        
        # Test machine fingerprint
        fingerprint = service._get_machine_fingerprint()
        print(f"✅ Machine fingerprint: {fingerprint[:16]}...")
        
        print("🎉 LicenseService basic tests completed!")
        
    except Exception as e:
        print(f"❌ LicenseService test failed: {e}")
        import traceback
        traceback.print_exc()