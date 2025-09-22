import cv2
import os
import json
import logging
import queue
import threading
import time
import glob
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# Đảm bảo thư mục LOG tồn tại
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOG_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "LOG")
os.makedirs(LOG_DIR, exist_ok=True)

# ✅ FIXED: Use direct logging.basicConfig instead of modules.config.logging_config
log_file_path = os.path.join(LOG_DIR, f"qr_detector_{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("QR Detector logging initialized")

# Đường dẫn tới mô hình WeChat QRCode (tương đối)
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models", "wechat_qr")
DETECT_PROTO = os.path.join(MODEL_DIR, "detect.prototxt")
DETECT_MODEL = os.path.join(MODEL_DIR, "detect.caffemodel")
SR_PROTO = os.path.join(MODEL_DIR, "sr.prototxt")
SR_MODEL = os.path.join(MODEL_DIR, "sr.caffemodel")

# Đường dẫn lưu ảnh
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "CameraROI")

def select_qr_roi(video_path, camera_id, roi_frame_path, step="mvd"):
    """
    Cho phép người dùng vẽ ROI cho mã QR (1 hoặc 2 vùng cho mvd), sau đó xử lý video.
    Args:
        video_path (str): Đường dẫn đến file video.
        camera_id (str): ID của camera.
        roi_frame_path (str): Đường dẫn đến ảnh tạm cuối cùng từ bước trước (đã có ROI vẽ sẵn).
        step (str): Giai đoạn hiện tại (mvd).
    Returns:
        dict: {'success': bool, 'rois': [{'x': int, 'y': int, 'w': int, 'h': int, 'type': str}, ...], 
               'roi_frame': str, 'qr_detected': bool, 'qr_detected_roi1': bool, 'qr_detected_roi2': bool, 
               'qr_content': str, 'trigger_detected': bool, 'table_type': str}
              hoặc {'success': false, 'error': str}
    """
    try:
        logger.debug(f"[MVD] Bắt đầu select_qr_roi với video_path: {video_path}, camera_id: {camera_id}, roi_frame_path: {roi_frame_path}, step: {step}")

        # Kiểm tra sự tồn tại của các mô hình
        for model_file in [DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL]:
            logger.debug(f"[MVD] Kiểm tra file mô hình: {model_file}")
            if not os.path.exists(model_file):
                logger.error(f"[MVD] File mô hình không tìm thấy: {model_file}")
                cv2.destroyAllWindows()
                return {"success": False, "error": f"File mô hình không tìm thấy: {model_file}"}

        # Kiểm tra file ảnh và video
        logger.debug(f"[MVD] Kiểm tra ảnh tạm: {roi_frame_path}")
        if not os.path.exists(roi_frame_path):
            logger.error(f"[MVD] Ảnh tạm không tồn tại: {roi_frame_path}")
            cv2.destroyAllWindows()
            return {"success": False, "error": f"Ảnh tạm không tồn tại: {roi_frame_path}"}
        
        logger.debug(f"[MVD] Kiểm tra video: {video_path}")
        if not os.path.exists(video_path):
            logger.error(f"[MVD] Video không tồn tại: {video_path}")
            cv2.destroyAllWindows()
            return {"success": False, "error": f"Video không tồn tại: {video_path}"}

        # Đọc frame từ ảnh tạm
        try:
            logger.debug(f"[MVD] Đọc ảnh tạm: {roi_frame_path}")
            frame = cv2.imread(roi_frame_path)
            if frame is None:
                logger.error(f"[MVD] Không thể đọc ảnh tạm: {roi_frame_path}")
                cv2.destroyAllWindows()
                return {"success": False, "error": f"Không thể đọc ảnh tạm: {roi_frame_path}"}
            logger.debug(f"[MVD] Kích thước ảnh tạm: {frame.shape[:2]}")
        except Exception as e:
            logger.error(f"[MVD] OpenCV imread error: {str(e)}\n{traceback.format_exc()}")
            cv2.destroyAllWindows()
            return {"success": False, "error": f"OpenCV imread error: {str(e)}"}

        # Chọn loại bàn đóng gói
        table_type = None
        while table_type is None:
            current_frame = frame.copy()
            window_title = "**** Nhan 1 cho ban tieu chuan, 2 cho ban khong tieu chuan, q thoat ****"
            cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
            cv2.imshow(window_title, current_frame)
            key = cv2.waitKey(0) & 0xFF
            cv2.destroyAllWindows()
            if key == ord('1'):
                table_type = "standard"
                logger.debug("[MVD] Chọn bàn tiêu chuẩn")
            elif key == ord('2'):
                table_type = "non_standard"
                logger.debug("[MVD] Chọn bàn không tiêu chuẩn")
            elif key == ord('q'):
                logger.debug("[MVD] Người dùng thoát")
                cv2.destroyAllWindows()
                return {"success": False, "error": "Người dùng thoát"}
            else:
                logger.debug("[MVD] Phím không hợp lệ, hiển thị lại hướng dẫn")
                continue

        while True:
            # Tạo bản sao mới của frame mỗi lần vẽ lại
            current_frame = frame.copy()
            rois = []

            # Vẽ ROI 1 (mã QR)
            window_title = "**** Keo chuot ve vung ma QR. Enter xac nhan, Esc huy ****"
            try:
                logger.debug("[MVD] Gọi cv2.selectROI cho MVD ROI 1")
                cv2.destroyAllWindows()
                cv2.startWindowThread()
                cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
                roi1 = cv2.selectROI(window_title, current_frame, showCrosshair=True, fromCenter=False)
                cv2.destroyAllWindows()
                x1, y1, w1, h1 = map(int, roi1)
                if w1 > 0 and h1 > 0:
                    rois.append({"x": x1, "y": y1, "w": w1, "h": h1, "type": "mvd"})
                    cv2.rectangle(current_frame, (x1, y1), (x1 + w1, y1 + h1), (0, 0, 255), 2)  # Màu đỏ cho MVD
                    cv2.putText(current_frame, "ShippingLabel", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    logger.debug(f"[MVD] Đã chọn MVD ROI 1: x={x1}, y={y1}, w={w1}, h={h1}")
                    cv2.namedWindow("**** Da ve vung ma QR ****", cv2.WINDOW_NORMAL)
                    cv2.imshow("**** Da ve vung ma QR ****", current_frame)
                    cv2.waitKey(500)
                    cv2.destroyAllWindows()
                else:
                    logger.debug("[MVD] ROI 1 không hợp lệ")
                    cv2.namedWindow("**** Loi: ROI khong hop le. Ve lai vung ma QR ****", cv2.WINDOW_NORMAL)
                    cv2.imshow("**** Loi: ROI khong hop le. Ve lai vung ma QR ****", current_frame)
                    cv2.waitKey(2000)
                    cv2.destroyAllWindows()
                    continue

                # Chỉ vẽ ROI 2 (trigger) cho bàn tiêu chuẩn
                if table_type == "standard":
                    window_title = "**** Ve vung ma trigger (QR: TimeGo). Enter xac nhan, Esc huy ****"
                    roi2_label = "Trigger"
                    logger.debug("[MVD] Gọi cv2.selectROI cho ROI 2")
                    cv2.destroyAllWindows()
                    cv2.startWindowThread()
                    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
                    roi2 = cv2.selectROI(window_title, current_frame, showCrosshair=True, fromCenter=False)
                    cv2.destroyAllWindows()
                    x2, y2, w2, h2 = map(int, roi2)
                    if w2 > 0 and h2 > 0:
                        roi_type = "trigger"
                        rois.append({"x": x2, "y": y2, "w": w2, "h": h2, "type": roi_type})
                        cv2.rectangle(current_frame, (x2, y2), (x2 + w2, y2 + h2), (0, 0, 255), 2)  # Màu đỏ
                        cv2.putText(current_frame, roi2_label, (x2, y2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        logger.debug(f"[MVD] Đã chọn ROI 2: x={x2}, y={y2}, w={w2}, h={h2}, type={roi_type}")
            except Exception as e:
                logger.error(f"[MVD] OpenCV selectROI error: {str(e)}\n{traceback.format_exc()}")
                cv2.destroyAllWindows()
                return {"success": False, "error": f"OpenCV selectROI error: {str(e)}"}

            # Lưu ảnh vào CameraROI nếu có ROI hợp lệ
            if rois:
                roi_frame_path_new = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_MVD.jpg")
                try:
                    logger.debug(f"[MVD] Lưu ảnh với ROI vào: {roi_frame_path_new}")
                    ret = cv2.imwrite(roi_frame_path_new, current_frame)
                    if not ret:
                        logger.error(f"[MVD] Không thể lưu ảnh tại: {roi_frame_path_new}")
                        cv2.destroyAllWindows()
                        return {"success": False, "error": f"Không thể lưu ảnh tại {roi_frame_path_new}"}
                    logger.info(f"[MVD] Đã lưu frame với ROI vào: {roi_frame_path_new}")
                except Exception as e:
                    logger.error(f"[MVD] OpenCV imwrite error: {str(e)}\n{traceback.format_exc()}")
                    cv2.destroyAllWindows()
                    return {"success": False, "error": f"OpenCV imwrite error: {str(e)}"}
                break
            else:
                logger.debug("[MVD] Không chọn được ROI hợp lệ, hiển thị lại ảnh trước đó để vẽ lại.")
                cv2.namedWindow("**** Loi: ROI khong hop le. Ve lai vung ma QR ****", cv2.WINDOW_NORMAL)
                cv2.imshow("**** Loi: ROI khong hop le. Ve lai vung ma QR ****", current_frame)
                cv2.waitKey(2000)
                cv2.destroyAllWindows()
                continue

        # Kiểm tra tính tương thích của ảnh packing với MVD
        logger.debug(f"[MVD] Kiểm tra tính tương thích của ảnh packing với MVD: {roi_frame_path}")

        # Khởi tạo danh sách hàng đợi và cờ thoát
        frame_queues = [queue.Queue(maxsize=50) for _ in range(len(rois))]
        exit_flag = threading.Event()
        qr_detected = False
        qr_detected_roi1 = False
        qr_detected_roi2 = False
        qr_content = ""
        trigger_detected = False

        def process_roi(video_file, roi_index, x, y, w, h, interval=5):
            nonlocal qr_detected, qr_detected_roi1, qr_detected_roi2, qr_content, trigger_detected
            try:
                logger.debug(f"[MVD] Khởi tạo WeChatQRCode cho ROI {roi_index + 1}")
                local_detector = cv2.wechat_qrcode_WeChatQRCode(DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL)  # type: ignore
                logger.debug(f"[MVD] WeChatQRCode khởi tạo thành công cho ROI {roi_index + 1}")
            except Exception as e:
                logger.error(f"[MVD] OpenCV WeChatQRCode error in ROI {roi_index + 1}: {str(e)}\n{traceback.format_exc()}")
                return

            try:
                logger.debug(f"[MVD] Mở video cho ROI {roi_index + 1}: {video_file}")
                cap = cv2.VideoCapture(video_file)
                if not cap.isOpened():
                    logger.error(f"[MVD] Không thể mở video '{video_file}' cho ROI {roi_index + 1}")
                    return
                logger.debug(f"[MVD] Video mở thành công cho ROI {roi_index + 1}")
            except Exception as e:
                logger.error(f"[MVD] OpenCV VideoCapture error in ROI {roi_index + 1}: {str(e)}\n{traceback.format_exc()}")
                return

            frame_count = 0
            start_time = time.time()

            while not exit_flag.is_set():
                try:
                    ret, frame = cap.read()
                    if not ret:
                        logger.debug(f"[MVD] Kết thúc video '{video_file}' (ROI {roi_index + 1})")
                        break

                    frame_count += 1
                    if frame_count % interval != 0:
                        continue

                    logger.debug(f"[MVD] Xử lý frame {frame_count} cho ROI {roi_index + 1}")
                    roi_frame = frame[y:y+h, x:x+w]
                    if roi_frame.size == 0 or roi_frame.shape[0] == 0 or roi_frame.shape[1] == 0:
                        logger.warning(f"[MVD] ROI {roi_index + 1} không hợp lệ, bỏ qua frame")
                        continue

                    if len(roi_frame.shape) == 2:
                        roi_frame = cv2.cvtColor(roi_frame, cv2.COLOR_GRAY2BGR)

                    logger.debug(f"[MVD] Phát hiện QR trong ROI {roi_index + 1}")
                    texts, points = local_detector.detectAndDecode(roi_frame)
                    if texts:
                        qr_detected = True
                        if roi_index == 0:
                            qr_detected_roi1 = True
                        elif roi_index == 1 and table_type == "standard":
                            qr_detected_roi2 = True
                        qr_content = texts[0]  # Lưu nội dung QR đầu tiên
                        # Kiểm tra trigger cho ROI 2 (bàn tiêu chuẩn)
                        if table_type == "standard" and roi_index == 1 and texts[0].lower() == "timego":
                            trigger_detected = True
                            logger.info(f"[MVD] [ROI {roi_index + 1}] Phát hiện trigger: {texts[0]}")
                        for text, box in zip(texts, points):
                            logger.info(f"[MVD] [ROI {roi_index + 1}] Nội dung mã QR: {text}")
                            # Vẽ khung viền QR
                            for i in range(4):
                                pt1 = tuple(map(int, box[i]))
                                pt2 = tuple(map(int, box[(i + 1) % 4]))
                                cv2.line(roi_frame, pt1, pt2, (0, 255, 0), 2)
                            # Hiển thị nội dung QR dưới khung viền
                            bottom_left = tuple(map(int, box[2]))  # Góc dưới trái
                            cv2.putText(roi_frame, text[:20], (bottom_left[0], bottom_left[1] + 30), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    elapsed_time = time.time() - start_time
                    elapsed_time_text = f"Time: {elapsed_time:.1f}"
                    cv2.putText(roi_frame, elapsed_time_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    cv2.putText(roi_frame, "Dang phat hien ma QR. Noi dung hien thi neu tim thay", 
                                (10, roi_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    frame_queues[roi_index].put(roi_frame)
                    logger.debug(f"[MVD] Đã đẩy frame cho ROI {roi_index + 1} vào hàng đợi")
                except Exception as e:
                    logger.error(f"[MVD] OpenCV processing error in process_roi (ROI {roi_index + 1}): {str(e)}\n{traceback.format_exc()}")
                    break

            logger.debug(f"[MVD] Giải phóng video capture cho ROI {roi_index + 1}")
            cap.release()

        # Khởi chạy luồng xử lý video cho từng ROI
        threads = []
        for i, roi in enumerate(rois):
            if roi["w"] > 0 and roi["h"] > 0:
                logger.debug(f"[MVD] Khởi chạy thread cho ROI {i + 1}")
                thread = threading.Thread(target=process_roi, args=(video_path, i, roi["x"], roi["y"], roi["w"], roi["h"], 5))
                thread.start()
                threads.append(thread)
                logger.info(f"[MVD] Thread cho ROI {i + 1} đã khởi chạy")
            else:
                logger.warning(f"[MVD] ROI {i + 1} không hợp lệ, bỏ qua")

        # Khởi tạo cửa sổ cho từng ROI
        for i in range(len(frame_queues)):
            try:
                logger.debug(f"[MVD] Khởi tạo cửa sổ cho ROI {i + 1}")
                window_title = f"**** Dang phat hien ma QR. Noi dung hien thi neu tim thay (ROI {i + 1}) ****"
                cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)
                logger.debug(f"[MVD] Cửa sổ cho ROI {i + 1} đã được khởi tạo")
            except Exception as e:
                logger.error(f"[MVD] OpenCV namedWindow error: {str(e)}\n{traceback.format_exc()}")
                cv2.destroyAllWindows()
                return {"success": False, "error": f"OpenCV namedWindow error: {str(e)}"}

        # Hiển thị mỗi ROI trong cửa sổ riêng
        while any(thread.is_alive() for thread in threads) or any(not q.empty() for q in frame_queues):
            for i in range(len(frame_queues)):
                try:
                    frame = frame_queues[i].get(timeout=0.1)
                    window_name = f"**** Dang phat hien ma QR. Noi dung hien thi neu tim thay (ROI {i + 1}) ****"
                    cv2.imshow(window_name, frame)
                    logger.debug(f"[MVD] Hiển thị frame cho {window_name}")
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.error(f"[MVD] OpenCV imshow error in loop: {str(e)}\n{traceback.format_exc()}")
                    cv2.destroyAllWindows()
                    return {"success": False, "error": f"OpenCV imshow error: {str(e)}"}

            try:
                if cv2.waitKey(10) & 0xFF == ord('q'):
                    logger.debug("[MVD] Nhận lệnh thoát từ người dùng")
                    exit_flag.set()
                    break
            except Exception as e:
                logger.error(f"[MVD] OpenCV waitKey error: {str(e)}\n{traceback.format_exc()}")
                cv2.destroyAllWindows()
                return {"success": False, "error": f"OpenCV waitKey error: {str(e)}"}

        logger.debug("[MVD] Đóng tất cả cửa sổ OpenCV")
        cv2.destroyAllWindows()
        for thread in threads:
            logger.debug(f"[MVD] Chờ thread ROI {threads.index(thread) + 1} kết thúc")
            thread.join()

        # Lưu kết quả vào /tmp/qr_roi.json
        result = {
            "success": True,
            "rois": rois,
            "roi_frame": os.path.relpath(roi_frame_path_new, BASE_DIR),
            "qr_detected": qr_detected,
            "qr_detected_roi1": qr_detected_roi1,
            "qr_detected_roi2": qr_detected_roi2 if table_type == "standard" else False,
            "qr_content": qr_content,
            "trigger_detected": trigger_detected,
            "table_type": table_type
        }
        logger.debug(f"[MVD] Lưu kết quả vào /tmp/qr_roi.json: {result}")
        try:
            with open("/tmp/qr_roi.json", "w") as f:
                json.dump(result, f)
            logger.info("[MVD] Đã lưu kết quả vào /tmp/qr_roi.json")
        except Exception as e:
            logger.error(f"[MVD] Lỗi khi lưu /tmp/qr_roi.json: {str(e)}\n{traceback.format_exc()}")
            cv2.destroyAllWindows()
            return {"success": False, "error": f"Lỗi khi lưu /tmp/qr_roi.json: {str(e)}"}

        logger.info(f"[MVD] Hoàn tất select_qr_roi cho camera_id: {camera_id}, step: {step}")
        cv2.destroyAllWindows()
        return result

    except Exception as e:
        logger.error(f"[MVD] Lỗi trong select_qr_roi: {str(e)}\n{traceback.format_exc()}")
        cv2.destroyAllWindows()
        return {"success": False, "error": f"Lỗi hệ thống: {str(e)}"}

def detect_qr_at_time(video_path: str, time_seconds: float, roi_config: dict, cancellation_flag=None) -> dict:
    """
    Detect QR codes at specific timestamp in video for preprocessing pipeline
    
    Args:
        video_path (str): Path to video file
        time_seconds (float): Video time in seconds
        roi_config (dict): ROI configuration {'x': int, 'y': int, 'w': int, 'h': int}
        cancellation_flag (threading.Event): Optional cancellation flag to check
    
    Returns:
        dict: {
            'success': bool,
            'qr_detections': [{'bbox': {'x': int, 'y': int, 'w': int, 'h': int}, 
                              'decoded_text': str, 'confidence': float}],
            'timestamp': float,
            'error': str (if error)
        }
    """
    try:
        logger.debug(f"[QR-DETECT] Detecting QR at time {time_seconds}s in {video_path}")
        
        # Check cancellation at start
        if cancellation_flag and cancellation_flag.is_set():
            logger.debug(f"[QR-DETECT] Detection cancelled before processing at {time_seconds}s")
            return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
        
        # Validate parameters
        if not os.path.exists(video_path):
            return {"success": False, "error": f"Video file not found: {video_path}"}
        
        if not roi_config or not all(k in roi_config for k in ['x', 'y', 'w', 'h']):
            return {"success": False, "error": "Invalid ROI configuration"}
        
        # Check model files exist
        for model_file in [DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL]:
            if not os.path.exists(model_file):
                return {"success": False, "error": f"Model file not found: {model_file}"}
        
        # Check cancellation before model initialization
        if cancellation_flag and cancellation_flag.is_set():
            logger.debug(f"[QR-DETECT] Detection cancelled before model init at {time_seconds}s")
            return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
        
        # Initialize QR detector
        try:
            qr_detector = cv2.wechat_qrcode_WeChatQRCode(DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL)  # type: ignore
        except Exception as e:
            return {"success": False, "error": f"Failed to initialize QR detector: {str(e)}"}
        
        # Check cancellation before video operations
        if cancellation_flag and cancellation_flag.is_set():
            logger.debug(f"[QR-DETECT] Detection cancelled before video open at {time_seconds}s")
            return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"success": False, "error": f"Cannot open video: {video_path}"}
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30  # Default fallback
            
            # Calculate frame number for timestamp
            frame_number = int(time_seconds * fps)
            
            # Check cancellation before seeking
            if cancellation_flag and cancellation_flag.is_set():
                logger.debug(f"[QR-DETECT] Detection cancelled before frame seek at {time_seconds}s")
                return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
            
            # Seek to specific frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                return {
                    "success": False, 
                    "error": f"Cannot read frame at time {time_seconds}s (frame {frame_number})"
                }
            
            # Check cancellation before ROI extraction
            if cancellation_flag and cancellation_flag.is_set():
                logger.debug(f"[QR-DETECT] Detection cancelled before ROI processing at {time_seconds}s")
                return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
            
            # Extract ROI from frame
            x, y, w, h = roi_config['x'], roi_config['y'], roi_config['w'], roi_config['h']
            
            # Validate ROI boundaries
            frame_h, frame_w = frame.shape[:2]
            if x < 0 or y < 0 or x + w > frame_w or y + h > frame_h:
                return {
                    "success": False,
                    "error": f"ROI out of bounds: ROI({x},{y},{w},{h}) vs Frame({frame_w},{frame_h})"
                }
            
            roi_frame = frame[y:y+h, x:x+w]
            
            if roi_frame.size == 0:
                return {"success": False, "error": "Empty ROI frame"}
            
            # Check cancellation before WeChat QR detection (this is the expensive operation)
            if cancellation_flag and cancellation_flag.is_set():
                logger.debug(f"[QR-DETECT] Detection cancelled before WeChat QR detection at {time_seconds}s")
                return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
            
            # NOTE: This is the critical blocking operation that cannot be directly cancelled
            # WeChat QR detector - no way to interrupt this once started
            logger.debug(f"[QR-DETECT] Starting WeChat QR detectAndDecode at {time_seconds}s")
            texts, points = qr_detector.detectAndDecode(roi_frame)
            logger.debug(f"[QR-DETECT] Completed WeChat QR detectAndDecode at {time_seconds}s")
            
            # Check cancellation after detection
            if cancellation_flag and cancellation_flag.is_set():
                logger.debug(f"[QR-DETECT] Detection cancelled after WeChat QR detection at {time_seconds}s")
                return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
            
            qr_detections = []
            if texts and points is not None:
                for i, (text, box) in enumerate(zip(texts, points)):
                    if text:  # Only include non-empty decoded text
                        # Calculate bounding box from points
                        if len(box) >= 4:
                            # Get bounding rectangle from QR corners
                            x_coords = [int(pt[0]) for pt in box]
                            y_coords = [int(pt[1]) for pt in box]
                            
                            bbox_x = min(x_coords)
                            bbox_y = min(y_coords)
                            bbox_w = max(x_coords) - bbox_x
                            bbox_h = max(y_coords) - bbox_y
                            
                            # Add ROI offset to convert to original frame coordinates
                            qr_detections.append({
                                'bbox': {
                                    'x': bbox_x + x,  # Add ROI offset
                                    'y': bbox_y + y,  # Add ROI offset
                                    'w': bbox_w,
                                    'h': bbox_h
                                },
                                'decoded_text': text,
                                'confidence': 0.95  # WeChat QR detector doesn't provide confidence, use fixed value
                            })
                            
                            logger.debug(f"[QR-DETECT] Found QR: '{text}' at bbox({bbox_x + x}, {bbox_y + y}, {bbox_w}, {bbox_h})")
            
            result = {
                'success': True,
                'qr_detections': qr_detections,
                'timestamp': time_seconds,
                'qr_count': len(qr_detections)
            }
            
            logger.debug(f"[QR-DETECT] Detected {len(qr_detections)} QR codes at {time_seconds}s")
            return result
            
        finally:
            cap.release()
            
    except Exception as e:
        if cancellation_flag and cancellation_flag.is_set():
            logger.debug(f"[QR-DETECT] Detection cancelled during processing at {time_seconds}s: {str(e)}")
            return {"success": False, "error": f"Detection cancelled at {time_seconds}s"}
        else:
            logger.error(f"[QR-DETECT] Error in detect_qr_at_time: {str(e)}\n{traceback.format_exc()}")
            return {"success": False, "error": f"Detection error: {str(e)}"}

def preprocess_video_qr(video_path: str, roi_config: dict, fps: int = 5, progress_callback=None) -> dict:
    """
    Pre-process entire video for QR detection at specified fps
    Cache results for perfect synchronization during playback
    
    Args:
        video_path (str): Path to video file
        roi_config (dict): ROI configuration {'x': int, 'y': int, 'w': int, 'h': int}
        fps (int): Detection fps (default 5fps = every 0.2s)
        progress_callback (callable): Function to call with progress updates
    
    Returns:
        dict: {
            'success': bool,
            'detections': [{'timestamp': float, 'qr_detections': list, 'qr_count': int}],
            'metadata': dict,
            'total_frames_processed': int,
            'error': str (if error)
        }
    """
    try:
        logger.info(f"[QR-PREPROCESS] Starting video preprocessing at {fps}fps for {video_path}")
        
        # Validate inputs
        if not os.path.exists(video_path):
            return {"success": False, "error": f"Video file not found: {video_path}"}
        
        if not roi_config or not all(k in roi_config for k in ['x', 'y', 'w', 'h']):
            return {"success": False, "error": "Invalid ROI configuration"}
        
        # Get video properties
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"success": False, "error": f"Cannot open video: {video_path}"}
        
        try:
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / video_fps if video_fps > 0 else 0
            
            logger.debug(f"[QR-PREPROCESS] Video info: {total_frames} frames, {video_fps} fps, {duration:.1f}s duration")
            
        finally:
            cap.release()
        
        # Calculate processing timestamps (5fps = every 0.2s)
        interval = 1.0 / fps  # 0.2s for 5fps
        timestamps = []
        current_time = 0.0
        
        while current_time <= duration:
            timestamps.append(round(current_time, 1))  # Round to avoid floating point issues
            current_time += interval
        
        total_timestamps = len(timestamps)
        logger.info(f"[QR-PREPROCESS] Processing {total_timestamps} timestamps at {fps}fps")
        
        # Initialize results
        detections = []
        processed_count = 0
        start_time = time.time()
        
        # Process each timestamp
        for i, timestamp in enumerate(timestamps):
            try:
                # Check cancellation via progress callback
                try:
                    from blueprints.qr_detection_bp import qr_preprocessing_progress
                    # Generate cache key to check status (same logic as in blueprint)
                    import hashlib
                    roi_str = f"{roi_config['x']}_{roi_config['y']}_{roi_config['w']}_{roi_config['h']}"
                    cache_input = f"{video_path}_{roi_str}"
                    cache_key = hashlib.md5(cache_input.encode()).hexdigest()
                    
                    if (cache_key in qr_preprocessing_progress and 
                        qr_preprocessing_progress[cache_key].get('cancelled', False)):
                        logger.info(f"[QR-PREPROCESS] CANCELLATION DETECTED at frame {i+1}/{total_timestamps} - FORCING SKIP TO END")
                        
                        # Force skip to last frame strategy
                        # Instead of stopping, jump to the last few frames and finish quickly
                        remaining_timestamps = timestamps[max(0, len(timestamps) - 3):]  # Process only last 3 frames
                        logger.info(f"[QR-PREPROCESS] Fast-finishing with last {len(remaining_timestamps)} frames")
                        
                        for final_timestamp in remaining_timestamps:
                            try:
                                result = detect_qr_at_time(video_path, final_timestamp, roi_config)
                                if result['success']:
                                    detection_entry = {
                                        'timestamp': final_timestamp,
                                        'qr_detections': result['qr_detections'],
                                        'qr_count': result.get('qr_count', 0)
                                    }
                                    detections.append(detection_entry)
                                else:
                                    detections.append({
                                        'timestamp': final_timestamp,
                                        'qr_detections': [],
                                        'qr_count': 0
                                    })
                                processed_count += 1
                            except Exception:
                                # Skip any errors during fast finish
                                detections.append({
                                    'timestamp': final_timestamp,
                                    'qr_detections': [],
                                    'qr_count': 0
                                })
                                processed_count += 1
                        
                        logger.info(f"[QR-PREPROCESS] Fast finish completed - processed {processed_count}/{total_timestamps} frames")
                        break  # Exit the main loop
                except ImportError:
                    # Blueprint not available, continue normally
                    pass
                except Exception as e:
                    logger.warning(f"[QR-PREPROCESS] Error checking cancellation: {str(e)}")
                
                # Call QR detection for this timestamp
                result = detect_qr_at_time(video_path, timestamp, roi_config)
                
                if result['success']:
                    # Store detection result
                    detection_entry = {
                        'timestamp': timestamp,
                        'qr_detections': result['qr_detections'],
                        'qr_count': result.get('qr_count', 0)
                    }
                    detections.append(detection_entry)
                    
                    if result.get('qr_count', 0) > 0:
                        logger.debug(f"[QR-PREPROCESS] Frame {i+1}/{total_timestamps}: {result['qr_count']} QR codes at {timestamp}s")
                else:
                    logger.warning(f"[QR-PREPROCESS] Frame {i+1}/{total_timestamps}: Failed at {timestamp}s - {result.get('error')}")
                    # Still add entry with empty detections for timeline consistency
                    detections.append({
                        'timestamp': timestamp,
                        'qr_detections': [],
                        'qr_count': 0
                    })
                
                processed_count += 1
                
                # Update progress AFTER processing (with new detections)
                if progress_callback:
                    try:
                        progress_percent = (processed_count / total_timestamps) * 100
                        elapsed_time = time.time() - start_time
                        estimated_total_time = elapsed_time * total_timestamps / processed_count
                        
                        # Call progress callback with current detections for incremental caching
                        progress_callback(
                            progress=progress_percent,
                            processed_count=processed_count,
                            total_frames=total_timestamps,
                            new_detections=[detection_entry] if 'detection_entry' in locals() else []
                        )
                    except Exception as callback_error:
                        if "cancelled" in str(callback_error).lower():
                            logger.info(f"[QR-PREPROCESS] Processing cancelled after frame {i+1}/{total_timestamps} (timestamp {timestamp}s)")
                            return {"success": False, "error": f"Processing cancelled after timestamp {timestamp}s"}
                        else:
                            raise callback_error
                
                # Log progress every 25%
                if processed_count % max(1, total_timestamps // 4) == 0:
                    progress_percent = (processed_count / total_timestamps) * 100
                    logger.info(f"[QR-PREPROCESS] Progress: {processed_count}/{total_timestamps} ({progress_percent:.1f}%)")
                    
            except Exception as e:
                if "cancelled" in str(e).lower():
                    logger.info(f"[QR-PREPROCESS] Processing cancelled during timestamp {timestamp}: {str(e)}")
                    return {"success": False, "error": f"Processing cancelled during timestamp {timestamp}s"}
                else:
                    logger.error(f"[QR-PREPROCESS] Error processing timestamp {timestamp}: {str(e)}")
                    # Add empty entry to maintain timeline
                    detections.append({
                        'timestamp': timestamp,
                        'qr_detections': [],
                        'qr_count': 0
                    })
                    processed_count += 1
        
        # Final statistics
        processing_time = time.time() - start_time
        total_qr_detections = sum(d.get('qr_count', 0) for d in detections)
        
        metadata = {
            'video_path': video_path,
            'roi_config': roi_config,
            'detection_fps': fps,
            'video_duration': duration,
            'total_timestamps': total_timestamps,
            'total_qr_detections': total_qr_detections,
            'processing_time_seconds': round(processing_time, 2),
            'qr_detection_rate': f"{total_qr_detections}/{total_timestamps} frames",
            'processed_at': datetime.now().isoformat()
        }
        
        logger.info(f"[QR-PREPROCESS] Completed: {total_qr_detections} QR detections in {processing_time:.2f}s")
        
        return {
            'success': True,
            'detections': detections,
            'metadata': metadata,
            'total_frames_processed': processed_count
        }
        
    except Exception as e:
        if "cancelled" in str(e).lower():
            logger.info(f"[QR-PREPROCESS] Processing cancelled: {str(e)}")
            return {"success": False, "error": f"Processing cancelled: {str(e)}"}
        else:
            logger.error(f"[QR-PREPROCESS] Error in preprocess_video_qr: {str(e)}\n{traceback.format_exc()}")
            return {"success": False, "error": f"Preprocessing error: {str(e)}"}

def detect_qr_from_image(image_content: str) -> dict:
    """
    Detect QR codes from base64 image using WeChat QRCode model

    Args:
        image_content (str): Base64 encoded image string

    Returns:
        dict: {
            'success': bool,
            'qr_detections': [str] - Array of detected QR code texts,
            'qr_count': int,
            'error': str (if success=False)
        }
    """
    try:
        import base64
        import numpy as np

        # Check model files exist
        for model_file in [DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL]:
            if not os.path.exists(model_file):
                return {"success": False, "error": f"Model file not found: {model_file}"}

        # Initialize WeChat QR detector
        try:
            qr_detector = cv2.wechat_qrcode_WeChatQRCode(DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL)  # type: ignore
        except Exception as e:
            return {"success": False, "error": f"Failed to initialize QR detector: {str(e)}"}

        # Decode base64 to image
        try:
            image_data = base64.b64decode(image_content)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {"success": False, "error": "Failed to decode image from base64"}

        except Exception as e:
            return {"success": False, "error": f"Failed to process image data: {str(e)}"}

        # Detect QR codes
        try:
            texts, points = qr_detector.detectAndDecode(image)

            qr_detections = []
            if texts and len(texts) > 0:
                for text in texts:
                    if text and text.strip():  # Only add non-empty texts
                        qr_detections.append(text.strip())

            logger.info(f"[QR-IMAGE] Detected {len(qr_detections)} QR codes from image")

            return {
                'success': True,
                'qr_detections': qr_detections,
                'qr_count': len(qr_detections)
            }

        except Exception as e:
            return {"success": False, "error": f"QR detection failed: {str(e)}"}

    except Exception as e:
        logger.error(f"[QR-IMAGE] Error in detect_qr_from_image: {str(e)}\n{traceback.format_exc()}")
        return {"success": False, "error": f"Image processing error: {str(e)}"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        logger.error("Usage: python3 qr_detector.py <video_path> <camera_id> <roi_frame_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    camera_id = sys.argv[2]
    roi_frame_path = sys.argv[3]
    try:
        result = select_qr_roi(video_path, camera_id, roi_frame_path, step="mvd")
        if not result["success"]:
            logger.error(result["error"])
            sys.exit(1)
    except Exception as e:
        logger.error(f"[MVD] Lỗi khi chạy script: {str(e)}\n{traceback.format_exc()}")
        cv2.destroyAllWindows()
        sys.exit(1)