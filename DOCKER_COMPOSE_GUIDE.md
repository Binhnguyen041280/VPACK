# ePACK Docker Compose Deployment Guide

Complete guide for deploying ePACK application using Docker Compose with pre-built images or development mode.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Production)](#quick-start-production)
3. [Development Mode](#development-mode)
4. [Configuration](#configuration)
5. [Volume Management](#volume-management)
6. [Networking](#networking)
7. [Health Checks](#health-checks)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## Prerequisites

### Required Software

- **Docker Desktop** 4.0+ (for Mac M1/M2/M3)
- **Docker Compose** 2.0+
- **Git** (for cloning repository)

### Verify Installation

```bash
docker --version          # Should be 20.10+
docker-compose --version  # Should be 2.0+
docker info               # Check Docker is running
```

### Pre-built Docker Images

Ensure these images exist locally:

```bash
# Check images
docker images | grep vtrack

# Expected output:
# epack-backend     phase2    <image-id>   <size>
# epack-frontend    phase3    <image-id>   <size>
```

If images don't exist, build them first:

```bash
# Build backend
cd backend
docker build -t epack-backend:phase2 --platform linux/arm64 .

# Build frontend
cd ../frontend
docker build -t epack-frontend:phase3 --platform linux/arm64 .
```

---

## Quick Start (Production)

### Step 1: Prepare Environment File

```bash
# Copy environment template
cp .env.docker.example .env

# Edit configuration
nano .env  # or use your preferred editor
```

### Step 2: Generate Security Keys

**REQUIRED** - Generate secure keys before first run:

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Copy the generated keys to your `.env` file.

### Step 3: Configure Required Variables

Edit `.env` and replace placeholders:

```bash
# REQUIRED - Security keys (use generated values above)
SECRET_KEY=<YOUR_GENERATED_SECRET_KEY>
ENCRYPTION_KEY=<YOUR_GENERATED_ENCRYPTION_KEY>

# REQUIRED - API URL (for browser access)
NEXT_PUBLIC_API_URL=http://localhost:8080

# OPTIONAL - Email configuration (for license delivery)
SMTP_USERNAME=<YOUR_EMAIL>
SMTP_PASSWORD=<YOUR_APP_PASSWORD>
ADMIN_EMAIL=<ADMIN_EMAIL>
```

### Step 4: Start Services

```bash
# Start all services in detached mode
docker-compose up -d

# View startup logs
docker-compose logs -f

# Wait for services to be healthy (30-60 seconds)
```

### Step 5: Verify Deployment

```bash
# Check service status
docker-compose ps

# Expected output:
# NAME                 STATUS         PORTS
# epack-backend       Up (healthy)   0.0.0.0:8080->8080/tcp
# epack-frontend      Up (healthy)   0.0.0.0:3000->3000/tcp

# Test backend health
curl http://localhost:8080/health

# Test frontend (in browser)
open http://localhost:3000
```

### Step 6: Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **Health Check**: http://localhost:8080/health

---

## Development Mode

### Prerequisites for Development

Development mode includes live code reloading for both backend and frontend.

### Start Development Environment

```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up

# Or detached mode
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

### Development Features

**Backend:**
- Flask debug mode enabled
- Auto-reload on Python file changes
- Source code mounted from `./backend`
- Debug logging enabled

**Frontend:**
- Next.js development server
- Hot Module Replacement (HMR)
- Fast Refresh for React components
- Source code mounted from `./frontend`

### Development Workflow

```bash
# Make code changes in your editor
# Changes are automatically reflected in containers

# Restart specific service
docker-compose -f docker-compose.dev.yml restart backend

# Rebuild after dependency changes
docker-compose -f docker-compose.dev.yml up --build

# Access shell for debugging
docker-compose -f docker-compose.dev.yml exec backend bash
docker-compose -f docker-compose.dev.yml exec frontend sh
```

---

## Configuration

### Environment Variables Reference

#### Docker Compose Settings

```bash
# Project configuration
COMPOSE_PROJECT_NAME=vtrack
DEPLOYMENT_MODE=production
DOCKER_PLATFORM=linux/arm64

# Pre-built images
BACKEND_IMAGE=epack-backend:phase2
FRONTEND_IMAGE=epack-frontend:phase3
```

#### Required Variables

```bash
# Security (REQUIRED)
SECRET_KEY=<GENERATE_WITH_COMMAND>
ENCRYPTION_KEY=<GENERATE_WITH_COMMAND>

# Flask settings
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
FLASK_ENV=production
FLASK_DEBUG=false

# Frontend API URL (browser-accessible)
NEXT_PUBLIC_API_URL=http://localhost:8080
```

#### Optional Variables

```bash
# Email configuration (for license delivery)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<YOUR_EMAIL>
SMTP_PASSWORD=<YOUR_APP_PASSWORD>

# Google Drive sync (optional)
GOOGLE_DRIVE_AUTO_SYNC=false
CLOUD_SYNC_ENABLED=false
```

### Port Configuration

Default ports (can be changed in docker-compose.yml):

```yaml
# Backend
ports:
  - "8080:8080"  # Change left side to modify host port

# Frontend
ports:
  - "3000:3000"  # Change left side to modify host port
```

---

## Volume Management

### Named Volumes

Docker Compose creates persistent named volumes for data storage:

| Volume Name | Container Path | Purpose |
|-------------|----------------|---------|
| epack-db | /app/database | SQLite databases, backups |
| epack-logs | /app/logs | Application logs |
| epack-sessions | /app/var/flask_session | Flask session storage |
| epack-cache | /app/var/cache | Temporary cache files |
| epack-uploads | /app/var/uploads | File uploads |
| epack-input | /app/resources/input | Video input resources |
| epack-output | /app/resources/output | Video output/recordings |

### Volume Commands

```bash
# List volumes
docker volume ls | grep vtrack

# Inspect volume
docker volume inspect epack-db

# View volume contents
docker run --rm -v epack-db:/data alpine ls -lah /data

# Backup volume
docker run --rm \
  -v epack-db:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/epack-db-$(date +%Y%m%d).tar.gz -C /data .

# Restore volume
docker run --rm \
  -v epack-db:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/epack-db-20251112.tar.gz -C /data

# Remove all volumes (WARNING: Data loss!)
docker-compose down -v
```

### Backup Strategy

**Automated Backup Script:**

```bash
#!/bin/bash
# backup-vtrack.sh

BACKUP_DIR="./backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup all volumes
for vol in epack-db epack-logs epack-sessions epack-uploads epack-input epack-output; do
  echo "Backing up $vol..."
  docker run --rm \
    -v $vol:/data \
    -v $BACKUP_DIR:/backup \
    alpine tar czf /backup/$vol.tar.gz -C /data .
done

echo "Backup completed: $BACKUP_DIR"
```

---

## Networking

### Network Architecture

```
┌─────────────────────────────────────────┐
│  Host Machine (Mac)                     │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  epack-network (bridge)         │  │
│  │                                  │  │
│  │  ┌──────────┐    ┌────────────┐ │  │
│  │  │ backend  │    │  frontend  │ │  │
│  │  │  :8080   │◄───┤   :3000    │ │  │
│  │  └────┬─────┘    └──────┬─────┘ │  │
│  │       │                 │       │  │
│  └───────┼─────────────────┼───────┘  │
│          │                 │          │
│     localhost:8080   localhost:3000   │
└──────────┴─────────────────┴──────────┘
```

### Service Communication

**Container-to-Container (Internal):**
```bash
# Frontend to Backend (inside containers)
http://backend:8080/api/endpoint
```

**Browser-to-Container (External):**
```bash
# From host machine browser
http://localhost:8080/api/endpoint  # Backend
http://localhost:3000               # Frontend
```

**Remote Access:**
```bash
# Update .env for remote access
NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP:8080

# Ensure firewall allows ports 3000 and 8080
```

### Network Troubleshooting

```bash
# Check network
docker network inspect epack-network

# Test connectivity from frontend to backend
docker-compose exec frontend wget -O- http://backend:8080/health

# Check container IPs
docker-compose exec backend hostname -i
docker-compose exec frontend hostname -i
```

---

## Health Checks

### Backend Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Frontend Health Check

```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### Check Service Health

```bash
# View health status
docker-compose ps

# Detailed health info
docker inspect epack-backend --format='{{.State.Health.Status}}'
docker inspect epack-frontend --format='{{.State.Health.Status}}'

# View health check logs
docker inspect epack-backend --format='{{json .State.Health}}' | jq
```

---

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Check port conflicts
lsof -i :8080
lsof -i :3000

# Kill conflicting processes
kill -9 <PID>
```

#### 2. Backend Returns 500 Error

```bash
# Check backend logs
docker-compose logs -f backend

# Check environment variables
docker-compose exec backend env | grep -E "(SECRET_KEY|ENCRYPTION_KEY|FLASK_)"

# Access backend shell
docker-compose exec backend bash
python -c "import cv2, mediapipe; print('OK')"
```

#### 3. Frontend Can't Connect to Backend

```bash
# Check NEXT_PUBLIC_API_URL
docker-compose exec frontend env | grep NEXT_PUBLIC_API_URL

# Should be: http://localhost:8080 (for browser access)
# NOT: http://backend:8080 (that's for internal container communication)

# Test backend from host
curl http://localhost:8080/health
```

#### 4. Permission Denied on Volumes

```bash
# Fix volume permissions
docker-compose down
docker volume rm epack-db epack-logs
docker-compose up -d

# Or manually fix permissions
docker run --rm -v epack-db:/data alpine chmod -R 777 /data
```

#### 5. Images Not Found

```bash
# List images
docker images | grep vtrack

# If missing, build them
docker build -t epack-backend:phase2 --platform linux/arm64 ./backend
docker build -t epack-frontend:phase3 --platform linux/arm64 ./frontend
```

#### 6. Healthy Check Fails

```bash
# Check health endpoint manually
docker-compose exec backend curl http://localhost:8080/health

# Check if service is listening
docker-compose exec backend netstat -tulpn | grep 8080

# Increase start_period in docker-compose.yml if needed
```

### Debug Mode

Enable detailed logging:

```bash
# Edit .env
FLASK_DEBUG=true
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Restart
docker-compose restart backend
docker-compose logs -f backend
```

---

## Maintenance

### Update Images

```bash
# Pull latest images (if using registry)
docker-compose pull

# Or rebuild local images
docker build -t epack-backend:phase2 --platform linux/arm64 ./backend
docker build -t epack-frontend:phase3 --platform linux/arm64 ./frontend

# Restart with new images
docker-compose down
docker-compose up -d
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes (WARNING: Data loss!)
docker-compose down -v

# Remove all unused Docker resources
docker system prune -a

# Remove specific volumes
docker volume rm epack-cache epack-sessions
```

### Monitor Resources

```bash
# View resource usage
docker stats

# View disk usage
docker system df

# View container logs size
docker-compose logs --tail=100 backend | wc -l
```

### Rotate Logs

```bash
# Clear logs without stopping containers
docker-compose logs --no-log-prefix backend > /dev/null
docker-compose logs --no-log-prefix frontend > /dev/null

# Or configure log rotation in docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Production Best Practices

### Security

1. **Environment Variables:**
   ```bash
   # Never commit .env to version control
   echo ".env" >> .gitignore

   # Restrict file permissions
   chmod 600 .env
   ```

2. **Secrets Management:**
   ```bash
   # Use Docker secrets for production
   echo "your-secret-key" | docker secret create vtrack_secret_key -
   ```

3. **Network Security:**
   ```bash
   # Use firewall rules
   sudo ufw allow 8080/tcp
   sudo ufw allow 3000/tcp
   ```

### Monitoring

```bash
# Install monitoring tools
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# View metrics
docker-compose exec backend curl http://localhost:8080/metrics
```

### Backup Automation

```bash
# Create cron job for daily backups
0 2 * * * /path/to/backup-vtrack.sh
```

---

## Support

### Logs Location

- **Backend logs**: `epack-logs` volume → `/app/logs/vtrack.log`
- **Frontend logs**: `docker-compose logs frontend`
- **Container logs**: `docker-compose logs -f`

### Useful Commands

```bash
# View all services
docker-compose ps

# Restart specific service
docker-compose restart backend

# Scale services (if supported)
docker-compose up -d --scale backend=2

# Execute command in container
docker-compose exec backend python -c "print('test')"

# Copy files from container
docker-compose cp backend:/app/logs/vtrack.log ./local-logs.log
```

---

## Summary

This Docker Compose setup provides:

- **Production-ready deployment** with pre-built images
- **Development mode** with live code reloading
- **Persistent storage** with named volumes
- **Health checks** for both services
- **Network isolation** with bridge networking
- **Easy maintenance** with simple commands

For additional help, refer to:
- Docker documentation: https://docs.docker.com/
- Docker Compose documentation: https://docs.docker.com/compose/
- ePACK repository: [Your Repository URL]
