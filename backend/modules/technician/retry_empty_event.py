"""Empty Event Retry Module for V_Track Video Processing System.

This module handles recovery of tracking codes from events that were marked as empty
(no MVD detected) during initial processing. It runs in PASS 3 when the system is idle,
processing events with full frame sampling (1fps) to attempt recovery.

Processing Strategy:
    1. Wait for system idle signal (file_list all processed)
    2. Query events marked with retry_needed=1
    3. For each empty event:
       - Open video file and seek to event start time (ts)
       - Scan frames from ts to te at full sampling (1fps = every frame)
       - Detect MVD (no TimeGo check needed for retry)
       - Stop immediately when MVD found
       - Update database with result
    4. Clear idle signal when retry completes

Threading:
    - Runs as daemon thread (exits when main program exits)
    - Uses db_rwlock for thread-safe database access
    - Coordinates with idle monitor via system_idle_event
    - Signals completion by clearing system_idle_event
"""

import cv2
import os
import logging
import sqlite3
import threading
import json
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock, system_idle_event, retry_in_progress_flag
from modules.technician.frame_sampler_trigger import FrameSamplerTrigger
from modules.config.logging_config import get_logger


class RetryEmptyEventProcessor:
    """Process empty events with full sampling to recover missed tracking codes.

    This processor inherits from FrameSamplerTrigger to reuse MVD detection logic
    and camera configuration management. It operates independently during idle periods.

    Attributes:
        logger: Logger instance for this module
        sampler: FrameSamplerTrigger instance for MVD detection
        fps: Video frames per second (from processing_config)

    Methods:
        run(): Main processing loop
        query_empty_events(): Fetch events marked for retry
        process_single_event(): Process one empty event with seeking
        detect_mvd_frame(): Detect MVD in a single frame
        update_event_success(): Mark event as recovered
        update_event_failed(): Mark event as unrecoverable
    """

    def __init__(self):
        """Initialize retry processor with frame sampler for MVD detection."""
        self.logger = get_logger(__name__, {"module": "retry_empty_event"})
        self.logger.info("🔄 RetryEmptyEventProcessor initialized")

        # Reuse FrameSamplerTrigger for MVD detection
        self.sampler = FrameSamplerTrigger()
        self.fps = self.sampler.fps  # Get FPS from sampler config

    def run(self):
        """Main loop: wait idle → query empty → process each → complete.

        Workflow:
            1. system_idle_event.wait() - Block until system idle
            2. Query events WHERE retry_needed=1
            3. For each event: process_single_event()
            4. Log results
            5. Clear system_idle_event to signal completion
            6. Repeat
        """
        self.logger.info("✅ Retry processor started - waiting for idle signal")

        while True:
            try:
                # Wait for system to be idle (no files being processed)
                system_idle_event.wait()
                self.logger.info("⏰ System idle detected - starting PASS 3 retry")

                # Query events marked for retry
                retry_events = self.query_empty_events()

                if not retry_events:
                    self.logger.info("📋 No events marked for retry")
                    system_idle_event.clear()
                    continue

                self.logger.info(f"🔍 Found {len(retry_events)} events to retry")

                # Process each empty event
                recovered = 0
                failed = 0

                for event_id, video_file, ts, te, camera_name in retry_events:
                    try:
                        success = self.process_single_event(
                            event_id, video_file, ts, te, camera_name
                        )
                        if success:
                            recovered += 1
                        else:
                            failed += 1
                    except Exception as e:
                        self.logger.error(f"❌ Exception processing event {event_id}: {e}")
                        failed += 1

                # Log results
                self.logger.info(f"✅ PASS 3 COMPLETE: {recovered}/{len(retry_events)} recovered, {failed} failed")

                # Signal completion and clear idle flag
                system_idle_event.clear()

            except Exception as e:
                self.logger.error(f"❌ Error in retry processor loop: {e}")
                system_idle_event.clear()

    def query_empty_events(self):
        """Query events marked for retry from database.

        Queries: events WHERE retry_needed=1 AND retry_count < 1 AND te IS NOT NULL
        Ordering: By event_id to process consistently

        Returns:
            List of tuples: (event_id, video_file, ts, te, camera_name)
        """
        try:
            with db_rwlock.gen_rlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT event_id, video_file, ts, te, camera_name
                        FROM events
                        WHERE retry_needed = 1 AND retry_count < 1
                        AND te IS NOT NULL
                        ORDER BY event_id ASC
                    """)
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"❌ Error querying empty events: {e}")
            return []

    def process_single_event(self, event_id, video_file, ts, te, camera_name):
        """Process one empty event: SEEK → SCAN → DETECT → STOP.

        Strategy:
            1. Open video file
            2. SEEK: Jump to event start frame (ts * fps)
            3. SCAN: Read frames from ts to te (every frame = 1fps)
            4. DETECT: Try to detect MVD in each frame (no TimeGo check)
            5. STOP: Return immediately when MVD found
            6. UPDATE: Database with result

        Args:
            event_id: Event ID from database
            video_file: Path to video file
            ts: Event start time in seconds
            te: Event end time in seconds
            camera_name: Camera name for packing_area lookup

        Returns:
            bool: True if MVD found and recovered, False if not found
        """
        try:
            # Open video file
            video = cv2.VideoCapture(video_file)
            if not video.isOpened():
                self.logger.error(f"❌ Event {event_id}: Cannot open video {video_file}")
                self.update_event_failed(event_id)
                return False

            # SEEK: Jump directly to event start
            start_frame = int(ts * self.fps)
            end_frame = int(te * self.fps)
            video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            self.logger.info(f"🔄 Event {event_id}: seeking to frame {start_frame} ({ts}s) - end {end_frame} ({te}s)")

            # Get packing area for this camera
            packing_area, _ = self.sampler.get_packing_area(camera_name)
            if not packing_area:
                self.logger.error(f"❌ Event {event_id}: No packing_area found for camera {camera_name}")
                video.release()
                self.update_event_failed(event_id)
                return False

            x, y, w, h = packing_area
            frame_count = start_frame
            found = False

            # SCAN: ts → te (every frame)
            while frame_count <= end_frame:
                ret, frame = video.read()
                if not ret:
                    self.logger.debug(f"Event {event_id}: Reached end of video at frame {frame_count}")
                    break

                frame_count += 1

                # Extract packing area from frame
                frame_packing = frame[y:y+h, x:x+w]

                # DETECT: MVD only (no TimeGo check, no trigger area)
                mvd = self.detect_mvd_frame(frame_packing, camera_name)

                # STOP: immediately when found
                if mvd:
                    self.logger.info(f"✅ Event {event_id}: recovered MVD={mvd} at frame {frame_count}")
                    self.update_event_success(event_id, mvd)
                    found = True
                    break

            video.release()

            # If not found, mark as failed
            if not found:
                self.logger.info(f"❌ Event {event_id}: MVD not found in {end_frame - start_frame} frames")
                self.update_event_failed(event_id)

            return found

        except Exception as e:
            self.logger.error(f"❌ Event {event_id}: Exception: {e}")
            if 'video' in locals():
                video.release()
            self.update_event_failed(event_id)
            return False

    def detect_mvd_frame(self, frame_packing, camera_name):
        """Detect MVD in a single frame (packing area).

        Uses FrameSamplerTrigger.process_frame() but only for MVD detection.
        For retry, we don't need TimeGo trigger detection.

        Args:
            frame_packing: Frame cropped to packing_area
            camera_name: Camera name (for potential future use)

        Returns:
            str: MVD tracking code if found, empty string otherwise
        """
        try:
            # Use sampler's process_frame but only extract MVD
            # Set frame_trigger=None since we only care about packing area
            state, mvd, mvd_bbox, _ = self.sampler.process_frame(
                frame_packing=frame_packing,
                frame_trigger=None,
                frame_count=0,
                packing_area_offset=None
            )

            return mvd  # Empty string if not found, tracking code if found

        except Exception as e:
            self.logger.debug(f"Error detecting MVD: {e}")
            return ""

    def update_event_success(self, event_id, mvd):
        """Update event in database when MVD is found.

        Updates: tracking_codes, retry_needed=0, status='completed_retry', retry_count++

        Args:
            event_id: Event ID to update
            mvd: Tracking code that was recovered
        """
        try:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()

                    # Convert mvd to list format (same as frame_sampler)
                    tracking_codes_list = [mvd]
                    tracking_codes_json = json.dumps(tracking_codes_list)

                    cursor.execute("""
                        UPDATE events
                        SET tracking_codes = ?,
                            retry_needed = 0,
                            status = 'completed_retry',
                            retry_count = retry_count + 1
                        WHERE event_id = ?
                    """, (tracking_codes_json, event_id))
                    conn.commit()

                    self.logger.debug(f"Event {event_id}: updated as success")
        except Exception as e:
            self.logger.error(f"❌ Error updating event {event_id} success: {e}")

    def update_event_failed(self, event_id):
        """Update event in database when MVD is not found.

        Updates: retry_needed=0, status='retry_failed', retry_count++

        Args:
            event_id: Event ID to update
        """
        try:
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE events
                        SET retry_needed = 0,
                            status = 'retry_failed',
                            retry_count = retry_count + 1
                        WHERE event_id = ?
                    """, (event_id,))
                    conn.commit()

                    self.logger.debug(f"Event {event_id}: updated as failed")
        except Exception as e:
            self.logger.error(f"❌ Error updating event {event_id} failed: {e}")


def start_retry_processor():
    """Start retry processor as a daemon thread.

    This function is called from program_runner to initialize the retry system.
    The thread runs continuously, waiting for idle signals and processing events.

    Returns:
        threading.Thread: The started retry processor thread

    Example:
        from modules.technician.retry_empty_event import start_retry_processor
        retry_thread = start_retry_processor()
        logger.info("Retry processor started")
    """
    processor = RetryEmptyEventProcessor()
    thread = threading.Thread(
        target=processor.run,
        name="RetryEmptyEvent",
        daemon=True  # Exit when main program exits
    )
    thread.start()
    return thread
