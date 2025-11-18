# Learn Config - Record VPACK 5-Step Configuration Flow

Auto-generated skill để học và ghi lại flow Configuration Wizard của VPACK.

## Mục tiêu

Record toàn bộ 5-step Configuration Wizard để sau này có thể:
- Tự động test config flow
- Tạo test suite từ lesson đã ghi
- Verify config flow không bị broken sau mỗi lần update

## Prerequisites

**1. Khởi động VPACK local:**
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate  # hoặc .\venv\Scripts\activate trên Windows
python app.py
# → Backend running on http://localhost:8080

# Terminal 2: Frontend
cd frontend
npm run dev
# → Frontend running on http://localhost:3000
```

**2. Kiểm tra MCP Chrome:**
```bash
# Verify MCP server đang chạy
# (Có thể test bằng cách mở Chrome với MCP enabled)
```

**3. Chuẩn bị test data:**
- Brand name: "Test Company"
- Country: Vietnam
- Timezone: Asia/Ho_Chi_Minh
- Working days: Mon-Fri
- Video source path: (để trống hoặc test path)

## Recording Steps

Khi invoke skill này, tôi sẽ thực hiện:

### Step 0: Setup Recording Session

```
🎬 Bắt đầu recording session: "vpack-config-5-steps"

📋 Tôi sẽ ghi lại:
  1. Mỗi UI interaction (click, input, select)
  2. Tất cả API calls (endpoint, payload, response)
  3. Navigation flow
  4. Timing và dependencies giữa các steps

⚠️  Tôi sẽ PAUSE tại Step 3 (Video Source) khi gặp Google Auth
```

### Step 1: Navigate to Config Wizard

```
🌐 Opening http://localhost:3000

📸 Capturing:
  - Initial page load
  - GET / → Response
  - Redirect to /config (nếu có)
```

### Step 2: Record Config Step 1 - Brand Name

```
📝 Step 1: Brand Name Configuration

Actions:
  1. Tìm input field "#brand-name" hoặc tương tự
  2. User nhập: "Test Company"
  3. Click "Next" button

API Calls (nếu có):
  - POST /api/config/brand {...}
  - Expected: 200 OK

Ghi lại:
  - Input value: "Test Company"
  - Validation rules
  - Response data
  - Next step navigation
```

### Step 3: Record Config Step 2 - Location & Time

```
📍 Step 2: Location & Time

Actions:
  1. Select country: "Vietnam"
  2. Select timezone: "Asia/Ho_Chi_Minh"
  3. Select working days: Monday-Friday checkboxes
  4. Click "Next"

API Calls:
  - POST /api/config/location {...}
  - Expected: 200 OK

Ghi lại:
  - Country selection
  - Timezone dropdown
  - Working days checkboxes state
  - API payload & response
```

### Step 4: Record Config Step 3 - Video Source ⚠️ PAUSE HERE

```
⏸️  PAUSED - Google Auth Required

📹 Step 3: Video Source

Tôi phát hiện 2 options:
  [ ] Local Storage
  [ ] Google Drive (requires authentication)

❓ User sẽ chọn option nào?

[1] Local Storage - Không cần auth, chỉ nhập path
[2] Google Drive - CẦN Google OAuth (sẽ pause để handle)

→ Nếu chọn [2], tôi sẽ hỏi:

  ⏸️  GOOGLE AUTH DETECTED

  User sẽ click "Connect Google Drive" → OAuth popup

  ❓ Làm sao handle trong test?

  [1] Mock - Fake OAuth response với test credentials
  [2] Real - Thực hiện real OAuth (cần user manual auth mỗi lần test)
  [3] Skip - Bỏ qua bước này, assume đã authenticated
  [4] Env - Dùng saved OAuth token từ .env file

  Your choice: _

Recording sẽ lưu:
{
  "step": 3,
  "name": "Video Source Selection",
  "sensitive": true,
  "sensitiveType": "oauth",
  "handling": "user_choice",  // Lưu choice của user
  "options": ["local", "google_drive"],
  "selected": "google_drive",
  "authMethod": "mock|real|skip|env"
}
```

### Step 5: Record Config Step 4 - ROI Configuration

```
🎯 Step 4: ROI Configuration

Actions:
  1. Select camera: "Cam1" (dropdown)
  2. Upload test video hoặc chọn từ available videos
  3. Click "Run ROI Selection"
  4. (System sẽ process video và hiển thị ROI)
  5. Confirm ROI coordinates
  6. Click "Next"

