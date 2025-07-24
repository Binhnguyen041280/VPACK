import sqlite3
import os
import json
from modules.db_utils import find_project_root
import time
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional

# 🔒 SECURITY: Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Xác định thư mục gốc của dự án
BASE_DIR = find_project_root(os.path.abspath(__file__))

# Đường dẫn cơ sở dữ liệu
DB_DIR = os.path.join(BASE_DIR, "backend/database")
DB_PATH = os.path.join(DB_DIR, "events.db")

# Đường dẫn mặc định
INPUT_VIDEO_DIR = os.path.join(BASE_DIR, "resources/Inputvideo")
OUTPUT_CLIPS_DIR = os.path.join(BASE_DIR, "resources/output_clips")

def get_db_connection():
    """
    Get DB connection with retry logic for locked database and enhanced WAL config
    """
    for attempt in range(5):  # Retry tối đa 5 lần
        try:
            conn = sqlite3.connect(DB_PATH, timeout=60.0)  # Tăng timeout lên 60 giây
            conn.execute("PRAGMA busy_timeout = 60000")   # Busy timeout 60s
            conn.execute("PRAGMA journal_mode = WAL")     # WAL mode cho concurrent reads/writes
            conn.execute("PRAGMA synchronous = NORMAL")   # Balanced sync (nhanh hơn FULL)
            conn.execute("PRAGMA temp_store = MEMORY")    # Temp data in memory (tăng speed)
            conn.execute("PRAGMA foreign_keys = ON")      # Enforce FK nếu cần
            print(f"✅ DB connection success (attempt {attempt+1})")  # Debug log
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < 4:
                print(f"⚠️ DB locked, retrying in 2s... (attempt {attempt+1}/5)")
                time.sleep(2)  # Wait 2 giây trước retry (tăng từ 1s để an toàn)
                continue
            raise e  # Raise error nếu hết retry
    raise sqlite3.OperationalError("Database locked after max retries")

