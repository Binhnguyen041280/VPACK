#!/usr/bin/env python3
"""
Sync Endpoints for VTrack - Missing API endpoints for auto-sync functionality
Exposes PyDriveDownloader methods as REST APIs
"""

import logging

from flask import Blueprint, jsonify, request

# Import the PyDrive downloader
from .pydrive_downloader import (
    force_sync_source,
    pydrive_downloader,
    start_source_sync,
    stop_source_sync,
)

logger = logging.getLogger(__name__)

# Create blueprint for sync endpoints
sync_bp = Blueprint("sync", __name__)


@sync_bp.route("/start-auto-sync", methods=["POST"])
def start_auto_sync():
    """Start auto-sync for a cloud source"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        source_id = data.get("source_id")
        if not source_id:
            return jsonify({"success": False, "message": "source_id is required"}), 400

        # Start auto-sync using PyDriveDownloader
        success = start_source_sync(source_id)

        if success:
            # Get initial status
            status = pydrive_downloader.get_sync_status(source_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Auto-sync started for source {source_id}",
                        "source_id": source_id,
                        "sync_status": status,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Failed to start auto-sync for source {source_id}",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"❌ Error starting auto-sync: {e}")
        return jsonify({"success": False, "message": f"Error starting auto-sync: {str(e)}"}), 500


@sync_bp.route("/stop-auto-sync", methods=["POST"])
def stop_auto_sync():
    """Stop auto-sync for a source"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        source_id = data.get("source_id")
        if not source_id:
            return jsonify({"success": False, "message": "source_id is required"}), 400

        # Stop auto-sync using PyDriveDownloader
        success = stop_source_sync(source_id)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Auto-sync stopped for source {source_id}",
                        "source_id": source_id,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Failed to stop auto-sync for source {source_id}",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"❌ Error stopping auto-sync: {e}")
        return jsonify({"success": False, "message": f"Error stopping auto-sync: {str(e)}"}), 500


@sync_bp.route("/sync-status/<int:source_id>", methods=["GET"])
def get_sync_status_api(source_id: int):
    """Get sync status for a source"""
    try:
        # Get sync status from database using pydrive_downloader
        status = pydrive_downloader.get_sync_status(source_id)

        if status:
            # Add runtime information
            is_running = source_id in pydrive_downloader.sync_timers

            response_data = {
                "success": True,
                "source_id": source_id,
                "sync_status": status,
                "runtime": {"is_running": is_running, "timer_active": is_running},
            }

            return jsonify(response_data), 200
        else:
            return (
                jsonify(
                    {"success": False, "message": f"No sync status found for source {source_id}"}
                ),
                404,
            )

    except Exception as e:
        logger.error(f"❌ Error getting sync status: {e}")
        return jsonify({"success": False, "message": f"Error getting sync status: {str(e)}"}), 500


@sync_bp.route("/force-sync/<int:source_id>", methods=["POST"])
def force_sync_api(source_id: int):
    """Force immediate sync for a source"""
    try:
        logger.info(f"🚀 Force sync requested for source {source_id}")

        # Trigger immediate sync using PyDriveDownloader
        result = force_sync_source(source_id)

        if result["success"]:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Sync completed for source {source_id}",
                        "source_id": source_id,
                        "sync_result": result,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Sync failed for source {source_id}",
                        "source_id": source_id,
                        "error": result.get("message", "Unknown error"),
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"❌ Error forcing sync: {e}")
        return jsonify({"success": False, "message": f"Error forcing sync: {str(e)}"}), 500


