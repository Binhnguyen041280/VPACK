import os
import sys
from flask_cors import CORS
from dotenv import load_dotenv
import os
load_dotenv()

# ==================== TẮT TẤT CẢ LOGS TRƯỚC KHI IMPORT ====================
# TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_LOGGING'] = 'ERROR'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Google/Abseil logs (MediaPipe)
os.environ['GLOG_minloglevel'] = '3'
os.environ['GLOG_logtostderr'] = '0'
os.environ['GLOG_stderrthreshold'] = '3'
os.environ['GLOG_v'] = '0'

# MediaPipe logs
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'
os.environ['MEDIAPIPE_LOG_LEVEL'] = '3'

# OpenCV logs
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

# Tắt C++ warnings
os.environ['PYTHONWARNINGS'] = 'ignore'

# Redirect stderr để tắt hoàn toàn C++ logs
import warnings
warnings.filterwarnings('ignore')

# Tắt absl logging
try:
    import absl.logging
    absl.logging.set_verbosity(absl.logging.ERROR)
    absl.logging.set_stderrthreshold(absl.logging.ERROR)
except ImportError:
    pass

# ==================== IMPORT MODULES ====================
from modules.config.logging_config import setup_logging, get_logger
from datetime import datetime
import logging
import signal
import threading
import socket
import atexit
import sqlite3
from datetime import datetime, timedelta, timezone

# Thiết lập logging từ logging_config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
setup_logging(BASE_DIR, app_name="app", log_level=logging.DEBUG)
logger = logging.getLogger("app")

# Import các modules khác
from modules.config.config import config_bp, init_app_and_config
from modules.scheduler.program import program_bp
from modules.query.query import query_bp
from blueprints.cutter_bp import cutter_bp
from blueprints.hand_detection_bp import hand_detection_bp
from blueprints.qr_detection_bp import qr_detection_bp
from blueprints.roi_bp import roi_bp
from modules.scheduler.program import scheduler  # Import BatchScheduler

# 🆕 NEW: Import cloud endpoints blueprint
from modules.sources.cloud_endpoints import cloud_bp
# 🆕 NEW: Import sync endpoints blueprint
from modules.sources.sync_endpoints import sync_bp
# 🆕 NEW: Import pydrive downloader for auto-start
from modules.sources.pydrive_downloader import pydrive_downloader

# 🆕 NEW: Import ZaloPay payment modules
from modules.payments.zalopay_handler import zalopay_bp
from modules.webhooks.zalopay_webhook import webhook_bp
from modules.licensing.license_models import init_license_db
from flask import Blueprint

# Create license management blueprint
license_bp = Blueprint('license', __name__)

# Khởi tạo Flask app và DB path từ config
app, DB_PATH, logger = init_app_and_config()

# Initialize license database
try:
    init_license_db()
    logger.info("License database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize license database: {str(e)}")
from flask_session import Session

# 🔧 FIXED: OAuth-Compatible Session Configuration
import secrets
app.config.update(
    # OAuth Session Fix - CRITICAL for Google OAuth
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_urlsafe(32)),
    SESSION_COOKIE_NAME='vtrack_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE='Lax',  # CRITICAL for OAuth redirects
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),  # Longer for OAuth
    
    # Session storage
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=os.path.join(BASE_DIR, 'flask_session'),
    
    # OAuth specific
    OAUTH_INSECURE_TRANSPORT=True,  # Only for development
)

# Initialize session
Session(app)

# ✅ SINGLE CORS Configuration - No duplicates
CORS(app, 
     resources={
         r"/*": {
             "origins": [
                 "http://localhost:3000", 
                 "http://127.0.0.1:3000"
             ],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": [
                 "Content-Type", 
                 "Authorization",
                 "X-Requested-With",
                 "Accept",
                 "Origin",
                 "Cache-Control",      # ✅ INCLUDE: Cache-Control header
                 "Pragma",             # ✅ INCLUDE: For cache control
                 "Expires"             # ✅ INCLUDE: For cache control
             ],
             "supports_credentials": True,
             "expose_headers": [
                 "Content-Type", 
                 "Authorization",
                 "Cache-Control",      # ✅ EXPOSE: Cache-Control header
                 "Pragma",
                 "Expires"
             ]
         }
     })

# ❌ REMOVED: @app.after_request to avoid duplicate headers

