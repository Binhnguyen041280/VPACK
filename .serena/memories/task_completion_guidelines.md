# V_Track Task Completion Guidelines

## When a Development Task is Completed

### 1. Code Quality Checks

#### Backend (Python)
```bash
# Run existing tests
cd backend
python3 test_fixes.py

# Check for syntax errors
python3 -m py_compile app.py
python3 -m py_compile modules/**/*.py

# Verify database operations
python3 database.py
```

#### Frontend (React)
```bash
cd frontend

# Run existing tests
npm test -- --watchAll=false

# Check for build errors
npm run build

# Verify no unused dependencies
npx depcheck
npx knip
```

### 2. Database Integrity Checks

#### Verify Database Operations
```bash
cd backend

# Test database initialization
python3 database.py

# Add test data and verify
python3 add_test_data.py

# Check database file integrity
sqlite3 database/events.db ".tables"
sqlite3 database/events.db ".schema"
```

#### Thread Safety Verification
- Ensure all database operations use `db_rwlock`
- Verify WAL mode is enabled
- Test concurrent access scenarios

### 3. Integration Testing

#### API Endpoint Testing
```bash
# Start backend
cd backend && python3 app.py

# Test key endpoints (in separate terminal)
curl http://localhost:8080/health
curl http://localhost:8080/api/system-info
curl -X POST http://localhost:8080/api/config -H "Content-Type: application/json" -d "{}"
```

#### Frontend-Backend Integration
```bash
# Start full system
./backend/start.sh

# Verify in browser:
# - http://localhost:3000 (frontend loads)
# - API calls work in network tab
# - No console errors
```

### 4. Video Processing Verification

#### Test Video Processing Pipeline
```bash
cd backend

# Verify OpenCV functionality
python3 -c "import cv2; print(cv2.__version__)"

# Verify MediaPipe functionality  
python3 -c "import mediapipe as mp; print('MediaPipe loaded')"

# Test with sample video if available
python3 -m modules.technician.video_processor
```

### 5. OAuth & Cloud Integration

#### Test Google Drive Integration
```bash
# Verify OAuth configuration
python3 -c "from modules.config.oauth_manager import OAuthManager; print('OAuth config OK')"

# Test cloud connectivity (if credentials available)
curl http://localhost:8080/api/test-cloud
```

### 6. Error Handling Verification

#### Test Error Scenarios
- Invalid file paths
- Database locks
- Network failures
- Missing dependencies
- Port conflicts

#### Check Log Output
```bash
# Monitor logs during testing
tail -f backend/logs/app.log  # if logging to file
# or check console output for structured logging
```

### 7. Performance Checks

#### Memory & Resource Usage
```bash
# Monitor during operation
top -pid $(pgrep -f "python3 app.py")
top -pid $(pgrep -f "npm start")
```

#### Database Performance
```bash
# Check database size and integrity
ls -lah backend/database/
sqlite3 backend/database/events.db "PRAGMA integrity_check;"
```

### 8. Documentation Updates

#### Update Documentation
- Update CLAUDE.md if architecture changes
- Add comments for complex logic
- Update README if new dependencies added
- Document any breaking changes

#### Code Comments
- Ensure complex functions have docstrings
- Add inline comments for business logic
- Update type hints where applicable

### 9. Security Verification

#### Check Security Practices
- No hardcoded credentials
- Environment variables properly used
- Input validation in place
- SQL queries parameterized
- File paths validated

### 10. Git & Version Control

#### Commit Changes
```bash
# Check what changed
git status
git diff

# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: description of what was implemented

- Specific change 1
- Specific change 2
- Any breaking changes noted"

# Push changes
git push origin main
```

## Checklist Before Task Completion

- [ ] **Functionality**: Feature works as intended
- [ ] **Tests**: Existing tests pass, new tests added if needed
- [ ] **Error Handling**: Graceful error handling implemented
- [ ] **Logging**: Appropriate logging added
- [ ] **Performance**: No significant performance regression
- [ ] **Security**: Security best practices followed
- [ ] **Documentation**: Code documented and README updated
- [ ] **Integration**: Works with existing system
- [ ] **Database**: Database operations are thread-safe
- [ ] **UI/UX**: Frontend changes are responsive and accessible
- [ ] **Clean Code**: Follows established patterns and conventions
- [ ] **Git**: Changes committed with clear messages

## Common Issues to Check

### Backend Issues
- Database connection handling
- Thread safety for concurrent operations
- OAuth token refresh logic
- File path validation
- Error response formatting

### Frontend Issues
- API call error handling
- State management consistency
- Responsive design on different screens
- Loading states and user feedback
- Memory leaks in React components

### Integration Issues
- CORS configuration for development
- API endpoint URL consistency
- Data format compatibility
- WebSocket connection stability
- Session persistence across restarts

## Deployment Readiness

### Development Environment
- All components start successfully with `./backend/start.sh`
- No console errors in browser
- Database initializes correctly
- OAuth flow works (if applicable)

### Production Considerations
- Environment variables configured
- Database backups available
- Error monitoring in place
- Performance acceptable under load
- Security measures active