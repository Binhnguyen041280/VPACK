import sqlite3
import os
import json
from modules.db_utils import find_project_root
from modules.db_utils.safe_connection import safe_db_connection
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

# Đường dẫn mặc định - OS-aware paths for Canvas compatibility
def get_default_storage_paths():
    """Get OS-specific default storage paths matching Canvas frontend expectations"""
    import platform
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: C:\Users\%USERNAME%\Videos\VTrack
        import os
        username = os.environ.get('USERNAME', 'User')
        input_dir = f"C:\\Users\\{username}\\Videos\\VTrack\\Input"
        output_dir = f"C:\\Users\\{username}\\Videos\\VTrack\\Output"
    elif system == "darwin":  # macOS
        # Mac: /Users/%USER%/Movies/VTrack  
        import os
        username = os.environ.get('USER', 'user')
        input_dir = f"/Users/{username}/Movies/VTrack/Input"
        output_dir = f"/Users/{username}/Movies/VTrack/Output"
    else:  # Linux and others
        # Linux: /home/%USER%/Videos/VTrack
        import os
        username = os.environ.get('USER', 'user')
        input_dir = f"/home/{username}/Videos/VTrack/Input"
        output_dir = f"/home/{username}/Videos/VTrack/Output"
    
    return input_dir, output_dir

# Get OS-specific paths
INPUT_VIDEO_DIR, OUTPUT_CLIPS_DIR = get_default_storage_paths()

# Fallback to project-relative paths if OS-specific paths fail
try:
    os.makedirs(os.path.dirname(INPUT_VIDEO_DIR), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CLIPS_DIR), exist_ok=True)
except (OSError, PermissionError):
    print("⚠️ Cannot create OS-specific paths, falling back to project directories")
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
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < 4:
                print(f"⚠️ DB locked, retrying in 2s... (attempt {attempt+1}/5)")
                time.sleep(2)
                continue
            raise e
    raise sqlite3.OperationalError("Database locked after max retries")

