# backend/modules/account/account.py
"""User management for first-run detection"""
import logging
from typing import Dict, Optional
from datetime import datetime
from modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)

def check_user_status() -> Dict[str, bool]:
    """Check if user exists and has license"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check users
            cursor.execute("SELECT COUNT(*) FROM user_profiles")
            user_count = cursor.fetchone()[0]
            
            # Check licenses  
            cursor.execute("""
                SELECT COUNT(*) FROM licenses 
                WHERE status = 'active' 
                AND (expires_at IS NULL OR expires_at > ?)
            """, (datetime.now().isoformat(),))
            license_count = cursor.fetchone()[0]
            
            return {
                'has_user': user_count > 0,
                'has_license': license_count > 0
            }
    except Exception as e:
        logger.error(f"User status check failed: {e}")
        return {'has_user': False, 'has_license': False}

def create_user_profile(user_info: dict) -> bool:
    """Create new user profile from OAuth data"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles (
                    gmail_address, display_name, photo_url, 
                    first_login, last_login, auto_setup_complete
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE)
            """, (
                user_info.get('email'),
                user_info.get('name'),
                user_info.get('picture')
            ))
        
        logger.info(f"✅ User profile created: {user_info.get('email')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating user profile: {e}")
        return False