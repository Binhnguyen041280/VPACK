"""
Recording Patterns - Define different camera recording behaviors
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of recording patterns"""
    CONTINUOUS = "continuous"
    MOTION_TRIGGERED = "motion_triggered"
    EVENT_TRIGGERED = "event_triggered"
    RANDOM_ON_OFF = "random_on_off"


class ScheduleType(Enum):
    """Types of scheduling"""
    ALWAYS = "24x7"
    WORKING_HOURS = "working_hours"  # 8:00-18:00
    CUSTOM = "custom"


@dataclass
class RecordingEvent:
    """Represents a single recording event"""
    start_time: datetime
    duration_minutes: float
    is_recording: bool  # True = record video, False = idle/offline


class RecordingPattern:
    """Base class for recording patterns"""

    def __init__(self, config: Dict):
        self.config = config
        self.schedule_type = ScheduleType(config.get('schedule', 'working_hours'))

        # Working hours configuration
        self.working_hours_start = config.get('working_hours_start', 8)  # 8:00
        self.working_hours_end = config.get('working_hours_end', 18)  # 18:00
        self.working_days = config.get('working_days', [0, 1, 2, 3, 4])  # Mon-Fri

        # Custom schedule (if provided)
        self.custom_hours = config.get('custom_hours', [])

    def is_in_schedule(self, timestamp: datetime) -> bool:
        """Check if timestamp is within scheduled recording time"""
        if self.schedule_type == ScheduleType.ALWAYS:
            return True

        elif self.schedule_type == ScheduleType.WORKING_HOURS:
            # Check day of week (0=Monday, 6=Sunday)
            if timestamp.weekday() not in self.working_days:
                return False
            # Check hour
            hour = timestamp.hour
            return self.working_hours_start <= hour < self.working_hours_end

        elif self.schedule_type == ScheduleType.CUSTOM:
            # Custom hours format: [(start_hour, end_hour), ...]
            hour = timestamp.hour
            for start, end in self.custom_hours:
                if start <= hour < end:
                    return True
            return False

        return True

    def generate_events(
        self,
        start_time: datetime,
        duration_hours: float
    ) -> List[RecordingEvent]:
        """Generate recording events for the specified time period"""
        raise NotImplementedError("Subclasses must implement generate_events()")


class ContinuousPattern(RecordingPattern):
    """Continuous recording pattern - records video at regular intervals"""

    def generate_events(
        self,
        start_time: datetime,
        duration_hours: float
    ) -> List[RecordingEvent]:
        """Generate continuous recording events"""
        events = []
        current_time = start_time
        end_time = start_time + timedelta(hours=duration_hours)

        # Get video duration range
        video_duration_range = self.config.get('video_duration_range', [15, 15])
        min_duration, max_duration = video_duration_range

        logger.info(
            f"Generating CONTINUOUS pattern: {min_duration}-{max_duration}m videos"
        )

        while current_time < end_time:
            # Check if in schedule
            if self.is_in_schedule(current_time):
                # Randomize duration if range provided
                if min_duration == max_duration:
                    duration = min_duration
                else:
                    duration = random.uniform(min_duration, max_duration)

                events.append(RecordingEvent(
                    start_time=current_time,
                    duration_minutes=duration,
                    is_recording=True
                ))

                current_time += timedelta(minutes=duration)
            else:
                # Outside schedule, skip to next scheduled time
                current_time = self._skip_to_next_schedule(current_time)

        logger.info(f"Generated {len(events)} continuous recording events")
        return events

    def _skip_to_next_schedule(self, current_time: datetime) -> datetime:
        """Skip to next scheduled time"""
        if self.schedule_type == ScheduleType.ALWAYS:
            return current_time

        # Skip to next working day/hour
        next_time = current_time + timedelta(hours=1)
        while not self.is_in_schedule(next_time):
            next_time += timedelta(hours=1)
        return next_time