def update_database():
    """Update database schema with all required tables and indexes"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # ==================== ENABLE WAL MODE (ONE-TIME SETUP) ====================
            # Enable Write-Ahead Logging for better concurrent access
            # This setting persists in the database file
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            print("✅ WAL mode enabled for database")

            # ==================== CORE TABLES ====================
            
            # 1. Program Status Table
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

            # 2. Processing Config Table
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
                    stable_duration_sec FLOAT DEFAULT 1,
                    multiple_sources_enabled INTEGER DEFAULT 0,
                    camera_paths TEXT DEFAULT '{}'
                )
            """)

            # Add missing columns if needed
            try:
                cursor.execute("ALTER TABLE processing_config ADD COLUMN camera_paths TEXT DEFAULT '{}'")
                print("✅ Added camera_paths column to processing_config")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE processing_config ADD COLUMN multiple_sources_enabled INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass


            cursor.execute("UPDATE processing_config SET db_path = ?, run_default_on_start = 0 WHERE db_path IS NULL OR run_default_on_start IS NULL", (DB_PATH,))

            # Insert default data if empty
            cursor.execute("SELECT COUNT(*) FROM processing_config")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO processing_config (
                        id, input_path, output_path, storage_duration, min_packing_time, 
                        max_packing_time, frame_rate, frame_interval, video_buffer, default_frame_mode, 
                        selected_cameras, db_path, run_default_on_start, multiple_sources_enabled, camera_paths
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (1, INPUT_VIDEO_DIR, OUTPUT_CLIPS_DIR, 30, 10, 120, 30, 5, 2, "default", "[]", DB_PATH, 0, 0, "{}"))

            # 3. File List Table
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

            # 4. Frame Settings Table
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

            # 5. General Info Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS general_info (
                    id INTEGER PRIMARY KEY,
                    country TEXT,
                    timezone TEXT,
                    brand_name TEXT,
                    working_days TEXT,
                    from_time TEXT,
                    to_time TEXT,
                    language TEXT
                )
            """)
            # ==================== TIMEZONE ENHANCEMENT ====================
            
            # Add enhanced timezone columns to general_info
            timezone_columns = [
                ("timezone_iana_name", "TEXT"),
                ("timezone_display_name", "TEXT"),
                ("timezone_utc_offset_hours", "REAL"),
                ("timezone_format_type", "TEXT"),
                ("timezone_validated", "INTEGER DEFAULT 0"),
                ("timezone_updated_at", "TEXT"),
                ("timezone_validation_warnings", "TEXT"),
                ("language", "TEXT")
            ]
            
            for col_name, col_definition in timezone_columns:
                try:
                    cursor.execute(f"ALTER TABLE general_info ADD COLUMN {col_name} {col_definition}")
                    print(f"✅ Added {col_name} column to general_info")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️ Error adding {col_name}: {e}")

            cursor.execute("SELECT COUNT(*) FROM general_info")
            if cursor.fetchone()[0] == 0:
                working_days = json.dumps(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                cursor.execute("""
                    INSERT INTO general_info (
                        id, country, timezone, brand_name, working_days, from_time, to_time,
                        timezone_iana_name, timezone_display_name, timezone_utc_offset_hours,
                        timezone_format_type, timezone_validated, timezone_updated_at, language
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (1, "Vietnam", "Asia/Ho_Chi_Minh", "Alan_go", working_days, "00:00", "00:00",
                      # Default timezone for first-time initialization - user can change via UI (Step 2)
                      # Default time range 00:00-00:00 means 24/7 operation
                      "Asia/Ho_Chi_Minh", "Vietnam (Ho Chi Minh City)", 7.0,
                      "iana_standard", 1, datetime.now().isoformat(), "vi"))

            # ==================== PLATFORM MANAGEMENT TABLES ====================

            # 6. Platform Column Mappings Table (Simplified for intent-based approach)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_column_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform_name TEXT NOT NULL UNIQUE,
                    column_letter TEXT NOT NULL,

                    -- Simple metadata only
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            # No default data seeding - user will create platforms from their own data
            logger.info("Platform column mappings table ready for user-defined configurations")

            # ==================== VIDEO PROCESSING TABLES ====================

            # 7. Events Table
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
            
            # Add timezone columns to events table
            events_timezone_columns = [
                ("timezone_info", "TEXT"),
                ("created_at_utc", "INTEGER"),
                ("updated_at_utc", "INTEGER")
            ]
            
            for col_name, col_definition in events_timezone_columns:
                try:
                    cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_definition}")
                    print(f"✅ Added {col_name} column to events")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️ Error adding {col_name}: {e}")

            # 7. Processed Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_logs (
                    log_file TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_processed INTEGER DEFAULT 0
                )
            """)

            # 8. Packing Profiles Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packing_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT NOT NULL,
                    qr_trigger_area TEXT,
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
            
            # ==================== TIMEZONE MANAGEMENT TABLES ====================
            
            # 9. Timezone Metadata Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timezone_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_timezone TEXT NOT NULL,
                    migration_version INTEGER NOT NULL DEFAULT 1,
                    migration_timestamp INTEGER NOT NULL,
                    utc_storage_enabled BOOLEAN NOT NULL DEFAULT 1,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            # Initialize timezone metadata if empty
            cursor.execute("SELECT COUNT(*) FROM timezone_metadata")
            if cursor.fetchone()[0] == 0:
                current_utc_timestamp = int(datetime.now().timestamp() * 1000)
                cursor.execute("""
                    INSERT INTO timezone_metadata
                    (system_timezone, migration_version, migration_timestamp, utc_storage_enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    # Default timezone for first-time initialization - sync with general_info
                    "Asia/Ho_Chi_Minh", 1, current_utc_timestamp, True, current_utc_timestamp, current_utc_timestamp
                ))
                print("✅ Initialized timezone_metadata table")
            
            # 10. Camera Configs Table (for timezone-specific camera configurations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS camera_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_name TEXT NOT NULL UNIQUE,
                    timezone TEXT,
                    timezone_iana_name TEXT,
                    timezone_validated INTEGER DEFAULT 0,
                    config_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ==================== VIDEO SOURCES & SYNC TABLES ====================
            
            # 11. Video Sources Table (local + cloud only)
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

            # Initialize predefined sources with fixed IDs if table is empty
            cursor.execute("SELECT COUNT(*) FROM video_sources")
            if cursor.fetchone()[0] == 0:
                # Insert predefined sources with specific IDs
                cursor.execute("""
                    INSERT INTO video_sources (id, source_type, name, path, config, active, created_at, folder_depth, parent_folder_id)
                    VALUES
                    (1, 'local', 'Local Storage', '', '{}', 0, datetime('now'), 0, ''),
                    (2, 'cloud', 'Google Storage', '', '{}', 0, datetime('now'), 0, '')
                """)
                print("✅ Initialized predefined sources: ID 1 (Local Storage), ID 2 (Google Storage)")

            # Add folder depth tracking columns if missing
            try:
                cursor.execute("ALTER TABLE video_sources ADD COLUMN folder_depth INTEGER DEFAULT 0")
                print("✅ Added folder_depth column to video_sources")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE video_sources ADD COLUMN parent_folder_id TEXT")
                print("✅ Added parent_folder_id column to video_sources")
            except sqlite3.OperationalError:
                pass

            # 10. Camera Configurations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS camera_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    camera_name TEXT NOT NULL,
                    camera_config TEXT,
                    is_selected INTEGER DEFAULT 1,
                    folder_path TEXT,
                    stream_url TEXT,
                    resolution TEXT,
                    codec TEXT,
                    capabilities TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE,
                    UNIQUE(source_id, camera_name)
                )
            """)

            # 11. Sync Status Table (Cloud sources auto-sync)
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
                    error_severity TEXT,
                    error_type TEXT,
                    last_timer_run TEXT,
                    timer_error_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_error_type TEXT DEFAULT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES video_sources (id) ON DELETE CASCADE,
                    UNIQUE(source_id)
                )
            """)

            # Add error tracking columns if missing
            try:
                cursor.execute("ALTER TABLE sync_status ADD COLUMN error_count INTEGER DEFAULT 0")
                print("✅ Added error_count column to sync_status")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE sync_status ADD COLUMN last_error_type TEXT DEFAULT NULL")
                print("✅ Added last_error_type column to sync_status")
            except Exception:
                pass

            cursor.execute("UPDATE sync_status SET error_count = 0 WHERE error_count IS NULL")

            # 12. Downloaded Files Table
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

            # Add new columns for recursive folder support
            try:
                cursor.execute("ALTER TABLE downloaded_files ADD COLUMN drive_file_id TEXT")
                print("✅ Added drive_file_id column to downloaded_files")
            except sqlite3.OperationalError:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE downloaded_files ADD COLUMN relative_path TEXT")
                print("✅ Added relative_path column to downloaded_files")
            except sqlite3.OperationalError:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE downloaded_files ADD COLUMN processing_timestamp TEXT")
                print("✅ Added processing_timestamp column to downloaded_files")
            except sqlite3.OperationalError:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE downloaded_files ADD COLUMN processing_status TEXT")
                print("✅ Added processing_status column to downloaded_files")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # 13. Last Downloaded File Table
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

            # ==================== SECURITY & AUTH TABLES ====================
            
            # 14. User Sessions Table
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

            # 15. Auth Audit Table
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

            # 16. User Profiles Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gmail_address TEXT UNIQUE,
                    display_name TEXT,
                    photo_url TEXT,
                    first_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    auto_setup_complete BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    authentication_method TEXT DEFAULT 'gmail_only',
                    google_drive_connected BOOLEAN DEFAULT FALSE
                )
            """)

            # Add authentication tracking columns if they don't exist
            try:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN authentication_method TEXT DEFAULT 'gmail_only'")
                logger.info("✅ Added authentication_method column to user_profiles")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN google_drive_connected BOOLEAN DEFAULT FALSE")
                logger.info("✅ Added google_drive_connected column to user_profiles")
            except sqlite3.OperationalError:
                pass

            # ==================== LICENSE MANAGEMENT TABLES ====================
            
            # 17. Payment Transactions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_trans_id TEXT UNIQUE NOT NULL,
                    payment_trans_id TEXT,
                    customer_email TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            # 18. Licenses Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT NOT NULL UNIQUE,
                    customer_email TEXT NOT NULL,
                    payment_transaction_id INTEGER,
                    product_type TEXT NOT NULL DEFAULT 'desktop',
                    features TEXT NOT NULL DEFAULT '["full_access"]',
                    status TEXT NOT NULL DEFAULT 'active',
                    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    machine_fingerprint TEXT,
                    activation_count INTEGER DEFAULT 0,
                    max_activations INTEGER DEFAULT 1,
                    FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions(id)
                )
            """)

            # Add updated_at column if missing
            try:
                cursor.execute("ALTER TABLE licenses ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("✅ Added updated_at column to licenses")
            except sqlite3.OperationalError:
                pass

            # 19. License Activations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS license_activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id INTEGER NOT NULL,
                    machine_fingerprint TEXT NOT NULL,
                    activation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    device_info TEXT,
                    FOREIGN KEY (license_id) REFERENCES licenses(id),
                    UNIQUE(license_id, machine_fingerprint)
                )
            """)

            # 20. Email Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_id INTEGER,
                    recipient_email TEXT NOT NULL,
                    email_type TEXT DEFAULT 'license_delivery',
                    subject TEXT,
                    status TEXT DEFAULT 'pending',
                    sent_at TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (license_id) REFERENCES licenses(id)
                )
            """)

            # ==================== CREATE ALL INDEXES ====================

            # Core table indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_te_event_id ON events(te, event_id)")

            # Platform management indexes (simplified)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_platform_mappings_name ON platform_column_mappings(platform_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_platform_mappings_active ON platform_column_mappings(is_active)")
            
            # ==================== TIMEZONE INDEXES ====================
            
            # General info timezone indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_general_info_timezone_iana ON general_info(timezone_iana_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_general_info_timezone_offset ON general_info(timezone_utc_offset_hours)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_general_info_timezone_validated ON general_info(timezone_validated)")
            
            # Events timezone indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timezone_camera ON events(camera_name, packing_time_start)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_packing_time_utc ON events(packing_time_start, packing_time_end)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_processed_timezone ON events(is_processed, packing_time_start, camera_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_created_utc ON events(created_at_utc)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_updated_utc ON events(updated_at_utc)")
            
            # Timezone metadata indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timezone_metadata_migration_version ON timezone_metadata(migration_version)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timezone_metadata_timestamp ON timezone_metadata(migration_timestamp)")
            
            # Camera configs indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_configs_name ON camera_configs(camera_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_configs_timezone ON camera_configs(timezone_iana_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_configs_validated ON camera_configs(timezone_validated)")
            
            print("✅ Created timezone performance indexes")
            
            # ==================== MIGRATE EXISTING TIMEZONE DATA ====================
            
            # Migrate existing general_info timezone data if needed
            cursor.execute("SELECT id, timezone, timezone_iana_name FROM general_info WHERE timezone_validated IS NULL OR timezone_validated = 0")
            rows_to_migrate = cursor.fetchall()
            
            if rows_to_migrate:
                print(f"🔄 Migrating {len(rows_to_migrate)} existing timezone records...")
                for row_id, current_timezone, iana_name in rows_to_migrate:
                    try:
                        # Migration fallback logic for common UTC offset formats
                        # Note: These are safe defaults for legacy data migration only
                        if current_timezone == "UTC+7":
                            iana_timezone = "Asia/Ho_Chi_Minh"  # Most common UTC+7 timezone
                            display_name = "Vietnam (Ho Chi Minh City)"
                            offset_hours = 7.0
                            format_type = "utc_offset"
                        elif current_timezone == "UTC+8":
                            iana_timezone = "Asia/Shanghai"
                            display_name = "China (Shanghai)"
                            offset_hours = 8.0
                            format_type = "utc_offset"
                        elif current_timezone == "UTC+9":
                            iana_timezone = "Asia/Tokyo"
                            display_name = "Japan (Tokyo)"
                            offset_hours = 9.0
                            format_type = "utc_offset"
                        else:
                            # Default fallback for unknown legacy formats
                            # Safe default - user should update via UI if incorrect
                            iana_timezone = "Asia/Ho_Chi_Minh"
                            display_name = "Vietnam (Ho Chi Minh City)"
                            offset_hours = 7.0
                            format_type = "legacy"
                        
                        cursor.execute("""
                            UPDATE general_info SET 
                                timezone_iana_name = ?,
                                timezone_display_name = ?,
                                timezone_utc_offset_hours = ?,
                                timezone_format_type = ?,
                                timezone_validated = 1,
                                timezone_updated_at = ?
                            WHERE id = ?
                        """, (iana_timezone, display_name, offset_hours, format_type, 
                              datetime.now().isoformat(), row_id))
                        
                        print(f"✅ Migrated timezone for record {row_id}: {current_timezone} → {iana_timezone}")
                        
                    except Exception as e:
                        print(f"⚠️ Error migrating timezone for record {row_id}: {e}")
                
                print("✅ Timezone data migration completed")
            
            # Video sources indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_folder_depth ON video_sources(folder_depth)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_parent_folder ON video_sources(parent_folder_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_source_type_active ON video_sources(source_type, active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_active ON video_sources(active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_source_type ON video_sources(source_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_created_at ON video_sources(created_at)")

            # Downloaded files indexes for recursive folders
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_drive_id ON downloaded_files(drive_file_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_relative_path ON downloaded_files(source_id, relative_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_processed ON downloaded_files(is_processed, download_timestamp)")

            # Camera configurations indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_configurations_source_id ON camera_configurations(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera_configurations_selected ON camera_configurations(is_selected)")
            
            # Sync status indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status_source_id ON sync_status(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status_next_sync ON sync_status(next_sync_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status_source_error ON sync_status(source_id, error_count)")
            
            # Downloaded files indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_source_camera ON downloaded_files(source_id, camera_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_timestamp ON downloaded_files(download_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloaded_files_processed ON downloaded_files(is_processed)")
            
            # Last downloaded file indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_downloaded_source_camera ON last_downloaded_file(source_id, camera_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_downloaded_timestamp ON last_downloaded_file(last_file_timestamp)")
            
            # Security indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_email ON user_sessions(user_email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_email ON auth_audit(user_email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_created ON auth_audit(created_at)')
            
            # License indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_email ON payment_transactions(customer_email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_status ON payment_transactions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_app_trans ON payment_transactions(app_trans_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(customer_email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_expires ON licenses(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_created ON licenses(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activations_license ON license_activations(license_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activations_machine ON license_activations(machine_fingerprint)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_logs_license ON email_logs(license_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status)")

            # ==================== CREATE VIEWS ====================
            
            # Active Cameras View
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

            # Sync Dashboard View (Cloud sources only)
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

            # Camera Sync Status View (Cloud sources only)
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

            # ==================== CREATE TRIGGERS ====================

            # Update platform mappings timestamp trigger
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_platform_mappings_timestamp
                AFTER UPDATE ON platform_column_mappings
                FOR EACH ROW
                BEGIN
                    UPDATE platform_column_mappings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)

            # Update licenses timestamp trigger
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_licenses_timestamp
                AFTER UPDATE ON licenses
                FOR EACH ROW
                BEGIN
                    UPDATE licenses SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)

            # Update camera configurations timestamp trigger
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_camera_configurations_timestamp
                AFTER UPDATE ON camera_configurations
                FOR EACH ROW
                BEGIN
                    UPDATE camera_configurations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)

            # Update sync status timestamp trigger
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_sync_status_timestamp
                AFTER UPDATE ON sync_status
                FOR EACH ROW
                BEGIN
                    UPDATE sync_status SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)

            # Update last downloaded file timestamp trigger
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_last_downloaded_file_timestamp
                AFTER UPDATE ON last_downloaded_file
                FOR EACH ROW
                BEGIN
                    UPDATE last_downloaded_file SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)

            conn.commit()
            print(f"🎉 Database updated successfully at {DB_PATH}")
            print("✅ All 23 tables created successfully")
            print("✅ Platform management system implemented")
            print("   - Added platform_column_mappings table with auto-detection patterns")
            print("✅ Enhanced timezone management system implemented")
            print("   - Enhanced general_info table with 7 timezone columns")
            print("   - Enhanced events table with timezone metadata")
            print("   - Added timezone_metadata table for system configuration")
            print("   - Added camera_configs table for camera-specific timezones")
            print("✅ All indexes created for optimal performance")
            print("   - 11 new timezone-specific indexes for query optimization")
            print("✅ All views created for efficient queries")
            print("✅ All triggers created for timestamp management")
            print("✅ License management system fully integrated")
            print("✅ Security and authentication tables ready")
            print("✅ Video sources support local and cloud only")
            print("✅ Sync system ready for cloud sources")
            print("✅ Lazy folder tree system implemented")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
        raise

