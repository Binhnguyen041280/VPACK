# Tổng Kết Fix Lỗi Docker - Custom Path & Local Source

## ✅ ĐÃ HOÀN THÀNH

### PHẦN 1: Cleanup Development Files
- ✅ Xóa `docker-compose.dev.yml` (không cần development mode)
- ✅ Cập nhật `start.sh` - loại bỏ `--dev` option
- ✅ Cập nhật `stop.sh` - loại bỏ `--dev` option

### PHẦN 2: Custom Path - File Upload
**Backend API (`backend/modules/scheduler/program.py`):**
- ✅ Endpoint mới: `POST /api/program/upload-custom-video`
- ✅ Nhận multipart file upload
- ✅ Lưu vào `/app/var/uploads/custom/` trong container
- ✅ Validate file type: mp4, avi, mov, mkv, flv, wmv, webm
- ✅ Auto cleanup file sau khi xử lý xong

**Frontend UI (`frontend/app/program/page.tsx`):**
- ✅ Thay text input → file picker
- ✅ Upload file trước khi start program
- ✅ Hiển thị upload progress
- ✅ Hiển thị file size và tên file đã chọn

**Cách hoạt động:**
1. User chọn video file từ bất kỳ đâu trên máy (file picker)
2. Frontend upload file vào container
3. Backend xử lý file từ container path
4. Tự động cleanup file sau khi xong

### PHẦN 3: Docker Management API
**Backend API (`backend/blueprints/docker_management_bp.py`):**
- ✅ Endpoint mới: `POST /api/docker/update-local-source-mount`
- ✅ Endpoint mới: `GET /api/docker/current-mounts`
- ✅ Có thể update `docker-compose.yml` programmatically
- ✅ Có thể restart container để apply mount mới
- ✅ Path validation để prevent security issues

**Đã thêm dependency:**
- ✅ PyYAML==6.0.2 vào `requirements.txt`

### PHẦN 4: Docker Configuration Updates
**Cập nhật `docker-compose.yml`:**
- ✅ Mount Docker socket: `/var/run/docker.sock:/var/run/docker.sock`
- ✅ Mount docker-compose.yml: `./docker-compose.yml:/app/docker-compose.yml:rw`
- ✅ Backend container có quyền modify docker-compose.yml và restart chính nó

**Đã register blueprint:**
- ✅ Thêm import `docker_bp` vào `backend/app.py`
- ✅ Register `docker_bp` với prefix `/api`

---

## 🚧 CẦN LÀM TIẾP

### 1. Rebuild Docker Image
```bash
# Stop current containers
./stop.sh

# Rebuild backend image với PyYAML dependency
docker build --platform linux/arm64 -t epack-backend:phase2 ./backend

# Start lại containers
./start.sh
```

### 2. Test Custom Path Feature
```bash
# 1. Truy cập http://localhost:3000/program
# 2. Chọn "Custom Path" program
# 3. Chọn video file từ máy
# 4. Chọn camera configuration
# 5. Click "Start Program"
# 6. Verify file được upload và xử lý
```

### 3. Tích hợp Local Source Auto-Mount (TÙY CHỌN)

**⚠️ LƯU Ý:** Feature này có trade-offs:
- ✅ PRO: User không cần mount thủ công
- ❌ CON: Container restart → gián đoạn session ~30 giây
- ❌ CON: User experience không tốt

**Nếu muốn implement:**

**Frontend (`frontend/src/components/canvas/VideoSourceCanvas.tsx`):**
```typescript
// Sau khi user nhập local source path và click save
const handleLocalSourceSave = async (path: string) => {
  try {
    // Call Docker management API
    const response = await fetch('http://localhost:8080/api/docker/update-local-source-mount', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ host_path: path })
    });

    const data = await response.json();

    if (data.success) {
      toast({
        title: 'Success',
        description: 'Container restarting to apply mount... Please wait 30 seconds',
        status: 'info',
        duration: 5000
      });

      // Wait for container restart
      setTimeout(() => {
        // Reload page or reconnect
        window.location.reload();
      }, 30000);
    }
  } catch (error) {
    console.error('Mount update failed:', error);
  }
};
```

**Alternative Approach (RECOMMENDED):**
Thay vì auto-mount, có thể:
1. Hiển thị instructions cho user về cách mount folder thủ công
2. Hoặc yêu cầu user setup mount trong docker-compose.yml một lần duy nhất
3. Custom path (single file) dùng upload → đã implement ✅

---

## 📝 KIẾN TRÚC SAU KHI FIX

### Custom Path (Single Video File)
```
User chọn file → Upload to container → Xử lý → Auto cleanup
                   /app/var/uploads/custom/
```

**Flow:**
1. User: Chọn video từ file picker (bất kỳ đâu trên máy)
2. Frontend: Upload file via `/api/program/upload-custom-video`
3. Backend: Lưu vào `/app/var/uploads/custom/timestamp_filename.mp4`
4. Backend: Xử lý video từ container path
5. Backend: Cleanup file sau khi hoàn thành

