# 🚀 MASTER PLAN - Multi-Cloud Storage Integration for VPACK

**Project**: Mở rộng VPACK để hỗ trợ 10 cloud storage providers
**Owner**: Development Team
**Timeline**: 4-6 tuần (phân theo 2 lộ trình)
**Status**: Planning Phase
**Last Updated**: 2025-11-19

---

## 📋 MỤC TIÊU DỰ ÁN

Hiện tại VPACK chỉ hỗ trợ 2 nguồn video:
- ✅ Local Storage (file system)
- ✅ Google Drive (OAuth2)

**Mục tiêu**: Mở rộng sang **10 cloud storage providers** để phục vụ đa dạng use cases của user tại Việt Nam và quốc tế.

### 🎯 Use Cases Chính

1. **Doanh nghiệp**: Camera IP/NVR/DVR với cloud storage (Hikvision, Dahua, Imou)
2. **Gia đình/SME**: Camera consumer với cloud (Ezviz, TP-Link, Imou)
3. **Tự quản lý**: User tự upload video lên cloud storage (OneDrive, Dropbox, S3)

---

## 🗺️ TỔNG QUAN 2 LỘ TRÌNH

### **Lộ trình 1: General Cloud Storage (3 providers)**
Cloud storage phổ biến cho user tự upload video

| # | Provider | Authentication | Độ khó | Timeline | Use Case |
|---|----------|----------------|--------|----------|----------|
| 1 | **Microsoft OneDrive** | OAuth2 (Microsoft Identity) | ⭐⭐ Medium | 3-4 ngày | Office 365 users, Doanh nghiệp |
| 2 | **Dropbox** | OAuth2 | ⭐ Easy | 2-3 ngày | Phổ biến nhất, cá nhân/SME |
| 3 | **Amazon S3** | IAM Access Key | ⭐⭐⭐ Hard | 4-5 ngày | Enterprise, video streaming |

**Tổng timeline**: ~10-12 ngày làm việc

---

### **Lộ trình 2: Camera Cloud Storage (5 providers)**
Cloud storage tích hợp sẵn với camera IP

| # | Provider | Parent Company | Authentication | Độ khó | Timeline | Use Case |
|---|----------|----------------|----------------|--------|----------|----------|
| 4 | **Hikvision (Hik-Connect)** | Hikvision | ISAPI (Digest Auth) | ⭐⭐⭐⭐ Very Hard | 5-7 ngày | Camera doanh nghiệp #1 VN |
| 5 | **Imou Life** | Dahua Technology | OAuth2 + OpenSDK | ⭐⭐ Medium | 3-4 ngày | Camera gia đình/SME, API tốt nhất |
| 6 | **Ezviz Cloud** | Hikvision (consumer) | OAuth2 + SDK | ⭐⭐⭐ Hard | 4-5 ngày | Camera gia đình phổ biến |
| 7 | **Dahua Cloud** | Dahua Technology | DMSS Protocol | ⭐⭐⭐⭐ Very Hard | 5-6 ngày | Camera doanh nghiệp #2 VN |
| 8 | **TP-Link Tapo/Kasa** | TP-Link | Cloud API (unofficial) | ⭐⭐⭐ Hard | 4-5 ngày | Camera giá rẻ, phổ biến |

**Tổng timeline**: ~21-27 ngày làm việc

---

## 📊 TỔNG THỜI GIAN DỰ KIẾN

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Planning & Documentation** | 1-2 ngày | Detailed plans cho 10 providers |
| **Lộ trình 1 Implementation** | 10-12 ngày | OneDrive, Dropbox, S3 hoàn chỉnh |
| **Lộ trình 2 Implementation** | 21-27 ngày | 5 camera cloud providers hoàn chỉnh |
| **Testing & Integration** | 3-5 ngày | E2E testing, bug fixes |
| **Documentation** | 2-3 ngày | User guides, API docs |
| **TỔNG CỘNG** | **37-49 ngày** | **~6-7 tuần** |

---

## 🏗️ KIẾN TRÚC CHUNG

### Workflow Hiện Tại (Google Drive)

```
User → OAuth2 Flow → Token Storage (encrypted) → Google Drive API
                                                 ↓
                                        List Folders (lazy load)
                                                 ↓
                                        Download Videos (background sync)
                                                 ↓
                                        Database Tracking (dedup by drive_file_id)
```

### Architecture Pattern để Mở Rộng

```python
# backend/modules/sources/cloud_manager.py
SUPPORTED_PROVIDERS = {
    'google_drive': {...},
    'onedrive': {...},        # NEW
    'dropbox': {...},         # NEW
    's3': {...},              # NEW
    'hikvision': {...},       # NEW
    'imou': {...},            # NEW
    'ezviz': {...},           # NEW
    'dahua': {...},           # NEW
    'tapo': {...},            # NEW
}
```