# ==================== SECURITY: SESSION MANAGEMENT METHODS ====================

def create_session(session_token: str, user_email: str, provider: str, 
                  encrypted_credentials: str, expires_at: datetime, 
                  user_agent: str = "", ip_address: str = "") -> bool:
    """Create new user session"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_sessions 
                (session_token, user_email, provider, encrypted_credentials, 
                 expires_at, user_agent, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_token, user_email, provider, encrypted_credentials, 
                  expires_at, user_agent or "", ip_address or ""))
            conn.commit()
        logger.info(f"Session created for {user_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return False

def get_session(session_token: str) -> Optional[Dict]:
    """Get session by token"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM user_sessions 
                WHERE session_token = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
            ''', (session_token,))
            row = cursor.fetchone()
            if row:
                cursor.execute('''
                    UPDATE user_sessions 
                    SET last_accessed = CURRENT_TIMESTAMP 
                    WHERE session_token = ?
                ''', (session_token,))
                conn.commit()
                columns = [description[0] for description in cursor.description]
                result = dict(zip(columns, row))
                return result
        return None
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        return None

def update_session_credentials(session_token: str, encrypted_credentials: str) -> bool:
    """Update session credentials (for token refresh)"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_sessions 
                SET encrypted_credentials = ?, last_accessed = CURRENT_TIMESTAMP
                WHERE session_token = ? AND is_active = 1
            ''', (encrypted_credentials, session_token))
            conn.commit()
            result = cursor.rowcount > 0
        return result
    except Exception as e:
        logger.error(f"Failed to update session credentials: {e}")
        return False

