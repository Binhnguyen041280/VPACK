# V_TRACK ACTION PLAN - CLAUDE CODE EDITION
## Kế Hoạch Thực Hiện với Claude Code làm chính

**Version:** 3.0 - Revised After User Survey
**Ngày:** 2025-10-31
**Executor:** Claude Code (với full agents + MCP tools)
**Supporter:** User (review & approve)
**Timeline:** 2 tuần (36 giờ = 6h/ngày x 6 ngày)

---

## 📋 KHẢO SÁT TRƯỚC KHI LẬP KẾ HOẠCH

### Mục đích khảo sát:
Thay vì áp dụng "lý thuyết framework" chung chung, tôi đã hỏi bạn 55 câu hỏi để hiểu rõ:
- Mục đích sử dụng thực tế
- Khách hàng là ai
- Timeline cụ thể
- Lo lắng gì nhất
- Ưu tiên công việc nào

---

### 📊 TÓM TẮT KẾT QUẢ KHẢO SÁT

| Câu hỏi | Trả lời |
|---------|---------|
| **Q1. Mục đích?** | B - Bán cho khách hàng (thương mại) |
| **Q2. Khách hàng?** | A - Công ty/doanh nghiệp |
| **Q3. Quan trọng nhất?** | A - **Ổn định** (chạy 24/7 không crash) |
| **Q4. Deploy online?** | Không - Sản phẩm local webapp |
| **Q5. Timeline?** | A - **1-2 tuần (urgent)** |
| **Q6. Thời gian/ngày?** | **6 giờ/ngày** |
| **Q7. Lo lắng gì?** | A - **Lo crash khi chạy lâu** |
| **Q8. Cải thiện trước?** | **Hoàn thiện để user test** |
| **Q15. Feature quan trọng?** | A - **Video processing** (core) |
| **Q16. Test 24h chưa?** | B - Chạy vài giờ, chưa test 24h đầy đủ |
| **Q17. Đã gặp crash?** | Không crash (fix ngay nên không biết còn crash không) |
| **Q18. Cần tài liệu?** | A - User Manual chi tiết (PDF/video) |
| **Q20. Hoàn thành gì?** | C - Có đầy đủ tài liệu + installer |
| **Q21. Sau 1-2 tuần?** | D - Cho test và đưa ra thị trường |
| **Q22. Lo lắng nhất?** | A - Crash giữa chừng → khách bỏ |
| **Q25. Hiện tại cài sao?** | Chưa có bộ cài, chỉ dev |
| **Q26. Installer mong đợi?** | .exe hay Docker - miễn tiện nhanh dễ |
| **Q27. Khách cài gì trước?** | D - Installer tự động cài hết |
| **Q29. Tài liệu cần gì?** | D - Tất cả (Installation + User + Troubleshooting) |
| **Q30. Dạng tài liệu?** | PDF, video, hoặc AI support |
| **Q32. Xử lý nhiều?** | Không biết - Đã test 5 video x 4GB |
| **Q33. Test ổn định?** | A - Script test tự động |
| **Q34. Performance?** | 1 video 30 phút → 7 phút (Mac M1) |
| **Q35. Log auto-send?** | C - Có log, khách tự gửi |
| **Q36. Log đủ info?** | A - Log chi tiết lắm |
| **Q39. Feature phức tạp?** | Processing - tự xây dựng, dễ không ổn định |
| **Q40. Tắt features?** | D - Tất cả đều quan trọng |
| **Q41. Ưu tiên trước?** | 1-Installer, 2-Tài liệu, 3-Test 24h, 4-Log, 5-Fix bugs |
| **Q43. Platform trước?** | C - Docker trước, .exe sau |
| **Q44. Docker update dễ?** | Rất dễ - 1 command, 2 phút |
| **Q45. AI support?** | A - Chatbot với LLM + docs (bạn tự xây dựng) |
| **Q47. Test 24h sao?** | B - Cung cấp video → Tôi setup pipeline |
| **Q48. Test case quan trọng?** | 3 video x 30 phút (3 camera) loop 24h |
| **Q50. Fix security bugs?** | A - **Tất cả 4 bugs** |
| **Q52. Giờ/ngày?** | **6 giờ/ngày** |
| **Q55. Roadmap OK?** | **OK, bắt đầu ngay!** |

---

### 🎯 KẾT LUẬN TỪ KHẢO SÁT

#### **Điều THỰC SỰ quan trọng:**
1. ✅ **Ổn định** (không crash) - Lo lắng nhất
2. ✅ **Installer** (Docker) - Ưu tiên #1
3. ✅ **Tài liệu** (PDF + Video) - Ưu tiên #2
4. ✅ **Test 24h** (3 video loop) - Ưu tiên #3
5. ✅ **Security bugs** - Fix hết 4 bugs

