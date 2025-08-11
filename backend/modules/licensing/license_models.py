# backend/modules/licensing/license_models.py
"""
V_Track License Management Models - Enhanced Version with Offline Validation
Only handles database operations, tables already created in database.py
ENHANCED: Added offline validation, signature verification, and integrity checks
"""

import sqlite3
import json
import logging
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Import database utilities
try:
    from modules.db_utils import get_db_connection
except ImportError:
    from backend.modules.db_utils import get_db_connection

logger = logging.getLogger(__name__)

def init_license_db():
    """
    Check if license tables exist (they should be created by database.py)
    This function only verifies, does NOT create tables
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if licenses table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='licenses'
            """)
            
            if cursor.fetchone():
                logger.info("✅ License tables verified - already exist")
                return True
            else:
                logger.warning("⚠️ License tables not found! Run database.py first")
                return False
                
    except Exception as e:
        logger.error(f"❌ Failed to verify license database: {str(e)}")
        return False

class PaymentTransaction:
    """Model for payment transactions"""
    
    @staticmethod
    def create(app_trans_id: str, customer_email: str, amount: int, payment_data: Optional[Dict] = None) -> Optional[int]:
        """Create new payment transaction"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                payment_data_json = json.dumps(payment_data) if payment_data else None
                
                cursor.execute("""
                    INSERT INTO payment_transactions 
                    (app_trans_id, customer_email, amount, status, payment_data)
                    VALUES (?, ?, ?, 'pending', ?)
                """, (app_trans_id, customer_email, amount, payment_data_json))
                
                transaction_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ Payment transaction created: ID {transaction_id}")
                return transaction_id
                
        except Exception as e:
            logger.error(f"❌ Failed to create payment transaction: {str(e)}")
            return None
    
    @staticmethod
    def get_by_app_trans_id(app_trans_id: str) -> Optional[Dict[str, Any]]:
        """Get payment transaction by app_trans_id"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payment_transactions 
                    WHERE app_trans_id = ?
                """, (app_trans_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Get column names
                cursor.execute("PRAGMA table_info(payment_transactions)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Convert to dict
                transaction = dict(zip(columns, row))
                
                # Parse JSON fields
                if transaction.get('payment_data'):
                    try:
                        transaction['payment_data'] = json.loads(transaction['payment_data'])
                    except (json.JSONDecodeError, TypeError):
                        transaction['payment_data'] = {}
                
                return transaction
                
        except Exception as e:
            logger.error(f"❌ Failed to get payment transaction: {str(e)}")
            return None
    
    @staticmethod
    def update_status(app_trans_id: str, status: str, zalopay_trans_id: Optional[str] = None) -> bool:
        """Update payment transaction status"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                update_fields = ["status = ?"]
                params = [status]
                
                if zalopay_trans_id:
                    update_fields.append("zalopay_trans_id = ?")
                    params.append(zalopay_trans_id)
                
                if status == 'completed':
                    update_fields.append("completed_at = ?")
                    params.append(datetime.now().isoformat())
                
                params.append(app_trans_id)
                
                cursor.execute(f"""
                    UPDATE payment_transactions 
                    SET {', '.join(update_fields)}
                    WHERE app_trans_id = ?
                """, params)
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"✅ Payment transaction status updated: {app_trans_id} -> {status}")
                else:
                    logger.warning(f"⚠️ Payment transaction not found: {app_trans_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Failed to update payment transaction: {str(e)}")
            return False