def invalidate_session(session_token: str) -> bool:
    """Invalidate a session"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE session_token = ?
            ''', (session_token,))
            conn.commit()
            result = cursor.rowcount > 0
        return result
    except Exception as e:
        logger.error(f"Failed to invalidate session: {e}")
        return False

def cleanup_expired_sessions() -> int:
    """Clean up expired sessions"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM user_sessions 
                WHERE expires_at < CURRENT_TIMESTAMP OR is_active = 0
            ''')
            conn.commit()
            deleted_count = cursor.rowcount
        logger.info(f"Cleaned up {deleted_count} expired sessions")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup sessions: {e}")
        return 0

def get_user_sessions(user_email: str) -> List[Dict]:
    """Get all active sessions for a user"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_token, provider, created_at, last_accessed, expires_at
                FROM user_sessions 
                WHERE user_email = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
                ORDER BY last_accessed DESC
            ''', (user_email,))
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        return []

# ==================== SECURITY: AUTHENTICATION AUDIT METHODS ====================

def log_auth_event(event_type: str, success: bool, user_email: str = "", 
                  session_token: str = "", provider: str = "", 
                  ip_address: str = "", user_agent: str = "", 
                  error_message: str = "", metadata: Optional[Dict] = None) -> bool:
    """Log authentication event"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO auth_audit 
                (session_token, user_email, event_type, provider, success, 
                 ip_address, user_agent, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_token or "",
                user_email or "",
                event_type, 
                provider or "",
                success,
                ip_address or "",
                user_agent or "",
                error_message or "",
                json.dumps(metadata or {})
            ))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to log auth event: {e}")
        return False

def get_auth_audit(user_email: str = "", limit: int = 100) -> List[Dict]:
    """Get authentication audit trail"""
    try:
        with safe_db_connection() as conn:
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
        return results
    except Exception as e:
        logger.error(f"Failed to get auth audit: {e}")
        return []

# ==================== HELPER FUNCTIONS FOR DATABASE OPERATIONS ====================

def update_camera_paths(source_id: int, camera_paths: dict):
    """Update camera_paths in processing_config for a source"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            camera_paths_json = json.dumps(camera_paths)
            cursor.execute("""
                UPDATE processing_config 
                SET camera_paths = ? 
                WHERE id = 1
            """, (camera_paths_json,))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error updating camera paths: {e}")
        return False

