"""
Core license management operations - FIXED VERSION
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
from .machine_fingerprint import generate_machine_fingerprint
from .license_config import *

# Import existing modules
try:
    from modules.licensing.license_models import License
    from modules.payments.cloud_function_client import get_cloud_client
    from modules.db_utils import get_db_connection
except ImportError:
    from backend.modules.licensing.license_models import License
    from backend.modules.payments.cloud_function_client import get_cloud_client
    from backend.modules.db_utils import get_db_connection

logger = logging.getLogger(__name__)

class LicenseManager:
    """Core license management class - FIXED"""
    
    def __init__(self):
        self.machine_fingerprint = generate_machine_fingerprint()
        self.cloud_client = None
        
    def get_local_license(self) -> Optional[Dict[str, Any]]:
        """Get active license from local database - FIXED QUERY"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # FIXED: More flexible query to find any valid license
                cursor.execute("""
                    SELECT * FROM licenses 
                    WHERE status = 'active' 
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if not row:
                    logger.debug("No active license found in database")
                    return None
                
                # Get column names
                cursor.execute("PRAGMA table_info(licenses)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Convert to dict
                license_data = dict(zip(columns, row))
                
                # Parse JSON fields safely
                if license_data.get('features'):
                    try:
                        if isinstance(license_data['features'], str):
                            license_data['features'] = json.loads(license_data['features'])
                    except (json.JSONDecodeError, TypeError):
                        license_data['features'] = ['full_access']
                
                logger.info(f"Found local license: {license_data.get('license_key', 'N/A')[:20]}...")
                return license_data
                
        except Exception as e:
            logger.error(f"Failed to get local license: {e}")
            return None
    
    def is_license_valid(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if license is valid - IMPROVED LOGIC"""
        try:
            if not license_data:
                return {'valid': False, 'reason': 'no_license_data'}
            
            # Check status first
            status = license_data.get('status', 'unknown')
            if status != 'active':
                return {'valid': False, 'reason': f'status_{status}'}
            
            # Check expiry date if exists
            expires_at = license_data.get('expires_at')
            if expires_at:
                try:
                    # Handle different date formats
                    if isinstance(expires_at, str):
                        # Try ISO format first
                        try:
                            expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        except:
                            # Try other common formats
                            expiry_date = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                    else:
                        expiry_date = expires_at
                    
                    if datetime.now() > expiry_date:
                        return {
                            'valid': False, 
                            'reason': 'expired', 
                            'expiry_date': expires_at,
                            'days_expired': (datetime.now() - expiry_date).days
                        }
                except Exception as date_error:
                    logger.warning(f"Date parsing error: {date_error}, assuming valid")
            
            return {'valid': True, 'license': license_data}
            
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return {'valid': False, 'reason': 'validation_error', 'error': str(e)}
    
    def validate_with_cloud(self, license_key: str) -> Dict[str, Any]:
        """Validate license with cloud service"""
        try:
            if not self.cloud_client:
                self.cloud_client = get_cloud_client()
            
            result = self.cloud_client.validate_license(license_key)
            logger.info(f"Cloud validation result: {result.get('valid', False)}")
            return result
            
        except Exception as e:
            logger.warning(f"Cloud validation failed: {e}")
            return {'success': False, 'valid': False, 'error': 'cloud_unavailable'}
    
    def activate_license(self, license_key: str) -> Dict[str, Any]:
        """Activate license and save locally"""
        try:
            # Step 1: Validate with cloud
            cloud_result = self.validate_with_cloud(license_key)
            
            if not cloud_result.get('valid'):
                return {'success': False, 'error': 'Invalid license key'}
            
            # Step 2: Save to local database
            license_data = cloud_result.get('data', {})
            
            license_id = License.create(
                license_key=license_key,
                customer_email=license_data.get('customer_email', 'unknown'),
                product_type=license_data.get('product_type', 'desktop'),
                features=license_data.get('features', ['full_access']),
                expires_days=365
            )
            
            if license_id:
                # Step 3: Create activation record
                self._create_activation_record(license_id, license_key)
                
                return {
                    'success': True, 
                    'license_id': license_id,
                    'machine_fingerprint': self.machine_fingerprint
                }
            else:
                return {'success': False, 'error': 'Failed to save license'}
                
        except Exception as e:
            logger.error(f"License activation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_activation_record(self, license_id: int, license_key: str):
        """Create license activation record"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO license_activations 
                    (license_id, machine_fingerprint, activation_time, status)
                    VALUES (?, ?, ?, 'active')
                """, (license_id, self.machine_fingerprint, datetime.now().isoformat()))
                conn.commit()
                logger.info(f"Activation record created for license {license_id}")
        except Exception as e:
            logger.error(f"Failed to create activation record: {e}")
    
    def get_license_status(self) -> Dict[str, Any]:
        """Get comprehensive license status - IMPROVED"""
        try:
            # Get local license
            local_license = self.get_local_license()
            
            if not local_license:
                logger.info("No local license found")
                return {
                    'status': 'no_license',
                    'has_license': False,
                    'message': 'No license found'
                }
            
            # Validate license
            validity_check = self.is_license_valid(local_license)
            
            if not validity_check['valid']:
                reason = validity_check['reason']
                logger.warning(f"License invalid: {reason}")
                return {
                    'status': 'invalid',
                    'has_license': True,
                    'reason': reason,
                    'license': local_license
                }
            
            logger.info("Valid license found")
            return {
                'status': 'valid',
                'has_license': True,
                'license': local_license,
                'machine_fingerprint': self.machine_fingerprint
            }
            
        except Exception as e:
            logger.error(f"Get license status failed: {e}")
            return {
                'status': 'error',
                'has_license': False,
                'error': str(e)
            }