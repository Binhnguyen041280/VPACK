# ePACK User Documentation

Comprehensive guides for end-users of ePACK video processing system.

## Getting Started

New to ePACK? Follow these guides in order:

1. **[Installation Guide](installation.md)** ⭐ START HERE
   - System requirements
   - Backend and frontend setup
   - Database initialization
   - Initial system setup

2. **[Configuration Wizard](configuration-wizard.md)** 🚀 FIRST-TIME SETUP
   - 5-step guided configuration
   - Brand name and location settings
   - Video source selection (local/cloud)
   - ROI detection and timing setup
   - Complete system initialization

3. **[Processing Modes](processing-modes.md)**
   - First Run mode (initial data processing)
   - Default mode (continuous auto-scan)
   - Custom mode (on-demand processing)

4. **[ROI Configuration](roi-configuration.md)**
   - Setting up Region of Interest (ROI)
   - Packing area and QR trigger zones
   - Hand detection configuration
   - Multi-camera setup

## Core Features

### Event Tracking
**[Trace Tracking Guide](trace-tracking.md)**
- Search events by tracking code
- Batch upload via Excel/CSV
- QR code image scanning
- Platform management (Shopee, Lazada, TikTok)
- Export results to CSV

### Cloud Integration
**[Cloud Sync Advanced](cloud-sync-advanced.md)**
- Google Drive OAuth setup
- Folder selection and lazy loading
- Auto-sync configuration
- Downloaded files management
- Troubleshooting sync issues

### License & Subscription
**[License & Payment Guide](license-payment.md)**
- Subscription plans (Personal/Business)
- PayOS payment flow
- License activation
- Machine fingerprinting
- Renewal process

## Quick Reference

| Feature | Guide | Page |
|---------|-------|------|
| Install ePACK | [Installation](installation.md) | Setup |
| First-time wizard | [Configuration Wizard](configuration-wizard.md) | Wizard |
| Process videos | [Processing Modes](processing-modes.md) | Modes |
| Configure cameras | [ROI Configuration](roi-configuration.md) | ROI |
| Search events | [Trace Tracking](trace-tracking.md) | Search |
| Sync Google Drive | [Cloud Sync](cloud-sync-advanced.md) | Cloud |
| Manage license | [License & Payment](license-payment.md) | License |

## Video Tutorials

Coming soon - Check `/docs/vtrack-official/assets/videos/` for tutorial videos.

## FAQ & Troubleshooting

Each guide includes a dedicated troubleshooting section. Common issues:

- **Installation issues** → See [Installation Guide § Troubleshooting](installation.md#troubleshooting)
- **Wizard not appearing** → See [Configuration Wizard § Troubleshooting](configuration-wizard.md#troubleshooting)
- **Processing not working** → See [Processing Modes § Troubleshooting](processing-modes.md#troubleshooting)
- **Cloud sync errors** → See [Cloud Sync § Troubleshooting](cloud-sync-advanced.md#troubleshooting)
- **Search not returning results** → See [Trace Tracking § Troubleshooting](trace-tracking.md#troubleshooting)

## Support

If you can't find the answer in the documentation:

- **Email**: support@epack.com
- **Health Check**: http://localhost:8080/health
- **Log Files**: `/var/logs/app_latest.log`, `/var/logs/event_processing_latest.log`

---

[← Back to Main Documentation](../README.md) | [Developer Docs →](../for-developers/README.md)
