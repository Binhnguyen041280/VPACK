# backend/modules/licensing/license_models.py
"""
V_Track License Management Models - FIXED VERSION
Handles both license_type and product_type columns
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
    try:
        from backend.modules.db_utils import get_db_connection
    except ImportError:
        from database import get_db_connection

logger = logging.getLogger(__name__)

class License:
    """
    Model for license management - FIXED VERSION
    Handles both license_type and product_type columns
    """
    
    @staticmethod
    def create(license_key: str, customer_email: str, payment_transaction_id: Optional[int] = None,
               product_type: str = 'desktop', features: Optional[List[str]] = None, 
               expires_days: int = 365) -> Optional[int]:
        """
        Create new license record in database - FIXED FOR BOTH COLUMNS
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Calculate expiration date
                expires_at = datetime.now() + timedelta(days=expires_days)
                
                # Prepare features JSON
                features_json = json.dumps(features or ['full_access'])
                
                # Check which columns exist
                cursor.execute("PRAGMA table_info(licenses)")
                columns = [col[1] for col in cursor.fetchall()]
                
                has_license_type = 'license_type' in columns
                has_product_type = 'product_type' in columns
                
                # Build INSERT query based on available columns
                if has_license_type and has_product_type:
                    # Both columns exist - insert into both
                    cursor.execute("""
                        INSERT INTO licenses 
                        (license_key, customer_email, payment_transaction_id, 
                         license_type, product_type, features, status, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'generated', ?)
                    """, (license_key, customer_email, payment_transaction_id, 
                          product_type, product_type, features_json, expires_at))
                          
                elif has_license_type:
                    # Only license_type exists
                    cursor.execute("""
                        INSERT INTO licenses 
                        (license_key, customer_email, payment_transaction_id, 
                         license_type, features, status, expires_at)
                        VALUES (?, ?, ?, ?, ?, 'generated', ?)
                    """, (license_key, customer_email, payment_transaction_id, 
                          product_type, features_json, expires_at))
                          
                elif has_product_type:
                    # Only product_type exists  
                    cursor.execute("""
                        INSERT INTO licenses 
                        (license_key, customer_email, payment_transaction_id, 
                         product_type, features, status, expires_at)
                        VALUES (?, ?, ?, ?, ?, 'generated', ?)
                    """, (license_key, customer_email, payment_transaction_id, 
                          product_type, features_json, expires_at))
                else:
                    # Neither column exists - basic insert
                    cursor.execute("""
                        INSERT INTO licenses 
                        (license_key, customer_email, payment_transaction_id, 
                         features, status, expires_at)
                        VALUES (?, ?, ?, ?, 'generated', ?)
                    """, (license_key, customer_email, payment_transaction_id, 
                          features_json, expires_at))
                
                license_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ License created: ID {license_id} for {customer_email}")
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
        Get license by license key - WORKS WITH BOTH COLUMNS
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
                
                # Normalize product_type from either column
                if 'product_type' in license_data:
                    product_type = license_data['product_type']
                elif 'license_type' in license_data:
                    product_type = license_data['license_type']
                    license_data['product_type'] = product_type  # Add for compatibility
                else:
                    product_type = 'desktop'
                    license_data['product_type'] = product_type
                
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
    def activate(license_key: str, machine_fingerprint: Optional[str] = None, device_info: Optional[Dict] = None) -> bool:
        """
        Activate a license for a specific machine
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # First, get the license
                license_data = License.get_by_key(license_key)
                if not license_data:
                    logger.warning(f"⚠️ License not found for activation: {license_key[:12]}...")
                    return False
                
                # Update license status and activation info
                cursor.execute("""
                    UPDATE licenses 
                    SET status = 'active', activated_at = ?, machine_fingerprint = ?,
                        activation_count = COALESCE(activation_count, 0) + 1
                    WHERE license_key = ?
                """, (datetime.now(), machine_fingerprint, license_key))
                
                conn.commit()
                
                logger.info(f"✅ License activated: {license_key[:12]}...")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to activate license: {str(e)}")
            return False
    
    @staticmethod
    def is_valid(license_key: str, machine_fingerprint: Optional[str] = None) -> bool:
        """
        Check if license is valid and active
        """
        try:
            license_data = License.get_by_key(license_key)
            if not license_data:
                return False
            
            # Check status
            status = license_data.get('status', 'active')
            if status not in ['generated', 'active']:
                return False
            
            # Check expiration
            if license_data.get('expires_at'):
                expires_at = datetime.fromisoformat(license_data['expires_at'])
                if datetime.now() > expires_at:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to validate license: {str(e)}")
            return False

def init_license_db():
    """Initialize license database tables"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Just ensure basic indexes exist
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_license_key ON licenses(license_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_license_email ON licenses(customer_email)")
            
            conn.commit()
            logger.info("✅ License database ready")
            
    except Exception as e:
        logger.warning(f"⚠️ License database initialization: {str(e)}")

# Auto-initialize on import
try:
    init_license_db()
except Exception as e:
    logger.warning(f"⚠️ License database auto-initialization failed: {str(e)}")
