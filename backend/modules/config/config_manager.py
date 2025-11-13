from datetime import datetime, timedelta
from flask import request, jsonify, g
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple
from google.oauth2.credentials import Credentials
import google.auth.exceptions
import google.auth.transport.requests
import logging
import os
import sys
from .security_config import SecurityConfig

# Import database functions that are used throughout the module
try:
    # Import from the backend root directory
    import importlib.util

    database_path = os.path.join(os.path.dirname(__file__), "../../../database.py")
    spec = importlib.util.spec_from_file_location("database", database_path)
    if spec and spec.loader:
        database_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(database_module)
        get_session = database_module.get_session
        update_session_credentials = database_module.update_session_credentials
        cleanup_expired_sessions = database_module.cleanup_expired_sessions
    else:
        raise ImportError("Could not load database module")
except Exception:
    # Fallback if import fails
    get_session = None
    update_session_credentials = None
    cleanup_expired_sessions = None

logger = logging.getLogger(__name__)


class ConfigManager:
    """Enhanced configuration manager with security features"""

    def __init__(self, db_manager=None):
        self.db = db_manager
        self.security = SecurityConfig()

        # = SECURITY: Cloud credential proxy cache
        self._credential_cache = {}
        self._cache_expiry = {}

        logger.info("=' Configuration manager initialized with security")

    # = SECURITY: Session verification middleware
    def require_session(self, f):
        """Decorator to require valid session"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "No valid session token provided"}), 401

            token = auth_header.split(" ")[1]
            session_data = self.security.validate_session_token(token)

            if not session_data:
                return jsonify({"error": "Invalid or expired session"}), 401

            # Check session in database
            if self.db and get_session:
                db_session = get_session(token)
                if not db_session:
                    return jsonify({"error": "Session not found"}), 401

                g.session_token = token
                g.user_email = session_data["user_email"]
                g.provider = session_data.get("provider", "google_drive")
                g.db_session = db_session

            return f(*args, **kwargs)

        return decorated_function

    # = SECURITY: Session-based source validation
    def validate_cloud_source(self, source_config: Dict, session_token: str) -> Tuple[bool, str]:
        """Validate cloud source configuration with session"""
        try:
            if not session_token:
                return False, "No session token provided"

            # Validate session
            session_data = self.security.validate_session_token(session_token)
            if not session_data:
                return False, "Invalid or expired session"

            # Get session from database
            if self.db and get_session:
                db_session = get_session(session_token)
                if not db_session:
                    return False, "Session not found in database"

                # Validate provider matches
                if source_config.get("provider") != db_session.get("provider"):
                    return False, "Provider mismatch with session"

                # Validate user matches
                if session_data["user_email"] != db_session["user_email"]:
                    return False, "User mismatch with session"

            # Validate required fields
            required_fields = ["provider", "selected_folders"]
            for field in required_fields:
                if field not in source_config:
                    return False, f"Missing required field: {field}"

            if not source_config["selected_folders"]:
                return False, "No folders selected"

            return True, "Cloud source configuration valid"

        except Exception as e:
            logger.error(f"Error validating cloud source: {e}")
            return False, f"Validation error: {str(e)}"

    # = SECURITY: Backend credential proxy for cloud operations
    def get_cloud_credentials(self, session_token: str) -> Optional[Credentials]:
        """Get decrypted credentials for cloud operations"""
        try:
            # Check cache first
            if session_token in self._credential_cache:
                cached_time = self._cache_expiry.get(session_token)
                if cached_time and datetime.utcnow() < cached_time:
                    return self._credential_cache[session_token]
                else:
                    # Clean expired cache
                    self._credential_cache.pop(session_token, None)
                    self._cache_expiry.pop(session_token, None)

            # Get session from database
            if not self.db:
                logger.error("Database manager not available")
                return None

            if get_session:
                db_session = get_session(session_token)
            if not db_session:
                logger.error("Session not found")
                return None

            # Decrypt credentials
            encrypted_creds = db_session.get("encrypted_credentials")
            if not encrypted_creds:
                logger.error("No encrypted credentials found")
                return None

            creds_dict = self.security.decrypt_credentials(encrypted_creds)

            # Create Google credentials object
            credentials = Credentials(
                token=creds_dict.get("token"),
                refresh_token=creds_dict.get("refresh_token"),
                token_uri=creds_dict.get("token_uri"),
                client_id=creds_dict.get("client_id"),
                client_secret=creds_dict.get("client_secret"),
                scopes=creds_dict.get("scopes"),
            )

            # Cache for 5 minutes
            self._credential_cache[session_token] = credentials
            self._cache_expiry[session_token] = datetime.utcnow() + timedelta(minutes=5)

            return credentials

        except Exception as e:
            logger.error(f"Failed to get cloud credentials: {e}")
            return None

    def refresh_cloud_credentials(self, session_token: str) -> bool:
        """Refresh cloud credentials and update session"""
        try:
            credentials = self.get_cloud_credentials(session_token)
            if not credentials:
                return False

            # Try to refresh
            credentials.refresh(google.auth.transport.requests.Request())

            # Update encrypted credentials in database
            creds_dict = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
            }

            encrypted_creds = self.security.encrypt_credentials(creds_dict)

            if self.db and update_session_credentials:
                success = update_session_credentials(session_token, encrypted_creds)
                if success:
                    # Update cache
                    self._credential_cache[session_token] = credentials
                    self._cache_expiry[session_token] = datetime.utcnow() + timedelta(minutes=5)
                    logger.info("Cloud credentials refreshed successfully")
                    return True

            return False

        except google.auth.exceptions.RefreshError as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return False
        except Exception as e:
            logger.error(f"Error refreshing credentials: {e}")
            return False

    def proxy_cloud_operation(self, session_token: str, operation: str, **kwargs) -> Dict:
        """Proxy cloud operations with backend credentials"""
        try:
            credentials = self.get_cloud_credentials(session_token)
            if not credentials:
                return {"success": False, "error": "Unable to get credentials"}

            # Import Google Drive service here to avoid circular imports
            from googleapiclient.discovery import build

            service = build("drive", "v3", credentials=credentials)

            if operation == "list_folders":
                # List folders operation
                query = "mimeType='application/vnd.google-apps.folder'"
                if "parent_id" in kwargs:
                    query += f" and '{kwargs['parent_id']}' in parents"

                results = (
                    service.files()
                    .list(
                        q=query,
                        fields="files(id, name, parents)",
                        pageSize=kwargs.get("page_size", 100),
                    )
                    .execute()
                )

                folders = results.get("files", [])
                return {"success": True, "folders": folders, "count": len(folders)}

            elif operation == "download_file":
                # Download file operation
                file_id = kwargs.get("file_id")
                if not file_id:
                    return {"success": False, "error": "File ID required"}

                # Get file metadata first
                file_metadata = service.files().get(fileId=file_id).execute()

                # Download file content
                content = service.files().get_media(fileId=file_id).execute()

                return {"success": True, "metadata": file_metadata, "content": content}

            else:
                return {"success": False, "error": f"Unsupported operation: {operation}"}

        except Exception as e:
            logger.error(f"Cloud operation failed: {e}")
            return {"success": False, "error": str(e)}

    def cleanup_expired_sessions(self):
        """Cleanup expired sessions and cache"""
        if self.db and cleanup_expired_sessions:
            deleted_count = cleanup_expired_sessions()
            logger.info(f"Cleaned up {deleted_count} expired sessions")

        # Clean credential cache
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, expiry in self._cache_expiry.items() if expiry < current_time
        ]

        for token in expired_tokens:
            self._credential_cache.pop(token, None)
            self._cache_expiry.pop(token, None)

        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired credential cache entries")