# 🔧 CRITICAL: Make sessions permanent for OAuth
@app.before_request
def make_session_permanent():
    from flask import session
    session.permanent = True

logger.info("🔑 OAuth-compatible session configuration applied")
logger.info("✅ Single CORS configuration with Cache-Control support applied")

# Đăng ký các Blueprint
app.register_blueprint(program_bp)
app.register_blueprint(config_bp, url_prefix='/api/config')
app.register_blueprint(query_bp)
app.register_blueprint(cutter_bp)
app.register_blueprint(hand_detection_bp)
app.register_blueprint(qr_detection_bp)
app.register_blueprint(roi_bp)

# 🆕 NEW: Register cloud endpoints blueprint with error handling
try:
    app.register_blueprint(cloud_bp, name='cloud_endpoints')
    logger.info("✅ Cloud endpoints registered: /api/cloud/*")
except ValueError as e:
    logger.warning(f"⚠️ Cloud blueprint already registered: {e}")
    # If already registered, skip (could be from config.py)
    pass

# 🆕 NEW: Register sync endpoints blueprint with error handling
try:
    app.register_blueprint(sync_bp, url_prefix='/api/sync')
    logger.info("✅ Sync endpoints registered: /api/sync/*")
except ValueError as e:
    logger.warning(f"⚠️ Sync blueprint already registered: {e}")
    # If already registered, skip
    pass
except ImportError as e:
    logger.warning(f"⚠️ Sync endpoints not available: {e}")
    pass

# 🆕 NEW: Register ZaloPay payment blueprints
try:
    app.register_blueprint(zalopay_bp, url_prefix='/api/payment')
    logger.info("✅ ZaloPay payment endpoints registered: /api/payment/*")
except Exception as e:
    logger.error(f"❌ Failed to register ZaloPay payment endpoints: {e}")

try:
    app.register_blueprint(webhook_bp, url_prefix='/webhook')
    logger.info("✅ ZaloPay webhook endpoints registered: /webhook/*")
except Exception as e:
    logger.error(f"❌ Failed to register ZaloPay webhook endpoints: {e}")

# 🔧 NOTE: License blueprint registration moved to end of file after route definitions

