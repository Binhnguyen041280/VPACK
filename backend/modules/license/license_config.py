"""License system configuration constants - Enhanced for Offline Fallback"""
import os

# License validation settings
LICENSE_CHECK_INTERVAL = 24  # hours
GRACE_PERIOD_DAYS = 7  # Days to allow offline usage after expiry
MAX_ACTIVATIONS = 1

# API settings
CLOUD_VALIDATION_TIMEOUT = 10  # seconds
OFFLINE_MODE_ENABLED = True
CONNECTIVITY_CACHE_SECONDS = 30  # Cache connectivity status

# Database settings
LICENSE_TABLE = 'licenses'
ACTIVATION_TABLE = 'license_activations'

# UI settings
SHOW_EXPIRY_WARNING_DAYS = 30
AUTO_CHECK_ON_STARTUP = True

# Offline support settings - Enhanced
OFFLINE_GRACE_PERIOD_DAYS = 7  # Allow offline usage within this period
OFFLINE_GRACE_PERIOD_HOURS = 72  # Hours for fine-grained grace period
MAX_OFFLINE_DAYS = 30  # Maximum days to run offline
FORCE_CLOUD_VALIDATION_DAYS = 7  # Force cloud validation after this period

# Auto-sync and retry settings
CLOUD_SYNC_RETRY_MINUTES = 30  # Minutes between cloud sync retry attempts
CLOUD_SYNC_MAX_RETRIES = 5  # Maximum retry attempts before giving up
CLOUD_SYNC_BACKOFF_MULTIPLIER = 2  # Exponential backoff multiplier

# Connectivity test settings
DNS_TEST_HOST = 'google.com'
HTTP_TEST_URL = 'https://httpbin.org/status/200'
SOCKET_TEST_HOST = '8.8.8.8'
SOCKET_TEST_PORT = 53
CONNECTIVITY_TIMEOUT = 3  # seconds

# Offline feature limits and capabilities
OFFLINE_FEATURES = {
    'license_validation': True,      # Can validate existing licenses offline
    'machine_binding': True,         # Can check machine fingerprint offline
    'activation_records': True,      # Can create/check activation records
    'expiry_checking': True,         # Can check license expiry offline
    'basic_app_functions': True,     # Core app functionality works offline
    
    # Limited/disabled features offline
    'payment_processing': False,     # Cannot process payments offline
    'license_purchase': False,       # Cannot buy new licenses offline
    'cloud_sync': False,            # Cannot sync with cloud storage offline
    'email_notifications': False,   # Cannot send emails offline
    'license_transfer': False,      # Cannot transfer licenses offline
    'remote_validation': False,     # Cannot validate with remote servers
    'usage_analytics': False,       # Cannot upload usage data offline
    'automatic_updates': False      # Cannot check/download updates offline
}

# Offline mode messages and warnings
OFFLINE_MESSAGES = {
    'validation_offline': 'License validated from local database - some features limited',
    'activation_offline': 'License activated offline - sync recommended when online',
    'payment_disabled': 'Payment features unavailable in offline mode',
    'sync_pending': 'Cloud sync pending - will resume when connection restored',
    'limited_features': 'Running in offline mode - limited functionality available',
    'cloud_unavailable': 'Cloud services unavailable - using local validation',
    'reconnect_recommended': 'Connect to internet for full functionality'
}

# Offline mode behavior configuration
OFFLINE_BEHAVIOR = {
    'allow_new_activations': True,           # Allow activating existing licenses offline
    'allow_existing_validation': True,       # Allow validating known licenses offline
    'block_unknown_licenses': True,         # Block completely unknown licenses offline
    'show_offline_warnings': True,          # Show offline mode warnings to users
    'cache_validation_results': True,       # Cache validation results for offline use
    'fallback_to_database': True,          # Use database when cloud unavailable
    'require_internet_for_purchase': True,  # Always require internet for purchases
    'grace_period_enforcement': True,       # Enforce grace periods for expired licenses
    'auto_retry_cloud_sync': True,         # Automatically retry cloud sync when online
    'log_offline_activities': True         # Log all offline activities for later sync
}

# Environment-based overrides
if os.getenv('EPACK_OFFLINE_MODE'):
    OFFLINE_MODE_ENABLED = os.getenv('EPACK_OFFLINE_MODE', 'true').lower() == 'true'

if os.getenv('EPACK_GRACE_PERIOD_HOURS'):
    OFFLINE_GRACE_PERIOD_HOURS = int(os.getenv('EPACK_GRACE_PERIOD_HOURS', '72'))

if os.getenv('EPACK_SYNC_RETRY_MINUTES'):
    CLOUD_SYNC_RETRY_MINUTES = int(os.getenv('EPACK_SYNC_RETRY_MINUTES', '30'))

# Development/debug settings
DEBUG_OFFLINE_MODE = os.getenv('DEBUG_OFFLINE_MODE', 'false').lower() == 'true'
SIMULATE_OFFLINE_MODE = os.getenv('SIMULATE_OFFLINE_MODE', 'false').lower() == 'true'
VERBOSE_OFFLINE_LOGGING = os.getenv('VERBOSE_OFFLINE_LOGGING', 'false').lower() == 'true'

# Validation helpers
def get_offline_feature_status(feature_name: str) -> bool:
    """Get offline availability status for a feature"""
    return OFFLINE_FEATURES.get(feature_name, False)

def get_offline_message(message_key: str) -> str:
    """Get offline mode message by key"""
    return OFFLINE_MESSAGES.get(message_key, 'Operating in offline mode')

def get_offline_behavior(behavior_key: str) -> bool:
    """Get offline behavior setting by key"""
    return OFFLINE_BEHAVIOR.get(behavior_key, False)

def is_offline_mode_enabled() -> bool:
    """Check if offline mode is enabled"""
    return OFFLINE_MODE_ENABLED

def get_grace_period_hours() -> int:
    """Get grace period in hours"""
    return OFFLINE_GRACE_PERIOD_HOURS

def get_sync_retry_interval() -> int:
    """Get cloud sync retry interval in minutes"""
    return CLOUD_SYNC_RETRY_MINUTES