"""
Machine fingerprinting for license binding
"""

import platform
import hashlib
import uuid
import json
import logging

logger = logging.getLogger(__name__)


def generate_machine_fingerprint() -> str:
    """
    Generate unique machine fingerprint
    Returns: 32-character hex string
    """
    try:
        # Collect system identifiers
        fingerprint_data = {
            "hostname": platform.node(),
            "mac_address": str(uuid.getnode()),
            "system": platform.system(),
            "release": platform.release(),
            "processor": platform.processor()[:50],  # Truncate long processor names
        }

        # Create consistent hash
        data_string = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint_hash = hashlib.sha256(data_string.encode()).hexdigest()

        return fingerprint_hash[:32]  # Return first 32 chars

    except Exception as e:
        logger.error(f"Fingerprint generation failed: {e}")
        # Fallback to hostname-based hash
        fallback = hashlib.md5(platform.node().encode()).hexdigest()
        return fallback[:32]


def get_system_info() -> dict:
    """Get detailed system information for debugging"""
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "mac_address": str(uuid.getnode()),
    }
