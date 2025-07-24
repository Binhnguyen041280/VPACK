import cv2
import mediapipe as mp
import time
import logging
import json
import os
import glob
from datetime import datetime
from modules.config.logging_config import get_logger


# Định nghĩa BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Khởi tạo logger mà không sử dụng video_path
logger = get_logger(__name__, {"module": "hand_detection"})
logger.info("Logging initialized")

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

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

def select_roi(video_path, camera_id, step="packing"):
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

def detect_hands(video_path, roi):
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
        try:
            if not cap.isOpened():
                logging.error("Không thể mở video.")
                return {"success": False, "hand_detected": False, "error": "Không thể mở video."}

            hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)
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
                            mp_drawing.draw_landmarks(roi_frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

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
            cap.release()
            cv2.destroyWindow("ROI Hand Detection")  # Chỉ đóng cửa sổ của detect_hands
            logging.debug("Đã giải phóng tài nguyên video (cap.release) trong detect_hands.")
    
    except Exception as e:
        logging.error(f"Lỗi trong detect_hands: {str(e)}")
        return {"success": False, "hand_detected": False, "error": f"Lỗi hệ thống: {str(e)}"}

def finalize_roi(video_path, camera_id, rois):
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

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 hand_detection.py <video_path> <camera_id>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    camera_id = sys.argv[2]
    try:
        roi_result = select_roi(video_path, camera_id)
        if not roi_result["success"]:
            print(roi_result["error"])
    except Exception as e:
        logging.error(f"Lỗi khi chạy script: {str(e)}")
        print(f"Lỗi khi chạy script: {str(e)}")