# Hàm ghi last_stop_time khi ứng dụng dừng
def exit_handler():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        last_stop_time = datetime.now(tz=timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT OR REPLACE INTO program_status (key, value)
            VALUES ('last_stop_time', ?)
        """, (last_stop_time,))
        conn.commit()
        conn.close()
        logger.info("Application stopped gracefully")
    except Exception as e:
        logger.error(f"Error saving last_stop_time: {e}")

# Đăng ký exit_handler
atexit.register(exit_handler)

def is_port_in_use(port):
    """Kiểm tra xem cổng có đang được sử dụng hay không."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return False
        except OSError:
            return True

# Global flag để tránh multiple shutdown
_shutdown_in_progress = False

def signal_handler(sig, frame):
    """Xử lý tín hiệu dừng ứng dụng một cách graceful"""
    global _shutdown_in_progress
    
    # Tránh multiple shutdown
    if _shutdown_in_progress:
        print("\nForced shutdown...")
        os._exit(1)  # Force exit nếu đã shutdown rồi
    
    _shutdown_in_progress = True
    print("\nShutting down gracefully... (Press Ctrl+C again to force)")
    
    try:
        logger.info("Received shutdown signal, stopping application...")
        
        # Dừng scheduler
        if 'scheduler' in globals():
            scheduler.stop()
            logger.info("Scheduler stopped")
        
        # Đợi các thread kết thúc với timeout ngắn hơn
        main_thread = threading.current_thread()
        for t in threading.enumerate():
            if t != main_thread and t.is_alive():
                try:
                    t.join(timeout=2)  # Giảm timeout xuống 2 giây
                    if t.is_alive():
                        logger.warning(f"Thread {t.name} did not stop gracefully")
                except:
                    pass  # Ignore errors during shutdown
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        os._exit(0)  # Force exit

# Đăng ký signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 🆕 NEW: Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    from flask import jsonify
    return jsonify({
        'status': 'healthy',
        'service': 'V_track Backend',
        'timestamp': datetime.now().isoformat(),
        'modules': {
            'sync': 'enabled',
            'cloud': 'enabled', 
            'payment': 'enabled',
            'licensing': 'enabled'
        }
    }), 200

# 🆕 NEW: Root endpoint
@app.route('/', methods=['GET'])
def root():
    """Root endpoint information"""
    from flask import jsonify
    return jsonify({
        'service': 'V_track Backend API',
        'version': '1.0.0',
        'features': [
            'Cloud Storage Sync',
            'NVR Camera Integration', 
            'ZaloPay Payment Processing',
            'Automated License Management'
        ],
        'endpoints': {
            'sync': '/api/sync',
            'cloud': '/api/cloud',
            'payment': '/api/payment',
            'webhook': '/webhook',
            'license': '/api/license',
            'health': '/health'
        }
    }), 200

# 🔧 Debug: List all registered endpoints on startup
def log_registered_routes():
    """Log all registered Flask routes for debugging"""
    logger.info("📋 Registered Flask Routes:")
    for rule in app.url_map.iter_rules():
        methods = ', '.join((rule.methods or set()) - {'HEAD', 'OPTIONS'})
        logger.info(f"   {methods:15} {rule.rule}")

# 🆕 NEW: Auto-start function for cloud sync (Flask 2.2+ compatible)
def initialize_auto_sync():
    """Auto-start sync for all enabled cloud sources on backend startup"""
    def startup_sync():
        try:
            # Wait for database operations to complete
            import time
            time.sleep(2)
            logger.info("🚀 Starting auto-sync for all enabled cloud sources...")
            result = pydrive_downloader.auto_start_all_enabled_sources()
            if result.get('success'):
                logger.info(f"✅ Auto-sync initialization completed: {result.get('started_count', 0)} sources started")
            else:
                logger.error(f"❌ Auto-sync initialization failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"❌ Auto-sync startup failed: {e}")
    
    # Run in background thread to not block app startup
    import threading
    threading.Thread(target=startup_sync, daemon=True).start()
    logger.info("🔄 Auto-sync initialization thread started")

# 🆕 NEW: License Management Endpoints
@license_bp.route('/validate', methods=['POST'])
def validate_license():
    """Validate license key"""
    from flask import request, jsonify
    try:
        from modules.payments.license_generator import LicenseGenerator
        from modules.licensing.license_models import License
        
        data = request.get_json()
        license_key = data.get('license_key')
        machine_fingerprint = data.get('machine_fingerprint')
        
        if not license_key:
            return jsonify({
                'success': False,
                'error': 'License key required'
            }), 400
        
        # Initialize license generator
        license_generator = LicenseGenerator()
        
        # Validate license signature
        license_data = license_generator.verify_license(license_key)
        
        if not license_data:
            return jsonify({
                'valid': False,
                'error': 'Invalid license signature'
            }), 400
        
        # Validate against database
        db_validation = License.validate(license_key, machine_fingerprint)
        
        return jsonify({
            'valid': db_validation['valid'],
            'license_data': license_data,
            'database_status': db_validation
        }), 200
        
    except Exception as e:
        logger.error(f"License validation error: {str(e)}")
        return jsonify({
            'valid': False,
            'error': f'Validation error: {str(e)}'
        }), 500

@license_bp.route('/activate', methods=['POST'])
def activate_license():
    """Activate license on machine"""
    from flask import request, jsonify
    try:
        from modules.payments.license_generator import LicenseGenerator
        from modules.licensing.license_models import License
        
        data = request.get_json()
        license_key = data.get('license_key')
        machine_fingerprint = data.get('machine_fingerprint')
        device_info = data.get('device_info', {})
        
        if not license_key:
            return jsonify({
                'success': False,
                'error': 'License key required'
            }), 400
        
        # Generate machine fingerprint if not provided
        if not machine_fingerprint:
            license_generator = LicenseGenerator()
            machine_fingerprint = license_generator.generate_machine_fingerprint()
        
        # Activate license
        result = License.activate(license_key, machine_fingerprint, device_info)
        
        if result['success']:
            return jsonify({
                'success': True,
                'status': result['status'],
                'machine_fingerprint': machine_fingerprint
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"License activation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Activation error: {str(e)}'
        }), 500

@license_bp.route('/info/<license_key>', methods=['GET'])
def get_license_info(license_key):
    """Get license information"""
    from flask import jsonify
    try:
        from modules.licensing.license_models import License
        
        license_data = License.get_by_key(license_key)
        
        if not license_data:
            return jsonify({
                'success': False,
                'error': 'License not found'
            }), 404
        
        # Remove sensitive data
        safe_data = {
            'product_type': license_data['product_type'],
            'features': license_data['features'],
            'status': license_data['status'],
            'created_at': license_data['created_at'],
            'expires_at': license_data['expires_at'],
            'activation_count': license_data['activation_count'],
            'max_activations': license_data['max_activations']
        }
        
        return jsonify({
            'success': True,
            'license_info': safe_data
        }), 200
        
    except Exception as e:
        logger.error(f"License info error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Info error: {str(e)}'
        }), 500

@license_bp.route('/stats', methods=['GET'])
def get_license_stats():
    """Get licensing statistics"""
    from flask import jsonify
    try:
        from modules.licensing.license_models import get_license_stats
        
        stats = get_license_stats()
        
        if stats:
            return jsonify({
                'success': True,
                'stats': stats
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to get stats'
            }), 500
            
    except Exception as e:
        logger.error(f"License stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Stats error: {str(e)}'
        }), 500

