# backend/modules/licensing/repositories/license_repository.py
"""
License Repository - Unified Database Operations for V_Track License System
ELIMINATES: 8x Database patterns, 6x Row-to-dict, 4x JSON parsing from license_models.py
Created: 2025-08-11 - Phase 1 Refactoring Step 2
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

# Import base repository
from base_repository import BaseRepository, DatabaseError

logger = logging.getLogger(__name__)

class LicenseRepository(BaseRepository):
    """
    Unified repository for all license database operations
    ELIMINATES duplicate patterns from license_models.py
    """
    
    def get_table_name(self) -> str:
        """Return primary table name"""
        return "licenses"
    
    def get_required_fields(self) -> List[str]:
        """Return required fields for license creation"""
        return ["license_key", "customer_email", "product_type"]
    
    # ==================== LICENSE CRUD OPERATIONS ====================
    
    def create_license(self, license_key: str, customer_email: str, 
                      payment_transaction_id: Optional[int] = None,
                      product_type: str = 'desktop', 
                      features: Optional[List[str]] = None, 
                      expires_days: int = 365) -> Optional[int]:
        """
        Create new license record - UNIFIED CREATION
        ELIMINATES: Duplicate creation logic from License.create()
        
        Args:
            license_key: Generated license key
            customer_email: Customer email address
            payment_transaction_id: Associated payment transaction ID
            product_type: Type of product license
            features: List of enabled features
            expires_days: Number of days until expiration
            
        Returns:
            int: License ID if created successfully, None otherwise
        """
        try:
            # Validate required fields
            license_data = {
                'license_key': license_key,
                'customer_email': customer_email,
                'product_type': product_type
            }
            
            if not self._validate_required_fields(license_data, self.get_required_fields()):
                logger.error("❌ License creation failed: Missing required fields")
                return None
            
            # Calculate expiration date
            expires_at = self._format_datetime(
                datetime.now() + timedelta(days=expires_days)
            )
            
            # Prepare features JSON
            features_json = json.dumps(features or ['full_access'])
            
            # Create license record
            insert_query = """
                INSERT INTO licenses 
                (license_key, customer_email, payment_transaction_id, 
                 product_type, features, status, expires_at, activated_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """
            
            params = (
                license_key, customer_email, payment_transaction_id,
                product_type, features_json, expires_at, 
                self._format_datetime(datetime.now())
            )
            
            license_id = self._execute_insert_update(insert_query, params)
            
            if license_id and isinstance(license_id, int) and license_id > 0:
                logger.info(f"✅ License created: ID {license_id} for {customer_email}")
                logger.debug(f"📋 Product type: {product_type}")
                logger.debug(f"📋 License key: {license_key[:12]}...")
                return license_id
            else:
                logger.error("❌ License creation failed: Insert returned no valid ID")
                return None
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"⚠️ License key already exists: {license_key[:12]}...")
                return None
            else:
                logger.error(f"❌ Database integrity error: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"❌ License creation failed: {str(e)}")
            return None
    
    def get_license_by_key(self, license_key: str) -> Optional[Dict[str, Any]]:
        """
        Get license by license key - UNIFIED LOOKUP
        ELIMINATES: Duplicate lookup logic from License.get_by_key()
        
        Args:
            license_key: License key to search for
            
        Returns:
            dict: License data if found, None otherwise
        """
        try:
            query = "SELECT * FROM licenses WHERE license_key = ?"
            params = (license_key,)
            
            license_data = self._execute_query_single(query, params, self.get_table_name())
            
            if not license_data:
                logger.debug(f"🔍 License not found: {license_key[:12]}...")
                return None
            
            # Parse JSON fields using unified parser
            license_data['features'] = self._parse_json_field(
                license_data, 'features', ['full_access']
            )
            
            logger.debug(f"✅ License found: {license_key[:12]}... for {license_data.get('customer_email')}")
            return license_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get license by key: {str(e)}")
            return None
    
    def get_licenses_by_email(self, customer_email: str) -> List[Dict[str, Any]]:
        """
        Get all licenses for customer email - UNIFIED MULTI-LOOKUP
        ELIMINATES: Duplicate multi-row logic from License.get_by_email()
        
        Args:
            customer_email: Customer email address
            
        Returns:
            List of license dictionaries
        """
        try:
            query = """
                SELECT * FROM licenses 
                WHERE customer_email = ?
                ORDER BY created_at DESC
            """
            params = (customer_email,)
            
            licenses_data = self._execute_query_with_result(query, params, self.get_table_name())
            
            if not licenses_data:
                logger.debug(f"🔍 No licenses found for: {customer_email}")
                return []
            
            # Parse JSON fields for all licenses using unified parser
            for license_data in licenses_data:
                license_data['features'] = self._parse_json_field(
                    license_data, 'features', ['full_access']
                )
            
            logger.info(f"📋 Found {len(licenses_data)} licenses for {customer_email}")
            return licenses_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get licenses by email: {str(e)}")
            return []
    
    def get_active_license(self) -> Optional[Dict[str, Any]]:
        """
        Get current active license - UNIFIED ACTIVE LOOKUP
        ELIMINATES: Duplicate active license logic from License.get_active_license()
        
        Returns:
            dict: Active license data if found, None otherwise
        """
        try:
            current_time = self._format_datetime(datetime.now())
            
            query = """
                SELECT * FROM licenses 
                WHERE status = 'active' 
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                LIMIT 1
            """
            params = (current_time,)
            
            license_data = self._execute_query_single(query, params, self.get_table_name())
            
            if not license_data:
                logger.debug("🔍 No active license found")
                return None
            
            # Parse JSON fields using unified parser
            license_data['features'] = self._parse_json_field(
                license_data, 'features', ['full_access']
            )
            
            logger.debug(f"✅ Active license found for {license_data.get('customer_email')}")
            return license_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get active license: {str(e)}")
            return None
    
    def update_license_status(self, license_key: str, status: str) -> bool:
        """
        Update license status - UNIFIED UPDATE
        ELIMINATES: Duplicate update logic from License.update_status()
        
        Args:
            license_key: License key to update
            status: New status value
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Validate status
            valid_statuses = ['active', 'inactive', 'expired', 'suspended']
            if status not in valid_statuses:
                logger.error(f"❌ Invalid status: {status}. Must be one of {valid_statuses}")
                return False
            
            query = "UPDATE licenses SET status = ? WHERE license_key = ?"
            params = (status, license_key)
            
            success = self._execute_insert_update(query, params)
            
            if success and isinstance(success, bool):
                logger.info(f"✅ License status updated: {license_key[:12]}... -> {status}")
                return True
            else:
                logger.warning(f"⚠️ License not found for update: {license_key[:12]}...")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to update license status: {str(e)}")
            return False
    
    def delete_license(self, license_key: str) -> bool:
        """
        Delete license record - UNIFIED DELETION
        ELIMINATES: Duplicate deletion logic from License.delete()
        
        Args:
            license_key: License key to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            query = "DELETE FROM licenses WHERE license_key = ?"
            params = (license_key,)
            
            success = self._execute_insert_update(query, params)
            
            if success and isinstance(success, bool):
                logger.info(f"✅ License deleted: {license_key[:12]}...")
                return True
            else:
                logger.warning(f"⚠️ License not found for deletion: {license_key[:12]}...")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to delete license: {str(e)}")
            return False
    
    # ==================== ENHANCED VALIDATION METHODS ====================
    
    def validate_license_integrity(self, license_key: str) -> Dict[str, Any]:
        """
        Enhanced license integrity validation - UNIFIED VALIDATION
        ELIMINATES: Duplicate validation logic from License._validate_database_integrity()
        
        Args:
            license_key: License key to validate
            
        Returns:
            dict: Comprehensive validation result
        """
        try:
            # Get license with activation data
            query = """
                SELECT l.*, la.machine_fingerprint, la.activation_time, la.status as activation_status
                FROM licenses l
                LEFT JOIN license_activations la ON l.id = la.license_id
                WHERE l.license_key = ?
                ORDER BY la.activation_time DESC
                LIMIT 1
            """
            params = (license_key,)
            
            # Use base method but handle complex join manually
            results = self._execute_query_with_result(query, params, self.get_table_name())
            
            if not results:
                return {
                    'valid': False,
                    'error': 'License not found in database',
                    'license_data': None
                }
            
            row_data = results[0]
            if not row_data:
                return {
                    'valid': False,
                    'error': 'Invalid license data returned',
                    'license_data': None
                }
            
            # Parse features JSON
            row_data['features'] = self._parse_json_field(row_data, 'features', ['full_access'])
            
            # Integrity checks
            integrity_issues = []
            
            # Check required fields
            for field in self.get_required_fields():
                if not row_data.get(field):
                    integrity_issues.append(f'Missing required field: {field}')
            
            # Check license key consistency
            if row_data.get('license_key') != license_key:
                integrity_issues.append('License key mismatch')
            
            # Check status validity
            valid_statuses = ['active', 'inactive', 'expired', 'suspended']
            if row_data.get('status') not in valid_statuses:
                integrity_issues.append(f'Invalid status: {row_data.get("status")}')
            
            # Extract activation data if present
            if (row_data.get('machine_fingerprint') is not None or 
                row_data.get('activation_time') is not None):
                row_data['activation_data'] = {
                    'machine_fingerprint': row_data.get('machine_fingerprint'),
                    'activation_time': row_data.get('activation_time'),
                    'activation_status': row_data.get('activation_status')
                }
            
            if integrity_issues:
                return {
                    'valid': False,
                    'error': f'Database integrity issues: {", ".join(integrity_issues)}',
                    'license_data': row_data,
                    'integrity_issues': integrity_issues
                }
            
            return {
                'valid': True,
                'license_data': row_data,
                'integrity_verified': True
            }
            
        except Exception as e:
            logger.error(f"❌ License integrity validation failed: {str(e)}")
            return {
                'valid': False,
                'error': f'Integrity validation failed: {str(e)}',
                'license_data': None
            }
    
    def check_license_expiry(self, license_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check license expiry status - UNIFIED EXPIRY CHECK
        ELIMINATES: Duplicate expiry logic from License._validate_license_expiry()
        
        Args:
            license_data: License data dictionary
            
        Returns:
            dict: Expiry validation result
        """
        try:
            expires_at = license_data.get('expires_at')
            if not expires_at:
                return {
                    'valid': True,
                    'expired': False,
                    'message': 'No expiry date set (lifetime license)'
                }
            
            # Parse expiry date using unified formatter
            current_time = datetime.now()
            
            try:
                if isinstance(expires_at, str):
                    expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                else:
                    expiry_date = expires_at
                
                if current_time > expiry_date:
                    days_expired = (current_time - expiry_date).days
                    return {
                        'valid': False,
                        'expired': True,
                        'error': f'License expired {days_expired} days ago',
                        'expired_date': expires_at,
                        'days_expired': days_expired
                    }
                else:
                    days_remaining = (expiry_date - current_time).days
                    return {
                        'valid': True,
                        'expired': False,
                        'message': f'License valid for {days_remaining} days',
                        'days_remaining': days_remaining,
                        'expires_at': expires_at
                    }
                    
            except Exception as date_error:
                return {
                    'valid': False,
                    'error': f'Invalid expiry date format: {str(date_error)}',
                    'expired': True
                }
            
        except Exception as e:
            logger.error(f"❌ Expiry check failed: {str(e)}")
            return {
                'valid': False,
                'error': f'Expiry validation error: {str(e)}',
                'expired': True
            }
    
    # ==================== STATISTICS AND UTILITIES ====================
    
    def get_license_statistics(self) -> Dict[str, Any]:
        """
        Get license usage statistics - UNIFIED STATS
        ELIMINATES: Duplicate statistics logic from get_license_statistics()
        
        Returns:
            dict: License statistics
        """
        try:
            stats = {}
            current_time = self._format_datetime(datetime.now())
            
            # Total licenses
            total_query = "SELECT COUNT(*) as total FROM licenses"
            total_result = self._execute_query_with_result(total_query, (), self.get_table_name())
            stats['total_licenses'] = total_result[0]['total'] if total_result and total_result[0] else 0
            
            # Active licenses
            active_query = """
                SELECT COUNT(*) as active FROM licenses 
                WHERE status = 'active' 
                AND (expires_at IS NULL OR expires_at > ?)
            """
            active_result = self._execute_query_with_result(active_query, (current_time,), self.get_table_name())
            stats['active_licenses'] = active_result[0]['active'] if active_result and active_result[0] else 0
            
            # Expired licenses
            expired_query = """
                SELECT COUNT(*) as expired FROM licenses 
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """
            expired_result = self._execute_query_with_result(expired_query, (current_time,), self.get_table_name())
            stats['expired_licenses'] = expired_result[0]['expired'] if expired_result and expired_result[0] else 0
            
            logger.debug(f"📊 License statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get license statistics: {str(e)}")
            return {
                'total_licenses': 0,
                'active_licenses': 0,
                'expired_licenses': 0,
                'error': str(e)
            }
    
    def find_licenses_by_product_type(self, product_type: str) -> List[Dict[str, Any]]:
        """
        Find licenses by product type - NEW UNIFIED METHOD
        
        Args:
            product_type: Product type to search for
            
        Returns:
            List of matching licenses
        """
        try:
            query = """
                SELECT * FROM licenses 
                WHERE product_type = ?
                ORDER BY created_at DESC
            """
            params = (product_type,)
            
            licenses_data = self._execute_query_with_result(query, params, self.get_table_name())
            
            # Parse JSON fields for all licenses
            for license_data in licenses_data:
                license_data['features'] = self._parse_json_field(
                    license_data, 'features', ['full_access']
                )
            
            logger.info(f"📋 Found {len(licenses_data)} licenses for product type: {product_type}")
            return licenses_data
            
        except Exception as e:
            logger.error(f"❌ Failed to find licenses by product type: {str(e)}")
            return []
    
    def get_licenses_expiring_soon(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        """
        Get licenses expiring within threshold - NEW UTILITY METHOD
        
        Args:
            days_threshold: Number of days to look ahead
            
        Returns:
            List of licenses expiring soon
        """
        try:
            threshold_date = self._format_datetime(
                datetime.now() + timedelta(days=days_threshold)
            )
            current_time = self._format_datetime(datetime.now())
            
            query = """
                SELECT * FROM licenses 
                WHERE status = 'active'
                AND expires_at IS NOT NULL 
                AND expires_at > ?
                AND expires_at <= ?
                ORDER BY expires_at ASC
            """
            params = (current_time, threshold_date)
            
            licenses_data = self._execute_query_with_result(query, params, self.get_table_name())
            
            # Parse JSON fields and add expiry info
            for license_data in licenses_data:
                license_data['features'] = self._parse_json_field(
                    license_data, 'features', ['full_access']
                )
                
                # Add days until expiry
                expires_at = license_data.get('expires_at')
                if expires_at:
                    try:
                        expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        days_remaining = (expiry_date - datetime.now()).days
                        license_data['days_until_expiry'] = max(0, days_remaining)
                    except Exception:
                        license_data['days_until_expiry'] = 0
                else:
                    license_data['days_until_expiry'] = None
            
            logger.info(f"📋 Found {len(licenses_data)} licenses expiring within {days_threshold} days")
            return licenses_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get expiring licenses: {str(e)}")
            return []

# Singleton instance for backward compatibility
_license_repository: Optional[LicenseRepository] = None

def get_license_repository() -> LicenseRepository:
    """Get singleton license repository instance"""
    global _license_repository
    if _license_repository is None:
        _license_repository = LicenseRepository()
    return _license_repository

def reset_license_repository():
    """Reset singleton (for testing)"""
    global _license_repository
    _license_repository = None

# Test repository functionality
if __name__ == "__main__":
    print("🧪 Testing LicenseRepository...")
    
    try:
        repo = LicenseRepository()
        print(f"✅ Repository created - Table: {repo.get_table_name()}")
        print(f"✅ Required fields: {repo.get_required_fields()}")
        
        # Test JSON parsing
        test_data = {"features": '["camera_access", "analytics"]'}
        parsed = repo._parse_json_field(test_data, "features", [])
        print(f"✅ JSON parsing test: {parsed}")
        
        # Test datetime formatting
        dt_str = repo._format_datetime(datetime.now())
        if dt_str:
            print(f"✅ Datetime formatting: {dt_str[:19]}...")
        else:
            print("❌ Datetime formatting returned None")
        
        print("🎉 LicenseRepository basic tests passed!")
        
    except Exception as e:
        print(f"❌ LicenseRepository test failed: {e}")