"""
Video Analysis Streaming Module
Provides real-time video analysis streaming capabilities for web interfaces
"""

import cv2
import json
import time
import uuid
import queue
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from modules.config.logging_config import get_logger

logger = get_logger(__name__)

class AnalysisMethod(Enum):
    TRADITIONAL = "traditional"
    QR_CODE = "qr_code"

class StreamStatus(Enum):
    STARTING = "starting"
    RUNNING = "running" 
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ROIConfig:
    """ROI configuration for analysis"""
    x: int
    y: int
    w: int
    h: int
    type: str
    label: str

@dataclass
class DetectionResult:
    """Detection result data structure"""
    timestamp: float
    frame_number: int
    roi_id: str
    detection_type: str
    confidence: float
    coordinates: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    landmarks: Optional[List[Dict[str, Any]]] = None

@dataclass
class StreamFrame:
    """Stream frame data structure"""
    timestamp: float
    frame_number: int
    frame_data: Optional[str] = None  # Base64 encoded frame
    detections: List[DetectionResult] = None
    status: str = "processing"

@dataclass
class AnalysisSession:
    """Analysis session metadata"""
    session_id: str
    method: AnalysisMethod
    video_path: str
    rois: List[ROIConfig]
    status: StreamStatus
    start_time: float
    frame_count: int = 0
    total_frames: int = 0
    fps: float = 0.0
    speed_multiplier: float = 5.0

