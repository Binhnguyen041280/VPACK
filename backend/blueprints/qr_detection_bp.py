from flask import Blueprint, request, jsonify
from modules.technician.qr_detector import select_qr_roi
import subprocess
import os
import json
import logging
import sys

qr_detection_bp = Blueprint('qr_detection', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ FIXED: Use same path calculation as hand_detection_bp.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "CameraROI")

@qr_detection_bp.route('/select-qr-roi', methods=['POST'])
def select_qr_roi_endpoint():
    """
    ✅ MAIN ENDPOINT: Direct function call for QR ROI selection
    This is the recommended endpoint to use (no subprocess overhead)
    """
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId')
        roi_frame_path = data.get('roiFramePath')
        step = data.get('step', 'mvd')
        
        logger.debug(f"[MVD-DIRECT] Received data: {data}")
        logger.debug(f"[MVD-DIRECT] Parameters - video_path: {video_path}, camera_id: {camera_id}, roi_frame_path: {roi_frame_path}, step: {step}")
        
        # Input validation
        if not video_path or not camera_id or not roi_frame_path:
            logger.error("[MVD-DIRECT] Missing required parameters")
            return jsonify({"success": False, "error": "Thiếu videoPath, cameraId hoặc roiFramePath."}), 400
        
        logger.debug(f"[MVD-DIRECT] Checking video path exists: {video_path}")
        if not os.path.exists(video_path):
            logger.error(f"[MVD-DIRECT] Video path does not exist: {video_path}")
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        
        logger.debug(f"[MVD-DIRECT] Checking ROI frame path exists: {roi_frame_path}")
        if not os.path.exists(roi_frame_path):
            logger.error(f"[MVD-DIRECT] ROI frame path does not exist: {roi_frame_path}")
            return jsonify({"success": False, "error": "Đường dẫn ảnh tạm không tồn tại."}), 404
        
        # Clean up previous results
        if os.path.exists("/tmp/qr_roi.json"):
            logger.debug("[MVD-DIRECT] Removing existing /tmp/qr_roi.json")
            os.remove("/tmp/qr_roi.json")
            logger.info("[MVD-DIRECT] Đã xóa file /tmp/qr_roi.json để bắt đầu quy trình mới")
        
        logger.debug(f"[MVD-DIRECT] Calling select_qr_roi with video_path: {video_path}, camera_id: {camera_id}, roi_frame_path: {roi_frame_path}, step: {step}")
        result = select_qr_roi(video_path, camera_id, roi_frame_path, step)
        logger.debug(f"[MVD-DIRECT] select_qr_roi result: {result}")
        logger.info(f"[MVD-DIRECT] Completed MVD step for camera_id: {camera_id}")
        
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"[MVD-DIRECT] Exception in select_qr_roi_endpoint: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500

