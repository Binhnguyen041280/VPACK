import cv2
import mediapipe as mp
import time
import logging
import json
import os
import glob
from datetime import datetime
from typing import Dict, Any, Optional

# Define BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Use var/logs for application logs
from modules.path_utils import get_logs_dir
log_dir = get_logs_dir()
log_file_path = os.path.join(log_dir, f"hand_detection_{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Type-safe MediaPipe imports
try:
    mp_hands = mp.solutions.hands  # type: ignore
    mp_drawing = mp.solutions.drawing_utils  # type: ignore
except AttributeError as e:
    logging.error(f"MediaPipe import error: {e}")
    raise ImportError("MediaPipe modules not found. Please reinstall MediaPipe.")

# Set frame step
FRAME_STEP = 5

# Path for saving images
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "CameraROI")

def ensure_directory_exists(directory):
    """Ensure directory exists, create if not."""
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.debug(f"Created directory: {directory}")
        # Check access permissions
        if not os.access(directory, os.W_OK):
            logging.error(f"No write permission for directory {directory}")
            raise PermissionError(f"No write permission for directory {directory}")
    except Exception as e:
        logging.error(f"Error creating directory {directory}: {str(e)}")
        raise

def select_roi(video_path: str, camera_id: str, step: str = "packing") -> Dict[str, Any]:
    """
    Open video and allow user to draw ROI using OpenCV, save results to CameraROI, then detect hands.
    Args:
        video_path (str): Path to video file.
        camera_id (str): Camera ID.
        step (str): Current stage (packing, trigger).
    Returns:
        dict: {'success': bool, 'roi': {'x': int, 'y': int, 'w': int, 'h': int}, 'roi_frame': str, 'hand_detected': bool} or {'success': false, 'error': str}
    """
    try:
        logging.debug(f"Starting select_roi with video_path: {video_path}, camera_id: {camera_id}, step: {step}")
        
        # Ensure CameraROI directory exists
        ensure_directory_exists(CAMERA_ROI_DIR)

        # Open video
        logging.debug("Opening video...")
        cap = cv2.VideoCapture(video_path)
        try:
            if not cap.isOpened():
                logging.error("Cannot open video.")
                return {"success": False, "error": "Cannot open video."}

            # Read first frame
            logging.debug("Reading first frame...")
            ret, frame = cap.read()
            if not ret:
                logging.error("Cannot read frame from video.")
                return {"success": False, "error": "Cannot read frame from video."}

            # Save original frame if in packing step
            if step == "packing":
                original_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_original.jpg")
                ret = cv2.imwrite(original_frame_path, frame)
                if not ret:
                    logging.error(f"Cannot save original image at: {original_frame_path}")
                    return {"success": False, "error": f"Cannot save original image at {original_frame_path}"}
                logging.debug(f"Saved original frame to: {original_frame_path}")
            
            while True:
                # Display ROI selection interface
                logging.debug("Calling cv2.selectROI...")
                current_frame = frame.copy()
                roi = cv2.selectROI(f"Click and drag mouse to select -{step.capitalize()} Area-", current_frame, showCrosshair=True, fromCenter=False)
                logging.debug(f"ROI returned: {roi}")
                cv2.destroyAllWindows()

                # Check if ROI is valid
                x, y, w, h = map(int, roi)
                if w == 0 or h == 0:
                    logging.debug("ROI is invalid, redisplaying original frame to redraw.")
                    continue  # Redisplay original frame, do not save file
                
                # ✅ CLAMP ROI WITHIN VIDEO FRAME - Clamp ROI to frame boundaries
                frame_height, frame_width = frame.shape[:2]
                
                # Clamp coordinates to frame boundaries
                x_clamped = max(0, min(x, frame_width - 1))
                y_clamped = max(0, min(y, frame_height - 1))
                
                # Adjust width and height to stay within frame
                w_clamped = max(1, min(w, frame_width - x_clamped))
                h_clamped = max(1, min(h, frame_height - y_clamped))
                
                # Update ROI values if clamping occurred
                if x != x_clamped or y != y_clamped or w != w_clamped or h != h_clamped:
                    logging.info(f"ROI adjusted to fit within video frame:")
                    logging.info(f"  Original: x={x}, y={y}, w={w}, h={h}")
                    logging.info(f"  Adjusted: x={x_clamped}, y={y_clamped}, w={w_clamped}, h={h_clamped}")
                    logging.info(f"  Video frame: {frame_width}x{frame_height}")
                    
                    # Update variables with clamped values
                    x, y, w, h = x_clamped, y_clamped, w_clamped, h_clamped
                
                # Draw ROI on frame
                color = (0, 255, 0) if step == "packing" else (0, 255, 255)
                cv2.rectangle(current_frame, (x, y), (x + w, y + h), color, 2)
                # Add "Packing" label if in packing step
                if step == "packing":
                    cv2.putText(current_frame, "Packing", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Display frame with ROI and title
                cv2.namedWindow("**** Packing Area Drawn ****", cv2.WINDOW_NORMAL)
                cv2.imshow("**** Packing Area Drawn ****", current_frame)
                cv2.waitKey(500)
                cv2.destroyAllWindows()
                
                # Save frame with ROI to CameraROI
                if step == "packing":
                    roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_packing.jpg")
                else:  # step == "trigger"
                    roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_trigger.jpg")
                
                ret = cv2.imwrite(roi_frame_path, current_frame)
                if not ret:
                    logging.error(f"Cannot save image at: {roi_frame_path}")
                    return {"success": False, "error": f"Cannot save image at {roi_frame_path}"}
                logging.debug(f"Saved frame with ROI to: {roi_frame_path}")

                # Check if file was saved successfully
                if not os.path.exists(roi_frame_path):
                    logging.error(f"File does not exist after saving: {roi_frame_path}")
                    return {"success": False, "error": f"File does not exist after saving: {roi_frame_path}"}
                
                # If packing step, call detect_hands to check for hands
                hand_detected = False
                if step == "packing":
                    detect_result = detect_hands(video_path, {"x": x, "y": y, "w": w, "h": h})
                    if not detect_result["success"]:
                        logging.error(f"Error detecting hand: {detect_result['error']}")
                        return {"success": False, "error": detect_result["error"]}
                    hand_detected = detect_result["hand_detected"]
                
                # Save ROI coordinates and hand_detected status to /tmp/roi.json
                result = {
                    "success": True,
                    "roi": {"x": x, "y": y, "w": w, "h": h},
                    "roi_frame": os.path.relpath(roi_frame_path, BASE_DIR),
                    "hand_detected": hand_detected
                }
                logging.debug(f"Saving ROI to /tmp/roi.json: {result}")
                with open("/tmp/roi.json", "w") as f:
                    json.dump(result, f)

                logging.debug(f"Valid ROI: x={x}, y={y}, w={w}, h={h}, hand_detected: {hand_detected}")
                return result
            
        finally:
            cap.release()
            logging.debug("Released video resources (cap.release).")

    except Exception as e:
        logging.error(f"Error in select_roi: {str(e)}")
        cv2.destroyAllWindows()
        return {"success": False, "error": f"System error: {str(e)}"}

def detect_hands(video_path: str, roi: Dict[str, int]) -> Dict[str, Any]:
    """
    Display video with hand detection in ROI area, return hand detection status.
    Args:
        video_path (str): Path to video file.
        roi (dict): ROI coordinates {'x': int, 'y': int, 'w': int, 'h': int}.
    Returns:
        dict: {'success': bool, 'hand_detected': bool, 'error': str if error}
    """
    try:
        x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
        if w <= 0 or h <= 0:
            logging.error("Invalid ROI (width or height is zero).")
            return {"success": False, "hand_detected": False, "error": "Invalid ROI."}

        # Open video
        logging.debug("Opening video for hand detection...")
        cap = cv2.VideoCapture(video_path)
        
        # Initialize MediaPipe Hands with explicit parameters
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        try:
            if not cap.isOpened():
                logging.error("Cannot open video.")
                return {"success": False, "hand_detected": False, "error": "Cannot open video."}

            frame_count = 0
            start_time = time.time()
            hand_detected = False

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Crop video by ROI
                roi_frame = frame[y:y+h, x:x+w]

                # Process only every FRAME_STEP frame
                if frame_count % FRAME_STEP == 0:
                    # Convert BGR to RGB
                    rgb_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)

                    # Detect hands
                    results = hands.process(rgb_frame)

                    # Check and confirm hand detection
                    if results.multi_hand_landmarks:
                        hand_detected = True
                        for hand_landmarks in results.multi_hand_landmarks:
                            # Draw keypoints when hand is detected
                            mp_drawing.draw_landmarks(
                                roi_frame, 
                                hand_landmarks, 
                                mp_hands.HAND_CONNECTIONS
                            )

                # Display video
                elapsed_time = time.time() - start_time
                cv2.putText(roi_frame, f"Time: {elapsed_time:.2f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("ROI Hand Detection", roi_frame)

                if cv2.waitKey(1) == ord("q"):
                    break

                frame_count += 1

            logging.debug(f"Hand detected: {hand_detected}")
            return {"success": True, "hand_detected": hand_detected}

        finally:
            hands.close()
            cap.release()
            cv2.destroyWindow("ROI Hand Detection")
            logging.debug("Released video resources (cap.release) in detect_hands.")

    except Exception as e:
        logging.error(f"Error in detect_hands: {str(e)}")
        return {"success": False, "hand_detected": False, "error": f"System error: {str(e)}"}

def finalize_roi(video_path: str, camera_id: str, rois: list) -> Dict[str, Any]:
    """
    Draw all ROI areas (packing, MVD, trigger) on frame and save to CameraROI folder.
    Args:
        video_path (str): Path to video file.
        camera_id (str): Camera ID.
        rois (list): List of ROI areas [{'type': str, 'x': int, 'y': int, 'w': int, 'h': int}, ...].
    Returns:
        dict: {'success': bool, 'final_roi_frame': str, 'error': str if error}
    """
    try:
        # Ensure CameraROI directory exists
        ensure_directory_exists(CAMERA_ROI_DIR)

        # Open video and get first frame
        logging.debug("Opening video to create composite image...")
        cap = cv2.VideoCapture(video_path)
        try:
            if not cap.isOpened():
                logging.error("Cannot open video.")
                return {"success": False, "error": "Cannot open video."}

            ret, frame = cap.read()
            if not ret:
                logging.error("Cannot read frame from video.")
                return {"success": False, "error": "Cannot read frame from video."}

            # Draw ROI areas with different colors
            for roi in rois:
                x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
                roi_type = roi["type"]

                # Define color for each ROI type
                if roi_type == "packing":
                    color = (0, 255, 0)  # Green
                elif roi_type == "mvd":
                    color = (0, 0, 255)  # Red
                elif roi_type == "trigger":
                    color = (0, 255, 255)  # Yellow
                else:
                    color = (255, 255, 255)  # White (default)

                # Draw ROI on frame
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                # Add label for ROI area
                cv2.putText(frame, roi_type.upper(), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            # Create filename with timestamp and camera_id
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_final_{timestamp}.jpg")

            # Save composite image
            ret = cv2.imwrite(final_roi_frame_path, frame)
            if not ret:
                logging.error(f"Cannot save composite image at: {final_roi_frame_path}")
                return {"success": False, "error": f"Cannot save composite image at {final_roi_frame_path}"}
            logging.debug(f"Saved composite image with all ROIs to: {final_roi_frame_path}")

            return {"success": True, "final_roi_frame": os.path.relpath(final_roi_frame_path, BASE_DIR)}
        
        finally:
            cap.release()
            logging.debug("Released video resources (cap.release) in finalize_roi.")

    except Exception as e:
        logging.error(f"Error in finalize_roi: {str(e)}")
        return {"success": False, "error": f"System error: {str(e)}"}

def detect_hands_at_time(video_path: str, time_seconds: float, roi_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Detect hands at specific time in video for web interface
    Based on the simple pattern from 2hand_detection.py
    
    Args:
        video_path (str): Path to video file
        time_seconds (float): Video time in seconds 
        roi_config (dict, optional): ROI configuration {'x': int, 'y': int, 'w': int, 'h': int}
        
    Returns:
        dict: {
            'success': bool,
            'landmarks': list,  # Hand landmarks in normalized coordinates  
            'confidence': float,
            'frame_number': int,
            'video_time': float,
            'hands_detected': int,
            'error': str (if error)
        }
    """
    try:
        logging.debug(f"Detecting hands at time {time_seconds}s in {video_path}")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                "success": False,
                "error": "Cannot open video file"
            }
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # Default FPS
                
            # Calculate frame number from time
            frame_number = int(time_seconds * fps)
            
            # Set video position to specific frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if not ret:
                return {
                    "success": False, 
                    "error": f"Cannot read frame at time {time_seconds}s"
                }
            
            # Apply ROI if provided
            if roi_config:
                x, y, w, h = roi_config["x"], roi_config["y"], roi_config["w"], roi_config["h"]
                # Ensure ROI is within frame bounds
                frame_height, frame_width = frame.shape[:2]
                x = max(0, min(x, frame_width - 1))
                y = max(0, min(y, frame_height - 1))
                w = max(1, min(w, frame_width - x))
                h = max(1, min(h, frame_height - y))
                
                roi_frame = frame[y:y+h, x:x+w]
            else:
                roi_frame = frame
                x, y = 0, 0
            
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)
            
            # Initialize MediaPipe Hands
            with mp_hands.Hands(
                static_image_mode=True,  # Process single image
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            ) as hands:
                
                # Process frame
                results = hands.process(rgb_frame)
                
                # Extract landmarks
                landmarks_list = []
                hands_detected = 0
                confidence_scores = []
                
                if results.multi_hand_landmarks:
                    hands_detected = len(results.multi_hand_landmarks)
                    
                    for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                        hand_points = []
                        
                        # Extract landmarks with TC Gốc coordinate transformation
                        for landmark in hand_landmarks.landmark:
                            if roi_config:
                                # ✅ CLAMP MEDIAPIPE COORDINATES - Prevent landmarks outside ROI from causing invalid coordinates
                                landmark_x_clamped = max(0.0, min(1.0, landmark.x))
                                landmark_y_clamped = max(0.0, min(1.0, landmark.y))
                                
                                # Step 2: MediaPipe runs on ROI - transform to TC Gốc (pixel thực)
                                x_orig = x + landmark_x_clamped * w  # Pixel thực trong video gốc
                                y_orig = y + landmark_y_clamped * h  # Pixel thực trong video gốc
                                
                                # ✅ FINAL BOUNDARY CHECK - Ensure coordinates stay within video frame
                                x_orig = max(0, min(frame.shape[1] - 1, x_orig))
                                y_orig = max(0, min(frame.shape[0] - 1, y_orig))
                                
                                # Calculate normalized coordinates for reference
                                full_x_norm = x_orig / frame.shape[1]
                                full_y_norm = y_orig / frame.shape[0]
                            else:
                                # Full frame processing
                                x_orig = landmark.x * frame.shape[1]  # Convert to pixel coordinates
                                y_orig = landmark.y * frame.shape[0]
                                full_x_norm = landmark.x
                                full_y_norm = landmark.y
                            
                            hand_points.append({
                                'x': landmark.x,      # ROI-relative coordinates
                                'y': landmark.y,
                                'z': landmark.z,
                                'x_orig': x_orig,     # TC Gốc - pixel thực trong video gốc
                                'y_orig': y_orig,     # TC Gốc - pixel thực trong video gốc
                                'x_norm': full_x_norm,  # Reference normalized coordinates
                                'y_norm': full_y_norm   # Reference normalized coordinates
                            })
                        
                        landmarks_list.append(hand_points)
                        
                        # Get confidence from handedness if available
                        if results.multi_handedness and idx < len(results.multi_handedness):
                            confidence = results.multi_handedness[idx].classification[0].score
                            confidence_scores.append(confidence)
                        else:
                            confidence_scores.append(0.85)  # Default confidence
                
                # Calculate overall confidence
                overall_confidence = float(sum(confidence_scores) / len(confidence_scores)) if confidence_scores else 0.0
                
                logging.debug(f"Hand detection complete: {hands_detected} hands detected, confidence: {overall_confidence:.2f}")
                
                return {
                    "success": True,
                    "landmarks": landmarks_list,
                    "confidence": overall_confidence,
                    "frame_number": frame_number,
                    "video_time": time_seconds,
                    "hands_detected": hands_detected,
                    "roi_applied": roi_config is not None,
                    "roi_config": roi_config
                }
                
        finally:
            cap.release()
            
    except Exception as e:
        error_msg = f"Error in hand detection at time {time_seconds}s: {str(e)}"
        logging.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

def preprocess_video_hands(video_path: str, roi_config: Dict[str, Any], fps: int = 5, progress_callback=None) -> Dict[str, Any]:
    """
    Pre-process entire video for hand detection at specified fps
    Cache results for perfect synchronization during playback
    
    Args:
        video_path (str): Path to video file
        roi_config (dict): ROI configuration {'x': int, 'y': int, 'w': int, 'h': int}
        fps (int): Detection fps (default 5fps = every 0.2s)
        progress_callback (callable): Function to call with progress updates
        
    Returns:
        dict: {
            'success': bool,
            'detections': [{'timestamp': float, 'landmarks': list, 'confidence': float}],
            'metadata': dict,
            'total_frames_processed': int,
            'error': str (if error)
        }
    """
    try:
        logging.info(f"Pre-processing video {video_path} at {fps}fps with ROI {roi_config}")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                "success": False,
                "error": "Cannot open video file"
            }
        
        try:
            # Get video properties
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            if video_fps <= 0:
                video_fps = 30.0  # Default FPS
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / video_fps
            
            # Calculate frame intervals for target fps
            frame_interval = max(1, int(video_fps / fps))  # Every N frames
            processing_timestamps = []
            
            # Generate timestamps for processing (every 1/fps seconds)
            current_time = 0.0
            while current_time <= duration:
                processing_timestamps.append(current_time)
                current_time += 1.0 / fps
            
            logging.info(f"Will process {len(processing_timestamps)} frames at {fps}fps for {duration:.1f}s video")
            
            # ROI bounds validation
            x, y, w, h = roi_config["x"], roi_config["y"], roi_config["w"], roi_config["h"]
            
            # Initialize MediaPipe Hands
            detections = []
            processed_count = 0
            
            with mp_hands.Hands(
                static_image_mode=True,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            ) as hands:
                
                for idx, timestamp in enumerate(processing_timestamps):
                    try:
                        # ✅ CHECK CANCELLATION DIRECTLY - NO DEPENDENCY ON PROGRESS CALLBACK
                        # Check if this processing job has been cancelled
                        try:
                            from blueprints.simple_hand_detection_bp import preprocessing_progress
                            # Generate cache key to check status (same logic as in blueprint)
                            import hashlib
                            roi_str = f"{roi_config['x']}_{roi_config['y']}_{roi_config['w']}_{roi_config['h']}"
                            cache_input = f"{video_path}_{roi_str}"
                            cache_key = hashlib.md5(cache_input.encode()).hexdigest()
                            
                            if (cache_key in preprocessing_progress and 
                                preprocessing_progress[cache_key].get('cancelled', False)):
                                logging.info(f"HAND CANCELLATION DETECTED at frame {idx+1}/{len(processing_timestamps)} - FORCING SKIP TO END")
                                
                                # ✅ FORCE SKIP TO LAST FRAME STRATEGY
                                # Process only last 3 timestamps to finish quickly
                                remaining_timestamps = processing_timestamps[max(0, len(processing_timestamps) - 3):]
                                logging.info(f"Fast-finishing hand detection with last {len(remaining_timestamps)} frames")
                                
                                for final_timestamp in remaining_timestamps:
                                    try:
                                        frame_number = int(final_timestamp * video_fps)
                                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                                        ret, frame = cap.read()
                                        
                                        if ret:
                                            # Quick processing for final frames
                                            frame_height, frame_width = frame.shape[:2]
                                            x_safe = max(0, min(x, frame_width - 1))
                                            y_safe = max(0, min(y, frame_height - 1))
                                            w_safe = max(1, min(w, frame_width - x_safe))
                                            h_safe = max(1, min(h, frame_height - y_safe))
                                                
                                            roi_frame = frame[y_safe:y_safe+h_safe, x_safe:x_safe+w_safe]
                                            rgb_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)
                                            results = hands.process(rgb_frame)
                                                
                                            # Add detection if hands found
                                            if results.multi_hand_landmarks:
                                                landmarks_list = []
                                                for hand_landmarks in results.multi_hand_landmarks:
                                                    hand_points = []
                                                    for landmark in hand_landmarks.landmark:
                                                        hand_points.append({
                                                            'x': landmark.x,
                                                            'y': landmark.y,
                                                            'z': landmark.z,
                                                            'x_orig': x_safe + landmark.x * w_safe,
                                                            'y_orig': y_safe + landmark.y * h_safe
                                                        })
                                                    landmarks_list.append(hand_points)
                                                
                                                detections.append({
                                                    'timestamp': round(final_timestamp, 2),
                                                    'landmarks': landmarks_list,
                                                    'confidence': 0.85,
                                                    'hands_detected': len(landmarks_list)
                                                })
                                        
                                        processed_count += 1
                                    except:
                                        processed_count += 1
                                        continue
                                
                                logging.info(f"Fast finish completed - processed {processed_count}/{len(processing_timestamps)} frames")
                                break  # Exit main loop
                        except Exception as e:
                            logging.warning(f"Could not check cancellation: {e}")
                        
                        # Calculate frame number for this timestamp
                        frame_number = int(timestamp * video_fps)
                        
                        # Set video position
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                        ret, frame = cap.read()
                        
                        if not ret:
                            logging.warning(f"Cannot read frame at timestamp {timestamp}")
                            continue
                            
                        # Apply ROI
                        frame_height, frame_width = frame.shape[:2]
                        x_safe = max(0, min(x, frame_width - 1))
                        y_safe = max(0, min(y, frame_height - 1))
                        w_safe = max(1, min(w, frame_width - x_safe))
                        h_safe = max(1, min(h, frame_height - y_safe))
                        
                        roi_frame = frame[y_safe:y_safe+h_safe, x_safe:x_safe+w_safe]
                        
                        # Convert to RGB for MediaPipe
                        rgb_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)
                        
                        # Process frame
                        results = hands.process(rgb_frame)
                        
                        # Extract landmarks if hands detected
                        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) > 0:
                            landmarks_list = []
                            confidence_scores = []
                            
                            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                                hand_points = []
                                
                                # Extract landmarks with TC Gốc coordinate transformation
                                for landmark_idx, landmark in enumerate(hand_landmarks.landmark):
                                    # ✅ CLAMP MEDIAPIPE COORDINATES - Prevent landmarks outside ROI from causing invalid coordinates
                                    landmark_x_clamped = max(0.0, min(1.0, landmark.x))
                                    landmark_y_clamped = max(0.0, min(1.0, landmark.y))
                                    
                                    # Step 2: MediaPipe runs on ROI - transform to TC Gốc (pixel thực)
                                    x_orig = x_safe + landmark_x_clamped * w_safe  # Pixel thực trong video gốc
                                    y_orig = y_safe + landmark_y_clamped * h_safe  # Pixel thực trong video gốc
                                    
                                    # ✅ FINAL BOUNDARY CHECK - Ensure coordinates stay within video frame
                                    x_orig = max(0, min(frame_width - 1, x_orig))
                                    y_orig = max(0, min(frame_height - 1, y_orig))
                                    
                                    # Calculate normalized coordinates for reference/debugging
                                    full_x_norm = x_orig / frame_width
                                    full_y_norm = y_orig / frame_height
                                    
                                    # Debug logging for first landmark of first hand
                                    if idx == 0 and landmark_idx == 0:
                                        logging.info(f"TC Gốc Backend Transform - Timestamp: {timestamp:.2f}s")
                                        logging.info(f"ROI_orig: x={x_safe}, y={y_safe}, w={w_safe}, h={h_safe}")
                                        logging.info(f"MediaPipe ROI coords: x={landmark.x:.3f}, y={landmark.y:.3f}")
                                        if landmark.x != landmark_x_clamped or landmark.y != landmark_y_clamped:
                                            logging.info(f"✅ CLAMPED MediaPipe coords: x={landmark_x_clamped:.3f}, y={landmark_y_clamped:.3f}")
                                        logging.info(f"TC Gốc pixel: x={x_orig:.1f}, y={y_orig:.1f}")
                                        logging.info(f"Video size: {frame_width}x{frame_height}")
                                        logging.info(f"Normalized reference: x={full_x_norm:.3f}, y={full_y_norm:.3f}")
                                    
                                    hand_points.append({
                                        'x': landmark.x,      # ROI-relative coordinates [0,1]
                                        'y': landmark.y,
                                        'z': landmark.z,
                                        'x_orig': x_orig,     # TC Gốc - pixel thực trong video gốc
                                        'y_orig': y_orig,     # TC Gốc - pixel thực trong video gốc
                                        'x_norm': full_x_norm,  # Reference normalized coordinates
                                        'y_norm': full_y_norm   # Reference normalized coordinates
                                    })
                                
                                landmarks_list.append(hand_points)
                                
                                # Get confidence from handedness if available
                                if results.multi_handedness and idx < len(results.multi_handedness):
                                    confidence = results.multi_handedness[idx].classification[0].score
                                    confidence_scores.append(confidence)
                                else:
                                    confidence_scores.append(0.85)  # Default confidence
                            
                            # Calculate overall confidence
                            overall_confidence = float(sum(confidence_scores) / len(confidence_scores))
                            
                            # Only add to detections if hands found
                            detections.append({
                                'timestamp': round(timestamp, 2),  # Round to 0.01s precision
                                'landmarks': landmarks_list,
                                'confidence': overall_confidence,
                                'hands_detected': len(landmarks_list)
                            })
                            
                            logging.debug(f"Timestamp {timestamp:.2f}s: {len(landmarks_list)} hands detected")
                        
                        processed_count += 1
                        
                        # Update progress callback every frame
                        progress = (processed_count / len(processing_timestamps)) * 100
                        
                        # Pass new detections to callback for progressive accumulation
                        new_detection = None
                        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) > 0:
                            # We just added a detection, pass it to callback
                            new_detection = [detections[-1]] if len(detections) > 0 else None
                        
                        if progress_callback:
                            if new_detection:
                                # Pass the single new detection for immediate accumulation
                                progress_callback(progress, processed_count, len(processing_timestamps), new_detection)
                            else:
                                # Update progress even if no detection found
                                progress_callback(progress, processed_count, len(processing_timestamps))
                        
                        # Log progress every 25 frames
                        if processed_count % 25 == 0:
                            total_detections_so_far = len(detections)
                            logging.info(f"Processing progress: {progress:.1f}% ({processed_count}/{len(processing_timestamps)} frames), Detections: {total_detections_so_far}")
                    
                    except Exception as e:
                        logging.warning(f"Error processing frame at {timestamp}s: {str(e)}")
                        continue
            
            # Final results
            logging.info(f"Pre-processing complete: {len(detections)} detections found in {processed_count} frames")
            
            return {
                "success": True,
                "detections": detections,
                "metadata": {
                    "video_path": video_path,
                    "duration": duration,
                    "total_frames": total_frames,
                    "video_fps": video_fps,
                    "detection_fps": fps,
                    "roi_config": roi_config,
                    "frames_processed": processed_count,
                    "hands_detected_count": len(detections)
                },
                "total_frames_processed": processed_count
            }
            
        finally:
            cap.release()
            
    except Exception as e:
        error_msg = f"Error in video pre-processing: {str(e)}"
        logging.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

if __name__ == "__main__":
    import sys
    # ✅ SUPPORT: Accept both 2 and 3 arguments, with optional step parameter
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python3 hand_detection.py <video_path> <camera_id> [step]")
        sys.exit(1)
    
    video_path = sys.argv[1]
    camera_id = sys.argv[2]
    step = sys.argv[3] if len(sys.argv) == 4 else "packing"  # Default to "packing"
    
    try:
        roi_result = select_roi(video_path, camera_id, step)
        if not roi_result["success"]:
            print(roi_result["error"])
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error running script: {str(e)}")
        print(f"Error running script: {str(e)}")
        sys.exit(1)