from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Flask, g
from flask_cors import CORS
import os
import json
import sqlite3
import logging
import time
from modules.db_utils import find_project_root, get_db_connection
from modules.scheduler.db_sync import db_rwlock
from modules.sources.path_manager import PathManager
from database import update_database, DB_PATH, initialize_sync_status
# 🆕 NEW: Cloud endpoints module
from modules.sources.cloud_endpoints import cloud_bp
# 🔒 SECURITY: Import security modules
import jwt
from cryptography.fernet import Fernet
import base64
import hashlib
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple
from google.oauth2.credentials import Credentials
import google.auth.exceptions
from modules.sources.sync_endpoints import sync_bp

"""
🎯 V_TRACK BACKGROUND SERVICE AUTHENTICATION STRATEGY

V_track is designed as a "set it and forget it" background monitoring service,
similar to traditional DVR/NVR systems. Users expect:

1. Setup once → Run forever
2. No daily authentication prompts  
3. Continuous auto-sync without interruption
4. Zero maintenance authentication

SESSION DURATION STRATEGY:
- JWT Session: 90 days (3 months)
- Refresh Token: 365 days (1 year)  
- Auto-refresh: When 7 days remaining
- Grace Period: 7 days if refresh fails

This ensures maximum user convenience while maintaining reasonable security.
User only needs to re-authenticate every 3 months, or ideally never if
auto-refresh works correctly.

BACKGROUND SERVICE PHILOSOPHY:
- Silent operation (no popups/interruptions)
- Aggressive auto-refresh to prevent expiry
- Graceful degradation if authentication fails
- Prioritize reliability over strict security
"""

config_bp = Blueprint('config', __name__)

# ✅ CLEAN: No more blueprint-level CORS handlers
# All CORS will be handled by Flask-CORS global config only