def initialize_sync_status(source_id: int, sync_enabled: bool = True, interval_minutes: int = 10):
    """Initialize sync status for a new source (Cloud sources only)"""
    try:
        with safe_db_connection() as conn:
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
        return True
    except Exception as e:
        print(f"Error initializing sync status: {e}")
        return False

def get_sync_status(source_id: int):
    """Get sync status for a source"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_status WHERE source_id = ?
            """, (source_id,))
            result = cursor.fetchone()
            if result:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, result))
        return None
    except Exception as e:
        print(f"Error getting sync status: {e}")
        return None

def update_last_downloaded_file(source_id: int, camera_name: str, latest_file_info: dict, total_count: int, total_size_mb: float):
    """Update last downloaded file info for a camera"""
    try:
        with safe_db_connection() as conn:
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
        return True
    except Exception as e:
        print(f"Error updating last downloaded file: {e}")
        return False

def get_last_downloaded_timestamp(source_id: int, camera_name: str):
    """Get last downloaded file timestamp for a camera"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_file_timestamp FROM last_downloaded_file 
                WHERE source_id = ? AND camera_name = ?
            """, (source_id, camera_name))
            result = cursor.fetchone()
            return result[0] if result else "1970-01-01T00:00:00"
    except Exception as e:
        print(f"Error getting last downloaded timestamp: {e}")
        return "1970-01-01T00:00:00"

