#!/bin/bash
echo "Creating or updating events.db..."
python3 /Users/annhu/vtrack_app/V_Track/backend/update_database.py
echo "Starting V_Track backend..."
python3 /Users/annhu/vtrack_app/V_Track/backend/app.py &
echo "Starting V_Track frontend..."
cd /Users/annhu/vtrack_app/V_Track/frontend
npm start &
echo "V_Track is running! Backend on http://0.0.0.0:8080, Frontend on http://localhost:3000"
