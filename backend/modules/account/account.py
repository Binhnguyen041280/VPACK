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
            
            # Get authentication method from user_info
            auth_method = user_info.get('authentication_method', 'gmail_only')
            google_drive_connected = auth_method == 'google_drive'
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles (
                    gmail_address, display_name, photo_url, 
                    first_login, last_login, auto_setup_complete,
                    authentication_method, google_drive_connected
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE, ?, ?)
            """, (
                user_info.get('email'),
                user_info.get('name'),
                user_info.get('picture', user_info.get('photo_url')),
                auth_method,
                google_drive_connected
            ))
        
        logger.info(f"✅ User profile created: {user_info.get('email')} (auth: {auth_method})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating user profile: {e}")
        return False

def get_user_authentication_status(email: str) -> Dict[str, any]:
    """Get user authentication status including Google Drive connection"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT authentication_method, google_drive_connected, display_name
                FROM user_profiles 
                WHERE gmail_address = ?
            """, (email,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'user_exists': True,
                    'authentication_method': result[0],
                    'google_drive_connected': bool(result[1]),
                    'display_name': result[2]
                }
            else:
                return {
                    'user_exists': False,
                    'authentication_method': None,
                    'google_drive_connected': False,
                    'display_name': None
                }
    except Exception as e:
        logger.error(f"Error getting user authentication status: {e}")
        return {
            'user_exists': False,
            'authentication_method': None,
            'google_drive_connected': False,
            'display_name': None
        }

def update_google_drive_status(email: str, connected: bool) -> bool:
    """Update Google Drive connection status for user"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_profiles 
                SET google_drive_connected = ?, last_login = CURRENT_TIMESTAMP
                WHERE gmail_address = ?
            """, (connected, email))
            
            if cursor.rowcount > 0:
                logger.info(f"✅ Updated Google Drive status for {email}: {connected}")
                return True
            else:
                logger.warning(f"⚠️ No user found to update Google Drive status: {email}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error updating Google Drive status: {e}")
        return False