def get_camera_download_stats(source_id: int):
    """Get download statistics for all cameras of a source"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT camera_name, last_filename, last_file_timestamp,
                       total_files_count, total_size_mb, last_download_time
                FROM last_downloaded_file 
                WHERE source_id = ?
                ORDER BY camera_name
            """, (source_id,))
            
            results = cursor.fetchall()
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

def create_source_with_folder_info(source_data: Optional[Dict] = None, selected_folders: Optional[List[Dict]] = None):
    """Create video source with lazy folder tree information"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            
            source_data = source_data or {}
            source_type = source_data.get('source_type', 'local')
            name = source_data.get('name', 'Unnamed Source')
            path = source_data.get('path', '')
            config = json.dumps(source_data.get('config', {}))
            
            if source_type == 'cloud' and selected_folders:
                config_dict = source_data.get('config', {})
                config_dict['selected_folders'] = selected_folders
                config_dict['lazy_loading_enabled'] = True
                config = json.dumps(config_dict)
                folder_depth = selected_folders[0].get('depth', 4) if selected_folders else 4
                parent_folder_id = selected_folders[0].get('parent_id', '') if selected_folders else ''
            else:
                folder_depth = 0
                parent_folder_id = ''
            
            cursor.execute("""
                INSERT INTO video_sources (
                    source_type, name, path, config, active, 
                    folder_depth, parent_folder_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source_type, name, path, config, 1, folder_depth, parent_folder_id))
            
            source_id = cursor.lastrowid
            conn.commit()
            
            print(f"✅ Created source with lazy folder info: {name} (ID: {source_id})")
            return source_id
        
    except Exception as e:
        print(f"❌ Error creating source with folder info: {e}")
        return None

