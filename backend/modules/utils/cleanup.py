"""Universal cleanup service for V_Track application

Manages automatic cleanup of temporary files across multiple directories:
- System logs (var/logs/application/)
- Cloud cache (var/cache/cloud_downloads/)
- Old logs (resources/output_clips/LOG/)
- Output files (user-configurable retention)
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List

from modules.db_utils.safe_connection import safe_db_connection
from modules.path_utils import get_paths

logger = logging.getLogger(__name__)

# Get centralized paths at module level
paths = get_paths()


class CleanupService:
    """Centralized cleanup service for V_Track files"""

    def cleanup_system_files(self) -> Dict:
        """
        Cleanup system temporary files (called every 1 hour).

        Targets:
        - var/logs/application/ (keep 1 day + *_latest.log)
        - var/cache/cloud_downloads/ (keep 1 day)
        - resources/output_clips/LOG/ (delete all)

        Returns:
            dict: Cleanup statistics
        """
        results = {
            "application_logs": self._cleanup_application_logs(),
            "cloud_cache": self._cleanup_cloud_cache(),
            "old_output_logs": self._cleanup_old_output_logs(),
        }

        # Calculate totals
        total_deleted = sum(r.get("deleted", 0) for r in results.values())
        total_freed_mb = sum(r.get("freed_mb", 0) for r in results.values())

        logger.info(
            f"✅ System cleanup: {total_deleted} files deleted, {total_freed_mb:.2f} MB freed"
        )

        return {
            "success": True,
            "total_deleted": total_deleted,
            "total_freed_mb": total_freed_mb,
            "details": results,
        }

    def _cleanup_application_logs(self) -> Dict:
        """Clean var/logs/application/ - keep 1 day + *_latest.log"""
        logs_dir = Path(paths["LOGS_DIR"])

        return self._clean_directory(
            path=logs_dir,
            patterns=["*.log", "*.log.*"],
            exclude_patterns=["*_latest.log"],
            max_age_days=1,
            name="var/logs/application",
        )

    def _cleanup_cloud_cache(self) -> Dict:
        """Clean var/cache/cloud_downloads/ - keep 1 day"""
        cache_dir = Path(paths["CLOUD_STAGING_DIR"])

        return self._clean_directory(
            path=cache_dir,
            patterns=["*"],
            exclude_patterns=[],
            max_age_days=1,
            name="var/cache/cloud_downloads",
            recursive=True,
        )

    def _cleanup_old_output_logs(self) -> Dict:
        """Clean resources/output_clips/LOG/ - delete ALL old logs"""
        old_logs = Path(paths["BASE_DIR"]) / "resources" / "output_clips" / "LOG"

        return self._clean_directory(
            path=old_logs,
            patterns=["*.log", "*.log.*"],
            exclude_patterns=[],
            max_age_days=0,  # Delete all
            name="resources/output_clips/LOG",
        )

    def cleanup_output_files(self) -> Dict:
        """
        Cleanup output files based on storage_duration config (called every 24 hours).

        Reads storage_duration from processing_config in database.
        Excludes system folders: CameraROI/, LOG/

        Returns:
            dict: Cleanup statistics
        """
        try:
            # Get configuration from database
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT output_path, storage_duration
                    FROM processing_config
                    WHERE id = 1
                """
                )
                result = cursor.fetchone()

            if not result:
                return {"deleted": 0, "freed_mb": 0, "error": "No processing config found"}

            output_path, storage_duration = result
            output_dir = Path(output_path)

            if not output_dir.exists():
                logger.warning(f"Output path does not exist: {output_path}")
                return {
                    "deleted": 0,
                    "freed_mb": 0,
                    "error": f"Output path not found: {output_path}",
                }

            # Cleanup with configured retention
            days_to_keep = storage_duration if storage_duration else 30
            result = self._clean_directory(
                path=output_dir,
                patterns=["*"],
                exclude_patterns=["CameraROI/*", "LOG/*"],
                max_age_days=days_to_keep,
                name=f"output_files (retention: {days_to_keep}d)",
                recursive=True,
            )

            logger.info(
                f"✅ Output cleanup: {result['deleted']} files deleted, {result['freed_mb']:.2f} MB freed"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Output cleanup failed: {e}")
            return {"deleted": 0, "freed_mb": 0, "error": str(e)}

    def _clean_directory(
        self,
        path: Path,
        patterns: List[str],
        exclude_patterns: List[str],
        max_age_days: int,
        name: str,
        recursive: bool = False,
    ) -> Dict:
        """
        Generic directory cleanup function.

        Args:
            path: Directory to clean
            patterns: File patterns to match (e.g., ["*.log", "*.mov"])
            exclude_patterns: Patterns to exclude from deletion
            max_age_days: Delete files older than N days (0 = delete all)
            name: Name for logging
            recursive: Walk subdirectories

        Returns:
            dict: {'deleted': count, 'freed_mb': size}
        """
        if not path.exists():
            logger.debug(f"Path does not exist: {path}")
            return {"deleted": 0, "freed_mb": 0}

        # Calculate cutoff time
        cutoff_time = time.time() - (max_age_days * 86400)
        deleted_count = 0
        freed_bytes = 0

        try:
            # Collect all matching files
            files = []
            for pattern in patterns:
                if recursive:
                    files.extend(path.rglob(pattern))
                else:
                    files.extend(path.glob(pattern))

            # Process files
            for file_path in files:
                # Skip if not a file (e.g., directories)
                if not file_path.is_file():
                    continue

                # Check exclude patterns
                if any(file_path.match(ex) for ex in exclude_patterns):
                    continue

                # Check age
                file_mtime = file_path.stat().st_mtime
                if file_mtime < cutoff_time:
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        freed_bytes += file_size
                        logger.debug(f"Deleted: {file_path.relative_to(path.parent)}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path.name}: {e}")

            freed_mb = freed_bytes / (1024 * 1024)
            if deleted_count > 0:
                logger.info(f"✅ Cleaned {name}: {deleted_count} files, {freed_mb:.2f} MB freed")

            return {"deleted": deleted_count, "freed_mb": freed_mb}

        except Exception as e:
            logger.error(f"❌ Cleanup {name} failed: {e}")
            return {"deleted": 0, "freed_mb": 0}


# Global instance
cleanup_service = CleanupService()
