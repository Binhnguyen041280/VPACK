#!/usr/bin/env python3
"""
Cloud Manager for VTrack - Unified Cloud Interface
Handles connection management, folder discovery, and authentication validation
Supports multiple cloud providers with Google Drive as primary implementation
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import existing Google Drive client
from .google_drive_client import GoogleDriveClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CloudManager:
    """
    Unified cloud interface for VTrack video source management
    Provides consistent API across different cloud providers
    """

    # Supported cloud providers
    SUPPORTED_PROVIDERS = {
        "google_drive": {
            "name": "Google Drive",
            "client_class": GoogleDriveClient,
            "auth_type": "oauth2",
            "supports_folders": True,
            "supports_nested": True,
        }
        # Future: Dropbox, OneDrive, etc.
    }

    def __init__(self, provider: str = "google_drive"):
        """
        Initialize CloudManager for specified provider

        Args:
            provider (str): Cloud provider name ('google_drive', etc.)
        """
        self.provider = provider
        self.client = None
        self.authenticated = False
        self.user_info = {}

        # Validate provider
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}. Supported: {list(self.SUPPORTED_PROVIDERS.keys())}"
            )

        # Initialize provider-specific client
        self._initialize_client()

        logger.info(f"CloudManager initialized for provider: {provider}")

    def _initialize_client(self):
        """Initialize the provider-specific client"""
        try:
            provider_config = self.SUPPORTED_PROVIDERS[self.provider]
            client_class = provider_config["client_class"]

            if self.provider == "google_drive":
                self.client = client_class()
            else:
                # Future provider initialization
                raise NotImplementedError(f"Provider {self.provider} not yet implemented")

            logger.info(f"✅ {provider_config['name']} client initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize {self.provider} client: {e}")
            raise

    def test_connection_and_discover_folders(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test cloud connection and discover available folders
        Main method called by VTrack's /test-source endpoint

        Args:
            config (dict): Source configuration containing provider settings

        Returns:
            dict: Connection test results with folder discovery
        """
        try:
            logger.info(f"🔍 Testing {self.provider} connection and discovering folders...")

            # Step 1: Test basic connection
            connection_result = self.test_connection(config)

            if not connection_result["success"]:
                return {
                    "accessible": False,
                    "message": connection_result["message"],
                    "provider": self.provider,
                    "folders": [],
                    "cameras": [],
                }

            # Step 2: Discover root folders
            root_folders = self.discover_root_folders()

            # Step 3: Basic folder structure info
            folder_analysis = {"total_folders": len(root_folders)}

            logger.info(f"✅ Connection successful: {len(root_folders)} root folders discovered")

            return {
                "accessible": True,
                "message": f"{self.provider.title()} connection successful",
                "provider": self.provider,
                "user_info": self.user_info,
                "folders": root_folders,
                "folder_analysis": folder_analysis,
                "cameras": [],  # Will be populated when specific folder is selected
                "connection_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return {
                "accessible": False,
                "message": f"Connection failed: {str(e)}",
                "provider": self.provider,
                "folders": [],
                "cameras": [],
                "error": str(e),
            }

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test basic cloud provider connection

        Args:
            config (dict): Provider configuration

        Returns:
            dict: Connection test result
        """
        try:
            if self.provider == "google_drive":
                return self._test_google_drive_connection(config)
            else:
                return {"success": False, "message": f"Provider {self.provider} not implemented"}

        except Exception as e:
            logger.error(f"❌ Connection test error: {e}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    def _test_google_drive_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Google Drive specific connection"""
        try:
            # Attempt authentication
            auth_success = self.client.authenticate()

            if not auth_success:
                return {"success": False, "message": "Google Drive authentication failed"}

            # Test API access
            connection_test = self.client.test_connection()

            if connection_test["success"]:
                self.authenticated = True
                self.user_info = {
                    "email": connection_test.get("user_email", "Unknown"),
                    "storage_used_gb": connection_test.get("storage_used_gb", 0),
                    "storage_total_gb": connection_test.get("storage_total_gb", "Unknown"),
                }

                logger.info(f"✅ Google Drive authenticated: {self.user_info['email']}")
                return {
                    "success": True,
                    "message": f"Connected to Google Drive: {self.user_info['email']}",
                    "user_info": self.user_info,
                }
            else:
                return {"success": False, "message": connection_test["message"]}

        except Exception as e:
            logger.error(f"❌ Google Drive connection error: {e}")
            return {"success": False, "message": f"Google Drive connection failed: {str(e)}"}

    def discover_root_folders(self) -> List[Dict[str, Any]]:
        """
        Discover root-level folders in cloud storage

        Returns:
            list: List of root folder information
        """
        try:
            if not self.authenticated:
                logger.warning("⚠️ Not authenticated - cannot discover folders")
                return []

            if self.provider == "google_drive":
                return self._discover_google_drive_folders()
            else:
                logger.warning(f"⚠️ Folder discovery not implemented for {self.provider}")
                return []

        except Exception as e:
            logger.error(f"❌ Folder discovery error: {e}")
            return []

    def _discover_google_drive_folders(self) -> List[Dict[str, Any]]:
        """Discover Google Drive folders"""
        try:
            # Get root-level folders from Google Drive
            folders = self.client.list_files(folder_id="root", limit=50)

            root_folders = []
            for folder in folders:
                if folder.get("mimeType") == "application/vnd.google-apps.folder":
                    folder_info = {
                        "id": folder["id"],
                        "name": folder["name"],
                        "created_time": folder.get("createdTime"),
                        "size": folder.get("size", 0),
                        "provider": "google_drive",
                        "type": "folder",
                        "description": f"Google Drive folder: {folder['name']}",
                    }
                    root_folders.append(folder_info)

            logger.info(f"📁 Discovered {len(root_folders)} Google Drive root folders")
            return root_folders

        except Exception as e:
            logger.error(f"❌ Google Drive folder discovery error: {e}")
            return []

    def discover_subfolders(
        self, folder_id: str, credentials: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Discover subfolders within a specific folder
        Used for camera folder detection in nested structures

        Args:
            folder_id (str): Parent folder ID
            credentials (dict): Optional authentication credentials

        Returns:
            dict: Subfolder discovery results
        """
        try:
            logger.info(f"🔍 Discovering subfolders in folder: {folder_id}")

            if self.provider == "google_drive":
                return self._discover_google_drive_subfolders(folder_id, credentials)
            else:
                return {
                    "success": False,
                    "message": f"Subfolder discovery not implemented for {self.provider}",
                    "subfolders": [],
                }

        except Exception as e:
            logger.error(f"❌ Subfolder discovery error: {e}")
            return {
                "success": False,
                "message": f"Subfolder discovery failed: {str(e)}",
                "subfolders": [],
                "error": str(e),
            }

    def _discover_google_drive_subfolders(
        self, folder_id: str, credentials: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Discover Google Drive subfolders"""
        try:
            # Re-authenticate if credentials provided
            if credentials and not self.authenticated:
                # TODO: Use provided credentials for authentication
                pass

            # Get subfolders
            subfolders_raw = self.client.list_files(folder_id=folder_id, limit=100)

            subfolders = []
            camera_folders = []

            for item in subfolders_raw:
                if item.get("mimeType") == "application/vnd.google-apps.folder":
                    folder_info = {
                        "id": item["id"],
                        "name": item["name"],
                        "created_time": item.get("createdTime"),
                        "size": item.get("size", 0),
                        "parent_id": folder_id,
                        "provider": "google_drive",
                        "type": "folder",
                    }

                    # All folders are treated equally
                    folder_info["is_camera_folder"] = False

                    subfolders.append(folder_info)

            logger.info(f"📁 Found {len(subfolders)} subfolders")

            return {
                "success": True,
                "message": f"Found {len(subfolders)} subfolders",
                "subfolders": subfolders,
                "camera_folders": camera_folders,
                "total_folders": len(subfolders),
                "camera_count": len(camera_folders),
            }

        except Exception as e:
            logger.error(f"❌ Google Drive subfolder discovery error: {e}")
            return {
                "success": False,
                "message": f"Google Drive subfolder discovery failed: {str(e)}",
                "subfolders": [],
                "error": str(e),
            }

    def get_authentication_status(self) -> Dict[str, Any]:
        """
        Get current authentication status

        Returns:
            dict: Authentication status information
        """
        return {
            "authenticated": self.authenticated,
            "provider": self.provider,
            "user_info": self.user_info if self.authenticated else {},
            "last_check": datetime.now().isoformat(),
        }

    def disconnect(self) -> Dict[str, Any]:
        """
        Disconnect from cloud provider

        Returns:
            dict: Disconnection result
        """
        try:
            # Provider-specific disconnection logic
            if self.provider == "google_drive":
                # TODO: Implement Google Drive token revocation
                pass

            # Reset local state
            self.authenticated = False
            self.user_info = {}
            self.client = None

            # Reinitialize client
            self._initialize_client()

            logger.info(f"🔌 Disconnected from {self.provider}")

            return {
                "success": True,
                "message": f"Disconnected from {self.provider}",
                "provider": self.provider,
            }

        except Exception as e:
            logger.error(f"❌ Disconnection error: {e}")
            return {"success": False, "message": f"Disconnection failed: {str(e)}", "error": str(e)}

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the current cloud provider

        Returns:
            dict: Provider information
        """
        if self.provider in self.SUPPORTED_PROVIDERS:
            provider_config = self.SUPPORTED_PROVIDERS[self.provider]
            return {
                "provider": self.provider,
                "name": provider_config["name"],
                "auth_type": provider_config["auth_type"],
                "supports_folders": provider_config["supports_folders"],
                "supports_nested": provider_config["supports_nested"],
                "authenticated": self.authenticated,
                "available": True,
            }
        else:
            return {
                "provider": self.provider,
                "available": False,
                "error": "Provider not supported",
            }


def test_cloud_manager():
    """
    Test function for CloudManager functionality
    """
    print("🔧 Testing CloudManager...")

    try:
        # Initialize CloudManager
        print("\n1. Initializing CloudManager...")
        cloud_manager = CloudManager("google_drive")
        print(f"✅ CloudManager initialized for: {cloud_manager.provider}")

        # Get provider info
        print("\n2. Getting provider info...")
        provider_info = cloud_manager.get_provider_info()
        print(f"✅ Provider: {provider_info['name']}")
        print(f"   Supports folders: {provider_info['supports_folders']}")
        print(f"   Supports nested: {provider_info['supports_nested']}")

        # Test connection (will attempt authentication)
        print("\n3. Testing connection...")
        test_config = {}  # Empty config for basic test
        connection_result = cloud_manager.test_connection_and_discover_folders(test_config)

        if connection_result["accessible"]:
            print(f"✅ Connection successful!")
            print(f"   User: {connection_result.get('user_info', {}).get('email', 'Unknown')}")
            print(f"   Folders found: {len(connection_result.get('folders', []))}")
        else:
            print(f"❌ Connection failed: {connection_result['message']}")

        # Get authentication status
        print("\n4. Checking authentication status...")
        auth_status = cloud_manager.get_authentication_status()
        print(f"✅ Authenticated: {auth_status['authenticated']}")

        print("\n🎉 CloudManager test completed!")

    except Exception as e:
        print(f"❌ CloudManager test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_cloud_manager()