#### **Điều KHÔNG quan trọng:**
- ❌ Cloud deployment (sản phẩm local)
- ❌ Framework lý thuyết (chỉ cần thực tế chạy tốt)
- ❌ Giảm features (khách cần đầy đủ)

#### **Timeline:**
- 🎯 **2 tuần** (36 giờ = 6h/ngày x 6 ngày)
- 🎯 Sau đó: Giao cho đồng nghiệp/bạn bè test
- 🎯 Mục tiêu: Đưa ra thị trường

#### **4 Security Bugs phải fix:**
1. **SECRET_KEY = 'your_secret_key_here'** → Hack license
2. **Missing CSRF protection** → Giả mạo request
3. **No rate limiting** → DoS attack
4. **Sensitive data not encrypted** → Leak data

---

## 🎯 PHÂN CÔNG

### Claude Code (Tôi) - 95% execution:
- ✅ Viết code (Backend, Frontend)
- ✅ Fix bugs
- ✅ Setup Docker
- ✅ Write documentation
- ✅ Create test scripts
- ✅ Security fixes

### User (Bạn) - 5% support:
- ✅ Review code
- ✅ Approve/reject
- ✅ Test manual (optional)
- ✅ Provide video data for testing

---

## 🤖 AGENTS TÔI SẼ DÙNG

### Available Agents:
1. **tech-lead-orchestrator** - Phân tích chiến lược, thiết kế architecture
2. **backend-developer** - Viết backend code (Flask, Python)
3. **frontend-developer** - Viết frontend code (React, Next.js)
4. **react-nextjs-expert** - Next.js specific (SSR, build optimization)
5. **documentation-specialist** - Viết docs (README, User Manual, PDF)
6. **performance-optimizer** - Optimize performance, Docker images
7. **code-reviewer** - Review code tự động
8. **code-archaeologist** - Explore codebase phức tạp

### MCP Tools Available:
1. **chrome-devtools** - Test frontend trong browser
2. **ide tools (getDiagnostics)** - Check errors/warnings
3. **executeCode** - Execute Python code for testing

---

## 📋 ROADMAP 2 TUẦN - DỰA TRÊN KHẢO SÁT

### 🎯 Output sau 2 tuần:
✅ Docker installer (1 command là chạy)
✅ Tài liệu đầy đủ (PDF + Video + Troubleshooting)
✅ Test 24h pass (3 video loop không crash)
✅ 4 security bugs đã fix
✅ Sẵn sàng giao cho tester

---

## 🗓️ TUẦN 1 (18 giờ = 6h/ngày x 3 ngày)

### **Day 1-2: Docker Setup (12 giờ)**

**Task 1.1: Backend Dockerfile (5 giờ)**

**BẠN nói:** "Claude, tạo Dockerfile cho backend"

**TÔI làm:**

```dockerfile
# Step 1: Analyze dependencies (1h)
Tôi: Launch tech-lead-orchestrator
Agent: Analyze backend/requirements.txt
Agent: List system packages (ffmpeg, libgl1-mesa-glx, etc.)
Output: Dependencies list + optimization tips

# Step 2: Write multi-stage Dockerfile (3h)
FROM python:3.10-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.10-slim
RUN apt-get update && apt-get install -y \
    ffmpeg libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
COPY . .
EXPOSE 8080
HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "app.py"]

# Step 3: Build and test (1h)
docker build -t epack-backend:test .
docker run -p 8080:8080 epack-backend:test
curl http://localhost:8080/health
```

**Output:** ✅ Backend Docker image (450MB)

---

**Task 1.2: Frontend Dockerfile (4 giờ)**

**BẠN nói:** "Claude, tạo Dockerfile cho frontend"

**TÔI làm:**

```dockerfile
# Next.js production Dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

**Output:** ✅ Frontend Docker image (~200MB)

---

**Task 1.3: docker-compose.yml (3 giờ)**

**BẠN nói:** "Claude, tạo docker-compose orchestration"

**TÔI làm:**

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: epack-backend
    ports:
      - "8080:8080"
    volumes:
      - ./backend/database:/app/database
      - ./backend/keys:/app/keys
      - ./var:/app/var
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: epack-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8080
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

networks:
  default:
    name: epack-network
```

**BẠN làm:**
- Run: `docker-compose up`
- Test: Open http://localhost:3000
- Approve (15 phút)

**Output:** ✅ Full stack running in Docker

---

### **Day 3: Fix Security Bugs (6 giờ)**