def get_sources_with_folder_info():
    """Get all sources with folder depth information"""
    try:
        with safe_db_connection() as conn:
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
            
            return sources
        
    except Exception as e:
        print(f"❌ Error getting sources with folder info: {e}")
        return []

def update_source_folder_depth(source_id, folder_depth, parent_folder_id: str = ""):
    """Update folder depth for existing source"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE video_sources 
                SET folder_depth = ?, parent_folder_id = ?
                WHERE id = ?
            """, (folder_depth, parent_folder_id or '', source_id))
            conn.commit()
            
            print(f"✅ Updated folder depth for source {source_id}: depth={folder_depth}")
            return True
        
    except Exception as e:
        print(f"❌ Error updating folder depth: {e}")
        return False

def cleanup_sync_integrity():
    """Clean up sync_status table to match only active cloud sources"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM sync_status")
                cursor.execute("""
                    SELECT id FROM video_sources 
                    WHERE active = 1 AND source_type = 'cloud'
                """)
                
                cloud_sources = cursor.fetchall()
                
                for (source_id,) in cloud_sources:
                    try:
                        initialize_sync_status(source_id, sync_enabled=True, interval_minutes=2)
                    except Exception as init_error:
                        logger.warning(f"⚠️ Failed to initialize sync for source {source_id}: {init_error}")
                        continue
                
                conn.commit()
                
                logger.info(f"✅ Sync integrity cleaned - {len(cloud_sources)} cloud sources")
                return True
            
        except Exception as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                logger.warning(f"⚠️ Database locked on cleanup attempt {attempt + 1}, retrying...")
                import time
                time.sleep(2)
                continue
            else:
                logger.error(f"❌ Sync cleanup failed after {attempt + 1} attempts: {e}")
                return False
    
    return False

if __name__ == "__main__":
    os.makedirs(DB_DIR, exist_ok=True)
    update_database()