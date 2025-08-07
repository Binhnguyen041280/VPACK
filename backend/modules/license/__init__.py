"""
V_Track Desktop License Management Module
Entry point for license system
"""
from .license_manager import LicenseManager
from .license_checker import LicenseChecker
from .machine_fingerprint import generate_machine_fingerprint

__all__ = ['LicenseManager', 'LicenseChecker', 'generate_machine_fingerprint']