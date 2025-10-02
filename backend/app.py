import os
import sys
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
from dotenv import load_dotenv
import logging
import signal
import threading
import socket
import atexit
import sqlite3
import queue
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Load environment variables
load_dotenv()

# ==================== DISABLE VERBOSE LOGGING ====================
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '3'
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'
os.environ['PYTHONWARNINGS'] = 'ignore'

import warnings
warnings.filterwarnings('ignore')

# Configure third-party library logging levels
import logging
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('modules.licensing.repositories').setLevel(logging.INFO)

# ==================== IMPORT CORE MODULES ====================
from modules.config.logging_config import setup_logging, get_logger
from modules.config.config import config_bp, init_app_and_config
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.program import program_bp, scheduler
from modules.query.query import query_bp
from blueprints.cutter_bp import cutter_bp
from blueprints.hand_detection_bp import hand_detection_bp
from blueprints.simple_hand_detection_bp import simple_hand_detection_bp
from blueprints.qr_detection_bp import qr_detection_bp
from blueprints.roi_bp import roi_bp
# Removed analysis_streaming_bp - replaced with simple_hand_detection_bp
from modules.config.routes.steps.step4_roi_routes import step4_roi_bp
from modules.sources.cloud_endpoints import cloud_bp
from modules.sources.cloud_lazy_folder_routes import lazy_folder_bp
from modules.sources.sync_endpoints import sync_bp
from modules.sources.pydrive_downloader import pydrive_downloader

# ==================== IMPORT LICENSE MODULES ====================
try:
    from modules.license.license_checker import LicenseChecker
    LICENSE_SYSTEM_AVAILABLE = True
    logger_temp = logging.getLogger("app")
    logger_temp.info("✅ License system loaded")
except ImportError as e:
    LICENSE_SYSTEM_AVAILABLE = False
    logger_temp = logging.getLogger("app")
    logger_temp.warning(f"⚠️ License system not available: {e}")

# ==================== IMPORT ACCOUNT MODULE ====================
try:
    from modules.account.account import check_user_status
    ACCOUNT_SYSTEM_AVAILABLE = True
    logger_temp.info("✅ Account system loaded")
except ImportError as e:
    ACCOUNT_SYSTEM_AVAILABLE = False
    logger_temp.warning(f"⚠️ Account system not available: {e}")

# Setup logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
setup_logging(BASE_DIR, app_name="app", log_level=logging.INFO)
logger = logging.getLogger("app")

# ==================== CLOUD FUNCTIONS INTEGRATION ====================
# Set Cloud Function URLs
os.environ.setdefault('CLOUD_PAYMENT_URL', 'https://asia-southeast1-v-track-payments.cloudfunctions.net/create-payment')
os.environ.setdefault('CLOUD_WEBHOOK_URL', 'https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler')
os.environ.setdefault('CLOUD_LICENSE_URL', 'https://asia-southeast1-v-track-payments.cloudfunctions.net/license-service')

# Import payment integration
PAYMENT_INTEGRATION_AVAILABLE = False
try:
    from modules.payments.cloud_function_client import get_cloud_client
    from modules.payments.payment_routes import payment_bp
    PAYMENT_INTEGRATION_AVAILABLE = True
    logger.info("✅ Cloud payment integration loaded")
except ImportError as e:
    logger.warning(f"⚠️ Payment integration not available: {e}")
except Exception as e:
    logger.error(f"❌ Payment integration error: {e}")

# ==================== FLASK APP INITIALIZATION ====================
app, DB_PATH, logger = init_app_and_config()

# ==================== LICENSE BACKGROUND THREAD ====================
class LicenseThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="LicenseChecker")
        self.result_queue = queue.Queue()
        self._stop_event = threading.Event()
        
    def run(self):
        """License check in background thread"""
        try:
            logger.info("🔑 Starting background license check...")
            license_checker = LicenseChecker()
            result = license_checker.startup_license_check()
            
            # Handle different license states WITHOUT UI BLOCKING
            if result['action'] == 'show_license_input':
                self.result_queue.put({
                    'status': 'requires_license',
                    'message': 'License key required - visit /payment to activate'
                })
                logger.warning("License key required")
                
            elif result['action'] == 'show_expiry_warning':
                days_remaining = result.get('days_remaining', 0)
                self.result_queue.put({
                    'status': 'expiring',
                    'message': f'License expires in {days_remaining} days'
                })
                logger.warning(f"License expires in {days_remaining} days")
                
            elif result['action'] == 'show_error':
                self.result_queue.put({
                    'status': 'error',
                    'message': f"License error: {result['message']}"
                })
                logger.error(f"License error: {result['message']}")
                
            elif result['action'] == 'continue':
                self.result_queue.put({
                    'status': 'valid',
                    'message': 'License valid'
                })
                logger.info("License check passed")
            
            else:
                self.result_queue.put({
                    'status': 'unknown',
                    'message': f"Unknown license action: {result['action']}"
                })
                
        except Exception as e:
            logger.error(f"License check failed: {e}")
            self.result_queue.put({
                'status': 'error',
                'message': f'License check error: {str(e)}'
            })
    
    def stop(self):
        self._stop_event.set()
    
    def get_result(self, timeout=0.1):
        """Get license result if available"""
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None

