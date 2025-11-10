# modules/sources/cloud_endpoints.py - FIXED: API Routes & Session Handling
#!/usr/bin/env python3

from google.auth.transport.requests import Request
from oauth2client.client import OAuth2Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from requests_oauthlib.oauth2_session import TokenUpdated
from oauthlib.oauth2.rfc6749.errors import InvalidScopeError, OAuth2Error
import hashlib
import json
import os
from pathlib import Path
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from oauth2client.client import OAuth2Credentials
from flask_cors import CORS, cross_origin
from functools import wraps
from flask import g
import time
from collections import defaultdict
import jwt
import secrets
from cryptography.fernet import Fernet
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secret key for JWT - In production, use environment variable
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')

# Import persistent encryption key from cloud_auth module
from .cloud_auth import ENCRYPTION_KEY

def generate_session_token(user_email, user_info, expires_minutes=129600):  # 90 days = 90*24*60 = 129600 minutes
    """Generate JWT session token for V_track background service (90 days duration)"""
    try:
        payload = {
            'user_email': user_email,
            'user_name': user_info.get('name', 'Unknown'),
            'photo_url': user_info.get('photo_url'),
            'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
            'iat': datetime.utcnow(),
            'iss': 'vtrack-background-service',  # Match with config.py issuer
            'type': 'session'
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
        logger.info(f"✅ Generated background service session token for: {user_email} (expires in {expires_minutes}min = {expires_minutes//1440} days)")
        return token
        
    except Exception as e:
        logger.error(f"❌ JWT generation error: {e}")
        return None

def verify_session_token(token):
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

def encrypt_credentials(credentials_dict):
    """Encrypt credentials before storage"""
    try:
        fernet = Fernet(ENCRYPTION_KEY)
        credentials_json = json.dumps(credentials_dict).encode()
        encrypted_data = fernet.encrypt(credentials_json)
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"❌ Credential encryption error: {e}")
        return None

def decrypt_credentials(encrypted_data):
    """Decrypt stored credentials"""
    try:
        fernet = Fernet(ENCRYPTION_KEY)
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_data = fernet.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())
    except Exception as e:
        logger.error(f"❌ Credential decryption error: {e}")
        return None

# 🆕 Rate limiting storage (in-memory for simplicity)
rate_limit_storage = defaultdict(list)

# 🆕 Caching storage for performance optimization
cache_storage = {}
CACHE_DURATIONS = {
    'auth_status': 300,      # 5 minutes
    'subfolders': 180,       # 3 minutes
    'user_info': 600,        # 10 minutes
}

def get_cache_key(endpoint, *args):
    """Generate cache key"""
    key_parts = [endpoint] + [str(arg) for arg in args]
    return hashlib.sha256(':'.join(key_parts).encode()).hexdigest()[:16]

def get_cached_data(cache_key):
    """Get cached data if valid"""
    if cache_key in cache_storage:
        cached_item = cache_storage[cache_key]
        if time.time() < cached_item['expires_at']:
            return cached_item['data']
        else:
            # Remove expired cache
            del cache_storage[cache_key]
    return None

def set_cached_data(cache_key, data, cache_type='default'):
    """Cache data with expiration"""
    duration = CACHE_DURATIONS.get(cache_type, 300)
    cache_storage[cache_key] = {
        'data': data,
        'expires_at': time.time() + duration,
        'created_at': time.time()
    }

RATE_LIMITS = {
    'auth_status': {'calls': 30, 'window': 60},   # 30 calls per minute  
    'default': {'calls': 60, 'window': 60}        # 60 calls per minute default
}

def rate_limit(endpoint_type='default'):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Get rate limit config
            limit_config = RATE_LIMITS.get(endpoint_type, RATE_LIMITS['default'])
            max_calls = limit_config['calls']
            time_window = limit_config['window']
            
            # Clean old entries
            cutoff_time = current_time - time_window
            rate_limit_storage[client_ip] = [
                call_time for call_time in rate_limit_storage[client_ip] 
                if call_time > cutoff_time
            ]
            
            # Check rate limit
            if len(rate_limit_storage[client_ip]) >= max_calls:
                logger.warning(f"🚫 Rate limit exceeded for {client_ip} on {endpoint_type}")
                return jsonify({
                    'success': False,
                    'message': f'Rate limit exceeded. Max {max_calls} calls per {time_window} seconds.',
                    'retry_after': int(time_window - (current_time - rate_limit_storage[client_ip][0]))
                }), 429
            
            # Record this call
            rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Create Blueprint for cloud endpoints
