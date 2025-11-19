# ePACK Docker Deployment Guide

Complete guide for deploying ePACK application using Docker and Docker Compose.

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [System Requirements](#-system-requirements)
- [Architecture Overview](#-architecture-overview)
- [Initial Setup](#-initial-setup)
- [Usage](#-usage)
- [Helper Scripts](#-helper-scripts)
- [Volumes and Data](#-volumes-and-data)
- [Troubleshooting](#-troubleshooting)
- [Advanced Configuration](#-advanced-configuration)
- [Documentation](#-documentation)

## 🚀 Quick Start

Get ePACK running in 5 minutes:

```bash
# 1. Copy environment template
cp .env.docker.example .env

# 2. Generate security keys (REQUIRED)
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# 3. Edit .env and paste the generated keys

# 4. Build Docker images
docker build --platform linux/arm64 -t epack-backend:phase2 ./backend
docker build --platform linux/arm64 -t epack-frontend:phase3 ./frontend

# 5. Start the stack
./start.sh

# 6. Access the application
# Frontend: http://localhost:3000
# Backend:  http://localhost:8080
```

## 📦 System Requirements

### Hardware
- **Platform**: Mac M1/M2/M3 (ARM64) or compatible
- **RAM**: Minimum 4GB, recommended 8GB+
- **Disk**: 5GB free space minimum

### Software
- **Docker Desktop**: Version 4.0+ (with Docker Compose)
- **Python**: 3.10+ (for key generation)
- **Operating System**: macOS 12+ (Monterey or later)

### Docker Images Sizes
- Backend: ~1.94GB (includes OpenCV, MediaPipe, ML dependencies)
- Frontend: ~211MB (Next.js 15 standalone)
- Total: ~2.15GB

## 🏗️ Architecture Overview

### Services

```
┌─────────────────────────────────────────┐
│         Browser (localhost)             │
│  Frontend: 3000  │  Backend: 8080      │
└─────────┬───────────────┬───────────────┘
          │               │
          │               │
┌─────────▼───────┐  ┌───▼────────────────┐
│   Frontend      │  │    Backend         │
│   Container     │  │    Container       │
│                 │  │                    │
│  Next.js 15     │  │  Flask + Python    │
│  React 19       │  │  Computer Vision   │
│  Port: 3000     │  │  Port: 8080        │
│                 │  │                    │
│  NEXT_PUBLIC_   │  │  VTRACK_IN_DOCKER  │
│  API_URL=       │◄─┤  =true             │
│  http://backend │  │                    │
│  :8080          │  │                    │
└─────────────────┘  └──────┬─────────────┘
                            │
                            │ Persistent Data
                            │
        ┌───────────────────┴────────────────────┐
        │         Named Volumes                  │
        ├────────────────────────────────────────┤
        │ • epack-db (SQLite databases)        │
        │ • epack-logs (Application logs)      │
        │ • epack-sessions (Flask sessions)    │
        │ • epack-cache (Cache files)          │
        │ • epack-uploads (User uploads)       │
        │ • epack-input (Video input)          │
        │ • epack-output (Video output)        │
        └───────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- Python 3.10 + Flask
- OpenCV (Computer Vision)
- MediaPipe (Hand Detection)
- APScheduler (Background Jobs)
- Google Cloud APIs

**Frontend:**
- Next.js 15 (App Router)
- React 19
- Chakra UI
- TypeScript

## 🔧 Initial Setup

### 1. Environment Configuration

```bash
# Create .env file from template
cp .env.docker.example .env
```

### 2. Generate Security Keys (CRITICAL)

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

### 3. Edit .env File

Open `.env` and update these critical variables:

```bash
# Security (REQUIRED - paste generated keys)
SECRET_KEY=<your_generated_secret_key_here>
ENCRYPTION_KEY=<your_generated_encryption_key_here>

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8080

# Docker flags
VTRACK_IN_DOCKER=true
VTRACK_INPUT_DIR=/app/resources/input
VTRACK_OUTPUT_DIR=/app/resources/output
VTRACK_SESSION_DIR=/app/var/flask_session
```

### 4. Build Docker Images

```bash
# Backend (takes 5-10 minutes)
docker build --platform linux/arm64 -t epack-backend:phase2 ./backend

# Frontend (takes 2-3 minutes)
docker build --platform linux/arm64 -t epack-frontend:phase3 ./frontend
```

### 5. Start the Application

```bash
# Production mode (detached)
./start.sh

# Or with logs attached
./start.sh --attach
```

## 🎮 Usage

### Starting Services

```bash
# Production mode
./start.sh

# Development mode (with live code reload)
./start.sh --dev

# With logs attached
./start.sh --attach
```

### Stopping Services

```bash
# Stop services, keep data
./stop.sh

# Stop and remove volumes (WARNING: Data loss!)
./stop.sh --volumes

# Stop development stack
./stop.sh --dev
```

### Viewing Logs

```bash
# Follow all logs
./logs.sh

# Backend only
./logs.sh backend

# Frontend only
./logs.sh frontend

# Show last 500 lines
./logs.sh --tail 500

# With timestamps
./logs.sh --timestamps
```

### Checking Status

```bash
# Full system status
./status.sh

# Shows:
# - Container status and health
# - Resource usage (CPU, Memory)
# - Docker images
# - Volumes and their sizes
# - Network information
# - Access URLs
```

### Manual Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart backend

# View service status
docker-compose ps

# Execute command in container
docker exec -it epack-backend bash
docker exec -it epack-frontend sh
```

## 🛠️ Helper Scripts

### start.sh
**Purpose**: Start ePACK application stack

**Options:**
- `--dev, --development`: Start in development mode
- `--attach, -a`: Run in attached mode (show logs)
- `--help, -h`: Show help message

**Examples:**
```bash
./start.sh                    # Production, detached
./start.sh --dev              # Development mode
./start.sh --attach           # Production with logs
./start.sh --dev --attach     # Dev with logs
```

### stop.sh
**Purpose**: Stop ePACK application stack

**Options:**
- `--volumes, -v`: Remove volumes (data loss!)
- `--orphans, -o`: Remove orphan containers
- `--dev`: Stop development stack
- `--all, -a`: Remove volumes and orphans
- `--help, -h`: Show help message

**Examples:**
```bash
./stop.sh               # Stop, keep data
./stop.sh --volumes     # Stop and remove data
./stop.sh --dev         # Stop dev stack
./stop.sh --all         # Clean everything
```

### logs.sh
**Purpose**: View logs from containers

**Options:**
- `backend, be`: Show backend logs only
- `frontend, fe`: Show frontend logs only
- `--no-follow, -n`: Don't follow (exit after display)
- `--tail, -t N`: Show last N lines
- `--all, -a`: Show all logs
- `--timestamps`: Show timestamps
- `--help, -h`: Show help message

**Examples:**
```bash
./logs.sh                 # All logs, follow
./logs.sh backend         # Backend only
./logs.sh frontend -n     # Frontend, no follow
./logs.sh --tail 500      # Last 500 lines
./logs.sh --timestamps    # With timestamps
```

### status.sh
**Purpose**: Check system status

**No options**, just run:
```bash
./status.sh
```

**Shows:**
- Container status (running/stopped)
- Resource usage (CPU, RAM, Network, Disk)
- Health checks (backend v2.1.0, frontend)
- Docker images and sizes
- Volumes and usage
- Network information
- Access URLs
- Quick commands

## 💾 Volumes and Data

### Volume List

| Volume Name | Mount Point | Purpose | Backup Priority |
|------------|-------------|---------|----------------|
| `epack-db` | `/app/database` | SQLite databases | **CRITICAL** |
| `epack-logs` | `/app/logs` | Application logs | Medium |
| `epack-sessions` | `/app/var/flask_session` | Flask sessions | Low |
| `epack-cache` | `/app/var/cache` | Cache files | Low |
| `epack-uploads` | `/app/var/uploads` | User uploads | High |
| `epack-input` | `/app/resources/input` | Video input | High |
| `epack-output` | `/app/resources/output` | Video output | **CRITICAL** |

### Backup Volumes

```bash
# Backup database
docker run --rm \
  -v epack-db:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/db-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# Backup all volumes
for vol in epack-db epack-output epack-input epack-uploads; do
  docker run --rm \
    -v $vol:/data \
    -v $(pwd)/backups:/backup \
    alpine tar czf /backup/$vol-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
done
```

### Restore Volumes

```bash
# Restore database
docker run --rm \
  -v epack-db:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/db-20251112-150000.tar.gz -C /data

# List volume contents
docker run --rm -it -v epack-db:/data alpine ls -la /data

# Access volume shell
docker run --rm -it -v epack-db:/data alpine sh
```

### Volume Management

```bash
# List volumes
docker volume ls | grep vtrack

# Inspect volume
docker volume inspect epack-db

# Check volume size
docker system df -v | grep vtrack

# Remove unused volumes (WARNING: Data loss!)
docker volume prune
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error**: `port is already allocated`

**Solution**:
```bash
# Find process using port
lsof -i :3000
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use different ports in .env
FLASK_PORT=8081
PORT=3001
```

#### 2. Images Not Found

**Error**: `pull access denied for epack-backend`

**Solution**:
```bash
# Build images first
docker build --platform linux/arm64 -t epack-backend:phase2 ./backend
docker build --platform linux/arm64 -t epack-frontend:phase3 ./frontend
```

#### 3. Permission Errors

**Error**: `Permission denied: '/app/database'`

**Solution**: Already fixed in Phase 2 - images run as non-root user (appuser:1001, nextjs:1001)

#### 4. Backend Unhealthy

**Check logs**:
```bash
./logs.sh backend --tail 100
```

**Common causes**:
- Missing environment variables (.env not configured)
- Database initialization error
- Port conflict

#### 5. Frontend Can't Connect to Backend

**Check network**:
```bash
docker exec epack-frontend wget -O- http://backend:8080/health
```

**Verify environment**:
```bash
docker exec epack-frontend env | grep NEXT_PUBLIC_API_URL
# Should show: NEXT_PUBLIC_API_URL=http://backend:8080
```

#### 6. Out of Disk Space

**Check disk usage**:
```bash
docker system df
```

**Clean up**:
```bash
# Remove unused images
docker image prune -a

# Remove build cache
docker builder prune -a

# Remove stopped containers
docker container prune

# Clean everything (WARNING!)
docker system prune -a --volumes
```

### Debug Commands

```bash
# Check container health
docker inspect epack-backend --format='{{.State.Health.Status}}'

# View health check logs
docker inspect epack-backend --format='{{json .State.Health}}' | python3 -m json.tool

# Enter backend container
docker exec -it epack-backend bash

# Enter frontend container
docker exec -it epack-frontend sh

# Check environment variables
docker exec epack-backend env
docker exec epack-frontend env

# Test API from inside frontend
docker exec epack-frontend wget -O- http://backend:8080/health

# Check network connectivity
docker network inspect epack-network
```

## ⚙️ Advanced Configuration

### Custom Ports

Edit `.env`:
```bash
FLASK_PORT=8081
PORT=3001
```

Edit `docker-compose.yml`:
```yaml
backend:
  ports:
    - "8081:8080"
frontend:
  ports:
    - "3001:3000"
```

### Resource Limits

Uncomment in `docker-compose.yml`:
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
```

### Development Mode

Use `docker-compose.dev.yml` for:
- Live code reloading
- Source code mounted as volumes
- Debug mode enabled
- Separate dev volumes

```bash
# Start dev mode
./start.sh --dev

# Or manually
docker-compose -f docker-compose.dev.yml up
```

### Environment Variables

See `.env.docker.example` for all available variables:
- Security keys (REQUIRED)
- Database paths
- API endpoints
- Feature flags
- Debug settings
- Cloud integrations

## 📚 Documentation

### Quick Reference
- **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** - Fast setup reference
- **[This File](DOCKER_README.md)** - Comprehensive guide

### Detailed Guides
- **[DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md)** - Complete Docker Compose guide (14KB)
- **[DOCKER_COMPOSE_IMPLEMENTATION.md](DOCKER_COMPOSE_IMPLEMENTATION.md)** - Implementation details (14KB)

### Configuration Files
- **`.env.docker.example`** - Environment template (423 lines)
- **`docker-compose.yml`** - Production configuration
- **`docker-compose.dev.yml`** - Development configuration

### Dockerfiles
- **`backend/Dockerfile`** - Backend multi-stage build (123 lines)
- **`frontend/Dockerfile`** - Frontend multi-stage build (93 lines)
- **`frontend/Dockerfile.dev`** - Frontend development build

## 🎯 Best Practices

1. **Security**
   - Never commit `.env` file
   - Generate unique keys for each deployment
   - Use non-root users in containers (already configured)

2. **Backups**
   - Backup `epack-db` volume regularly (CRITICAL)
   - Backup `epack-output` volume (processed videos)
   - Keep backup scripts automated

3. **Monitoring**
   - Use `./status.sh` regularly
   - Monitor disk space: `docker system df`
   - Check logs: `./logs.sh`

4. **Updates**
   - Rebuild images after code changes
   - Test in dev mode first: `./start.sh --dev`
   - Backup before major updates

5. **Performance**
   - Backend: ~112MB RAM (typical)
   - Frontend: ~47MB RAM (typical)
   - Monitor with: `docker stats`

## 🐛 Known Issues

1. **License Warning**: "WARNING: License expires in 29 days"
   - **Impact**: Informational only, does not affect functionality
   - **Fix**: Renew license through application UI

2. **Docker Compose Version Warning**: `version: '3.8' is obsolete`
   - **Impact**: None, warning only
   - **Status**: Fixed in docker-compose.yml (version removed)

## 📞 Support

### Getting Help
- Check logs: `./logs.sh`
- Check status: `./status.sh`
- Review documentation in this directory

### Reporting Issues
When reporting issues, include:
```bash
# System info
./status.sh > system-status.txt

# Recent logs
./logs.sh --no-follow --tail 200 > logs.txt

# Docker info
docker version > docker-info.txt
docker info >> docker-info.txt
```

## 📝 Change Log

### Phase 3 - Frontend Complete (2025-11-12)
- ✅ Frontend Docker image built (211MB)
- ✅ Next.js 15 with Suspense fixes
- ✅ All TypeScript errors resolved
- ✅ Standalone output verified

### Phase 4 - Integration Complete (2025-11-12)
- ✅ Docker Compose production setup
- ✅ Docker Compose development setup
- ✅ 7 persistent volumes configured
- ✅ Network connectivity verified
- ✅ Health checks passing
- ✅ Full stack integration tested

### Phase 5 - Helper Scripts Complete (2025-11-12)
- ✅ start.sh (production & dev modes)
- ✅ stop.sh (with volume management)
- ✅ logs.sh (flexible log viewer)
- ✅ status.sh (comprehensive status)

---

**Last Updated**: 2025-11-12
**Version**: 1.0.0
**Status**: Production Ready ✅