class StreamingAnalyzer:
    """
    Main streaming analyzer class that coordinates video analysis and streaming
    """
    
    def __init__(self):
        self.sessions: Dict[str, AnalysisSession] = {}
        self.stream_queues: Dict[str, queue.Queue] = {}
        self.analysis_threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        self.client_connections: Dict[str, List[Callable]] = {}
        
    def create_session(self, 
                      video_path: str, 
                      method: AnalysisMethod,
                      rois: List[Dict[str, Any]]) -> str:
        """
        Create a new analysis session
        
        Args:
            video_path: Path to video file
            method: Analysis method (traditional or qr_code)
            rois: List of ROI configurations
            
        Returns:
            session_id: Unique session identifier
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Convert ROI dictionaries to ROIConfig objects
            roi_configs = [ROIConfig(**roi) for roi in rois]
            
            # Get video metadata
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            # Create session
            session = AnalysisSession(
                session_id=session_id,
                method=method,
                video_path=video_path,
                rois=roi_configs,
                status=StreamStatus.STARTING,
                start_time=time.time(),
                total_frames=total_frames,
                fps=fps
            )
            
            self.sessions[session_id] = session
            self.stream_queues[session_id] = queue.Queue(maxsize=100)
            self.stop_events[session_id] = threading.Event()
            self.client_connections[session_id] = []
            
            logger.info(f"Created analysis session {session_id} for method {method.value}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating analysis session: {str(e)}")
            raise

    def start_analysis(self, session_id: str) -> bool:
        """
        Start video analysis for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: Success status
        """
        try:
            if session_id not in self.sessions:
                logger.error(f"Session {session_id} not found")
                return False
                
            session = self.sessions[session_id]
            
            if session.status == StreamStatus.RUNNING:
                logger.warning(f"Session {session_id} already running")
                return True
                
            # Start analysis thread
            if session.method == AnalysisMethod.TRADITIONAL:
                analysis_func = self._analyze_traditional
            else:
                analysis_func = self._analyze_qr_code
                
            thread = threading.Thread(
                target=analysis_func,
                args=(session_id,),
                daemon=True
            )
            
            self.analysis_threads[session_id] = thread
            session.status = StreamStatus.RUNNING
            thread.start()
            
            logger.info(f"Started analysis for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting analysis for session {session_id}: {str(e)}")
            if session_id in self.sessions:
                self.sessions[session_id].status = StreamStatus.ERROR
            return False

    def stop_analysis(self, session_id: str) -> bool:
        """
        Stop video analysis for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: Success status
        """
        try:
            if session_id not in self.sessions:
                logger.error(f"Session {session_id} not found")
                return False
                
            session = self.sessions[session_id]
            session.status = StreamStatus.STOPPING
            
            # Signal stop to analysis thread
            if session_id in self.stop_events:
                self.stop_events[session_id].set()
                
            # Wait for thread to finish
            if session_id in self.analysis_threads:
                thread = self.analysis_threads[session_id]
                thread.join(timeout=5.0)
                if thread.is_alive():
                    logger.warning(f"Analysis thread for session {session_id} did not stop gracefully")
                    
            session.status = StreamStatus.STOPPED
            logger.info(f"Stopped analysis for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping analysis for session {session_id}: {str(e)}")
            return False

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session status and metadata
        
        Args:
            session_id: Session identifier
            
        Returns:
            dict: Session status information
        """
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        
        return {
            "session_id": session_id,
            "method": session.method.value,
            "status": session.status.value,
            "frame_count": session.frame_count,
            "total_frames": session.total_frames,
            "fps": session.fps,
            "speed_multiplier": session.speed_multiplier,
            "progress": session.frame_count / session.total_frames if session.total_frames > 0 else 0.0,
            "elapsed_time": time.time() - session.start_time,
            "roi_count": len(session.rois)
        }

    def get_stream_data(self, session_id: str, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        Get next stream data frame
        
        Args:
            session_id: Session identifier
            timeout: Timeout for queue get operation
            
        Returns:
            dict: Stream frame data or None if no data available
        """
        if session_id not in self.stream_queues:
            return None
            
        try:
            stream_frame = self.stream_queues[session_id].get(timeout=timeout)
            return asdict(stream_frame)
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error getting stream data for session {session_id}: {str(e)}")
            return None

    def cleanup_session(self, session_id: str):
        """
        Clean up session resources
        
        Args:
            session_id: Session identifier
        """
        try:
            # Stop analysis if running
            self.stop_analysis(session_id)
            
            # Clean up resources
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.stream_queues:
                del self.stream_queues[session_id]
            if session_id in self.analysis_threads:
                del self.analysis_threads[session_id]
            if session_id in self.stop_events:
                del self.stop_events[session_id]
            if session_id in self.client_connections:
                del self.client_connections[session_id]
                
            logger.info(f"Cleaned up session {session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {str(e)}")

    def _analyze_traditional(self, session_id: str):
        """
        Traditional method analysis thread
        
        Args:
            session_id: Session identifier
        """
        try:
            from modules.technician.hand_detection_streaming import HandDetectionStreaming
            
            session = self.sessions[session_id]
            detector = HandDetectionStreaming()
            
            logger.info(f"Starting traditional analysis for session {session_id}")
            
            cap = cv2.VideoCapture(session.video_path)
            frame_interval = max(1, int(session.fps / (session.fps * session.speed_multiplier)))
            
            frame_number = 0
            
            while not self.stop_events[session_id].is_set():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_number += 1
                session.frame_count = frame_number
                
                # Process frame at specified intervals
                if frame_number % frame_interval == 0:
                    detections = []
                    
                    # Process each ROI
                    for roi in session.rois:
                        if roi.type == 'packing_area':
                            roi_frame = frame[roi.y:roi.y+roi.h, roi.x:roi.x+roi.w]
                            detection_result = detector.detect_hands_in_frame(roi_frame, frame_number)
                            
                            if detection_result:
                                detection = DetectionResult(
                                    timestamp=time.time(),
                                    frame_number=frame_number,
                                    roi_id=f"{roi.type}_{roi.x}_{roi.y}",
                                    detection_type="hand_detection",
                                    confidence=detection_result.get('confidence', 0.0),
                                    landmarks=detection_result.get('landmarks', [])
                                )
                                detections.append(detection)
                    
                    # Create stream frame
                    stream_frame = StreamFrame(
                        timestamp=time.time(),
                        frame_number=frame_number,
                        detections=detections,
                        status="processing"
                    )
                    
                    # Add to stream queue
                    try:
                        self.stream_queues[session_id].put_nowait(stream_frame)
                    except queue.Full:
                        # Remove oldest frame if queue is full
                        try:
                            self.stream_queues[session_id].get_nowait()
                            self.stream_queues[session_id].put_nowait(stream_frame)
                        except queue.Empty:
                            pass
                            
            cap.release()
            logger.info(f"Traditional analysis completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error in traditional analysis for session {session_id}: {str(e)}")
            if session_id in self.sessions:
                self.sessions[session_id].status = StreamStatus.ERROR

    def _analyze_qr_code(self, session_id: str):
        """
        QR Code method analysis thread
        
        Args:
            session_id: Session identifier
        """
        try:
            from modules.technician.qr_detector_streaming import QRDetectorStreaming
            
            session = self.sessions[session_id]
            detector = QRDetectorStreaming()
            
            logger.info(f"Starting QR code analysis for session {session_id}")
            
            cap = cv2.VideoCapture(session.video_path)
            frame_interval = max(1, int(session.fps / (session.fps * session.speed_multiplier)))
            
            frame_number = 0
            
            while not self.stop_events[session_id].is_set():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_number += 1
                session.frame_count = frame_number
                
                # Process frame at specified intervals
                if frame_number % frame_interval == 0:
                    detections = []
                    
                    # Process each ROI
                    for roi in session.rois:
                        if roi.type in ['qr_mvd', 'qr_trigger']:
                            roi_frame = frame[roi.y:roi.y+roi.h, roi.x:roi.x+roi.w]
                            detection_result = detector.detect_qr_in_frame(roi_frame, frame_number)
                            
                            if detection_result:
                                detection = DetectionResult(
                                    timestamp=time.time(),
                                    frame_number=frame_number,
                                    roi_id=f"{roi.type}_{roi.x}_{roi.y}",
                                    detection_type="qr_detection",
                                    confidence=detection_result.get('confidence', 0.0),
                                    content=detection_result.get('content', ''),
                                    coordinates=detection_result.get('coordinates', {})
                                )
                                detections.append(detection)
                    
                    # Create stream frame
                    stream_frame = StreamFrame(
                        timestamp=time.time(),
                        frame_number=frame_number,
                        detections=detections,
                        status="processing"
                    )
                    
                    # Add to stream queue
                    try:
                        self.stream_queues[session_id].put_nowait(stream_frame)
                    except queue.Full:
                        # Remove oldest frame if queue is full
                        try:
                            self.stream_queues[session_id].get_nowait()
                            self.stream_queues[session_id].put_nowait(stream_frame)
                        except queue.Empty:
                            pass
                            
            cap.release()
            logger.info(f"QR code analysis completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error in QR code analysis for session {session_id}: {str(e)}")
            if session_id in self.sessions:
                self.sessions[session_id].status = StreamStatus.ERROR

# Global analyzer instance
streaming_analyzer = StreamingAnalyzer()