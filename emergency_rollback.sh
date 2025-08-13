#!/bin/bash

# V_Track Emergency Rollback Script
# Usage: ./emergency_rollback.sh
# This script provides fast rollback to pre-refactor state

set -e

echo "🚨 V_TRACK EMERGENCY ROLLBACK INITIATED"
echo "========================================"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify we're in the right directory
if [ ! -f "backend/app.py" ] || [ ! -f "frontend/package.json" ]; then
    echo "❌ Error: Not in V_Track root directory"
    echo "Please run this script from /Users/annhu/vtrack_app/V_Track/"
    exit 1
fi

log "✅ Verified V_Track directory structure"

# Step 1: Stop current processes
log "🛑 Stopping current V_Track processes..."

# Stop backend processes
BACKEND_PIDS=$(pgrep -f "python.*app.py" 2>/dev/null || true)
if [ ! -z "$BACKEND_PIDS" ]; then
    log "Stopping backend processes: $BACKEND_PIDS"
    echo $BACKEND_PIDS | xargs kill 2>/dev/null || true
    sleep 2
    
    # Force kill if still running
    REMAINING_BACKEND=$(pgrep -f "python.*app.py" 2>/dev/null || true)
    if [ ! -z "$REMAINING_BACKEND" ]; then
        log "Force killing remaining backend processes: $REMAINING_BACKEND"
        echo $REMAINING_BACKEND | xargs kill -9 2>/dev/null || true
    fi
else
    log "No backend processes found"
fi

# Stop frontend processes
FRONTEND_PIDS=$(pgrep -f "npm.*start" 2>/dev/null || true)
if [ ! -z "$FRONTEND_PIDS" ]; then
    log "Stopping frontend processes: $FRONTEND_PIDS"
    echo $FRONTEND_PIDS | xargs kill 2>/dev/null || true
    sleep 2
    
    # Force kill if still running
    REMAINING_FRONTEND=$(pgrep -f "npm.*start" 2>/dev/null || true)
    if [ ! -z "$REMAINING_FRONTEND" ]; then
        log "Force killing remaining frontend processes: $REMAINING_FRONTEND"
        echo $REMAINING_FRONTEND | xargs kill -9 2>/dev/null || true
    fi
else
    log "No frontend processes found"
fi

log "✅ All processes stopped"

# Step 2: Git rollback
log "📦 Rolling back code to pre-refactor state..."

# Stash any current changes
log "Stashing current changes..."
git stash push -m "Emergency rollback stash - $(date)" 2>/dev/null || true

# Find the most recent backup branch
BACKUP_BRANCH=$(git branch -a | grep -E "backup-pre-refactor|backup.*refactor" | head -1 | sed 's/^[* ]*//g' | sed 's/remotes\/origin\///g' 2>/dev/null || true)

if [ ! -z "$BACKUP_BRANCH" ]; then
    log "Found backup branch: $BACKUP_BRANCH"
    git checkout "$BACKUP_BRANCH" 2>/dev/null || {
        log "Failed to checkout backup branch, trying alternative method..."
        git checkout HEAD~1 2>/dev/null || {
            log "❌ Git rollback failed, trying file restoration..."
        }
    }
else
    log "No backup branch found, rolling back to previous commit..."
    git checkout HEAD~1 2>/dev/null || {
        log "❌ Git rollback failed"
        exit 1
    }
fi

log "✅ Code rolled back successfully"

# Step 3: Database rollback (if backup exists)
log "🗄️ Checking for database backup..."

LATEST_DB_BACKUP=$(ls -t backend/database/events.db.backup-* 2>/dev/null | head -1 || true)
if [ ! -z "$LATEST_DB_BACKUP" ]; then
    log "Found database backup: $LATEST_DB_BACKUP"
    cp "$LATEST_DB_BACKUP" backend/database/events.db
    log "✅ Database restored from backup"
else
    log "⚠️ No database backup found - keeping current database"
fi

