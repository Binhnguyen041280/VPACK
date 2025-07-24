from flask import Blueprint, request, jsonify
from modules.technician.qr_detector import select_qr_roi
import subprocess
import os
import json
import logging

qr_detection_bp = Blueprint('qr_detection', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

CAMERA_ROI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "resources/output_clips/CameraROI")

@qr_detection_bp.route('/select-qr-roi', methods=['POST'])
def select_qr_roi_endpoint():
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId')
        roi_frame_path = data.get('roiFramePath')
        step = data.get('step', 'mvd')
        
        logging.debug(f"[MVD] Received data: {data}")
        logging.debug(f"[MVD] Parameters - video_path: {video_path}, camera_id: {camera_id}, roi_frame_path: {roi_frame_path}, step: {step}")
        
        if not video_path or not camera_id or not roi_frame_path:
            logging.error("[MVD] Missing required parameters")
            return jsonify({"success": False, "error": "Thiếu videoPath, cameraId hoặc roiFramePath."}), 400
        
        logging.debug(f"[MVD] Checking video path exists: {video_path}")
        if not os.path.exists(video_path):
            logging.error(f"[MVD] Video path does not exist: {video_path}")
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        
        logging.debug(f"[MVD] Checking ROI frame path exists: {roi_frame_path}")
        if not os.path.exists(roi_frame_path):
            logging.error(f"[MVD] ROI frame path does not exist: {roi_frame_path}")
            return jsonify({"success": False, "error": "Đường dẫn ảnh tạm không tồn tại."}), 404
        
        if os.path.exists("/tmp/qr_roi.json"):
            logging.debug("[MVD] Removing existing /tmp/qr_roi.json")
            os.remove("/tmp/qr_roi.json")
            logging.info("[MVD] Đã xóa file /tmp/qr_roi.json để bắt đầu quy trình mới")
        
        logging.debug(f"[MVD] Calling select_qr_roi with video_path: {video_path}, camera_id: {camera_id}, roi_frame_path: {roi_frame_path}, step: {step}")
        result = select_qr_roi(video_path, camera_id, roi_frame_path, step)
        logging.debug(f"[MVD] select_qr_roi result: {result}")
        logging.info(f"[MVD] Completed MVD step for camera_id: {camera_id}")
        
        return jsonify(result), 200 if result["success"] else 400
    
    except Exception as e:
        logging.error(f"[MVD] Exception in select_qr_roi_endpoint: {str(e)}")
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500

@qr_detection_bp.route('/run-qr-detector', methods=['POST'])
def run_qr_detector_endpoint():
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId', 'default_camera')
        
        if not video_path:
            return jsonify({"success": False, "error": "Thiếu videoPath."}), 400
        
        absolute_roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_packing.jpg")
        
        logging.info(f"Running qr_detector.py with video_path: {video_path}, camera_id: {camera_id}, roi_frame_path: {absolute_roi_frame_path}")
        
        if not os.path.exists(video_path):
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        if not os.path.exists(absolute_roi_frame_path):
            return jsonify({"success": False, "error": "Đường dẫn ảnh packing không tồn tại."}), 404
        
        if os.path.exists("/tmp/qr_roi.json"):
            os.remove("/tmp/qr_roi.json")
        
        result = subprocess.run(
            ["python3", "modules/technician/qr_detector.py", video_path, camera_id, absolute_roi_frame_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            error_message = f"Lỗi khi chạy script: {result.stderr}"
            logging.error(error_message)
            return jsonify({"success": False, "error": error_message}), 500
        
        if not os.path.exists("/tmp/qr_roi.json"):
            return jsonify({"success": False, "error": "Không tìm thấy file kết quả ROI."}), 500
        
        with open("/tmp/qr_roi.json", "r") as f:
            qr_roi_result = json.load(f)
        
        logging.info(f"QR ROI result from /tmp/qr_roi.json: {qr_roi_result}")
        return jsonify(qr_roi_result), 200 if qr_roi_result["success"] else 400
    
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Hết thời gian chờ khi chạy script."}), 500
    except Exception as e:
        logging.error(f"Unexpected error in run-qr-detector: {str(e)}")
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500