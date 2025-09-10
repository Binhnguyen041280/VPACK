import cv2
import mediapipe as mp
import time
import logging
import json
import os
import glob
from datetime import datetime
from typing import Dict, Any, Optional

# Định nghĩa BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Cấu hình logging (sử dụng cách cũ - không import modules.config.logging_config)
log_dir = os.path.join(BASE_DIR, "resources", "output_clips", "LOG")
os.makedirs(log_dir, exist_ok=True)
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

# Đặt bước nhảy frame
FRAME_STEP = 5

# Đường dẫn lưu ảnh
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "CameraROI")

def ensure_directory_exists(directory):
    """Đảm bảo thư mục tồn tại, nếu không thì tạo mới."""
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.debug(f"Đã tạo thư mục: {directory}")
        # Kiểm tra quyền truy cập
        if not os.access(directory, os.W_OK):
            logging.error(f"Không có quyền ghi vào thư mục {directory}")
            raise PermissionError(f"Không có quyền ghi vào thư mục {directory}")
    except Exception as e:
        logging.error(f"Lỗi khi tạo thư mục {directory}: {str(e)}")
        raise

def select_roi(video_path: str, camera_id: str, step: str = "packing") -> Dict[str, Any]:
    """
    Mở video và cho phép người dùng vẽ ROI bằng OpenCV, lưu kết quả vào CameraROI, sau đó phát hiện tay.
    Args:
        video_path (str): Đường dẫn đến file video.
        camera_id (str): ID của camera.
        step (str): Giai đoạn hiện tại (packing, trigger).
    Returns:
        dict: {'success': bool, 'roi': {'x': int, 'y': int, 'w': int, 'h': int}, 'roi_frame': str, 'hand_detected': bool} hoặc {'success': false, 'error': str}
    """
    try:
        logging.debug(f"Bắt đầu select_roi với video_path: {video_path}, camera_id: {camera_id}, step: {step}")
        
        # Đảm bảo thư mục CameraROI tồn tại
        ensure_directory_exists(CAMERA_ROI_DIR)

        # Mở video
        logging.debug("Đang mở video...")
        cap = cv2.VideoCapture(video_path)
        try:
            if not cap.isOpened():
                logging.error("Không thể mở video.")
                return {"success": False, "error": "Không thể mở video."}
            
            # Đọc frame đầu tiên
            logging.debug("Đang đọc frame đầu tiên...")
            ret, frame = cap.read()
            if not ret:
                logging.error("Không thể đọc frame từ video.")
                return {"success": False, "error": "Không thể đọc frame từ video."}
            
            # Lưu frame gốc nếu ở bước packing
            if step == "packing":
                original_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_original.jpg")
                ret = cv2.imwrite(original_frame_path, frame)
                if not ret:
                    logging.error(f"Không thể lưu ảnh gốc tại: {original_frame_path}")
                    return {"success": False, "error": f"Không thể lưu ảnh gốc tại {original_frame_path}"}
                logging.debug(f"Đã lưu frame gốc vào: {original_frame_path}")
            
            while True:
                # Hiển thị giao diện chọn ROI
                logging.debug("Gọi cv2.selectROI...")
                current_frame = frame.copy()
                roi = cv2.selectROI(f"Click va keo chuot de chon -Vung {step.capitalize()}-", current_frame, showCrosshair=True, fromCenter=False)
                logging.debug(f"ROI trả về: {roi}")
                cv2.destroyAllWindows()
                
                # Kiểm tra nếu ROI hợp lệ
                x, y, w, h = map(int, roi)
                if w == 0 or h == 0:
                    logging.debug("ROI không hợp lệ, hiển thị lại frame gốc để vẽ lại.")
                    continue  # Hiển thị lại frame gốc, không lưu file
                
                # ✅ GIỚI HẠN ROI TRONG KHUNG VIDEO - Clamp ROI to frame boundaries
                frame_height, frame_width = frame.shape[:2]
                
                # Clamp coordinates to frame boundaries
                x_clamped = max(0, min(x, frame_width - 1))
                y_clamped = max(0, min(y, frame_height - 1))
                
                # Adjust width and height to stay within frame
                w_clamped = max(1, min(w, frame_width - x_clamped))
                h_clamped = max(1, min(h, frame_height - y_clamped))
                
                # Update ROI values if clamping occurred
                if x != x_clamped or y != y_clamped or w != w_clamped or h != h_clamped:
                    logging.info(f"ROI được điều chỉnh để nằm trong khung video:")
                    logging.info(f"  Gốc: x={x}, y={y}, w={w}, h={h}")
                    logging.info(f"  Điều chỉnh: x={x_clamped}, y={y_clamped}, w={w_clamped}, h={h_clamped}")
                    logging.info(f"  Khung video: {frame_width}x{frame_height}")
                    
                    # Update variables with clamped values
                    x, y, w, h = x_clamped, y_clamped, w_clamped, h_clamped
                
                # Vẽ ROI lên frame
                color = (0, 255, 0) if step == "packing" else (0, 255, 255)
                cv2.rectangle(current_frame, (x, y), (x + w, y + h), color, 2)
                # Thêm tiêu đề "Packing" nếu ở bước packing
                if step == "packing":
                    cv2.putText(current_frame, "Packing", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Hiển thị frame với ROI và tiêu đề
                cv2.namedWindow("**** Da ve vung Packing ****", cv2.WINDOW_NORMAL)
                cv2.imshow("**** Da ve vung Packing ****", current_frame)
                cv2.waitKey(500)
                cv2.destroyAllWindows()
                
                # Lưu frame với ROI vào CameraROI
                if step == "packing":
                    roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_packing.jpg")
                else:  # step == "trigger"
                    roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_trigger.jpg")
                
                ret = cv2.imwrite(roi_frame_path, current_frame)
                if not ret:
                    logging.error(f"Không thể lưu ảnh tại: {roi_frame_path}")
                    return {"success": False, "error": f"Không thể lưu ảnh tại {roi_frame_path}"}
                logging.debug(f"Đã lưu frame với ROI vào: {roi_frame_path}")
                
                # Kiểm tra file đã được lưu thành công
                if not os.path.exists(roi_frame_path):
                    logging.error(f"File không tồn tại sau khi lưu: {roi_frame_path}")
                    return {"success": False, "error": f"File không tồn tại sau khi lưu: {roi_frame_path}"}
                
                # Nếu là bước packing, gọi detect_hands để kiểm tra tay
                hand_detected = False
                if step == "packing":
                    detect_result = detect_hands(video_path, {"x": x, "y": y, "w": w, "h": h})
                    if not detect_result["success"]:
                        logging.error(f"Lỗi khi phát hiện tay: {detect_result['error']}")
                        return {"success": False, "error": detect_result["error"]}
                    hand_detected = detect_result["hand_detected"]
                
                # Lưu tọa độ ROI và trạng thái hand_detected vào /tmp/roi.json
                result = {
                    "success": True,
                    "roi": {"x": x, "y": y, "w": w, "h": h},
                    "roi_frame": os.path.relpath(roi_frame_path, BASE_DIR),
                    "hand_detected": hand_detected
                }
                logging.debug(f"Lưu ROI vào /tmp/roi.json: {result}")
                with open("/tmp/roi.json", "w") as f:
                    json.dump(result, f)
                
                logging.debug(f"ROI hợp lệ: x={x}, y={y}, w={w}, h={h}, hand_detected: {hand_detected}")
                return result
            
        finally:
            cap.release()
            logging.debug("Đã giải phóng tài nguyên video (cap.release).")
        
    except Exception as e:
        logging.error(f"Lỗi trong select_roi: {str(e)}")
        cv2.destroyAllWindows()
        return {"success": False, "error": f"Lỗi hệ thống: {str(e)}"}

def detect_hands(video_path: str, roi: Dict[str, int]) -> Dict[str, Any]:
    """
    Hiển thị video với phát hiện tay trong vùng ROI, trả về trạng thái phát hiện tay.
    Args:
        video_path (str): Đường dẫn đến file video.
        roi (dict): Tọa độ ROI {'x': int, 'y': int, 'w': int, 'h': int}.
    Returns:
        dict: {'success': bool, 'hand_detected': bool, 'error': str nếu có lỗi}
    """
    try:
        x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
        if w <= 0 or h <= 0:
            logging.error("ROI không hợp lệ (chiều rộng hoặc chiều cao bằng 0).")
            return {"success": False, "hand_detected": False, "error": "ROI không hợp lệ."}

        # Mở video
        logging.debug("Đang mở video để phát hiện tay...")
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
                logging.error("Không thể mở video.")
                return {"success": False, "hand_detected": False, "error": "Không thể mở video."}

            frame_count = 0
            start_time = time.time()
            hand_detected = False

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Cắt video theo ROI
                roi_frame = frame[y:y+h, x:x+w]

                # Chỉ xử lý mỗi FRAME_STEP frame
                if frame_count % FRAME_STEP == 0:
                    # Chuyển đổi BGR sang RGB
                    rgb_frame = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)

                    # Phát hiện bàn tay
                    results = hands.process(rgb_frame)

                    # Kiểm tra và xác nhận phát hiện tay
                    if results.multi_hand_landmarks:
                        hand_detected = True
                        for hand_landmarks in results.multi_hand_landmarks:
                            # Vẽ keypoints ngay khi phát hiện tay
                            mp_drawing.draw_landmarks(
                                roi_frame, 
                                hand_landmarks, 
                                mp_hands.HAND_CONNECTIONS
                            )

                # Hiển thị video
                elapsed_time = time.time() - start_time
                cv2.putText(roi_frame, f"Time: {elapsed_time:.2f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("ROI Hand Detection", roi_frame)

                if cv2.waitKey(1) == ord("q"):
                    break

                frame_count += 1

            logging.debug(f"Phát hiện tay: {hand_detected}")
            return {"success": True, "hand_detected": hand_detected}
        
        finally:
            hands.close()
            cap.release()
            cv2.destroyWindow("ROI Hand Detection")
            logging.debug("Đã giải phóng tài nguyên video (cap.release) trong detect_hands.")
    
    except Exception as e:
        logging.error(f"Lỗi trong detect_hands: {str(e)}")
        return {"success": False, "hand_detected": False, "error": f"Lỗi hệ thống: {str(e)}"}

def finalize_roi(video_path: str, camera_id: str, rois: list) -> Dict[str, Any]:
    """
    Vẽ tất cả các vùng ROI (packing, MVD, trigger) lên frame và lưu vào thư mục CameraROI.
    Args:
        video_path (str): Đường dẫn đến file video.
        camera_id (str): ID của camera.
        rois (list): Danh sách các vùng ROI [{'type': str, 'x': int, 'y': int, 'w': int, 'h': int}, ...].
    Returns:
        dict: {'success': bool, 'final_roi_frame': str, 'error': str nếu có lỗi}
    """
    try:
        # Đảm bảo thư mục CameraROI tồn tại
        ensure_directory_exists(CAMERA_ROI_DIR)

        # Mở video và lấy frame đầu tiên
        logging.debug("Đang mở video để tạo ảnh tổng hợp...")
        cap = cv2.VideoCapture(video_path)
        try:
            if not cap.isOpened():
                logging.error("Không thể mở video.")
                return {"success": False, "error": "Không thể mở video."}

            ret, frame = cap.read()
            if not ret:
                logging.error("Không thể đọc frame từ video.")
                return {"success": False, "error": "Không thể đọc frame từ video."}

            # Vẽ các vùng ROI với màu sắc khác nhau
            for roi in rois:
                x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
                roi_type = roi["type"]

                # Định nghĩa màu sắc cho từng loại ROI
                if roi_type == "packing":
                    color = (0, 255, 0)  # Xanh lá
                elif roi_type == "mvd":
                    color = (0, 0, 255)  # Đỏ
                elif roi_type == "trigger":
                    color = (0, 255, 255)  # Vàng
                else:
                    color = (255, 255, 255)  # Trắng (mặc định)

                # Vẽ ROI lên frame
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                # Thêm nhãn cho vùng ROI
                cv2.putText(frame, roi_type.upper(), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            # Tạo tên file với timestamp và camera_id
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_final_{timestamp}.jpg")

            # Lưu ảnh tổng hợp
            ret = cv2.imwrite(final_roi_frame_path, frame)
            if not ret:
                logging.error(f"Không thể lưu ảnh tổng hợp tại: {final_roi_frame_path}")
                return {"success": False, "error": f"Không thể lưu ảnh tổng hợp tại {final_roi_frame_path}"}
            logging.debug(f"Đã lưu ảnh tổng hợp với tất cả ROI vào: {final_roi_frame_path}")

            return {"success": True, "final_roi_frame": os.path.relpath(final_roi_frame_path, BASE_DIR)}
        
        finally:
            cap.release()
            logging.debug("Đã giải phóng tài nguyên video (cap.release) trong finalize_roi.")
    
    except Exception as e:
        logging.error(f"Lỗi trong finalize_roi: {str(e)}")
        return {"success": False, "error": f"Lỗi hệ thống: {str(e)}"}

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
        logging.error(f"Lỗi khi chạy script: {str(e)}")
        print(f"Lỗi khi chạy script: {str(e)}")
        sys.exit(1)