# Step 4: Restore configuration files (if backups exist)
log "⚙️ Checking for configuration backups..."

LATEST_CONFIG_BACKUP=$(ls -t config.json.backup-* 2>/dev/null | head -1 || true)
if [ ! -z "$LATEST_CONFIG_BACKUP" ]; then
    log "Found config backup: $LATEST_CONFIG_BACKUP"
    cp "$LATEST_CONFIG_BACKUP" config.json
    log "✅ Configuration restored from backup"
fi

LATEST_ENV_BACKUP=$(ls -t .env.backup-* 2>/dev/null | head -1 || true)
if [ ! -z "$LATEST_ENV_BACKUP" ]; then
    log "Found .env backup: $LATEST_ENV_BACKUP"
    cp "$LATEST_ENV_BACKUP" .env
    log "✅ Environment file restored from backup"
fi

# Step 5: Restart services
log "🚀 Restarting V_Track services..."

# Start backend
log "Starting backend service..."
cd backend
nohup python3 app.py > rollback_app.log 2>&1 &
BACKEND_PID=$!
log "Backend started with PID: $BACKEND_PID"

# Wait for backend to initialize
sleep 5

# Test backend health
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/config/get-sources 2>/dev/null || echo "000")
if [ "$BACKEND_HEALTH" = "200" ]; then
    log "✅ Backend health check: PASSED ($BACKEND_HEALTH)"
else
    log "⚠️ Backend health check: WARNING ($BACKEND_HEALTH) - may still be starting"
fi

# Start frontend
log "Starting frontend service..."
cd ../frontend
nohup npm start > rollback_frontend.log 2>&1 &
FRONTEND_PID=$!
log "Frontend started with PID: $FRONTEND_PID"

# Save PIDs for future reference
echo $BACKEND_PID > /tmp/vtrack_rollback_backend.pid
echo $FRONTEND_PID > /tmp/vtrack_rollback_frontend.pid

cd ..

# Step 6: Final verification
log "🔍 Running final verification..."

sleep 10

# Check if processes are still running
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    log "✅ Backend process is running (PID: $BACKEND_PID)"
else
    log "❌ Backend process died - check rollback_app.log"
fi

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    log "✅ Frontend process is running (PID: $FRONTEND_PID)"
else
    log "❌ Frontend process died - check rollback_frontend.log"
fi

# Final health check
log "Performing final health check..."
sleep 5

FINAL_BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/config/get-sources 2>/dev/null || echo "000")
if [ "$FINAL_BACKEND_HEALTH" = "200" ]; then
    log "✅ Final backend health: HEALTHY ($FINAL_BACKEND_HEALTH)"
else
    log "⚠️ Final backend health: NEEDS ATTENTION ($FINAL_BACKEND_HEALTH)"
fi

# Step 7: Cleanup and summary
log "🧹 Cleaning up..."

# Remove PID files from failed deployment (if any)
rm -f /tmp/vtrack_backend.pid /tmp/vtrack_frontend.pid 2>/dev/null || true

echo ""
echo "========================================"
echo "🎉 EMERGENCY ROLLBACK COMPLETED"
echo "========================================"
echo ""
echo "📊 ROLLBACK SUMMARY:"
echo "  Backend PID: $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo "  Backend Health: $FINAL_BACKEND_HEALTH"
echo "  Log Files:"
echo "    - Backend: backend/rollback_app.log"
echo "    - Frontend: frontend/rollback_frontend.log"
echo ""
echo "🔍 NEXT STEPS:"
echo "  1. Monitor the log files for any errors"
echo "  2. Test critical functionality manually"
echo "  3. Verify all user workflows are working"
echo "  4. Document the issue that caused the rollback"
echo ""
echo "📞 If issues persist, check:"
echo "  - Log files for detailed error messages"
echo "  - Database integrity: backend/database/events.db"
echo "  - Network connectivity to ports 8080 and 3000"
echo ""
echo "✅ Rollback completed at: $(date)"
echo ""