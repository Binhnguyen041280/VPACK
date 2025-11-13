import logging
import os
import sys
import time
import uuid
import glob
from datetime import datetime
from logging.handlers import RotatingFileHandler
from collections import defaultdict
from modules.path_utils import get_logs_dir, is_development_mode

# Global session ID - unique per application run
# Used for correlating logs from the same execution session
_SESSION_ID = str(uuid.uuid4())[:8]  # Short 8-char unique ID


class LogSizeFilter(logging.Filter):
    def __init__(self, log_file, max_size=500 * 1024):
        super().__init__()
        self.log_file = log_file
        self.max_size = max_size

    def filter(self, record):
        if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_size:
            if record.levelno < logging.INFO:
                return False
            print("Log file size exceeds 500KB, switching to INFO level", file=sys.stderr)
            return True
        return True


class ContextAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        if self.extra:
            context = " ".join(f"{k}={v}" for k, v in self.extra.items())
            return f"[{context}] {msg}", kwargs
        return msg, kwargs


class SessionFilter(logging.Filter):
    """Filter that adds session ID to every log record.

    Session ID allows correlating all logs from a single application run,
    making it easy to extract logs for debugging a specific execution.
    """

    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id

    def filter(self, record):
        record.session_id = self.session_id
        return True


class RateLimitFilter(logging.Filter):
    """Rate limiting filter to prevent log flooding.

    Limits the number of log messages of the same type within a time window.
    Helps prevent disk space exhaustion from error loops or retry storms.
    """

    def __init__(self, rate=100, per=60, burst=200):
        """Initialize rate limiter.

        Args:
            rate: Maximum messages allowed per time window
            per: Time window in seconds
            burst: Allow short bursts above rate limit
        """
        super().__init__()
        self.rate = rate
        self.per = per
        self.burst = burst
        self.message_counts = defaultdict(lambda: {"count": 0, "reset_time": time.time()})
        self.suppressed_counts = defaultdict(int)

    def filter(self, record):
        # Create key from module + level + message template (ignore variables)
        key = f"{record.name}:{record.levelname}:{record.msg}"

        now = time.time()
        msg_data = self.message_counts[key]

        # Reset counter if time window expired
        if now - msg_data["reset_time"] > self.per:
            # Log suppressed count before reset
            if self.suppressed_counts[key] > 0:
                record.msg = f"[RATE LIMIT] Suppressed {self.suppressed_counts[key]} identical messages in last {self.per}s: {record.msg}"
                self.suppressed_counts[key] = 0
            msg_data["count"] = 0
            msg_data["reset_time"] = now

        # Check rate limit
        if msg_data["count"] < self.rate or msg_data["count"] < self.burst:
            msg_data["count"] += 1
            return True
        else:
            self.suppressed_counts[key] += 1
            return False  # Suppress this log


class ModuleFilter(logging.Filter):
    """Filter logs by module name patterns.

    Allows creating focused log files for specific components.
    """

    def __init__(self, include_modules=None, exclude_modules=None):
        """Initialize module filter.

        Args:
            include_modules: List of module prefixes to INCLUDE (whitelist)
            exclude_modules: List of module prefixes to EXCLUDE (blacklist)

        Example:
            # Only log event processing modules
            filter = ModuleFilter(include_modules=[
                'modules.scheduler',
                'modules.technician.frame_sampler',
            ])
        """
        super().__init__()
        self.include_modules = include_modules or []
        self.exclude_modules = exclude_modules or []

    def filter(self, record):
        module_name = record.name

        # If include list specified, only allow matching modules
        if self.include_modules:
            if not any(module_name.startswith(prefix) for prefix in self.include_modules):
                return False

        # Exclude specific modules
        if self.exclude_modules:
            if any(module_name.startswith(prefix) for prefix in self.exclude_modules):
                return False

        return True


