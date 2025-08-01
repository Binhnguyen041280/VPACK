
import sqlite3
import os
from datetime import datetime
from modules.db_utils import get_db_connection

def init_zalopay_database():
    """Initialize ZaloPay integration database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Payment Transactions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_trans_id TEXT NOT NULL UNIQUE,
                zalopay_trans_id TEXT,
                customer_email TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Licenses Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL UNIQUE,
                customer_email TEXT NOT NULL,
                license_type TEXT NOT NULL,
                machine_id TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activated_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                payment_transaction_id INTEGER,
                FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions (id)
            )
        """)
        
        # Email Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                email_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                license_id INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (license_id) REFERENCES licenses (id)
            )
        """)
        
        # Create Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_status ON payment_transactions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_email ON payment_transactions(customer_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(customer_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_active ON licenses(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_logs_type ON email_logs(email_type)")
        
        conn.commit()
        conn.close()
        
        print("✅ ZaloPay database tables created successfully")
        print("  - payment_transactions")
        print("  - licenses") 
        print("  - email_logs")
        print("  - All indexes created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating ZaloPay tables: {e}")
        return False

if __name__ == "__main__":
    init_zalopay_database()