API Calls:
  - POST /run-select-roi
    {
      "video_path": "/path/to/video.mp4",
      "camera_id": "Cam1",
      "step": "packing"
    }
  - Expected: 200 OK, ROI coordinates

  - POST /finalize-roi
    {
      "cameraId": "Cam1",
      "rois": [{"type": "packing", "x": 100, "y": 200, "w": 300, "h": 400}]
    }

⚠️ Nếu không có test video:
  → PAUSE và hỏi: "Mock ROI data or skip step?"
  → Option: Use dummy coordinates for testing

Ghi lại:
  - Camera selection
  - Video path
  - ROI selection process
  - Finalize coordinates
  - API calls & responses
```

### Step 6: Record Config Step 5 - Timing & Storage

```
⏱️  Step 5: Timing & Storage

Actions:
  1. Set packing start time: "08:00"
  2. Set packing end time: "17:00"
  3. Set frame rate: "2" (frames per second)
  4. Set storage path: "/path/to/storage" (hoặc default)
  5. Click "Finish" / "Complete Configuration"

API Calls:
  - POST /api/config/timing
    {
      "packingStartTime": "08:00",
      "packingEndTime": "17:00",
      "frameRate": 2,
      "storagePath": "/path/to/storage"
    }
  - Expected: 200 OK

  - POST /api/config/complete (nếu có)

Ghi lại:
  - Time inputs
  - Frame rate selection
  - Storage path
  - Final submission
  - Success redirect (thường về /dashboard)
```

### Step 7: Finalize Recording

```
✅ Recording Completed!

📊 Summary:
  • Total steps: 5 (Config Wizard steps)
  • UI interactions: ~15
  • API endpoints: 4-5 endpoints
  • Sensitive steps: 1 (Google Auth)
  • Pause points: 1-2 (Auth, optionally ROI)

💾 Saving lesson...
  → .claude/lessons/vpack-config-flow.json

🎯 Tạo test skill?

Skill name: test-config-local
Description: Test 5-step configuration wizard on local VPACK

✨ Generated files:
  • .claude/lessons/vpack-config-flow.json
  • .claude/skills/test-config-local.md
  • .claude/test-templates/test_config.py (optional)
