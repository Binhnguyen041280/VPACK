"""
Hand Detection Web Adapter
Adapted from hand_detection.py for web streaming capabilities
Removes cv2.imshow dependencies and provides streaming interface
"""

import cv2
import mediapipe as mp
import time
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from modules.config.logging_config import get_logger
from modules.technician.landmark_mapper import LandmarkMapper, ROIConfig, VideoDimensions, CanvasDimensions

logger = get_logger(__name__)

# Type-safe MediaPipe imports
try:
    mp_hands = mp.solutions.hands  # type: ignore
    mp_drawing = mp.solutions.drawing_utils  # type: ignore
except AttributeError as e:
    logger.error(f"MediaPipe import error: {e}")
    raise ImportError("MediaPipe modules not found. Please reinstall MediaPipe.")

# Frame processing step - exactly same as original hand_detection.py
FRAME_STEP = 5

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

class HandDetectionWeb:
    """
    Hand detection class adapted for web streaming from proven hand_detection.py
    Maintains exact same MediaPipe logic and frame processing rate (FRAME_STEP=5)
    """
    
    def __init__(self, 
                 detection_confidence: float = 0.5,
                 tracking_confidence: float = 0.5,
                 max_num_hands: int = 2):
        """
        Initialize hand detection for web streaming
        Uses exact same parameters as hand_detection.py for proven results
        """
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        self.max_num_hands = max_num_hands
        
        # Initialize MediaPipe Hands with exact same config as hand_detection.py
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
        
        logger.info(f"HandDetectionWeb initialized with FRAME_STEP={FRAME_STEP}, confidence={detection_confidence}")

    def detect_hands_in_frame(self, 
                            frame: np.ndarray, 
                            frame_number: int,
                            roi_offset: Optional[Dict[str, int]] = None,
                            video_dims: Optional[Dict[str, int]] = None,
                            canvas_dims: Optional[Dict[str, int]] = None) -> Optional[Dict[str, Any]]:
        """
        Detect hands in a single frame for streaming output
        Maintains exact same MediaPipe processing as original
        
        Args:
            frame: Input frame (BGR format)
            frame_number: Frame sequence number
            roi_offset: ROI offset coordinates for absolute positioning
            video_dims: Original video dimensions for coordinate mapping
            canvas_dims: Canvas dimensions for display coordinate mapping
            
        Returns:
            dict: Detection results with optional canvas_landmarks field
        """
        try:
            if frame is None or frame.size == 0:
                logger.warning(f"Frame {frame_number}: Invalid frame (None or empty)")
                return None
            
            # Check frame dimensions for MediaPipe compatibility
            if len(frame.shape) != 3 or frame.shape[2] != 3:
                logger.warning(f"Frame {frame_number}: Invalid frame shape {frame.shape}, expected (H,W,3)")
                return None
                
            if frame.shape[0] < 10 or frame.shape[1] < 10:
                logger.warning(f"Frame {frame_number}: Frame too small {frame.shape[:2]}, may not contain detectable hands")
                return None
                
            # Convert BGR to RGB - exact same as hand_detection.py
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame with MediaPipe - exact same logic
            results = self.hands.process(rgb_frame)
            
            if not results.multi_hand_landmarks:
                logger.debug(f"Frame {frame_number}: No hands detected by MediaPipe in ROI frame {frame.shape[:2]}")
                return None
                
            # Extract detection data - same structure as original
            hands_detected = len(results.multi_hand_landmarks)
            landmarks_list = []
            bounding_boxes = []
            hand_labels = []
            confidences = []
            
            for idx, (hand_landmarks, hand_classification) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness or [])
            ):
                # Extract landmarks - same processing
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
                    x_coords.append(landmark.x)
                    y_coords.append(landmark.y)
                
                landmarks_list.append(landmarks)
                
                # Calculate bounding box
                if x_coords and y_coords:
                    bbox = {
                        'x_min': min(x_coords),
                        'y_min': min(y_coords),
                        'x_max': max(x_coords),
                        'y_max': max(y_coords),
                        'width': max(x_coords) - min(x_coords),
                        'height': max(y_coords) - min(y_coords)
                    }
                    bounding_boxes.append(bbox)
                
                # Get hand label and confidence
                if hand_classification and hasattr(hand_classification, 'classification'):
                    classification = hand_classification.classification[0]
                    hand_labels.append(classification.label)
                    confidences.append(classification.score)
                else:
                    hand_labels.append("Unknown")
                    confidences.append(0.0)
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Create base response
            result = {
                'timestamp': time.time(),
                'frame_number': frame_number,
                'hands_detected': hands_detected,
                'confidence': avg_confidence,
                'landmarks': landmarks_list,
                'bounding_boxes': bounding_boxes,
                'hand_labels': hand_labels
            }
            
            # Add canvas_landmarks if mapping parameters provided
            if roi_offset and video_dims and canvas_dims:
                try:
                    # Convert landmarks to format expected by LandmarkMapper
                    mapper_landmarks = []
                    for hand_landmarks in landmarks_list:
                        hand_data = []
                        for landmark in hand_landmarks:
                            hand_data.append({
                                'x': landmark.x,
                                'y': landmark.y,
                                'z': landmark.z
                            })
                        mapper_landmarks.append(hand_data)
                    
                    # Create mapping objects
                    roi = ROIConfig(
                        x=roi_offset['x'],
                        y=roi_offset['y'],
                        w=roi_offset['w'],
                        h=roi_offset['h']
                    )
                    video_dimensions = VideoDimensions(
                        width=video_dims['width'],
                        height=video_dims['height']
                    )
                    canvas_dimensions = CanvasDimensions(
                        width=canvas_dims['width'],
                        height=canvas_dims['height']
                    )
                    
                    # Generate canvas landmarks with fixed sizing
                    canvas_response = LandmarkMapper.create_canvas_landmarks_response(
                        mapper_landmarks, roi, video_dimensions, canvas_dimensions
                    )
                    
                    if canvas_response['success']:
                        result['canvas_landmarks'] = canvas_response['canvas_landmarks']
                        result['fixed_sizes'] = canvas_response['fixed_sizes']
                        result['mapping_algorithm'] = 'fixed_size_mapping'
                        
                        # Debug: Log first landmark coordinate verification
                        if canvas_response['canvas_landmarks'] and len(canvas_response['canvas_landmarks']) > 0:
                            first_hand = canvas_response['canvas_landmarks'][0]
                            if len(first_hand) > 0:
                                first_landmark = first_hand[0]
                                logger.debug(f"🔍 Coordinate Verification - First landmark:")
                                logger.debug(f"  ROI-relative: ({first_landmark.get('x_rel', 0):.3f}, {first_landmark.get('y_rel', 0):.3f})")
                                logger.debug(f"  Video pixel (TC Gốc): ({first_landmark.get('x_orig', 0):.1f}, {first_landmark.get('y_orig', 0):.1f})")
                                logger.debug(f"  Canvas display: ({first_landmark.get('x_disp', 0):.1f}, {first_landmark.get('y_disp', 0):.1f})")
                                logger.debug(f"  Video size: {video_dims['width']}x{video_dims['height']}, Canvas: {canvas_dims['width']}x{canvas_dims['height']}")
                    else:
                        logger.warning(f"Canvas landmark mapping failed: {canvas_response.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error generating canvas landmarks: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in detect_hands_in_frame: {str(e)}")
            return None

    def detect_hands_streaming(self, 
                             video_path: str, 
                             roi: Dict[str, int], 
                             detection_callback: Callable[[Dict[str, Any]], None],
                             stop_event = None) -> Dict[str, Any]:
        """
        Stream hand detection results for web interface
        Adapted from detect_hands() function in hand_detection.py
        
        Args:
            video_path: Path to video file
            roi: ROI coordinates {'x': int, 'y': int, 'w': int, 'h': int}
            detection_callback: Callback function for streaming results
            stop_event: Threading event to stop processing
            
        Returns:
            dict: Final processing results
        """
        try:
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            if w <= 0 or h <= 0:
                logger.error("ROI không hợp lệ (chiều rộng hoặc chiều cao bằng 0).")
                return {"success": False, "hand_detected": False, "error": "ROI không hợp lệ."}

            # Mở video - same as original
            logger.debug(f"Opening video for hand detection: {video_path}")
            cap = cv2.VideoCapture(video_path)
            
            try:
                if not cap.isOpened():
                    logger.error("Không thể mở video.")
                    return {"success": False, "hand_detected": False, "error": "Không thể mở video."}

                frame_count = 0
                start_time = time.time()
                hand_detected = False
                total_detections = 0

                while cap.isOpened():
                    # Check stop event if provided
                    if stop_event and stop_event.is_set():
                        logger.info("Stop event received, ending detection")
                        break
                        
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Get frame dimensions first for ROI bounds checking
                    frame_height, frame_width = frame.shape[:2]
                    
                    # Apply ROI bounds checking - CRITICAL FIX!
                    # Same logic as hand_detection.py to prevent out of bounds errors
                    x_safe = max(0, min(x, frame_width - 1))
                    y_safe = max(0, min(y, frame_height - 1))
                    w_safe = max(1, min(w, frame_width - x_safe))
                    h_safe = max(1, min(h, frame_height - y_safe))
                    
                    # Cắt video theo ROI với bounds checking
                    roi_frame = frame[y_safe:y_safe+h_safe, x_safe:x_safe+w_safe]

                    # Chỉ xử lý mỗi FRAME_STEP frame - EXACT SAME LOGIC as hand_detection.py
                    if frame_count % FRAME_STEP == 0:
                        
                        # Debug logging for coordinate accuracy verification
                        logger.debug(f"Frame {frame_count}: Video dimensions {frame_width}x{frame_height}, "
                                   f"ROI original: ({x},{y},{w},{h}) → ROI safe: ({x_safe},{y_safe},{w_safe},{h_safe}), "
                                   f"Scale factors: X={960/frame_width:.3f}, Y={540/frame_height:.3f}")
                        
                        # Detect hands using our streaming method with coordinate mapping
                        # IMPORTANT: Use safe coordinates for accurate mapping
                        detection_result = self.detect_hands_in_frame(
                            roi_frame, 
                            frame_count,
                            roi_offset={'x': x_safe, 'y': y_safe, 'w': w_safe, 'h': h_safe},
                            video_dims={'width': frame_width, 'height': frame_height},
                            canvas_dims={'width': 960, 'height': 540}  # Default canvas size
                        )
                        
                        if detection_result:
                            hand_detected = True
                            total_detections += 1
                            
                            # Add ROI offset to landmarks for absolute coordinates
                            adjusted_result = detection_result.copy()
                            adjusted_result['roi_offset'] = {'x': x, 'y': y, 'w': w, 'h': h}
                            adjusted_result['elapsed_time'] = time.time() - start_time
                            
                            # Stream result via callback
                            detection_callback(adjusted_result)
                            
                            logger.debug(f"Hand detected at frame {frame_count}, confidence: {detection_result['confidence']:.2f}")

                    frame_count += 1

                elapsed_time = time.time() - start_time
                logger.debug(f"Detection completed: {total_detections} detections in {elapsed_time:.2f}s, hand_detected: {hand_detected}")
                
                return {
                    "success": True, 
                    "hand_detected": hand_detected,
                    "total_detections": total_detections,
                    "total_frames": frame_count,
                    "elapsed_time": elapsed_time
                }
        
            finally:
                cap.release()
                logger.debug("Released video capture resources")
    
        except Exception as e:
            logger.error(f"Error in detect_hands_streaming: {str(e)}")
            return {"success": False, "hand_detected": False, "error": f"Lỗi hệ thống: {str(e)}"}
    
    def close(self):
        """Clean up MediaPipe resources"""
        if hasattr(self, 'hands') and self.hands:
            self.hands.close()
            logger.debug("MediaPipe Hands resources cleaned up")


# Convenience function for compatibility
def create_web_detector(detection_confidence: float = 0.5,
                       tracking_confidence: float = 0.5,
                       max_num_hands: int = 2) -> HandDetectionWeb:
    """
    Factory function to create HandDetectionWeb instance
    Uses exact same default parameters as hand_detection.py
    """
    return HandDetectionWeb(
        detection_confidence=detection_confidence,
        tracking_confidence=tracking_confidence,
        max_num_hands=max_num_hands
    )


if __name__ == "__main__":
    # Test script for debugging
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 hand_detection_web.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    test_roi = {"x": 100, "y": 100, "w": 400, "h": 300}
    
    detector = create_web_detector()
    
    def test_callback(detection_data):
        print(f"Detection: Frame {detection_data['frame_number']}, "
              f"Hands: {detection_data['hands_detected']}, "
              f"Confidence: {detection_data['confidence']:.2f}")
    
    try:
        result = detector.detect_hands_streaming(video_path, test_roi, test_callback)
        print(f"Final result: {result}")
    finally:
        detector.close()