class MotionTriggeredPattern(RecordingPattern):
    """Motion-triggered recording - alternates between idle and recording"""

    def generate_events(
        self,
        start_time: datetime,
        duration_hours: float
    ) -> List[RecordingEvent]:
        """Generate motion-triggered recording events"""
        events = []
        current_time = start_time
        end_time = start_time + timedelta(hours=duration_hours)

        # Get duration ranges
        video_duration_range = self.config.get('video_duration_range', [5, 20])
        idle_duration_range = self.config.get('idle_duration_range', [10, 30])

        min_video, max_video = video_duration_range
        min_idle, max_idle = idle_duration_range

        logger.info(
            f"Generating MOTION_TRIGGERED pattern: "
            f"video {min_video}-{max_video}m, idle {min_idle}-{max_idle}m"
        )

        is_recording = False  # Start with idle

        while current_time < end_time:
            if self.is_in_schedule(current_time):
                if is_recording:
                    # Generate recording event
                    duration = random.uniform(min_video, max_video)
                    events.append(RecordingEvent(
                        start_time=current_time,
                        duration_minutes=duration,
                        is_recording=True
                    ))
                    current_time += timedelta(minutes=duration)
                    is_recording = False
                else:
                    # Generate idle event
                    duration = random.uniform(min_idle, max_idle)
                    events.append(RecordingEvent(
                        start_time=current_time,
                        duration_minutes=duration,
                        is_recording=False
                    ))
                    current_time += timedelta(minutes=duration)
                    is_recording = True
            else:
                # Outside schedule
                current_time = self._skip_to_next_schedule(current_time)

        recording_count = sum(1 for e in events if e.is_recording)
        logger.info(
            f"Generated {len(events)} events "
            f"({recording_count} recording, {len(events)-recording_count} idle)"
        )
        return events

    def _skip_to_next_schedule(self, current_time: datetime) -> datetime:
        """Skip to next scheduled time"""
        if self.schedule_type == ScheduleType.ALWAYS:
            return current_time

        next_time = current_time + timedelta(hours=1)
        while not self.is_in_schedule(next_time):
            next_time += timedelta(hours=1)
        return next_time


class EventTriggeredPattern(RecordingPattern):
    """Event-triggered recording - longer idle periods, shorter recording"""

    def generate_events(
        self,
        start_time: datetime,
        duration_hours: float
    ) -> List[RecordingEvent]:
        """Generate event-triggered recording events"""
        events = []
        current_time = start_time
        end_time = start_time + timedelta(hours=duration_hours)

        # Get duration ranges (typically shorter videos, longer idle)
        video_duration_range = self.config.get('video_duration_range', [3, 10])
        idle_duration_range = self.config.get('idle_duration_range', [20, 60])

        min_video, max_video = video_duration_range
        min_idle, max_idle = idle_duration_range

        logger.info(
            f"Generating EVENT_TRIGGERED pattern: "
            f"video {min_video}-{max_video}m, idle {min_idle}-{max_idle}m"
        )

        is_recording = False  # Start with idle

        while current_time < end_time:
            if self.is_in_schedule(current_time):
                if is_recording:
                    # Generate recording event
                    duration = random.uniform(min_video, max_video)
                    events.append(RecordingEvent(
                        start_time=current_time,
                        duration_minutes=duration,
                        is_recording=True
                    ))
                    current_time += timedelta(minutes=duration)
                    is_recording = False
                else:
                    # Generate idle event
                    duration = random.uniform(min_idle, max_idle)
                    events.append(RecordingEvent(
                        start_time=current_time,
                        duration_minutes=duration,
                        is_recording=False
                    ))
                    current_time += timedelta(minutes=duration)
                    is_recording = True
            else:
                # Outside schedule
                current_time = self._skip_to_next_schedule(current_time)

        recording_count = sum(1 for e in events if e.is_recording)
        logger.info(
            f"Generated {len(events)} events "
            f"({recording_count} recording, {len(events)-recording_count} idle)"
        )
        return events

    def _skip_to_next_schedule(self, current_time: datetime) -> datetime:
        """Skip to next scheduled time"""
        if self.schedule_type == ScheduleType.ALWAYS:
            return current_time

        next_time = current_time + timedelta(hours=1)
        while not self.is_in_schedule(next_time):
            next_time += timedelta(hours=1)
        return next_time


