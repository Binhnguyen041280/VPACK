"""Database Synchronization Module for ePACK Video Processing System.

This module provides thread synchronization primitives for coordinating between
different components of the video processing pipeline. It ensures thread-safe
database access and proper workflow coordination.

Synchronization Objects:
    db_rwlock: Reader-writer lock for database access synchronization
    frame_sampler_event: Signals when video files are ready for processing
    event_detector_event: Signals when logs are ready for event detection
    event_detector_done: Signals when event detection is complete

Threading Model:
    - Multiple frame sampler threads can read from database concurrently (reader locks)
    - Database writes require exclusive access (writer locks)
    - Events coordinate workflow between frame sampling and event detection stages
    - Fair reader-writer lock prevents starvation

Usage Patterns:
    - Database reads: Use gen_rlock() for concurrent access
    - Database writes: Use gen_wlock() for exclusive access
    - Signal work available: Set events to wake up waiting threads
    - Wait for work: Call event.wait() to block until signaled
    - Signal completion: Set event_detector_done to allow pipeline continuation

Event Flow:
    1. File scanner sets frame_sampler_event when new files are available
    2. Frame samplers wait on frame_sampler_event, process videos, set event_detector_event
    3. Event detector waits on event_detector_event, processes logs, sets event_detector_done
    4. Frame samplers wait on event_detector_done before continuing to next video
"""

from readerwriterlock import rwlock
import threading
from typing import Optional
# Import logger conditionally to avoid circular imports during initialization
try:
    from modules.config.logging_config import get_logger
    logger = get_logger(__name__, {"module": "db_sync"})
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Reader-Writer Lock for database access synchronization
# Uses RWLockFairD to prevent reader/writer starvation and avoid deadlocks
db_rwlock = rwlock.RWLockFairD()

# Event signaling when video files are ready for frame sampling
# Set by: File scanner when new videos are discovered
# Waited on by: Frame sampler threads
frame_sampler_event = threading.Event()

# Event signaling when frame sampling logs are ready for event detection
# Set by: Frame sampler threads after processing videos
# Waited on by: Event detector thread
event_detector_event = threading.Event()

# Event signaling when event detection is complete
# Set by: Event detector thread after processing logs
# Waited on by: Frame sampler threads before continuing to next video
event_detector_done = threading.Event()
event_detector_done.set()  # Initially set to allow frame samplers to start

# Event signaling when system is idle (no files being processed)
# Set by: Idle monitor in batch_scheduler when all files processed
# Waited on by: Retry processor to start empty event recovery
# Cleared by: Idle monitor after retry completes
system_idle_event = threading.Event()

# Event signaling retry is in progress (blocks file scanner)
# Set by: Idle monitor before starting retry
# Checked by: File scanner to pause new file scanning
# Cleared by: Idle monitor after retry completes
retry_in_progress_flag = threading.Event()

# Log module initialization with thread information
logger.debug("Database sync module initialized", extra={"thread_id": threading.current_thread().ident})

# Enhanced event operations with comprehensive logging for debugging
class LoggedEvent:
    """Wrapper around threading.Event with debug logging.
    
    This class provides enhanced debugging capabilities for threading events
    by logging all operations with thread context information. Useful for
    diagnosing thread coordination issues and understanding event flow.
    
    Attributes:
        name (str): Human-readable name for the event
        event (threading.Event): The underlying event object
    
    Usage:
        Replace direct threading.Event usage with LoggedEvent for debugging:
        logged_event = LoggedEvent("my_event", threading.Event())
        logged_event.set()  # Logs the set operation with thread ID
        logged_event.wait()  # Logs waiting and completion
    """
    def __init__(self, name: str, event: threading.Event) -> None:
        """Initialize LoggedEvent with name and underlying event.
        
        Args:
            name (str): Human-readable name for debugging
            event (threading.Event): The event object to wrap
        """
        self.name = name
        self.event = event
        
    def set(self) -> None:
        """Set the event and log the operation with thread context."""
        logger.debug(f"Event {self.name} set", extra={
            "thread_id": threading.current_thread().ident, 
            "event_name": self.name
        })
        self.event.set()
        
    def clear(self) -> None:
        """Clear the event and log the operation with thread context."""
        logger.debug(f"Event {self.name} cleared", extra={
            "thread_id": threading.current_thread().ident, 
            "event_name": self.name
        })
        self.event.clear()
        
    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for the event with optional timeout, logging the operation.
        
        Args:
            timeout (float, optional): Maximum time to wait in seconds
            
        Returns:
            bool: True if event was set, False if timeout occurred
        """
        logger.debug(f"Waiting for event {self.name}", extra={
            "thread_id": threading.current_thread().ident, 
            "event_name": self.name
        })
        result = self.event.wait(timeout)
        
        if result:
            logger.debug(f"Event {self.name} received", extra={
                "thread_id": threading.current_thread().ident, 
                "event_name": self.name
            })
        else:
            logger.debug(f"Event {self.name} timeout", extra={
                "thread_id": threading.current_thread().ident, 
                "event_name": self.name
            })
        return result
        
    def is_set(self) -> bool:
        """Check if the event is set without blocking.
        
        Returns:
            bool: True if event is set, False otherwise
        """
        return self.event.is_set()

# Optional logged event wrappers for enhanced debugging
# These can be imported and used instead of the raw events when debugging
# thread coordination issues or understanding event flow patterns
logged_frame_sampler_event = LoggedEvent("frame_sampler", frame_sampler_event)
logged_event_detector_event = LoggedEvent("event_detector", event_detector_event)
logged_event_detector_done = LoggedEvent("event_detector_done", event_detector_done)
