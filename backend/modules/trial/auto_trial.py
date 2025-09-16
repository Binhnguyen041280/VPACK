"""
Auto Trial Service with CloudFunction Integration
Siêu đơn giản: Auto create trial cho first-time users
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import existing infrastructure
try:
    from modules.payments.cloud_function_client import get_cloud_client
    from modules.db_utils.safe_connection import safe_db_connection
    from .machine_id import generate_machine_id
except ImportError:
    from backend.modules.payments.cloud_function_client import get_cloud_client
    from backend.modules.db_utils.safe_connection import safe_db_connection
    from backend.modules.trial.machine_id import generate_machine_id

logger = logging.getLogger(__name__)

class AutoTrialService:
    """
    Siêu đơn giản auto trial service
    Tự động tạo trial cho user mới, track với CloudFunction security
    """

    @staticmethod
    def check_or_create_trial(machine_id: str) -> Dict[str, Any]:
        """
        Main method: Check license status và auto create trial nếu cần

        Args:
            machine_id: Unique machine identifier

        Returns:
            Status dict với license/trial info
        """
        try:
            logger.info(f"🔍 Checking auto trial for machine: {machine_id[:16]}...")

            # Step 1: Check if already has paid license
            paid_license = AutoTrialService._check_paid_license()
            if paid_license:
                logger.info("✅ Found paid license, no trial needed")
                return {
                    'type': 'paid',
                    'status': 'active',
                    'license_data': paid_license,
                    'source': 'local_database'
                }

            # Step 2: Check local trial cache first (for speed)
            local_trial = AutoTrialService._check_local_trial()
            if local_trial:
                logger.info(f"📋 Found local trial: {local_trial['status']}")
                return local_trial

            # Step 3: Check CloudFunction trial eligibility
            cloud_result = AutoTrialService._check_cloud_trial_eligibility(machine_id)

            if cloud_result.get('eligible'):
                # Step 4: Auto-generate trial via CloudFunction
                trial_result = AutoTrialService._generate_cloud_trial(machine_id)

                if trial_result.get('success'):
                    # Step 5: Cache trial locally for fast access
                    AutoTrialService._cache_trial_locally(trial_result['license_data'])

                    logger.info("✅ Auto trial created successfully")
                    return {
                        'type': 'trial',
                        'status': 'active',
                        'days_left': 7,
                        'license_data': trial_result['license_data'],
                        'source': 'cloudfunction_generated'
                    }
                else:
                    logger.warning("⚠️ Trial generation failed")
                    return {
                        'type': 'none',
                        'status': 'failed',
                        'error': trial_result.get('error', 'Trial generation failed'),
                        'source': 'cloudfunction_error'
                    }
            else:
                # Not eligible (already used trial on this machine)
                reason = cloud_result.get('reason', 'not_eligible')
                logger.info(f"❌ Trial not eligible: {reason}")
                return {
                    'type': 'none',
                    'status': 'not_eligible',
                    'reason': reason,
                    'message': cloud_result.get('message', 'Trial not available'),
                    'source': 'cloudfunction_check'
                }

        except Exception as e:
            logger.error(f"❌ Auto trial check failed: {str(e)}")
            return {
                'type': 'none',
                'status': 'error',
                'error': str(e),
                'source': 'exception'
            }

    @staticmethod
    def _check_paid_license() -> Optional[Dict[str, Any]]:
        """Check if user already has paid license"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM licenses
                    WHERE status = 'active'
                    AND (expires_at IS NULL OR expires_at > ?)
                    AND (product_type NOT LIKE '%trial%')
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (datetime.now().isoformat(),))

                row = cursor.fetchone()
                if row:
                    # Get column names
                    cursor.execute("PRAGMA table_info(licenses)")
                    columns = [col[1] for col in cursor.fetchall()]

                    license_data = dict(zip(columns, row))
                    logger.info(f"✅ Found paid license: {license_data.get('license_key', 'unknown')[:12]}...")
                    return license_data

                return None

        except Exception as e:
            logger.error(f"Failed to check paid license: {e}")
            return None

    @staticmethod
    def _check_local_trial() -> Optional[Dict[str, Any]]:
        """Check local trial cache"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM licenses
                    WHERE status = 'active'
                    AND product_type LIKE '%trial%'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if row:
                    # Get column names
                    cursor.execute("PRAGMA table_info(licenses)")
                    columns = [col[1] for col in cursor.fetchall()]

                    trial_data = dict(zip(columns, row))

                    # Check if trial is still valid
                    expires_at = trial_data.get('expires_at')
                    if expires_at:
                        expiry_date = datetime.fromisoformat(expires_at)
                        now = datetime.now()

                        if now > expiry_date:
                            logger.info("❌ Local trial expired")
                            return {
                                'type': 'trial',
                                'status': 'expired',
                                'expired_at': expires_at,
                                'source': 'local_cache'
                            }
                        else:
                            days_left = (expiry_date - now).days
                            logger.info(f"✅ Local trial active: {days_left} days left")
                            return {
                                'type': 'trial',
                                'status': 'active',
                                'days_left': days_left,
                                'license_data': trial_data,
                                'source': 'local_cache'
                            }

                return None

        except Exception as e:
            logger.error(f"Failed to check local trial: {e}")
            return None

    @staticmethod
    def _check_cloud_trial_eligibility(machine_id: str) -> Dict[str, Any]:
        """Check trial eligibility via CloudFunction"""
        try:
            cloud_client = get_cloud_client()

            # Call CloudFunction trial eligibility check
            result = cloud_client.check_trial_eligibility(machine_id)

            if result.get('success'):
                logger.info(f"✅ CloudFunction eligibility check successful")
                return {
                    'eligible': result.get('data', {}).get('eligible', False),
                    'reason': result.get('data', {}).get('reason'),
                    'message': result.get('data', {}).get('message'),
                    'trial_data': result.get('data', {}).get('trial_data', {})
                }
            else:
                logger.warning(f"⚠️ CloudFunction eligibility check failed: {result.get('error')}")
                return {
                    'eligible': False,
                    'reason': 'cloud_check_failed',
                    'message': result.get('error', 'Cloud check failed')
                }

        except Exception as e:
            logger.error(f"CloudFunction eligibility check error: {e}")
            return {
                'eligible': False,
                'reason': 'cloud_error',
                'message': str(e)
            }

    @staticmethod
    def _generate_cloud_trial(machine_id: str) -> Dict[str, Any]:
        """Generate trial license via CloudFunction"""
        try:
            cloud_client = get_cloud_client()

            # Call CloudFunction trial generation
            result = cloud_client.generate_trial_license(machine_id)

            if result.get('success'):
                logger.info(f"✅ CloudFunction trial generated successfully")
                return {
                    'success': True,
                    'license_data': result.get('data', {}),
                    'trial_license_key': result.get('data', {}).get('trial_license_key'),
                    'expires_at': result.get('data', {}).get('expires_at')
                }
            else:
                logger.warning(f"⚠️ CloudFunction trial generation failed: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Trial generation failed')
                }

        except Exception as e:
            logger.error(f"CloudFunction trial generation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _cache_trial_locally(license_data: Dict[str, Any]) -> bool:
        """Cache trial license locally for fast access"""
        try:
            # Import license models for creating local record
            try:
                from modules.licensing.license_models import License
            except ImportError:
                from backend.modules.licensing.license_models import License

            # Extract data from CloudFunction response
            license_key = license_data.get('trial_license_key') or license_data.get('license_key')

            # NEW: Get real user email instead of hardcode
            customer_email = license_data.get('customer_email')
            if not customer_email:
                customer_email = AutoTrialService._get_current_user_email()

            product_type = license_data.get('product_type', 'trial_7d')
            expires_at = license_data.get('expires_at')
            features = license_data.get('features', ['trial_access'])

            if not license_key:
                logger.error("❌ No trial license key in CloudFunction response")
                return False

            # Calculate expires_days for License.create()
            if expires_at:
                try:
                    expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    expires_days = (expiry_date - datetime.now()).days
                except:
                    expires_days = 7  # Default fallback
            else:
                expires_days = 7

            # Create local license record
            license_id = License.create(
                license_key=license_key,
                customer_email=customer_email,
                payment_transaction_id=None,  # No payment for trial
                product_type=product_type,
                features=features,
                expires_days=expires_days
            )

            if license_id:
                logger.info(f"✅ Trial cached locally: ID {license_id}")
                return True
            else:
                logger.error("❌ Failed to cache trial locally")
                return False

        except Exception as e:
            logger.error(f"Failed to cache trial locally: {e}")
            return False

    @staticmethod
    def get_trial_status() -> Dict[str, Any]:
        """
        Get current trial status (simplified version of check_or_create)
        Used for status checks without auto-creation
        """
        try:
            # Check paid license first
            paid_license = AutoTrialService._check_paid_license()
            if paid_license:
                return {
                    'type': 'paid',
                    'status': 'active',
                    'license_data': paid_license
                }

            # Check local trial
            local_trial = AutoTrialService._check_local_trial()
            if local_trial:
                return local_trial

            # No license found
            return {
                'type': 'none',
                'status': 'no_license',
                'message': 'No license or trial found'
            }

        except Exception as e:
            logger.error(f"Get trial status failed: {e}")
            return {
                'type': 'none',
                'status': 'error',
                'error': str(e)
            }

    @staticmethod
    def _get_current_user_email() -> str:
        """Get current user email from database"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT gmail_address FROM user_profiles
                    ORDER BY last_login DESC
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if row:
                    return row[0]
                else:
                    logger.warning("No user profile found, using fallback email")
                    return 'trial@local.dev'

        except Exception as e:
            logger.error(f"Failed to get user email: {e}")
            return 'trial@local.dev'

    @staticmethod
    def check_auto_trial() -> Dict[str, Any]:
        """
        Convenience method: Auto-generate machine ID and check trial
        Used by API endpoints for easy integration

        Returns:
            Auto trial check result with machine ID
        """
        try:
            machine_id = generate_machine_id()
            result = AutoTrialService.check_or_create_trial(machine_id)
            result['machine_id'] = machine_id
            return result

        except Exception as e:
            logger.error(f"Auto trial check failed: {e}")
            return {
                'type': 'none',
                'status': 'error',
                'error': str(e),
                'machine_id': None
            }