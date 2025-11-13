"""Gunicorn configuration for ePACK production deployment."""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gevent"  # Use gevent for async support (already in requirements.txt)
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests (prevent memory leaks)
max_requests_jitter = 50  # Add randomness to max_requests
timeout = 120  # Workers silent for more than this many seconds are killed
keepalive = 5  # Wait this many seconds for requests on Keep-Alive connections

# Process naming
proc_name = "vpack"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Preload app for better performance
preload_app = True

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190


def on_starting(server):
    """Called just before the master process is initialized."""
    print(f"🚀 Starting Gunicorn with {workers} workers")


def when_ready(server):
    """Called just after the server is started."""
    print(f"✅ Server is ready. Listening on {bind}")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("🔄 Reloading workers...")


def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    print(f"⚠️  Worker {worker.pid} received INT or QUIT signal")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    print(f"❌ Worker {worker.pid} received ABRT signal (timeout)")
