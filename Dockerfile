# ============================================
# ePACK - Multi-stage Docker Build
# ============================================
# This Dockerfile creates a production-ready containerized
# deployment of ePACK with both frontend and backend.
#
# Build:
#   docker build -t epack:latest .
#
# Run:
#   docker run -p 8080:8080 -p 3000:3000 epack:latest
#
# Or use docker-compose:
#   docker-compose up

# ============================================
# STAGE 1: Frontend Builder
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (use ci for deterministic builds)
RUN npm ci --production=false

# Copy frontend source
COPY frontend/ ./

# Build frontend application
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# Clean up dev dependencies
RUN npm prune --production

# ============================================
# STAGE 2: Backend Setup
# ============================================
FROM python:3.10-slim AS backend-builder

WORKDIR /app

# Install system dependencies for Python packages
# opencv-contrib-python, mediapipe require these
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies including gunicorn for production
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn[gevent]==21.2.0

# ============================================
# STAGE 3: Production Image
# ============================================
FROM python:3.10-slim

LABEL maintainer="ePACK Team"
LABEL description="ePACK - Video Processing and Analysis Container"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=backend-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend source and gunicorn config
COPY backend/ /app/backend/
COPY backend/gunicorn.conf.py /app/backend/gunicorn.conf.py

# Copy frontend build artifacts
COPY --from=frontend-builder /app/frontend/.next /app/frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend-builder /app/frontend/package.json /app/frontend/package.json
COPY --from=frontend-builder /app/frontend/next.config.js /app/frontend/next.config.js
COPY --from=frontend-builder /app/frontend/public /app/frontend/public

# Copy startup scripts
COPY scripts/ /app/scripts/

# Create necessary directories
RUN mkdir -p /app/var/logs \
    /app/var/cache \
    /app/var/tmp \
    /app/var/uploads \
    /app/var/flask_session \
    /app/backend/VTrack_db.db

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VTRACK_IN_DOCKER=true \
    VTRACK_DEPLOYMENT_MODE=docker \
    VTRACK_BASE_DIR=/app \
    VTRACK_SESSION_DIR=/app/var/flask_session \
    TF_CPP_MIN_LOG_LEVEL=3 \
    MEDIAPIPE_DISABLE_GPU=1 \
    PYTHONWARNINGS=ignore \
    FLASK_ENV=production \
    NODE_ENV=production

# Expose ports
# 8080: Backend Flask API
# 3000: Frontend Next.js
EXPOSE 8080 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/health', timeout=5)" || exit 1

# Initialize database on container start
RUN cd /app/backend && python database.py

# Default command: Start both backend (with Gunicorn) and frontend
# In production, it's recommended to use separate containers via docker-compose
CMD ["sh", "-c", "cd /app/backend && gunicorn --config gunicorn.conf.py app:app & cd /app/frontend && npm run start"]

# For production deployment:
# - Use docker-compose to run separate containers
# - Backend: Gunicorn with gevent workers
# - Frontend: Next.js production server
# - Nginx: Reverse proxy (recommended)
