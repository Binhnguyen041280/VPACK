# TimezoneManager Documentation

The **TimezoneManager** is a comprehensive timezone handling system for the ePACK application, designed to replace hardcoded timezone handling with a unified, configurable, and thread-safe solution.

## Features

- **Unified Timezone Handling**: Single point of control for all timezone operations
- **User-Configurable Timezones**: Supports user-defined timezones stored in database
- **Thread-Safe**: Concurrent access safe with caching for performance
- **Database Integration**: Seamlessly integrates with ePACK's safe_db_connection pattern
- **Fallback Support**: Graceful handling when database is unavailable
- **High Performance**: < 1ms for basic conversions with intelligent caching
- **Cross-Platform**: Uses zoneinfo (Python 3.9+) with pytz fallback

## Quick Start

### Basic Usage

```python
from modules.utils.timezone_manager import TimezoneManager

# Get singleton instance
tz = TimezoneManager()

# Current times
utc_now = tz.now_utc()           # Current UTC time
local_now = tz.now_local()       # Current local time (user's timezone)

# Conversions
utc_time = tz.to_utc(some_datetime)      # Convert to UTC
local_time = tz.to_local(some_datetime)   # Convert to local

# Database operations
db_string = tz.format_for_db(datetime_obj)  # Format for storage
parsed_dt = tz.parse_from_db(db_string)     # Parse from storage
```

### Convenience Functions

```python
from modules.utils import now_utc, now_local, to_utc, to_local, format_for_db, parse_from_db

# Direct access to common operations
current_utc = now_utc()
current_local = now_local()

# Quick conversions
utc_dt = to_utc(naive_datetime)
local_dt = to_local(utc_datetime)

# Database helpers
db_timestamp = format_for_db(datetime_obj)
dt = parse_from_db(db_timestamp)
```

## Core Concepts

### Timezone Storage
User timezone preferences are stored in the `general_info` table:

```sql
CREATE TABLE general_info (
    id INTEGER PRIMARY KEY,
    timezone TEXT,  -- IANA timezone (e.g., 'Asia/Ho_Chi_Minh')
    -- other fields...
);
```

### UTC+7 Conversion
Legacy `UTC+7` format is automatically converted to IANA `Asia/Ho_Chi_Minh` format for compatibility.

### Fallback Mechanism
When database is unavailable, the system falls back to `Asia/Ho_Chi_Minh` (Vietnam timezone).

## API Reference

### TimezoneManager Class

#### Core Methods

##### `now_utc() -> datetime`
Returns current UTC time with timezone information.

```python
utc_time = tz.now_utc()
# Returns: datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=timezone.utc)
```

##### `now_local() -> datetime`
Returns current time in user's configured timezone.

```python
local_time = tz.now_local()
# Returns: datetime.datetime(2023, 12, 25, 17, 30, 0, tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
```

##### `to_utc(dt: datetime) -> datetime`
Converts any datetime to UTC.

```python
# From naive datetime (assumes local timezone)
naive_dt = datetime(2023, 12, 25, 17, 30, 0)
utc_dt = tz.to_utc(naive_dt)

# From timezone-aware datetime
aware_dt = datetime(2023, 12, 25, 17, 30, 0, tzinfo=some_timezone)
utc_dt = tz.to_utc(aware_dt)
```

##### `to_local(dt: datetime) -> datetime`
Converts any datetime to user's local timezone.

```python
# From UTC datetime
utc_dt = datetime(2023, 12, 25, 10, 30, 0, tzinfo=timezone.utc)
local_dt = tz.to_local(utc_dt)

# From naive datetime (assumes UTC)
naive_dt = datetime(2023, 12, 25, 10, 30, 0)
local_dt = tz.to_local(naive_dt)
```

##### `format_for_db(dt: datetime) -> str`
Formats datetime for database storage (always UTC).

```python
dt = datetime(2023, 12, 25, 17, 30, 45, 123456)
db_string = tz.format_for_db(dt)
# Returns: "2023-12-25 10:30:45.123"  # Converted to UTC
```

##### `parse_from_db(dt_str: str) -> datetime`
Parses datetime from database and converts to local timezone.

```python
db_string = "2023-12-25 10:30:45.123"  # UTC from database
local_dt = tz.parse_from_db(db_string)
# Returns: datetime in user's local timezone
```

#### Configuration Methods

##### `get_user_timezone_name() -> str`
Returns user's configured timezone identifier.

```python
timezone_name = tz.get_user_timezone_name()
# Returns: "Asia/Ho_Chi_Minh"
```

##### `set_user_timezone(timezone_name: str) -> bool`
Updates user's timezone in database.

```python
success = tz.set_user_timezone("Asia/Tokyo")
if success:
    print("Timezone updated successfully")
```

##### `get_timezone_offset(dt: Optional[datetime] = None) -> str`
Gets timezone offset string for a given datetime.

```python
offset = tz.get_timezone_offset()
# Returns: "+07:00" or "-05:00" etc.

# For specific datetime
dt = datetime(2023, 12, 25, 17, 30, 0)
offset = tz.get_timezone_offset(dt)
```

#### Utility Methods

##### `clear_cache()`
Clears internal timezone cache (useful for testing or timezone updates).

```python
tz.clear_cache()  # Forces fresh database lookup
```

##### `temporary_timezone(timezone_name: str)`
Context manager for temporarily changing timezone.

```python
with tz.temporary_timezone("Asia/Tokyo"):
    tokyo_time = tz.now_local()  # Uses Tokyo timezone
# Automatically restored to original timezone
```

## Integration Examples

### Replacing Hardcoded Timezone Usage

**Before (hardcoded):**
```python
import pytz
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Convert to Vietnam timezone
vietnam_time = utc_dt.astimezone(VIETNAM_TZ)
```

