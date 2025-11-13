"""
Cloud Pricing Client for V_Track Desktop
Fetch pricing from CloudFunction on-demand
"""

import requests
import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CloudPricingClient:
    """Client to fetch pricing from CloudFunction"""

    def __init__(self):
        # CloudFunction URL
        self.pricing_url = os.getenv(
            "PRICING_SERVICE_URL",
            "https://asia-southeast1-v-track-payments.cloudfunctions.net/pricing-service",
        )

        # Session cache (chỉ trong memory)
        self.session_cache = None
        self.cache_timestamp = None

        logger.info(f"Pricing client initialized: {self.pricing_url}")

    def fetch_pricing_on_startup(self) -> Dict[str, Any]:
        """Fetch pricing when app starts - cache for session"""

        logger.info("🚀 Fetching pricing on app startup...")

        try:
            response = requests.get(
                f"{self.pricing_url}?action=get_packages",
                timeout=10,
                headers={"User-Agent": "VTrack-Desktop/2.1.0", "Accept": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("success"):
                    # Cache for session
                    self.session_cache = data
                    self.cache_timestamp = datetime.now()

                    packages_count = len(data.get("packages", {}))
                    version = data.get("version", "unknown")

                    logger.info(
                        f"✅ Startup pricing loaded: {packages_count} packages, version {version}"
                    )
                    return data
                else:
                    logger.error(f"❌ Pricing API error: {data.get('error')}")
                    return self._get_fallback_pricing()
            else:
                logger.error(f"❌ HTTP error {response.status_code}: {response.text}")
                return self._get_fallback_pricing()

        except requests.exceptions.Timeout:
            logger.warning("⏰ Pricing API timeout - using fallback")
            return self._get_fallback_pricing()
        except requests.exceptions.ConnectionError:
            logger.warning("🌐 No internet connection - using fallback")
            return self._get_fallback_pricing()
        except Exception as e:
            logger.error(f"💥 Unexpected error: {str(e)}")
            return self._get_fallback_pricing()

    def fetch_pricing_for_upgrade(self) -> Dict[str, Any]:
        """Fetch fresh pricing when user wants to upgrade"""

        logger.info("💰 Fetching fresh pricing for upgrade...")

        try:
            response = requests.get(
                f"{self.pricing_url}?action=get_packages&fresh=true",
                timeout=15,  # Longer timeout for user action
                headers={"User-Agent": "VTrack-Desktop/2.1.0", "Accept": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("success"):
                    packages_count = len(data.get("packages", {}))
                    version = data.get("version", "unknown")

                    logger.info(
                        f"✅ Fresh pricing loaded: {packages_count} packages, version {version}"
                    )

                    # Update cache
                    self.session_cache = data
                    self.cache_timestamp = datetime.now()

                    return data
                else:
                    logger.error(f"❌ Fresh pricing API error: {data.get('error')}")
                    return self.session_cache or self._get_fallback_pricing()
            else:
                logger.error(f"❌ Fresh pricing HTTP error {response.status_code}")
                return self.session_cache or self._get_fallback_pricing()

        except Exception as e:
            logger.error(f"💥 Failed to fetch fresh pricing: {str(e)}")
            return self.session_cache or self._get_fallback_pricing()

    def get_cached_pricing(self) -> Optional[Dict[str, Any]]:
        """Get cached pricing for display (no API call)"""
        return self.session_cache

    def _get_fallback_pricing(self) -> Dict[str, Any]:
        """No fallback pricing - return error when CloudFunction unavailable"""

        logger.error("🆘 CloudFunction pricing unavailable - no fallback pricing")

        return {
            "success": False,
            "error": "Pricing service unavailable - please check internet connection",
            "packages": {},
            "source": "error",
            "timestamp": datetime.now().isoformat(),
            "support_contact": "alanngaongo@gmail.com",
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to pricing service"""

        try:
            response = requests.get(f"{self.pricing_url}?action=health", timeout=5)

            if response.status_code == 200:
                data = response.json()
                return {
                    "connected": True,
                    "status": data.get("status"),
                    "version": data.get("version"),
                    "packages_available": data.get("packages_available"),
                }
            else:
                return {"connected": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"connected": False, "error": str(e)}


# Singleton instance
_cloud_pricing_client = None


def get_cloud_pricing_client() -> CloudPricingClient:
    """Get singleton pricing client"""
    global _cloud_pricing_client
    if _cloud_pricing_client is None:
        _cloud_pricing_client = CloudPricingClient()
    return _cloud_pricing_client
