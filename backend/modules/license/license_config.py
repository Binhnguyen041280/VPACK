"""License system configuration constants"""
import os

# License validation settings
LICENSE_CHECK_INTERVAL = 24  # hours
GRACE_PERIOD_DAYS = 7
MAX_ACTIVATIONS = 1

# API settings
CLOUD_VALIDATION_TIMEOUT = 10  # seconds
OFFLINE_MODE_ENABLED = True

# Database settings
LICENSE_TABLE = 'licenses'
ACTIVATION_TABLE = 'license_activations'

# UI settings
SHOW_EXPIRY_WARNING_DAYS = 30
AUTO_CHECK_ON_STARTUP = True