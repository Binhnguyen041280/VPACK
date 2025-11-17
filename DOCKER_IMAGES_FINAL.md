# 📦 DOCKER IMAGES CUỐI CÙNG - XÁC NHẬN

## ✅ PRODUCTION IMAGES (Final - Đang sử dụng)

### Backend Production Image
```
Tên:          vtrack-backend:phase2
Image ID:     e39d94a6e574
Size:         1.94GB
Created:      2025-11-12 08:26:55 (7 giờ trước)
Architecture: arm64
OS:           linux
Sử dụng trong: docker-compose.yml (line 27)
```

**Dockerfile location:**
- `backend/Dockerfile` (123 lines, 3-stage build)

**Build command:**
```bash
docker build --platform linux/arm64 -t vtrack-backend:phase2 ./backend
```

**Nội dung:**
- Python 3.10 + Flask
- OpenCV, MediaPipe (Computer Vision)
- APScheduler (Background Jobs)
- Google Cloud APIs
- Non-root user: appuser (uid:1001)

---

### Frontend Production Image
```
Tên:          vtrack-frontend:phase3
Image ID:     44d2109e31ff
Size:         211MB
Created:      2025-11-12 14:43:10 (30 phút trước)
Architecture: arm64
OS:           linux
Sử dụng trong: docker-compose.yml (line 96)
```

**Dockerfile location:**
- `frontend/Dockerfile` (93 lines, 3-stage build)

**Build command:**
```bash
docker build --platform linux/arm64 -t vtrack-frontend:phase3 ./frontend
```

**Nội dung:**
- Next.js 15 + React 19
- Node.js 18 Alpine
- Standalone output (optimized)
- Non-root user: nextjs (uid:1001)

---

## 📍 VỊ TRÍ IMAGES

### Local Docker Registry
- **macOS**: `~/Library/Containers/com.docker.docker/Data/vms/0/`
- Images được Docker Engine quản lý tự động

### Kiểm tra vị trí:
```bash
# Xem chi tiết image
docker image inspect vtrack-backend:phase2
docker image inspect vtrack-frontend:phase3

# Xem layers
docker history vtrack-backend:phase2
docker history vtrack-frontend:phase3
```

---

## 🗂️ IMAGES ĐÃ XÓA (Cleanup hoàn tất)

✅ Đã xóa thành công:
- `vtrack-backend:v2` (duplicate tag)
- `vtrack-backend:fixed` (old version)
- `vtrack-frontend:production` (old version)
- `vtrack-frontend-deps:latest` (build artifact)

**Space freed**: ~4.13GB

---

## 📊 DOCKER DISK USAGE

```
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          4         1         5.126GB   3.182GB (62%)
Containers      1         1         553.7kB   0B (0%)
Local Volumes   9         0         952.6MB   952.6MB (100%)
Build Cache     172       0         21.86GB   21.86GB
```

### Cleanup thêm (nếu cần):
```bash
# Xóa build cache (free 21.86GB)
docker builder prune -a

# Xóa unused volumes (free 952.6MB)
docker volume prune

# Xóa all unused data
docker system prune -a --volumes
```

---

## 🚀 KHỞI ĐỘNG CONTAINERS VỚI IMAGES CUỐI CÙNG

### Cách 1: Docker Compose (Recommended)
```bash
# Production mode
./start.sh

# Hoặc manual
docker-compose up -d
```

### Cách 2: Docker Run (Manual)
```bash
# Backend
docker run -d \
  --name vtrack-backend \
  --platform linux/arm64 \
  -p 8080:8080 \
  -e VTRACK_IN_DOCKER=true \
  vtrack-backend:phase2

# Frontend
docker run -d \
  --name vtrack-frontend \
  --platform linux/arm64 \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8080 \
  vtrack-frontend:phase3
```

---

## 💾 BACKUP IMAGES

### Export images (để sao lưu hoặc chuyển máy)
```bash
# Backend
docker save vtrack-backend:phase2 | gzip > vtrack-backend-phase2.tar.gz

# Frontend
docker save vtrack-frontend:phase3 | gzip > vtrack-frontend-phase3.tar.gz
```

### Import images
```bash
# Backend
docker load < vtrack-backend-phase2.tar.gz

# Frontend
docker load < vtrack-frontend-phase3.tar.gz
```

---

## 🔍 VERIFY IMAGES

### Check images exist
```bash
docker images | grep vtrack

# Expected output:
# vtrack-frontend   phase3   44d2109e31ff   30 minutes ago   211MB
# vtrack-backend    phase2   e39d94a6e574   7 hours ago      1.94GB
```

### Test images
```bash
# Test backend
docker run --rm -it vtrack-backend:phase2 python --version

# Test frontend
docker run --rm -it vtrack-frontend:phase3 node --version
```

---

## 📝 TÓM TẮT

✅ **Images cuối cùng đã được xác nhận**:
1. `vtrack-backend:phase2` (1.94GB) - Backend production
2. `vtrack-frontend:phase3` (211MB) - Frontend production

✅ **Images cũ đã xóa**: Tiết kiệm ~4.13GB

✅ **Vị trí**: Local Docker Registry (managed by Docker Engine)

✅ **Sử dụng**: Trong `docker-compose.yml`

✅ **Trạng thái**: PRODUCTION READY

---

**Cập nhật**: 2025-11-12 15:15
**Status**: ✅ Images cleaned up and verified