**Task 2.1: Fix SECRET_KEY (5 phút)**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Update .env with generated key
```

**Task 2.2: CSRF Protection (3 giờ)**

```python
# Install Flask-WTF
# Add CSRFProtect to app.py
# Protect 25 POST endpoints
# Add CSRF token to frontend API calls
```

**Task 2.3: Rate Limiting (2 giờ)**

```python
# Install Flask-Limiter
# Add rate limits to 18 sensitive endpoints:
# - /api/auth/*: 5/minute
# - /api/payment/*: 10/minute
# - /api/license/*: 10/minute
```

**Task 2.4: Encrypt Sensitive Data (1 giờ)**

```python
# Create encryption module
# Encrypt license keys, payment data, OAuth tokens
```

**Output:** ✅ 4 security bugs fixed

---

## 🗓️ TUẦN 2 (18 giờ = 6h/ngày x 3 ngày)

### **Day 4-5: Test Automation (12 giờ)**

**Task 3.1: Setup Test Pipeline (6 giờ)**

**BẠN nói:** "Claude, setup test tự động cho 3 video loop 24h"

**TÔI làm:**

```python
# test_pipeline.py
import os
import time
import requests
from datetime import datetime

VIDEO_PATHS = [
    "/path/to/camera1_video.mp4",  # 30 phút
    "/path/to/camera2_video.mp4",  # 30 phút
    "/path/to/camera3_video.mp4",  # 30 phút
]

def test_24h_stability():
    """Test 3 video processing every 30 minutes for 24 hours"""
    start_time = datetime.now()
    test_count = 0
    errors = []

    while (datetime.now() - start_time).total_seconds() < 86400:  # 24 hours
        for camera_id, video_path in enumerate(VIDEO_PATHS, 1):
            try:
                # Submit video processing
                response = requests.post(
                    "http://localhost:8080/api/process_video",
                    json={"video_path": video_path, "camera_id": camera_id}
                )

                if response.status_code != 200:
                    errors.append(f"[{datetime.now()}] Camera {camera_id} failed: {response.text}")

                test_count += 1
                print(f"[{datetime.now()}] Processed {test_count} videos, {len(errors)} errors")

            except Exception as e:
                errors.append(f"[{datetime.now()}] Exception: {str(e)}")

        # Wait 30 minutes
        time.sleep(1800)

    # Report
    print(f"\n=== 24H TEST COMPLETE ===")
    print(f"Total videos processed: {test_count}")
    print(f"Total errors: {len(errors)}")
    print(f"Success rate: {((test_count - len(errors)) / test_count * 100):.2f}%")

    if errors:
        print("\n=== ERRORS ===")
        for error in errors:
            print(error)

if __name__ == "__main__":
    test_24h_stability()
```

**BẠN làm:**
- Cung cấp 3 video files
- Run: `python test_pipeline.py`
- Để chạy 24h (không cần theo dõi)

---

**Task 3.2: Monitor & Fix Bugs (6 giờ)**

```python
# Tôi sẽ monitor test results real-time
# Nếu có crash/error:
#   1. Analyze log
#   2. Fix bug
#   3. Restart test
#   4. Report to you
```

**Output:** ✅ Test 24h pass, success rate > 95%

---

### **Day 6: Documentation (6 giờ)**

**Task 4.1: Installation Guide (2 giờ)**

**TÔI làm với documentation-specialist agent:**

```markdown
# V_TRACK INSTALLATION GUIDE

## System Requirements
- Docker 20.10+
- 8GB RAM minimum
- 20GB free disk space

## Quick Start (5 minutes)

### Step 1: Download ePACK
Extract `vtrack-v2.1.0.zip` to desired location

### Step 2: Configure
```bash
cp .env.example .env
# Edit .env: Set SECRET_KEY (see guide below)
```

### Step 3: Start ePACK
```bash
docker-compose up -d
```

### Step 4: Access Application
- Frontend: http://localhost:3000
- Backend: http://localhost:8080

## Troubleshooting
[Common issues and solutions...]
```

---

**Task 4.2: User Manual (3 giờ)**

```markdown
# V_TRACK USER MANUAL

## 1. Getting Started
## 2. Video Processing
## 3. Camera Management
## 4. Viewing Results
## 5. License Management
## 6. Troubleshooting
## 7. FAQ
```

---

**Task 4.3: Generate PDF (1 giờ)**

```bash
# Convert markdown to PDF with pandoc
pandoc installation.md -o Installation_Guide.pdf
pandoc user_manual.md -o User_Manual.pdf
```

**Output:**
✅ Installation_Guide.pdf (10 pages)
✅ User_Manual.pdf (30 pages)
✅ Troubleshooting_Guide.pdf (5 pages)

---

## 🚀 WORKFLOW CHO MỖI TASK

### Standard Workflow:

```
1. BẠN: "Claude, làm task X"