@sync_bp.route("/sync-dashboard", methods=["GET"])
def get_sync_dashboard():
    """Get comprehensive sync dashboard data"""
    try:
        from modules.db_utils.safe_connection import safe_db_connection

        # Get all cloud sources with sync status
        with safe_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    vs.id as source_id,
                    vs.name as source_name,
                    vs.source_type,
                    vs.path as source_path,
                    ss.sync_enabled,
                    ss.last_sync_timestamp,
                    ss.next_sync_timestamp,
                    ss.sync_interval_minutes,
                    ss.last_sync_status,
                    ss.last_sync_message,
                    ss.files_downloaded_count,
                    ss.total_download_size_mb
                FROM video_sources vs
                LEFT JOIN sync_status ss ON vs.id = ss.source_id
                WHERE vs.active = 1 AND vs.source_type = 'cloud'
                ORDER BY vs.name
            """
            )

            results = cursor.fetchall()

        # Format dashboard data
        dashboard_data = []
        for row in results:
            source_id = row[0]
            is_running = source_id in pydrive_downloader.sync_timers

            source_data = {
                "source_id": source_id,
                "source_name": row[1],
                "source_type": row[2],
                "source_path": row[3],
                "sync_enabled": bool(row[4]) if row[4] is not None else False,
                "last_sync_timestamp": row[5],
                "next_sync_timestamp": row[6],
                "sync_interval_minutes": row[7] or 15,
                "last_sync_status": row[8] or "not_started",
                "last_sync_message": row[9] or "No sync performed yet",
                "files_downloaded_count": row[10] or 0,
                "total_download_size_mb": row[11] or 0.0,
                "runtime": {"is_running": is_running, "timer_active": is_running},
            }
            dashboard_data.append(source_data)

        return (
            jsonify(
                {
                    "success": True,
                    "dashboard": dashboard_data,
                    "total_sources": len(dashboard_data),
                    "active_syncs": len([s for s in dashboard_data if s["runtime"]["is_running"]]),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"❌ Error getting sync dashboard: {e}")
        return (
            jsonify({"success": False, "message": f"Error getting sync dashboard: {str(e)}"}),
            500,
        )


@sync_bp.route("/debug-credentials/<int:source_id>", methods=["GET"])
def debug_credentials(source_id: int):
    """Debug credentials loading step by step"""
    try:
        import hashlib
        import json
        import os

        from modules.db_utils.safe_connection import safe_db_connection

        debug_info = {}

        # Step 1: Get source config
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT config FROM video_sources 
                WHERE id = ? AND source_type = 'cloud' AND active = 1
            """,
                (source_id,),
            )
            result = cursor.fetchone()

        if not result or not result[0]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"No source config found for source {source_id}",
                        "debug_info": debug_info,
                    }
                ),
                404,
            )

        debug_info["step1_config"] = "Found source config"

        # Step 2: Parse config
        config_data = json.loads(result[0])
        user_email = config_data.get("user_email")
        debug_info["step2_user_email"] = user_email

        if not user_email:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No user_email in source config",
                        "debug_info": debug_info,
                    }
                ),
                400,
            )

        # Step 3: Calculate file path
        tokens_dir = os.path.join(os.path.dirname(__file__), "tokens")
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        token_filename = f"google_drive_{email_hash}.json"
        token_filepath = os.path.join(tokens_dir, token_filename)

        debug_info["step3_filepath"] = token_filepath
        debug_info["step3_file_exists"] = os.path.exists(token_filepath)

        if not os.path.exists(token_filepath):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Credentials file not found: {token_filepath}",
                        "debug_info": debug_info,
                    }
                ),
                404,
            )

        # Step 4: Load encrypted storage
        with open(token_filepath, "r") as f:
            encrypted_storage = json.load(f)

        debug_info["step4_storage_keys"] = list(encrypted_storage.keys())
        debug_info["step4_has_encrypted_data"] = "encrypted_data" in encrypted_storage

        # Step 5: Test decryption
        try:
            from modules.sources.cloud_endpoints import decrypt_credentials

            credential_data = decrypt_credentials(encrypted_storage["encrypted_data"])
            debug_info["step5_decrypt_success"] = credential_data is not None
            if credential_data:
                debug_info["step5_credential_keys"] = list(credential_data.keys())
            else:
                debug_info["step5_decrypt_error"] = "Decryption returned None"
        except Exception as e:
            debug_info["step5_decrypt_error"] = str(e)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Decryption failed: {str(e)}",
                        "debug_info": debug_info,
                    }
                ),
                500,
            )

        # Step 6: Test credentials object creation - FIXED: Use oauth2client for PyDrive2 compatibility
        try:
            from datetime import datetime, timezone

            from oauth2client.client import OAuth2Credentials

            # Convert expires_at to datetime if it exists
            token_expiry = None
            if credential_data and credential_data.get("expires_at"):
                try:
                    # Handle both timestamp and datetime formats
                    expires_at = credential_data.get("expires_at")
                    if isinstance(expires_at, (int, float)):
                        token_expiry = datetime.fromtimestamp(expires_at, tz=timezone.utc)
                    elif isinstance(expires_at, str):
                        token_expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                except Exception as exp_e:
                    debug_info["step6_expiry_parse_warning"] = (
                        f"Could not parse expires_at: {exp_e}"
                    )

            credentials = (
                OAuth2Credentials(
                    access_token=credential_data.get("token"),
                    client_id=credential_data.get("client_id"),
                    client_secret=credential_data.get("client_secret"),
                    refresh_token=credential_data.get("refresh_token"),
                    token_expiry=token_expiry,
                    token_uri=credential_data.get(
                        "token_uri", "https://oauth2.googleapis.com/token"
                    ),
                    user_agent="VTrack-PyDrive2-Client/1.0",
                )
                if credential_data
                else None
            )

            debug_info["step6_credentials_created"] = credentials is not None
            if credentials:
                debug_info["step6_credentials_expired"] = credentials.access_token_expired
                debug_info["step6_has_refresh_token"] = credentials.refresh_token is not None
            else:
                debug_info["step6_credentials_error"] = "Credentials object is None"
        except Exception as e:
            debug_info["step6_credentials_error"] = str(e)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"OAuth2Client credentials creation failed: {str(e)}",
                        "debug_info": debug_info,
                    }
                ),
                500,
            )

        # Step 7: Test PyDrive auth
        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive

            # Configure GoogleAuth with proper settings (same as pydrive_core.py)
            gauth = GoogleAuth()
            gauth.settings = {
                "client_config_backend": "service",
                "client_config": {
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uri": "http://localhost:8080/api/cloud/oauth/callback",
                },
                "save_credentials": False,
                "save_credentials_backend": "file",
                "save_credentials_file": None,
                "get_refresh_token": True,
                "oauth_scope": [
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/drive.metadata.readonly",
                ],
            }
            gauth.credentials = credentials
            drive = GoogleDrive(gauth)

            # Test connection
            about = drive.GetAbout()
            debug_info["step7_pydrive_success"] = True
            debug_info["step7_user_info"] = {
                "name": about.get("name", "Unknown"),
                "email": about.get("user", {}).get("emailAddress", "Unknown"),
            }

        except Exception as e:
            debug_info["step7_pydrive_error"] = str(e)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"PyDrive authentication failed: {str(e)}",
                        "debug_info": debug_info,
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "All authentication steps successful",
                    "debug_info": debug_info,
                }
            ),
            200,
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "error": f"Debug failed: {str(e)}", "debug_info": debug_info}
            ),
            500,
        )


