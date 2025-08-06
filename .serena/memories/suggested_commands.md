# V_Track Suggested Commands

## System Startup Commands

### Full System Startup (Recommended)
```bash
# Start both backend and frontend concurrently
./backend/start.sh
```

### Individual Component Startup
```bash
# Backend only
cd backend
python3 app.py

# Frontend only (separate terminal)
cd frontend
npm start
```

## Development Setup Commands

### Initial Project Setup
```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install

# Initialize database
cd backend
python3 database.py
```

### Database Management
```bash
# Initialize/reset database
python3 backend/database.py

# Add test data for development
python3 backend/add_test_data.py

# Run backend tests
python3 backend/test_fixes.py
```

## Frontend Development Commands

### React Development
```bash
cd frontend

# Start development server (with hot reload)
npm start

# Build for production
npm run build

# Run tests
npm test

# Eject configuration (avoid unless necessary)
npm run eject
```

### Code Quality & Dependencies
```bash
cd frontend

# Check for unused dependencies
npx depcheck

# Find unused exports and dependencies
npx knip
```

## Backend Development Commands

### Flask Development
```bash
cd backend

# Start Flask development server
python3 app.py

# Run with debug mode (set in environment)
FLASK_DEBUG=1 python3 app.py
```

### Testing & Debugging
```bash
cd backend

# Run specific test files
python3 test_fixes.py
python3 add_test_data.py

# Check specific modules (examples)
python3 -m modules.scheduler.main
python3 -m modules.technician.video_processor
```

## System Utilities (macOS/Darwin)

### Process Management
```bash
# Find processes using port 8080
lsof -i :8080

# Find processes using port 3000
lsof -i :3000

# Kill process by PID
kill -9 <PID>

# Kill processes by name
pkill -f "python3 app.py"
pkill -f "npm start"
```

### File & Directory Operations
```bash
# List files with details
ls -la

# Find files by pattern
find . -name "*.py" -type f
find . -name "*.js" -type f

# Search in files (case-insensitive)
grep -ri "search_term" .

# Monitor log files
tail -f backend/logs/app.log
```

### Network & Connectivity
```bash
# Test API endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/system-info

# Test frontend availability
curl http://localhost:3000

# Check network interfaces (for camera discovery)
ifconfig
```

## Git Commands

### Version Control
```bash
# Check status
git status

# Stage and commit changes
git add .
git commit -m "descriptive commit message"

# Push changes
git push origin main

# Pull latest changes
git pull origin main

# View commit history
git log --oneline
```

## Performance & Monitoring

### System Monitoring
```bash
# Monitor system resources
top
htop  # if installed

# Monitor disk usage
df -h

# Monitor memory usage
vm_stat

# Monitor network connections
netstat -an | grep LISTEN
```

### Application Monitoring
```bash
# Monitor Flask logs
tail -f backend/app.log

# Monitor React build
cd frontend && npm run build

# Check bundle sizes
cd frontend && npx webpack-bundle-analyzer build/static/js/*.js
```

## Quick Troubleshooting Commands

### Common Issues
```bash
# Clear React cache
cd frontend
rm -rf node_modules package-lock.json
npm install

# Reset Python environment
cd backend
pip install --force-reinstall -r requirements.txt

# Database reset
cd backend
rm -f database/events.db*
python3 database.py

# Port conflicts
lsof -ti:8080 | xargs kill
lsof -ti:3000 | xargs kill
```

### Environment Checks
```bash
# Check Python version
python3 --version

# Check Node.js version
node --version
npm --version

# Check available Python packages
pip list | grep -E "(flask|opencv|mediapipe)"

# Check React dependencies
cd frontend && npm list
```