**After (with TimezoneManager):**
```python
from modules.utils import to_local

# Convert to user's configured timezone
local_time = to_local(utc_dt)
```

### Database Operations

**Storing timestamps:**
```python
from modules.utils import format_for_db
from modules.db_utils.safe_connection import safe_db_connection

# Store current time
current_time = datetime.now()
db_timestamp = format_for_db(current_time)

with safe_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (event_time, description) VALUES (?, ?)",
        (db_timestamp, "Event occurred")
    )
    conn.commit()
```

**Reading timestamps:**
```python
from modules.utils import parse_from_db
from modules.db_utils.safe_connection import safe_db_connection

with safe_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT event_time FROM events WHERE id = ?", (event_id,))
    result = cursor.fetchone()
    
    if result:
        # Automatically converted to user's local timezone
        local_event_time = parse_from_db(result[0])
        print(f"Event occurred at: {local_event_time}")
```

### File Processing with Timestamps

```python
from modules.utils import timezone_manager, format_for_db
import os

def process_file_with_timezone(file_path):
    # Get file modification time
    mtime = os.path.getmtime(file_path)
    file_dt = datetime.fromtimestamp(mtime)
    
    # Convert to user's timezone for display
    local_dt = timezone_manager.to_local(file_dt)
    
    # Store in database (always UTC)
    db_timestamp = format_for_db(file_dt)
    
    print(f"File modified: {local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    return db_timestamp
```

### Working Hours Check

```python
from modules.utils import now_local

def is_within_working_hours():
    current_local = now_local()
    current_hour = current_local.hour
    
    # Working hours: 7 AM to 11 PM local time
    return 7 <= current_hour <= 23
```

## Migration Guide

### Step 1: Replace Direct Timezone Usage

Replace hardcoded timezone references:

```python
# OLD
import pytz
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')
local_time = utc_dt.astimezone(VIETNAM_TZ)

# NEW
from modules.utils import to_local
local_time = to_local(utc_dt)
```

### Step 2: Update Database Operations

Replace direct datetime formatting:

```python
# OLD
db_string = dt.strftime('%Y-%m-%d %H:%M:%S')

# NEW
from modules.utils import format_for_db
db_string = format_for_db(dt)
```

### Step 3: Update Timestamp Parsing

Replace manual datetime parsing:

```python
# OLD
dt = datetime.strptime(db_string, '%Y-%m-%d %H:%M:%S')

# NEW
from modules.utils import parse_from_db
dt = parse_from_db(db_string)  # Automatically in local timezone
```

## Performance Considerations

### Caching
- Timezone objects are cached after first use
- User timezone setting is cached after database lookup
- Cache is thread-safe and can be cleared when needed

### Database Calls
- User timezone is fetched once and cached
- Only database writes occur when changing timezone
- Fallback to default timezone if database unavailable

### Benchmarks
- Basic operations (now_utc, now_local): < 0.001ms
- Timezone conversions: < 0.01ms
- Database formatting/parsing: < 0.01ms

## Error Handling

### TimezoneError Exception
Custom exception raised for timezone-related errors:

```python
from modules.utils.timezone_manager import TimezoneError

try:
    tz.set_user_timezone("Invalid/Timezone")
except TimezoneError as e:
    print(f"Timezone error: {e}")
```

### Common Error Scenarios
1. **Invalid timezone name**: Raises `TimezoneError`
2. **Database unavailable**: Falls back to default timezone
3. **Invalid datetime format**: Raises `TimezoneError` during parsing
4. **Library unavailable**: Raises `TimezoneError` during initialization

## Thread Safety

The TimezoneManager is fully thread-safe:

```python
import threading
from modules.utils import timezone_manager

def worker_function(worker_id):
    # Safe to use in multiple threads
    for i in range(100):
        utc_time = timezone_manager.now_utc()
        local_time = timezone_manager.now_local()
        # Thread-safe operations

# Create multiple threads
threads = []
for i in range(10):
    thread = threading.Thread(target=worker_function, args=(i,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

## Testing

### Unit Tests
Run the test suite:

```bash
cd /Users/annhu/vtrack_app/ePACK/backend
python test_timezone_simple.py
```

### Integration Tests
The TimezoneManager includes integration tests with real database operations.

### Performance Tests
Performance benchmarks are included in the test suite to ensure < 1ms requirements are met.

## Troubleshooting

### Common Issues

**Issue**: "No timezone library available"
**Solution**: Ensure Python 3.9+ (for zoneinfo) or install pytz: `pip install pytz`

**Issue**: Database connection errors
**Solution**: TimezoneManager will fall back to default timezone. Check database configuration.

**Issue**: Incorrect timezone conversions
**Solution**: Verify user timezone setting in database: `SELECT timezone FROM general_info WHERE id = 1`

**Issue**: Performance concerns
**Solution**: TimezoneManager uses aggressive caching. Clear cache if needed: `timezone_manager.clear_cache()`

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from modules.utils.timezone_manager import TimezoneManager
tz = TimezoneManager()  # Will show debug information
```

## Best Practices

1. **Use convenience functions** for simple operations
2. **Store all timestamps in UTC** using `format_for_db()`
3. **Display in local timezone** using `parse_from_db()` or `to_local()`
4. **Cache timezone objects** are handled automatically
5. **Handle TimezoneError** for invalid timezone operations
6. **Test timezone changes** with `temporary_timezone()` context manager
7. **Clear cache** after timezone configuration changes

## Version History

- **v1.0** (2025-08-14): Initial implementation with full feature set
  - Singleton pattern with thread safety
  - Database integration with safe_db_connection
  - Comprehensive error handling and fallback mechanisms
  - Performance optimizations with caching
  - Full test coverage with integration tests