@sync_bp.route("/auto-start-cloud-sync", methods=["POST"])
def auto_start_cloud_sync():
    """Auto-start sync for all active cloud sources (called when backend starts)"""
    try:
        from modules.db_utils.safe_connection import safe_db_connection

        # Get all active cloud sources
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name FROM video_sources 
                WHERE active = 1 AND source_type = 'cloud'
            """
            )
            sources = cursor.fetchall()

        started_sources = []
        failed_sources = []

        for source_id, source_name in sources:
            try:
                success = start_source_sync(source_id)
                if success:
                    started_sources.append({"id": source_id, "name": source_name})
                    logger.info(f"✅ Auto-started sync for {source_name} (ID: {source_id})")
                else:
                    failed_sources.append({"id": source_id, "name": source_name})
                    logger.warning(
                        f"⚠️ Failed to auto-start sync for {source_name} (ID: {source_id})"
                    )
            except Exception as e:
                failed_sources.append({"id": source_id, "name": source_name, "error": str(e)})
                logger.error(f"❌ Error auto-starting sync for {source_name}: {e}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Auto-start completed: {len(started_sources)} started, {len(failed_sources)} failed",
                    "started_sources": started_sources,
                    "failed_sources": failed_sources,
                    "total_sources": len(sources),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"❌ Error in auto-start: {e}")
        return jsonify({"success": False, "message": f"Auto-start failed: {str(e)}"}), 500


# Health check endpoint
@sync_bp.route("/sync-health", methods=["GET"])
def sync_health_check():
    """Health check for sync service"""
    try:
        active_timers = len(pydrive_downloader.sync_timers)
        active_locks = len(pydrive_downloader.sync_locks)
        cached_clients = len(pydrive_downloader.core.drive_clients)

        return (
            jsonify(
                {
                    "success": True,
                    "health": "healthy",
                    "service": "PyDriveDownloader",
                    "stats": {
                        "active_sync_timers": active_timers,
                        "active_sync_locks": active_locks,
                        "cached_drive_clients": cached_clients,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return jsonify({"success": False, "health": "unhealthy", "error": str(e)}), 500