# Global license thread
license_thread = None
license_status = {'initialized': False, 'status': 'checking', 'message': 'License check in progress...'}

def initialize_license_system():
    """Non-blocking license initialization"""
    global license_thread, license_status
    
    if not LICENSE_SYSTEM_AVAILABLE:
        logger.warning("License system not available - skipping")
        license_status.update({
            'initialized': True, 
            'status': 'disabled', 
            'message': 'License system disabled'
        })
        return True
    
    # Start license check in background
    license_thread = LicenseThread()
    license_thread.start()
    
    logger.info("🔑 License check started in background")
    return True

# ==================== WEBAPP TEMPLATE CONFIGURATION ====================
# Backend API only - webapp handled by React frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from flask_session import Session
import secrets

# Configure session for OAuth compatibility
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_urlsafe(32)),
    SESSION_COOKIE_NAME='vtrack_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=os.path.join(BASE_DIR, 'flask_session'),
    OAUTH_INSECURE_TRANSPORT=True,
)

Session(app)

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin", "x-timezone-version", "x-timezone-detection", "x-client-offset", "x-client-timezone", "x-client-dst"],
        "supports_credentials": True,
    }
})

@app.before_request
def make_session_permanent():
    from flask import session
    session.permanent = True

logger.info("🔑 Session configuration applied")

# ==================== REGISTER BLUEPRINTS ====================
# Core modules
app.register_blueprint(program_bp, url_prefix='/api')
app.register_blueprint(config_bp, url_prefix='/api/config')
app.register_blueprint(step4_roi_bp)  # ROI configuration endpoints
app.register_blueprint(query_bp)
app.register_blueprint(cutter_bp)
app.register_blueprint(hand_detection_bp)
app.register_blueprint(simple_hand_detection_bp, url_prefix='/api/hand-detection')
app.register_blueprint(qr_detection_bp, url_prefix='/api/qr-detection')
app.register_blueprint(roi_bp)
# Removed complex streaming blueprint - now using simple_hand_detection_bp

# Cloud and sync modules
try:
    app.register_blueprint(cloud_bp, name='cloud_endpoints')
    logger.info("✅ Cloud endpoints registered")
except ValueError as e:
    logger.warning(f"⚠️ Cloud blueprint already registered: {e}")

try:
    app.register_blueprint(lazy_folder_bp, url_prefix='/api/cloud')
    logger.info("✅ Lazy folder endpoints registered")
except ValueError as e:
    logger.warning(f"⚠️ Lazy folder blueprint already registered: {e}")

try:
    app.register_blueprint(sync_bp, url_prefix='/api/sync')
    logger.info("✅ Sync endpoints registered")
except (ValueError, ImportError) as e:
    logger.warning(f"⚠️ Sync endpoints issue: {e}")

# Payment integration
if PAYMENT_INTEGRATION_AVAILABLE:
    try:
        cloud_client = get_cloud_client()
        app.register_blueprint(payment_bp)
        logger.info("✅ Payment blueprint registered")
        
        # Test connectivity
        connection_test = cloud_client.test_connection()
        if connection_test.get('success'):
            logger.info(f"✅ Cloud connectivity verified ({connection_test.get('response_time_ms', 0)}ms)")
        else:
            logger.warning(f"⚠️ Cloud connectivity issues: {connection_test.get('error')}")
    except Exception as e:
        logger.error(f"❌ Payment integration failed: {e}")
        PAYMENT_INTEGRATION_AVAILABLE = False

# ==================== API BACKEND ONLY ====================
# Legacy webapp routes removed - frontend handled by React app on port 3000
# Backend serves API endpoints only