class License:
    """
    Model for license management - MAIN LICENSE CLASS
    Works with tables created by database.py
    SIMPLIFIED: Only uses product_type column
    """
    
    @staticmethod
    def create(license_key: str, customer_email: str, payment_transaction_id: Optional[int] = None,
               product_type: str = 'desktop', features: Optional[List[str]] = None, 
               expires_days: int = 365) -> Optional[int]:
        """
        Create new license record in database
        
        Args:
            license_key: Generated license key
            customer_email: Customer email address
            payment_transaction_id: Associated payment transaction ID
            product_type: Type of product license (desktop, premium, etc.)
            features: List of enabled features
            expires_days: Number of days until expiration
            
        Returns:
            int: License ID if created successfully, None otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Calculate expiration date
                expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
                
                # Prepare features JSON
                features_json = json.dumps(features or ['full_access'])
                
                # ✅ CLEAN SQL - Uses product_type column only
                cursor.execute("""
                INSERT INTO licenses 
                (license_key, customer_email, payment_transaction_id, 
                product_type, features, status, expires_at, activated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """, (license_key, customer_email, payment_transaction_id, 
                    product_type, features_json, expires_at, datetime.now().isoformat()))
                
                license_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ License created: ID {license_id} for {customer_email}")
                logger.debug(f"📋 Product type: {product_type}")
                logger.debug(f"📋 License key: {license_key[:12]}...")
                
                return license_id
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"⚠️ License key already exists: {license_key[:12]}...")
                return None
            else:
                logger.error(f"❌ Database integrity error: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to create license: {str(e)}")
            return None
    
    @staticmethod
    def get_by_key(license_key: str) -> Optional[Dict[str, Any]]:
        """
        Get license by license key
        
        Args:
            license_key: License key to search for
            
        Returns:
            dict: License data if found, None otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM licenses 
                    WHERE license_key = ?
                """, (license_key,))
                
                row = cursor.fetchone()
                if not row:
                    logger.debug(f"🔍 License not found: {license_key[:12]}...")
                    return None
                
                # Get column names
                cursor.execute("PRAGMA table_info(licenses)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Convert to dict
                license_data = dict(zip(columns, row))
                
                # Parse JSON fields
                if license_data.get('features'):
                    try:
                        license_data['features'] = json.loads(license_data['features'])
                    except (json.JSONDecodeError, TypeError):
                        license_data['features'] = ['full_access']
                
                logger.debug(f"✅ License found: {license_key[:12]}... for {license_data.get('customer_email')}")
                return license_data
                
        except Exception as e:
            logger.error(f"❌ Failed to get license by key: {str(e)}")
            return None
    
    @staticmethod
    def get_by_email(customer_email: str) -> List[Dict[str, Any]]:
        """Get all licenses for a customer email"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM licenses 
                    WHERE customer_email = ?
                    ORDER BY created_at DESC
                """, (customer_email,))
                
                rows = cursor.fetchall()
                if not rows:
                    return []
                
                # Get column names
                cursor.execute("PRAGMA table_info(licenses)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Convert to list of dicts
                licenses = []
                for row in rows:
                    license_data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    if license_data.get('features'):
                        try:
                            license_data['features'] = json.loads(license_data['features'])
                        except (json.JSONDecodeError, TypeError):
                            license_data['features'] = ['full_access']
                    
                    licenses.append(license_data)
                
                logger.info(f"📋 Found {len(licenses)} licenses for {customer_email}")
                return licenses
                
        except Exception as e:
            logger.error(f"❌ Failed to get licenses by email: {str(e)}")
            return []
    
    @staticmethod
    def get_active_license() -> Optional[Dict[str, Any]]:
        """
        Get current active license (singular)
        
        Returns:
            dict: Active license data if found, None otherwise
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM licenses 
                    WHERE status = 'active' 
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (datetime.now().isoformat(),))
                
                row = cursor.fetchone()
                if not row:
                    logger.debug("🔍 No active license found")
                    return None
                
                # Get column names
                cursor.execute("PRAGMA table_info(licenses)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Convert to dict
                license_data = dict(zip(columns, row))
                
                # Parse JSON fields
                if license_data.get('features'):
                    try:
                        license_data['features'] = json.loads(license_data['features'])
                    except (json.JSONDecodeError, TypeError):
                        license_data['features'] = ['full_access']
                
                logger.debug(f"✅ Active license found for {license_data.get('customer_email')}")
                return license_data
                
        except Exception as e:
            logger.error(f"❌ Failed to get active license: {str(e)}")
            return None
    
    @staticmethod
    def update_status(license_key: str, status: str) -> bool:
        """Update license status"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE licenses 
                    SET status = ?
                    WHERE license_key = ?
                """, (status, license_key))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"✅ License status updated: {license_key[:12]}... -> {status}")
                else:
                    logger.warning(f"⚠️ License not found for update: {license_key[:12]}...")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Failed to update license status: {str(e)}")
            return False
    
    @staticmethod
    def delete(license_key: str) -> bool:
        """Delete license record"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM licenses WHERE license_key = ?
                """, (license_key,))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"✅ License deleted: {license_key[:12]}...")
                else:
                    logger.warning(f"⚠️ License not found for deletion: {license_key[:12]}...")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Failed to delete license: {str(e)}")
            return False

    # ==================== ENHANCED OFFLINE VALIDATION METHODS ====================
    
    @staticmethod
    def validate_offline(license_key: str, strict_mode: bool = False) -> Dict[str, Any]:
        """
        Enhanced offline license validation with multiple verification layers
        
        Args:
            license_key: License key to validate
            strict_mode: Whether to enforce strict validation rules
            
        Returns:
            dict: Comprehensive validation result
        """
        try:
            logger.info(f"🔍 Starting offline validation for license: {license_key[:12]}...")
            
            validation_result = {
                'valid': False,
                'license_data': None,
                'validation_source': 'offline',
                'checks_performed': [],
                'checks_passed': [],
                'checks_failed': [],
                'warnings': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Step 1: Basic format validation
            format_check = License._validate_license_format(license_key)
            validation_result['checks_performed'].append('format_validation')
            
            if not format_check['valid']:
                validation_result['checks_failed'].append('format_validation')
                validation_result['error'] = format_check['error']
                return validation_result
            else:
                validation_result['checks_passed'].append('format_validation')
            
            # Step 2: Database integrity check
            db_check = License._validate_database_integrity(license_key)
            validation_result['checks_performed'].append('database_integrity')
            
            if not db_check['valid']:
                validation_result['checks_failed'].append('database_integrity')
                if strict_mode:
                    validation_result['error'] = db_check['error']
                    return validation_result
                else:
                    validation_result['warnings'].append(f"Database check failed: {db_check['error']}")
            else:
                validation_result['checks_passed'].append('database_integrity')
                validation_result['license_data'] = db_check['license_data']
            
            # Step 3: Cryptographic signature verification (if available)
            crypto_check = License._validate_cryptographic_signature(license_key)
            validation_result['checks_performed'].append('cryptographic_signature')
            
            if crypto_check['valid']:
                validation_result['checks_passed'].append('cryptographic_signature')
                # Use crypto data if database check failed
                if not validation_result['license_data']:
                    validation_result['license_data'] = crypto_check['license_data']
            else:
                validation_result['checks_failed'].append('cryptographic_signature')
                if strict_mode and not validation_result['license_data']:
                    validation_result['error'] = crypto_check['error']
                    return validation_result
                else:
                    validation_result['warnings'].append(f"Crypto check failed: {crypto_check['error']}")
            
            # Step 4: Expiry validation using local system time
            if validation_result['license_data']:
                expiry_check = License._validate_license_expiry(validation_result['license_data'])
                validation_result['checks_performed'].append('expiry_validation')
                
                if expiry_check['valid']:
                    validation_result['checks_passed'].append('expiry_validation')
                else:
                    validation_result['checks_failed'].append('expiry_validation')
                    if strict_mode:
                        validation_result['error'] = expiry_check['error']
                        return validation_result
                    else:
                        validation_result['warnings'].append(f"Expiry check: {expiry_check['error']}")
                        validation_result['expired'] = True
                
                # Step 5: Feature availability determination
                feature_check = License._determine_available_features(validation_result['license_data'], validation_result.get('expired', False))
                validation_result['checks_performed'].append('feature_determination')
                validation_result['checks_passed'].append('feature_determination')
                validation_result['available_features'] = feature_check['features']
                validation_result['feature_limitations'] = feature_check['limitations']
            
            # Final validation decision
            critical_checks = ['format_validation']
            if strict_mode:
                critical_checks.extend(['database_integrity', 'cryptographic_signature', 'expiry_validation'])
            
            critical_failures = [check for check in critical_checks if check in validation_result['checks_failed']]
            
            if not critical_failures and validation_result['license_data']:
                validation_result['valid'] = True
                validation_result['message'] = f"License valid (offline) - {len(validation_result['checks_passed'])}/{len(validation_result['checks_performed'])} checks passed"
                logger.info(f"✅ Offline validation successful: {validation_result['message']}")
            else:
                validation_result['valid'] = False
                validation_result['message'] = f"License invalid - {len(critical_failures)} critical checks failed"
                if not validation_result.get('error'):
                    validation_result['error'] = f"Critical validation failures: {critical_failures}"
                logger.warning(f"❌ Offline validation failed: {validation_result['message']}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Offline validation error: {str(e)}")
            return {
                'valid': False,
                'error': f'Validation process failed: {str(e)}',
                'validation_source': 'offline',
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def _validate_license_format(license_key: str) -> Dict[str, Any]:
        """
        Validate license key format and basic structure
        """
        try:
            # Basic format checks
            if not license_key or len(license_key) < 10:
                return {'valid': False, 'error': 'License key too short'}
            
            if len(license_key) > 500:
                return {'valid': False, 'error': 'License key too long'}
            
            # Check for obvious invalid patterns
            invalid_patterns = ['INVALID-', 'TEST-', 'DEMO-', 'FAKE-']
            if any(license_key.upper().startswith(pattern) for pattern in invalid_patterns):
                return {'valid': False, 'error': 'License key contains invalid pattern'}
            
            # Try to decode if it looks like Base64
            if license_key.count('-') == 0 and len(license_key) > 50:
                try:
                    decoded = base64.b64decode(license_key)
                    if len(decoded) < 10:
                        return {'valid': False, 'error': 'Invalid Base64 license structure'}
                except Exception:
                    pass  # Not Base64, continue with other checks
            
            # Check VTRACK-XXXX-XXXX format
            elif '-' in license_key:
                parts = license_key.split('-')
                if len(parts) >= 2:
                    prefix = parts[0].upper()
                    if prefix not in ['VTRACK', 'VTK', 'VTRAC']:
                        return {'valid': False, 'error': 'Invalid license key prefix'}
                    
                    # Validate package code format
                    if len(parts) >= 2:
                        package_code = parts[1].upper()
                        valid_codes = ['P1M', 'P1Y', 'B1M', 'B1Y', 'DESKTOP', 'PREMIUM']
                        if package_code not in valid_codes:
                            # Not necessarily invalid, might be new format
                            pass
            
            return {'valid': True, 'format_type': 'validated'}
            
        except Exception as e:
            return {'valid': False, 'error': f'Format validation error: {str(e)}'}
    
    @staticmethod
    def _validate_database_integrity(license_key: str) -> Dict[str, Any]:
        """
        Verify license hasn't been tampered with in local database
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get license with integrity check
                cursor.execute("""
                    SELECT l.*, la.machine_fingerprint, la.activation_time, la.status as activation_status
                    FROM licenses l
                    LEFT JOIN license_activations la ON l.id = la.license_id
                    WHERE l.license_key = ?
                    ORDER BY la.activation_time DESC
                    LIMIT 1
                """, (license_key,))
                
                row = cursor.fetchone()
                if not row:
                    return {'valid': False, 'error': 'License not found in database'}
                
                # Get column names for licenses table
                cursor.execute("PRAGMA table_info(licenses)")
                license_columns = [col[1] for col in cursor.fetchall()]
                
                # Parse license data
                license_data = {}
                for i, col_name in enumerate(license_columns):
                    if i < len(row):
                        license_data[col_name] = row[i]
                
                # Parse features JSON
                if license_data.get('features'):
                    try:
                        license_data['features'] = json.loads(license_data['features'])
                    except (json.JSONDecodeError, TypeError):
                        license_data['features'] = ['full_access']
                
                # Additional integrity checks
                integrity_issues = []
                
                # Check for required fields
                required_fields = ['license_key', 'customer_email', 'status']
                for field in required_fields:
                    if not license_data.get(field):
                        integrity_issues.append(f'Missing required field: {field}')
                
                # Check license key consistency
                if license_data.get('license_key') != license_key:
                    integrity_issues.append('License key mismatch')
                
                # Check for suspicious modifications
                if license_data.get('status') not in ['active', 'inactive', 'expired', 'suspended']:
                    integrity_issues.append(f'Invalid status: {license_data.get("status")}')
                
                # Verify activation data if present
                if len(row) > len(license_columns):
                    activation_data = {
                        'machine_fingerprint': row[len(license_columns)],
                        'activation_time': row[len(license_columns) + 1],
                        'activation_status': row[len(license_columns) + 2]
                    }
                    license_data['activation_data'] = activation_data
                
                if integrity_issues:
                    return {
                        'valid': False, 
                        'error': f'Database integrity issues: {", ".join(integrity_issues)}',
                        'license_data': license_data
                    }
                
                return {
                    'valid': True, 
                    'license_data': license_data,
                    'integrity_verified': True
                }
                
        except Exception as e:
            return {'valid': False, 'error': f'Database integrity check failed: {str(e)}'}
    
    @staticmethod
    def _validate_cryptographic_signature(license_key: str) -> Dict[str, Any]:
        """
        Basic cryptographic validation offline using available generators
        """
        try:
            # Try to import license generator for crypto validation
            try:
                from ..payments.license_generator import LicenseGenerator
                license_gen = LicenseGenerator()
                
                # Verify license signature
                license_data = license_gen.verify_license(license_key)
                
                if license_data:
                    return {
                        'valid': True,
                        'license_data': {
                            'license_key': license_key,
                            'customer_email': license_data.get('customer_email'),
                            'product_type': license_data.get('product_type'),
                            'features': license_data.get('features', []),
                            'expires_at': license_data.get('expiry_date'),
                            'license_id': license_data.get('license_id'),
                            'crypto_verified': True
                        }
                    }
                else:
                    return {'valid': False, 'error': 'Cryptographic signature verification failed'}
                    
            except ImportError:
                # License generator not available - try basic validation
                return License._basic_cryptographic_check(license_key)
                
        except Exception as e:
            return {'valid': False, 'error': f'Cryptographic validation error: {str(e)}'}
    
    @staticmethod
    def _basic_cryptographic_check(license_key: str) -> Dict[str, Any]:
        """
        Basic cryptographic checks when full generator isn't available
        """
        try:
            # Try to parse as Base64 encoded JSON
            if license_key.count('-') == 0 and len(license_key) > 50:
                try:
                    # Decode potential Base64 license
                    decoded_bytes = base64.b64decode(license_key)
                    decoded_str = decoded_bytes.decode('utf-8')
                    
                    # Try to parse as JSON
                    license_package = json.loads(decoded_str)
                    
                    if isinstance(license_package, dict) and 'data' in license_package:
                        # Decode license data
                        license_data_b64 = license_package.get('data')
                        if license_data_b64:
                            license_data_bytes = base64.b64decode(license_data_b64)
                            license_data = json.loads(license_data_bytes.decode('utf-8'))
                            
                            return {
                                'valid': True,
                                'license_data': {
                                    'license_key': license_key,
                                    'customer_email': license_data.get('customer_email'),
                                    'product_type': license_data.get('product_type'),
                                    'features': license_data.get('features', []),
                                    'expires_at': license_data.get('expiry_date'),
                                    'crypto_parsed': True,
                                    'signature_verified': False  # Can't verify without keys
                                }
                            }
                            
                except Exception:
                    pass  # Not a valid encoded license
            
            # Generate simple hash-based validation for structured keys
            if '-' in license_key:
                parts = license_key.split('-')
                if len(parts) >= 3:
                    # Extract potential checksum
                    checksum_part = parts[-1]
                    data_parts = '-'.join(parts[:-1])
                    
                    # Simple hash verification
                    expected_hash = hashlib.md5(data_parts.encode()).hexdigest()[:8].upper()
                    if checksum_part.upper() == expected_hash:
                        # Extract package info from structured key
                        package_info = License._extract_package_info_from_key(license_key)
                        return {
                            'valid': True,
                            'license_data': {
                                'license_key': license_key,
                                'product_type': package_info.get('product_type', 'desktop'),
                                'features': ['basic_access'],  # Conservative features
                                'hash_verified': True,
                                'signature_verified': False
                            }
                        }
            
            return {'valid': False, 'error': 'No cryptographic validation method available'}
            
        except Exception as e:
            return {'valid': False, 'error': f'Basic crypto check failed: {str(e)}'}
    
    @staticmethod
    def _extract_package_info_from_key(license_key: str) -> Dict[str, Any]:
        """Extract package information from structured license key"""
        try:
            parts = license_key.split('-')
            if len(parts) >= 2:
                package_code = parts[1].upper()
                
                package_mapping = {
                    'P1M': {'product_type': 'personal_1m', 'duration_days': 30},
                    'P1Y': {'product_type': 'personal_1y', 'duration_days': 365},
                    'B1M': {'product_type': 'business_1m', 'duration_days': 30},
                    'B1Y': {'product_type': 'business_1y', 'duration_days': 365},
                    'DESKTOP': {'product_type': 'desktop', 'duration_days': 365},
                    'PREMIUM': {'product_type': 'premium', 'duration_days': 365}
                }
                
                return package_mapping.get(package_code, {'product_type': 'desktop', 'duration_days': 365})
            
            return {'product_type': 'desktop', 'duration_days': 365}
            
        except Exception:
            return {'product_type': 'desktop', 'duration_days': 365}
    
    @staticmethod
    def _validate_license_expiry(license_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use local system time for basic expiry checks
        """
        try:
            expires_at = license_data.get('expires_at')
            if not expires_at:
                return {'valid': True, 'message': 'No expiry date set'}
            
            # Parse expiry date
            try:
                if isinstance(expires_at, str):
                    expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                else:
                    expiry_date = expires_at
                
                now = datetime.now()
                
                if now > expiry_date:
                    days_expired = (now - expiry_date).days
                    return {
                        'valid': False, 
                        'error': f'License expired {days_expired} days ago',
                        'expired_date': expires_at,
                        'days_expired': days_expired
                    }
                else:
                    days_remaining = (expiry_date - now).days
                    return {
                        'valid': True,
                        'message': f'License valid for {days_remaining} days',
                        'days_remaining': days_remaining,
                        'expires_at': expires_at
                    }
                    
            except Exception as date_error:
                return {'valid': False, 'error': f'Invalid expiry date format: {str(date_error)}'}
            
        except Exception as e:
            return {'valid': False, 'error': f'Expiry validation error: {str(e)}'}
    
    @staticmethod
    def _determine_available_features(license_data: Dict[str, Any], is_expired: bool = False) -> Dict[str, Any]:
        """
        Determine available features offline based on license data
        """
        try:
            # Default features
            base_features = ['basic_access']
            
            # Get features from license data
            license_features = license_data.get('features', [])
            if isinstance(license_features, str):
                try:
                    license_features = json.loads(license_features)
                except:
                    license_features = ['full_access']
            
            # Determine product type
            product_type = license_data.get('product_type', 'desktop')
            
            # Feature mapping based on product type
            feature_mapping = {
                'personal_1m': ['camera_access', 'basic_analytics', 'local_storage'],
                'personal_1y': ['camera_access', 'advanced_analytics', 'local_storage', 'cloud_sync'],
                'business_1m': ['unlimited_cameras', 'advanced_analytics', 'api_access', 'multi_user'],
                'business_1y': ['unlimited_cameras', 'advanced_analytics', 'api_access', 'multi_user', 'priority_support'],
                'desktop': ['full_access', 'camera_access', 'analytics'],
                'premium': ['full_access', 'unlimited_cameras', 'advanced_analytics', 'api_access']
            }
            
            # Get available features
            available_features = feature_mapping.get(product_type, base_features)
            
            # Apply license-specific features if available
            if 'full_access' in license_features:
                available_features = list(set(available_features + ['full_access']))
            elif license_features:
                # Use intersection of license features and product features
                available_features = list(set(available_features) & set(license_features))
                if not available_features:
                    available_features = base_features
            
            # Apply expiry limitations
            limitations = []
            if is_expired:
                # Reduce features for expired licenses
                available_features = ['basic_access', 'limited_mode']
                limitations.append('expired_license')
                limitations.append('features_reduced')
            
            # Check for crypto verification limitations
            if not license_data.get('crypto_verified') and not license_data.get('signature_verified'):
                limitations.append('unverified_signature')
                # Don't grant full access without crypto verification
                if 'full_access' in available_features:
                    available_features.remove('full_access')
                    available_features.append('limited_access')
            
            return {
                'features': available_features,
                'limitations': limitations,
                'product_type': product_type,
                'feature_source': 'offline_determination'
            }
            
        except Exception as e:
            logger.error(f"❌ Feature determination error: {str(e)}")
            return {
                'features': base_features,
                'limitations': ['feature_determination_failed'],
                'error': str(e)
            }

# Utility functions
def get_license_statistics() -> Dict[str, int]:
    """Get license usage statistics"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total licenses
            cursor.execute("SELECT COUNT(*) FROM licenses")
            stats['total_licenses'] = cursor.fetchone()[0]
            
            # Active licenses
            cursor.execute("""
                SELECT COUNT(*) FROM licenses 
                WHERE status = 'active' 
                AND (expires_at IS NULL OR expires_at > ?)
            """, (datetime.now().isoformat(),))
            stats['active_licenses'] = cursor.fetchone()[0]
            
            # Expired licenses
            cursor.execute("""
                SELECT COUNT(*) FROM licenses 
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """, (datetime.now().isoformat(),))
            stats['expired_licenses'] = cursor.fetchone()[0]
            
            return stats
            
    except Exception as e:
        logger.error(f"❌ Failed to get license statistics: {str(e)}")
        return {}

# Convenience functions for payment_routes.py compatibility
def get_active_license():
    """Get active license - convenience function"""
    return License.get_active_license()

def create_license(license_key: str, customer_email: str, **kwargs):
    """Create license - convenience function"""
    return License.create(license_key, customer_email, **kwargs)

# ==================== ENHANCED OFFLINE VALIDATION CONVENIENCE FUNCTIONS ====================

def validate_license_offline(license_key: str, strict_mode: bool = False) -> Dict[str, Any]:
    """
    Convenience function for enhanced offline license validation
    
    Args:
        license_key: License key to validate
        strict_mode: Whether to enforce strict validation rules
        
    Returns:
        dict: Comprehensive validation result
    """
    return License.validate_offline(license_key, strict_mode)

def get_license_with_validation(license_key: str) -> Dict[str, Any]:
    """
    Get license with comprehensive offline validation
    Combines database lookup with integrity checks
    """
    try:
        # First try to get from database
        license_data = License.get_by_key(license_key)
        
        if not license_data:
            return {
                'success': False,
                'error': 'License not found in database',
                'validation_performed': False
            }
        
        # Perform offline validation
        validation_result = License.validate_offline(license_key, strict_mode=False)
        
        # Combine results
        return {
            'success': True,
            'license_data': license_data,
            'validation_result': validation_result,
            'combined_status': {
                'database_found': True,
                'validation_passed': validation_result.get('valid', False),
                'checks_performed': validation_result.get('checks_performed', []),
                'available_features': validation_result.get('available_features', ['basic_access']),
                'limitations': validation_result.get('feature_limitations', [])
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Combined license validation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'validation_performed': False
        }

def check_license_features_offline(license_key: str) -> Dict[str, Any]:
    """
    Check available features for a license using offline methods
    
    Returns:
        dict: Feature availability information
    """
    try:
        validation_result = License.validate_offline(license_key, strict_mode=False)
        
        if not validation_result.get('valid'):
            return {
                'available_features': ['basic_access'],
                'limitations': ['license_invalid'],
                'error': validation_result.get('error', 'License validation failed')
            }
        
        return {
            'available_features': validation_result.get('available_features', ['basic_access']),
            'limitations': validation_result.get('feature_limitations', []),
            'product_type': validation_result.get('license_data', {}).get('product_type', 'unknown'),
            'validation_source': 'offline_determination'
        }
        
    except Exception as e:
        logger.error(f"❌ Feature check failed: {str(e)}")
        return {
            'available_features': ['basic_access'],
            'limitations': ['feature_check_failed'],
            'error': str(e)
        }

def get_enhanced_license_status() -> Dict[str, Any]:
    """
    Get enhanced license status with offline validation capabilities
    Provides comprehensive status for system health checks
    """
    try:
        # Get active license from database
        active_license = License.get_active_license()
        
        if not active_license:
            return {
                'has_license': False,
                'status': 'no_license',
                'message': 'No active license found',
                'validation_capabilities': {
                    'database': True,
                    'cryptographic': _check_crypto_capability(),
                    'offline_fallback': True
                }
            }
        
        license_key = active_license.get('license_key')
        
        # Perform comprehensive offline validation
        if license_key:
            validation_result = License.validate_offline(license_key, strict_mode=False)
        else:
            validation_result = {'valid': False, 'checks_passed': [], 'checks_failed': ['no_license_key']}
        
        return {
            'has_license': True,
            'status': 'valid' if validation_result.get('valid') else 'invalid',
            'license_data': active_license,
            'validation_summary': {
                'valid': validation_result.get('valid', False),
                'checks_passed': len(validation_result.get('checks_passed', [])),
                'checks_total': len(validation_result.get('checks_performed', [])),
                'warnings_count': len(validation_result.get('warnings', [])),
                'available_features': validation_result.get('available_features', []),
                'limitations': validation_result.get('feature_limitations', [])
            },
            'validation_details': validation_result,
            'capabilities': {
                'database': True,
                'cryptographic': _check_crypto_capability(),
                'offline_fallback': True
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Enhanced license status check failed: {str(e)}")
        return {
            'has_license': False,
            'status': 'error',
            'error': str(e),
            'capabilities': {
                'database': True,
                'cryptographic': False,
                'offline_fallback': True
            }
        }

def _check_crypto_capability() -> bool:
    """Check if cryptographic validation is available"""
    try:
        from ..payments.license_generator import LicenseGenerator
        return True
    except ImportError:
        return False

# Verify database on import (does NOT create tables)
if __name__ != "__main__":
    try:
        init_license_db()  # Only verifies tables exist
    except Exception as e:
        logger.warning(f"⚠️ License database verification failed: {str(e)}")
        logger.info("💡 Make sure to run 'python database.py' first to create tables")