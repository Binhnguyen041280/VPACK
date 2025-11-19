# ePACK Backend - Docker Deployment Guide

## Critical Fixes Applied

This deployment addresses the following critical issues:

### 1. Flask Session Permission Error (FIXED)
**Problem**: `PermissionError: [Errno 13] Permission denied: '/flask_session'`

**Solution**:
- Flask session directory now uses `/app/var/flask_session` in Docker mode
- Directory is created during image build with proper permissions
- Controlled by `VTRACK_SESSION_DIR` environment variable

### 2. Hardcoded macOS Paths (FIXED)
**Problem**: Warning about `/Users/annhu/Movies/VTrack/Output` in Docker

**Solution**:
- Docker mode now bypasses database path configuration
- Uses environment variables and Docker-compatible defaults
- All paths respect `VTRACK_IN_DOCKER=true` flag

---

## Quick Start

### 1. Build the Docker Image

```bash
cd /Users/annhu/vtrack_app/ePACK/backend
docker build -t epack-backend:latest .
```

### 2. Create Environment File

```bash
cp .env.docker.example .env.docker

# Edit .env.docker and set:
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - Other configuration as needed
```

### 3. Create Required Directories

```bash
mkdir -p database logs resources/input resources/output
```

### 4. Run the Container

```bash
docker run -d \
  --name epack-backend \
  -p 8080:8080 \
  --env-file .env.docker \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/resources/input:/app/resources/input \
  -v $(pwd)/resources/output:/app/resources/output \
  epack-backend:latest
```

### 5. Verify Deployment

```bash
# Check container logs
docker logs epack-backend

# Check health endpoint
curl http://localhost:8080/health

# Expected output: {"status": "healthy", ...}
```

---

## Using Docker Compose (Recommended)

### 1. Copy Example Configuration

```bash
cp docker-compose.example.yml docker-compose.yml
```

### 2. Edit docker-compose.yml

```yaml
# Update the SECRET_KEY in environment section
- SECRET_KEY=your_secret_key_here_change_me  # CHANGE THIS!
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Check Status

```bash
# View logs
docker-compose logs -f epack-backend

# Check health
docker-compose exec epack-backend curl http://localhost:8080/health
```

---

## Directory Structure in Docker

```
/app/
├── database/           # SQLite database (volume mount)
├── logs/              # Application logs (volume mount)
├── resources/
│   ├── input/         # Video input files (volume mount)
│   └── output/        # Processed clips (volume mount)
├── var/
│   ├── flask_session/ # Flask session storage (writable)
│   ├── cache/         # Temporary cache
│   └── uploads/       # File uploads
├── keys/              # OAuth credentials (optional)
└── models/            # AI models
    └── wechat_qr/     # WeChat QR detection models
```

---

## Environment Variables Reference

### Critical Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VTRACK_IN_DOCKER` | `true` | **MUST BE SET** - Enables Docker-compatible paths |
| `VTRACK_SESSION_DIR` | `/app/var/flask_session` | Flask session storage directory |
| `VTRACK_OUTPUT_DIR` | `/app/resources/output` | Processed video output directory |
| `VTRACK_INPUT_DIR` | `/app/resources/input` | Video input directory |
| `SECRET_KEY` | *required* | Flask session encryption key |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/app/database/vtrack.db` | SQLite database file path |
| `LOG_LEVEL` | `INFO` | Logging level |
| `TZ` | `UTC` | Container timezone |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend URL for CORS |

---

## Troubleshooting

### Issue: Permission Denied Errors

**Symptom**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
1. Verify directories are writable by UID 1001 (appuser)
   ```bash
   chown -R 1001:1001 database logs resources
   ```

2. Check environment variables:
   ```bash
   docker exec epack-backend env | grep VTRACK
   ```

### Issue: Container Exits Immediately

**Symptom**: Container stops right after starting

**Solution**:
1. Check logs for errors:
   ```bash
   docker logs epack-backend
   ```

2. Verify required environment variables:
   ```bash
   docker exec epack-backend env | grep -E "VTRACK_IN_DOCKER|SECRET_KEY"
   ```

3. Run interactively for debugging:
   ```bash
   docker run -it --rm --env-file .env.docker epack-backend:latest /bin/bash
   ```

### Issue: Database Not Persisting

**Symptom**: Data lost after container restart

**Solution**:
1. Verify volume mount:
   ```bash
   docker inspect epack-backend | grep -A 5 Mounts
   ```

2. Check database directory permissions:
   ```bash
   ls -la database/
   # Should show: drwxr-xr-x ... 1001 1001 ... database
   ```

### Issue: Session Storage Warnings

**Symptom**: Warnings about session directory creation

**Solution**:
1. Verify `VTRACK_SESSION_DIR` is set correctly:
   ```bash
   docker exec epack-backend env | grep VTRACK_SESSION_DIR
   ```

2. Check directory exists and is writable:
   ```bash
   docker exec epack-backend ls -la /app/var/flask_session
   ```

---

## Health Checks

The container includes built-in health checks:

```bash
# Manual health check
curl http://localhost:8080/health

# Expected response (healthy):
{
  "status": "healthy",
  "service": "ePACK Desktop Backend",
  "version": "2.1.0",
  "timestamp": "2025-11-12T10:30:00.000000",
  "modules": {
    "computer_vision": "enabled",
    "batch_processing": "enabled",
    "cloud_sync": "enabled"
  }
}

# Check Docker health status
docker inspect epack-backend | grep -A 5 Health
```

---

## Production Deployment Checklist

- [ ] Generate strong `SECRET_KEY`
- [ ] Set `FLASK_ENV=production`
- [ ] Set `FLASK_DEBUG=false`
- [ ] Configure volume mounts for persistent data
- [ ] Set appropriate timezone (`TZ`)
- [ ] Configure resource limits (CPU, memory)
- [ ] Enable container restart policy
- [ ] Set up log rotation for volume-mounted logs
- [ ] Configure backup for database volume
- [ ] Review and customize CORS settings
- [ ] Enable HTTPS if using reverse proxy
- [ ] Test health check endpoint
- [ ] Monitor container resource usage

---

## Upgrading

### Pull Latest Code

```bash
cd /Users/annhu/vtrack_app/ePACK/backend
git pull origin main
```

### Rebuild Image

```bash
docker build -t epack-backend:latest .
```

### Restart Container

```bash
# Using docker run
docker stop epack-backend
docker rm epack-backend
# Then run the container again (see Quick Start)

# Using docker-compose
docker-compose down
docker-compose up -d --build
```

---

## Performance Tuning

### Resource Limits

Adjust based on your video processing needs:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Increase for faster processing
      memory: 8G       # Increase for large videos
    reservations:
      cpus: '2.0'
      memory: 4G
```

### Worker Configuration

Set environment variables:

```bash
FLASK_WORKERS=4           # Concurrent request handlers
MAX_PROCESSING_JOBS=2     # Concurrent video processing jobs
```

---

## Security Considerations

1. **Secret Key**: Always use a strong, randomly generated `SECRET_KEY`
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **File Permissions**: Ensure mounted volumes have restrictive permissions
   ```bash
   chmod 700 database logs
   ```

3. **Network Isolation**: Use Docker networks to isolate services
   ```yaml
   networks:
     - epack-network
   ```

4. **Credentials**: Never commit `.env.docker` or credentials to version control

---

## Support

For issues or questions:
1. Check application logs: `docker logs epack-backend`
2. Review this guide's Troubleshooting section
3. Verify environment variables are set correctly
4. Check container health status

---

**Last Updated**: 2025-11-12
**Version**: 2.1.0
