from datetime import datetime, timedelta
from flask import Blueprint, Flask
from flask_cors import CORS
import os
import logging
from modules.db_utils import get_db_connection
from modules.config.config_manager import ConfigManager

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
"""

# Create Flask Blueprint for config routes
config_bp = Blueprint('config', __name__)

# Register routes from separate modules
from modules.config.routes.config_routes import config_routes_bp
from modules.config.routes.camera_routes import camera_routes_bp
from modules.config.routes.source_routes import source_routes_bp

# ✅ FIXED: Remove URL prefix to match working version
config_bp.register_blueprint(config_routes_bp)
config_bp.register_blueprint(camera_routes_bp)
config_bp.register_blueprint(source_routes_bp)

# Global configuration manager
config_manager = None

def init_config():
    """Initialize configuration manager"""
    global config_manager
    logger = logging.getLogger(__name__)
    
    try:
        # Create database manager
        db_manager = get_db_connection()
        
        global config_manager
        config_manager = ConfigManager(db_manager)
        logger.info("🔧 Configuration initialized")
        return config_manager
    except Exception as e:
        logger.error(f"❌ Failed to initialize config: {e}")
        raise

def init_app_and_config():
    """Initialize Flask app with full configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    
    # ✅ FIXED: CORS configuration matches working version
    CORS(app, 
         resources={
             r"/*": {
                 "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True
             }
         },
         supports_credentials=True
    )
    
    # ✅ FIX: Do NOT register blueprint here - app.py will handle it
    # app.register_blueprint(config_bp)  # REMOVED
    
    # Initialize configuration
    init_config()
    
    # ✅ FIX: Calculate DB_PATH for compatibility with app.py
    try:
        from modules.db_utils import find_project_root
        BASE_DIR = find_project_root(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR, "backend/database/events.db")
    except ImportError:
        # Fallback method
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        DB_PATH = os.path.join(BASE_DIR, "backend/database/events.db")
    
    logger.info(f"📍 DB_PATH calculated: {DB_PATH}")
    
    # ✅ FIX: Return tuple (app, DB_PATH, logger) as expected by app.py
    return app, DB_PATH, logger

if __name__ == '__main__':
    try:
        # Initialize app
        app, DB_PATH, logger = init_app_and_config()
        
        # Add simple test endpoint
        @app.route('/api/test', methods=['GET'])
        def test():
            from flask import jsonify
            return jsonify({
                'status': 'ok',
                'message': 'VTrack Config Server is running!',
                'timestamp': datetime.now().isoformat(),
                'db_path': DB_PATH
            })
        
        # Server info
        print("="*50)
        print("🚀 V_Track Configuration Server")
        print("="*50)
        print(f"🌐 Server will start on: http://localhost:8080")
        print(f"🔧 Test URL: http://localhost:8080/api/test")
        print(f"📡 API Base: http://localhost:8080/api/config/")
        print(f"📍 Database: {DB_PATH}")
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