# Quick API endpoint for latest user (development)
@app.route('/api/user/latest', methods=['GET', 'OPTIONS'])
def get_latest_user_wrapper():
    from flask_cors import cross_origin
    
    def get_latest_user():
        """Get latest user from database with simple avatar download"""
        try:
            from modules.db_utils import get_db_connection
            from modules.utils.simple_avatar import avatar_downloader
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT gmail_address, display_name, photo_url, last_login 
                FROM user_profiles 
                ORDER BY last_login DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                gmail_address, display_name, photo_url, last_login = row
                
                # Download avatar to frontend public folder
                local_avatar_path = avatar_downloader.download_avatar(gmail_address, photo_url)
                
                return {
                    'success': True,
                    'user': {
                        'gmail_address': gmail_address,
                        'display_name': display_name, 
                        'photo_url': local_avatar_path,
                        'original_photo_url': photo_url,  # Keep original for reference
                        'last_login': last_login
                    }
                }
            else:
                return {'success': False, 'message': 'No users found'}
                
        except Exception as e:
            logger.error(f"Error fetching latest user: {e}")
            return {'success': False, 'message': str(e)}
    
    return cross_origin(origins=['http://localhost:3000'], supports_credentials=True)(get_latest_user)()

# User logout API endpoint
@app.route('/api/user/logout', methods=['POST', 'OPTIONS'])
def logout_user():
    """Logout user - clear session and authentication data"""
    from flask import session, request
    from flask_cors import cross_origin
    
    try:
        # Clear Flask session if exists
        if 'user_id' in session:
            session.pop('user_id', None)
        if 'user_email' in session:
            session.pop('user_email', None)
        if 'authenticated' in session:
            session.pop('authenticated', None)
            
        # Clear all session data
        session.clear()
        
        # Clear user profile from database to prevent auto-authentication
        try:
            from modules.db_utils.safe_connection import safe_db_connection
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get the latest user before deleting
                cursor.execute("""
                    SELECT gmail_address FROM user_profiles 
                    ORDER BY last_login DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    user_email = row[0]
                    
                    # Delete user profile to ensure complete logout
                    cursor.execute("DELETE FROM user_profiles WHERE gmail_address = ?", (user_email,))
                    
                    # Also clear any OAuth credentials/tokens if stored
                    # cursor.execute("DELETE FROM oauth_tokens WHERE user_email = ?", (user_email,))
                    
                    logger.info(f"🗑️ User profile deleted for complete logout: {user_email}")
                else:
                    logger.info("ℹ️ No user profile found to delete")
                    
        except Exception as db_error:
            logger.error(f"❌ Database cleanup error during logout: {db_error}")
            # Continue with logout even if DB cleanup fails
        
        logger.info("✅ Complete user logout successful")
        
        return cross_origin(
            origins=['http://localhost:3000', 'http://localhost:3003'], 
            supports_credentials=True
        )(lambda: {
            'success': True,
            'message': 'Logged out successfully - user profile cleared'
        })()
        
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        return cross_origin(
            origins=['http://localhost:3000', 'http://localhost:3003'], 
            supports_credentials=True
        )(lambda: {
            'success': False,
            'message': 'Logout failed',
            'error': str(e)
        })()

# Static file serving for cached avatars
@app.route('/static/avatars/<filename>')
def serve_cached_avatar(filename):
    """Serve cached avatar files"""
    from flask import send_from_directory
    import os
    
    avatar_dir = os.path.join(os.path.dirname(__file__), 'static', 'avatars')
    
    # Security: prevent directory traversal
    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400
        
    return send_from_directory(avatar_dir, filename)

# ==================== PAYMENT REDIRECT ROUTES ====================
# FIXED: Unified payment redirect handling for both success and cancel scenarios

@app.route('/payment/redirect')
def payment_redirect():
    """Primary auto-close payment popup for both success and cancel"""
    logger.info("🔄 Payment redirect triggered - auto-closing popup")
    return """
    <script>
        // Try multiple close methods for maximum compatibility
        try {
            if (window.opener) {
                // Popup window - close immediately
                window.close();
            } else if (window.parent !== window) {
                // Iframe - notify parent
                window.parent.postMessage('payment_completed', '*');
            } else {
                // Fallback - redirect to main page
                window.location.href = '/';
            }
        } catch (error) {
            // Ultimate fallback
            window.location.href = '/';
        }
    </script>
    """

@app.route('/cancel')
def payment_cancel():
    """Fallback route for PayOS cancel redirects (legacy compatibility)"""
    logger.info("⚠️ Legacy /cancel route accessed - redirecting to unified handler")
    
    # OPTION 1: Redirect to unified handler
    return redirect('/payment/redirect')
    
    # OPTION 2: Direct auto-close (uncomment if you prefer direct handling)
    # return """
    # <script>
    #     if (window.opener) {
    #         window.close();
    #     } else {
    #         window.location.href = '/';
    #     }
    # </script>
    # """

# Note: Removed /payment/success route as it's no longer needed
# PayOS now redirects both success and cancel to /payment/redirect

# ==================== API ENDPOINTS ====================
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        health_data = {
            'status': 'healthy',
            'service': 'V_Track Desktop Backend',
            'version': '2.1.0',
            'timestamp': datetime.now().isoformat(),
            'modules': {
                'computer_vision': 'enabled',
                'batch_processing': 'enabled',
                'cloud_sync': 'enabled',
                'payment_system': 'enabled' if PAYMENT_INTEGRATION_AVAILABLE else 'disabled',
                'license_management': 'enabled' if PAYMENT_INTEGRATION_AVAILABLE else 'disabled'
            },
            'payment_routes': {
                'unified_redirect': '/payment/redirect',
                'legacy_cancel': '/cancel',
                'redirect_strategy': 'unified'
            }
        }
        
        # Check cloud functions if available
        if PAYMENT_INTEGRATION_AVAILABLE:
            try:
                cloud_client = get_cloud_client()
                cloud_health = cloud_client.health_check()
                health_data['cloud_functions'] = {
                    'configured': True,
                    'healthy': cloud_health.get('overall_status') == 'healthy',
                    'services_status': cloud_health.get('services_healthy', '0/0')
                }
                if cloud_health.get('overall_status') != 'healthy':
                    health_data['status'] = 'degraded'
            except Exception as e:
                health_data['cloud_functions'] = {
                    'configured': True,
                    'healthy': False,
                    'error': str(e)
                }
                health_data['status'] = 'degraded'
        else:
            health_data['cloud_functions'] = {
                'configured': False,
                'healthy': False,
                'note': 'Payment integration not available'
            }
        
        status_code = 200 if health_data['status'] == 'healthy' else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'service': 'V_Track Desktop Backend',
            'version': '2.1.0',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.route('/api/system-info', methods=['GET'])
def system_info():
    """System information API"""
    return jsonify({
        'service': 'V_Track Desktop Backend',
        'version': '2.1.0',
        'status': 'running',
        'features': [
            'Computer Vision Processing',
            'Video File Batch Processing',
            'Cloud Storage Sync',
            'Payment Processing' if PAYMENT_INTEGRATION_AVAILABLE else 'Payment Processing (Disabled)',
            'License Management' if PAYMENT_INTEGRATION_AVAILABLE else 'License Management (Disabled)'
        ],
        'endpoints': {
            'health': '/health',
            'payment': '/payment' if PAYMENT_INTEGRATION_AVAILABLE else None,
            'settings': '/settings',
            'analytics': '/analytics'
        },
        'payment_configuration': {
            'unified_redirect_url': '/payment/redirect',
            'legacy_cancel_url': '/cancel',
            'strategy': 'unified_redirect_with_fallback'
        }
    })

@app.route('/api/license-status', methods=['GET'])
def get_license_status():
    """Get current license status"""
    global license_thread, license_status
    
    # Check for license result if thread is running
    if license_thread and license_thread.is_alive():
        result = license_thread.get_result()
        if result:
            license_status.update({
                'initialized': True,
                'status': result['status'],
                'message': result['message']
            })
    
    return jsonify(license_status)

@app.route('/api/camera-configurations', methods=['GET', 'OPTIONS'])
def get_camera_configurations():
    """Get camera configurations from database"""
    try:
        from flask_cors import cross_origin

        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 200

        cameras = []

        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Get camera configurations from active sources only
            cursor.execute("""
                SELECT cc.camera_name, cc.folder_path, cc.is_selected,
                       cc.stream_url, cc.resolution, cc.codec,
                       vs.source_type, vs.name as source_name
                FROM camera_configurations cc
                JOIN video_sources vs ON cc.source_id = vs.id
                WHERE vs.active = 1 AND cc.is_selected = 1
                ORDER BY cc.camera_name
            """)

            results = cursor.fetchall()

            for row in results:
                camera_name, folder_path, is_selected, stream_url, resolution, codec, source_type, source_name = row

                cameras.append({
                    'name': camera_name,
                    'path': camera_name,  # Just use camera name instead of full folder path
                    'stream_url': stream_url,
                    'resolution': resolution,
                    'codec': codec,
                    'source_type': source_type,
                    'source_name': source_name,
                    'is_selected': bool(is_selected)
                })

        return jsonify({
            'success': True,
            'cameras': cameras,
            'count': len(cameras)
        }), 200

    except Exception as e:
        logger.error(f"Error getting camera configurations: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'cameras': []
        }), 500

