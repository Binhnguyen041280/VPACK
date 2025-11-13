#!/usr/bin/env python3
"""
Cloud Staging Cleanup Utility
Manages automatic cleanup of cloud staging directory
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path

from modules.path_utils import get_cloud_staging_path
from modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)


class StagingCleanup:
    """Manages cleanup of cloud staging directory"""

    def __init__(self, max_age_days: int = 7):
        """
        Initialize cleanup manager

        Args:
            max_age_days (int): Maximum age of files before cleanup (default 7 days)
        """
        self.max_age_days = max_age_days
        self.staging_dir = get_cloud_staging_path()

    def cleanup_old_files(self, source_name: str = None) -> Dict:
        """
        Remove files older than max_age_days from staging

        Args:
            source_name (str, optional): Specific source to clean, or all if None

        Returns:
            dict: Cleanup results
        """
        try:
            logger.info(f"🧹 Starting staging cleanup (max age: {self.max_age_days} days)")

            if source_name:
                cleanup_paths = [get_cloud_staging_path(source_name)]
            else:
                # Clean all source directories
                cleanup_paths = [
                    os.path.join(self.staging_dir, d)
                    for d in os.listdir(self.staging_dir)
                    if os.path.isdir(os.path.join(self.staging_dir, d))
                ]

            total_deleted = 0
            total_size_freed = 0
            deleted_files = []

            cutoff_time = time.time() - (self.max_age_days * 24 * 60 * 60)

            for path in cleanup_paths:
                if not os.path.exists(path):
                    continue

                # Walk through directory tree
                for root, dirs, files in os.walk(path, topdown=False):
                    for filename in files:
                        file_path = os.path.join(root, filename)

                        try:
                            # Check file age
                            file_mtime = os.path.getmtime(file_path)

                            if file_mtime < cutoff_time:
                                # Check if file is in processed status
                                if self._is_file_processed(file_path):
                                    file_size = os.path.getsize(file_path)
                                    os.remove(file_path)
                                    total_deleted += 1
                                    total_size_freed += file_size
                                    deleted_files.append(file_path)
                                    logger.debug(f"   Deleted: {filename}")

                        except Exception as e:
                            logger.warning(f"   Failed to delete {filename}: {e}")

                    # Remove empty directories
                    for dirname in dirs:
                        dir_path = os.path.join(root, dirname)
                        try:
                            if not os.listdir(dir_path):  # Empty directory
                                os.rmdir(dir_path)
                                logger.debug(f"   Removed empty dir: {dirname}")
                        except Exception as e:
                            logger.warning(f"   Failed to remove dir {dirname}: {e}")

            size_mb = total_size_freed / (1024 * 1024)
            logger.info(
                f"✅ Cleanup completed: {total_deleted} files deleted, {size_mb:.2f} MB freed"
            )

            return {
                "success": True,
                "files_deleted": total_deleted,
                "size_freed_mb": size_mb,
                "deleted_files": deleted_files[:100],  # Return first 100 for logging
            }

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return {"success": False, "message": str(e), "files_deleted": 0, "size_freed_mb": 0}

    def _is_file_processed(self, file_path: str) -> bool:
        """
        Check if file has been processed (safe to delete from staging)

        Args:
            file_path (str): Local file path

        Returns:
            bool: True if processed or doesn't exist in DB
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT is_processed FROM downloaded_files
                    WHERE local_file_path = ?
                """,
                    (file_path,),
                )

                result = cursor.fetchone()

                # If not tracked in DB, safe to delete (orphaned file)
                if not result:
                    return True

                # If tracked, only delete if processed
                return result[0] == 1

        except Exception as e:
            logger.error(f"❌ Error checking file status: {e}")
            # Conservative: don't delete if can't verify
            return False

    def cleanup_processed_files(self, source_name: str = None, min_age_days: int = 7) -> Dict:
        """
        Remove processed files older than min_age_days from staging directory.
        Only removes files marked as is_processed=1 in database.

        Args:
            source_name: Specific source to clean (None = all sources)
            min_age_days: Minimum age in days before cleanup (default: 7)

        Returns:
            Dict with cleanup statistics
        """
        try:
            from datetime import datetime, timedelta

            cleanup_threshold = datetime.now() - timedelta(days=min_age_days)

            # Get processed files ready for cleanup
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT id, local_file_path, original_filename, file_size_bytes
                    FROM downloaded_files
                    WHERE is_processed = 1
                    AND download_timestamp < ?
                """
                params = [cleanup_threshold.isoformat()]

                if source_name:
                    query += " AND local_file_path LIKE ?"
                    params.append(f"%{source_name}%")

                cursor.execute(query, params)
                files_to_cleanup = cursor.fetchall()

            removed_count = 0
            removed_size = 0
            errors = []

            for file_id, file_path, filename, file_size in files_to_cleanup:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        removed_count += 1
                        removed_size += file_size or 0
                        logger.info(f"🗑️ Removed processed file: {filename}")

                    # Remove from database
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM downloaded_files WHERE id = ?", (file_id,))

                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
                    logger.warning(f"⚠️ Failed to remove {filename}: {e}")

            return {
                "success": True,
                "removed_count": removed_count,
                "removed_size_mb": removed_size / (1024 * 1024),
                "errors": errors,
                "message": f"Cleaned up {removed_count} processed files ({removed_size / (1024 * 1024):.1f} MB)",
            }

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return {"success": False, "message": f"Cleanup error: {str(e)}"}

    def cleanup_by_source(self, source_id: int) -> Dict:
        """
        Cleanup staging files for specific source

        Args:
            source_id (int): Source ID

        Returns:
            dict: Cleanup results
        """
        try:
            # Get source name
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM video_sources WHERE id = ?", (source_id,))
                result = cursor.fetchone()

            if not result:
                return {"success": False, "message": f"Source {source_id} not found"}

            source_name = result[0]
            return self.cleanup_old_files(source_name)

        except Exception as e:
            logger.error(f"❌ Cleanup by source failed: {e}")
            return {"success": False, "message": str(e)}

    def get_staging_disk_usage(self) -> Dict:
        """
        Get disk usage statistics for staging directory

        Returns:
            dict: Disk usage info
        """
        try:
            total_size = 0
            file_count = 0
            source_stats = {}

            if not os.path.exists(self.staging_dir):
                return {"total_size_mb": 0, "file_count": 0, "sources": {}}

            for source_dir in os.listdir(self.staging_dir):
                source_path = os.path.join(self.staging_dir, source_dir)

                if not os.path.isdir(source_path):
                    continue

                source_size = 0
                source_files = 0

                for root, dirs, files in os.walk(source_path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        try:
                            file_size = os.path.getsize(file_path)
                            source_size += file_size
                            source_files += 1
                            total_size += file_size
                            file_count += 1
                        except Exception:
                            pass

                source_stats[source_dir] = {
                    "size_mb": source_size / (1024 * 1024),
                    "file_count": source_files,
                }

            return {
                "total_size_mb": total_size / (1024 * 1024),
                "file_count": file_count,
                "sources": source_stats,
                "staging_path": self.staging_dir,
            }

        except Exception as e:
            logger.error(f"❌ Failed to get disk usage: {e}")
            return {"total_size_mb": 0, "file_count": 0, "sources": {}, "error": str(e)}


# Global instance
staging_cleanup = StagingCleanup()


def auto_cleanup_staging():
    """Run automatic cleanup - can be called from scheduler"""
    return staging_cleanup.cleanup_old_files()


def get_staging_usage():
    """Get staging directory usage statistics"""
    return staging_cleanup.get_staging_disk_usage()
