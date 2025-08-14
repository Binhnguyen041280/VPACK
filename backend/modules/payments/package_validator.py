"""
Package Validation Service
Centralizes package validation using CloudFunction as single source
"""

import logging
from typing import Dict, Any, List, Optional
from modules.pricing.cloud_pricing_client import get_cloud_pricing_client

logger = logging.getLogger(__name__)

class PackageValidator:
    """Centralized package validation using CloudFunction"""
    
    def __init__(self):
        self.pricing_client = get_cloud_pricing_client()
        self._package_cache = None
        self._cache_timestamp = None
    
    def validate_package_type(self, package_type: str) -> Dict[str, Any]:
        """Validate if package type exists in CloudFunction"""
        try:
            # Get available packages
            available_packages = self._get_available_packages()
            
            if not available_packages:
                return {
                    'valid': False,
                    'error': 'Cannot validate package - pricing service unavailable',
                    'available_packages': []
                }
            
            if package_type in available_packages:
                return {
                    'valid': True,
                    'package_info': available_packages[package_type],
                    'available_packages': list(available_packages.keys())
                }
            else:
                return {
                    'valid': False,
                    'error': f'Invalid package type: {package_type}',
                    'available_packages': list(available_packages.keys())
                }
                
        except Exception as e:
            logger.error(f"Package validation error: {str(e)}")
            return {
                'valid': False,
                'error': f'Package validation failed: {str(e)}',
                'available_packages': []
            }
    
    def _get_available_packages(self) -> Dict[str, Any]:
        """Get available packages from CloudFunction with caching"""
        try:
            pricing_data = self.pricing_client.fetch_pricing_for_upgrade()
            
            if pricing_data.get('success'):
                return pricing_data.get('packages', {})
            else:
                logger.error(f"Failed to fetch packages: {pricing_data.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching packages: {str(e)}")
            return {}

# Singleton
_package_validator = None

def get_package_validator() -> PackageValidator:
    """Get singleton package validator"""
    global _package_validator
    if _package_validator is None:
        _package_validator = PackageValidator()
    return _package_validator