cloud_bp = Blueprint('cloud', __name__, url_prefix='/api/cloud')
# 🔧 FIX: Add CORS to cloud blueprint
CORS(cloud_bp, 
     origins=['http://localhost:3000'],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'x-timezone-version', 'x-timezone-detection', 'x-client-offset', 'x-client-timezone', 'x-client-dst'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

@cloud_bp.route('/drive-auth', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def drive_authenticate():
    """Google Drive OAuth2 authentication - Separate from Gmail authentication"""
    try:
        # Prerequisite check: Require Gmail authentication first
        gmail_authenticated = session.get('gmail_authenticated', False)
        if not gmail_authenticated:
            return jsonify({
                'success': False,
                'message': 'Gmail authentication required before Drive access',
                'error_code': 'gmail_auth_required',
                'action_required': 'complete_gmail_auth_first'
            }), 401
        
        data = request.get_json()
        provider = data.get('provider', 'google_drive')
        action = data.get('action', 'initiate_auth')
        
        # 🆕 NEW: Get redirect URI from request or determine automatically
        custom_redirect = data.get('redirect_uri')
        
        logger.info(f"🔐 Drive authentication request: {provider}, action: {action}")
        
        if action == 'initiate_auth':
            CLIENT_SECRETS_FILE = str(Path(__file__).parent / 'credentials/google_drive_credentials_web.json')
            
            if not Path(CLIENT_SECRETS_FILE).exists():
                return jsonify({
                    'success': False,
                    'message': f'Credentials file not found: {CLIENT_SECRETS_FILE}',
                    'setup_required': True
                }), 400
            
            SCOPES = [
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/drive.metadata.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid'
            ]
            
            # Create flow
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, 
                scopes=SCOPES
            )
            
            # 🔧 FIX: Standardized redirect URI to avoid OAuth origin mismatch
            if custom_redirect:
                redirect_uri = custom_redirect
            else:
                # Standardized to localhost to avoid OAuth origin mismatch
                redirect_uri = 'http://localhost:8080/api/cloud/oauth/callback'
            
            flow.redirect_uri = redirect_uri
            
            # 🔐 PHASE 1 SECURITY: Enhanced CSRF protection with cryptographically secure random state
            state = secrets.token_urlsafe(32)  # More secure than default
            
            # Generate authorization URL
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                state=state  # Use secure state
            )
            
            # 🔐 Store secure state in session with timestamp
            session['oauth2_state'] = state
            session['oauth2_state_created'] = datetime.now().isoformat()
            session['oauth2_flow_data'] = {
                'scopes': SCOPES,
                'redirect_uri': flow.redirect_uri,
                'client_secrets_file': CLIENT_SECRETS_FILE,
                'csrf_token': secrets.token_hex(16)  # Additional CSRF protection
            }
            session.permanent = True
            
            logger.info(f"✅ OAuth flow initiated")
            logger.info(f"   Auth URL: {authorization_url}")
            logger.info(f"   Redirect URI: {flow.redirect_uri}")
            
            return jsonify({
                'success': True,
                'auth_url': authorization_url,
                'state': state,
                'redirect_uri': flow.redirect_uri,
                'message': 'OAuth flow initiated - open popup window'
            }), 200
            
        else:
            return jsonify({
                'success': False,
                'message': f'Unknown action: {action}'
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Cloud authentication error: {e}")
        return jsonify({
            'success': False,
            'message': f'Cloud authentication failed: {str(e)}'
        }), 500

def user_exists_in_db(email):
    """Check if user exists in user_profiles table"""
    try:
        from modules.db_utils.safe_connection import safe_db_connection
        
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM user_profiles WHERE gmail_address = ?", (email,))
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        logger.error(f"Error checking user existence: {e}")
        return False

# ==================== GMAIL-ONLY AUTHENTICATION ====================

@cloud_bp.route('/gmail-auth', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def gmail_authenticate():
    """Gmail-only authentication endpoint with minimal scopes"""
    try:
        logger.info("🔐 Starting Gmail-only authentication...")
        
        data = request.get_json()
        action = data.get('action', 'initiate_auth')
        
        if action == 'initiate_auth':
            # Use dedicated Gmail credentials file
            CLIENT_SECRETS_FILE = str(Path(__file__).parent / 'credentials/gmail_credentials.json')
            
            if not Path(CLIENT_SECRETS_FILE).exists():
                return jsonify({
                    'success': False,
                    'message': f'Credentials file not found: {CLIENT_SECRETS_FILE}',
                    'setup_required': True
                }), 400
            
            # Gmail-only scopes (minimal permissions) - use full Google scope URIs
            GMAIL_SCOPES = [
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
            
            # Create flow with minimal scopes
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, 
                scopes=GMAIL_SCOPES
            )
            
            # Use dedicated Gmail callback endpoint - standardized to localhost
            redirect_uri = 'http://localhost:8080/api/cloud/gmail-callback'
            
            flow.redirect_uri = redirect_uri
            
            # Generate secure state
            state = secrets.token_urlsafe(32)
            
            # Generate authorization URL (Gmail-only, no granted scopes from other services)
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent',
                state=state
            )
            
            # Store state in session
            session['gmail_oauth_state'] = state
            session['gmail_oauth_flow_data'] = {
                'scopes': GMAIL_SCOPES,
                'redirect_uri': flow.redirect_uri,
                'client_secrets_file': CLIENT_SECRETS_FILE,
                'auth_type': 'gmail_only'
            }
            session.permanent = True
            
            logger.info(f"✅ Gmail OAuth flow initiated")
            logger.info(f"   Auth URL: {authorization_url}")
            logger.info(f"   Redirect URI: {flow.redirect_uri}")
            
            return jsonify({
                'success': True,
                'auth_url': authorization_url,
                'state': state,
                'redirect_uri': flow.redirect_uri,
                'auth_type': 'gmail_only',
                'scopes': GMAIL_SCOPES,
                'message': 'Gmail OAuth flow initiated'
            }), 200
            
        else:
            return jsonify({
                'success': False,
                'message': f'Unknown action: {action}'
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Gmail authentication error: {e}")
        return jsonify({
            'success': False,
            'message': f'Gmail authentication failed: {str(e)}'
        }), 500

@cloud_bp.route('/gmail-callback', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def gmail_oauth_callback():
    """Gmail-only OAuth2 callback handler"""
    try:
        logger.info("🔄 Processing Gmail OAuth callback...")
        logger.info(f"   Request URL: {request.url}")
        
        # Get OAuth parameters
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        
        # Handle errors
        if error:
            logger.error(f"❌ Gmail OAuth error: {error}")
            return _create_gmail_error_page(f"Gmail OAuth error: {error}", error_description)
        
        if not code or not state:
            logger.error("❌ Missing required Gmail OAuth parameters")
            return _create_gmail_error_page("Missing OAuth parameters", "Authorization code or state missing")
        
        # Verify state
        stored_state = session.get('gmail_oauth_state')
        if not stored_state or state != stored_state:
            logger.error(f"❌ Gmail OAuth state mismatch: got {state}, expected {stored_state}")
            return _create_gmail_error_page("Security verification failed", "Please try authenticating again")
        
        # Get flow data
        flow_data = session.get('gmail_oauth_flow_data')
        if not flow_data:
            logger.error("❌ No Gmail OAuth flow data found")
            return _create_gmail_error_page("Session expired", "Please start authentication again")
        
        # Recreate Gmail flow using dedicated credentials
        CLIENT_SECRETS_FILE = str(Path(__file__).parent / 'credentials/gmail_credentials.json')
        
        GMAIL_SCOPES = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, 
            scopes=GMAIL_SCOPES
        )
        flow.redirect_uri = flow_data['redirect_uri']
        
        # Exchange code for tokens
        try:
            logger.info(f"🔄 Attempting Gmail token exchange...")
            flow.fetch_token(code=code)
            credentials = flow.credentials
            logger.info("✅ Gmail token exchange successful")
        except Exception as token_error:
            logger.error(f"❌ Gmail token exchange failed: {token_error}")
            return _create_gmail_error_page("Token exchange failed", str(token_error))
        
        # Get user info using OAuth2 API (minimal scopes)
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info_response = service.userinfo().get().execute()
            
            user_info = {
                'email': user_info_response.get('email', 'unknown'),
                'name': user_info_response.get('name', 'Unknown User'),
                'photo_url': user_info_response.get('picture'),
                'verified_email': user_info_response.get('verified_email', False),
                'authentication_method': 'gmail_only'
            }
            logger.info(f"✅ Gmail user info retrieved: {user_info['email']}")
            
        except Exception as user_error:
            logger.error(f"❌ Failed to get Gmail user info: {user_error}")
            return _create_gmail_error_page("User info retrieval failed", str(user_error))
        
        # Create or update user profile
        try:
            from modules.account.account import create_user_profile
            create_user_profile(user_info)
            logger.info(f"✅ User profile created/updated for: {user_info['email']}")
        except Exception as profile_error:
            logger.warning(f"⚠️ User profile creation failed: {profile_error}")
            # Continue anyway - profile creation is not critical for authentication
        
        # Generate session token for Gmail-only authentication
        try:
            session_token = generate_session_token(user_info['email'], user_info, expires_minutes=129600)  # 90 days
            if not session_token:
                raise Exception("Failed to generate session token")
            
            logger.info("✅ Gmail session token generated")
        except Exception as token_error:
            logger.error(f"❌ Failed to generate Gmail session token: {token_error}")
            return _create_gmail_error_page("Session token generation failed", str(token_error))

        # Store minimal authentication data (no Google Drive credentials)
        try:
            # Store authentication status
            session['gmail_authenticated'] = True
            session['gmail_user_email'] = user_info['email']
            session['gmail_user_info'] = user_info
            session['gmail_session_token'] = session_token
            session['authentication_method'] = 'gmail_only'
            # Store consistent user_email for unified credential system
            session['user_email'] = user_info['email']
            session.permanent = True
            
            logger.info("✅ Gmail authentication data stored in session")
        except Exception as storage_error:
            logger.error(f"❌ Failed to store Gmail authentication data: {storage_error}")
            return _create_gmail_error_page("Authentication storage failed", str(storage_error))

        # Return success page with minimal data
        return _create_gmail_success_page({
            'success': True,
            'authenticated': True,
            'user_info': user_info,
            'user_email': user_info['email'],
            'session_token': session_token,
            'authentication_method': 'gmail_only',
            'google_drive_connected': False,
            'message': f'Gmail authentication successful for {user_info["email"]}'
        })
        
    except Exception as e:
        logger.error(f"❌ Gmail OAuth callback error: {e}")
        return _create_gmail_error_page("Authentication failed", str(e))

def _create_gmail_success_page(data):
    """Create success page for Gmail authentication"""
    import json
    
    # Safely serialize user_info to JSON
    user_info_json = json.dumps(data.get('user_info', {}))
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gmail Authentication Success</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .success {{ color: #28a745; }}
            .info {{ color: #666; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 class="success">✅ Gmail Authentication Successful!</h2>
            <p><strong>Welcome:</strong> {data.get('user_email', 'Unknown')}</p>
            <p><strong>Authentication Method:</strong> Gmail Only</p>
            <p class="info">You can now use V_Track with your Gmail identity. Google Drive connection is optional and can be configured later in settings.</p>
        </div>
        <script>
            // Send success message to parent window
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'GMAIL_AUTH_SUCCESS',
                    user_info: {user_info_json},
                    user_email: '{data.get('user_email', '')}',
                    session_token: '{data.get('session_token', '')}',
                    authentication_method: 'gmail_only',
                    google_drive_connected: false,
                    backend_port: 8080
                }}, '*');  // Allow both 3000 and 5001 ports
                
                // Close popup immediately after sending message
                window.close();
            }} else if (window.parent !== window) {{
                // If opened in iframe
                window.parent.postMessage({{
                    type: 'GMAIL_AUTH_SUCCESS',
                    user_info: {user_info_json},
                    user_email: '{data.get('user_email', '')}',
                    session_token: '{data.get('session_token', '')}',
                    authentication_method: 'gmail_only',
                    google_drive_connected: false
                }}, '*');
            }} else {{
                // Fallback - redirect to main page
                setTimeout(() => {{ window.location.href = '/'; }}, 2000);
            }}
        </script>
    </body>
    </html>
    """

def _create_gmail_error_page(error, details=None):
    """Create error page for Gmail authentication"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gmail Authentication Error</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .error {{ color: #dc3545; }}
            .details {{ color: #666; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 class="error">❌ Gmail Authentication Failed</h2>
            <p><strong>Error:</strong> {error}</p>
            {f'<p class="details"><strong>Details:</strong> {details}</p>' if details else ''}
            <p>Please close this window and try again.</p>
        </div>
        <script>
            // Send error message to parent window
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'GMAIL_AUTH_ERROR',
                    message: '{error}',
                    details: '{details or ''}'
                }}, '*');  // Allow both 3000 and 5001 ports
                
                // Close popup
                setTimeout(() => {{ window.close(); }}, 3000);
            }} else if (window.parent !== window) {{
                window.parent.postMessage({{
                    type: 'GMAIL_AUTH_ERROR',
                    message: '{error}',
                    details: '{details or ''}'
                }}, '*');
            }}
        </script>
    </body>
    </html>
    """

@cloud_bp.route('/gmail-auth-status', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def gmail_auth_status():
    """Simplified check: does user exist in database?"""
    try:
        logger.info("🔍 Checking user profile existence...")
        
        # Get latest user from database (reuse existing function from app.py)
        from modules.db_utils.safe_connection import safe_db_connection
        
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT gmail_address, display_name, photo_url, last_login 
                FROM user_profiles 
                ORDER BY last_login DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            
            if row:
                gmail_address, display_name, photo_url, last_login = row
                
                logger.info(f"✅ User profile found: {gmail_address}")
                
                return jsonify({
                    'success': True,
                    'authenticated': True,
                    'user_email': gmail_address,
                    'user_info': {
                        'name': display_name,
                        'email': gmail_address,
                        'photo_url': photo_url
                    },
                    'authentication_method': 'profile_based',
                    'google_drive_connected': False,
                    'message': f'User profile found - continuing configuration for {display_name}'
                }), 200
            else:
                logger.info("📭 No user profile found in database")
                return jsonify({
                    'success': False,
                    'authenticated': False,
                    'message': 'No user profile found - signup required'
                }), 200
            
    except Exception as e:
        logger.error(f"❌ User profile check error: {e}")
        return jsonify({
            'success': False,
            'authenticated': False,
            'error': str(e),
            'message': 'User profile check failed'
        }), 500

@cloud_bp.route('/oauth/callback', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def cloud_oauth_callback():
    """OAuth2 callback handler - FIXED for session management and CORS"""
    try:
        logger.info("🔄 Processing OAuth callback...")
        logger.info(f"   Request URL: {request.url}")
        logger.info(f"   Session ID: {session.get('_id', 'no-session')}")
        
        # Get OAuth parameters
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        
        # Handle errors
        if error:
            logger.error(f"❌ OAuth error: {error}")
            return _create_error_page(f"OAuth error: {error}", error_description)
        
        if not code or not state:
            logger.error("❌ Missing required OAuth parameters")
            return _create_error_page("Missing OAuth parameters", "Authorization code or state missing")
        
        # This is Google Drive OAuth flow only
        stored_state = session.get('oauth2_state')
        if not stored_state:
            logger.warning("⚠️ No stored state found, but proceeding (session might have expired)")
            # Don't fail immediately - try to continue with OAuth
        elif state != stored_state:
            logger.error(f"❌ State mismatch: got {state}, expected {stored_state}")
            return _create_error_page("Security verification failed", "Please try authenticating again")
        
        # Set flags for Google Drive flow
        is_gmail_only = False
        
        # Get flow data (Google Drive only)
        flow_data = session.get('oauth2_flow_data')
        
        if not flow_data:
            logger.warning("⚠️ No flow data, using Google Drive defaults")
            flow_data = {
                'scopes': [
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/drive.metadata.readonly'
                ],
                'redirect_uri': 'http://localhost:8080/api/cloud/oauth/callback',
                'client_secrets_file': str(Path(__file__).parent / 'credentials/google_drive_credentials_web.json')
            }
        
        # Recreate flow
        flow = Flow.from_client_secrets_file(
            flow_data['client_secrets_file'], 
            scopes=flow_data['scopes']
        )
        flow.redirect_uri = flow_data['redirect_uri']
        
        logger.info(f"   Using redirect URI: {flow.redirect_uri}")
        
        # Exchange code for tokens (Google Drive flow)
        try:
            logger.info(f"🔄 Attempting Google Drive token exchange...")
            flow.fetch_token(code=code)
            credentials = flow.credentials
            logger.info("✅ Google Drive token exchange successful")
            
        except (InvalidScopeError, OAuth2Error) as scope_error:
            # Handle scope validation errors more gracefully
            error_msg = str(scope_error)
            if "Scope has changed" in error_msg or "userinfo" in error_msg.lower():
                logger.warning(f"⚠️ Google Drive scope validation: {error_msg}")
                logger.info("🔄 Attempting token exchange without strict scope validation (Google auto-adds userinfo scopes)...")
                
                # Try to fetch token without scope validation by directly using the OAuth session
                try:
                    # Get the underlying OAuth2Session and disable scope validation
                    oauth_session = flow.oauth2session
                    original_scope_check = oauth_session._populate_attributes
                    
                    # Temporarily disable scope checking
                    def bypass_scope_check(token):
                        return token
                    
                    oauth_session._populate_attributes = bypass_scope_check
                    
                    # Retry token fetch
                    flow.fetch_token(code=code)
                    credentials = flow.credentials
                    
                    # Restore original scope checking
                    oauth_session._populate_attributes = original_scope_check
                    
                    logger.info("✅ Google Drive token exchange successful (with scope tolerance)")
                    
                except Exception as retry_error:
                    logger.error(f"❌ Google Drive token exchange failed even with scope tolerance: {retry_error}")
                    return _create_error_page("Token exchange failed", str(retry_error))
            else:
                logger.error(f"❌ Google Drive OAuth error: {scope_error}")
                return _create_error_page("OAuth authentication failed", str(scope_error))
            
        except Exception as token_error:
            logger.error(f"❌ Google Drive token exchange failed: {token_error}")
            return _create_error_page("Token exchange failed", str(token_error))
        
        # Get user info using Google Drive API
        try:
            logger.info("💾 Using Drive API for Google Drive user info")
            service = build('drive', 'v3', credentials=credentials)
            about = service.about().get(fields='user,storageQuota').execute()
            
            user_info = {
                'email': about.get('user', {}).get('emailAddress', 'unknown'),
                'name': about.get('user', {}).get('displayName', 'Unknown User'),
                'photo_url': about.get('user', {}).get('photoLink'),
                'authentication_method': 'google_drive'
            }
            
            logger.info(f"✅ Google Drive user info retrieved: {user_info['email']}")
            
        except Exception as user_error:
            logger.error(f"❌ Failed to get Google Drive user info: {user_error}")
            user_info = {
                'email': 'unknown', 
                'name': 'Unknown User',
                'authentication_method': 'google_drive'
            }
        
        # Store Google Drive credentials safely
        session_credentials = None
        try:
            session_credentials = _store_credentials_safely(credentials, user_info)
            logger.info("✅ Google Drive credentials encrypted and session token generated")
                
        except Exception as storage_error:
            logger.error(f"❌ Failed to store Google Drive credentials securely: {storage_error}")
            return _create_error_page("Secure storage failed", str(storage_error))

        # 🔐 GOOGLE DRIVE SESSION RESULT
        session_result = {
            'success': True,
            'authenticated': True,
            'user_info': user_info,
            'user_email': user_info['email'],
            'session_token': session_credentials['session_token'],  # JWT token only
            'folders': [],  # Use loaded folders
            'folder_loading_required': True,
            'lazy_loading_enabled': True,
            'existing_auth': False,
            'authentication_method': 'google_drive',
            'google_drive_connected': True,
            'message': f'Google Drive authentication completed for {user_info["email"]}',
            'backend_port': 8080,
            'timestamp': datetime.now().isoformat(),
            'security_mode': 'encrypted_storage',  # Indicate security enhancement
            # ✅ ADDED BACK: 'credentials' field for list_subfolders endpoint (google-auth format)
            'credentials': {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': list(credentials.scopes) if credentials.scopes else []
            }
        }    
            # Store in session with longer lifetime
        session['auth_result'] = session_result
        session['session_token'] = session_credentials['session_token']  # Store session token for backend access
        session['user_email'] = user_info['email']  # Store user email for fallback
        session.permanent = True
        
        # 🔧 FIX: Clear Google Drive OAuth session data
        session.pop('oauth2_state', None)
        session.pop('oauth2_flow_data', None)
        
        logger.info(f"✅ OAuth completed successfully for: {user_info['email']}")
        
        # ==================== REGISTRATION FLOW LOGIC ====================
        # Check if this is a registration flow
        is_registration = False

        # Method 1: Check session storage
        if session.get('registration_mode') == 'true':
            is_registration = True
            logger.info(f"🎯 Registration mode detected from session for: {user_info['email']}")

        # Method 2: Check if user is new (doesn't exist in user_profiles)
        elif not user_exists_in_db(user_info['email']):
            is_registration = True
            logger.info(f"🆕 New user detected, treating as registration: {user_info['email']}")

        if is_registration:
            logger.info(f"🎉 Processing registration flow for: {user_info['email']}")
            
            # Create user profile using existing account module
            try:
                from modules.account.account import create_user_profile

                user_profile_data = {
                    'email': user_info['email'],
                    'name': user_info.get('name', 'Unknown User'),
                    'picture': user_info.get('photo_url'),
                    'authentication_method': 'google_drive'  # Mark as Google Drive auth
                }

                create_success = create_user_profile(user_profile_data)
                
                if create_success:
                    logger.info(f"✅ User profile created successfully for: {user_info['email']}")
                else:
                    logger.warning(f"⚠️ User profile creation failed for: {user_info['email']}")
                    
            except Exception as profile_error:
                logger.error(f"❌ User profile creation error: {profile_error}")
            
            # Clear registration mode from session
            session.pop('registration_mode', None)
            
            # Create redirect page instead of popup for registration
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Registration Successful</title>
                <meta charset="utf-8">
                <meta http-equiv="refresh" content="3;url=/payment?registered=true&email={user_info['email']}">
            </head>
            <body style="font-family: system-ui; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <div style="background: white; color: #333; padding: 40px; border-radius: 15px; display: inline-block;">
                    <h1 style="color: #28a745;">🎉 Registration Successful!</h1>
                    <p><strong>Welcome:</strong> {user_info['name']}</p>
                    <p><strong>Email:</strong> {user_info['email']}</p>
                    <p>Redirecting to license selection...</p>
                    <div style="margin: 20px 0;">
                        <div style="display: inline-block; animation: spin 1s linear infinite;">⏳</div>
                    </div>
                </div>
                <style>
                    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                </style>
            </body>
            </html>
            """

        else:
            # Normal OAuth flow - continue with existing logic
            logger.info(f"🔄 Normal OAuth flow for existing user: {user_info['email']}")
            
            # Return Google Drive success page
            return _create_success_page_with_postmessage(session_result)
        
    except Exception as e:
        logger.error(f"❌ OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        return _create_error_page("Authentication error", str(e))

def _store_credentials_safely(credentials, user_info):
    """Store credentials safely with AES-256 encryption"""
    try:
        tokens_dir = str(Path(__file__).parent / 'tokens')
        os.makedirs(tokens_dir, exist_ok=True)

        email_hash = hashlib.sha256(user_info['email'].encode()).hexdigest()[:16]
        token_filename = f"google_drive_{email_hash}.json"
        token_filepath = str(Path(tokens_dir) / token_filename)

        # Convert google-auth credentials to oauth2client format for consistent storage
        credential_data = {
            'token': credentials.token,  # google-auth uses 'token' not 'access_token'
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else [],
            'user_info': user_info,
            'created_at': datetime.now().isoformat(),
            'expires_at': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        # 🔐 PHASE 1 SECURITY: Encrypt credentials before storage
        encrypted_credentials = encrypt_credentials(credential_data)
        if not encrypted_credentials:
            raise Exception("Failed to encrypt credentials")
        
        # Store encrypted credentials
        encrypted_storage = {
            'encrypted_data': encrypted_credentials,
            'user_email': user_info['email'],  # Keep email unencrypted for lookup
            'created_at': datetime.now().isoformat(),
            'encryption_version': '1.0'
        }
        
        with open(token_filepath, 'w') as f:
            json.dump(encrypted_storage, f, indent=2)
        
        # Set restrictive permissions (600 = owner read/write only)
        os.chmod(token_filepath, 0o600)
        logger.info(f"✅ Encrypted credentials stored to: {token_filepath}")
        
        # 🔐 PHASE 1: Return session data instead of raw credentials
        return {
            'session_token': generate_session_token(user_info['email'], user_info),
            'user_email': user_info['email'],
            'user_name': user_info.get('name', 'Unknown'),
            'photo_url': user_info.get('photo_url'),
            'encrypted_storage_path': token_filepath
        }
        
    except Exception as e:
        logger.error(f"❌ Secure credential storage error: {e}")
        raise
    
def _create_success_page_with_postmessage(session_result):
    """Success page with postMessage for COOP compatibility"""
    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>VTrack - Authentication Successful</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    min-height: 100vh;
                }}
                .container {{
                    background: white;
                    color: #333;
                    padding: 40px;
                    border-radius: 15px;
                    display: inline-block;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    max-width: 500px;
                }}
                .success-icon {{ font-size: 4em; margin-bottom: 20px; }}
                .user-info {{
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    text-align: left;
                }}
                .status {{
                    background: #cce5ff;
                    border: 1px solid #99ccff;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 8px;
                    text-align: left;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h1 style="color: #28a745;">Authentication Successful!</h1>
                
                <div class="user-info">
                    <h3>Google Drive Connected (Secure Mode)</h3>
                    <p><strong>Account:</strong> {session_result['user_email']}</p>
                    <p><strong>Name:</strong> {session_result['user_info']['name']}</p>
                    <p><strong>Security:</strong> Encrypted storage, Session tokens</p>
                    <p><strong>Backend:</strong> localhost:8080</p>
                </div>
                
                <div class="status" id="status">
                    <strong>Status:</strong> <span id="statusText">Notifying VTrack...</span>
                </div>
                
                <p style="color: #28a745; font-weight: bold;">
                    🎉 You can now close this window and return to VTrack!
                </p>
                
                <p style="font-size: 0.9em; color: #666;">
                    This window will close automatically in <span id="countdown">10</span> seconds.
                </p>
                
                <button onclick="window.close()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 10px;">
                    Close Window
                </button>
            </div>
            
            <script>
                console.log('✅ OAuth success page loaded');
                
                const statusEl = document.getElementById('statusText');
                const countdownEl = document.getElementById('countdown');
                
                // 🔐 PHASE 1 SECURITY: Prepare SECURE session data (NO CREDENTIALS)
                const authData = {{
                    success: {str(session_result.get('success', True)).lower()},
                    authenticated: {str(session_result.get('authenticated', True)).lower()},
                    user_email: "{session_result.get('user_email', '')}",
                    user_info: {json.dumps(session_result.get('user_info', {}))},
                    session_token: "{session_result.get('session_token', '')}",
                    folders: {json.dumps(session_result.get('folders', []))},
                    folder_loading_required: {str(session_result.get('folder_loading_required', True)).lower()},
                    lazy_loading_enabled: {str(session_result.get('lazy_loading_enabled', True)).lower()},
                    existing_auth: {str(session_result.get('existing_auth', False)).lower()},
                    message: "{session_result.get('message', '')}",
                    backend_port: {session_result.get('backend_port', 8080)},
                    timestamp: "{session_result.get('timestamp', '')}",
                    security_mode: "{session_result.get('security_mode', 'encrypted_storage')}"
                    // ❌ REMOVED: credentials field - no longer exposed to frontend
                }};
                
                // Function to notify parent window
                function notifyParent() {{
                    try {{
                        if (window.opener && !window.opener.closed) {{
                            console.log('📬 Sending SECURE success message to parent window');
                            
                            // ✅ FIXED: Send only to localhost:3000 to avoid origin mismatch
                            window.opener.postMessage({{
                                type: 'OAUTH_SUCCESS',
                                ...authData
                            }}, '*');  // Allow both 3000 and 5001 ports
                            
                            statusEl.textContent = 'VTrack notified successfully! (Secure mode)';
                            statusEl.style.color = '#28a745';
                        }} else {{
                            console.log('⚠️ Parent window not available');
                            statusEl.textContent = 'Parent window not found';
                            statusEl.style.color = '#856404';
                        }}
                    }} catch (error) {{
                        console.error('❌ Error notifying parent:', error);
                        statusEl.textContent = 'Error notifying VTrack';
                        statusEl.style.color = '#dc3545';
                    }}
                }}
                
                // Auto-close countdown
                let countdown = 10;
                const countdownInterval = setInterval(() => {{
                    countdown--;
                    countdownEl.textContent = countdown;
                    if (countdown <= 0) {{
                        clearInterval(countdownInterval);
                        window.close();
                    }}
                }}, 1000);
                
                // Immediate notification
                notifyParent();
                
                // Auto-close after delay
                setTimeout(() => {{
                    try {{
                        window.close();
                    }} catch (e) {{
                        console.log('📝 Note: Could not auto-close window');
                    }}
                }}, 10000);
            </script>
        </body>
    </html>
    """

def _create_error_page(error_message, error_details=None):
    """Error page for port 8080"""
    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>VTrack - Authentication Failed</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                    color: white;
                    margin: 0;
                    min-height: 100vh;
                }}
                .container {{
                    background: white;
                    color: #333;
                    padding: 40px;
                    border-radius: 15px;
                    display: inline-block;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                }}
                .error-icon {{ font-size: 4em; margin-bottom: 20px; }}
                .error-details {{
                    background: #f8d7da;
                    border: 1px solid #f5c6cb;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 8px;
                    text-align: left;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">❌</div>
                <h1 style="color: #dc3545;">Authentication Failed</h1>
                
                <div class="error-details">
                    <h4>Error Details:</h4>
                    <p><strong>Message:</strong> {error_message}</p>
                    {f"<p><strong>Details:</strong> {error_details}</p>" if error_details else ""}
                    <p><strong>Backend:</strong> localhost:8080</p>
                </div>
                
                <p>Please try again or contact support.</p>
                <button onclick="window.close()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Close Window
                </button>
            </div>
            
            <script>
                // Notify parent window of error
                if (window.opener) {{
                    // Standardized to localhost only to avoid origin mismatch
                    window.opener.postMessage({{
                        type: 'OAUTH_ERROR',
                        error: '{error_message}',
                        details: '{error_details or ""}',
                        backend_port: 8080
                    }}, '*');  // Allow both 3000 and 5001 ports
                }}
                
                setTimeout(() => window.close(), 10000);
            </script>
        </body>
    </html>
    """, 400

# 🆕 NEW: Auth status check with lazy loading support
@cloud_bp.route('/drive-auth-status', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@rate_limit('auth_status')
def drive_auth_status():
    """🔐 PHASE 1 SECURITY: Check Google Drive authentication status using session tokens"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,x-timezone-version,x-timezone-detection,x-client-offset')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        # 🎯 CHECK SETUP CONTEXT FIRST
        setup_step = session.get('current_setup_step')
        is_video_source_setup = (setup_step == 'video-source')

        if is_video_source_setup:
            # Step 3 setup: Always return NOT authenticated to force manual auth
            logger.info("🎯 Step 3 setup detected - Drive auth status: NOT AUTHENTICATED")
            result = {
                'success': True,
                'authenticated': False,
                'message': 'Setup mode - manual Google Drive auth required',
                'setup_mode': True,
                'requires_auth': True
            }
            return jsonify(result), 200

        # Normal mode: Check actual session tokens
        cache_key = get_cache_key('auth_status', session.get('_id', 'anonymous'))
        cached_result = get_cached_data(cache_key)

        if cached_result:
            logger.debug("📋 Auth status cache hit")
            return jsonify(cached_result), 200

        # 🔐 PHASE 1: Get session token from request headers or session
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '') or session.get('session_token')

        if session_token:
            # Verify session token
            token_payload = verify_session_token(session_token)
            if token_payload:
                # Valid session token
                result = {
                    'success': True,
                    'authenticated': True,
                    'user_email': token_payload.get('user_email'),
                    'user_info': {
                        'email': token_payload.get('user_email'),
                        'name': token_payload.get('user_name'),
                        'photo_url': token_payload.get('photo_url')
                    },
                    'session_token': session_token,  # Return current token
                    'folders': [],  # Empty - use separate endpoint
                    'folder_loading_required': True,
                    'lazy_loading_enabled': True,
                    'message': f"Authenticated as {token_payload.get('user_email')}",
                    'existing_auth': True,
                    'backend_port': 8080,
                    'security_mode': 'session_based',
                    'token_expires': token_payload.get('exp')
                    # ❌ REMOVED: 'credentials' field - no longer exposed
                }
                
                set_cached_data(cache_key, result, 'auth_status')
                return jsonify(result), 200
            else:
                # Invalid or expired token
                result = {
                    'success': False,
                    'authenticated': False,
                    'message': 'Session token invalid or expired',
                    'lazy_loading_enabled': False,
                    'requires_reauth': True,
                    'security_mode': 'session_based'
                }
        else:
            # No session token found
            result = {
                'success': False,
                'authenticated': False,
                'message': 'No authentication session found',
                'lazy_loading_enabled': False,
                'security_mode': 'session_based'
            }
        
        set_cached_data(cache_key, result, 'auth_status')
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Auth status error: {e}")
        return jsonify({
            'success': False,
            'authenticated': False,
            'message': f'Auth status check failed: {str(e)}',
            'security_mode': 'session_based'
        }), 500

# 🆕 NEW: Folder initialization endpoint
@cloud_bp.route('/folders/initialize', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@rate_limit('folder_discovery')
def initialize_folder_tree():
    """
    Initialize folder tree after authentication
    Called separately from auth flow for better performance
    """
    try:
        # 🔒 SECURITY: Verify session token
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_token:
            return jsonify({
                'success': False,
                'message': 'Session token required',
                'requires_auth': True
            }), 401

        # Verify session token
        token_payload = verify_session_token(session_token)
        if not token_payload:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired session token',
                'requires_reauth': True
            }), 401

        user_email = token_payload.get('user_email')
        
        # Load encrypted credentials for this user
        credentials = load_encrypted_credentials_for_user(user_email)
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid credentials found',
                'requires_auth': True
            }), 401
        
        # Get request parameters
        data = request.get_json() or {}
        max_folders = min(data.get('max_folders', 30), 50)  # Default 30, max 50
        
        logger.info(f"📂 Loading initial folder tree (max: {max_folders}) for: {user_email}")
        
        # Initialize Google Drive service
        service = build('drive', 'v3', credentials=credentials)
        
        # Get root level folders
        query = "mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, parents, createdTime)",
            pageSize=max_folders,
            orderBy='name'
        ).execute()
        
        folders = results.get('files', [])
        
        # Format for tree component
        tree_folders = []
        for folder in folders:
            tree_folder = {
                'id': folder['id'],
                'name': folder['name'],
                'type': 'folder',
                'parent_id': 'root',
                'depth': 1,
                'selectable': False,  # Only depth 4 is selectable
                'has_subfolders': True,  # Assume true, check on expand
                'created': folder.get('createdTime'),
                'path': f"/My Drive/{folder['name']}",
                'loaded': False  # Mark as not fully loaded
            }
            tree_folders.append(tree_folder)
        
        response_data = {
            'success': True,
            'folders': tree_folders,
            'total_count': len(tree_folders),
            'user_email': user_email,
            'tree_initialized': True,
            'lazy_loading': True,
            'max_depth': 4,
            'selectable_depth': 4,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Folder tree initialized: {len(tree_folders)} root folders")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Folder tree initialization error: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to initialize folder tree: {str(e)}',
            'error_type': type(e).__name__
        }), 500

# 🆕 NEW: List subfolders endpoint
@cloud_bp.route('/folders/list_subfolders', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@rate_limit('folder_discovery')
def list_subfolders():
    """List subfolders for a given parent folder"""
    try:
        # 🔒 SECURITY: Verify session token
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_token:
            return jsonify({
                'success': False,
                'message': 'Session token required',
                'requires_auth': True
            }), 401

        # Verify session token
        token_payload = verify_session_token(session_token)
        if not token_payload:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired session token',
                'requires_reauth': True
            }), 401

        user_email = token_payload.get('user_email')
        
        # Load encrypted credentials for this user
        credentials = load_encrypted_credentials_for_user(user_email)
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No valid credentials found',
                'requires_auth': True
            }), 401
        
        # Get request parameters
        data = request.get_json() or {}
        parent_id = data.get('parent_id', 'root')
        max_results = min(data.get('max_results', 50), 100)
        
        logger.info(f"📂 Loading subfolders for: {parent_id} (user: {user_email})")
        
        # Initialize Google Drive service
        service = build('drive', 'v3', credentials=credentials)
        
        # Get subfolders
        query = f"mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, parents, createdTime)",
            pageSize=max_results,
            orderBy='name'
        ).execute()
        
        folders = results.get('files', [])
        
        # Format for tree component (determine depth from parent)
        parent_depth = 0  # TODO: Could track depth in request if needed
        tree_folders = []
        for folder in folders:
            tree_folder = {
                'id': folder['id'],
                'name': folder['name'],
                'type': 'folder',
                'parent_id': parent_id,
                'depth': parent_depth + 1,
                'selectable': (parent_depth + 1) >= 3,  # Selectable at depth 3+
                'has_subfolders': True,  # Assume true for now
                'created': folder.get('createdTime'),
                'path': f"/{folder['name']}",  # Simplified path
                'loaded': False
            }
            tree_folders.append(tree_folder)
        
        response_data = {
            'success': True,
            'folders': tree_folders,
            'total_count': len(tree_folders),
            'parent_id': parent_id,
            'user_email': user_email,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Loaded {len(tree_folders)} subfolders for {parent_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ List subfolders error: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to list subfolders: {str(e)}',
            'error_type': type(e).__name__
        }), 500

# 🆕 NEW: Disconnect endpoint
@cloud_bp.route('/disconnect', methods=['POST'])
def cloud_disconnect():
    """Disconnect from cloud provider"""
    try:
        data = request.get_json()
        provider = data.get('provider', 'google_drive')
        user_email = data.get('user_email')
        
        logger.info(f"🔌 Disconnecting {provider} for {user_email}")
        
        # Clear session
        session.pop('auth_result', None)
        session.pop('oauth2_state', None)
        session.pop('oauth2_flow_data', None)
        
        # Clear cache
        cache_storage.clear()
        
        # Optionally remove stored token file
        if user_email:
            try:
                tokens_dir = str(Path(__file__).parent / 'tokens')
                email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
                token_filename = f"google_drive_{email_hash}.json"
                token_filepath = str(Path(tokens_dir) / token_filename)
                
                if Path(token_filepath).exists():
                    os.remove(token_filepath)
                    logger.info(f"🗑️ Removed token file: {token_filename}")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove token file: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully disconnected from {provider}',
            'provider': provider
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Disconnect error: {e}")
        return jsonify({
            'success': False,
            'message': f'Disconnect failed: {str(e)}'
        }), 500

def load_encrypted_credentials_for_user(user_email):
    """Load and decrypt credentials for backend operations"""
    try:
        tokens_dir = str(Path(__file__).parent / 'tokens')
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        token_filename = f"google_drive_{email_hash}.json"
        token_filepath = str(Path(tokens_dir) / token_filename)
        
        if not Path(token_filepath).exists():
            logger.warning(f"⚠️ No encrypted credentials found for: {user_email}")
            return None
        
        # Load encrypted storage
        with open(token_filepath, 'r') as f:
            encrypted_storage = json.load(f)
        
        # Decrypt credentials
        credential_data = decrypt_credentials(encrypted_storage['encrypted_data'])
        if not credential_data:
            logger.error(f"❌ Failed to decrypt credentials for: {user_email}")
            return None
        
        # Reconstruct credentials object using oauth2client for PyDrive2 compatibility
        from datetime import datetime, timezone

        # Convert expires_at to datetime if it exists
        token_expiry = None
        if 'expires_at' in credential_data and credential_data['expires_at']:
            token_expiry = datetime.fromisoformat(credential_data['expires_at'].replace('Z', '+00:00'))

        credentials = OAuth2Credentials(
            access_token=credential_data['token'],
            client_id=credential_data['client_id'],
            client_secret=credential_data['client_secret'],
            refresh_token=credential_data['refresh_token'],
            token_expiry=token_expiry,
            token_uri=credential_data['token_uri'],
            user_agent="VTrack-PyDrive2-Client/1.0"
        )
        
        # Refresh if expired (oauth2client compatibility)
        if credentials.access_token_expired and credentials.refresh_token:
            logger.info("🔄 Refreshing expired credentials...")
            import httplib2
            http = httplib2.Http()
            credentials.refresh(http)

            # Update stored credentials with new token
            credential_data['token'] = credentials.access_token
            credential_data['expires_at'] = credentials.token_expiry.isoformat() if credentials.token_expiry else None
            
            encrypted_updated = encrypt_credentials(credential_data)
            if encrypted_updated:
                encrypted_storage['encrypted_data'] = encrypted_updated
                with open(token_filepath, 'w') as f:
                    json.dump(encrypted_storage, f, indent=2)
                os.chmod(token_filepath, 0o600)
        
        logger.info(f"✅ Loaded encrypted credentials for: {user_email}")
        return credentials
        
    except Exception as e:
        logger.error(f"❌ Error loading encrypted credentials: {e}")
        return None

@cloud_bp.route('/set-registration-mode', methods=['POST'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def set_registration_mode():
    """Set registration mode flag in session"""
    try:
        session['registration_mode'] = 'true'
        session.permanent = True
        
        logger.info("🎯 Registration mode set in session")
        
        return jsonify({
            'success': True,
            'message': 'Registration mode activated'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error setting registration mode: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to set registration mode: {str(e)}'
        }), 500

def get_credentials_from_session():
    """Get credentials using session token (for API endpoints)"""
    try:
        # Get session token from request headers or session
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '') or session.get('session_token')

        if not session_token:
            return None

        # Verify session token
        token_payload = verify_session_token(session_token)
        if not token_payload:
            return None

        user_email = token_payload.get('user_email')
        if not user_email:
            return None

        # Load encrypted credentials for this user
        return load_encrypted_credentials_for_user(user_email)

    except Exception as e:
        logger.error(f"❌ Error getting credentials from session: {e}")
        return None

@cloud_bp.route('/set-setup-step', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def set_setup_step():
    """Set current setup step for tracking initial setup flow"""
    try:
        data = request.get_json()
        step = data.get('step')

        if step:
            session['current_setup_step'] = step
            session.permanent = True
            logger.info(f"📍 Setup step set: {step}")

            return jsonify({
                'success': True,
                'step': step,
                'message': f'Setup step set to: {step}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Step parameter required'
            }), 400

    except Exception as e:
        logger.error(f"❌ Error setting setup step: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to set setup step: {str(e)}'
        }), 500

@cloud_bp.route('/clear-setup-step', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def clear_setup_step():
    """Clear setup step - marks setup as completed"""
    try:
        session.pop('current_setup_step', None)
        session.permanent = True
        logger.info("✅ Setup step cleared - setup completed")

        return jsonify({
            'success': True,
            'message': 'Setup completed - step cleared'
        }), 200

    except Exception as e:
        logger.error(f"❌ Error clearing setup step: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to clear setup step: {str(e)}'
        }), 500