@app.route('/api/processing-status', methods=['GET', 'OPTIONS'])
def get_processing_status():
    """Get current file processing status and progress"""
    try:
        if request.method == 'OPTIONS':
            return jsonify({'success': True}), 200

        # Mock processing status for now
        # In production, this would read from actual processing state
        processing_status = {
            'is_processing': True,
            'current_file': 'DonggoiN_80cm25.mov',
            'processed_files': 47,
            'total_files': 100,
            'progress_percentage': 47.0,
            'processing_program': 'First Run',
            'estimated_time_remaining': '15 minutes',
            'current_camera': 'Cloud_Cam1',
            'started_at': '2025-09-29T08:00:00Z'
        }

        return jsonify({
            'success': True,
            'processing_status': processing_status
        }), 200

    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'processing_status': {
                'is_processing': False,
                'current_file': None,
                'processed_files': 0,
                'total_files': 0,
                'progress_percentage': 0.0
            }
        }), 500

# ==================== APPLICATION LIFECYCLE ====================
def _get_system_tz():
    """Get system timezone from database configuration."""
    try:
        from modules.utils.simple_timezone import get_system_timezone_from_db
        return ZoneInfo(get_system_timezone_from_db())
    except:
        # Fallback to UTC if helper not available during shutdown
        return timezone.utc

