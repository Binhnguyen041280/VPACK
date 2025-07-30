# V_Track - Task Completion Guidelines

## Quy trình khi hoàn thành task

### 1. Code Quality Check
- Code phải hoạt động đúng chức năng
- Follow code conventions của project
- Error handling đầy đủ
- Comments bằng tiếng Việt khi cần

### 2. Testing
- Test manual các chức năng mới
- Kiểm tra integration với existing code
- Verify database operations (SQLite)
- Test WebSocket connections nếu có

### 3. Git Backup (QUAN TRỌNG)
```bash
git add .
git commit -m "feat: mô tả chức năng mới"
git push origin main
```

### 4. Documentation
- Update progress files trong `docs/Noidung tien do/`
- Ghi chú các thay đổi quan trọng
- Update README nếu cần

### 5. Restart Services (nếu cần)
```bash
# Stop existing processes
lsof -ti:8080 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Restart
cd backend && ./start.sh
```

### 6. Verification Checklist
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Backend starts without errors (`python3 app.py`)
- [ ] Database migrations complete (`update_database.py`)
- [ ] All APIs respond correctly
- [ ] UI displays properly
- [ ] No console errors
- [ ] Git backup completed

## Performance Considerations
- Optimize database queries
- Minimize WebSocket message frequency
- Compress large video files
- Handle memory efficiently for computer vision tasks

## Deployment Notes
- Project đã 93% hoàn thành
- Cần hardware testing cho ONVIF cameras
- Production ready sau khi test hardware