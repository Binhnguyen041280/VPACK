# backend/modules/licensing/license_models.py

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from modules.db_utils import get_db_connection

logger = logging.getLogger(__name__)

def init_license_db():
    """
    Initialize license management tables trong existing database
    Extends current V_track database với licensing functionality
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Payment Transactions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_trans_id TEXT UNIQUE NOT NULL,
                    zalopay_trans_id TEXT,
                    customer_email TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_data TEXT,  -- JSON metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # 2. Licenses Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT UNIQUE NOT NULL,
                    customer_email TEXT NOT NULL,
                    payment_transaction_id INTEGER,
                    product_type TEXT DEFAULT 'desktop',
                    features TEXT,  -- JSON array của features
                    status TEXT DEFAULT 'generated',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    activated_at TIMESTAMP,
                    machine_fingerprint TEXT,
                    activation_count INTEGER DEFAULT 0,
                    max_activations INTEGER DEFAULT 1,
                    FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions(id)
                )
            """)
            
            # 3. License Activations Table (tracking multiple activations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS license_activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id INTEGER NOT NULL,
                    machine_fingerprint TEXT NOT NULL,
                    activation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    device_info TEXT,  -- JSON với device details
                    FOREIGN KEY (license_id) REFERENCES licenses(id),
                    UNIQUE(license_id, machine_fingerprint)
                )
            """)
            
            # 4. Email Log Table (tracking email delivery)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id INTEGER,
                    recipient_email TEXT NOT NULL,
                    email_type TEXT DEFAULT 'license_delivery',
                    subject TEXT,
                    status TEXT DEFAULT 'pending',
                    sent_at TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (license_id) REFERENCES licenses(id)
                )
            """)
            
            # 5. License Usage Stats (optional analytics)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS license_usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    usage_hours REAL DEFAULT 0,
                    feature_usage TEXT,  -- JSON tracking feature usage
                    performance_metrics TEXT,  -- JSON với performance data
                    FOREIGN KEY (license_id) REFERENCES licenses(id),
                    UNIQUE(license_id, date)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_email ON payment_transactions(customer_email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_status ON payment_transactions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_license_email ON licenses(customer_email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_license_status ON licenses(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activation_license ON license_activations(license_id)")
            
            conn.commit()
            logger.info("License database tables initialized successfully")
            
            # Verify tables created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%license%' OR name LIKE '%payment%'")
            tables = cursor.fetchall()
            logger.info(f"Created license tables: {[table[0] for table in tables]}")
            
    except Exception as e:
        logger.error(f"Failed to initialize license database: {str(e)}")
        raise

class PaymentTransaction:
    """Model for payment transactions"""
    
    @staticmethod
    def create(app_trans_id, customer_email, amount, payment_data=None):
        """Create new payment transaction"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO payment_transactions 
                    (app_trans_id, customer_email, amount, status, payment_data)
                    VALUES (?, ?, ?, 'pending', ?)
                """, (
                    app_trans_id,
                    customer_email,
                    amount,
                    json.dumps(payment_data) if payment_data else None
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to create payment transaction: {str(e)}")
            return None
    
    @staticmethod
    def get_by_app_trans_id(app_trans_id):
        """Get payment transaction by app_trans_id"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payment_transactions 
                    WHERE app_trans_id = ?
                """, (app_trans_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'app_trans_id': row[1],
                        'zalopay_trans_id': row[2],
                        'customer_email': row[3],
                        'amount': row[4],
                        'status': row[5],
                        'payment_data': json.loads(row[6]) if row[6] else {},
                        'created_at': row[7],
                        'completed_at': row[8]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get payment transaction: {str(e)}")
            return None
    
    @staticmethod
    def update_status(app_trans_id, status, zalopay_trans_id=None):
        """Update payment transaction status"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                update_fields = ["status = ?", "completed_at = ?"]
                update_values = [status, datetime.now() if status == 'completed' else None]
                
                if zalopay_trans_id:
                    update_fields.append("zalopay_trans_id = ?")
                    update_values.append(zalopay_trans_id)
                
                update_values.append(app_trans_id)
                
                cursor.execute(f"""
                    UPDATE payment_transactions 
                    SET {', '.join(update_fields)}
                    WHERE app_trans_id = ?
                """, update_values)
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update payment status: {str(e)}")
            return False

class License:
    """Model for license management"""
    
    @staticmethod
    def create(license_key, customer_email, payment_transaction_id, product_type='desktop', features=None, expires_days=365):
        """Create new license"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                expires_at = datetime.now() + timedelta(days=expires_days)
                features_json = json.dumps(features) if features else json.dumps(['full_access'])
                
                cursor.execute("""
                    INSERT INTO licenses 
                    (license_key, customer_email, payment_transaction_id, product_type, features, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    license_key,
                    customer_email,
                    payment_transaction_id,
                    product_type,
                    features_json,
                    expires_at
                ))
                
                conn.commit()
                license_id = cursor.lastrowid
                logger.info(f"Created license {license_id} for {customer_email}")
                return license_id
                
        except Exception as e:
            logger.error(f"Failed to create license: {str(e)}")
            return None
    
    @staticmethod
    def get_by_key(license_key):
        """Get license by license key"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM licenses 
                    WHERE license_key = ?
                """, (license_key,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'license_key': row[1],
                        'customer_email': row[2],
                        'payment_transaction_id': row[3],
                        'product_type': row[4],
                        'features': json.loads(row[5]) if row[5] else [],
                        'status': row[6],
                        'created_at': row[7],
                        'expires_at': row[8],
                        'activated_at': row[9],
                        'machine_fingerprint': row[10],
                        'activation_count': row[11],
                        'max_activations': row[12]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get license: {str(e)}")
            return None
    
    @staticmethod
    def get_by_email(customer_email):
        """Get all licenses for customer email"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM licenses 
                    WHERE customer_email = ?
                    ORDER BY created_at DESC
                """, (customer_email,))
                
                rows = cursor.fetchall()
                licenses = []
                
                for row in rows:
                    licenses.append({
                        'id': row[0],
                        'license_key': row[1],
                        'customer_email': row[2],
                        'payment_transaction_id': row[3],
                        'product_type': row[4],
                        'features': json.loads(row[5]) if row[5] else [],
                        'status': row[6],
                        'created_at': row[7],
                        'expires_at': row[8],
                        'activated_at': row[9],
                        'machine_fingerprint': row[10],
                        'activation_count': row[11],
                        'max_activations': row[12]
                    })
                
                return licenses
                
        except Exception as e:
            logger.error(f"Failed to get licenses for email: {str(e)}")
            return []
    
    @staticmethod
    def activate(license_key, machine_fingerprint, device_info=None):
        """Activate license on specific machine"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get license info
                license_data = License.get_by_key(license_key)
                if not license_data:
                    return {'success': False, 'error': 'License not found'}
                
                # Check if license is already activated on this machine
                cursor.execute("""
                    SELECT * FROM license_activations 
                    WHERE license_id = ? AND machine_fingerprint = ?
                """, (license_data['id'], machine_fingerprint))
                
                existing_activation = cursor.fetchone()
                
                if existing_activation:
                    # Update heartbeat
                    cursor.execute("""
                        UPDATE license_activations 
                        SET last_heartbeat = ?, status = 'active'
                        WHERE license_id = ? AND machine_fingerprint = ?
                    """, (datetime.now(), license_data['id'], machine_fingerprint))
                    
                    conn.commit()
                    return {'success': True, 'status': 'already_activated'}
                
                # Check activation limits
                if license_data['activation_count'] >= license_data['max_activations']:
                    return {'success': False, 'error': 'Maximum activations reached'}
                
                # Check expiration
                if license_data['expires_at']:
                    expires_at = datetime.fromisoformat(license_data['expires_at'])
                    if datetime.now() > expires_at:
                        return {'success': False, 'error': 'License expired'}
                
                # Create new activation
                cursor.execute("""
                    INSERT INTO license_activations 
                    (license_id, machine_fingerprint, device_info, last_heartbeat)
                    VALUES (?, ?, ?, ?)
                """, (
                    license_data['id'],
                    machine_fingerprint,
                    json.dumps(device_info) if device_info else None,
                    datetime.now()
                ))
                
                # Update license activation count and status
                cursor.execute("""
                    UPDATE licenses 
                    SET activation_count = activation_count + 1,
                        activated_at = COALESCE(activated_at, ?),
                        status = 'active'
                    WHERE id = ?
                """, (datetime.now(), license_data['id']))
                
                conn.commit()
                logger.info(f"License {license_key} activated on machine {machine_fingerprint[:8]}...")
                return {'success': True, 'status': 'activated'}
                
        except Exception as e:
            logger.error(f"Failed to activate license: {str(e)}")
            return {'success': False, 'error': f'Activation error: {str(e)}'}
    
    @staticmethod
    def validate(license_key, machine_fingerprint=None):
        """Validate license status"""
        try:
            license_data = License.get_by_key(license_key)
            if not license_data:
                return {'valid': False, 'error': 'License not found'}
            
            # Check expiration
            if license_data['expires_at']:
                expires_at = datetime.fromisoformat(license_data['expires_at'])
                if datetime.now() > expires_at:
                    return {'valid': False, 'error': 'License expired'}
            
            # Check status
            if license_data['status'] not in ['active', 'generated']:
                return {'valid': False, 'error': f'License status: {license_data["status"]}'}
            
            # If machine fingerprint provided, check activation
            if machine_fingerprint:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT status FROM license_activations 
                        WHERE license_id = ? AND machine_fingerprint = ?
                    """, (license_data['id'], machine_fingerprint))
                    
                    activation = cursor.fetchone()
                    if not activation:
                        return {'valid': False, 'error': 'License not activated on this machine'}
                    
                    if activation[0] != 'active':
                        return {'valid': False, 'error': f'Activation status: {activation[0]}'}
            
            return {
                'valid': True,
                'license_data': license_data
            }
            
        except Exception as e:
            logger.error(f"Failed to validate license: {str(e)}")
            return {'valid': False, 'error': f'Validation error: {str(e)}'}

class EmailLog:
    """Model for email delivery tracking"""
    
    @staticmethod
    def create(license_id, recipient_email, email_type, subject):
        """Create email log entry"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO email_logs 
                    (license_id, recipient_email, email_type, subject)
                    VALUES (?, ?, ?, ?)
                """, (license_id, recipient_email, email_type, subject))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to create email log: {str(e)}")
            return None
    
    @staticmethod
    def update_status(log_id, status, error_message=None):
        """Update email delivery status"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE email_logs 
                    SET status = ?, sent_at = ?, error_message = ?
                    WHERE id = ?
                """, (
                    status,
                    datetime.now() if status == 'sent' else None,
                    error_message,
                    log_id
                ))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update email log: {str(e)}")
            return False

# Utility functions
def get_license_stats():
    """Get licensing statistics"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total licenses
            cursor.execute("SELECT COUNT(*) FROM licenses")
            total_licenses = cursor.fetchone()[0]
            
            # Active licenses
            cursor.execute("SELECT COUNT(*) FROM licenses WHERE status = 'active'")
            active_licenses = cursor.fetchone()[0]
            
            # Recent payments (last 30 days)
            cursor.execute("""
                SELECT COUNT(*) FROM payment_transactions 
                WHERE created_at > datetime('now', '-30 days') AND status = 'completed'
            """)
            recent_payments = cursor.fetchone()[0]
            
            # Revenue (last 30 days)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM payment_transactions 
                WHERE created_at > datetime('now', '-30 days') AND status = 'completed'
            """)
            recent_revenue = cursor.fetchone()[0]
            
            return {
                'total_licenses': total_licenses,
                'active_licenses': active_licenses,
                'recent_payments': recent_payments,
                'recent_revenue': recent_revenue
            }
            
    except Exception as e:
        logger.error(f"Failed to get license stats: {str(e)}")
        return None

def cleanup_expired_licenses():
    """Cleanup expired and old data"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Deactivate expired licenses
            cursor.execute("""
                UPDATE licenses 
                SET status = 'expired' 
                WHERE expires_at < datetime('now') AND status != 'expired'
            """)
            
            expired_count = cursor.rowcount
            
            # Cleanup old payment transactions (older than 1 year)
            cursor.execute("""
                DELETE FROM payment_transactions 
                WHERE created_at < datetime('now', '-1 year') AND status = 'pending'
            """)
            
            cleaned_payments = cursor.rowcount
            
            conn.commit()
            logger.info(f"License cleanup: {expired_count} expired, {cleaned_payments} old payments removed")
            
            return {'expired_licenses': expired_count, 'cleaned_payments': cleaned_payments}
            
    except Exception as e:
        logger.error(f"License cleanup failed: {str(e)}")
        return None