class DeduplicationFilter(logging.Filter):
    """Deduplication filter to remove consecutive identical log messages.

    Prevents log files from being filled with repeated identical messages.
    Useful for catching infinite loops or repetitive errors.
    """

    def __init__(self, max_duplicates=5):
        """Initialize deduplication filter.

        Args:
            max_duplicates: Maximum consecutive identical messages to allow
        """
        super().__init__()
        self.last_log = {}
        self.duplicate_count = defaultdict(int)
        self.max_duplicates = max_duplicates

    def filter(self, record):
        key = f"{record.name}:{record.levelname}:{record.msg}"

        if key == self.last_log.get(record.name):
            self.duplicate_count[key] += 1

            # Allow first max_duplicates occurrences
            if self.duplicate_count[key] > self.max_duplicates:
                if self.duplicate_count[key] == self.max_duplicates + 1:
                    # Log once that we're suppressing
                    record.msg = f"[DUPLICATE] Message repeated, suppressing further duplicates: {record.msg}"
                    return True
                return False  # Suppress subsequent duplicates
        else:
            # New message, reset counter
            if self.duplicate_count.get(key, 0) > self.max_duplicates:
                # Log how many times previous message was repeated
                record.msg = f"[DUPLICATE] Previous message repeated {self.duplicate_count[key]} times. New message: {record.msg}"
            self.last_log[record.name] = key
            self.duplicate_count[key] = 0

        return True


class SafeRotatingFileHandler(RotatingFileHandler):
    """Enhanced RotatingFileHandler with emergency failsafe.

    Adds hard size limit and graceful degradation if rotation fails.
    Prevents runaway log files from filling the disk.
    """

    def __init__(
        self,
        *args,
        maxBytes=500 * 1024,
        backupCount=5,
        emergency_max_size=50 * 1024 * 1024,
        **kwargs,
    ):
        """Initialize safe rotating handler.

        Args:
            maxBytes: Normal rotation threshold (default 500KB)
            backupCount: Number of backup files to keep
            emergency_max_size: Hard limit to force rotation (default 50MB)
        """
        super().__init__(*args, maxBytes=maxBytes, backupCount=backupCount, **kwargs)
        self.emergency_max_size = emergency_max_size
        self.rotation_failures = 0

    def emit(self, record):
        try:
            # Emergency size check
            if os.path.exists(self.baseFilename):
                file_size = os.path.getsize(self.baseFilename)
                if file_size > self.emergency_max_size:
                    # Force immediate rotation
                    self.doRollover()
                    record.msg = f"🚨 EMERGENCY rotation at {self.emergency_max_size/1024/1024:.1f}MB: {record.msg}"

            super().emit(record)
            self.rotation_failures = 0

        except Exception as e:
            self.rotation_failures += 1

            # If rotation fails 3 times, disable file logging
            if self.rotation_failures > 3:
                self.close()
                print(
                    f"🚨 LOGGING FAILURE: Disabled file logging after 3 failures. Error: {e}",
                    file=sys.stderr,
                )
                # Don't raise - allow app to continue


def cleanup_old_logs(log_dir, app_name, keep_count=None, keep_days=None):
    """Auto-cleanup old log files to prevent disk space issues.

    Args:
        log_dir: Directory containing log files
        app_name: Application name prefix for log files
        keep_count: Number of recent files to keep (for development mode)
        keep_days: Number of days to retain logs (for production mode)
    """
    try:
        # Find all log files matching pattern (exclude symlinks)
        pattern = os.path.join(log_dir, f"{app_name}_*.log")
        log_files = [f for f in glob.glob(pattern) if not os.path.islink(f)]

        if keep_count is not None:
            # Development: Keep N most recent files
            log_files.sort(key=os.path.getmtime, reverse=True)
            files_to_delete = log_files[keep_count:]

            for old_file in files_to_delete:
                try:
                    os.remove(old_file)
                    # Use print instead of logger (logger may not be initialized yet)
                    print(f"Cleaned up old log: {os.path.basename(old_file)}", file=sys.stderr)
                except OSError:
                    pass  # Ignore errors during cleanup

        elif keep_days is not None:
            # Production: Delete files older than N days
            cutoff_time = time.time() - (keep_days * 86400)

            for log_file in log_files:
                try:
                    if os.path.getmtime(log_file) < cutoff_time:
                        os.remove(log_file)
                        print(f"Cleaned up old log: {os.path.basename(log_file)}", file=sys.stderr)
                except OSError:
                    pass  # Ignore errors during cleanup

    except Exception as e:
        # Don't fail application if cleanup fails
        print(f"Warning: Log cleanup failed: {e}", file=sys.stderr)


