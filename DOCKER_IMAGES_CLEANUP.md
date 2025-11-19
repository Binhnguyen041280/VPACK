# Docker Images Cleanup Guide

## Current Docker Images Status

### ✅ PRODUCTION IMAGES (KEEP - Đang sử dụng)

| Image | Tag | ID | Size | Status |
|-------|-----|----|----|--------|
| `epack-backend` | **phase2** | `e39d94a6e574` | 1.94GB | ✅ **IN USE** (docker-compose.yml) |
| `epack-frontend` | **phase3** | `44d2109e31ff` | 211MB | ✅ **IN USE** (docker-compose.yml) |

**Location**: Local Docker Registry
**Usage**: Referenced in `docker-compose.yml`

---

### ⚠️ DUPLICATE/OLD IMAGES (Can be removed)

| Image | Tag | ID | Size | Reason |
|-------|-----|----|----|--------|
| `epack-backend` | v2 | `e39d94a6e574` | 1.94GB | ⚠️ **DUPLICATE** - Same as phase2 |
| `epack-backend` | fixed | `93a24d631bb2` | 1.94GB | ⚠️ **OLD VERSION** |
| `epack-frontend` | production | `139229ccee75` | 208MB | ⚠️ **OLD VERSION** |
| `epack-frontend-deps` | latest | `42dcf5e11830` | 989MB | ⚠️ **BUILD ARTIFACT** |

**Total wasted space**: ~4.13GB

---

## Cleanup Commands

### Option 1: Remove Specific Old Images (Recommended)

```bash
# Remove duplicate backend tag (same image as phase2)
docker rmi epack-backend:v2

# Remove old backend version
docker rmi epack-backend:fixed

# Remove old frontend version
docker rmi epack-frontend:production

# Remove intermediate build artifact
docker rmi epack-frontend-deps:latest
```

**Space saved**: ~4.13GB

### Option 2: Auto Cleanup (Safe - keeps tagged images in use)

```bash
# Remove dangling images
docker image prune

# Remove all unused images (not in containers)
docker image prune -a --filter "label!=keep"
```

### Option 3: Manual Verification First

```bash
# List all images with details
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedSince}}"

# Check which images are actually used by containers
docker ps -a --format "{{.Image}}"

# Check docker-compose.yml references
grep "image:" docker-compose.yml
```

---

## Verification After Cleanup

```bash
# Should show only 2 images
docker images | grep vtrack

# Expected output:
# epack-backend    phase2    e39d94a6e574   1.94GB   7 hours ago
# epack-frontend   phase3    44d2109e31ff   211MB    27 minutes ago
```

---

## Safe Cleanup Script

Create and run this script:

```bash
#!/bin/bash
# cleanup-docker-images.sh

echo "🧹 Cleaning up old Docker images..."
echo ""

# Check current disk usage
echo "📊 Current Docker disk usage:"
docker system df
echo ""

# Remove duplicate and old images
echo "🗑️  Removing old images..."

# Remove duplicate tag (same image as phase2)
docker rmi epack-backend:v2 2>/dev/null && echo "✅ Removed epack-backend:v2" || echo "⚠️  epack-backend:v2 not found"

# Remove old backend
docker rmi epack-backend:fixed 2>/dev/null && echo "✅ Removed epack-backend:fixed" || echo "⚠️  epack-backend:fixed not found"

# Remove old frontend
docker rmi epack-frontend:production 2>/dev/null && echo "✅ Removed epack-frontend:production" || echo "⚠️  epack-frontend:production not found"

# Remove build artifact
docker rmi epack-frontend-deps:latest 2>/dev/null && echo "✅ Removed epack-frontend-deps:latest" || echo "⚠️  epack-frontend-deps:latest not found"

echo ""
echo "✅ Cleanup complete!"
echo ""

# Show final disk usage
echo "📊 Final Docker disk usage:"
docker system df
echo ""

# Show remaining images
echo "📦 Remaining vtrack images:"
docker images | grep vtrack || echo "None found"
```

Make executable and run:
```bash
chmod +x cleanup-docker-images.sh
./cleanup-docker-images.sh
```

---

## Image Rebuild Commands (If needed)

If you accidentally remove production images, rebuild with:

```bash
# Rebuild backend
docker build --platform linux/arm64 -t epack-backend:phase2 ./backend

# Rebuild frontend
docker build --platform linux/arm64 -t epack-frontend:phase3 ./frontend
```

---

## Docker Registry Locations

### Local Docker Registry (Default)
- **Linux**: `/var/lib/docker/`
- **macOS**: `~/Library/Containers/com.docker.docker/Data/vms/0/`
- **Windows**: `C:\ProgramData\Docker\`

### View Image Layers
```bash
# Backend layers
docker history epack-backend:phase2

# Frontend layers
docker history epack-frontend:phase3
```

### Export Images (Backup)
```bash
# Export backend
docker save epack-backend:phase2 | gzip > epack-backend-phase2.tar.gz

# Export frontend
docker save epack-frontend:phase3 | gzip > epack-frontend-phase3.tar.gz
```

### Import Images (Restore)
```bash
# Import backend
docker load < epack-backend-phase2.tar.gz

# Import frontend
docker load < epack-frontend-phase3.tar.gz
```

---

## Summary

✅ **Keep**:
- `epack-backend:phase2` (1.94GB) - Production backend
- `epack-frontend:phase3` (211MB) - Production frontend

❌ **Remove**:
- `epack-backend:v2` (duplicate tag)
- `epack-backend:fixed` (old version)
- `epack-frontend:production` (old version)
- `epack-frontend-deps:latest` (build artifact)

💾 **Total space to save**: ~4.13GB

**Recommendation**: Run cleanup script to free up disk space while keeping production images safe.