# Xác định thư mục gốc của dự án
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# 🔒 SECURITY: Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration and utilities"""
    
    def __init__(self):
        # 🔒 SECURITY: Initialize encryption keys
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', self._generate_jwt_secret())
        self.encryption_key = os.getenv('ENCRYPTION_KEY', self._generate_encryption_key())
        self.cipher_suite = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        
        # 🎯 V_TRACK BACKGROUND SERVICE: Long-running authentication for "set it and forget it" model
        # User behavior: Setup once → Run forever like DVR/NVR, no daily interaction
        
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
        
        logger.info("🔒 V_track Background Service authentication initialized")
        logger.info(f"📅 JWT Session Duration: {self.session_duration}")
        logger.info(f"🔄 Refresh Token Duration: {self.refresh_token_duration}")
        logger.info(f"⚡ Auto-refresh Threshold: {self.refresh_threshold}")    
    def _generate_jwt_secret(self) -> str:
        """Generate JWT secret key if not provided"""
        import secrets
        secret = secrets.token_urlsafe(32)
        logger.warning("🔑 JWT_SECRET_KEY not found in environment, generated temporary key")
        return secret
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key if not provided"""
        key = Fernet.generate_key()
        logger.warning("🔑 ENCRYPTION_KEY not found in environment, generated temporary key")
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
            logger.info(f"✅ Refreshed tokens for user: {user_email}")
            return new_tokens
            
        except jwt.ExpiredSignatureError:
            logger.warning("🚨 Refresh token expired - require re-authentication")
            return None
        except jwt.InvalidTokenError:
            logger.warning("❌ Invalid refresh token")
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

class ConfigManager:
    """Enhanced configuration manager with security features"""
    
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.security = SecurityConfig()
        
        # 🔒 SECURITY: Cloud credential proxy cache
        self._credential_cache = {}
        self._cache_expiry = {}
        
        logger.info("🔧 Configuration manager initialized with security")
    
    # 🔒 SECURITY: Session verification middleware
    def require_session(self, f):
        """Decorator to require valid session"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'No valid session token provided'}), 401
            
            token = auth_header.split(' ')[1]
            session_data = self.security.validate_session_token(token)
            
            if not session_data:
                return jsonify({'error': 'Invalid or expired session'}), 401
            
            # Check session in database
            if self.db:
                from database import get_session
                db_session = get_session(token)
                if not db_session:
                    return jsonify({'error': 'Session not found'}), 401
                
                g.session_token = token
                g.user_email = session_data['user_email']
                g.provider = session_data.get('provider', 'google_drive')
                g.db_session = db_session
            
            return f(*args, **kwargs)
        return decorated_function
    
    # 🔒 SECURITY: Session-based source validation
    def validate_cloud_source(self, source_config: Dict, session_token: str) -> Tuple[bool, str]:
        """Validate cloud source configuration with session"""
        try:
            if not session_token:
                return False, "No session token provided"
            
            # Validate session
            session_data = self.security.validate_session_token(session_token)
            if not session_data:
                return False, "Invalid or expired session"
            
            # Get session from database
            if self.db:
                from database import get_session
                db_session = get_session(session_token)
                if not db_session:
                    return False, "Session not found in database"
                
                # Validate provider matches
                if source_config.get('provider') != db_session.get('provider'):
                    return False, "Provider mismatch with session"
                
                # Validate user matches
                if session_data['user_email'] != db_session['user_email']:
                    return False, "User mismatch with session"
            
            # Validate required fields
            required_fields = ['provider', 'selected_folders']
            for field in required_fields:
                if field not in source_config:
                    return False, f"Missing required field: {field}"
            
            if not source_config['selected_folders']:
                return False, "No folders selected"
            
            return True, "Cloud source configuration valid"
            
        except Exception as e:
            logger.error(f"Error validating cloud source: {e}")
            return False, f"Validation error: {str(e)}"
    
    # 🔒 SECURITY: Backend credential proxy for cloud operations
    def get_cloud_credentials(self, session_token: str) -> Optional[Credentials]:
        """Get decrypted credentials for cloud operations"""
        try:
            # Check cache first
            if session_token in self._credential_cache:
                cached_time = self._cache_expiry.get(session_token)
                if cached_time and datetime.utcnow() < cached_time:
                    return self._credential_cache[session_token]
                else:
                    # Clean expired cache
                    self._credential_cache.pop(session_token, None)
                    self._cache_expiry.pop(session_token, None)
            
            # Get session from database
            if not self.db:
                logger.error("Database manager not available")
                return None
            
            from database import get_session
            db_session = get_session(session_token)
            if not db_session:
                logger.error("Session not found")
                return None
            
            # Decrypt credentials
            encrypted_creds = db_session.get('encrypted_credentials')
            if not encrypted_creds:
                logger.error("No encrypted credentials found")
                return None
            
            creds_dict = self.security.decrypt_credentials(encrypted_creds)
            
            # Create Google credentials object
            credentials = Credentials(
                token=creds_dict.get('token'),
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict.get('token_uri'),
                client_id=creds_dict.get('client_id'),
                client_secret=creds_dict.get('client_secret'),
                scopes=creds_dict.get('scopes')
            )
            
            # Cache for 5 minutes
            self._credential_cache[session_token] = credentials
            self._cache_expiry[session_token] = datetime.utcnow() + timedelta(minutes=5)
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get cloud credentials: {e}")
            return None
    
    def refresh_cloud_credentials(self, session_token: str) -> bool:
        """Refresh cloud credentials and update session"""
        try:
            credentials = self.get_cloud_credentials(session_token)
            if not credentials:
                return False
            
            # Try to refresh
            credentials.refresh(google.auth.transport.requests.Request())
            
            # Update encrypted credentials in database
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            encrypted_creds = self.security.encrypt_credentials(creds_dict)
            
            if self.db:
                from database import update_session_credentials
                success = update_session_credentials(session_token, encrypted_creds)
                if success:
                    # Update cache
                    self._credential_cache[session_token] = credentials
                    self._cache_expiry[session_token] = datetime.utcnow() + timedelta(minutes=5)
                    logger.info("Cloud credentials refreshed successfully")
                    return True
            
            return False
            
        except google.auth.exceptions.RefreshError as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return False
        except Exception as e:
            logger.error(f"Error refreshing credentials: {e}")
            return False
    
    def proxy_cloud_operation(self, session_token: str, operation: str, **kwargs) -> Dict:
        """Proxy cloud operations with backend credentials"""
        try:
            credentials = self.get_cloud_credentials(session_token)
            if not credentials:
                return {'success': False, 'error': 'Unable to get credentials'}
            
            # Import Google Drive service here to avoid circular imports
            from googleapiclient.discovery import build
            
            service = build('drive', 'v3', credentials=credentials)
            
            if operation == 'list_folders':
                # List folders operation
                query = "mimeType='application/vnd.google-apps.folder'"
                if 'parent_id' in kwargs:
                    query += f" and '{kwargs['parent_id']}' in parents"
                
                results = service.files().list(
                    q=query,
                    fields="files(id, name, parents)",
                    pageSize=kwargs.get('page_size', 100)
                ).execute()
                
                folders = results.get('files', [])
                return {
                    'success': True,
                    'folders': folders,
                    'count': len(folders)
                }
            
            elif operation == 'download_file':
                # Download file operation
                file_id = kwargs.get('file_id')
                if not file_id:
                    return {'success': False, 'error': 'File ID required'}
                
                # Get file metadata first
                file_metadata = service.files().get(fileId=file_id).execute()
                
                # Download file content
                content = service.files().get_media(fileId=file_id).execute()
                
                return {
                    'success': True,
                    'metadata': file_metadata,
                    'content': content
                }
            
            else:
                return {'success': False, 'error': f'Unsupported operation: {operation}'}
                
        except Exception as e:
            logger.error(f"Cloud operation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_expired_sessions(self):
        """Cleanup expired sessions and cache"""
        if self.db:
            from database import cleanup_expired_sessions
            deleted_count = cleanup_expired_sessions()
            logger.info(f"Cleaned up {deleted_count} expired sessions")
        
        # Clean credential cache
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, expiry in self._cache_expiry.items()
            if expiry < current_time
        ]
        
        for token in expired_tokens:
            self._credential_cache.pop(token, None)
            self._cache_expiry.pop(token, None)
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired credential cache entries")

# Global configuration instance
config_manager = None

def get_config_manager(db_manager=None):
    """Get or create global configuration manager"""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager(db_manager)
    return config_manager

def init_config(db_manager):
    """Initialize configuration with database manager"""
    global config_manager
    config_manager = ConfigManager(db_manager)
    logger.info("🔧 Configuration initialized")
    return config_manager

