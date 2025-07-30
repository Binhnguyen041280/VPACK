# V_Track - Project Structure

## Root Structure
```
V_Track/
├── frontend/          # React frontend
├── backend/           # Flask backend  
├── docs/              # Documentation & progress
├── database/          # SQLite databases
├── cloud_sync/        # Cloud synchronization
├── nvr_downloads/     # NVR downloads storage
├── output_clips/      # Processed video clips
├── migration_backups/ # Database backups
└── localhost:5050/    # Local server artifacts
```

## Frontend Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # Reusable UI components
│   │   ├── config/       # Configuration forms
│   │   ├── query/        # Query interface
│   │   ├── result/       # Result display & video cutter
│   │   └── program/      # Program management
│   ├── hooks/            # Custom React hooks
│   └── [main files]      # App.js, api.js, etc.
└── public/               # Static assets
```

## Backend Structure  
```
backend/
├── modules/
│   ├── technician/       # Core CV processing
│   │   └── cutter/       # Video cutting utilities
│   ├── sources/          # Input sources (NVR, Cloud, Local)
│   ├── config/           # Configuration management
│   ├── scheduler/        # Background tasks
│   ├── account/          # User management
│   ├── query/            # Query processing
│   └── db_utils/         # Database utilities
├── blueprints/           # Flask route blueprints
├── models/               # AI models (WeChat QR)
└── downloads/            # Download management
```