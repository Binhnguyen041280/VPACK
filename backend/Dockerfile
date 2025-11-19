# ============================================================================
# ePACK Backend - 3-Stage Multi-Stage Dockerfile
# Python 3.10 | Debian Bookworm | ARM64/AMD64 Compatible
# Optimized for Computer Vision (MediaPipe, OpenCV-Contrib)
# ============================================================================

# ============================================================================
# Stage 1: BASE - System Dependencies & Runtime Environment
# ============================================================================
FROM python:3.10-slim-bookworm AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies required for OpenCV, MediaPipe, and runtime
# Critical: libgl1-mesa-glx, libglib2.0-0 for OpenCV
# ffmpeg for video processing
# libzbar0 for QR code scanning (pyzbar)
# gcc/g++/make for building Python packages with native extensions
# docker.io for Docker CLI (to restart container via Docker socket)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    wget \
    curl \
    gcc \
    g++ \
    make \
    libzbar0 \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ============================================================================
# Stage 2: BUILDER - Install Python Dependencies
# ============================================================================
FROM base AS builder

# Copy only requirements first for better layer caching
COPY requirements.txt .

# Install Python packages to user directory
# --user flag installs to /root/.local (will be copied to production stage)
# --no-warn-script-location suppresses PATH warnings (scripts not needed in builder)
RUN pip install --user --no-warn-script-location -r requirements.txt

# Validate critical imports to catch build-time errors
# This ensures opencv-contrib-python, mediapipe, and flask are properly installed
RUN python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')" && \
    python -c "import mediapipe as mp; print(f'MediaPipe version: {mp.__version__}')" && \
    python -c "import flask; print(f'Flask version: {flask.__version__}')" && \
    python -c "from cv2 import wechat_qrcode_WeChatQRCode; print('WeChatQRCode available')" && \
    echo "All critical dependencies validated successfully"

# ============================================================================
# Stage 3: PRODUCTION - Minimal Runtime Image
# ============================================================================
FROM base AS production

# Create non-root user for security
# UID 1001 for consistency with container best practices
RUN adduser --system --uid 1001 --group appuser

# Copy installed Python packages from builder stage
# This dramatically reduces final image size
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code with proper ownership
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
# database: SQLite database files (volume mount point)
# logs: Application logs (volume mount point)
# var/flask_session: Flask session storage (writable by appuser)
# var/cache: Temporary cache files
# var/uploads: File upload storage
# keys: OAuth credentials (copied from source)
# models: WeChat QR detection models (copied from source)
RUN mkdir -p \
    database \
    logs \
    var/flask_session \
    var/cache \
    var/uploads \
    keys \
    models/wechat_qr \
    resources/input \
    resources/output \
    && chown -R appuser:appuser \
    database \
    logs \
    var \
    keys \
    models \
    resources

# Add user site-packages to PATH and PYTHONPATH
# MPLCONFIGDIR to avoid matplotlib warnings with system user
# EPACK_IN_DOCKER to enable Docker-aware path resolution
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONPATH="/home/appuser/.local/lib/python3.10/site-packages" \
    MPLCONFIGDIR="/tmp/matplotlib" \
    EPACK_IN_DOCKER="true" \
    EPACK_INPUT_DIR="/app/resources/input" \
    EPACK_OUTPUT_DIR="/app/resources/output" \
    EPACK_SESSION_DIR="/app/var/flask_session"

# Build metadata labels
ARG BUILD_DATE
LABEL service="BACKEND" \
      build.date="${BUILD_DATE}" \
      description="ePACK Backend Service"

# Switch to non-root user
USER appuser

# Expose backend port
EXPOSE 8080

# Health check using curl (available from base stage)
# Checks /health endpoint every 30s with 3s timeout
# Container marked unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start Flask application
# app.py should bind to 0.0.0.0:8080 in production mode
CMD ["python", "app.py"]
