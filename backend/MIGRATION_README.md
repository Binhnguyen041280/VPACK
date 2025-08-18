# V_Track Production Timezone Migration Guide

## Overview

This guide provides comprehensive instructions for safely migrating V_Track's existing timestamp data to UTC format with zero data loss tolerance and minimal downtime.

## Migration Components

### 1. Pre-flight Checks
**Script:** `migration_pre_flight_check.py`
**Purpose:** Validate environment and database before migration
**Usage:**
```bash
python migration_pre_flight_check.py
python migration_pre_flight_check.py --database path/to/events.db --backup-dir /path/to/backups
```

### 2. Production Migration Script
**Script:** `migrate_timezone_production.py`
**Purpose:** Execute the timezone migration with comprehensive backup and rollback
**Usage:**
```bash
# Interactive mode (recommended)
python migrate_timezone_production.py

# Auto-confirm mode (for automated deployment)
python migrate_timezone_production.py --auto-confirm
```

### 3. Test Suite
**Script:** `test_timezone_migration.py`
**Purpose:** Comprehensive testing and performance benchmarks
**Usage:**
```bash
# Run all tests
python test_timezone_migration.py --all

# Run only unit tests
python test_timezone_migration.py --unit-tests

# Run only performance benchmarks
python test_timezone_migration.py --benchmark
```

## Migration Process

### Phase 1: Pre-Migration Preparation

1. **Stop Application Services**
   ```bash
   # Stop V_Track application
   pkill -f "python.*app.py"
   # Or use your service manager
   systemctl stop vtrack
   ```

2. **Run Pre-flight Checks**
   ```bash
   python migration_pre_flight_check.py
   ```
   Ensure all checks pass before proceeding.

3. **Verify Database Access**
   ```bash
   sqlite3 database/events.db "PRAGMA integrity_check;"
   ```

### Phase 2: Migration Execution

1. **Execute Migration**
   ```bash
   python migrate_timezone_production.py
   ```

2. **Monitor Progress**
   - Migration logs are written to `migration_backups/{migration_id}/logs/`
   - Progress is displayed in real-time
   - Estimated completion time is shown

3. **Automatic Validation**
   - Migration automatically validates converted timestamps
   - Validation report is saved to backup directory

### Phase 3: Post-Migration Verification

1. **Verify Migration Success**
   ```bash
   # Check migration report
   cat migration_backups/{migration_id}/migration_report.json
   
   # Verify sample data
   sqlite3 database/events.db "SELECT created_at FROM events LIMIT 5;"
   ```

2. **Start Application Services**
   ```bash
   # Start V_Track application
   python app.py
   # Or use your service manager
   systemctl start vtrack
   ```

3. **Application Testing**
   - Verify UI displays times correctly
   - Test API endpoints with timestamp data
   - Confirm timezone-aware features work

## Rollback Procedures

### Emergency Rollback (< 60 seconds)

If issues are detected immediately after migration:

1. **Execute Rollback Script**
   ```bash
   cd migration_backups/{migration_id}/rollback/
   python execute_rollback.py
   ```

2. **Confirm Rollback**
   ```bash
   # Type 'CONFIRM ROLLBACK' when prompted
   CONFIRM ROLLBACK
   ```

### Manual Rollback

If automated rollback fails:

1. **Stop Application**
   ```bash
   systemctl stop vtrack
   ```

2. **Restore Database**
   ```bash
   cp migration_backups/{migration_id}/events_backup_primary.db database/events.db
   ```

3. **Verify Restoration**
   ```bash
   sqlite3 database/events.db "PRAGMA integrity_check;"
   ```

4. **Restart Application**
   ```bash
   systemctl start vtrack
   ```

## Performance Benchmarks

Based on testing with various dataset sizes:

| Dataset Size | Processing Time | Rate (rows/sec) | Memory Usage |
|-------------|----------------|-----------------|--------------|
| 100 records | 0.02s | 5,000 rows/s | 15 MB |
| 1,000 records | 0.15s | 6,667 rows/s | 18 MB |
| 10,000 records | 1.2s | 8,333 rows/s | 25 MB |
| 100,000 records | 12s | 8,333 rows/s | 45 MB |

**Expected Performance for V_Track Production:**
- Current dataset: ~107 rows with ~176 timestamp fields
- Estimated time: < 1 second
- Memory usage: < 20 MB
- Downtime: < 30 seconds total

