"""
Video Generator - FFmpeg wrapper for creating simulated camera videos
"""
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VideoGenerator:
    """Generates video files with realistic metadata for camera simulation"""

    def __init__(self):
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("FFmpeg is available")
            else:
                raise RuntimeError("FFmpeg not working properly")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"FFmpeg not found or not working: {e}")

    def get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                logger.error(f"Failed to get duration: {result.stderr}")
                return 0.0
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
            return 0.0

    def create_video_clip(
        self,
        source_video: str,
        output_path: str,
        duration_minutes: float,
        timestamp: datetime,
        start_offset: float = 0.0
    ) -> bool:
        """
        Create a video clip from source video with updated metadata

        Args:
            source_video: Path to source video file
            output_path: Path for output video file
            duration_minutes: Duration of output clip in minutes
            timestamp: Timestamp for video creation time
            start_offset: Start time in source video (seconds)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Get source video duration
            source_duration = self.get_video_duration(source_video)
            if source_duration == 0:
                logger.error(f"Invalid source video: {source_video}")
                return False

            duration_seconds = duration_minutes * 60

            # If requested duration is longer than source, we'll loop the source
            # If start_offset + duration > source_duration, wrap around
            if start_offset >= source_duration:
                start_offset = start_offset % source_duration

            # Format timestamp for metadata
            creation_time = timestamp.strftime('%Y-%m-%dT%H:%M:%S')

            # Build FFmpeg command
            if duration_seconds <= source_duration - start_offset:
                # Simple case: can extract from source directly
                cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output file
                    '-ss', str(start_offset),  # Start offset
                    '-t', str(duration_seconds),  # Duration
                    '-i', source_video,
                    '-c', 'copy',  # Copy codec (fast, no re-encoding)
                    '-metadata', f'creation_time={creation_time}',
                    '-avoid_negative_ts', 'make_zero',
                    output_path
                ]
            else:
                # Complex case: need to loop source video
                # For now, we'll just take what we can from source
                # TODO: Implement looping if needed
                available_duration = source_duration - start_offset
                logger.warning(
                    f"Requested duration {duration_minutes}m exceeds available "
                    f"{available_duration/60:.1f}m from source. Using available duration."
                )
                cmd = [
                    'ffmpeg',
                    '-y',
                    '-ss', str(start_offset),
                    '-i', source_video,
                    '-c', 'copy',
                    '-metadata', f'creation_time={creation_time}',
                    '-avoid_negative_ts', 'make_zero',
                    output_path
                ]

            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False

            # Set file system timestamps
            timestamp_unix = timestamp.timestamp()
            os.utime(output_path, (timestamp_unix, timestamp_unix))

            logger.info(
                f"Created video: {output_path} "
                f"({duration_minutes}m, timestamp: {creation_time})"
            )
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout while creating {output_path}")
            return False
        except Exception as e:
            logger.error(f"Error creating video clip: {e}")
            return False

    def copy_video_with_metadata(
        self,
        source_video: str,
        output_path: str,
        timestamp: datetime
    ) -> bool:
        """
        Copy entire source video with updated metadata

        Args:
            source_video: Path to source video file
            output_path: Path for output video file
            timestamp: Timestamp for video creation time

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Format timestamp for metadata
            creation_time = timestamp.strftime('%Y-%m-%dT%H:%M:%S')

            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-i', source_video,
                '-c', 'copy',  # Copy codec (fast, no re-encoding)
                '-metadata', f'creation_time={creation_time}',
                output_path
            ]

            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False

            # Set file system timestamps
            timestamp_unix = timestamp.timestamp()
            os.utime(output_path, (timestamp_unix, timestamp_unix))

            logger.info(f"Copied video with updated metadata: {output_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout while copying {output_path}")
            return False
        except Exception as e:
            logger.error(f"Error copying video: {e}")
            return False