def exit_handler():
    """Graceful shutdown handler"""
    try:
        with safe_db_connection(timeout=5) as conn:
            cursor = conn.cursor()
            last_stop_time = datetime.now(tz=_get_system_tz()).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT OR REPLACE INTO program_status (key, value)
                VALUES ('last_stop_time', ?)
            """, (last_stop_time,))
        logger.info("Application stopped gracefully")
    except Exception as e:
        logger.error(f"Error saving last_stop_time: {e}")

atexit.register(exit_handler)

def is_port_in_use(port):
    """Check if port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return False
        except OSError:
            return True

_shutdown_in_progress = False

def signal_handler(sig, frame):
    """Handle shutdown signals - with license thread cleanup"""
    global _shutdown_in_progress, license_thread
    
    if _shutdown_in_progress:
        print("\nForced shutdown...")
        os._exit(1)
    
    _shutdown_in_progress = True
    print("\nShutting down gracefully... (Press Ctrl+C again to force)")
    
    try:
        logger.info("Received shutdown signal, stopping application...")
        
        # Stop license thread if running
        if license_thread and license_thread.is_alive():
            print("🔑 Stopping license thread...")
            license_thread.stop()
            license_thread.join(timeout=2)
            if license_thread.is_alive():
                logger.warning("License thread did not stop gracefully")
        
        # Stop scheduler
        if 'scheduler' in globals() and scheduler is not None:
            try:
                if hasattr(scheduler, 'stop'):
                    scheduler.stop()
                    logger.info("Scheduler stopped")
                else:
                    logger.warning("Scheduler stop method not found")
            except Exception as e:
                logger.warning(f"Scheduler stop error: {e}")
        
        # Wait for threads to finish
        main_thread = threading.current_thread()
        for t in threading.enumerate():
            if t != main_thread and t.is_alive():
                try:
                    t.join(timeout=2)
                except:
                    pass
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def validate_pricing_integration():
    """Validate pricing integration on startup"""
    try:
        logger.info("🔍 Validating pricing integration...")
        
        from modules.pricing.cloud_pricing_client import get_cloud_pricing_client
        pricing_client = get_cloud_pricing_client()
        
        # Test connection
        connection_result = pricing_client.test_connection()
        if not connection_result.get('connected'):
            logger.warning(f"⚠️ Pricing service connection failed: {connection_result.get('error')}")
            return False
        
        # Test package fetching
        pricing_data = pricing_client.fetch_pricing_on_startup()
        if not pricing_data.get('success'):
            logger.error(f"❌ Cannot fetch packages: {pricing_data.get('error')}")
            return False
        
        packages = pricing_data.get('packages', {})
        logger.info(f"✅ Pricing integration validated: {len(packages)} packages available")
        logger.info(f"📦 Available packages: {list(packages.keys())}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Pricing validation failed: {str(e)}")
        return False