### Local Source (Camera Folders)
```
Host folder → Bind mount → Container
/Users/annhu/Movies/VTrack/Input → /app/resources/input
```

**Option A: Manual Mount (HIỆN TẠI):**
```yaml
# docker-compose.yml
volumes:
  - /Users/annhu/Movies/VTrack/Input:/app/resources/input:ro
```
User edit docker-compose.yml thủ công, restart container

**Option B: Auto Mount (CHƯA IMPLEMENT):**
```
User nhập path → API update docker-compose.yml → Restart container → Mount active
```
Trade-off: Container restart → gián đoạn service

---

## 🔒 SECURITY CONSIDERATIONS

### Docker Socket Access
- ⚠️ Backend có quyền control Docker host
- ✅ Chỉ whitelist specific operations (restart, update compose)
- ✅ Path validation để prevent mounting sensitive directories
- ✅ Log tất cả Docker management operations

### File Upload
- ✅ Validate file extensions
- ✅ Max file size: 5GB
- ✅ Secure filename (werkzeug.secure_filename)
- ✅ Auto cleanup sau xử lý

### Bind Mounts
- ✅ Read-only mounts cho local source (`:ro`)
- ✅ Không allow mount system directories (/etc, /sys, /proc)
- ✅ Không allow parent directory traversal (`..`)

---

## 🧪 TEST CHECKLIST

### Custom Path Feature
- [ ] Upload video file nhỏ (< 100MB)
- [ ] Upload video file lớn (> 1GB)
- [ ] Upload file không phải video → expect error
- [ ] Xử lý video → verify progress
- [ ] Xử lý hoàn thành → verify file cleanup
- [ ] Kiểm tra `/app/var/uploads/custom/` trong container rỗng sau khi xong

### Docker Management API
- [ ] Call `/api/docker/current-mounts` → see current volumes
- [ ] Call `/api/docker/update-local-source-mount` với valid path
- [ ] Verify docker-compose.yml được update
- [ ] Verify container restart thành công
- [ ] Call với invalid path → expect validation error

### Production Readiness
- [ ] Build image thành công
- [ ] Container start không lỗi
- [ ] Frontend connect được backend
- [ ] Upload API hoạt động
- [ ] Custom program process video thành công

---

## 📊 FILES MODIFIED

### Backend Files
```
backend/modules/scheduler/program.py         # Upload API + cleanup logic
backend/blueprints/docker_management_bp.py   # NEW: Docker management API
backend/app.py                                # Register docker_bp
backend/requirements.txt                      # Add PyYAML==6.0.2
```

### Frontend Files
```
frontend/app/program/page.tsx                # File upload UI
```

### Docker Files
```
docker-compose.yml                           # Add socket + compose file mounts
docker-compose.dev.yml                       # DELETED
start.sh                                     # Remove dev mode
stop.sh                                      # Remove dev mode
```

### Documentation
```
DOCKER_FIXES_SUMMARY.md                      # NEW: This file
```

---

## 🚀 NEXT STEPS

1. **Rebuild Docker image:**
   ```bash
   ./stop.sh
   docker build --platform linux/arm64 -t epack-backend:phase2 ./backend
   ```

2. **Start containers:**
   ```bash
   ./start.sh
   ```

3. **Test custom path:**
   - Go to http://localhost:3000/program
   - Select "Custom Path"
   - Choose a video file
   - Select camera
   - Start program
   - Verify upload + processing works

4. **Decision on Local Source Auto-Mount:**
   - Nếu muốn: Implement frontend integration (code mẫu ở trên)
   - Nếu không: Document manual mount process cho users
   - Recommended: Manual mount (setup 1 lần, không gián đoạn)

5. **Git commit:**
   ```bash
   git add .
   git commit -m "fix: Implement custom path file upload and Docker management API

   - Replace text input with file picker for custom path
   - Add upload API endpoint with cleanup
   - Add Docker management API for dynamic mounts
   - Mount Docker socket and compose file
   - Add PyYAML dependency
   - Remove dev mode files (docker-compose.dev.yml)"

   git push origin docker-2025-11-12
   ```

---

## ❓ QUÁ TRÌNH RA QUYẾT ĐỊNH

### Tại sao upload file thay vì dynamic bind mount cho Custom Path?
- Custom path = single file, bất kỳ đâu
- Dynamic bind mount phải restart container (30s downtime)
- Upload = instant, no downtime, better UX
- Trade-off: Disk space (nhưng auto cleanup)

### Tại sao vẫn giữ Docker management API nếu không dùng?
- Infrastructure đã ready nếu cần sau này
- Có thể dùng cho local source auto-mount nếu user chấp nhận restart
- API có thể dùng cho các operations khác (backup, logs, etc.)

### Tại sao xóa docker-compose.dev.yml?
- User confirm không cần dev mode
- Tránh nhầm lẫn giữa 2 files
- Simplify deployment process
