# backend/modules/licensing/license_models.py
"""
V_Track License Management Models - No Duplicate Tables
Only handles database operations, tables already created in database.py
"""

import sqlite3
import json
import logging
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
    """
    
    @staticmethod
    def create(license_key: str, customer_email: str, payment_transaction_id: Optional[int] = None,
               product_type: str = 'desktop', features: Optional[List[str]] = None, 
               expires_days: int = 365) -> Optional[int]:
        """
        Create new license record in database - FIXED VERSION
        
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
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Calculate expiration date
                expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
                
                # Prepare features JSON
                features_json = json.dumps(features or ['full_access'])
                
                # FIXED SQL - Correct column mapping with database.py schema
                cursor.execute("""
                INSERT INTO licenses 
                (license_key, customer_email, payment_transaction_id, 
                product_type, features, status, expires_at, activated_at, license_type)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """, (license_key, customer_email, payment_transaction_id, 
                product_type, features_json, expires_at, datetime.now().isoformat(), product_type))
                
                license_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ License created: ID {license_id} for {customer_email}")
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
                
                # Add package_name field for payment_routes compatibility
                license_data['package_name'] = license_data.get('product_type', 'desktop')
                
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
                    
                    # Add package_name field for compatibility
                    license_data['package_name'] = license_data.get('product_type', 'desktop')
                    
                    licenses.append(license_data)
                
                logger.info(f"📋 Found {len(licenses)} licenses for {customer_email}")
                return licenses
                
        except Exception as e:
            logger.error(f"❌ Failed to get licenses by email: {str(e)}")
            return []
    
    @staticmethod
    def get_active_license() -> Optional[Dict[str, Any]]:
        """
        Get current active license (singular) - FOR payment_routes.py
        
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
                
                # Add package_name field for payment_routes compatibility
                license_data['package_name'] = license_data.get('product_type', 'desktop')
                
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

# Verify database on import (does NOT create tables)
if __name__ != "__main__":
    try:
        init_license_db()  # Only verifies tables exist
    except Exception as e:
        logger.warning(f"⚠️ License database verification failed: {str(e)}")
        logger.info("💡 Make sure to run 'python database.py' first to create tables")