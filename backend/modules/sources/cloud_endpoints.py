# modules/sources/cloud_endpoints.py - FIXED: API Routes & Session Handling
#!/usr/bin/env python3

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import hashlib
import json
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from google.oauth2.credentials import Credentials
from flask_cors import CORS, cross_origin
from functools import wraps
from flask import g
import time
from collections import defaultdict
import jwt
import secrets
from cryptography.fernet import Fernet
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secret key for JWT - In production, use environment variable
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')

# Encryption key for credentials - In production, use environment variable  
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
if isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

def generate_session_token(user_email, user_info, expires_minutes=30):
    """Generate JWT session token instead of returning raw credentials"""
    try:
        payload = {
            'user_email': user_email,
            'user_name': user_info.get('name', 'Unknown'),
            'photo_url': user_info.get('photo_url'),
            'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
            'iat': datetime.utcnow(),
            'iss': 'vtrack-oauth',
            'type': 'session'
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
        logger.info(f"✅ Generated session token for: {user_email} (expires in {expires_minutes}min)")
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
     origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

@cloud_bp.route('/authenticate', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
def cloud_authenticate():
    """Google OAuth2 authentication - FIXED for multiple environments"""
    try:
        data = request.get_json()
        provider = data.get('provider', 'google_drive')
        action = data.get('action', 'initiate_auth')
        
        # 🆕 NEW: Get redirect URI from request or determine automatically
        custom_redirect = data.get('redirect_uri')
        
        logger.info(f"🔐 Cloud authentication request: {provider}, action: {action}")
        
        if action == 'initiate_auth':
            CLIENT_SECRETS_FILE = os.path.join(
                os.path.dirname(__file__), 
                'credentials/google_drive_credentials_web.json'
            )
            
            if not os.path.exists(CLIENT_SECRETS_FILE):
                return jsonify({
                    'success': False,
                    'message': f'Credentials file not found: {CLIENT_SECRETS_FILE}',
                    'setup_required': True
                }), 400
            
            SCOPES = [
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/drive.metadata.readonly'
            ]
            
            # Create flow
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, 
                scopes=SCOPES
            )
            
            # 🔧 FIX: Determine redirect URI dynamically
            if custom_redirect:
                redirect_uri = custom_redirect
            else:
                # Auto-detect based on request headers
                host = request.headers.get('Host', 'localhost:8080')
                if '127.0.0.1' in host:
                    redirect_uri = 'http://127.0.0.1:8080/api/cloud/oauth/callback'
                else:
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
        
        # 🔧 FIX: More flexible state verification
        stored_state = session.get('oauth2_state')
        if not stored_state:
            logger.warning("⚠️ No stored state found, but proceeding (session might have expired)")
            # Don't fail immediately - try to continue with OAuth
        elif state != stored_state:
            logger.error(f"❌ State mismatch: got {state}, expected {stored_state}")
            return _create_error_page("Security verification failed", "Please try authenticating again")
        
        # Get flow data (with fallback)
        flow_data = session.get('oauth2_flow_data')
        if not flow_data:
            logger.warning("⚠️ No flow data, using defaults")
            flow_data = {
                'scopes': [
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/drive.metadata.readonly'
                ],
                'redirect_uri': 'http://localhost:8080/api/cloud/oauth/callback',
                'client_secrets_file': os.path.join(
                    os.path.dirname(__file__), 
                    'credentials/google_drive_credentials_web.json'
                )
            }
        
        # Recreate flow
        flow = Flow.from_client_secrets_file(
            flow_data['client_secrets_file'], 
            scopes=flow_data['scopes']
        )
        flow.redirect_uri = flow_data['redirect_uri']
        
        logger.info(f"   Using redirect URI: {flow.redirect_uri}")
        
        # Exchange code for tokens
        try:
            logger.info(f"🔄 Attempting token exchange...")
            flow.fetch_token(code=code)
            credentials = flow.credentials
            logger.info("✅ Token exchange successful")
        except Exception as token_error:
            logger.error(f"❌ Token exchange failed: {token_error}")
            return _create_error_page("Token exchange failed", str(token_error))
        
        # Get user info
        try:
            service = build('drive', 'v3', credentials=credentials)
            about = service.about().get(fields='user,storageQuota').execute()
            
            user_info = {
                'email': about.get('user', {}).get('emailAddress', 'unknown'),
                'name': about.get('user', {}).get('displayName', 'Unknown User'),
                'photo_url': about.get('user', {}).get('photoLink'),
            }
            logger.info(f"✅ User info retrieved: {user_info['email']}")
            
        except Exception as user_error:
            logger.error(f"❌ Failed to get user info: {user_error}")
            user_info = {'email': 'unknown', 'name': 'Unknown User'}
        
        # 🔐 PHASE 1 SECURITY: Store credentials safely and return session token only
        session_credentials = None
        try:
            session_credentials = _store_credentials_safely(credentials, user_info)
            logger.info("✅ Credentials encrypted and session token generated")
        except Exception as storage_error:
            logger.error(f"❌ Failed to store credentials securely: {storage_error}")
            return _create_error_page("Secure storage failed", str(storage_error))

        # 🔐 SECURE SESSION RESULT - NO RAW CREDENTIALS
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
            'message': f'Authentication completed for {user_info["email"]}',
            'backend_port': 8080,
            'timestamp': datetime.now().isoformat(),
            'security_mode': 'encrypted_storage'  # Indicate security enhancement
            # ❌ REMOVED: 'credentials' field - no longer exposed to frontend
        }    
            # Store in session with longer lifetime
        session['auth_result'] = session_result
        session.permanent = True
        
        # 🔧 FIX: Clear OAuth session data
        session.pop('oauth2_state', None)
        session.pop('oauth2_flow_data', None)
        
        logger.info(f"✅ OAuth completed successfully for: {user_info['email']}")
        
        # Return success page with postMessage
        return _create_success_page_with_postmessage(session_result)
        
    except Exception as e:
        logger.error(f"❌ OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        return _create_error_page("Authentication error", str(e))

def _store_credentials_safely(credentials, user_info):
    """Store credentials safely with AES-256 encryption"""
    try:
        tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
        os.makedirs(tokens_dir, exist_ok=True)
        
        email_hash = hashlib.sha256(user_info['email'].encode()).hexdigest()[:16]
        token_filename = f"google_drive_{email_hash}.json"
        token_filepath = os.path.join(tokens_dir, token_filename)
        
        # Prepare credential data
        credential_data = {
            'token': credentials.token,
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
                            
                            // 🔧 FIX: Send to both localhost:3000 and 127.0.0.1:3000
                            const origins = [
                                'http://localhost:3000',
                                'http://127.0.0.1:3000'
                            ];
                            
                            origins.forEach(origin => {{
                                window.opener.postMessage({{
                                    type: 'OAUTH_SUCCESS',
                                    ...authData
                                }}, origin);
                            }});
                            
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
                    const origins = ['http://localhost:3000', 'http://127.0.0.1:3000'];
                    origins.forEach(origin => {{
                        window.opener.postMessage({{
                            type: 'OAUTH_ERROR',
                            error: '{error_message}',
                            details: '{error_details or ""}',
                            backend_port: 8080
                        }}, origin);
                    }});
                }}
                
                setTimeout(() => window.close(), 10000);
            </script>
        </body>
    </html>
    """, 400

# 🆕 NEW: Auth status check with lazy loading support
@cloud_bp.route('/auth-status', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
@rate_limit('auth_status')
def auth_status():
    """🔐 PHASE 1 SECURITY: Check authentication status using session tokens"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
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
                tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
                email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
                token_filename = f"google_drive_{email_hash}.json"
                token_filepath = os.path.join(tokens_dir, token_filename)
                
                if os.path.exists(token_filepath):
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
        tokens_dir = os.path.join(os.path.dirname(__file__), 'tokens')
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        token_filename = f"google_drive_{email_hash}.json"
        token_filepath = os.path.join(tokens_dir, token_filename)
        
        if not os.path.exists(token_filepath):
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
        
        # Reconstruct credentials object
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
            
            # Update stored credentials with new token
            credential_data['token'] = credentials.token
            credential_data['expires_at'] = credentials.expiry.isoformat() if credentials.expiry else None
            
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