@qr_detection_bp.route('/run-qr-detector', methods=['POST'])
def run_qr_detector_endpoint():
    """
    ✅ SUBPROCESS ENDPOINT: Subprocess-based QR detection (use same approach as hand_detection_bp.py)
    """
    logger.warning("[MVD-SUBPROCESS] Using subprocess endpoint for GUI stability")
    
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId', 'default_camera')
        
        # Input validation
        if not video_path:
            logger.error("[MVD-SUBPROCESS] Missing videoPath parameter")
            return jsonify({"success": False, "error": "Thiếu videoPath."}), 400
        
        # Check video file exists
        if not os.path.exists(video_path):
            logger.error(f"[MVD-SUBPROCESS] Video file not found: {video_path}")
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        
        # Construct ROI frame path - use same pattern as roi_bp.py
        absolute_roi_frame_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_packing.jpg")
        
        if not os.path.exists(absolute_roi_frame_path):
            logger.error(f"[MVD-SUBPROCESS] ROI frame not found: {absolute_roi_frame_path}")
            return jsonify({"success": False, "error": "Đường dẫn ảnh packing không tồn tại."}), 404
        
        logger.info(f"[MVD-SUBPROCESS] Running qr_detector.py with video_path: {video_path}, camera_id: {camera_id}, roi_frame_path: {absolute_roi_frame_path}")
        
        # Clean up previous results
        if os.path.exists("/tmp/qr_roi.json"):
            os.remove("/tmp/qr_roi.json")
            logger.info("[MVD-SUBPROCESS] Cleaned up previous QR ROI results")
        
        logger.debug(f"[MVD-SUBPROCESS] BASE_DIR: {BASE_DIR}")
        logger.debug(f"[MVD-SUBPROCESS] BACKEND_DIR (working dir): {BACKEND_DIR}")
        
        # Check script exists
        script_path = os.path.join(BACKEND_DIR, "modules", "technician", "qr_detector.py")
        if not os.path.exists(script_path):
            logger.error(f"[MVD-SUBPROCESS] Script not found: {script_path}")
            return jsonify({"success": False, "error": f"Script {script_path} không tồn tại."}), 404
        
        try:
            # ✅ SIMPLE: Use same approach as hand_detection_bp.py (working)
            result = subprocess.run(
                ["python3", "modules/technician/qr_detector.py", video_path, camera_id, absolute_roi_frame_path],
                cwd=BACKEND_DIR,  # Working directory = backend/
                capture_output=True,
                text=True,
                timeout=300
            )
            
            logger.debug(f"[MVD-SUBPROCESS] Script exit code: {result.returncode}")
            logger.debug(f"[MVD-SUBPROCESS] Script stdout: {result.stdout}")
            logger.debug(f"[MVD-SUBPROCESS] Script stderr: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            logger.error("[MVD-SUBPROCESS] Script execution timeout")
            return jsonify({"success": False, "error": "Hết thời gian chờ khi chạy script (300s)."}), 500
        except FileNotFoundError as e:
            logger.error(f"[MVD-SUBPROCESS] Python executable not found: {e}")
            return jsonify({"success": False, "error": "Không tìm thấy Python executable."}), 500
        
        # Check execution result
        if result.returncode != 0:
            error_msg = f"Script failed with code {result.returncode}"
            if result.stderr:
                error_msg += f": {result.stderr}"
            if result.stdout:
                error_msg += f"\nOutput: {result.stdout}"
            
            logger.error(f"[MVD-SUBPROCESS] {error_msg}")
            return jsonify({
                "success": False, 
                "error": f"Lỗi khi chạy script (code {result.returncode})",
                "details": result.stderr,
                "stdout": result.stdout
            }), 500
        
        # Check result file exists
        if not os.path.exists("/tmp/qr_roi.json"):
            logger.error("[MVD-SUBPROCESS] QR ROI result file not created")
            logger.debug(f"[MVD-SUBPROCESS] Script stdout: {result.stdout}")
            return jsonify({
                "success": False, 
                "error": "Script chạy thành công nhưng không tạo file kết quả.",
                "stdout": result.stdout
            }), 500
        
        # Read and return result
        try:
            with open("/tmp/qr_roi.json", "r", encoding='utf-8') as f:
                qr_roi_result = json.load(f)
            
            logger.info(f"[MVD-SUBPROCESS] QR ROI result loaded successfully: {qr_roi_result.get('success', False)}")
            status_code = 200 if qr_roi_result.get("success", False) else 400
            return jsonify(qr_roi_result), status_code
            
        except json.JSONDecodeError as e:
            logger.error(f"[MVD-SUBPROCESS] Invalid JSON in result file: {e}")
            return jsonify({"success": False, "error": "File kết quả có định dạng JSON không hợp lệ."}), 500
        except Exception as e:
            logger.error(f"[MVD-SUBPROCESS] Error reading result file: {e}")
            return jsonify({"success": False, "error": f"Lỗi đọc file kết quả: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"[MVD-SUBPROCESS] Unexpected error in run-qr-detector: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500

@qr_detection_bp.route('/health', methods=['GET'])
def qr_health_check():
    """Health check endpoint for QR detection"""
    try:
        return jsonify({
            "status": "healthy",
            "endpoints": ["/select-qr-roi", "/run-qr-detector"],
            "camera_roi_dir": CAMERA_ROI_DIR,
            "camera_roi_dir_exists": os.path.exists(CAMERA_ROI_DIR),
            "base_dir": BASE_DIR,
            "backend_dir": BACKEND_DIR,
            "script_path": os.path.join(BACKEND_DIR, "modules", "technician", "qr_detector.py"),
            "script_exists": os.path.exists(os.path.join(BACKEND_DIR, "modules", "technician", "qr_detector.py"))
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500