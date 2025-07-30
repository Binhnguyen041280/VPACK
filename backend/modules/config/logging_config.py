import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

class LogSizeFilter(logging.Filter):
    def __init__(self, log_file, max_size=500*1024):
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
        context = " ".join(f"{k}={v}" for k, v in self.extra.items())
        return f"[{context}] {msg}", kwargs

def setup_logging(base_dir, app_name="app", log_level=logging.INFO):
    log_dir = os.path.join(base_dir, "resources", "output_clips", "LOG")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{app_name}_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    handler = RotatingFileHandler(log_file, maxBytes=500*1024, backupCount=5)
    handler.setFormatter(logging.Formatter(
        '%(asctime)sZ [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    ))
    handler.addFilter(LogSizeFilter(log_file))
    
    logging.basicConfig(level=log_level, handlers=[handler])

def get_logger(module_name, context=None, separate_log=None):
    logger = logging.getLogger("app")
    if separate_log:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "output_clips", "LOG")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{separate_log}_{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = RotatingFileHandler(log_file, maxBytes=500*1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s,%(msecs)03d - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    return ContextAdapter(logger, context or {})