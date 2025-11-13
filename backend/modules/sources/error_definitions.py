#!/usr/bin/env python3
"""
Simplified Error Definitions for VTrack
Just essential error types and simple classification
"""

from enum import Enum
from typing import Dict

# ==================== SIMPLIFIED ERROR TYPES ====================


class VTrackError(Exception):
    """Base exception for VTrack operations"""

    pass


class VTrackNetworkError(VTrackError):
    """Network-related errors"""

    pass


class VTrackAuthError(VTrackError):
    """Authentication errors"""

    pass


class VTrackQuotaError(VTrackError):
    """Quota/limit errors"""

    pass


# ==================== SIMPLE ERROR CLASSIFICATION ====================


def classify_error_simple(error_text: str) -> str:
    """Simple error classification - just 4 types"""
    error_lower = error_text.lower()

    if any(keyword in error_lower for keyword in ["network", "timeout", "connection", "dns"]):
        return "network"
    elif any(keyword in error_lower for keyword in ["oauth", "token", "unauthorized", "auth"]):
        return "auth"
    elif any(keyword in error_lower for keyword in ["quota", "limit", "rate"]):
        return "quota"
    else:
        return "other"


# ==================== SIMPLE USER MESSAGES ====================

SIMPLE_USER_MESSAGES = {
    "network": "Network connection error",
    "auth": "Please log in again",
    "quota": "Download limit exceeded",
    "other": "Unknown error",
}