@license_bp.route('/test-email', methods=['POST'])
def test_email_delivery():
    """Test email delivery system"""
    from flask import request, jsonify
    try:
        from modules.payments.email_sender import EmailSender
        
        data = request.get_json()
        test_email = data.get('email')
        
        if not test_email:
            return jsonify({
                'success': False,
                'error': 'Email address required'
            }), 400
        
        # Send test email
        email_sender = EmailSender()
        result = email_sender.send_test_email(test_email)
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Test email error: {str(e)}'
        }), 500

@license_bp.route('/config', methods=['GET'])
def get_license_config():
    """Get license system configuration"""
    from flask import jsonify
    try:
        from modules.payments.email_sender import EmailSender
        
        email_sender = EmailSender()
        email_config = email_sender.get_email_config_status()
        
        # ZaloPay config (without sensitive data)
        zalopay_config = {
            'app_id': os.getenv('ZALOPAY_APP_ID', 'Not set'),
            'environment': os.getenv('ZALOPAY_ENVIRONMENT', 'Not set'),
            'endpoint_configured': bool(os.getenv('ZALOPAY_ENDPOINT')),
            'keys_configured': bool(os.getenv('ZALOPAY_KEY1') and os.getenv('ZALOPAY_KEY2'))
        }
        
        return jsonify({
            'success': True,
            'config': {
                'email': email_config,
                'zalopay': zalopay_config,
                'license_system': 'operational'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Config error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Config error: {str(e)}'
        }), 500

# 🔧 FIXED: Register license blueprint AFTER route definitions
try:
    app.register_blueprint(license_bp, url_prefix='/api/license')
    logger.info("✅ License management endpoints registered: /api/license/*")
except Exception as e:
    logger.error(f"❌ Failed to register license endpoints: {e}")

# Khởi chạy ứng dụng
if __name__ == "__main__":
    port = 8080
    
    # Kiểm tra port trước khi khởi chạy
    if is_port_in_use(port):
        logger.error(f"Port {port} is already in use!")
        sys.exit(1)
    
    logger.info(f"Starting VTrack application on port {port}")
    logger.info(f"🔑 OAuth session security: ✅ Enabled")
    
    print("🚀 V_track Backend Starting...")
    print(f"📡 Server: http://0.0.0.0:{port}")
    print("🔧 Modules:")
    print("   ✅ Cloud Storage Sync")
    print("   ✅ NVR Camera Integration") 
    print("   ✅ ZaloPay Payment Processing")
    print("   ✅ Automated License Management")
    print("   ✅ Email Delivery System")
    print("\n🔗 API Endpoints:")
    print(f"   📊 Health Check: http://0.0.0.0:{port}/health")
    print(f"   💳 Payments: http://0.0.0.0:{port}/api/payment")
    print(f"   🔔 Webhooks: http://0.0.0.0:{port}/webhook")
    print(f"   🔑 Licenses: http://0.0.0.0:{port}/api/license")
    print(f"   ☁️  Cloud Sync: http://0.0.0.0:{port}/api/cloud")
    print(f"   📹 NVR Sources: http://0.0.0.0:{port}/api/sync")
    
    # 🔧 Debug: Log registered routes
    log_registered_routes()
    
    # ✅ NEW: Manual auto-sync initialization (Flask 2.2+ compatible)
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
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        logger.info("Application terminated")