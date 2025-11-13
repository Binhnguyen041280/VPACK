"""
Machine ID Generator for Trial System
Simple but effective machine fingerprinting
"""

import hashlib
import platform
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_machine_id() -> str:
    """
    Generate unique machine identifier
    Uses platform info + MAC address for uniqueness

    Returns:
        16-character machine ID string
    """
    try:
        # Collect machine information
        machine_info = []

        # Platform information
        machine_info.append(platform.node())  # Computer name
        machine_info.append(platform.machine())  # Machine type (x86_64, etc.)
        machine_info.append(platform.processor())  # Processor name
        machine_info.append(platform.system())  # OS name (Darwin, Windows, Linux)

        # Network interface (MAC address)
        try:
            import uuid

            mac_address = hex(uuid.getnode())[2:].upper().zfill(12)
            machine_info.append(mac_address)
        except:
            machine_info.append("NO_MAC")

        # Combine all info
        combined_info = "|".join(str(info) for info in machine_info if info)

        # Generate hash
        machine_hash = hashlib.sha256(combined_info.encode("utf-8")).hexdigest()

        # Return first 16 characters as machine ID
        machine_id = machine_hash[:16].upper()

        logger.debug(f"Generated machine ID: {machine_id}")
        return machine_id

    except Exception as e:
        logger.error(f"Failed to generate machine ID: {e}")
        # Fallback to simple hash
        import time

        fallback_info = f"{platform.system()}-{int(time.time())}"
        fallback_hash = hashlib.md5(fallback_info.encode()).hexdigest()
        return fallback_hash[:16].upper()


def get_machine_info() -> dict:
    """
    Get detailed machine information for debugging

    Returns:
        Dictionary with machine details
    """
    try:
        import uuid

        machine_info = {
            "machine_id": generate_machine_id(),
            "platform": {
                "system": platform.system(),
                "node": platform.node(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "platform": platform.platform(),
                "version": platform.version(),
            },
            "network": {"mac_address": hex(uuid.getnode())[2:].upper().zfill(12)},
        }

        return machine_info

    except Exception as e:
        logger.error(f"Failed to get machine info: {e}")
        return {"machine_id": generate_machine_id(), "error": str(e)}


def validate_machine_id(machine_id: str) -> bool:
    """
    Validate machine ID format

    Args:
        machine_id: Machine ID to validate

    Returns:
        True if valid format, False otherwise
    """
    try:
        if not machine_id:
            return False

        # Should be 16 character hex string
        if len(machine_id) != 16:
            return False

        # Should only contain hex characters
        try:
            int(machine_id, 16)
            return True
        except ValueError:
            return False

    except Exception:
        return False
