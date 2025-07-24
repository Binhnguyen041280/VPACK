from flask import Blueprint, request, jsonify
from modules.technician.hand_detection import select_roi
import subprocess
import os
import json
import logging

hand_detection_bp = Blueprint('hand_detection', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@hand_detection_bp.route('/select-roi', methods=['POST'])
def select_roi_endpoint():
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId')
        step = data.get('step', 'packing')
        
        logging.debug(f"Received request for select-roi with step: {step}, video_path: {video_path}, camera_id: {camera_id}")
        
        if not video_path or not camera_id:
            logging.error("Missing videoPath or cameraId")
            return jsonify({"success": False, "error": "Thiếu videoPath hoặc cameraId."}), 400
        
        if not os.path.exists(video_path):
            logging.error(f"Video path does not exist: {video_path}")
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        
        if os.path.exists("/tmp/roi.json"):
            os.remove("/tmp/roi.json")
            logging.info("Đã xóa file /tmp/roi.json để bắt đầu quy trình mới")
        
        result = select_roi(video_path, camera_id, step)
        logging.debug(f"Result from select_roi: {result}")
        return jsonify(result), 200 if result["success"] else 400
    
    except Exception as e:
        logging.error(f"Exception in select_roi_endpoint: {str(e)}")
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500

@hand_detection_bp.route('/run-select-roi', methods=['POST'])
def run_select_roi_endpoint():
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId', 'default_camera')
        
        if not video_path:
            return jsonify({"success": False, "error": "Thiếu videoPath."}), 400
        
        logging.info(f"Running hand_detection.py with video_path: {video_path}, camera_id: {camera_id}")
        
        if not os.path.exists(video_path):
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        
        if os.path.exists("/tmp/roi.json"):
            os.remove("/tmp/roi.json")
        
        result = subprocess.run(
            ["python3", "modules/technician/hand_detection.py", video_path, camera_id],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            error_message = f"Lỗi khi chạy script: {result.stderr}"
            logging.error(error_message)
            return jsonify({"success": False, "error": error_message}), 500
        
        if not os.path.exists("/tmp/roi.json"):
            return jsonify({"success": False, "error": "Không tìm thấy file kết quả ROI."}), 500
        
        with open("/tmp/roi.json", "r") as f:
            roi_result = json.load(f)
        
        logging.info(f"ROI result from /tmp/roi.json: {roi_result}")
        return jsonify(roi_result), 200 if roi_result["success"] else 400
    
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Hết thời gian chờ khi chạy script."}), 500
    except Exception as e:
        logging.error(f"Unexpected error in run-select-roi: {str(e)}")
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500
