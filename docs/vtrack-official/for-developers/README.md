# V_Track Developer Documentation

Technical documentation for developers working on or integrating with V_Track.

## Getting Started

New developer? Start here:

1. **[CLAUDE.md](CLAUDE.md)** ⭐ READ FIRST
   - Project overview
   - Development commands
   - Code architecture patterns
   - Path management guidelines
   - Import best practices

2. **[Architecture Overview](architecture/overview.md)**
   - System architecture diagrams
   - Complete database schema (23 tables)
   - Backend module structure
   - Frontend architecture
   - Data flow diagrams

3. **[API Documentation](api/endpoints.md)**
   - REST API endpoints
   - Request/response formats
   - Authentication flows
   - WebSocket connections

## Architecture

### System Overview
**[Architecture Overview](architecture/overview.md)** - Complete technical reference

**Key Components**:
- **Frontend**: Next.js 15.1.6 + React 19.2.0 (Stable) + Chakra UI 2.8.2 + TypeScript 4.9.5
- **Backend**: Flask 3.0.0 + Python 3.8+
- **Database**: SQLite with WAL mode
- **Computer Vision**: MediaPipe, OpenCV, pyzbar
- **Cloud**: Google OAuth 2.0, PyDrive2, Cloud Functions (Serverless)
- **Payments**: PayOS integration via Cloud Functions
- **Cloud Functions**: Payment processing, license management, pricing service

**Database Schema**:
- 23 tables: events, file_list, video_sources, licenses, etc.
- 50+ indexes for performance
- 4 database views for queries
- See [Architecture § Database Schema](architecture/overview.md#database-schema)

### Module Structure

**Backend Modules** (`/backend/modules/`):
- `config/` - System configuration, OAuth, logging
- `db_utils/` - Thread-safe database operations
- `scheduler/` - Batch processing, job queue
- `technician/` - Video processing (hand, QR, ROI detection)
- `sources/` - Multi-source management (local, cloud)
- `license/` - License validation, machine fingerprinting
- `payments/` - PayOS integration
- `query/` - Event search and tracking
- `utils/` - Timezone, avatars, helpers

**Frontend Structure** (`/frontend/app/`):
- `/` - Dashboard (main page with dual layout)
- `/program` - Processing control page
- `/trace` - Event tracking and search
- `/plan` - License and payment management

## API Reference

### [Complete API Documentation](api/endpoints.md)

**Core Endpoints**:
- `POST /api/program` - Start/stop processing
- `POST /query` - Search events by tracking code
- `POST /api/cloud/drive-auth` - Google Drive authentication
- `POST /run-select-roi` - ROI configuration
- `POST /api/payment/create` - Create payment order (calls Cloud Functions)
- `GET /health` - System health check

**Cloud Functions**:
- [Cloud Functions API Reference](cloud-functions/api-reference.md) - Complete Cloud Functions API documentation

### Authentication
- OAuth 2.0 for Google services
- Session-based authentication with Flask
- JWT tokens for license validation
- See [API § Authentication](api/endpoints.md#authentication)

## Development Guidelines

### Setup Environment

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python app.py

# Frontend
cd frontend
npm install
npm run dev
```

### Code Standards

**Import Patterns** (CRITICAL):
```python
# ✅ CORRECT - Absolute imports
from modules.config.logging_config import get_logger
from modules.db_utils import get_db_connection

# ❌ WRONG - Complex relative imports
from ..licensing.repositories import get_license_repository
```

**Database Operations** (CRITICAL):
```python
# Always use thread-safe pattern
from modules.scheduler.db_sync import db_rwlock
from modules.db_utils import get_db_connection

with db_rwlock.gen_wlock():
    conn = get_db_connection()  # Auto-retry on lock
    # Database operations
    conn.commit()
    conn.close()
```

See [CLAUDE.md § Development Notes](CLAUDE.md#development-notes) for complete guidelines.

### Testing

```bash
# Backend tests
cd backend
python test_fixes.py
python add_test_data.py

# Frontend tests
cd frontend
npm test
```

## Integration Points

### Google Cloud Functions
**[Complete Cloud Functions Documentation](cloud-functions/)**

V_Track uses serverless Cloud Functions for payment and licensing:

- **[create-payment](cloud-functions/api-reference.md#create-payment)**: PayOS payment link generation
- **[webhook-handler](cloud-functions/api-reference.md#webhook-handler)**: Automated license delivery
- **[license-service](cloud-functions/api-reference.md#license-service)**: License validation & trial system
- **[pricing-service](cloud-functions/api-reference.md#pricing-service)**: Centralized pricing management

**Deployed in**: asia-southeast1 region (Singapore)

**See Also**:
- [Cloud Functions Setup & Deployment](cloud-functions/deployment-guide.md)
- [Firestore Database Schema](cloud-functions/firestore-schema.md)

### PayOS Payment Gateway
- Webhook endpoint: Cloud Functions `webhook-handler`
- Order creation: Desktop app → `create-payment` Cloud Function
- License delivery: Automated via webhook
- Payment flow: Desktop → Cloud Functions → PayOS → Webhook → Email

### Video Processing Pipeline
- MediaPipe hand detection
- OpenCV QR code scanning
- ROI-based filtering
- Frame sampling (trigger & continuous modes)

## Performance Optimization

**Database**:
- WAL mode for concurrent access
- 50+ indexes for query speed
- Connection pooling with retry logic

**Video Processing**:
- Frame sampling (83% reduction in processing time)
- ROI filtering (90% performance gain)
- Batch processing with job queue

See [Architecture § Performance](architecture/overview.md#performance--scalability)

## Troubleshooting

**Common Development Issues**:
- ModuleNotFoundError → Check you're running from `/backend/` directory
- Database locked → Ensure WAL mode enabled, use retry logic
- Import errors → Use absolute imports from `modules/`

See [CLAUDE.md § Critical Architecture Patterns](CLAUDE.md#critical-architecture-patterns)

## Contributing

This is a commercial desktop application. Internal development only.

**Before submitting changes**:
1. Read [CLAUDE.md](CLAUDE.md) guidelines
2. Follow import and database patterns
3. Update relevant documentation
4. Test with actual database

---

[← Back to Main Documentation](../README.md) | [User Docs →](../for-users/README.md)