```

## Lesson File Structure

File `.claude/lessons/vpack-config-flow.json` sẽ có dạng:

```json
{
  "lesson": {
    "name": "vpack-config-flow",
    "description": "VPACK 5-step Configuration Wizard",
    "app": "VPACK",
    "baseUrl": "http://localhost:3000",
    "createdAt": "2025-11-18T...",
    "totalSteps": 5
  },
  "steps": [
    {
      "step": 1,
      "name": "Brand Name",
      "url": "/config/step1",
      "inputs": {
        "#brand-name": "Test Company"
      },
      "action": {
        "type": "click",
        "selector": "#next-btn"
      },
      "apiCall": {
        "method": "POST",
        "endpoint": "/api/config/brand",
        "payload": {"brandName": "Test Company"},
        "expectedResponse": {"status": 200}
      }
    },
    {
      "step": 2,
      "name": "Location & Time",
      "url": "/config/step2",
      "inputs": {
        "#country-select": "Vietnam",
        "#timezone-select": "Asia/Ho_Chi_Minh",
        ".working-days input[value='monday']": true,
        ".working-days input[value='friday']": true
      },
      "apiCall": {
        "method": "POST",
        "endpoint": "/api/config/location",
        "payload": {
          "country": "Vietnam",
          "timezone": "Asia/Ho_Chi_Minh",
          "workingDays": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }
      }
    },
    {
      "step": 3,
      "name": "Video Source",
      "url": "/config/step3",
      "sensitive": true,
      "sensitiveType": "oauth",
      "handling": "mock",
      "inputs": {
        "input[name='source']": "google_drive"
      },
      "authFlow": {
        "trigger": "#connect-google-btn",
        "type": "oauth_popup",
        "provider": "google",
        "mockResponse": {
          "accessToken": "{{ENV.GOOGLE_TEST_TOKEN}}",
          "user": {"email": "test@example.com"}
        }
      },
      "apiCall": {
        "method": "POST",
        "endpoint": "/api/sources/connect",
        "headers": {
          "Authorization": "Bearer {{authFlow.mockResponse.accessToken}}"
        }
      }
    },
    {
      "step": 4,
      "name": "ROI Configuration",
      "url": "/config/step4",
      "inputs": {
        "#camera-select": "Cam1",
        "#video-path": "/test/video.mp4"
      },
      "apiCalls": [
        {
          "method": "POST",
          "endpoint": "/run-select-roi",
          "payload": {
            "video_path": "/test/video.mp4",
            "camera_id": "Cam1",
            "step": "packing"
          },
          "expectedResponse": {
            "status": 200,
            "roi": {"x": 100, "y": 200, "w": 300, "h": 400}
          }
        },
        {
          "method": "POST",
          "endpoint": "/finalize-roi",
          "payload": {
            "cameraId": "Cam1",
            "rois": [{"type": "packing", "x": 100, "y": 200, "w": 300, "h": 400}]
          }
        }
      ]
    },
    {
      "step": 5,
      "name": "Timing & Storage",
      "url": "/config/step5",
      "inputs": {
        "#packing-start-time": "08:00",
        "#packing-end-time": "17:00",
        "#frame-rate": "2",
        "#storage-path": "/var/vpack/storage"
      },
      "apiCall": {
        "method": "POST",
        "endpoint": "/api/config/timing",
        "payload": {
          "packingStartTime": "08:00",
          "packingEndTime": "17:00",
          "frameRate": 2,
          "storagePath": "/var/vpack/storage"
        }
      },
      "finalAction": {
        "type": "click",
        "selector": "#finish-btn"
      },
      "expectedRedirect": "/dashboard"
    }
  ],
  "metadata": {
    "sensitiveSteps": [3],
    "apiEndpoints": [
      "POST /api/config/brand",
      "POST /api/config/location",
      "POST /api/sources/connect",
      "POST /run-select-roi",
      "POST /finalize-roi",
      "POST /api/config/timing"
    ]
  }
}
```

## Execution Flow

Khi user invoke skill này:

1. **Tôi sẽ hướng dẫn user:**
   ```
   🎬 Sẵn sàng record VPACK config flow!

   ✅ Prerequisites checked:
     • Backend: http://localhost:8080 ✓
     • Frontend: http://localhost:3000 ✓
     • MCP Chrome: Ready ✓

   🚀 Hãy bắt đầu thực hiện 5-step configuration wizard.
   Tôi sẽ quan sát và ghi lại mọi thứ.

   ⏸️  Tôi sẽ DỪNG LẠI tại Step 3 (Google Auth) để hỏi bạn cách handle.

   👉 Gõ "ready" khi sẵn sàng...
   ```

2. **User thực hiện các bước trên UI:**
   - Tôi sẽ theo dõi qua MCP Chrome
   - Ghi lại mọi interaction
   - PAUSE tại sensitive steps

3. **Tôi hỏi về sensitive actions:**
   ```
   ⏸️  PAUSED at Step 3: Google OAuth

   ❓ Làm sao handle trong test?
   [1] Mock, [2] Real, [3] Skip, [4] Env

   → User chọn: [1]

   ✓ Saved: Will use mock OAuth in tests
   ```

4. **Tiếp tục recording:**
   - Complete remaining steps
   - Save lesson file
   - Generate test skill

## Generated Test Skill

Sau khi recording xong, skill `test-config-local.md` sẽ được tạo:

```markdown
# Test Config Local

Test 5-step VPACK configuration wizard on localhost.

## Usage

@test-config-local

## Test Steps

1. ✓ Step 1: Brand Name → POST /api/config/brand
2. ✓ Step 2: Location & Time → POST /api/config/location
3. ✓ Step 3: Video Source (mocked OAuth) → POST /api/sources/connect
4. ✓ Step 4: ROI Configuration → POST /run-select-roi, /finalize-roi
5. ✓ Step 5: Timing & Storage → POST /api/config/timing

## Expected Result

All 5 steps complete successfully, redirect to /dashboard
```

## Notes

- Recording này chỉ chạy 1 lần để tạo lesson
- Sau khi có lesson, dùng `@test-config-local` để test
- Có thể re-record bằng cách invoke skill này lại
- Lesson file có thể edit manually nếu cần adjust

## Related Commands

- `/learn "vpack config"` - Alternative way to start recording
- `@test-config-local` - Run test từ lesson này
- `/list-lessons` - Xem tất cả lessons đã record
