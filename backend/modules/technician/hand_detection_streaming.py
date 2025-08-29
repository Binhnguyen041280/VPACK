"""
Hand Detection Streaming Module
Adapted from hand_detection.py for web streaming capabilities
"""

import cv2
import mediapipe as mp
import time
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from modules.config.logging_config import get_logger

logger = get_logger(__name__)

# Type-safe MediaPipe imports
try:
    mp_hands = mp.solutions.hands  # type: ignore
    mp_drawing = mp.solutions.drawing_utils  # type: ignore
except AttributeError as e:
    logger.error(f"MediaPipe import error: {e}")
    raise ImportError("MediaPipe modules not found. Please reinstall MediaPipe.")

@dataclass
class HandLandmark:
    """Hand landmark data structure"""
    x: float
    y: float
    z: float
    visibility: Optional[float] = None

@dataclass
class HandDetectionResult:
    """Hand detection result for streaming"""
    timestamp: float
    frame_number: int
    hands_detected: int
    confidence: float
    landmarks: List[List[HandLandmark]]
    bounding_boxes: List[Dict[str, float]]
    hand_labels: List[str]  # Left, Right

class HandDetectionStreaming:
    """
    Hand detection class adapted for streaming output instead of cv2.imshow
    """
    
    def __init__(self, 
                 detection_confidence: float = 0.5,
                 tracking_confidence: float = 0.5,
                 max_num_hands: int = 2):
        """
        Initialize hand detection for streaming
        
        Args:
            detection_confidence: Minimum detection confidence
            tracking_confidence: Minimum tracking confidence  
            max_num_hands: Maximum number of hands to detect
        """
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        self.max_num_hands = max_num_hands
        
        # Initialize MediaPipe Hands
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
        
        logger.info(f"HandDetectionStreaming initialized with confidence={detection_confidence}")

    def detect_hands_in_frame(self, 
                            frame: np.ndarray, 
                            frame_number: int) -> Optional[Dict[str, Any]]:
        """
        Detect hands in a single frame for streaming output
        
        Args:
            frame: Input frame (BGR format)
            frame_number: Frame sequence number
            
        Returns:
            dict: Detection results or None if no hands detected
        """
        try:
            if frame is None or frame.size == 0:
                return None
                
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame
            results = self.hands.process(rgb_frame)
            
            if not results.multi_hand_landmarks:
                return None
                
            # Extract detection data
            hands_detected = len(results.multi_hand_landmarks)
            landmarks_list = []
            bounding_boxes = []
            hand_labels = []
            confidences = []
            
            for idx, (hand_landmarks, hand_classification) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness or [])
            ):
                # Extract landmarks
                landmarks = []
                x_coords = []
                y_coords = []
                
                for landmark in hand_landmarks.landmark:
                    landmark_data = HandLandmark(
                        x=landmark.x,
                        y=landmark.y,
                        z=landmark.z,
                        visibility=getattr(landmark, 'visibility', None)
                    )
                    landmarks.append(landmark_data)
                    x_coords.append(landmark.x * frame.shape[1])
                    y_coords.append(landmark.y * frame.shape[0])
                
                landmarks_list.append([
                    {"x": l.x, "y": l.y, "z": l.z, "visibility": l.visibility}
                    for l in landmarks
                ])
                
                # Calculate bounding box
                if x_coords and y_coords:
                    bbox = {
                        "x_min": float(min(x_coords)),
                        "y_min": float(min(y_coords)),
                        "x_max": float(max(x_coords)),
                        "y_max": float(max(y_coords)),
                        "width": float(max(x_coords) - min(x_coords)),
                        "height": float(max(y_coords) - min(y_coords))
                    }
                    bounding_boxes.append(bbox)
                
                # Extract hand classification
                if hand_classification and hand_classification.classification:
                    label = hand_classification.classification[0].label
                    confidence = hand_classification.classification[0].score
                    hand_labels.append(label)
                    confidences.append(confidence)
                else:
                    hand_labels.append("Unknown")
                    confidences.append(0.5)
            
            # Calculate overall confidence
            overall_confidence = float(np.mean(confidences)) if confidences else 0.0
            
            return {
                "timestamp": time.time(),
                "frame_number": frame_number,
                "hands_detected": hands_detected,
                "confidence": overall_confidence,
                "landmarks": landmarks_list,
                "bounding_boxes": bounding_boxes,
                "hand_labels": hand_labels,
                "detection_type": "hand_detection"
            }
            
        except Exception as e:
            logger.error(f"Error in hand detection for frame {frame_number}: {str(e)}")
            return None

    def analyze_hand_motion(self, 
                          detection_results: List[Dict[str, Any]], 
                          window_size: int = 10) -> Dict[str, Any]:
        """
        Analyze hand motion patterns from detection results
        
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
                    "average_speed": 0.0,
                    "dominant_direction": "none"
                }
            
            recent_results = detection_results[-window_size:]
            movements = []
            
            # Calculate movements between consecutive frames
            for i in range(1, len(recent_results)):
                prev_result = recent_results[i-1]
                curr_result = recent_results[i]
                
                if (prev_result.get("hands_detected", 0) > 0 and 
                    curr_result.get("hands_detected", 0) > 0):
                    
                    # Compare first hand positions
                    prev_landmarks = prev_result.get("landmarks", [[]])[0]
                    curr_landmarks = curr_result.get("landmarks", [[]])[0]
                    
                    if prev_landmarks and curr_landmarks:
                        # Use wrist position (landmark 0) for movement calculation
                        prev_wrist = prev_landmarks[0]
                        curr_wrist = curr_landmarks[0]
                        
                        dx = curr_wrist["x"] - prev_wrist["x"]
                        dy = curr_wrist["y"] - prev_wrist["y"]
                        distance = np.sqrt(dx**2 + dy**2)
                        
                        movements.append({
                            "distance": distance,
                            "dx": dx,
                            "dy": dy,
                            "frame_delta": curr_result["frame_number"] - prev_result["frame_number"]
                        })
            
            if not movements:
                return {
                    "motion_detected": False,
                    "average_speed": 0.0,
                    "dominant_direction": "none"
                }
            
            # Calculate motion metrics
            distances = [m["distance"] for m in movements]
            average_distance = float(np.mean(distances))
            max_distance = float(np.max(distances))
            
            # Calculate dominant direction
            dx_total = sum(m["dx"] for m in movements)
            dy_total = sum(m["dy"] for m in movements)
            
            if abs(dx_total) > abs(dy_total):
                dominant_direction = "horizontal" if dx_total > 0 else "horizontal"
            else:
                dominant_direction = "vertical" if dy_total > 0 else "vertical"
            
            # Motion detection threshold
            motion_detected = average_distance > 0.02  # Adjust threshold as needed
            
            return {
                "motion_detected": motion_detected,
                "average_speed": average_distance,
                "max_speed": max_distance,
                "dominant_direction": dominant_direction,
                "total_frames_analyzed": len(movements),
                "motion_consistency": float(np.std(distances)) if len(distances) > 1 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing hand motion: {str(e)}")
            return {
                "motion_detected": False,
                "average_speed": 0.0,
                "dominant_direction": "none",
                "error": str(e)
            }

    def detect_packing_events(self, 
                            detection_results: List[Dict[str, Any]],
                            event_threshold: float = 0.05) -> List[Dict[str, Any]]:
        """
        Detect packing events from hand detection results
        
        Args:
            detection_results: List of detection results
            event_threshold: Motion threshold for event detection
            
        Returns:
            list: Detected packing events
        """
        try:
            events = []
            
            if len(detection_results) < 5:
                return events
                
            # Analyze motion patterns to detect packing events
            motion_analysis = self.analyze_hand_motion(detection_results)
            
            if motion_analysis["motion_detected"]:
                # Look for significant motion changes
                recent_results = detection_results[-10:]
                motion_peaks = []
                
                for i in range(1, len(recent_results)):
                    prev_result = recent_results[i-1]
                    curr_result = recent_results[i]
                    
                    # Calculate motion intensity
                    prev_hands = prev_result.get("hands_detected", 0)
                    curr_hands = curr_result.get("hands_detected", 0)
                    
                    if curr_hands > 0:
                        # Detect potential packing action
                        confidence = curr_result.get("confidence", 0.0)
                        
                        if confidence > 0.7 and motion_analysis["average_speed"] > event_threshold:
                            event = {
                                "timestamp": curr_result.get("timestamp", time.time()),
                                "frame_number": curr_result.get("frame_number", 0),
                                "event_type": "packing_action",
                                "confidence": confidence,
                                "motion_speed": motion_analysis["average_speed"],
                                "hands_involved": curr_hands,
                                "description": f"Packing action detected with {curr_hands} hands"
                            }
                            events.append(event)
                
            return events
            
        except Exception as e:
            logger.error(f"Error detecting packing events: {str(e)}")
            return []

    def cleanup(self):
        """Clean up MediaPipe resources"""
        try:
            if hasattr(self, 'hands') and self.hands:
                self.hands.close()
                logger.info("HandDetectionStreaming resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up HandDetectionStreaming: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()