class RandomOnOffPattern(RecordingPattern):
    """Random on/off pattern - camera goes online/offline for extended periods"""

    def generate_events(
        self,
        start_time: datetime,
        duration_hours: float
    ) -> List[RecordingEvent]:
        """Generate random on/off events"""
        events = []
        current_time = start_time
        end_time = start_time + timedelta(hours=duration_hours)

        # Get duration ranges for online/offline periods (in hours)
        online_duration_range = self.config.get('online_duration_range', [2, 8])
        offline_duration_range = self.config.get('offline_duration_range', [1, 4])

        # Video recording config when online
        video_duration_range = self.config.get('video_duration_range', [10, 20])
        min_video, max_video = video_duration_range

        min_online, max_online = online_duration_range
        min_offline, max_offline = offline_duration_range

        logger.info(
            f"Generating RANDOM_ON_OFF pattern: "
            f"online {min_online}-{max_online}h, offline {min_offline}-{max_offline}h"
        )

        is_online = random.choice([True, False])

        while current_time < end_time:
            if is_online:
                # Camera is online - generate continuous recordings
                online_duration_hours = random.uniform(min_online, max_online)
                online_end_time = min(
                    current_time + timedelta(hours=online_duration_hours),
                    end_time
                )

                logger.debug(
                    f"Camera ONLINE period: "
                    f"{online_duration_hours:.1f}h from {current_time}"
                )

                # Generate recordings during online period
                while current_time < online_end_time:
                    if self.is_in_schedule(current_time):
                        duration = random.uniform(min_video, max_video)
                        # Don't exceed online period
                        remaining = (online_end_time - current_time).total_seconds() / 60
                        duration = min(duration, remaining)

                        if duration > 1:  # Only add if > 1 minute
                            events.append(RecordingEvent(
                                start_time=current_time,
                                duration_minutes=duration,
                                is_recording=True
                            ))
                        current_time += timedelta(minutes=duration)
                    else:
                        current_time = self._skip_to_next_schedule(current_time)

                is_online = False

            else:
                # Camera is offline
                offline_duration_hours = random.uniform(min_offline, max_offline)
                logger.debug(
                    f"Camera OFFLINE period: "
                    f"{offline_duration_hours:.1f}h from {current_time}"
                )

                # Add offline event
                events.append(RecordingEvent(
                    start_time=current_time,
                    duration_minutes=offline_duration_hours * 60,
                    is_recording=False
                ))

                current_time += timedelta(hours=offline_duration_hours)
                is_online = True

        recording_count = sum(1 for e in events if e.is_recording)
        logger.info(
            f"Generated {len(events)} events "
            f"({recording_count} recording, {len(events)-recording_count} offline)"
        )
        return events

    def _skip_to_next_schedule(self, current_time: datetime) -> datetime:
        """Skip to next scheduled time"""
        if self.schedule_type == ScheduleType.ALWAYS:
            return current_time

        next_time = current_time + timedelta(hours=1)
        while not self.is_in_schedule(next_time):
            next_time += timedelta(hours=1)
        return next_time


def create_pattern(pattern_type: str, config: Dict) -> RecordingPattern:
    """Factory function to create recording patterns"""
    pattern_map = {
        PatternType.CONTINUOUS.value: ContinuousPattern,
        PatternType.MOTION_TRIGGERED.value: MotionTriggeredPattern,
        PatternType.EVENT_TRIGGERED.value: EventTriggeredPattern,
        PatternType.RANDOM_ON_OFF.value: RandomOnOffPattern,
    }

    pattern_class = pattern_map.get(pattern_type)
    if pattern_class is None:
        raise ValueError(
            f"Unknown pattern type: {pattern_type}. "
            f"Available: {list(pattern_map.keys())}"
        )

    return pattern_class(config)
