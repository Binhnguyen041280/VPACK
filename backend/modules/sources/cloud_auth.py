#!/usr/bin/env python3
"""
Cloud Authentication Handler for VTrack
Manages OAuth2 flows, token storage, and session management
Supports Google Drive OAuth2 with extensible design for other providers
"""

import os
import json
import uuid
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import threading
import time
import jwt
from cryptography.fernet import Fernet
import base64
from flask import g

# OAuth2 and Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    logging.warning("Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secret key for JWT - In production, use environment variable
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')

# Encryption key for credentials - Load from persistent file or generate new one
def _load_or_generate_oauth_encryption_key():
    """Load existing OAuth encryption key or generate new one with persistence"""
    try:
        # Define key file path
        keys_dir = str(Path(__file__).parent.parent.parent / 'keys')
        os.makedirs(keys_dir, exist_ok=True)
        key_path = str(Path(keys_dir) / 'oauth_encryption.key')

        if Path(key_path).exists():
            # Load existing key
            with open(key_path, 'rb') as f:
                key = f.read()
            logger.info("✅ Loaded existing OAuth encryption key")
            return key
        else:
            # Generate new key and save
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            # Set secure permissions (owner read/write only)
            os.chmod(key_path, 0o600)
            logger.info("🔑 Generated new persistent OAuth encryption key")
            return key
    except Exception as e:
        logger.error(f"❌ OAuth encryption key initialization error: {e}")
        # Fallback to environment variable or temporary key
        env_key = os.getenv('ENCRYPTION_KEY')
        if env_key:
            return env_key.encode() if isinstance(env_key, str) else env_key
        else:
            logger.warning("⚠️ Using temporary encryption key - credentials won't persist across restarts")
            return Fernet.generate_key()

ENCRYPTION_KEY = _load_or_generate_oauth_encryption_key()