2. TÔI:
   a. Launch tech-lead-orchestrator (planning)
   b. Execute với appropriate agent
   c. Test code/Docker/features
   d. Present results

3. BẠN: Review & approve (5-15 phút)

4. TÔI: Commit (if approved)

5. REPEAT next task
```

---

## ✅ DELIVERABLES SAU 2 TUẦN

### 1. Docker Package
```
vtrack-v2.1.0/
├── docker-compose.yml
├── .env.example
├── backend/
│   └── Dockerfile
├── frontend/
│   └── Dockerfile
└── README.md
```

**Usage:**
```bash
cd vtrack-v2.1.0
cp .env.example .env
# Edit .env
docker-compose up -d
```

---

### 2. Documentation Package
```
docs/
├── Installation_Guide.pdf
├── User_Manual.pdf
├── Troubleshooting_Guide.pdf
└── video_tutorials/
    ├── 01_installation.mp4
    ├── 02_first_video.mp4
    └── 03_viewing_results.mp4
```

---

### 3. Test Report
```
Test Results - 24H Stability Test
==================================
Duration: 24 hours
Videos processed: 144 (3 cameras x 48 cycles)
Success rate: 98.6%
Errors: 2 (minor, fixed)
Memory usage: Stable (< 2GB)
CPU usage: Average 45%

Conclusion: ✅ PASS - Ready for production
```

---

### 4. Security Audit
```
Security Fixes Applied
======================
✅ SECRET_KEY: Secure 256-bit key generated
✅ CSRF Protection: 25 endpoints protected
✅ Rate Limiting: 18 endpoints rate-limited
✅ Data Encryption: All sensitive data encrypted

Status: ✅ SECURE - Ready for customer deployment
```

---

## 🎯 BẮT ĐẦU NGAY

### Immediate Start Tasks:

**BẠN nói:**
```
"Claude, bắt đầu Tuần 1, Day 1:
1. Tạo Backend Dockerfile
2. Tạo Frontend Dockerfile
3. Tạo docker-compose.yml
4. Test Docker full stack"
```

**TÔI sẽ:**
1. Launch tech-lead-orchestrator để analyze
2. Execute với backend-developer + react-nextjs-expert
3. Build Docker images
4. Test full stack
5. Present results cho bạn review

**Timeline:** 12 giờ (Day 1-2)

**Bạn chỉ cần:** Review 15 phút, test `docker-compose up`, approve

---

## 📊 TRACKING PROGRESS

Tôi sẽ maintain progress tracker:

```markdown
# PROGRESS_TRACKER.md

## Tuần 1

### Day 1 (6h)
- ✅ Backend Dockerfile (5h) - DONE
- 🚧 Frontend Dockerfile (1h/4h) - IN PROGRESS

### Day 2 (6h)
- ⏳ Frontend Dockerfile (3h remaining)
- ⏳ docker-compose.yml (3h)

### Day 3 (6h)
- ⏳ Security fixes (6h)

## Stats
- Hours completed: 5/36 (14%)
- Tasks completed: 1/8 (12.5%)
- On track: ✅ YES
```

---

## 🎓 KẾT LUẬN

### So với plan cũ (16-20 tuần):

| Old Plan | New Plan |
|----------|----------|
| 16-20 tuần | **2 tuần** |
| Team of 4 | Claude + User |
| 2,096 hours | **36 hours** |
| Full framework | **Focus on essentials** |
| Theory-driven | **User need-driven** |

### Tại sao 2 tuần đủ?

1. ✅ **Focus:** Chỉ làm điều THỰC SỰ cần (từ khảo sát)
2. ✅ **Docker:** Update dễ, ship nhanh
3. ✅ **AI agents:** Code 10x faster than human
4. ✅ **Test targeted:** 3 video loop 24h (đủ để phát hiện vấn đề)
5. ✅ **Docs template:** Có sẵn structure, chỉ cần fill content

### Bạn chỉ cần:

**Total time from you: ~2 giờ trong 2 tuần**
- Day 1: Review Docker setup (15 phút)
- Day 2: Approve docker-compose (15 phút)
- Day 3: Approve security fixes (30 phút)
- Day 4: Provide 3 video files (15 phút)
- Day 5: Check test results (15 phút)
- Day 6: Review docs (30 phút)

---

## 🚀 READY TO START?

**Bạy nói:**
```
"Claude, bắt đầu ngay!"
```

**Tôi sẽ bắt đầu từ:**
- Task 1.1: Backend Dockerfile
- Estimated: 5 giờ
- Agent: tech-lead-orchestrator + backend-developer

**Let's build this! 🎯**