### Các Components Cần Implement

Cho mỗi provider:

1. **Authentication Module** (`{provider}_auth.py`)
   - OAuth2 flow hoặc API Key authentication
   - Token/credential storage (encrypted)
   - Token refresh mechanism

2. **Client Module** (`{provider}_client.py`)
   - Folder/bucket listing
   - File listing (video files)
   - File download
   - Connection testing

3. **API Endpoints** (`{provider}_endpoints.py` hoặc thêm vào `cloud_endpoints.py`)
   - `/api/cloud/{provider}-auth` - Initiate auth
   - `/api/cloud/{provider}/oauth/callback` - OAuth callback
   - `/api/cloud/{provider}/list_folders` - List folders
   - `/api/cloud/{provider}/download` - Download files

4. **Frontend Component** (`{Provider}FolderTree.tsx`)
   - Folder tree UI (lazy loading)
   - Authentication status
   - Folder selection

5. **Database Schema Updates**
   - Extend `video_sources` table config
   - Provider-specific metadata

6. **Tests**
   - Unit tests cho client
   - Integration tests cho API
   - E2E tests cho workflow

---

## 📁 CẤU TRÚC DOCUMENTATION

```
/home/user/VPACK/docs/cloud-storage-integration/
│
├── 00-MASTER-PLAN.md                    ← File này
│
├── route-1-general-cloud/
│   ├── 01-onedrive-plan.md              ← Detailed plan OneDrive (8 mục)
│   ├── 02-dropbox-plan.md               ← Detailed plan Dropbox (8 mục)
│   └── 03-amazon-s3-plan.md             ← Detailed plan S3 (8 mục)
│
├── route-2-camera-cloud/
│   ├── 04-hikvision-plan.md             ← Detailed plan Hikvision (8 mục)
│   ├── 05-imou-life-plan.md             ← Detailed plan Imou (8 mục)
│   ├── 06-ezviz-cloud-plan.md           ← Detailed plan Ezviz (8 mục)
│   ├── 07-dahua-cloud-plan.md           ← Detailed plan Dahua (8 mục)
│   └── 08-tplink-tapo-plan.md           ← Detailed plan TP-Link (8 mục)
│
├── architecture/
│   ├── authentication-patterns.md        ← OAuth2 vs API Key patterns
│   ├── database-schema.md                ← Schema changes needed
│   └── reusable-components.md            ← Shared utilities
│
└── implementation-guides/
    ├── testing-strategy.md               ← Testing approach
    ├── security-checklist.md             ← Security requirements
    └── deployment-guide.md               ← Deployment steps
```

---

## 🎯 CHIẾN LƯỢC IMPLEMENTATION

### Phase 1: Foundation (Ngày 1-2)
- ✅ Tạo detailed plans cho tất cả 10 providers
- ✅ Setup documentation structure
- ✅ Review và update `cloud_manager.py` architecture
- ✅ Prepare database migration scripts

### Phase 2: Lộ trình 1 - Quick Wins (Ngày 3-14)
**Thứ tự ưu tiên:**
1. **Dropbox** (dễ nhất, API đơn giản)
2. **OneDrive** (phổ biến, OAuth2 mature)
3. **Amazon S3** (khó hơn, nhiều config)

**Lý do**: Build momentum với các provider dễ trước

### Phase 3: Lộ trình 2 - Camera Cloud (Ngày 15-41)
**Thứ tự ưu tiên:**
1. **Imou Life** (API tốt nhất, document rõ ràng)
2. **Ezviz** (có SDK, Hikvision ecosystem)
3. **Hikvision** (phổ biến nhất nhưng khó nhất)
4. **Dahua** (tương tự Hikvision)
5. **TP-Link Tapo** (unofficial API, community-driven)

**Lý do**: Học từ Imou (easy) trước khi tackle Hikvision/Dahua (hard)

### Phase 4: Integration & Testing (Ngày 42-46)
- E2E testing tất cả providers
- Bug fixes
- Performance optimization

### Phase 5: Documentation & Deployment (Ngày 47-49)
- User documentation
- API documentation
- Deployment guide

---

## ⚠️ RISKS & MITIGATION

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Camera cloud APIs không public** | High | Medium | Dùng tài khoản cá nhân, không cần enterprise |
| **OAuth2 credentials expiration** | Medium | High | Implement auto-refresh cho tất cả providers |
| **Rate limiting** | Medium | High | Implement caching + backoff strategy |
| **Hikvision ISAPI phức tạp** | High | High | Allocate thêm thời gian, có fallback plan |
| **TP-Link unofficial API thay đổi** | Medium | Medium | Document version, có fallback |
| **S3 costs cho testing** | Low | Medium | Dùng LocalStack hoặc MinIO local |

