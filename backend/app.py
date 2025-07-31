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

# Khởi tạo Flask app và DB path từ config
app, DB_PATH, logger = init_app_and_config()
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

# 🔧 Debug: List all registered endpoints on startup
def log_registered_routes():
    """Log all registered Flask routes for debugging"""
    logger.info("📋 Registered Flask Routes:")
    for rule in app.url_map.iter_rules():
        methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
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

# Khởi chạy ứng dụng
if __name__ == "__main__":
    port = 8080
    
    # Kiểm tra port trước khi khởi chạy
    if is_port_in_use(port):
        logger.error(f"Port {port} is already in use!")
        sys.exit(1)
    
    logger.info(f"Starting VTrack application on port {port}")
    logger.info(f"🔑 OAuth session security: ✅ Enabled")
    
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