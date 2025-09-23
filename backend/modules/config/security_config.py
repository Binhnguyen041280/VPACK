from datetime import datetime, timedelta
import os
import json
import logging
import jwt
from cryptography.fernet import Fernet
import base64
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration and utilities"""
    
    def __init__(self):
        # Initialize encryption keys
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', self._generate_jwt_secret())
        # Use persistent OAuth encryption key from cloud_auth module
        try:
            from ..sources.cloud_auth import ENCRYPTION_KEY
            self.encryption_key = ENCRYPTION_KEY
            logger.info("✅ Using persistent OAuth encryption key from cloud_auth module")
        except ImportError:
            # Fallback to original behavior
            self.encryption_key = os.getenv('ENCRYPTION_KEY', self._generate_encryption_key())
            logger.warning("⚠️ Fallback to non-persistent encryption key")

        self.cipher_suite = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        
        # V_TRACK BACKGROUND SERVICE: Long-running authentication for "set it and forget it" model
        # User behavior: Setup once → Process videos automatically, no daily interaction
        
        # Primary session duration (JWT token) - Background service mode
        self.session_duration = timedelta(days=90)  # 3 months for background service
        
        # Refresh token configuration - Long-term authentication
        self.refresh_token_duration = timedelta(days=365)  # 1 year refresh token
        
        # Aggressive auto-refresh to prevent interruption
        self.refresh_threshold = timedelta(days=7)  # Refresh when 7 days remaining
        self.refresh_retry_interval = timedelta(hours=1)  # Retry every hour if fail
        self.max_refresh_retries = 168  # Retry for 1 week (168 hours)
        
        # Background service flags
        self.background_service_mode = True  # Enable background service features
        self.silent_operation = True  # No user popups/interruptions
        self.emergency_grace_period = timedelta(days=7)  # Grace period if refresh fails
        
        logger.info("V_track Background Service authentication initialized")
        logger.info(f"JWT Session Duration: {self.session_duration}")
        logger.info(f"Refresh Token Duration: {self.refresh_token_duration}")
        logger.info(f"Auto-refresh Threshold: {self.refresh_threshold}")    
    
    def _generate_jwt_secret(self) -> str:
        """Generate JWT secret key if not provided"""
        import secrets
        secret = secrets.token_urlsafe(32)
        logger.warning("JWT_SECRET_KEY not found in environment, generated temporary key")
        return secret
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key if not provided"""
        key = Fernet.generate_key()
        logger.warning("ENCRYPTION_KEY not found in environment, generated temporary key")
        return key
    
    def encrypt_credentials(self, credentials_dict: Dict) -> str:
        """Encrypt OAuth credentials"""
        try:
            credentials_json = json.dumps(credentials_dict)
            encrypted = self.cipher_suite.encrypt(credentials_json.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise
    
    def decrypt_credentials(self, encrypted_credentials: str) -> Dict:
        """Decrypt OAuth credentials"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_credentials.encode())
            decrypted = self.cipher_suite.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise
    
    def generate_session_token(self, user_email: str, provider: str = 'google_drive') -> str:
        """Generate JWT session token"""
        payload = {
            'user_email': user_email,
            'provider': provider,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + self.session_duration,
            'iss': 'vtrack-background-service',  # Match cloud_endpoints.py issuer
            'type': 'session'  # Add type field for consistency
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    def generate_token_pair(self, user_email: str, provider: str = 'google_drive') -> dict:
        """Generate access token + refresh token pair for background service"""
        now = datetime.utcnow()
        
        # Access token (for API calls)
        access_payload = {
            'user_email': user_email,
            'provider': provider,
            'type': 'access',
            'iat': now,
            'exp': now + self.session_duration,
            'background_service': True
        }
        
        # Refresh token (for renewing access token)
        refresh_payload = {
            'user_email': user_email,
            'provider': provider,
            'type': 'refresh', 
            'iat': now,
            'exp': now + self.refresh_token_duration,
            'background_service': True
        }
        
        return {
            'access_token': jwt.encode(access_payload, self.jwt_secret, algorithm='HS256'),
            'refresh_token': jwt.encode(refresh_payload, self.jwt_secret, algorithm='HS256'),
            'expires_in': int(self.session_duration.total_seconds()),
            'refresh_expires_in': int(self.refresh_token_duration.total_seconds()),
            'token_type': 'Bearer'
        }
    
    def should_refresh_token(self, token: str) -> bool:
        """Check if token should be refreshed (when 7 days remaining)"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            exp_time = datetime.utcfromtimestamp(payload['exp'])
            time_left = exp_time - datetime.utcnow()
            
            # Refresh aggressively when 7 days left (not waiting until expiry)
            return time_left < self.refresh_threshold
        except jwt.ExpiredSignatureError:
            return True  # Expired token, needs refresh
        except jwt.InvalidTokenError:
            return True  # Invalid token, needs refresh
    
    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=['HS256'])
            
            if payload.get('type') != 'refresh':
                logger.warning("Invalid token type for refresh")
                return None
                
            user_email = payload['user_email']
            provider = payload.get('provider', 'google_drive')
            
            # Generate new token pair
            new_tokens = self.generate_token_pair(user_email, provider)
            logger.info(f"Refreshed tokens for user: {user_email}")
            return new_tokens
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expired - require re-authentication")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid refresh token")
            return None
    
    def get_token_time_remaining(self, token: str) -> Optional[timedelta]:
        """Get time remaining until token expiry"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            exp_time = datetime.utcfromtimestamp(payload['exp'])
            time_left = exp_time - datetime.utcnow()
            return time_left if time_left.total_seconds() > 0 else timedelta(0)
        except:
            return None
    
    def validate_session_token(self, token: str) -> Optional[Dict]:
        """Validate JWT session token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {e}")
            return None