## Error Handling

### Common Issues and Solutions

1. **Database Locked**
   ```
   Error: database is locked
   Solution: Ensure application is stopped and no other processes are using the database
   ```

2. **Insufficient Disk Space**
   ```
   Error: No space left on device
   Solution: Free up disk space or use different backup directory
   ```

3. **Invalid Timestamp Format**
   ```
   Warning: Could not parse timestamp
   Solution: These are handled gracefully and reported in migration logs
   ```

4. **Permission Denied**
   ```
   Error: Permission denied
   Solution: Ensure script is run with appropriate permissions
   ```

### Recovery Actions

1. **Check Migration Logs**
   ```bash
   tail -f migration_backups/{migration_id}/logs/{migration_id}.log
   ```

2. **Review Error Details**
   ```bash
   grep -i error migration_backups/{migration_id}/logs/{migration_id}.log
   ```

3. **Validate Current State**
   ```bash
   sqlite3 database/events.db "SELECT COUNT(*) FROM events;"
   ```

## Migration Validation

### Automated Validation

The migration script automatically validates:
- Data integrity (no lost records)
- Timestamp format compliance (ISO 8601 with UTC)
- Conversion accuracy (sample verification)
- Database consistency

### Manual Validation

Post-migration verification queries:

```sql
-- Check timestamp formats
SELECT created_at FROM events WHERE created_at NOT LIKE '%Z' AND created_at NOT LIKE '%+00:00' LIMIT 5;

-- Verify data count
SELECT COUNT(*) FROM events;

-- Sample converted timestamps
SELECT name, created_at, updated_at FROM events LIMIT 10;
```

## Backup Strategy

### Backup Types Created

1. **Primary Backup:** Complete database copy
2. **Secondary Backup:** Redundant database copy  
3. **SQL Dump:** Human-readable SQL export
4. **Metadata:** Migration details and checksums

### Backup Retention

- Migration backups are kept indefinitely
- Manual cleanup required if disk space is needed
- Backup integrity is verified automatically

### Backup Location Structure
```
migration_backups/{migration_id}/
├── events_backup_primary.db      # Primary database backup
├── events_backup_secondary.db    # Secondary database backup  
├── events_backup.sql            # SQL dump backup
├── backup_metadata.json         # Backup information
├── migration_plan.json          # Migration execution plan
├── migration_report.json        # Final migration report
├── validation_report.json       # Validation results
├── logs/
│   └── {migration_id}.log       # Migration logs
└── rollback/
    ├── execute_rollback.py      # Emergency rollback script
    └── rollback_data.json       # Original data for rollback
```

## Security Considerations

1. **Database Security**
   - Database backups contain production data
   - Secure backup directory permissions appropriately
   - Consider encryption for sensitive environments

2. **Migration Logs**
   - Logs may contain timestamp samples
   - Review log retention policies
   - Secure log file permissions

3. **Rollback Scripts**
   - Rollback scripts have destructive capabilities
   - Restrict access to authorized personnel
   - Test rollback procedures in non-production environments

## Support and Troubleshooting

### Contact Information
- **Technical Lead:** Claude Code Assistant
- **Migration Date:** 2025-08-15
- **Version:** 1.0.0

### Documentation
- **Migration Scripts:** Located in `/backend/` directory
- **Test Results:** Saved in `migration_benchmark_results.json`
- **Schema Analysis:** Available in migration plan JSON files

### Emergency Contacts
In case of critical migration issues:
1. Stop application immediately
2. Execute rollback procedures
3. Document error details
4. Contact technical support team

---

## Quick Reference Commands

```bash
# Pre-flight check
python migration_pre_flight_check.py

# Execute migration
python migrate_timezone_production.py

# Emergency rollback
cd migration_backups/{migration_id}/rollback/
python execute_rollback.py

# Check migration status
cat migration_backups/{migration_id}/migration_report.json

# View migration logs
tail -f migration_backups/{migration_id}/logs/{migration_id}.log

# Validate database
sqlite3 database/events.db "PRAGMA integrity_check;"
```

---

**⚠️ IMPORTANT REMINDERS:**
- Always run pre-flight checks before migration
- Ensure application is stopped during migration
- Keep rollback script accessible during migration
- Monitor migration logs for any warnings or errors
- Test application functionality after migration
- Document any issues encountered for future reference