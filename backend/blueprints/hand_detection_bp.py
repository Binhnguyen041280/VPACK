from flask import Blueprint, request, jsonify
from modules.technician.hand_detection import select_roi
import subprocess
import os
import json
import logging
import threading
import gc
import psutil
import sys

hand_detection_bp = Blueprint('hand_detection', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ NEW: Model Management & Threading Protection
class ModelManager:
    """Singleton pattern for managing AI models to prevent memory leaks"""
    _instance = None
    _lock = threading.Lock()
    _models_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.model_lock = threading.Lock()
            self.initialized = True
            logger.info("ModelManager initialized")
    
    def get_memory_usage(self):
        """Get current memory usage for monitoring"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024
        }
    
    def cleanup_memory(self):
        """Force garbage collection to free up memory"""
        gc.collect()
        memory_after = self.get_memory_usage()
        logger.info(f"Memory cleanup completed. Current usage: {memory_after['rss_mb']:.1f} MB")

# Global model manager instance
model_manager = ModelManager()

@hand_detection_bp.route('/select-roi', methods=['POST'])
def select_roi_endpoint():
    """
    ✅ MAIN ENDPOINT: Direct function call for ROI selection with hand detection
    This is the recommended endpoint to use (no subprocess overhead)
    """
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId')
        step = data.get('step', 'packing')
        
        logger.debug(f"[DIRECT] ROI selection - step: {step}, video: {video_path}, camera: {camera_id}")
        
        # Input validation
        if not video_path or not camera_id:
            logger.error("[DIRECT] Missing videoPath or cameraId")
            return jsonify({"success": False, "error": "Thiếu videoPath hoặc cameraId."}), 400
        
        if not os.path.exists(video_path):
            logger.error(f"[DIRECT] Video path does not exist: {video_path}")
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        
        # Clean up previous results
        if os.path.exists("/tmp/roi.json"):
            os.remove("/tmp/roi.json")
            logger.info("[DIRECT] Cleaned up previous ROI results")
        
        # ✅ Memory monitoring before processing
        memory_before = model_manager.get_memory_usage()
        logger.info(f"[DIRECT] Memory before processing: {memory_before['rss_mb']:.1f} MB")
        
        # ✅ Thread-safe model usage
        with model_manager.model_lock:
            logger.debug("[DIRECT] Acquired model lock, starting ROI selection")
            result = select_roi(video_path, camera_id, step)
            logger.debug(f"[DIRECT] ROI selection completed with result: {result}")
        
        # ✅ Memory monitoring after processing
        memory_after = model_manager.get_memory_usage()
        memory_diff = memory_after['rss_mb'] - memory_before['rss_mb']
        logger.info(f"[DIRECT] Memory after processing: {memory_after['rss_mb']:.1f} MB (diff: {memory_diff:+.1f} MB)")
        
        # ✅ Cleanup if memory usage increased significantly
        if memory_diff > 100:  # More than 100MB increase
            logger.warning(f"[DIRECT] High memory increase detected ({memory_diff:.1f} MB), cleaning up")
            model_manager.cleanup_memory()
        
        # Return result
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"[DIRECT] Exception in select_roi_endpoint: {str(e)}", exc_info=True)
        
        # ✅ Emergency memory cleanup on exception
        try:
            model_manager.cleanup_memory()
        except:
            pass
            
        return jsonify({
            "success": False, 
            "error": f"Lỗi hệ thống: {str(e)}"
        }), 500

@hand_detection_bp.route('/run-select-roi', methods=['POST'])
def run_select_roi_endpoint():
    """
    ✅ SUBPROCESS ENDPOINT: Subprocess-based ROI selection (sử dụng approach cũ - đã working)
    """
    logger.warning("[SUBPROCESS] Using subprocess endpoint for GUI stability")
    
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId', 'default_camera')
        step = data.get('step', 'packing')
        
        # Input validation
        if not video_path:
            logger.error("[SUBPROCESS] Missing videoPath parameter")
            return jsonify({"success": False, "error": "Thiếu videoPath."}), 400
        
        # Check video file exists
        if not os.path.exists(video_path):
            logger.error(f"[SUBPROCESS] Video file not found: {video_path}")
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404
        
        logger.info(f"[SUBPROCESS] Running hand_detection.py with video_path: {video_path}, camera_id: {camera_id}, step: {step}")
        
        # Clean up previous results
        if os.path.exists("/tmp/roi.json"):
            os.remove("/tmp/roi.json")
            logger.info("[SUBPROCESS] Cleaned up previous ROI results")
        
        # ✅ SIMPLE APPROACH: Use simple subprocess call like the old working version
        # Working directory sẽ là backend/ để có thể access modules/
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        BACKEND_DIR = os.path.join(BASE_DIR, "backend")
        
        logger.debug(f"[SUBPROCESS] BASE_DIR: {BASE_DIR}")
        logger.debug(f"[SUBPROCESS] BACKEND_DIR (working dir): {BACKEND_DIR}")
        
        # Check script exists
        script_path = os.path.join(BACKEND_DIR, "modules", "technician", "hand_detection.py")
        if not os.path.exists(script_path):
            logger.error(f"[SUBPROCESS] Script not found: {script_path}")
            return jsonify({"success": False, "error": f"Script {script_path} không tồn tại."}), 404
        
        try:
            # ✅ SIMPLE: Use same approach as old working qr_detection_bp.py
            result = subprocess.run(
                ["python3", "modules/technician/hand_detection.py", video_path, camera_id, step],
                cwd=BACKEND_DIR,  # Working directory = backend/
                capture_output=True,
                text=True,
                timeout=300
            )
            
            logger.debug(f"[SUBPROCESS] Script exit code: {result.returncode}")
            logger.debug(f"[SUBPROCESS] Script stdout: {result.stdout}")
            logger.debug(f"[SUBPROCESS] Script stderr: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            logger.error("[SUBPROCESS] Script execution timeout")
            return jsonify({"success": False, "error": "Hết thời gian chờ khi chạy script (300s)."}), 500
        except FileNotFoundError as e:
            logger.error(f"[SUBPROCESS] Python executable not found: {e}")
            return jsonify({"success": False, "error": "Không tìm thấy Python executable."}), 500
        
        # Check execution result
        if result.returncode != 0:
            error_msg = f"Script failed with code {result.returncode}"
            if result.stderr:
                error_msg += f": {result.stderr}"
            if result.stdout:
                error_msg += f"\nOutput: {result.stdout}"
            
            logger.error(f"[SUBPROCESS] {error_msg}")
            return jsonify({
                "success": False, 
                "error": f"Lỗi khi chạy script (code {result.returncode})",
                "details": result.stderr,
                "stdout": result.stdout
            }), 500
        
        # Check result file exists
        if not os.path.exists("/tmp/roi.json"):
            logger.error("[SUBPROCESS] ROI result file not created")
            logger.debug(f"[SUBPROCESS] Script stdout: {result.stdout}")
            return jsonify({
                "success": False, 
                "error": "Script chạy thành công nhưng không tạo file kết quả.",
                "stdout": result.stdout
            }), 500
        
        # Read and return result
        try:
            with open("/tmp/roi.json", "r", encoding='utf-8') as f:
                roi_result = json.load(f)
            
            logger.info(f"[SUBPROCESS] ROI result loaded successfully: {roi_result.get('success', False)}")
            status_code = 200 if roi_result.get("success", False) else 400
            return jsonify(roi_result), status_code
            
        except json.JSONDecodeError as e:
            logger.error(f"[SUBPROCESS] Invalid JSON in result file: {e}")
            return jsonify({"success": False, "error": "File kết quả có định dạng JSON không hợp lệ."}), 500
        except Exception as e:
            logger.error(f"[SUBPROCESS] Error reading result file: {e}")
            return jsonify({"success": False, "error": f"Lỗi đọc file kết quả: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"[SUBPROCESS] Unexpected error in run-select-roi: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500

@hand_detection_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with memory monitoring"""
    try:
        memory_usage = model_manager.get_memory_usage()
        return jsonify({
            "status": "healthy",
            "memory_usage_mb": memory_usage['rss_mb'],
            "model_manager_initialized": hasattr(model_manager, 'initialized')
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@hand_detection_bp.route('/cleanup', methods=['POST'])
def manual_cleanup():
    """Manual memory cleanup endpoint for debugging"""
    try:
        memory_before = model_manager.get_memory_usage()
        model_manager.cleanup_memory()
        memory_after = model_manager.get_memory_usage()
        
        return jsonify({
            "success": True,
            "memory_before_mb": memory_before['rss_mb'],
            "memory_after_mb": memory_after['rss_mb'],
            "memory_freed_mb": memory_before['rss_mb'] - memory_after['rss_mb']
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500