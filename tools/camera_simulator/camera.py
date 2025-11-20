"""
Camera Simulator - Simulates a single camera recording behavior
"""
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

from video_generator import VideoGenerator
from patterns import create_pattern, RecordingEvent

logger = logging.getLogger(__name__)


class CameraSimulator:
    """Simulates a single camera's recording behavior"""

    def __init__(
        self,
        name: str,
        source_video: str,
        output_folder: str,
        pattern_type: str,
        config: Dict,
        video_generator: VideoGenerator
    ):
        """
        Initialize camera simulator

        Args:
            name: Camera name (e.g., "PackingLine1")
            source_video: Path to source video file
            output_folder: Output folder for generated videos
            pattern_type: Recording pattern type
            config: Pattern configuration
            video_generator: Shared VideoGenerator instance
        """
        self.name = name
        self.source_video = source_video
        self.output_folder = output_folder
        self.pattern_type = pattern_type
        self.config = config
        self.video_generator = video_generator

        # State
        self.is_running = False
        self.is_paused = False
        self.thread: Optional[threading.Thread] = None
        self.events: List[RecordingEvent] = []
        self.current_event_index = 0
        self.stats = {
            'videos_created': 0,
            'total_duration_minutes': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }

        # Create output folder
        os.makedirs(output_folder, exist_ok=True)

        # Validate source video
        if not os.path.exists(source_video):
            raise FileNotFoundError(f"Source video not found: {source_video}")

        # Get source video duration for offset calculation
        self.source_duration = video_generator.get_video_duration(source_video)
        logger.info(
            f"Camera '{name}' initialized: "
            f"source={source_video} ({self.source_duration:.1f}s), "
            f"output={output_folder}, "
            f"pattern={pattern_type}"
        )

    def generate_schedule(self, start_time: datetime, duration_hours: float):
        """Generate recording schedule based on pattern"""
        logger.info(
            f"[{self.name}] Generating schedule: "
            f"start={start_time}, duration={duration_hours}h"
        )

        # Create pattern and generate events
        pattern = create_pattern(self.pattern_type, self.config)
        self.events = pattern.generate_events(start_time, duration_hours)

        # Log schedule summary
        recording_events = [e for e in self.events if e.is_recording]
        total_recording_minutes = sum(e.duration_minutes for e in recording_events)

        logger.info(
            f"[{self.name}] Schedule generated: "
            f"{len(self.events)} events, "
            f"{len(recording_events)} recordings, "
            f"{total_recording_minutes:.1f} minutes of video"
        )

    def start(self, start_time: Optional[datetime] = None):
        """Start camera simulation"""
        if self.is_running:
            logger.warning(f"[{self.name}] Already running")
            return

        if not self.events:
            logger.error(f"[{self.name}] No events generated. Call generate_schedule() first")
            return

        self.is_running = True
        self.is_paused = False
        self.current_event_index = 0
        self.stats['start_time'] = datetime.now()

        # Start simulation thread
        self.thread = threading.Thread(
            target=self._simulation_loop,
            args=(start_time,),
            daemon=True
        )
        self.thread.start()
        logger.info(f"[{self.name}] Started")

    def stop(self):
        """Stop camera simulation"""
        if not self.is_running:
            return

        self.is_running = False
        self.is_paused = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        self.stats['end_time'] = datetime.now()
        logger.info(f"[{self.name}] Stopped")

    def pause(self):
        """Pause camera simulation"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info(f"[{self.name}] Paused")

    def resume(self):
        """Resume camera simulation"""
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info(f"[{self.name}] Resumed")

    def _simulation_loop(self, start_time: Optional[datetime] = None):
        """Main simulation loop"""
        logger.info(f"[{self.name}] Simulation loop started")

        simulation_start = start_time or datetime.now()

        for i, event in enumerate(self.events):
            if not self.is_running:
                break

            # Wait while paused
            while self.is_paused and self.is_running:
                time.sleep(1)

            if not self.is_running:
                break

            self.current_event_index = i

            # Calculate when this event should happen
            event_time = event.start_time
            now = datetime.now()

            # Calculate simulated time vs real time
            # In real-time mode: wait until event_time
            # In fast mode: process immediately
            use_real_time = self.config.get('use_real_time', False)

            if use_real_time:
                # Real-time mode: wait until event time
                time_to_wait = (event_time - now).total_seconds()
                if time_to_wait > 0:
                    logger.debug(f"[{self.name}] Waiting {time_to_wait:.1f}s until {event_time}")
                    # Wait in small increments to allow pause/stop
                    wait_end = now + timedelta(seconds=time_to_wait)
                    while datetime.now() < wait_end and self.is_running:
                        time.sleep(min(1, (wait_end - datetime.now()).total_seconds()))
                        while self.is_paused and self.is_running:
                            time.sleep(1)

            if not self.is_running:
                break

            # Process event
            if event.is_recording:
                self._create_video(event)
            else:
                # Idle/offline period
                logger.debug(
                    f"[{self.name}] Idle period: "
                    f"{event.duration_minutes:.1f}m at {event.start_time}"
                )

            # Small delay between events if not in real-time mode
            if not use_real_time:
                time.sleep(0.1)

        logger.info(
            f"[{self.name}] Simulation loop completed. "
            f"Created {self.stats['videos_created']} videos"
        )

    def _create_video(self, event: RecordingEvent):
        """Create a video file for the recording event"""
        try:
            # Generate output filename with timestamp
            timestamp_str = event.start_time.strftime('%Y%m%d_%H%M%S')
            output_filename = f"{self.name}_{timestamp_str}.mp4"
            output_path = os.path.join(self.output_folder, output_filename)

            logger.info(
                f"[{self.name}] Creating video: "
                f"{output_filename} ({event.duration_minutes:.1f}m)"
            )

            # Calculate start offset in source video (for variety)
            # We'll cycle through the source video to create different clips
            offset_minutes = (self.stats['videos_created'] * event.duration_minutes) % (self.source_duration / 60)
            start_offset = offset_minutes * 60  # Convert to seconds

            # Create video clip
            success = self.video_generator.create_video_clip(
                source_video=self.source_video,
                output_path=output_path,
                duration_minutes=event.duration_minutes,
                timestamp=event.start_time,
                start_offset=start_offset
            )

            if success:
                self.stats['videos_created'] += 1
                self.stats['total_duration_minutes'] += event.duration_minutes
                logger.info(
                    f"[{self.name}] ✓ Created: {output_filename} "
                    f"(total: {self.stats['videos_created']} videos)"
                )
            else:
                self.stats['errors'] += 1
                logger.error(f"[{self.name}] ✗ Failed to create: {output_filename}")

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"[{self.name}] Error creating video: {e}", exc_info=True)

    def get_stats(self) -> Dict:
        """Get camera statistics"""
        stats = self.stats.copy()
        stats['name'] = self.name
        stats['is_running'] = self.is_running
        stats['is_paused'] = self.is_paused
        stats['progress'] = (
            f"{self.current_event_index + 1}/{len(self.events)}"
            if self.events else "0/0"
        )
        return stats

    def get_status(self) -> str:
        """Get current status string"""
        if not self.is_running:
            return "Stopped"
        if self.is_paused:
            return "Paused"
        if self.current_event_index < len(self.events):
            event = self.events[self.current_event_index]
            status = "Recording" if event.is_recording else "Idle"
            return f"{status} ({self.current_event_index + 1}/{len(self.events)})"
        return "Completed"
