# ePACK Official Documentation

Welcome to the official documentation for ePACK - Intelligent Video Processing & Tracking System.

## Documentation Structure

This documentation is organized into two main sections:

### 👤 [For Users](for-users/)
End-user guides covering installation, configuration, and day-to-day usage of ePACK.

**Getting Started**:
1. [Installation Guide](for-users/installation.md) - Setup backend and frontend
2. [Processing Modes](for-users/processing-modes.md) - Understanding First Run, Default, and Custom modes
3. [ROI Configuration](for-users/roi-configuration.md) - Setting up detection regions

**Core Features**:
- [Trace Tracking](for-users/trace-tracking.md) - Search events and analyze tracking codes
- [License & Payment](for-users/license-payment.md) - Subscription management and activation
- [Cloud Sync](for-users/cloud-sync-advanced.md) - Google Drive integration

### 👨‍💻 [For Developers](for-developers/)
Technical documentation for developers working on or integrating with ePACK.

**Architecture**:
- [System Overview](for-developers/architecture/overview.md) - Complete architecture and database schema
- Frontend structure (Next.js 15.1.6)
- Backend modules (Flask 3.0.0)

**API Reference**:
- [API Endpoints](for-developers/api/endpoints.md) - Complete REST API documentation
- [Cloud Functions API](for-developers/cloud-functions/api-reference.md) - Serverless backend API
- Authentication flows
- Webhook integration

**Cloud Infrastructure**:
- [Cloud Functions Overview](for-developers/cloud-functions/) - Serverless payment & licensing backend
- [Deployment Guide](for-developers/cloud-functions/deployment-guide.md) - Setup and deployment
- [Firestore Schema](for-developers/cloud-functions/firestore-schema.md) - Cloud database structure

**Development**:
- [CLAUDE.md](for-developers/CLAUDE.md) - Development guidelines for AI agents
- Setup environment
- Coding standards
- Testing procedures

## Quick Links

**ePACK Main Application**:
- **Main Project README**: [/README.md](../../README.md)
- **Backend Code**: `/backend/`
- **Frontend Code**: `/frontend/`
- **Documentation Assets**: [assets/](assets/)

**ePACK Cloud Functions** (Serverless Backend):
- **CloudFunctions Repository**: `/ePACK_CloudFunctions/`
- **CloudFunctions Docs**: [for-developers/cloud-functions/](for-developers/cloud-functions/)
- **API Reference**: [Cloud Functions API](for-developers/cloud-functions/api-reference.md)
- **Deployment Guide**: [Setup & Deploy](for-developers/cloud-functions/deployment-guide.md)

## Version Information

- **ePACK Version**: 2.1.0
- **Documentation Last Updated**: 2025-10-06
- **Platform**: Desktop (Windows, macOS, Linux)

## Support

- **Email**: support@epack.com
- **Health Check**: http://localhost:8080/health
- **Issue Tracker**: Contact development team

---

**Note**: For legacy documentation, migration scripts, and archived materials, see the `/docs/archive/` folder.
