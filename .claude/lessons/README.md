# VPACK Test Lessons

Directory này chứa các "bài học" (lessons) đã được ghi lại từ UI interactions.

## Cấu trúc

Mỗi lesson là một file JSON chứa:
- Các bước UI interaction
- API calls tương ứng
- Expected responses
- Sensitive data handling

## Lessons Available

_(Lessons sẽ được tạo khi bạn chạy recording skills)_

### Planned Lessons:

1. **vpack-config-flow.json** - 5-step Configuration Wizard
   - Brand Name setup
   - Location & Timezone
   - Video Source (với OAuth)
   - ROI Configuration
   - Timing & Storage

2. **vpack-login-flow.json** (Future) - User authentication
3. **vpack-create-program.json** (Future) - Create processing program
4. **vpack-roi-setup.json** (Future) - ROI configuration only

## Sử dụng

1. **Recording**: Chạy `@learn-config` để ghi lại config flow
2. **Testing**: Lessons sẽ được convert thành test skills
3. **Updating**: Re-run recording skill để cập nhật lesson

## Lesson Schema

```json
{
  "lesson": {
    "name": "lesson-name",
    "description": "Mô tả",
    "app": "VPACK",
    "baseUrl": "http://localhost:3000",
    "createdAt": "ISO timestamp",
    "totalSteps": 5
  },
  "steps": [
    {
      "step": 1,
      "name": "Step name",
      "url": "/path",
      "inputs": {},
      "apiCall": {},
      "sensitive": false
    }
  ],
  "metadata": {
    "sensitiveSteps": [],
    "apiEndpoints": []
  }
}
```

## Notes

- Lessons được dùng để generate test code
- Có thể edit manual để adjust
- Sensitive data (passwords, tokens) được mark và handle riêng