def setup_logging(base_dir, app_name="app", log_level=logging.INFO):
    """Setup application logging with environment-aware configuration.

    Features:
    - Development: Per-run log files with session ID + symlink to latest
    - Production: Daily consolidated log files with session ID for filtering
    - Rate limiting: Max 100 logs/minute per message type
    - Deduplication: Max 5 consecutive identical messages
    - Emergency rotation: Hard limit at 50MB
    - Auto-cleanup: 50 files (dev) or 30 days (prod)

    Args:
        base_dir: Base directory (not used, kept for backward compatibility)
        app_name: Application name for log file naming
        log_level: Logging level (default: INFO)

    Returns:
        str: Path to the created log file
    """
    log_dir = get_logs_dir()
    is_dev = is_development_mode()

    # === ENVIRONMENT-AWARE FILENAME ===
    if is_dev:
        # Development: Per-run files with timestamp + session ID
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(log_dir, f"{app_name}_{timestamp}_s-{_SESSION_ID}.log")

        # Create/update 'latest.log' symlink to current run
        latest_link = os.path.join(log_dir, "latest.log")
        try:
            if os.path.exists(latest_link) or os.path.islink(latest_link):
                os.remove(latest_link)
            os.symlink(os.path.basename(log_file), latest_link)
        except OSError as e:
            print(f"Warning: Could not create latest.log symlink: {e}", file=sys.stderr)

        # Auto-cleanup: Keep only 50 most recent files
        cleanup_old_logs(log_dir, app_name, keep_count=50)
    else:
        # Production: Daily consolidated files
        log_file = os.path.join(log_dir, f"{app_name}_{datetime.now().strftime('%Y-%m-%d')}.log")

        # Auto-cleanup: Remove files older than 30 days
        cleanup_old_logs(log_dir, app_name, keep_days=30)

    # FIX: Clear existing handlers first (prevents basicConfig from being ignored)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Use SafeRotatingFileHandler with emergency protection
    file_handler = SafeRotatingFileHandler(
        log_file,
        maxBytes=500 * 1024,  # Normal rotation at 500KB
        backupCount=5,  # Keep 5 backup files
        emergency_max_size=50 * 1024 * 1024,  # Hard limit at 50MB
    )

    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)sZ [%(session_id)s] [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    # Add multi-layer protection filters
    file_handler.addFilter(SessionFilter(_SESSION_ID))  # Add session ID to all logs
    file_handler.addFilter(RateLimitFilter(rate=100, per=60, burst=200))  # 100 msgs/min
    file_handler.addFilter(DeduplicationFilter(max_duplicates=5))  # Max 5 duplicates
    file_handler.addFilter(LogSizeFilter(log_file))  # Legacy size check
    file_handler.setLevel(log_level)

    # Add file handler to root logger
    root_logger.addHandler(file_handler)
    root_logger.setLevel(log_level)

    # Add console handler for ERROR level only (emergency fallback)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    console_handler.setLevel(logging.ERROR)
    root_logger.addHandler(console_handler)

    # Log initialization message with environment info
    mode = "DEV" if is_dev else "PROD"
    cleanup_info = "keep:50" if is_dev else "retain:30d"
    root_logger.info(
        f"✅ Logging [{mode}] session:{_SESSION_ID} file:{os.path.basename(log_file)} (Rate:100/min, Dedup:5x, {cleanup_info})"
    )

    return log_file


def setup_dual_logging(
    base_dir, app_name="app", general_level=logging.INFO, event_level=logging.DEBUG
):
    """Setup 2 log files riêng biệt:
    1. app.log - Tổng quan app (all modules, configurable level)
    2. event_processing.log - Focus event processing (filtered modules, DEBUG level)

    Args:
        base_dir: Base directory (kept for backward compatibility)
        app_name: Application name for log file naming
        general_level: Level cho app.log (default: INFO)
        event_level: Level cho event_processing.log (default: DEBUG)

    Returns:
        dict: {"app_log": path1, "event_log": path2, "session_id": id}
    """
    log_dir = get_logs_dir()
    is_dev = is_development_mode()

    # === Create application subfolder ===
    app_log_dir = os.path.join(log_dir, "application")
    os.makedirs(app_log_dir, exist_ok=True)

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)  # Root logger accepts all levels

    # === LOG 1: app.log (General overview) ===
    if is_dev:
        app_log_filename = (
            f"{app_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_SESSION_ID}.log"
        )
    else:
        app_log_filename = f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"

    app_log_path = os.path.join(app_log_dir, app_log_filename)

    app_handler = SafeRotatingFileHandler(
        app_log_path,
        maxBytes=500 * 1024,  # 500KB
        backupCount=50 if is_dev else 30,
        emergency_max_size=50 * 1024 * 1024,  # 50MB emergency
    )
    app_handler.setLevel(general_level)

    app_formatter = logging.Formatter(
        fmt="%(asctime)s [%(session_id)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app_handler.setFormatter(app_formatter)

    # Add filters
    app_handler.addFilter(SessionFilter(_SESSION_ID))
    app_handler.addFilter(RateLimitFilter(rate=100, per=60))
    app_handler.addFilter(DeduplicationFilter(max_duplicates=5))

    root_logger.addHandler(app_handler)

    # === LOG 2: event_processing.log (Focus on event detection) ===
    if is_dev:
        event_log_filename = (
            f"event_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_SESSION_ID}.log"
        )
    else:
        event_log_filename = f"event_processing_{datetime.now().strftime('%Y%m%d')}.log"

    event_log_path = os.path.join(app_log_dir, event_log_filename)

    event_handler = SafeRotatingFileHandler(
        event_log_path,
        maxBytes=500 * 1024,  # 500KB
        backupCount=30 if is_dev else 15,
        emergency_max_size=50 * 1024 * 1024,
    )
    event_handler.setLevel(event_level)

    event_formatter = logging.Formatter(
        fmt="%(asctime)s [%(session_id)s] [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    event_handler.setFormatter(event_formatter)

    # Add filters - ONLY log event processing modules
    event_handler.addFilter(SessionFilter(_SESSION_ID))
    event_handler.addFilter(
        ModuleFilter(
            include_modules=[
                "modules.scheduler.program_runner",
                "modules.scheduler",
                "modules.technician.frame_sampler_trigger",
                "modules.technician.frame_sampler_no_trigger",
                "modules.technician.event_detector",
                "event_detector",
                "__main__",
                "program_runner",
            ]
        )
    )
    event_handler.addFilter(RateLimitFilter(rate=200, per=60))  # Higher rate for debug
    event_handler.addFilter(DeduplicationFilter(max_duplicates=3))

    root_logger.addHandler(event_handler)

    # === Console Handler (WARNING+ only) ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # === Symlink to latest (development only) ===
    if is_dev:
        # Symlink app.log (in application/ subfolder)
        latest_app = os.path.join(app_log_dir, f"{app_name}_latest.log")
        if os.path.islink(latest_app):
            os.unlink(latest_app)
        try:
            # Use relative path (just filename, symlink is in same directory)
            os.symlink(app_log_filename, latest_app)
        except OSError:
            pass

        # Symlink event_processing.log (in application/ subfolder)
        latest_event = os.path.join(app_log_dir, "event_processing_latest.log")
        if os.path.islink(latest_event):
            os.unlink(latest_event)
        try:
            # Use relative path (just filename, symlink is in same directory)
            os.symlink(event_log_filename, latest_event)
        except OSError:
            pass

    # === Cleanup old logs (in application/ subfolder) ===
    cleanup_old_logs(
        app_log_dir, app_name, keep_count=50 if is_dev else None, keep_days=None if is_dev else 30
    )
    cleanup_old_logs(
        app_log_dir,
        "event_processing",
        keep_count=30 if is_dev else None,
        keep_days=None if is_dev else 15,
    )

    print(f"📋 Dual logging initialized:", file=sys.stderr)
    print(f"   App log: {app_log_path}", file=sys.stderr)
    print(f"   Event log: {event_log_path}", file=sys.stderr)
    print(f"   Session ID: {_SESSION_ID}", file=sys.stderr)

    return {"app_log": app_log_path, "event_log": event_log_path, "session_id": _SESSION_ID}


def get_session_id():
    """Get the current session ID.

    Returns:
        str: 8-character session ID for the current application run
    """
    return _SESSION_ID


def get_logger(module_name, context=None, separate_log=None):
    """Get a logger with optional context and separate log file.

    Args:
        module_name: Name of the module (used for filtering and routing)
        context: Optional dict of context key-value pairs
        separate_log: Optional separate log file name (e.g., 'cloud_sync')

    Returns:
        ContextAdapter: Configured logger adapter
    """
    # FIX: Use actual module name instead of hardcoded "app"
    # This allows ModuleFilter to route logs correctly to event_processing.log
    logger = logging.getLogger(module_name)

    if separate_log:
        # Use /var/logs directory
        log_dir = get_logs_dir()
        log_file = os.path.join(
            log_dir, f"{separate_log}_{datetime.now().strftime('%Y-%m-%d')}.log"
        )

        file_handler = RotatingFileHandler(log_file, maxBytes=500 * 1024, backupCount=5)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s,%(msecs)03d - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

        # Add protection for separate logs (lower limits than main log)
        file_handler.addFilter(RateLimitFilter(rate=50, per=60))  # 50 msgs/min
        file_handler.addFilter(DeduplicationFilter(max_duplicates=3))  # Max 3 duplicates

        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

    return ContextAdapter(logger, context or {})