def initialize_auto_sync():
    """Initialize auto-sync for cloud sources"""
    def startup_sync():
        try:
            import time
            time.sleep(2)
            logger.info("🚀 Starting auto-sync for enabled cloud sources...")
            result = pydrive_downloader.auto_start_all_enabled_sources()
            if result.get('success'):
                logger.info(f"✅ Auto-sync completed: {result.get('started_count', 0)} sources started")
            else:
                logger.error(f"❌ Auto-sync failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"❌ Auto-sync startup failed: {e}")
    
    threading.Thread(target=startup_sync, daemon=True).start()
    logger.info("🔄 Auto-sync initialization started")

# ==================== APPLICATION STARTUP ====================
if __name__ == "__main__":
    port = 8080
    
    # Check port availability
    if is_port_in_use(port):
        logger.error(f"Port {port} is already in use!")
        sys.exit(1)
    
    logger.info(f"Starting V_Track Desktop Application on port {port}")
    
    # Initialize license system (non-blocking)
    license_ok = initialize_license_system()
    if not license_ok:
        logger.error("License initialization failed - continuing anyway")
    
    # Validate pricing integration
    pricing_ok = validate_pricing_integration()
    if not pricing_ok:
        print("⚠️ Warning: Pricing service integration issues detected")
    else:
        print("💰 Pricing integration validated successfully")
    
    # Display startup information
    print("🚀 V_Track Desktop App Starting...")
    print(f"📡 Server: http://0.0.0.0:{port}")
    print("🔧 Core Features:")
    print("   ✅ Computer Vision Processing")
    print("   ✅ Video File Batch Processing")
    print("   ✅ Cloud Storage Sync")
    
    if PAYMENT_INTEGRATION_AVAILABLE:
        try:
            cloud_client = get_cloud_client()
            connection_test = cloud_client.test_connection()
            
            if connection_test.get('success'):
                print("   ✅ Cloud Payment Processing")
                print("   ✅ License Management System")
                print(f"\n💳 Payment System:")
                print(f"   📱 Payment UI: http://0.0.0.0:{port}/payment")
                print(f"   🧪 Cloud Test: http://0.0.0.0:{port}/api/test-cloud")
                print(f"   ⚡ Response Time: {connection_test.get('response_time_ms', 0)}ms")
                print(f"   🔄 Unified Redirects: /payment/redirect")
                print(f"   🔙 Legacy Fallback: /cancel")
            else:
                print("   ⚠️  Cloud Payment Processing (Connection Issues)")
                print("   ⚠️  License Management (Degraded)")
        except Exception as e:
            print("   ❌ Cloud Payment Processing (Error)")
            print("   ❌ License Management (Failed)")
            logger.error(f"Cloud integration error: {e}")
    else:
        print("   ❌ Payment Processing (Not Available)")
        print("   ❌ License Management (Not Available)")
    
    print(f"\n📍 Main Pages:")
    print(f"   🏠 Dashboard: http://0.0.0.0:{port}/")
    print(f"   💳 Payment: http://0.0.0.0:{port}/payment")
    print(f"   ⚙️  Settings: http://0.0.0.0:{port}/settings")
    print(f"   📊 Analytics: http://0.0.0.0:{port}/analytics")
    print(f"   🏥 Health: http://0.0.0.0:{port}/health")
    print(f"   🔑 License Status: http://0.0.0.0:{port}/api/license-status")
    if PAYMENT_INTEGRATION_AVAILABLE:
        print(f"   💰 Pricing API: http://0.0.0.0:{port}/api/payment/packages")
    
    # API Backend only - React frontend on port 3000
    print(f"\n🔗 Frontend: React app running on http://localhost:3000")
    print(f"🔗 Backend API: Flask running on http://localhost:8080")
    
    print(f"\n⚡ Shutdown: Ctrl+C (immediate response)")
    
    # Initialize auto-sync
    initialize_auto_sync()
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Application error: {e}")
    finally:
        print("🔚 Application terminated")
        logger.info("Application terminated")