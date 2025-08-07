import os
import sys
from flask import Flask, render_template, jsonify
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

# Load environment variables
load_dotenv()

# ==================== DISABLE VERBOSE LOGGING ====================
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '3'
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'
os.environ['PYTHONWARNINGS'] = 'ignore'

import warnings
warnings.filterwarnings('ignore')

# ==================== IMPORT CORE MODULES ====================
from modules.config.logging_config import setup_logging, get_logger
from modules.config.config import config_bp, init_app_and_config
from modules.scheduler.program import program_bp, scheduler
from modules.query.query import query_bp
from blueprints.cutter_bp import cutter_bp
from blueprints.hand_detection_bp import hand_detection_bp
from blueprints.qr_detection_bp import qr_detection_bp
from blueprints.roi_bp import roi_bp
from modules.sources.cloud_endpoints import cloud_bp
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
# Configure Flask template and static paths for webapp structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
webapp_templates = os.path.join(BASE_DIR, 'webapp', 'templates')
webapp_static = os.path.join(BASE_DIR, 'webapp', 'static')

# Update Flask app configuration
app.template_folder = webapp_templates
app.static_folder = webapp_static

# Create directories if they don't exist
os.makedirs(webapp_templates, exist_ok=True)
os.makedirs(webapp_static, exist_ok=True)
os.makedirs(os.path.join(webapp_static, 'js'), exist_ok=True)
os.makedirs(os.path.join(webapp_static, 'css'), exist_ok=True)

# Log configuration
logger.info(f"📁 Template folder configured: {webapp_templates}")
logger.info(f"📁 Static folder configured: {webapp_static}")

# Verify paths and warn if empty
if not os.path.exists(webapp_templates) or not os.listdir(webapp_templates):
    logger.warning(f"⚠️ Template folder empty: {webapp_templates}")
    logger.warning("💡 Run: cp -r templates/* webapp/templates/ to copy templates")

if not os.path.exists(webapp_static) or not any(os.listdir(os.path.join(webapp_static, subdir)) for subdir in ['js', 'css'] if os.path.exists(os.path.join(webapp_static, subdir))):
    logger.warning(f"⚠️ Static folder empty: {webapp_static}")
    logger.warning("💡 Run: cp -r static/* webapp/static/ to copy static files")

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
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
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
app.register_blueprint(program_bp)
app.register_blueprint(config_bp, url_prefix='/api/config')
app.register_blueprint(query_bp)
app.register_blueprint(cutter_bp)
app.register_blueprint(hand_detection_bp)
app.register_blueprint(qr_detection_bp)
app.register_blueprint(roi_bp)

# Cloud and sync modules
try:
    app.register_blueprint(cloud_bp, name='cloud_endpoints')
    logger.info("✅ Cloud endpoints registered")
except ValueError as e:
    logger.warning(f"⚠️ Cloud blueprint already registered: {e}")

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

# ==================== MAIN ROUTES ====================
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/payment')
def payment_page():
    """Payment and license management page"""
    if not PAYMENT_INTEGRATION_AVAILABLE:
        return render_template('payment_unavailable.html'), 503
    return render_template('payment.html')

@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html')

@app.route('/analytics')
def analytics_page():
    """Analytics dashboard page"""
    return render_template('analytics.html')

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
                'nvr_processing': 'enabled',
                'cloud_sync': 'enabled',
                'payment_system': 'enabled' if PAYMENT_INTEGRATION_AVAILABLE else 'disabled',
                'license_management': 'enabled' if PAYMENT_INTEGRATION_AVAILABLE else 'disabled'
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
            'NVR Camera Integration',
            'Cloud Storage Sync',
            'Payment Processing' if PAYMENT_INTEGRATION_AVAILABLE else 'Payment Processing (Disabled)',
            'License Management' if PAYMENT_INTEGRATION_AVAILABLE else 'License Management (Disabled)'
        ],
        'endpoints': {
            'health': '/health',
            'payment': '/payment' if PAYMENT_INTEGRATION_AVAILABLE else None,
            'settings': '/settings',
            'analytics': '/analytics'
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

if PAYMENT_INTEGRATION_AVAILABLE:
    @app.route('/api/test-cloud', methods=['GET'])
    def test_cloud_integration():
        """Test cloud function integration"""
        try:
            cloud_client = get_cloud_client()
            
            # Run basic tests
            tests = {}
            
            # Connectivity test
            try:
                connection_test = cloud_client.test_connection()
                tests['connectivity'] = {
                    'status': 'pass' if connection_test.get('success') else 'fail',
                    'response_time_ms': connection_test.get('response_time_ms'),
                    'details': connection_test
                }
            except Exception as e:
                tests['connectivity'] = {'status': 'fail', 'error': str(e)}
            
            # Health check test
            try:
                health_check = cloud_client.health_check()
                tests['health_check'] = {
                    'status': 'pass' if health_check.get('success') else 'fail',
                    'services_healthy': health_check.get('services_healthy', '0/0'),
                    'details': health_check
                }
            except Exception as e:
                tests['health_check'] = {'status': 'fail', 'error': str(e)}
            
            # Package loading test
            try:
                packages = cloud_client.get_packages()
                tests['packages'] = {
                    'status': 'pass' if packages.get('success') else 'fail',
                    'package_count': len(packages.get('packages', {})),
                    'details': packages
                }
            except Exception as e:
                tests['packages'] = {'status': 'fail', 'error': str(e)}
            
            all_passed = all(test.get('status') == 'pass' for test in tests.values())
            
            return jsonify({
                'desktop_app': {'status': 'running', 'version': '2.1.0'},
                'cloud_functions': {
                    'configured': True,
                    'endpoints': {
                        'payment': os.environ.get('CLOUD_PAYMENT_URL'),
                        'webhook': os.environ.get('CLOUD_WEBHOOK_URL'),
                        'license': os.environ.get('CLOUD_LICENSE_URL')
                    }
                },
                'tests': tests,
                'overall_status': 'pass' if all_passed else 'fail',
                'integration': 'success' if all_passed else 'partial',
                'timestamp': datetime.now().isoformat()
            }), 200 if all_passed else 500
            
        except Exception as e:
            return jsonify({
                'desktop_app': {'status': 'running', 'version': '2.1.0'},
                'cloud_functions': {'configured': True, 'error': str(e)},
                'tests': {'initialization': {'status': 'fail', 'error': str(e)}},
                'overall_status': 'fail',
                'integration': 'failed',
                'timestamp': datetime.now().isoformat()
            }), 500

# ==================== APPLICATION LIFECYCLE ====================
def exit_handler():
    """Graceful shutdown handler"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
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
    
    # Display startup information
    print("🚀 V_Track Desktop App Starting...")
    print(f"📡 Server: http://0.0.0.0:{port}")
    print("🔧 Core Features:")
    print("   ✅ Computer Vision Processing")
    print("   ✅ NVR Camera Integration")
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
    
    # Display webapp configuration
    print(f"\n📁 Webapp Configuration:")
    print(f"   📂 Templates: {webapp_templates}")
    print(f"   📂 Static: {webapp_static}")
    
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