class CloudAuthManager:
    """
    Manages OAuth2 authentication flows for cloud providers
    Handles token storage, refresh, and session management
    """
    
    # OAuth2 scopes for different providers
    PROVIDER_SCOPES = {
        'google_drive': [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ],
        'gmail_only': [
            'openid',
            'email',
            'profile'
        ]
    }
    
    # OAuth2 endpoints
    OAUTH_ENDPOINTS = {
        'google_drive': {
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_secrets_file': 'google_drive_credentials_web.json'
        },
        'gmail_only': {
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_secrets_file': 'gmail_credentials.json'  # Dedicated Gmail credentials
        }
    }
    
    def __init__(self, provider: str = 'google_drive', base_dir: Optional[str] = None):
        """
        Initialize CloudAuthManager
        
        Args:
            provider (str): Cloud provider ('google_drive', etc.)
            base_dir (str): Base directory for credential storage
        """
        self.provider = provider
        self.base_dir = base_dir or str(Path(__file__).parent)
        
        # Authentication state
        self.auth_sessions = {}  # Active auth sessions
        self.credentials_cache = {}  # Cached credentials
        
        # Thread safety
        self.auth_lock = threading.Lock()
        
        # Credential file paths
        self.credentials_dir = str(Path(self.base_dir) / 'credentials')
        self.tokens_dir = str(Path(self.base_dir) / 'tokens')
        
        # Ensure directories exist
        os.makedirs(self.credentials_dir, exist_ok=True)
        os.makedirs(self.tokens_dir, exist_ok=True)
        
        logger.info(f"CloudAuthManager initialized for {provider}")

    def generate_session_token(self, user_email: str, user_info: Dict[str, Any], expires_minutes: int = 30) -> Optional[str]:
        """Generate JWT session token instead of returning raw credentials"""
        try:
            payload = {
                'user_email': user_email,
                'user_name': user_info.get('name', 'Unknown'),
                'photo_url': user_info.get('photo_url'),
                'provider': self.provider,
                'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
                'iat': datetime.utcnow(),
                'iss': 'vtrack-cloud-auth',
                'type': 'session'
            }
            token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
            logger.info(f"✅ Generated session token for: {user_email} (expires in {expires_minutes}min)")
            return token
        except Exception as e:
            logger.error(f"❌ JWT generation error: {e}")
            return None

    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT session token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ Session token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid session token: {e}")
            return None

    def encrypt_credentials(self, credentials_dict: Dict[str, Any]) -> Optional[str]:
        """Encrypt credentials before storage"""
        try:
            fernet = Fernet(ENCRYPTION_KEY)
            credentials_json = json.dumps(credentials_dict).encode()
            encrypted_data = fernet.encrypt(credentials_json)
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"❌ Credential encryption error: {e}")
            return None

    def decrypt_credentials(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """Decrypt stored credentials"""
        try:
            fernet = Fernet(ENCRYPTION_KEY)
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"❌ Credential decryption error: {e}")
            return None

    def initiate_oauth_flow(self, redirect_uri: str = 'http://localhost:8080/oauth/callback') -> Dict[str, Any]:
        """
        Initiate OAuth2 authentication flow
        
        Args:
            redirect_uri (str): OAuth2 redirect URI
            
        Returns:
            dict: OAuth flow information including auth URL
        """
        try:
            logger.info(f"🔐 Initiating OAuth2 flow for {self.provider}")
            
            if self.provider in ['google_drive', 'gmail_only']:
                return self._initiate_google_oauth(redirect_uri)
            else:
                return {
                    'success': False,
                    'message': f"OAuth2 not implemented for {self.provider}"
                }
                
        except Exception as e:
            logger.error(f"❌ OAuth2 initiation failed: {e}")
            return {
                'success': False,
                'message': f"OAuth2 initiation failed: {str(e)}",
                'error': str(e)
            }
    
    def _initiate_google_oauth(self, redirect_uri: str) -> Dict[str, Any]:
        """Initiate Google Drive OAuth2 flow"""
        try:
            # Get client secrets file path
            client_secrets_file = str(Path(self.credentials_dir) / self.OAUTH_ENDPOINTS[self.provider]['client_secrets_file'])
            
            if not Path(client_secrets_file).exists():
                return {
                    'success': False,
                    'message': f"Google credentials file not found: {client_secrets_file}",
                    'setup_required': True
                }
            
            # Create OAuth2 flow
            flow = Flow.from_client_secrets_file(
                client_secrets_file,
                scopes=self.PROVIDER_SCOPES[self.provider],
                redirect_uri=redirect_uri
            )
            
            # Generate state parameter for security
            state = secrets.token_urlsafe(32)
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'  # Force consent to get refresh token
            )
            
            # Store flow in session for later completion
            session_id = str(uuid.uuid4())
            
            with self.auth_lock:
                self.auth_sessions[session_id] = {
                    'flow': flow,
                    'state': state,
                    'provider': self.provider,
                    'created_at': datetime.now().isoformat(),
                    'redirect_uri': redirect_uri,
                    'status': 'pending'
                }
            
            logger.info(f"✅ Google OAuth2 flow created with session: {session_id}")
            
            return {
                'success': True,
                'auth_url': auth_url,
                'session_id': session_id,
                'state': state,
                'provider': self.provider,
                'message': 'OAuth2 flow initiated successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Google OAuth2 initiation error: {e}")
            return {
                'success': False,
                'message': f"Google OAuth2 initiation failed: {str(e)}",
                'error': str(e)
            }

    def complete_oauth_flow(self, session_id: str, authorization_code: str, state: str) -> Dict[str, Any]:
        """🔐 PHASE 1 SECURITY: Complete OAuth2 flow with session tokens instead of raw credentials"""
        try:
            logger.info(f"🔐 Completing OAuth2 flow for session: {session_id}")
            
            # Retrieve and validate session
            with self.auth_lock:
                if session_id not in self.auth_sessions:
                    return {
                        'success': False,
                        'message': 'OAuth session not found or expired',
                        'requires_reauth': True
                    }
                
                session = self.auth_sessions[session_id]
                
                # Enhanced state validation with timing check
                if session['state'] != state:
                    return {
                        'success': False,
                        'message': 'OAuth state mismatch - potential security issue',
                        'security_error': True
                    }
                
                # Check session age (max 1 hour)
                session_created = datetime.fromisoformat(session['created_at'])
                if datetime.now() - session_created > timedelta(hours=1):
                    return {
                        'success': False,
                        'message': 'OAuth session expired',
                        'requires_reauth': True
                    }
                
                flow = session['flow']
            
            # Exchange authorization code for tokens
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Validate credentials
            if not credentials.valid:
                return {
                    'success': False,
                    'message': 'Invalid credentials received from OAuth flow'
                }
            
            # Get user information
            user_info = self._get_user_info(credentials)
            
            # 🔐 PHASE 1: Secure credential storage with encryption
            credential_storage_result = self._store_credentials_securely(credentials, user_info)
            
            if not credential_storage_result['success']:
                return credential_storage_result
            
            # Generate session token instead of returning raw credentials
            session_token = self.generate_session_token(user_info['email'], user_info)
            if not session_token:
                return {
                    'success': False,
                    'message': 'Failed to generate session token',
                    'error': 'token_generation_failed'
                }
            
            # Update session status
            with self.auth_lock:
                if session_id in self.auth_sessions:
                    self.auth_sessions[session_id]['status'] = 'completed'
                    self.auth_sessions[session_id]['completed_at'] = datetime.now().isoformat()
            
            # Audit logging
            self._log_authentication_event(
                event_type='oauth_completed',
                user_email=user_info.get('email', 'Unknown'),
                session_id=session_id,
                success=True
            )
            
            logger.info(f"✅ OAuth2 flow completed securely for: {user_info.get('email', 'Unknown')}")
            
            # 🔐 Return session data instead of raw credentials
            return {
                'success': True,
                'message': 'OAuth2 authentication completed successfully',
                'user_info': user_info,
                'session_token': session_token,  # JWT token only
                'user_email': user_info['email'],
                'provider': self.provider,
                'authenticated_at': datetime.now().isoformat(),
                'security_mode': 'encrypted_storage',
                'token_expires_minutes': 30
                # ❌ REMOVED: 'credentials' field - no longer exposed
            }
            
        except Exception as e:
            logger.error(f"❌ OAuth2 completion error: {e}")
            
            # Audit logging for failures
            self._log_authentication_event(
                event_type='oauth_failed',
                user_email='Unknown',
                session_id=session_id,
                success=False,
                error=str(e)
            )
            
            return {
                'success': False,
                'message': f'OAuth2 completion failed: {str(e)}',
                'error': str(e),
                'security_mode': 'encrypted_storage'
            }
            
    def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """
        Get user information from OAuth2 credentials
        
        Args:
            credentials: OAuth2 credentials
            
        Returns:
            dict: User information
        """
        try:
            if self.provider == 'google_drive':
                return self._get_google_user_info(credentials)
            elif self.provider == 'gmail_only':
                return self._get_gmail_user_info(credentials)
            else:
                return {'email': 'unknown', 'name': 'Unknown User'}
                
        except Exception as e:
            logger.error(f"❌ Error getting user info: {e}")
            return {'email': 'unknown', 'name': 'Unknown User', 'error': str(e)}
    
    def _get_google_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """Get Google user information"""
        try:
            # Build Drive service to get user info
            service = build('drive', 'v3', credentials=credentials)
            about = service.about().get(fields='user,storageQuota').execute()
            
            user = about.get('user', {})
            quota = about.get('storageQuota', {})
            
            return {
                'email': user.get('emailAddress', 'unknown'),
                'name': user.get('displayName', 'Unknown User'),
                'photo_url': user.get('photoLink'),
                'storage_used_gb': int(quota.get('usage', 0)) / (1024**3) if quota.get('usage') else 0,
                'storage_total_gb': int(quota.get('limit', 0)) / (1024**3) if quota.get('limit') else 'Unlimited'
            }
            
        except Exception as e:
            logger.error(f"❌ Google user info error: {e}")
            return {'email': 'unknown', 'name': 'Unknown User', 'error': str(e)}
    
    def _get_gmail_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """Get Gmail user information using OAuth2 userinfo endpoint"""
        try:
            # Use OAuth2 service to get user info with minimal scopes
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                'email': user_info.get('email', 'unknown'),
                'name': user_info.get('name', 'Unknown User'),
                'photo_url': user_info.get('picture'),
                'gmail_verified': user_info.get('verified_email', False),
                'authentication_method': 'gmail_only'
            }
            
        except Exception as e:
            logger.error(f"❌ Gmail user info error: {e}")
            return {'email': 'unknown', 'name': 'Unknown User', 'error': str(e), 'authentication_method': 'gmail_only'}
    
    def _store_credentials_securely(self, credentials: Credentials, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """🔐 PHASE 1 SECURITY: Securely store OAuth2 credentials with AES-256 encryption"""
        try:
            # Prepare credential data
            credential_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': list(credentials.scopes) if credentials.scopes else [],
                'provider': self.provider,
                'user_info': user_info,
                'created_at': datetime.now().isoformat(),
                'expires_at': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            # 🔐 Encrypt credentials
            encrypted_credentials = self.encrypt_credentials(credential_data)
            if not encrypted_credentials:
                return {
                    'success': False,
                    'message': 'Failed to encrypt credentials',
                    'error': 'encryption_failed'
                }
            
            # Generate secure filename
            user_email = user_info.get('email', 'unknown')
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            token_filename = f"{self.provider}_{email_hash}.json"
            token_filepath = str(Path(self.tokens_dir) / token_filename)
            
            # Store encrypted credentials
            encrypted_storage = {
                'encrypted_data': encrypted_credentials,
                'user_email': user_email,  # Keep email unencrypted for lookup
                'created_at': datetime.now().isoformat(),
                'encryption_version': '1.0',
                'provider': self.provider
            }
            
            with open(token_filepath, 'w') as f:
                json.dump(encrypted_storage, f, indent=2)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(token_filepath, 0o600)
            
            # Cache credentials for immediate use
            with self.auth_lock:
                self.credentials_cache[user_email] = {
                    'credentials': credentials,
                    'user_info': user_info,
                    'filepath': token_filepath,
                    'cached_at': datetime.now()
                }
            
            logger.info(f"✅ Encrypted credentials stored for: {user_email}")
            
            return {
                'success': True,
                'message': 'Credentials stored securely',
                'filepath': token_filepath,
                'encryption_used': 'AES-256'
            }
            
        except Exception as e:
            logger.error(f"❌ Secure credential storage error: {e}")
            return {
                'success': False,
                'message': f'Credential storage failed: {str(e)}',
                'error': str(e)
            }
        
    def load_stored_credentials(self, user_email: Optional[str] = None) -> Optional[Credentials]:
        """
        Load stored credentials for user
        
        Args:
            user_email (str): User email (if None, loads first available)
            
        Returns:
            Credentials: OAuth2 credentials if found
        """
        try:
            # Check cache first
            if user_email and user_email in self.credentials_cache:
                cached = self.credentials_cache[user_email]
                if (datetime.now() - cached['cached_at']).seconds < 3600:  # 1 hour cache
                    logger.info(f"✅ Using cached credentials for: {user_email}")
                    return cached['credentials']
            
            # Load from file
            token_files = []
            for filename in os.listdir(self.tokens_dir):
                if filename.startswith(f"{self.provider}_") and filename.endswith('.json'):
                    token_files.append(filename)
            
            if not token_files:
                logger.info("📭 No stored credentials found")
                return None
            
            # If specific user requested, find their file
            if user_email:
                email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
                target_filename = f"{self.provider}_{email_hash}.json"
                if target_filename in token_files:
                    token_files = [target_filename]
                else:
                    logger.warning(f"⚠️ No credentials found for: {user_email}")
                    return None
            
            # Load the first (or specified) credential file
            token_filepath = str(Path(self.tokens_dir) / token_files[0])
            
            with open(token_filepath, 'r') as f:
                credential_data = json.load(f)
            
            # Check if this is encrypted storage
            if 'encrypted_data' in credential_data:
                # New encrypted format
                decrypted_data = self.decrypt_credentials(credential_data['encrypted_data'])
                if not decrypted_data:
                    logger.error(f"❌ Failed to decrypt credentials")
                    return None
                credential_data = decrypted_data
            
            # Reconstruct credentials
            credentials = Credentials(
                token=credential_data['token'],
                refresh_token=credential_data['refresh_token'],
                token_uri=credential_data['token_uri'],
                client_id=credential_data['client_id'],
                client_secret=credential_data['client_secret'],
                scopes=credential_data['scopes']
            )
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                logger.info("🔄 Refreshing expired credentials...")
                credentials.refresh(Request())
                
                # Update stored credentials
                credential_data['token'] = credentials.token
                credential_data['expires_at'] = credentials.expiry.isoformat() if credentials.expiry else None
                
                # Re-encrypt and save
                encrypted_credentials = self.encrypt_credentials(credential_data)
                if encrypted_credentials:
                    encrypted_storage = {
                        'encrypted_data': encrypted_credentials,
                        'user_email': credential_data['user_info']['email'],
                        'created_at': datetime.now().isoformat(),
                        'encryption_version': '1.0',
                        'provider': self.provider
                    }
                    with open(token_filepath, 'w') as f:
                        json.dump(encrypted_storage, f, indent=2)
                    os.chmod(token_filepath, 0o600)
            
            # Cache credentials
            stored_user_email = credential_data['user_info']['email']
            with self.auth_lock:
                self.credentials_cache[stored_user_email] = {
                    'credentials': credentials,
                    'user_info': credential_data['user_info'],
                    'filepath': token_filepath,
                    'cached_at': datetime.now()
                }
            
            logger.info(f"✅ Loaded credentials for: {stored_user_email}")
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error loading credentials: {e}")
            return None
    
    def get_authentication_status(self, session_token: Optional[str] = None) -> Dict[str, Any]:
        """🔐 PHASE 1 SECURITY: Get authentication status using session tokens"""
        try:
            if not session_token:
                return {
                    'authenticated': False,
                    'provider': self.provider,
                    'message': 'No session token provided',
                    'security_mode': 'session_based',
                    'last_check': datetime.now().isoformat()
                }
            
            # Verify session token
            token_payload = self.verify_session_token(session_token)
            if not token_payload:
                return {
                    'authenticated': False,
                    'provider': self.provider,
                    'message': 'Invalid or expired session token',
                    'requires_reauth': True,
                    'security_mode': 'session_based',
                    'last_check': datetime.now().isoformat()
                }
            
            user_email = token_payload.get('user_email')
            if not user_email:
                return {
                    'authenticated': False,
                    'provider': self.provider,
                    'message': 'Invalid token payload',
                    'security_mode': 'session_based',
                    'last_check': datetime.now().isoformat()
                }
            
            # Check if encrypted credentials exist
            encrypted_credentials_exist = self._check_encrypted_credentials_exist(user_email)
            
            if encrypted_credentials_exist:
                return {
                    'authenticated': True,
                    'provider': self.provider,
                    'user_email': user_email,
                    'user_name': token_payload.get('user_name', 'Unknown'),
                    'photo_url': token_payload.get('photo_url'),
                    'expires_at': token_payload.get('exp'),
                    'security_mode': 'session_based',
                    'credentials_encrypted': True,
                    'last_check': datetime.now().isoformat()
                }
            else:
                return {
                    'authenticated': False,
                    'provider': self.provider,
                    'message': 'Stored credentials not found',
                    'requires_reauth': True,
                    'security_mode': 'session_based',
                    'last_check': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Authentication status check error: {e}")
            return {
                'authenticated': False,
                'provider': self.provider,
                'error': str(e),
                'security_mode': 'session_based',
                'last_check': datetime.now().isoformat()
            }

    def _check_encrypted_credentials_exist(self, user_email: str) -> bool:
        """Check if encrypted credentials exist for user"""
        try:
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            token_filename = f"{self.provider}_{email_hash}.json"
            token_filepath = str(Path(self.tokens_dir) / token_filename)
            return Path(token_filepath).exists()
        except Exception:
            return False

    def load_credentials_from_session(self, session_token: str) -> Optional[Credentials]:
        """🔐 PHASE 1: Load encrypted credentials using session token"""
        try:
            # Verify session token
            token_payload = self.verify_session_token(session_token)
            if not token_payload:
                logger.warning("⚠️ Invalid session token for credential loading")
                return None
            
            user_email = token_payload.get('user_email')
            if not user_email:
                logger.warning("⚠️ No user email in session token")
                return None
            
            return self._load_encrypted_credentials(user_email)
            
        except Exception as e:
            logger.error(f"❌ Session-based credential loading error: {e}")
            return None

    def _load_encrypted_credentials(self, user_email: str) -> Optional[Credentials]:
        """Load and decrypt stored credentials for user"""
        try:
            # Check cache first
            if user_email in self.credentials_cache:
                cached = self.credentials_cache[user_email]
                if (datetime.now() - cached['cached_at']).seconds < 3600:  # 1 hour cache
                    logger.info(f"✅ Using cached credentials for: {user_email}")
                    return cached['credentials']
            
            # Load from encrypted storage
            email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
            token_filename = f"{self.provider}_{email_hash}.json"
            token_filepath = str(Path(self.tokens_dir) / token_filename)
            
            if not Path(token_filepath).exists():
                logger.warning(f"⚠️ No encrypted credentials found for: {user_email}")
                return None
            
            # Load and decrypt
            with open(token_filepath, 'r') as f:
                encrypted_storage = json.load(f)
            
            credential_data = self.decrypt_credentials(encrypted_storage['encrypted_data'])
            if not credential_data:
                logger.error(f"❌ Failed to decrypt credentials for: {user_email}")
                return None
            
            # Reconstruct credentials
            credentials = Credentials(
                token=credential_data['token'],
                refresh_token=credential_data['refresh_token'],
                token_uri=credential_data['token_uri'],
                client_id=credential_data['client_id'],
                client_secret=credential_data['client_secret'],
                scopes=credential_data['scopes']
            )
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                logger.info("🔄 Refreshing expired credentials...")
                credentials.refresh(Request())
                
                # Update stored credentials
                credential_data['token'] = credentials.token
                credential_data['expires_at'] = credentials.expiry.isoformat() if credentials.expiry else None
                
                encrypted_updated = self.encrypt_credentials(credential_data)
                if encrypted_updated:
                    encrypted_storage['encrypted_data'] = encrypted_updated
                    with open(token_filepath, 'w') as f:
                        json.dump(encrypted_storage, f, indent=2)
                    os.chmod(token_filepath, 0o600)
            
            # Update cache
            with self.auth_lock:
                self.credentials_cache[user_email] = {
                    'credentials': credentials,
                    'user_info': credential_data['user_info'],
                    'filepath': token_filepath,
                    'cached_at': datetime.now()
                }
            
            logger.info(f"✅ Loaded encrypted credentials for: {user_email}")
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error loading encrypted credentials: {e}")
            return None
    
    def _log_authentication_event(self, event_type: str, user_email: str, session_id: str = None, 
                                 success: bool = True, error: str = None):
        """🔐 PHASE 1: Audit logging for authentication events"""
        try:
            # Get IP address safely
            try:
                ip_address = g.remote_addr if hasattr(g, 'remote_addr') else 'unknown'
            except RuntimeError:
                ip_address = 'unknown'  # Outside Flask request context
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'user_email': user_email,
                'session_id': session_id,
                'provider': self.provider,
                'success': success,
                'error': error,
                'ip_address': ip_address
            }
            
            # Write to audit log file
            audit_log_path = str(Path(self.base_dir) / 'audit_logs')
            os.makedirs(audit_log_path, exist_ok=True)
            
            log_file = str(Path(audit_log_path) / f'auth_audit_{datetime.now().strftime("%Y%m")}.log')
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Set restrictive permissions on audit log
            os.chmod(log_file, 0o600)
            
            logger.info(f"📝 Audit log: {event_type} for {user_email} - {'Success' if success else 'Failed'}")
            
        except Exception as e:
            logger.error(f"❌ Audit logging error: {e}")
            
    def revoke_credentials(self, session_token: str = None, user_email: str = None) -> Dict[str, Any]:
        """🔐 PHASE 1 SECURITY: Revoke stored credentials with audit logging"""
        try:
            revoked_count = 0
            revoked_users = []
            
            if session_token:
                # Revoke based on session token
                token_payload = self.verify_session_token(session_token)
                if token_payload:
                    user_email = token_payload.get('user_email')
                else:
                    return {
                        'success': False,
                        'message': 'Invalid session token for revocation',
                        'security_mode': 'session_based'
                    }
            
            if user_email:
                # Revoke specific user credentials
                email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
                token_filename = f"{self.provider}_{email_hash}.json"
                token_filepath = str(Path(self.tokens_dir) / token_filename)
                
                if Path(token_filepath).exists():
                    os.remove(token_filepath)
                    revoked_count = 1
                    revoked_users.append(user_email)
                    
                    # Remove from cache
                    with self.auth_lock:
                        if user_email in self.credentials_cache:
                            del self.credentials_cache[user_email]
                    
                    # Audit logging
                    self._log_authentication_event(
                        event_type='credentials_revoked',
                        user_email=user_email,
                        success=True
                    )
            else:
                # Revoke all credentials for provider
                for filename in os.listdir(self.tokens_dir):
                    if filename.startswith(f"{self.provider}_") and filename.endswith('.json'):
                        filepath = str(Path(self.tokens_dir) / filename)
                        
                        # Try to get user email for audit log
                        try:
                            with open(filepath, 'r') as f:
                                storage = json.load(f)
                                revoked_user_email = storage.get('user_email', 'unknown')
                                revoked_users.append(revoked_user_email)
                        except:
                            revoked_users.append('unknown')
                        
                        os.remove(filepath)
                        revoked_count += 1
                
                # Clear cache
                with self.auth_lock:
                    self.credentials_cache.clear()
                
                # Audit logging for bulk revocation
                for revoked_user in revoked_users:
                    self._log_authentication_event(
                        event_type='credentials_revoked_bulk',
                        user_email=revoked_user,
                        success=True
                    )
            
            logger.info(f"🔌 Revoked {revoked_count} credential(s) for {self.provider}")
            
            return {
                'success': True,
                'message': f"Revoked {revoked_count} credential(s)",
                'revoked_count': revoked_count,
                'revoked_users': revoked_users,
                'provider': self.provider,
                'security_mode': 'session_based'
            }
            
        except Exception as e:
            logger.error(f"❌ Credential revocation error: {e}")
            return {
                'success': False,
                'message': f"Credential revocation failed: {str(e)}",
                'error': str(e),
                'security_mode': 'session_based'
            }
    
    def cleanup_expired_sessions(self, max_age_hours: int = 1):
        """
        Clean up expired OAuth sessions
        
        Args:
            max_age_hours (int): Maximum session age in hours
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            expired_sessions = []
            
            with self.auth_lock:
                for session_id, session_data in list(self.auth_sessions.items()):
                    created_at = datetime.fromisoformat(session_data['created_at'])
                    if created_at < cutoff_time:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    del self.auth_sessions[session_id]
            
            if expired_sessions:
                logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired OAuth sessions")
                
        except Exception as e:
            logger.error(f"❌ Session cleanup error: {e}")


def test_cloud_auth():
    """Test function for CloudAuthManager functionality"""
    print("🔧 Testing CloudAuthManager...")
    
    try:
        # Initialize CloudAuthManager
        print("\n1. Initializing CloudAuthManager...")
        auth_manager = CloudAuthManager('google_drive')
        print("✅ CloudAuthManager initialized")
        
        # Check authentication status
        print("\n2. Checking authentication status...")
        auth_status = auth_manager.get_authentication_status()
        print(f"✅ Authenticated: {auth_status['authenticated']}")
        
        if auth_status['authenticated']:
            print(f"   User: {auth_status.get('user_email', 'Unknown')}")
        else:
            print("   No existing credentials found")
        
        # Load stored credentials (if any)
        print("\n3. Loading stored credentials...")
        credentials = auth_manager.load_stored_credentials()
        
        if credentials:
            print(f"✅ Credentials loaded successfully")
            print(f"   Valid: {credentials.valid}")
            print(f"   Scopes: {list(credentials.scopes) if credentials.scopes else 'None'}")
        else:
            print("📭 No stored credentials found")
        
        print("\n🎉 CloudAuthManager test completed!")
        
    except Exception as e:
        print(f"❌ CloudAuthManager test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_cloud_auth()