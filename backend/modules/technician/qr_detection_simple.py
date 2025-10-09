"""
Simple QR Detection Module
Reuse WeChat QRCode model for frame-by-frame QR detection
Integrated with hand detection pipeline
"""

import cv2
import os
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)

# WeChat QRCode model paths (reuse existing)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_DIR = os.path.join(BASE_DIR, "models", "wechat_qr")
DETECT_PROTO = os.path.join(MODEL_DIR, "detect.prototxt")
DETECT_MODEL = os.path.join(MODEL_DIR, "detect.caffemodel")
SR_PROTO = os.path.join(MODEL_DIR, "sr.prototxt")
SR_MODEL = os.path.join(MODEL_DIR, "sr.caffemodel")

class QRDetector:
    """Simple QR detector using WeChat model"""
    
    def __init__(self):
        self.detector = None
        self._initialize_detector()
    
    def _initialize_detector(self):
        """Initialize WeChat QRCode detector"""
        try:
            # Check model files exist
            for model_file in [DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL]:
                if not os.path.exists(model_file):
                    logger.error(f"QR model file not found: {model_file}")
                    return False
            
            # Initialize detector
            self.detector = cv2.wechat_qrcode_WeChatQRCode(
                DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL
            )
            logger.info("WeChat QRCode detector initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize QR detector: {e}")
            return False
    
    def detect_qr_in_frame(self, frame: np.ndarray, roi_config: Optional[Dict] = None) -> List[Dict]:
        """
        Detect QR codes in frame
        
        Args:
            frame: Input video frame
            roi_config: Optional ROI to limit detection area
            
        Returns:
            List of QR detections with bbox and decoded text
        """
        if self.detector is None:
            return []
        
        try:
            # Apply ROI if specified
            if roi_config:
                x, y, w, h = roi_config['x'], roi_config['y'], roi_config['w'], roi_config['h']
                # Ensure ROI is within frame bounds
                frame_h, frame_w = frame.shape[:2]
                x = max(0, min(x, frame_w - 1))
                y = max(0, min(y, frame_h - 1))
                w = max(1, min(w, frame_w - x))
                h = max(1, min(h, frame_h - y))
                
                roi_frame = frame[y:y+h, x:x+w]
                offset_x, offset_y = x, y
            else:
                roi_frame = frame
                offset_x, offset_y = 0, 0
            
            # Detect QR codes
            texts, points = self.detector.detectAndDecode(roi_frame)
            
            detections = []
            for text, box in zip(texts, points):
                if text:  # Only include valid decoded QR codes
                    # Convert points to bbox format
                    box_array = np.array(box, dtype=np.int32)
                    x_min = int(np.min(box_array[:, 0])) + offset_x
                    y_min = int(np.min(box_array[:, 1])) + offset_y
                    x_max = int(np.max(box_array[:, 0])) + offset_x
                    y_max = int(np.max(box_array[:, 1])) + offset_y
                    
                    detection = {
                        'bbox': {
                            'x': x_min,
                            'y': y_min,
                            'w': x_max - x_min,
                            'h': y_max - y_min
                        },
                        'decoded_text': text,
                        'confidence': 1.0,  # WeChat detector doesn't provide confidence
                        'points': box_array.tolist()  # Raw corner points
                    }
                    detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"QR detection error: {e}")
            return []

# Global detector instance
_qr_detector = None

def get_qr_detector() -> QRDetector:
    """Get global QR detector instance"""
    global _qr_detector
    if _qr_detector is None:
        _qr_detector = QRDetector()
    return _qr_detector

def detect_qr_at_time(video_path: str, time_seconds: float, roi_config: Optional[Dict] = None) -> Dict:
    """
    Detect QR codes at specific video time
    Compatible with hand detection pipeline
    
    Args:
        video_path: Path to video file
        time_seconds: Time in seconds
        roi_config: Optional ROI configuration
        
    Returns:
        Detection result dict
    """
    try:
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                'success': False,
                'error': f'Cannot open video: {video_path}'
            }
        
        # Seek to time
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(time_seconds * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        # Read frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return {
                'success': False,
                'error': 'Cannot read frame at specified time'
            }
        
        # Detect QR codes
        detector = get_qr_detector()
        detections = detector.detect_qr_in_frame(frame, roi_config)
        
        return {
            'success': True,
            'qr_detections': detections,
            'frame_number': frame_number,
            'video_time': time_seconds,
            'qr_count': len(detections)
        }
        
    except Exception as e:
        logger.error(f"QR detection at time error: {e}")
        return {
            'success': False,
            'error': str(e)
        }