def init_app_and_config():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    
    # ✅ FIXED: Single CORS configuration - no duplicates
    CORS(app, 
         resources={
             r"/*": {
                 "origins": ["http://localhost:3000"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True
             }
         })

    # 🎯 V_TRACK BACKGROUND SERVICE: Long-term session configuration
    app.config.update(
        # Background service session - Very long duration for "set it and forget it"
        PERMANENT_SESSION_LIFETIME=timedelta(days=90),  # 3 months session
        
        # Session persistence
        SESSION_REFRESH_EACH_REQUEST=True,  # Extend session on activity
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
        SESSION_COOKIE_SAMESITE='Lax',
        
        # OAuth configuration for background service
        OAUTH_SESSION_LIFETIME=timedelta(days=90),  # Match JWT session duration
        
        # Background service flags
        BACKGROUND_SERVICE_MODE=True,
        SILENT_OPERATION=True
    )
    
    logger.info("🎯 V_track Background Service session configured")
    logger.info("📅 Session lifetime: 90 days (background service mode)")

    DB_PATH = os.path.join(BASE_DIR, "database", "events.db")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Gọi update_database để tạo bảng trước khi truy vấn
    update_database()

    def get_db_path():
        default_db_path = DB_PATH
        try:
            with db_rwlock.gen_rlock():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT db_path FROM processing_config WHERE id = 1")
                result = cursor.fetchone()
                conn.close()
            return result[0] if result else default_db_path
        except Exception as e:
            logger.error(f"Error getting DB_PATH from database: {e}")
            return default_db_path

    final_db_path = get_db_path()
    logger.info(f"Using DB_PATH: {final_db_path}")

    # Truy vấn cấu hình từ processing_config
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT input_path, output_path, frame_rate, frame_interval FROM processing_config WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        if result:
            INPUT_PATH, OUTPUT_PATH, FRAME_RATE, FRAME_INTERVAL = result
        else:
            INPUT_PATH = os.path.join(BASE_DIR, "Inputvideo")
            OUTPUT_PATH = os.path.join(BASE_DIR, "output_clips")
            FRAME_RATE = 30
            FRAME_INTERVAL = 6
    except Exception as e:
        logger.error(f"Error querying processing_config: {e}")
        INPUT_PATH = os.path.join(BASE_DIR, "Inputvideo")
        OUTPUT_PATH = os.path.join(BASE_DIR, "output_clips")
        FRAME_RATE = 30
        FRAME_INTERVAL = 6

    return app, final_db_path, logger

# Hàm đọc cấu hình từ file hoặc biến môi trường
def load_config():
    default_config = {
        "db_path": os.path.join(BASE_DIR, "database", "events.db"),
        "input_path": os.path.join(BASE_DIR, "Inputvideo"),
        "output_path": os.path.join(BASE_DIR, "output_clips")
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
            return default_config
    
    return {
        "db_path": os.getenv("DB_PATH", default_config["db_path"]),
        "input_path": os.getenv("INPUT_PATH", default_config["input_path"]),
        "output_path": os.getenv("OUTPUT_PATH", default_config["output_path"])
    }

# Load cấu hình từ processing_config thay vì config.json
config = load_config()

def detect_camera_folders(path):
    """Detect camera folders in the given path"""
    cameras = []
    
    if not os.path.exists(path):
        return cameras
    
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                # Check if this looks like a camera folder
                # Common camera folder patterns: Cam*, Camera*, Channel*, etc.
                item_lower = item.lower()
                if any(pattern in item_lower for pattern in ['cam', 'camera', 'channel', 'ch']):
                    cameras.append(item)
                # Also include any directory that contains video files
                elif has_video_files(item_path):
                    cameras.append(item)
        
        cameras.sort()  # Sort alphabetically
        return cameras
    except Exception as e:
        print(f"Error detecting cameras in {path}: {e}")
        return cameras

def has_video_files(path, max_depth=2):
    """Check if directory contains video files (recursive up to max_depth)"""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg')
    
    def check_directory(dir_path, depth):
        if depth > max_depth:
            return False
        
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path) and item.lower().endswith(video_extensions):
                    return True
                elif os.path.isdir(item_path) and depth < max_depth:
                    if check_directory(item_path, depth + 1):
                        return True
        except (PermissionError, OSError):
            pass
        
        return False
    
    return check_directory(path, 0)

# ✅ FIX: Helper function để map path cho các source type khác nhau (NO NVR)
def get_working_path_for_source(source_type, source_name, source_path):
    """Map source connection info to actual working directory"""
    if source_type == 'local':
        # Local: source_path is actual file system path
        working_path = source_path
        print(f"📁 Local Path Mapping: {source_path} → {working_path}")
        return working_path
        
    elif source_type == 'cloud':
        # Cloud: source_path is cloud URL, working path is sync directory
        working_path = os.path.join(BASE_DIR, "cloud_sync", source_name)
        print(f"☁️ Cloud Path Mapping: {source_path} → {working_path}")
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(working_path, exist_ok=True)
            print(f"📁 Created/verified Cloud directory: {working_path}")
        except Exception as e:
            print(f"❌ Failed to create Cloud directory {working_path}: {e}")
            
        return working_path
        
    else:
        # Unknown source type: use as-is
        print(f"❓ Unknown source type '{source_type}', using path as-is: {source_path}")
        return source_path
    
# 🔧 ADD HELPER FUNCTION HERE - NGAY SAU function trên kết thúc:
def extract_cameras_from_cloud_folders(folders):
    """Extract camera names from cloud folders"""
    cameras = []
    
    for folder in folders:
        if isinstance(folder, dict):
            # Folder object với metadata
            camera_name = folder.get('name', 'Unknown_Folder')
            
            # If it's a deep folder, use parent names for context
            if folder.get('depth', 1) > 2:
                path_parts = folder.get('path', '').split('/')
                # Use second-to-last part as camera name (skip filename)
                if len(path_parts) >= 2:
                    camera_name = path_parts[-2] or path_parts[-1]
        else:
            # Simple string name
            camera_name = str(folder)
        
        # Clean và standardize camera name
        camera_name = (camera_name
                      .replace(' ', '_')
                      .replace('/', '_')
                      .replace('\\', '_')
                      .strip('_'))
        
        if camera_name and camera_name not in cameras:
            cameras.append(camera_name)
    
    return cameras

# 🔧 FIX 3: Add debug endpoint to check camera sync
@config_bp.route('/debug-cameras', methods=['GET'])
def debug_cameras():
    """Debug endpoint to check camera sync status"""
    try:
        # Get processing_config cameras
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT selected_cameras, input_path FROM processing_config WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            selected_cameras, input_path = result
            try:
                cameras = json.loads(selected_cameras) if selected_cameras else []
            except:
                cameras = []
                
            # Get active source info
            path_manager = PathManager()
            active_sources = path_manager.get_all_active_sources()
            
            return jsonify({
                "processing_config": {
                    "selected_cameras": cameras,
                    "camera_count": len(cameras),
                    "input_path": input_path
                },
                "active_sources": active_sources,
                "debug_time": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({"error": "No processing config found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Debug failed: {str(e)}"}), 500

@config_bp.route('/detect-cameras', methods=['POST'])
def detect_cameras():
    """Detect camera folders in the specified path"""
    try:
        data = request.json
        path = data.get('path')
        
        if not path:
            return jsonify({"error": "Path is required"}), 400
        
        if not os.path.exists(path):
            return jsonify({"error": f"Path does not exist: {path}"}), 400
        
        # Detect camera folders
        cameras = detect_camera_folders(path)
        
        # Get current selected cameras from processing_config
        selected_cameras = []
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT selected_cameras FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            if result and result[0]:
                selected_cameras = json.loads(result[0])
            conn.close()
        except Exception as e:
            print(f"Error getting selected cameras: {e}")
        
        return jsonify({
            "cameras": cameras,
            "selected_cameras": selected_cameras,
            "path": path,
            "count": len(cameras)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to detect cameras: {str(e)}"}), 500

@config_bp.route('/update-source-cameras', methods=['POST'])
def update_source_cameras():
    """🔧 Update selected cameras for a source in processing_config (Simple Update)"""
    try:
        data = request.json
        source_id = data.get('source_id')
        selected_cameras = data.get('selected_cameras', [])
        
        # Update processing_config with selected cameras
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE processing_config 
            SET selected_cameras = ? 
            WHERE id = 1
        """, (json.dumps(selected_cameras),))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Camera selection updated successfully",
            "selected_cameras": selected_cameras,
            "count": len(selected_cameras)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update camera selection: {str(e)}"}), 500

@config_bp.route('/get-cameras', methods=['GET'])
def get_cameras():
    try:
        path_manager = PathManager()
        sources = path_manager.get_all_active_sources()
        
        cameras = []
        
        if sources:
            # Use active source
            active_source = sources[0]  # Single active source
            source_type = active_source['source_type']
            
            if source_type == 'local':
                # Local directory scanning
                video_root = active_source['path']
                if not os.path.exists(video_root):
                    return jsonify({"error": f"Directory {video_root} does not exist. Ensure the path is correct or create the directory."}), 400
                
                # Detect camera folders
                detected_cameras = detect_camera_folders(video_root)
                for camera in detected_cameras:
                    cameras.append({"name": camera, "path": os.path.join(video_root, camera)})
            
            elif source_type in ['cloud', 'camera']:
                # For other source types, use source name as camera
                cameras.append({"name": active_source['name'], "path": active_source['path']})
        else:
            # Fallback to legacy behavior
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT input_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            conn.close()

            if not result:
                return jsonify({"error": "video_root not found in configuration. Please update via /save-config endpoint."}), 400

            video_root = result[0]
            if not os.path.exists(video_root):
                return jsonify({"error": f"Directory {video_root} does not exist. Ensure the path is correct or create the directory."}), 400

            detected_cameras = detect_camera_folders(video_root)
            for camera in detected_cameras:
                cameras.append({"name": camera, "path": os.path.join(video_root, camera)})

        return jsonify({"cameras": cameras}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve cameras: {str(e)}"}), 500

@config_bp.route('/save-config', methods=['POST'])
def save_config():
    """Fixed save_config without frame_settings table dependency"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        video_root = data.get('video_root')
        output_path = data.get('output_path', config.get("output_path", "/default/output"))
        default_days = data.get('default_days', 30)
        min_packing_time = data.get('min_packing_time', 10)
        max_packing_time = data.get('max_packing_time', 120)
        frame_rate = data.get('frame_rate', 30)
        frame_interval = data.get('frame_interval', 5)
        video_buffer = data.get('video_buffer', 2)
        selected_cameras = data.get('selected_cameras', [])
        run_default_on_start = data.get('run_default_on_start', 1)

        print(f"=== SAVE CONFIG REQUEST ===")
        print(f"Raw video_root from frontend: {video_root}")
        print(f"Selected cameras: {selected_cameras}")

        # ✅ FIX: Enhanced path mapping with better error handling
        try:
            # Try to get active source for path mapping
            try:
                from modules.sources.path_manager import PathManager
                path_manager = PathManager()
                active_sources = path_manager.get_all_active_sources()
                
                if active_sources:
                    active_source = active_sources[0]  # Single active source
                    source_type = active_source['source_type']
                    source_name = active_source['name']
                    source_path = active_source['path']
                    
                    print(f"Found active source: {source_name} ({source_type})")
                    
                    # Apply proper path mapping (NO NVR)
                    correct_working_path = get_working_path_for_source(source_type, source_name, source_path)
                    
                    if video_root != correct_working_path:
                        print(f"🔄 Correcting video_root: {video_root} → {correct_working_path}")
                        video_root = correct_working_path
                    else:
                        print(f"✅ video_root already correct: {video_root}")
                else:
                    print("⚠️ No active video source found, using video_root as-is")
                    
            except ImportError:
                print("⚠️ PathManager not available, using video_root as-is")
            except Exception as pm_error:
                print(f"⚠️ PathManager error: {pm_error}, using video_root as-is")
                
        except Exception as path_error:
            print(f"❌ Error in path mapping: {path_error}")

        # ✅ Final validation
        if not video_root or video_root.strip() == "":
            error_msg = "❌ video_root cannot be empty"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        # Basic URL validation
        if '://' in video_root or 'localhost:' in video_root:
            error_msg = f"❌ video_root cannot be a URL: {video_root}"
            print(error_msg)
            return jsonify({"error": error_msg}), 400

        print(f"📝 Final video_root for database: {video_root}")

        # ✅ FIXED: Database operations - only processing_config table
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({"error": "Database connection failed"}), 500
                
            cursor = conn.cursor()
            
            # Check if processing_config table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='processing_config'
            """)
            if not cursor.fetchone():
                return jsonify({"error": "processing_config table not found"}), 500
            
            # Add column if not exists (safe operation)
            try:
                cursor.execute("ALTER TABLE processing_config ADD COLUMN run_default_on_start INTEGER DEFAULT 1")
                print("✅ Added run_default_on_start column")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # ✅ MAIN FIX: Only insert into processing_config (no frame_settings)
            cursor.execute("""
                INSERT OR REPLACE INTO processing_config (
                    id, input_path, output_path, storage_duration, min_packing_time, 
                    max_packing_time, frame_rate, frame_interval, video_buffer, default_frame_mode, 
                    selected_cameras, db_path, run_default_on_start
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (1, video_root, output_path, default_days, min_packing_time, max_packing_time, 
                  frame_rate, frame_interval, video_buffer, "default", json.dumps(selected_cameras), 
                  DB_PATH, run_default_on_start))

            print("✅ processing_config updated successfully")

            # ✅ REMOVED: No more frame_settings table insert
            # Frame data is now stored in processing_config table only

            conn.commit()
            
            # ✅ Verify what was saved
            cursor.execute("SELECT input_path, selected_cameras, frame_rate, frame_interval FROM processing_config WHERE id = 1")
            result = cursor.fetchone()
            if result:
                saved_path, saved_cameras, saved_fr, saved_fi = result
                print(f"✅ Verified saved input_path: {saved_path}")
                print(f"✅ Verified saved cameras: {saved_cameras}")
                print(f"✅ Verified saved frame_rate: {saved_fr}, frame_interval: {saved_fi}")
            
            conn.close()
            
            print("✅ Config saved successfully")
            return jsonify({
                "message": "Configuration saved successfully",
                "saved_path": video_root,
                "saved_cameras": selected_cameras,
                "frame_settings": {
                    "frame_rate": frame_rate,
                    "frame_interval": frame_interval
                }
            }), 200
            
        except sqlite3.PermissionError as e:
            error_msg = f"Database permission denied: {str(e)}"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 403
        except sqlite3.Error as e:
            error_msg = f"Database error: {str(e)}"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 500
        except Exception as e:
            error_msg = f"Database operation failed: {str(e)}"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 500

    except Exception as e:
        # ✅ Catch-all error handler to ensure JSON response
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ CRITICAL ERROR in save_config: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

@config_bp.route('/save-general-info', methods=['POST'])
def save_general_info():
    data = request.json
    country = data.get('country')
    timezone = data.get('timezone')
    brand_name = data.get('brand_name')
    working_days = data.get('working_days', ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"])
    
    # Bản đồ ngày tiếng Việt sang tiếng Anh
    day_map = {
        'Thứ Hai': 'Monday', 'Thứ Ba': 'Tuesday', 'Thứ Tư': 'Wednesday',
        'Thứ Năm': 'Thursday', 'Thứ Sáu': 'Friday', 'Thứ Bảy': 'Saturday',
        'Chủ Nhật': 'Sunday'
    }
    
    # Chuyển đổi working_days sang tiếng Anh
    working_days_en = [day_map.get(day, day) for day in working_days]
    
    from_time = data.get('from_time', "07:00")
    to_time = data.get('to_time', "23:00")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO general_info (
                id, country, timezone, brand_name, working_days, from_time, to_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (1, country, timezone, brand_name, json.dumps(working_days_en), from_time, to_time))

        conn.commit()
        conn.close()
    except PermissionError as e:
        return jsonify({"error": f"Permission denied: {str(e)}. Check database file permissions."}), 403
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}. Ensure the database is accessible."}), 500

    print("General info saved:", data)
    return jsonify({"message": "General info saved"}), 200

# ✅ ADD to config.py - Modify save-sources endpoint to support overwrite

@config_bp.route('/save-sources', methods=['POST'])
def save_video_sources():
    """Save single active video source - ENHANCED: Support overwrite"""
    data = request.json
    sources = data.get('sources', [])
    
    if not sources:
        return jsonify({"error": "No sources provided"}), 400
    
    # Single Active Source: only process the first source
    source = sources[0]
    source_type = source.get('source_type')
    name = source.get('name')
    path = source.get('path')
    config_data = source.get('config', {})
    overwrite = source.get('overwrite', False)  # ✅ NEW: Check overwrite flag
    
    print(f"=== SAVE SOURCE: {name} ({source_type}) ===")
    print(f"Connection path: {path}")
    print(f"Config data: {config_data}")
    print(f"Overwrite mode: {overwrite}")  # ✅ NEW: Log overwrite mode
    
    if not all([source_type, name, path]):
        return jsonify({"error": "Source missing required fields"}), 400
    
    path_manager = PathManager()
    
    try:
        # ✅ ENHANCED: Handle overwrite mode
        if overwrite:
            print(f"🔄 Overwrite mode: Replacing existing source '{name}'")
            
            # Delete existing source with same name first
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM video_sources WHERE name = ?", (name,))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            print(f"✅ Deleted {deleted_count} existing source(s) with name '{name}'")
        else:
            # ✅ EXISTING: Disable all existing sources first (normal mode)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE video_sources SET active = 0")
            conn.commit()
            conn.close()
        
        # ✅ COMMON: Add new source as active
        success, message = path_manager.add_source(source_type, name, path, config_data)
        
        if success:
            # Get source ID for database operations
            source_id = path_manager.get_source_id_by_name(name)
            
            # Calculate correct working path and update processing_config (NO NVR)
            working_path = get_working_path_for_source(source_type, name, path)
            
            # Update processing_config.input_path to point to working path
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processing_config 
                SET input_path = ? 
                WHERE id = 1
            """, (working_path,))
            
            print(f"✅ Updated processing_config.input_path to: {working_path}")
            
            # Handle different source types (existing logic)
            if source_type == 'cloud':
                print(f"🔧 PROCESSING CLOUD SOURCE...")
                
                selected_folders = config_data.get('selected_folders', [])
                tree_folders = config_data.get('selected_tree_folders', [])
                all_folders = selected_folders + tree_folders
                
                if all_folders:
                    cloud_cameras = extract_cameras_from_cloud_folders(all_folders)
                    cloud_cameras = list(set(cloud_cameras))
                    
                    cursor.execute("""
                        UPDATE processing_config 
                        SET selected_cameras = ? 
                        WHERE id = 1
                    """, (json.dumps(cloud_cameras),))
                    
                    print(f"✅ Cloud cameras synced to processing_config: {cloud_cameras}")
                    
                    # Create camera directories
                    try:
                        for camera_name in cloud_cameras:
                            camera_dir = os.path.join(working_path, camera_name)
                            os.makedirs(camera_dir, exist_ok=True)
                            print(f"📁 Created camera directory: {camera_dir}")
                    except Exception as dir_error:
                        print(f"⚠️ Could not create camera directories: {dir_error}")
            
            elif source_type == 'local':
                # Auto-detect cameras from file system
                try:
                    cameras = detect_camera_folders(working_path)
                    if cameras:
                        cursor.execute("""
                            UPDATE processing_config 
                            SET selected_cameras = ? 
                            WHERE id = 1
                        """, (json.dumps(cameras),))
                        print(f"✅ Local cameras auto-selected: {cameras}")
                except Exception as camera_error:
                    print(f"Camera detection failed: {camera_error}")
                    cursor.execute("UPDATE processing_config SET selected_cameras = '[]' WHERE id = 1")
            
            conn.commit()
            conn.close()
            
            # ✅ ENHANCED RESPONSE
            action_taken = "replaced" if overwrite else "added"
            response_data = {
                "message": f"Source '{name}' {action_taken} successfully",
                "source_type": source_type,
                "connection_path": path,
                "working_path": working_path,
                "action": action_taken,
                "overwrite_mode": overwrite
            }
            
            return jsonify(response_data), 200
        else:
            return jsonify({"error": f"Failed to save source: {message}"}), 400
            
    except Exception as e:
        print(f"Failed to save sources: {str(e)}")
        return jsonify({"error": f"Failed to save sources: {str(e)}"}), 500

@config_bp.route('/test-source', methods=['POST'])  
def test_source_connection():
    """Test connectivity for local and cloud source types only"""
    try:
        # Ensure we have valid JSON request
        if not request.is_json:
            return jsonify({
                "accessible": False,
                "message": "Invalid request format - JSON required",
                "source_type": "unknown"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "accessible": False,
                "message": "No data provided",
                "source_type": "unknown"
            }), 400
        
        source_type = data.get('source_type')
        
        if not source_type:
            return jsonify({
                "accessible": False,
                "message": "source_type is required",
                "source_type": "unknown"
            }), 400
        
        # Handle different source types (NO NVR)
        if source_type == 'local':
            # Existing local path validation
            source_config = {
                'source_type': source_type,
                'path': data.get('path'),
                'config': data.get('config', {})
            }
            
            if not source_config['path']:
                return jsonify({
                    "accessible": False,
                    "message": "path is required for local sources",
                    "source_type": source_type
                }), 400
            
            path_manager = PathManager()
            is_accessible, message = path_manager.validate_source_accessibility(source_config)
            
            return jsonify({
                "accessible": is_accessible,
                "message": message,
                "source_type": source_type
            }), 200
            
        elif source_type == 'cloud':
            # ✅ Cloud connection testing + folder discovery
            from modules.sources.cloud_manager import CloudManager
            cloud_manager = CloudManager(provider='google_drive')
            result = cloud_manager.test_connection_and_discover_folders(data)
            return jsonify(result), 200
            
        else:
            return jsonify({
                "accessible": False,
                "message": f"Source type '{source_type}' not supported. Only 'local' and 'cloud' are available.",
                "source_type": source_type
            }), 400
        
    except ImportError as e:
        return jsonify({
            "accessible": False,
            "message": f"Required module not available: {str(e)}",
            "source_type": data.get('source_type', 'unknown')
        }), 500
        
    except json.JSONDecodeError:
        return jsonify({
            "accessible": False,
            "message": "Invalid JSON format",
            "source_type": "unknown"
        }), 400
        
    except Exception as e:
        return jsonify({
            "accessible": False,
            "message": f"Test failed: {str(e)}",
            "source_type": data.get('source_type', 'unknown')
        }), 500

@config_bp.route('/get-sources', methods=['GET'])
def get_video_sources():
    """Get all video sources"""
    try:
        path_manager = PathManager()
        sources = path_manager.get_all_active_sources()
        
        return jsonify({"sources": sources}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve sources: {str(e)}"}), 500

@config_bp.route('/update-source/<int:source_id>', methods=['PUT'])
def update_video_source(source_id):
    """🔧 Simple update video source - same type only, mainly for camera selection"""
    try:
        data = request.json
        path_manager = PathManager()
        
        # Get current source for validation
        current_source = path_manager.get_source_by_id(source_id)
        if not current_source:
            return jsonify({"error": f"Source with id {source_id} not found"}), 404
        
        # For now, we only support updating the config (mainly for camera selection)
        # Path and source_type changes are handled by "Change" button workflow
        new_config = data.get('config', current_source['config'])
        
        # 🔄 Update source config only
        success, message = path_manager.update_source(source_id, config=new_config)
        
        if not success:
            return jsonify({"error": message}), 400
        
        return jsonify({
            "message": message,
            "source_id": source_id,
            "updated_fields": ["config"]
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update source: {str(e)}"}), 500

@config_bp.route('/delete-source/<int:source_id>', methods=['DELETE'])
def delete_video_source(source_id):
    """🔄 Delete video source (used by Change button to reset workflow)"""
    path_manager = PathManager()
    
    try:
        # Get source info before deletion for logging
        source = path_manager.get_source_by_id(source_id)
        source_name = source.get('name', 'Unknown') if source else 'Unknown'
        
        success, message = path_manager.delete_source(source_id)
        
        if success:
            # 🧹 Clean reset processing_config 
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE processing_config 
                    SET input_path = '', selected_cameras = '[]' 
                    WHERE id = 1
                """)
                conn.commit()
                conn.close()
                
                print(f"Source '{source_name}' deleted and processing_config reset")
                
            except Exception as config_error:
                print(f"Failed to reset processing_config: {config_error}")
            
            return jsonify({
                "message": f"Source '{source_name}' removed successfully. You can now add a new source.",
                "reset": True
            }), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        return jsonify({"error": f"Failed to delete source: {str(e)}"}), 500

@config_bp.route('/toggle-source/<int:source_id>', methods=['POST'])
def toggle_source_status(source_id):
    """Toggle source active status"""
    data = request.json
    active = data.get('active', True)
    path_manager = PathManager()
    
    try:
        if active:
            # Disable all other sources first (Single Active Source)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE video_sources SET active = 0")
            conn.commit()
            conn.close()
        
        success, message = path_manager.toggle_source_status(source_id, active)
        
        if success and active:
            # Update input_path to this source
            source = path_manager.get_source_by_id(source_id)
            if source:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE processing_config 
                    SET input_path = ? 
                    WHERE id = 1
                """, (source['path'],))
                
                # Auto-detect cameras for local sources
                if source['source_type'] == 'local':
                    try:
                        cameras = detect_camera_folders(source['path'])
                        if cameras:
                            cursor.execute("""
                                UPDATE processing_config 
                                SET selected_cameras = ? 
                                WHERE id = 1
                            """, (json.dumps(cameras),))
                        else:
                            cursor.execute("""
                                UPDATE processing_config 
                                SET selected_cameras = '[]' 
                                WHERE id = 1
                            """)
                    except Exception as camera_error:
                        print(f"Camera detection failed: {camera_error}")
                        cursor.execute("""
                            UPDATE processing_config 
                            SET selected_cameras = '[]' 
                            WHERE id = 1
                        """)
                else:
                    # Clear cameras for non-local sources
                    cursor.execute("""
                        UPDATE processing_config 
                        SET selected_cameras = '[]' 
                        WHERE id = 1
                    """)
                
                conn.commit()
                conn.close()
        
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        return jsonify({"error": f"Failed to toggle source status: {str(e)}"}), 500
    
@config_bp.route('/get-processing-cameras', methods=['GET'])
def get_processing_cameras():
    """Get selected cameras from processing_config"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT selected_cameras FROM processing_config WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            selected_cameras = json.loads(result[0])
            return jsonify({
                "selected_cameras": selected_cameras,
                "count": len(selected_cameras)
            }), 200
        else:
            return jsonify({
                "selected_cameras": [],
                "count": 0
            }), 200
            
    except Exception as e:
        return jsonify({"error": f"Failed to get processing cameras: {str(e)}"}), 500

# 🔧 ADD THESE ENDPOINTS TO config.py (chèn sau existing endpoints)

@config_bp.route('/sync-cloud-cameras', methods=['POST'])
def sync_cloud_cameras():
    """🔧 Manual sync cloud cameras from active cloud source"""
    try:
        # Get active cloud source
        path_manager = PathManager()
        sources = path_manager.get_all_active_sources()
        cloud_source = None
        
        for source in sources:
            if source['source_type'] == 'cloud':
                cloud_source = source
                break
        
        if not cloud_source:
            return jsonify({"error": "No active cloud source found"}), 404
        
        print(f"🔄 Syncing cameras for cloud source: {cloud_source['name']}")
        
        # Extract cameras from cloud config
        config_data = cloud_source.get('config', {})
        selected_folders = config_data.get('selected_folders', [])
        tree_folders = config_data.get('selected_tree_folders', [])
        all_folders = selected_folders + tree_folders
        
        if all_folders:
            cloud_cameras = extract_cameras_from_cloud_folders(all_folders)
            cloud_cameras = list(set(cloud_cameras))  # Remove duplicates
            
            print(f"🎥 Generated cloud cameras: {cloud_cameras}")
            
            # Update processing_config
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processing_config 
                SET selected_cameras = ? 
                WHERE id = 1
            """, (json.dumps(cloud_cameras),))
            conn.commit()
            conn.close()
            
            print(f"✅ Cloud cameras synced to processing_config")
            
            return jsonify({
                "success": True,
                "message": f"Synced {len(cloud_cameras)} cameras from cloud source",
                "cameras": cloud_cameras,
                "source_name": cloud_source['name']
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "No folders found in cloud source config"
            }), 400
            
    except Exception as e:
        print(f"❌ Error syncing cloud cameras: {e}")
        return jsonify({"error": f"Failed to sync cloud cameras: {str(e)}"}), 500

@config_bp.route('/refresh-cameras', methods=['POST'])
def refresh_cameras():
    """🔄 Refresh cameras based on active source type"""
    try:
        # Get active source
        path_manager = PathManager()
        sources = path_manager.get_all_active_sources()
        
        if not sources:
            return jsonify({
                "success": False,
                "message": "No active source found",
                "cameras": []
            }), 404
        
        active_source = sources[0]  # Single active source
        source_type = active_source['source_type']
        source_name = active_source['name']
        
        print(f"🔄 Refreshing cameras for {source_type} source: {source_name}")
        
        cameras = []
        
        if source_type == 'local':
            # Local: Scan directories
            working_path = active_source['path']
            if os.path.exists(working_path):
                detected_cameras = detect_camera_folders(working_path)
                cameras = detected_cameras
                print(f"📁 Local cameras detected: {cameras}")
            else:
                print(f"⚠️ Local path not found: {working_path}")
                
        elif source_type == 'cloud':
            # Cloud: Extract from config
            config_data = active_source.get('config', {})
            selected_folders = config_data.get('selected_folders', [])
            tree_folders = config_data.get('selected_tree_folders', [])
            all_folders = selected_folders + tree_folders
            
            if all_folders:
                cameras = extract_cameras_from_cloud_folders(all_folders)
                cameras = list(set(cameras))  # Remove duplicates
                print(f"☁️ Cloud cameras extracted: {cameras}")
            else:
                # Also check existing selected_cameras in config
                cameras = config_data.get('selected_cameras', [])
                print(f"☁️ Using existing cloud cameras: {cameras}")
        
        # Update processing_config if cameras found
        if cameras:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processing_config 
                SET selected_cameras = ? 
                WHERE id = 1
            """, (json.dumps(cameras),))
            conn.commit()
            conn.close()
            
            print(f"✅ Updated processing_config with {len(cameras)} cameras")
        
        return jsonify({
            "success": True,
            "message": f"Refreshed {len(cameras)} cameras from {source_type} source",
            "cameras": cameras,
            "source_type": source_type,
            "source_name": source_name
        }), 200
        
    except Exception as e:
        print(f"❌ Error refreshing cameras: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to refresh cameras: {str(e)}",
            "cameras": []
        }), 500

@config_bp.route('/camera-status', methods=['GET'])
def get_camera_status():
    """📊 Get comprehensive camera status for debugging"""
    try:
        # Get processing_config cameras
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT selected_cameras, input_path FROM processing_config WHERE id = 1")
        result = cursor.fetchone()
        conn.close()
        
        processing_cameras = []
        input_path = ""
        
        if result:
            selected_cameras, input_path = result
            try:
                processing_cameras = json.loads(selected_cameras) if selected_cameras else []
            except:
                processing_cameras = []
        
        # Get active sources
        path_manager = PathManager()
        active_sources = path_manager.get_all_active_sources()
        
        # Get source-specific camera info
        source_cameras = []
        source_info = None
        
        if active_sources:
            source = active_sources[0]
            source_info = {
                "name": source['name'],
                "type": source['source_type'],
                "path": source['path']
            }
            
            if source['source_type'] == 'cloud':
                config_data = source.get('config', {})
                selected_folders = config_data.get('selected_folders', [])
                tree_folders = config_data.get('selected_tree_folders', [])
                all_folders = selected_folders + tree_folders
                
                if all_folders:
                    source_cameras = extract_cameras_from_cloud_folders(all_folders)
                    source_cameras = list(set(source_cameras))
                
                source_info.update({
                    "folders_count": len(all_folders),
                    "legacy_folders": len(selected_folders),
                    "tree_folders": len(tree_folders)
                })
                
            elif source['source_type'] == 'local':
                working_path = source['path']
                if os.path.exists(working_path):
                    source_cameras = detect_camera_folders(working_path)
        
        # Check sync status
        cameras_synced = set(processing_cameras) == set(source_cameras)
        
        return jsonify({
            "processing_config": {
                "cameras": processing_cameras,
                "camera_count": len(processing_cameras),
                "input_path": input_path
            },
            "active_source": source_info,
            "source_cameras": {
                "cameras": source_cameras,
                "camera_count": len(source_cameras)
            },
            "sync_status": {
                "cameras_synced": cameras_synced,
                "needs_sync": not cameras_synced
            },
            "recommendations": {
                "action_needed": "sync_cloud_cameras" if source_info and source_info['type'] == 'cloud' and not cameras_synced else None,
                "message": "Cameras not synced - use /sync-cloud-cameras endpoint" if not cameras_synced else "Cameras are in sync"
            },
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get camera status: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500
    
# Thêm vào cuối file config.py:

if __name__ == "__main__":
    try:
        print("🚀 Starting VTrack Config Server...")
        
        # Initialize app và config
        app, db_path, logger = init_app_and_config()
        
        # Register blueprint
        app.register_blueprint(config_bp, url_prefix='/api/config')
        
        # Import và register cloud blueprint nếu có
        try:
            from modules.sources.cloud_endpoints import cloud_bp
            app.register_blueprint(cloud_bp, url_prefix='/api/cloud')
            print("✅ Cloud endpoints registered")
        except ImportError:
            print("⚠️  Cloud endpoints not available")
        # Import và register sync blueprint
        try:
            from modules.sources.sync_endpoints import sync_bp
            app.register_blueprint(sync_bp, url_prefix='/api')
            print("✅ Sync endpoints registered")
        except ImportError as e:
            print(f"⚠️  Sync endpoints not available: {e}")

        
        # Initialize database manager
        try:
            from database import get_db_manager
            db_manager = get_db_manager()
            config_manager = init_config(db_manager)
            print("✅ Database manager initialized")
        except Exception as e:
            print(f"⚠️  Database manager error: {e}")
        
        # Add simple test endpoint
        @app.route('/api/test', methods=['GET'])
        def test():
            return jsonify({
                'status': 'ok',
                'message': 'VTrack Config Server is running!',
                'database': db_path,
                'timestamp': datetime.now().isoformat()
            })
        
        # Server info
        print(f"✅ Database: {db_path}")
        print(f"🌐 Server will start on: http://localhost:8080")
        print(f"🔧 Test URL: http://localhost:8080/api/test")
        print(f"📡 API Base: http://localhost:8080/api/config/")
        print("="*50)
        
        # Start server
        app.run(
            host='0.0.0.0',  # Accept từ mọi IP
            port=8080, 
            debug=True,      # Enable debug mode
            use_reloader=False  # Tránh restart 2 lần
        )
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()