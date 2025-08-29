"""
QR Code Detection Streaming Module
Adapted from qr_detector.py for web streaming capabilities
"""

import cv2
import time
import logging
import numpy as np
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from modules.config.logging_config import get_logger

logger = get_logger(__name__)

# WeChat QR Code model paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_DIR = os.path.join(BASE_DIR, "backend", "models", "wechat_qr")
DETECT_PROTO = os.path.join(MODEL_DIR, "detect.prototxt")
DETECT_MODEL = os.path.join(MODEL_DIR, "detect.caffemodel")
SR_PROTO = os.path.join(MODEL_DIR, "sr.prototxt")
SR_MODEL = os.path.join(MODEL_DIR, "sr.caffemodel")

@dataclass
class QRDetectionResult:
    """QR detection result for streaming"""
    timestamp: float
    frame_number: int
    qr_codes_detected: int
    content: List[str]
    coordinates: List[Dict[str, Any]]
    confidence: float
    detection_boxes: List[Dict[str, float]]

class QRDetectorStreaming:
    """
    QR Code detection class adapted for streaming output instead of cv2.imshow
    """
    
    def __init__(self):
        """Initialize QR detection for streaming"""
        self.detector = None
        self.initialized = False
        self._init_detector()
        
    def _init_detector(self):
        """Initialize WeChat QR Code detector"""
        try:
            # Check if model files exist
            model_files = [DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL]
            missing_files = [f for f in model_files if not os.path.exists(f)]
            
            if missing_files:
                logger.error(f"Missing QR model files: {missing_files}")
                return
                
            # Initialize WeChat QRCode detector
            self.detector = cv2.wechat_qrcode_WeChatQRCode(
                DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL
            )
            self.initialized = True
            logger.info("QRDetectorStreaming initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing QR detector: {str(e)}")
            self.detector = None
            self.initialized = False

    def detect_qr_in_frame(self, 
                          frame: np.ndarray, 
                          frame_number: int) -> Optional[Dict[str, Any]]:
        """
        Detect QR codes in a single frame for streaming output
        
        Args:
            frame: Input frame (BGR format)
            frame_number: Frame sequence number
            
        Returns:
            dict: Detection results or None if no QR codes detected
        """
        try:
            if not self.initialized or self.detector is None:
                return None
                
            if frame is None or frame.size == 0:
                return None
                
            # Detect QR codes
            texts, points = self.detector.detectAndDecode(frame)
            
            if not texts or len(texts) == 0:
                return None
                
            # Process detection results
            qr_codes_detected = len(texts)
            detection_boxes = []
            coordinates = []
            confidence_scores = []
            
            for i, (text, box) in enumerate(zip(texts, points)):
                if text:  # Only process non-empty QR codes
                    # Calculate bounding box
                    if len(box) >= 4:
                        x_coords = [point[0] for point in box]
                        y_coords = [point[1] for point in box]
                        
                        bbox = {
                            "x_min": float(min(x_coords)),
                            "y_min": float(min(y_coords)),
                            "x_max": float(max(x_coords)),
                            "y_max": float(max(y_coords)),
                            "width": float(max(x_coords) - min(x_coords)),
                            "height": float(max(y_coords) - min(y_coords)),
                            "center_x": float(sum(x_coords) / len(x_coords)),
                            "center_y": float(sum(y_coords) / len(y_coords))
                        }
                        detection_boxes.append(bbox)
                        
                        # Store coordinates for visualization
                        coord_data = {
                            "qr_id": i,
                            "content": text,
                            "corners": [
                                {"x": float(point[0]), "y": float(point[1])} 
                                for point in box
                            ],
                            "bounding_box": bbox
                        }
                        coordinates.append(coord_data)
                        
                        # Calculate confidence based on box area and text length
                        box_area = bbox["width"] * bbox["height"]
                        text_confidence = min(1.0, len(text) / 20.0)  # Normalize by expected length
                        area_confidence = min(1.0, box_area / (100 * 100))  # Normalize by expected area
                        combined_confidence = (text_confidence + area_confidence) / 2
                        confidence_scores.append(combined_confidence)
            
            if not detection_boxes:
                return None
                
            # Calculate overall confidence
            overall_confidence = float(np.mean(confidence_scores)) if confidence_scores else 0.5
            
            return {
                "timestamp": time.time(),
                "frame_number": frame_number,
                "qr_codes_detected": qr_codes_detected,
                "content": list(texts),
                "coordinates": coordinates,
                "confidence": overall_confidence,
                "detection_boxes": detection_boxes,
                "detection_type": "qr_detection"
            }
            
        except Exception as e:
            logger.error(f"Error in QR detection for frame {frame_number}: {str(e)}")
            return None

    def analyze_qr_motion(self, 
                         detection_results: List[Dict[str, Any]], 
                         window_size: int = 10) -> Dict[str, Any]:
        """
        Analyze QR code motion patterns from detection results
        
        Args:
            detection_results: List of recent detection results
            window_size: Number of frames to analyze
            
        Returns:
            dict: Motion analysis results
        """
        try:
            if len(detection_results) < 2:
                return {
                    "motion_detected": False,
                    "qr_stability": 1.0,
                    "position_change": 0.0
                }
            
            recent_results = detection_results[-window_size:]
            position_changes = []
            stability_scores = []
            
            # Track QR code positions over time
            for i in range(1, len(recent_results)):
                prev_result = recent_results[i-1]
                curr_result = recent_results[i]
                
                prev_qrs = prev_result.get("qr_codes_detected", 0)
                curr_qrs = curr_result.get("qr_codes_detected", 0)
                
                # Calculate stability (consistent detection)
                if prev_qrs > 0 and curr_qrs > 0:
                    stability_scores.append(1.0)
                    
                    # Compare positions if we have coordinates
                    prev_coords = prev_result.get("coordinates", [])
                    curr_coords = curr_result.get("coordinates", [])
                    
                    if prev_coords and curr_coords:
                        # Compare center positions of first QR code
                        prev_center = prev_coords[0]["bounding_box"]
                        curr_center = curr_coords[0]["bounding_box"]
                        
                        dx = curr_center["center_x"] - prev_center["center_x"]
                        dy = curr_center["center_y"] - prev_center["center_y"]
                        distance = np.sqrt(dx**2 + dy**2)
                        
                        position_changes.append(distance)
                else:
                    stability_scores.append(0.0)
            
            # Calculate metrics
            average_stability = float(np.mean(stability_scores)) if stability_scores else 0.0
            average_position_change = float(np.mean(position_changes)) if position_changes else 0.0
            motion_detected = average_position_change > 5.0  # Threshold for significant motion
            
            return {
                "motion_detected": motion_detected,
                "qr_stability": average_stability,
                "position_change": average_position_change,
                "frames_analyzed": len(recent_results),
                "detection_consistency": average_stability
            }
            
        except Exception as e:
            logger.error(f"Error analyzing QR motion: {str(e)}")
            return {
                "motion_detected": False,
                "qr_stability": 0.0,
                "position_change": 0.0,
                "error": str(e)
            }

    def detect_qr_events(self, 
                        detection_results: List[Dict[str, Any]],
                        trigger_content: str = "timego") -> List[Dict[str, Any]]:
        """
        Detect QR-based events from detection results
        
        Args:
            detection_results: List of detection results
            trigger_content: Expected trigger QR content (case insensitive)
            
        Returns:
            list: Detected QR events
        """
        try:
            events = []
            
            if len(detection_results) < 2:
                return events
                
            trigger_content_lower = trigger_content.lower()
            
            # Look for QR appearance/disappearance and trigger detection
            for i, result in enumerate(detection_results):
                qr_contents = result.get("content", [])
                frame_number = result.get("frame_number", i)
                timestamp = result.get("timestamp", time.time())
                confidence = result.get("confidence", 0.0)
                
                # Check for QR code appearance
                if len(qr_contents) > 0 and confidence > 0.6:
                    # Check for trigger QR content
                    for content in qr_contents:
                        if content.lower() == trigger_content_lower:
                            event = {
                                "timestamp": timestamp,
                                "frame_number": frame_number,
                                "event_type": "trigger_qr_detected",
                                "confidence": confidence,
                                "qr_content": content,
                                "description": f"Trigger QR code detected: {content}"
                            }
                            events.append(event)
                        else:
                            # Regular QR detection event
                            event = {
                                "timestamp": timestamp,
                                "frame_number": frame_number,
                                "event_type": "qr_detected",
                                "confidence": confidence,
                                "qr_content": content,
                                "description": f"QR code detected: {content}"
                            }
                            events.append(event)
                
                # Check for QR disappearance (coverage/uncoverage)
                if i > 0:
                    prev_result = detection_results[i-1]
                    prev_contents = prev_result.get("content", [])
                    
                    # QR covered (was visible, now not)
                    if len(prev_contents) > 0 and len(qr_contents) == 0:
                        event = {
                            "timestamp": timestamp,
                            "frame_number": frame_number,
                            "event_type": "qr_covered",
                            "confidence": prev_result.get("confidence", 0.0),
                            "qr_content": prev_contents[0] if prev_contents else "",
                            "description": "QR code covered/hidden"
                        }
                        events.append(event)
                    
                    # QR uncovered (was not visible, now visible)
                    elif len(prev_contents) == 0 and len(qr_contents) > 0:
                        event = {
                            "timestamp": timestamp,
                            "frame_number": frame_number,
                            "event_type": "qr_uncovered",
                            "confidence": confidence,
                            "qr_content": qr_contents[0],
                            "description": "QR code uncovered/visible"
                        }
                        events.append(event)
                
            return events
            
        except Exception as e:
            logger.error(f"Error detecting QR events: {str(e)}")
            return []

    def analyze_trigger_correlation(self, 
                                  qr_events: List[Dict[str, Any]],
                                  motion_events: List[Dict[str, Any]],
                                  correlation_window: float = 2.0) -> Dict[str, Any]:
        """
        Analyze correlation between QR trigger events and motion events
        
        Args:
            qr_events: List of QR detection events
            motion_events: List of motion detection events
            correlation_window: Time window in seconds for correlation
            
        Returns:
            dict: Correlation analysis results
        """
        try:
            trigger_events = [e for e in qr_events if e.get("event_type") == "trigger_qr_detected"]
            
            if not trigger_events or not motion_events:
                return {
                    "correlated_events": 0,
                    "correlation_rate": 0.0,
                    "average_delay": 0.0,
                    "total_triggers": len(trigger_events)
                }
            
            correlated_pairs = []
            
            # Find motion events that occur within correlation window of trigger events
            for trigger_event in trigger_events:
                trigger_time = trigger_event["timestamp"]
                
                # Find closest motion event within window
                closest_motion = None
                min_delay = float('inf')
                
                for motion_event in motion_events:
                    motion_time = motion_event["timestamp"]
                    delay = abs(motion_time - trigger_time)
                    
                    if delay <= correlation_window and delay < min_delay:
                        min_delay = delay
                        closest_motion = motion_event
                
                if closest_motion:
                    correlated_pairs.append({
                        "trigger_event": trigger_event,
                        "motion_event": closest_motion,
                        "delay": min_delay
                    })
            
            # Calculate correlation metrics
            correlation_rate = len(correlated_pairs) / len(trigger_events) if trigger_events else 0.0
            average_delay = np.mean([pair["delay"] for pair in correlated_pairs]) if correlated_pairs else 0.0
            
            return {
                "correlated_events": len(correlated_pairs),
                "correlation_rate": correlation_rate,
                "average_delay": float(average_delay),
                "total_triggers": len(trigger_events),
                "total_motions": len(motion_events),
                "correlation_pairs": correlated_pairs
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trigger correlation: {str(e)}")
            return {
                "correlated_events": 0,
                "correlation_rate": 0.0,
                "average_delay": 0.0,
                "total_triggers": 0,
                "error": str(e)
            }

    def cleanup(self):
        """Clean up detector resources"""
        try:
            self.detector = None
            self.initialized = False
            logger.info("QRDetectorStreaming resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up QRDetectorStreaming: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()