---

## 🔐 BẢO MẬT

Tất cả providers phải tuân thủ:

1. **Credential Storage**: AES-256 encryption (như Google Drive hiện tại)
2. **Session Tokens**: JWT với expiration
3. **Rate Limiting**: Prevent abuse
4. **Audit Logging**: Track authentication events
5. **Permission Model**: User chỉ thấy cloud sources của mình

---

## 📈 SUCCESS METRICS

| Metric | Target |
|--------|--------|
| **Providers Implemented** | 10/10 |
| **Test Coverage** | >80% |
| **Authentication Success Rate** | >95% |
| **Video Download Success Rate** | >90% |
| **Average Implementation Time per Provider** | <5 ngày |
| **Documentation Completeness** | 100% |

---

## 👥 YÊU CẦU TỪ USER

### Tài Khoản Cần Chuẩn Bị

User đã xác nhận có:
- ✅ **Ezviz account** (cá nhân)
- ✅ **Hikvision account** (giả định)
- ✅ **Imou account** (giả định)

Cần chuẩn bị thêm:
- [ ] **Microsoft account** (cho OneDrive) - Free
- [ ] **Dropbox account** - Free tier
- [ ] **AWS account** (cho S3) - Free tier 12 tháng
- [ ] **Dahua account** (nếu có camera)
- [ ] **TP-Link account** (nếu có camera Tapo/Kasa)

### Developer Registrations Cần Làm

1. **Microsoft Azure**: Đăng ký app tại https://portal.azure.com
2. **Dropbox Developer**: https://www.dropbox.com/developers/apps
3. **AWS IAM**: Tạo IAM user với S3 permissions
4. **Hikvision Partner**: https://tpp.hikvision.com (nếu cần SDK)
5. **Imou Open Platform**: https://open.imoulife.com
6. **Ezviz Developer**: https://isgpopen.ezvizlife.com

**Lưu ý**: Tất cả đều có thể dùng tài khoản cá nhân, KHÔNG cần enterprise!

---

## 📞 HỖ TRỢ & ESCALATION

Nếu gặp blocker:

| Issue | Contact | Timeline |
|-------|---------|----------|
| Microsoft API issues | Azure Support | 24-48h |
| Dropbox API issues | Dropbox Developer Forum | 12-24h |
| AWS S3 issues | AWS Support (có trong free tier) | 12-24h |
| Hikvision SDK | tpp.hikvision.com support | 2-3 days |
| Imou API | open-team@ezvizlife.com | 1-2 days |
| Ezviz API | open-team@ezvizlife.com | 1-2 days |

---

## 🎯 DELIVERABLES

### Mỗi Provider Sẽ Có

1. ✅ Authentication working
2. ✅ Folder/file listing working
3. ✅ Video download working
4. ✅ Auto-sync integration
5. ✅ Frontend UI component
6. ✅ Unit tests (>80% coverage)
7. ✅ Integration tests
8. ✅ Documentation (API + User guide)

### Final Deliverables

1. **Code**: All 10 providers integrated vào VPACK
2. **Tests**: Full test suite
3. **Documentation**:
   - 10 detailed plans (file này + 10 plan files)
   - API documentation
   - User guides
4. **Database Migration**: Scripts để upgrade existing DB
5. **Deployment Guide**: Step-by-step deployment

---

## 📝 NEXT STEPS

1. ✅ **Complete Master Plan** ← Đang làm
2. ⏳ **Create 10 Detailed Plans** ← Tiếp theo
3. ⏳ **Review Plans với User**
4. ⏳ **Start Implementation - Lộ trình 1**
5. ⏳ **Start Implementation - Lộ trình 2**
6. ⏳ **Testing & Integration**
7. ⏳ **Deployment**

---

## 📅 TIMELINE GANTT

```
Week 1:  [Planning & Docs]
Week 2:  [Dropbox] [OneDrive -----]
Week 3:  [OneDrive] [S3 -----------]
Week 4:  [S3 ----] [Imou ----------]
Week 5:  [Imou] [Ezviz -----------]
Week 6:  [Ezviz] [Hikvision ------]
Week 7:  [Hikvision] [Dahua ------]
Week 8:  [Dahua] [TP-Link] [Testing]
```

---

**Prepared by**: Claude (AI Assistant)
**Approved by**: _[Chờ User approve]_
**Version**: 1.0
**Date**: 2025-11-19