def update_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Tạo bảng file_list
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_type TEXT NOT NULL,
                days INTEGER,
                custom_path TEXT,
                file_path TEXT NOT NULL,
                ctime DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_processed INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'chưa bắt đầu',
                log_file_path TEXT,
                camera_name TEXT
            )
        """)

        # Tạo bảng program_status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS program_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM program_status WHERE key = 'first_run_completed'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO program_status (key, value) VALUES ('first_run_completed', 'false')")

        # Tạo bảng processing_config
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_config (
                id INTEGER PRIMARY KEY,
                input_path TEXT,
                output_path TEXT,
                storage_duration INTEGER,
                min_packing_time INTEGER,
                max_packing_time INTEGER,
                frame_rate INTEGER,
                frame_interval INTEGER,
                video_buffer INTEGER,
                default_frame_mode TEXT,
                selected_cameras TEXT,
                db_path TEXT NOT NULL,
                run_default_on_start INTEGER DEFAULT 0,
                motion_threshold FLOAT DEFAULT 0.1,
                stable_duration_sec FLOAT DEFAULT 1
            )
        """)
        cursor.execute("UPDATE processing_config SET db_path = ?, run_default_on_start = 0 WHERE db_path IS NULL OR run_default_on_start IS NULL", (DB_PATH,))

        # Add camera_paths column to processing_config
        try:
            cursor.execute("ALTER TABLE processing_config ADD COLUMN camera_paths TEXT DEFAULT '{}'")
            print("✅ Added camera_paths column to processing_config")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Thêm cột multiple_sources_enabled nếu chưa có
        try:
            cursor.execute("ALTER TABLE processing_config ADD COLUMN multiple_sources_enabled INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Cột đã tồn tại

        # Chèn dữ liệu mặc định nếu bảng processing_config rỗng
        cursor.execute("SELECT COUNT(*) FROM processing_config")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO processing_config (
                    id, input_path, output_path, storage_duration, min_packing_time, 
                    max_packing_time, frame_rate, frame_interval, video_buffer, default_frame_mode, 
                    selected_cameras, db_path, run_default_on_start, multiple_sources_enabled, camera_paths
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (1, INPUT_VIDEO_DIR, OUTPUT_CLIPS_DIR, 30, 10, 120, 30, 5, 2, "default", "[]", DB_PATH, 0, 0, "{}"))

        # 🔒 SECURITY: Add user_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT NOT NULL UNIQUE,
                user_email TEXT NOT NULL,
                provider TEXT NOT NULL,
                encrypted_credentials TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                user_agent TEXT,
                ip_address TEXT
            )
        """)

        # 🔒 SECURITY: Add authentication audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT,
                user_email TEXT,
                event_type TEXT NOT NULL,
                provider TEXT,
                success BOOLEAN NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                error_message TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create sync_status table for auto-sync management (Cloud sources)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                sync_enabled INTEGER DEFAULT 1,
                last_sync_timestamp TEXT,
                next_sync_timestamp TEXT,
                sync_interval_minutes INTEGER DEFAULT 10,
                last_sync_status TEXT DEFAULT 'pending',
                last_sync_message TEXT,
                files_downloaded_count INTEGER DEFAULT 0,
                total_download_size_mb REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE,
                UNIQUE(source_id)
            )
        """)
        print("✅ Created sync_status table")

        # Create downloaded_files table for tracking downloaded content
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloaded_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                camera_name TEXT NOT NULL,
                original_filename TEXT,
                local_file_path TEXT NOT NULL,
                file_size_bytes INTEGER DEFAULT 0,
                download_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                recording_start_time TEXT,
                recording_end_time TEXT,
                file_format TEXT,
                checksum TEXT,
                sync_batch_id TEXT,
                is_processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE
            )
        """)
        print("✅ Created downloaded_files table")

        # Create last_downloaded_file table for efficient tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS last_downloaded_file (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                camera_name TEXT NOT NULL,
                last_filename TEXT,
                last_file_timestamp TEXT,
                last_download_time TEXT DEFAULT CURRENT_TIMESTAMP,
                total_files_count INTEGER DEFAULT 0,
                total_size_mb REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE,
                UNIQUE(source_id, camera_name)
            )
        """)
        print("✅ Created last_downloaded_file table")

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status_source_id ON sync_status(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status_next_sync ON sync_status(next_sync_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_source_camera ON downloaded_files(source_id, camera_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_timestamp ON downloaded_files(download_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_processed ON downloaded_files(is_processed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_downloaded_source_camera ON last_downloaded_file(source_id, camera_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_downloaded_timestamp ON last_downloaded_file(last_file_timestamp)")
        
        # 🔒 SECURITY: Indexes for session management
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_email ON user_sessions(user_email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_email ON auth_audit(user_email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_created ON auth_audit(created_at)')
   
        # Tạo bảng frame_settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frame_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                frame_rate INTEGER,
                frame_interval INTEGER,
                description TEXT
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM frame_settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO frame_settings (mode, frame_rate, frame_interval, description)
                VALUES (?, ?, ?, ?)
            """, ("default", 30, 5, "Chế độ mặc định từ giao diện"))

        # Tạo bảng general_info với working_days dạng JSON tiếng Anh
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS general_info (
                id INTEGER PRIMARY KEY,
                country TEXT,
                timezone TEXT,
                brand_name TEXT,
                working_days TEXT,
                from_time TEXT,
                to_time TEXT
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM general_info")
        if cursor.fetchone()[0] == 0:
            working_days = json.dumps(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            cursor.execute("""
                INSERT INTO general_info (
                    id, country, timezone, brand_name, working_days, from_time, to_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (1, "Việt Nam", "UTC+7", "MyBrand", working_days, "07:00", "23:00"))

        # Tạo bảng events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER,
                te INTEGER,
                duration INTEGER,
                tracking_codes TEXT,
                video_file TEXT NOT NULL,
                buffer INTEGER NOT NULL,
                camera_name TEXT,
                packing_time_start INTEGER,
                packing_time_end INTEGER,
                is_processed INTEGER DEFAULT 0,
                processed_timestamp INTEGER,
                output_video_path TEXT,
                session_id TEXT,
                output_file TEXT
            )
        """)
        # Tạo chỉ mục trên te và event_id
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_te_event_id ON events(te, event_id)")

        # Tạo bảng processed_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_logs (
                log_file TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_processed INTEGER DEFAULT 0
            )
        """)

        # Tạo bảng packing_profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packing_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL,
                qr_trigger_area TEXT,
                qr_motion_area TEXT,
                qr_mvd_area TEXT,
                packing_area TEXT,
                min_packing_time INTEGER,
                jump_time_ratio REAL,
                mvd_jump_ratio REAL,
                scan_mode TEXT,
                fixed_threshold INTEGER,
                margin INTEGER,
                additional_params TEXT
            )
        """)

        # Tạo bảng video_sources (support local + cloud only)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL CHECK(source_type IN ('local', 'cloud')),
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                config TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                folder_depth INTEGER DEFAULT 0,
                parent_folder_id TEXT
            )
        """)
        
        # Add folder depth tracking columns
        try:
            cursor.execute("ALTER TABLE video_sources ADD COLUMN folder_depth INTEGER DEFAULT 0")
            print("✅ Added folder_depth column to video_sources")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE video_sources ADD COLUMN parent_folder_id TEXT")
            print("✅ Added parent_folder_id column to video_sources")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        # Create indexes for lazy folder tree
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_folder_depth ON video_sources(folder_depth)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_parent_folder ON video_sources(parent_folder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_source_type_active ON video_sources(source_type, active)")
        print("✅ Created indexes for lazy folder tree performance")

        # Update index cho video_sources
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_active ON video_sources(active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_source_type ON video_sources(source_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_created_at ON video_sources(created_at)")

        # Tạo table camera_configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS camera_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                camera_name TEXT NOT NULL,
                camera_config TEXT, -- JSON config specific to this camera
                is_selected INTEGER DEFAULT 1,
                folder_path TEXT, -- Local folder path for this camera
                stream_url TEXT, -- RTSP/stream URL if applicable
                resolution TEXT,
                codec TEXT,
                capabilities TEXT, -- JSON array of capabilities
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE,
                UNIQUE(source_id, camera_name)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_configurations_source_id ON camera_configurations(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_configurations_selected ON camera_configurations(is_selected)")

        # Create view active_cameras
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_cameras AS
            SELECT 
                vs.id as source_id,
                vs.name as source_name,
                vs.source_type,
                vs.path as source_path,
                cc.camera_name,
                cc.folder_path,
                cc.stream_url,
                cc.resolution,
                cc.codec,
                cc.capabilities,
                cc.is_selected
            FROM video_sources vs
            LEFT JOIN camera_configurations cc ON vs.id = cc.source_id
            WHERE vs.active = 1 AND cc.is_selected = 1
        """)

        # Create trigger update_camera_configurations_timestamp
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_camera_configurations_timestamp
            AFTER UPDATE ON camera_configurations
            FOR EACH ROW
            BEGIN
                UPDATE camera_configurations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        # Create trigger to update sync_status timestamp
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_sync_status_timestamp
            AFTER UPDATE ON sync_status
            FOR EACH ROW
            BEGIN
                UPDATE sync_status SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        # Create trigger to update last_downloaded_file timestamp
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_last_downloaded_file_timestamp
            AFTER UPDATE ON last_downloaded_file
            FOR EACH ROW
            BEGIN
                UPDATE last_downloaded_file SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        # Create view for sync dashboard (Cloud sources only)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS sync_dashboard AS
            SELECT 
                vs.id as source_id,
                vs.name as source_name,
                vs.source_type,
                vs.path as source_path,
                ss.sync_enabled,
                ss.last_sync_timestamp,
                ss.next_sync_timestamp,
                ss.sync_interval_minutes,
                ss.last_sync_status,
                ss.last_sync_message,
                ss.files_downloaded_count,
                ss.total_download_size_mb,
                COUNT(df.id) as total_downloaded_files,
                SUM(df.file_size_bytes) / (1024*1024) as total_size_mb_calculated
            FROM video_sources vs
            LEFT JOIN sync_status ss ON vs.id = ss.source_id
            LEFT JOIN downloaded_files df ON vs.id = df.source_id
            WHERE vs.active = 1 AND vs.source_type = 'cloud'
            GROUP BY vs.id, vs.name, vs.source_type, vs.path, ss.sync_enabled, 
                     ss.last_sync_timestamp, ss.next_sync_timestamp, ss.sync_interval_minutes,
                     ss.last_sync_status, ss.last_sync_message, ss.files_downloaded_count, ss.total_download_size_mb
        """)

        # Create view for efficient camera tracking (Cloud sources only)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS camera_sync_status AS
            SELECT 
                vs.id as source_id,
                vs.name as source_name,
                vs.source_type,
                ldf.camera_name,
                ldf.last_filename,
                ldf.last_file_timestamp,
                ldf.last_download_time,
                ldf.total_files_count,
                ldf.total_size_mb,
                ss.sync_enabled,
                ss.sync_interval_minutes,
                ss.last_sync_status
            FROM video_sources vs
            LEFT JOIN last_downloaded_file ldf ON vs.id = ldf.source_id
            LEFT JOIN sync_status ss ON vs.id = ss.source_id
            WHERE vs.active = 1 AND vs.source_type = 'cloud'
            ORDER BY vs.name, ldf.camera_name
        """)

        conn.commit()
        conn.close()
        print(f"🎉 Database updated successfully at {DB_PATH}")
        print("✅ Added camera_paths column to processing_config")
        print("✅ Created sync_status table for auto-sync management")
        print("✅ Created downloaded_files table for file tracking")
        print("✅ Created last_downloaded_file table for efficient tracking")
        print("✅ Created indexes and views for performance")
        print("✅ Added folder_depth and parent_folder_id columns to video_sources")
        print("✅ Created indexes for lazy folder tree performance")
        print("✅ Added helper functions for folder depth management")
        print("🔒 Added user_sessions and auth_audit tables for security")
        print("✅ Updated source_type constraint to support local and cloud only")
        
    except Exception as e:
        print(f"Error updating database: {e}")
        raise

# 🔒 SECURITY: Session Management Methods
def create_session(session_token: str, user_email: str, provider: str, 
                  encrypted_credentials: str, expires_at: datetime, 
                  user_agent: str = None, ip_address: str = None) -> bool:
    """Create new user session"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_sessions 
            (session_token, user_email, provider, encrypted_credentials, 
             expires_at, user_agent, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_token, user_email, provider, encrypted_credentials, 
              expires_at, user_agent, ip_address))
        conn.commit()
        conn.close()
        logger.info(f"Session created for {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return False

def get_session(session_token: str) -> Optional[Dict]:
    """Get session by token"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM user_sessions 
            WHERE session_token = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
        ''', (session_token,))
        row = cursor.fetchone()
        if row:
            # Update last accessed
            cursor.execute('''
                UPDATE user_sessions 
                SET last_accessed = CURRENT_TIMESTAMP 
                WHERE session_token = ?
            ''', (session_token,))
            conn.commit()
            # Convert row to dict
            columns = [description[0] for description in cursor.description]
            result = dict(zip(columns, row))
            conn.close()
            return result
        conn.close()
        return None
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        return None

def update_session_credentials(session_token: str, encrypted_credentials: str) -> bool:
    """Update session credentials (for token refresh)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_sessions 
            SET encrypted_credentials = ?, last_accessed = CURRENT_TIMESTAMP
            WHERE session_token = ? AND is_active = 1
        ''', (encrypted_credentials, session_token))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Failed to update session credentials: {e}")
        return False

def invalidate_session(session_token: str) -> bool:
    """Invalidate a session"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE session_token = ?
        ''', (session_token,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Failed to invalidate session: {e}")
        return False

def cleanup_expired_sessions() -> int:
    """Clean up expired sessions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM user_sessions 
            WHERE expires_at < CURRENT_TIMESTAMP OR is_active = 0
        ''')
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()
        logger.info(f"Cleaned up {deleted_count} expired sessions")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup sessions: {e}")
        return 0

def get_user_sessions(user_email: str) -> List[Dict]:
    """Get all active sessions for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_token, provider, created_at, last_accessed, expires_at
            FROM user_sessions 
            WHERE user_email = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
            ORDER BY last_accessed DESC
        ''', (user_email,))
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        return []

# 🔒 SECURITY: Authentication Audit Methods
def log_auth_event(event_type: str, success: bool, user_email: str = None, 
                  session_token: str = None, provider: str = None, 
                  ip_address: str = None, user_agent: str = None, 
                  error_message: str = None, metadata: Dict = None) -> bool:
    """Log authentication event"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO auth_audit 
            (session_token, user_email, event_type, provider, success, 
             ip_address, user_agent, error_message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_token, user_email, event_type, provider, success,
              ip_address, user_agent, error_message, 
              json.dumps(metadata) if metadata else None))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to log auth event: {e}")
        return False

def get_auth_audit(user_email: str = None, limit: int = 100) -> List[Dict]:
    """Get authentication audit trail"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_email:
            cursor.execute('''
                SELECT * FROM auth_audit 
                WHERE user_email = ?
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_email, limit))
        else:
            cursor.execute('''
                SELECT * FROM auth_audit 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Failed to get auth audit: {e}")
        return []

# Helper functions for database operations

def update_camera_paths(source_id: int, camera_paths: dict):
    """Update camera_paths in processing_config for a source"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update processing_config with camera paths
        camera_paths_json = json.dumps(camera_paths)
        cursor.execute("""
            UPDATE processing_config 
            SET camera_paths = ? 
            WHERE id = 1
        """, (camera_paths_json,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating camera paths: {e}")
        return False

def initialize_sync_status(source_id: int, sync_enabled: bool = True, interval_minutes: int = 10):
    """Initialize sync status for a new source (Cloud sources only)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        from datetime import datetime, timedelta
        
        now = datetime.now()
        next_sync = now + timedelta(minutes=interval_minutes)
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_status (
                source_id, sync_enabled, last_sync_timestamp, next_sync_timestamp,
                sync_interval_minutes, last_sync_status, last_sync_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id, 
            1 if sync_enabled else 0,
            now.isoformat(),
            next_sync.isoformat(),
            interval_minutes,
            'initialized',
            'Auto-sync initialized'
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error initializing sync status: {e}")
        return False

def get_sync_status(source_id: int):
    """Get sync status for a source"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sync_status WHERE source_id = ?
        """, (source_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, result))
        return None
    except Exception as e:
        print(f"Error getting sync status: {e}")
        return None

# Helper functions for efficient file tracking

def update_last_downloaded_file(source_id: int, camera_name: str, latest_file_info: dict, total_count: int, total_size_mb: float):
    """Update last downloaded file info for a camera"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        from datetime import datetime
        
        cursor.execute("""
            INSERT OR REPLACE INTO last_downloaded_file (
                source_id, camera_name, last_filename, last_file_timestamp,
                last_download_time, total_files_count, total_size_mb
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id,
            camera_name,
            latest_file_info['filename'],
            latest_file_info['timestamp'].isoformat(),
            datetime.now().isoformat(),
            total_count,
            total_size_mb
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating last downloaded file: {e}")
        return False

def get_last_downloaded_timestamp(source_id: int, camera_name: str):
    """Get last downloaded file timestamp for a camera"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT last_file_timestamp FROM last_downloaded_file 
            WHERE source_id = ? AND camera_name = ?
        """, (source_id, camera_name))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else "1970-01-01T00:00:00"
    except Exception as e:
        print(f"Error getting last downloaded timestamp: {e}")
        return "1970-01-01T00:00:00"

def get_camera_download_stats(source_id: int):
    """Get download statistics for all cameras of a source"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT camera_name, last_filename, last_file_timestamp,
                   total_files_count, total_size_mb, last_download_time
            FROM last_downloaded_file 
            WHERE source_id = ?
            ORDER BY camera_name
        """, (source_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        camera_stats = {}
        total_files = 0
        total_size = 0
        
        for row in results:
            camera_name, last_filename, last_timestamp, files_count, size_mb, last_download = row
            camera_stats[camera_name] = {
                'last_filename': last_filename,
                'last_timestamp': last_timestamp,
                'files_count': files_count or 0,
                'size_mb': size_mb or 0.0,
                'last_download': last_download
            }
            total_files += files_count or 0
            total_size += size_mb or 0.0
        
        return {
            'camera_stats': camera_stats,
            'total_files': total_files,
            'total_size_mb': total_size,
            'cameras_count': len(camera_stats)
        }
    except Exception as e:
        print(f"Error getting camera download stats: {e}")
        return {
            'camera_stats': {},
            'total_files': 0,
            'total_size_mb': 0.0,
            'cameras_count': 0
        }

# Helper functions for lazy folder tree

def create_source_with_folder_info(source_data, selected_folders=None):
    """Create video source with lazy folder tree information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Prepare source data
        source_type = source_data.get('source_type')
        name = source_data.get('name')
        path = source_data.get('path')
        config = json.dumps(source_data.get('config', {}))
        
        # For cloud sources with lazy folder selection
        if source_type == 'cloud' and selected_folders:
            # Store selected folders in config
            config_dict = source_data.get('config', {})
            config_dict['selected_folders'] = selected_folders
            config_dict['lazy_loading_enabled'] = True
            config = json.dumps(config_dict)
            
            # Use depth from first selected folder (they should all be depth 4)
            folder_depth = selected_folders[0].get('depth', 4) if selected_folders else 4
            parent_folder_id = selected_folders[0].get('parent_id') if selected_folders else None
        else:
            folder_depth = 0
            parent_folder_id = None
        
        # Insert source
        cursor.execute("""
            INSERT INTO video_sources (
                source_type, name, path, config, active, 
                folder_depth, parent_folder_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source_type, name, path, config, 1, folder_depth, parent_folder_id))
        
        source_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        print(f"✅ Created source with lazy folder info: {name} (ID: {source_id})")
        return source_id
        
    except Exception as e:
        print(f"❌ Error creating source with folder info: {e}")
        return None

def get_sources_with_folder_info():
    """Get all sources with folder depth information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, source_type, name, path, config, active, 
                   folder_depth, parent_folder_id, created_at
            FROM video_sources 
            WHERE active = 1
            ORDER BY created_at DESC
        """)
        
        sources = []
        for row in cursor.fetchall():
            source = {
                'id': row[0],
                'source_type': row[1],
                'name': row[2],
                'path': row[3],
                'config': json.loads(row[4]) if row[4] else {},
                'active': row[5],
                'folder_depth': row[6],
                'parent_folder_id': row[7],
                'created_at': row[8]
            }
            sources.append(source)
        
        conn.close()
        return sources
        
    except Exception as e:
        print(f"❌ Error getting sources with folder info: {e}")
        return []

def update_source_folder_depth(source_id, folder_depth, parent_folder_id=None):
    """Update folder depth for existing source"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE video_sources 
            SET folder_depth = ?, parent_folder_id = ?
            WHERE id = ?
        """, (folder_depth, parent_folder_id, source_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Updated folder depth for source {source_id}: depth={folder_depth}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating folder depth: {e}")
        return False

if __name__ == "__main__":
    os.makedirs(DB_DIR, exist_ok=True)
    update_database()