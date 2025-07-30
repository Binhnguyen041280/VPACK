# V_Track - Development Commands

## Quick Start (All-in-one)
```bash
cd backend
./start.sh
```
Script này sẽ:
1. Update database (`python3 update_database.py`)
2. Start backend (`python3 app.py`) 
3. Start frontend (`npm start`)

## Manual Development

### Frontend Commands
```bash
cd frontend
npm start           # Start dev server (localhost:3000)
npm run build       # Production build
npm test            # Run tests
npm run eject       # Eject from CRA (one-way)
```

### Backend Commands  
```bash
cd backend
python3 app.py      # Start Flask server (port 8080)
python3 update_database.py  # Update/create SQLite database
```

### System Commands (macOS/Darwin)
- `git` - Version control
- `ls`, `cd`, `find`, `grep` - File operations
- `lsof -ti:8080` - Check port usage
- `ps aux | grep python` - Check running processes

## Development URLs
- Frontend: http://localhost:3000
- Backend: http://127.0.0.1:8080
- Backend API: http://0.0.0.0:8080

## Database Management
- Database file: `backend/database/events.db`
- Backup folder: `migration_backups/`
- Always run `update_database.py` before starting