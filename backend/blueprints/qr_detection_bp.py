from flask import Blueprint, request, jsonify
from modules.technician.qr_detector import select_qr_roi, detect_qr_at_time, preprocess_video_qr, detect_qr_from_image
import subprocess
import os
import json
import logging
import sys
import threading
import time
import hashlib
from datetime import datetime, timedelta

qr_detection_bp = Blueprint('qr_detection', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# In-memory cache for pre-processed QR detections (same pattern as hand detection)
# Structure: {cache_key: {'detections': [...], 'metadata': {...}, 'expires_at': datetime}}
qr_preprocessing_cache = {}
qr_preprocessing_progress = {}  # Track progress for ongoing processing

# ✅ FIXED: Use same path calculation as hand_detection_bp.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "CameraROI")

def generate_qr_cache_key(video_path: str, roi_config: dict) -> str:
    """Generate unique cache key for video + ROI combination"""
    roi_str = f"{roi_config['x']}_{roi_config['y']}_{roi_config['w']}_{roi_config['h']}"
    cache_input = f"{video_path}_{roi_str}"
    return hashlib.md5(cache_input.encode()).hexdigest()

def cleanup_expired_qr_cache():
    """Remove expired QR cache entries"""
    global qr_preprocessing_cache
    
    now = datetime.now()
    expired_keys = [
        key for key, cache_data in qr_preprocessing_cache.items()
        if cache_data.get('expires_at', now) <= now
    ]
    
    for key in expired_keys:
        del qr_preprocessing_cache[key]
        logger.info(f"Removed expired QR cache entry: {key}")

@qr_detection_bp.route('/preprocess-video', methods=['POST'])
def preprocess_qr_video():
    """
    Pre-process entire video for QR detection at 5fps
    Results are cached for perfect synchronization during playback
    
    Request body:
    {
        "video_path": str,
        "roi_config": {
            "x": int, "y": int, "w": int, "h": int
        },
        "fps": int (optional, default 5)
    }
    
    Response:
    {
        "success": bool,
        "cache_key": str,
        "status": "started" | "completed" | "in_progress",
        "progress": float (0-100),
        "detections": list (if completed),
        "metadata": dict (if completed),
        "error": str (if error)
    }
    """
    try:
        # Clean up expired cache first
        cleanup_expired_qr_cache()
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate required parameters
        video_path = data.get('video_path')
        roi_config = data.get('roi_config')
        fps = data.get('fps', 5)  # Default 5fps
        
        if not video_path:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: video_path"
            }), 400
            
        if not roi_config:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: roi_config"
            }), 400
        
        # Validate ROI config
        required_roi_fields = ['x', 'y', 'w', 'h']
        for field in required_roi_fields:
            if field not in roi_config:
                return jsonify({
                    "success": False,
                    "error": f"Missing ROI field: {field}"
                }), 400
            try:
                roi_config[field] = int(roi_config[field])
                if roi_config[field] < 0:
                    raise ValueError(f"ROI {field} must be non-negative")
            except (ValueError, TypeError) as e:
                return jsonify({
                    "success": False,
                    "error": f"Invalid ROI {field} value: {str(e)}"
                }), 400
        
        # Validate fps
        try:
            fps = int(fps)
            if fps <= 0 or fps > 30:
                raise ValueError("fps must be between 1 and 30")
        except (ValueError, TypeError) as e:
            return jsonify({
                "success": False,
                "error": f"Invalid fps value: {str(e)}"
            }), 400
        
        # Generate cache key
        cache_key = generate_qr_cache_key(video_path, roi_config)
        
        # Check if already cached and not expired
        if cache_key in qr_preprocessing_cache:
            cache_data = qr_preprocessing_cache[cache_key]
            if cache_data.get('expires_at', datetime.now()) > datetime.now():
                logger.info(f"Returning cached QR results for {cache_key}")
                return jsonify({
                    "success": True,
                    "cache_key": cache_key,
                    "status": "completed",
                    "progress": 100.0,
                    "detections": cache_data['detections'],
                    "metadata": cache_data['metadata']
                }), 200
        
        # Check if processing is already in progress
        if cache_key in qr_preprocessing_progress:
            progress_data = qr_preprocessing_progress[cache_key]
            return jsonify({
                "success": True,
                "cache_key": cache_key,
                "status": "in_progress",
                "progress": progress_data.get('progress', 0.0),
                "estimated_completion": progress_data.get('estimated_completion')
            }), 202  # 202 Accepted - Processing
        
        # Start background processing
        def background_qr_processing():
            try:
                # Initialize progress tracking - simplified
                qr_preprocessing_progress[cache_key] = {
                    'progress': 0.0,
                    'started_at': datetime.now(),
                    'estimated_completion': None,
                    'processed_count': 0,
                    'total_frames': 0
                }
                
                # Initialize main cache entry for progressive accumulation
                qr_preprocessing_cache[cache_key] = {
                    'detections': [],  # Start with empty list to accumulate
                    'metadata': {
                        'partial_results': True,
                        'progress': 0.0,
                        'processed_count': 0,
                        'total_frames': 0
                    },
                    'expires_at': datetime.now() + timedelta(minutes=30),
                    'processed_at': datetime.now()
                }
                
                # Progress callback function - simplified with skip-to-end logic
                def update_qr_progress(progress, processed_count, total_frames, new_detections=None):
                    # Check for cancellation flag and trigger skip-to-end
                    if cache_key not in qr_preprocessing_progress:
                        logger.info(f"QR preprocessing cancelled - progress tracking removed for {cache_key}")
                        raise Exception(f"QR preprocessing cancelled for {cache_key}")
                    
                    if qr_preprocessing_progress[cache_key].get('cancelled', False):
                        logger.info(f"QR preprocessing skip-to-end triggered for {cache_key}")
                        raise Exception(f"QR preprocessing cancelled for {cache_key}")
                    
                    qr_preprocessing_progress[cache_key].update({
                        'progress': progress,
                        'processed_count': processed_count,
                        'total_frames': total_frames
                    })
                    
                    # Accumulate new detections into main cache (không overwrite)
                    if new_detections and len(new_detections) > 0:
                        if cache_key in qr_preprocessing_cache:
                            # Append new detections to existing list instead of replacing
                            qr_preprocessing_cache[cache_key]['detections'].extend(new_detections)
                            qr_preprocessing_cache[cache_key]['metadata'].update({
                                'progress': progress,
                                'processed_count': processed_count,
                                'total_frames': total_frames
                            })
                            total_detections = len(qr_preprocessing_cache[cache_key]['detections'])
                            logger.debug(f"QR: Accumulated {len(new_detections)} new detections. Total: {total_detections} for {cache_key}")
                        else:
                            logger.warning(f"QR: Cache key {cache_key} not found during update")
                
                logger.info(f"Starting QR video pre-processing for cache key: {cache_key}")
                
                # Call the QR pre-processing function with progress callback
                result = preprocess_video_qr(video_path, roi_config, fps, progress_callback=update_qr_progress)
                
                if result.get('success'):
                    # Cache the results for 30 minutes
                    expires_at = datetime.now() + timedelta(minutes=30)
                    qr_preprocessing_cache[cache_key] = {
                        'detections': result['detections'],
                        'metadata': result['metadata'],
                        'expires_at': expires_at,
                        'processed_at': datetime.now()
                    }
                    
                    total_qr_detections = sum(d.get('qr_count', 0) for d in result['detections'])
                    logger.info(f"QR pre-processing completed for {cache_key}: {len(result['detections'])} timeline entries, {total_qr_detections} QR detections cached")
                else:
                    if "cancelled" in str(result.get('error', '')).lower():
                        logger.info(f"QR pre-processing cancelled for {cache_key}: {result.get('error')}")
                    else:
                        logger.error(f"QR pre-processing failed for {cache_key}: {result.get('error')}")
                
                # Clean up progress tracking
                if cache_key in qr_preprocessing_progress:
                    del qr_preprocessing_progress[cache_key]
                    
            except Exception as e:
                if "cancelled" in str(e).lower():
                    logger.info(f"Background QR processing cancelled for {cache_key}: {str(e)}")
                else:
                    logger.error(f"Background QR processing error for {cache_key}: {str(e)}")
                if cache_key in qr_preprocessing_progress:
                    del qr_preprocessing_progress[cache_key]
        
        # Start processing in background thread
        thread = threading.Thread(target=background_qr_processing, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "cache_key": cache_key,
            "status": "started",
            "progress": 0.0,
            "message": f"QR pre-processing started for video at {fps}fps",
            "estimated_duration_seconds": "10-30"  # Rough estimate
        }), 202  # 202 Accepted - Processing started
        
    except Exception as e:
        error_msg = f"Unexpected error in QR preprocess-video endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@qr_detection_bp.route('/preprocess-status/<cache_key>', methods=['GET'])
def qr_preprocess_status(cache_key: str):
    """
    Check status of QR video pre-processing
    
    Response:
    {
        "success": bool,
        "status": "completed" | "in_progress" | "not_found",
        "progress": float (0-100),
        "detections": list (if completed),
        "metadata": dict (if completed),
        "error": str (if error)
    }
    """
    try:
        cleanup_expired_qr_cache()
        
        # Check if completed and cached
        if cache_key in qr_preprocessing_cache:
            cache_data = qr_preprocessing_cache[cache_key]
            if cache_data.get('expires_at', datetime.now()) > datetime.now():
                return jsonify({
                    "success": True,
                    "status": "completed",
                    "progress": 100.0,
                    "detections": cache_data['detections'],
                    "metadata": cache_data['metadata'],
                    "processed_at": cache_data['processed_at'].isoformat(),
                    "expires_at": cache_data['expires_at'].isoformat()
                }), 200
        
        # Check if still in progress
        if cache_key in qr_preprocessing_progress:
            progress_data = qr_preprocessing_progress[cache_key]
            return jsonify({
                "success": True,
                "status": "in_progress",
                "progress": progress_data.get('progress', 0.0),
                "processed_count": progress_data.get('processed_count', 0),
                "total_frames": progress_data.get('total_frames', 0),
                "started_at": progress_data['started_at'].isoformat(),
                "estimated_completion": progress_data.get('estimated_completion')
            }), 200
        
        # Not found
        return jsonify({
            "success": False,
            "status": "not_found",
            "error": f"No QR processing found for cache key: {cache_key}"
        }), 404
        
    except Exception as e:
        error_msg = f"Error checking QR preprocess status: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@qr_detection_bp.route('/get-cached-qr', methods=['POST'])
def get_cached_qr():
    """
    Get QR detections for specific timestamp from cached results
    
    Request body:
    {
        "cache_key": str,
        "timestamp": float,
        "canvas_dims": {  # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "video_dims": {   # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "roi_config": {   # optional - for display coordinate mapping
            "x": int,
            "y": int,
            "w": int,
            "h": int
        }
    }
    
    Response:
    {
        "success": bool,
        "qr_detections": list | null,
        "canvas_qr_detections": list | null,  # NEW - display-ready coordinates
        "exact_match": bool,
        "matched_timestamp": float | null,
        "qr_count": int,
        "error": str (if error)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        cache_key = data.get('cache_key')
        timestamp = data.get('timestamp')
        canvas_dims = data.get('canvas_dims')
        video_dims = data.get('video_dims')
        roi_config = data.get('roi_config')
        
        if not cache_key:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: cache_key"
            }), 400
            
        if timestamp is None:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: timestamp"
            }), 400
        
        try:
            timestamp = float(timestamp)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "Invalid timestamp value"
            }), 400
        
        # Check main cache
        if cache_key not in qr_preprocessing_cache:
            return jsonify({
                "success": False,
                "error": "QR cache key not found or expired"
            }), 404
        
        cache_data = qr_preprocessing_cache[cache_key]
        if cache_data.get('expires_at', datetime.now()) <= datetime.now():
            del qr_preprocessing_cache[cache_key]
            return jsonify({
                "success": False,
                "error": "QR cache expired"
            }), 404
        
        # Find QR detections for timestamp (exact match within 0.15s tolerance)
        detections = cache_data['detections']
        closest_detection = None
        min_time_diff = float('inf')
        
        for detection in detections:
            time_diff = abs(detection['timestamp'] - timestamp)
            if time_diff < 0.15 and time_diff < min_time_diff:  # 0.15s tolerance for 5fps (0.2s interval)
                closest_detection = detection
                min_time_diff = time_diff
        
        if closest_detection:
            qr_detections = closest_detection.get('qr_detections', [])
            qr_count = closest_detection.get('qr_count', 0)
            
            response = {
                "success": True,
                "qr_detections": qr_detections,
                "exact_match": min_time_diff < 0.05,  # Consider <0.05s as exact match
                "matched_timestamp": closest_detection['timestamp'],
                "qr_count": qr_count,
                "time_difference": round(min_time_diff, 3)
            }
            
            # Add canvas_qr_detections using LandmarkMapper for consistent coordinate transformation
            if canvas_dims and video_dims and roi_config and qr_detections:
                try:
                    from modules.technician.landmark_mapper import LandmarkMapper, ROIConfig, VideoDimensions, CanvasDimensions
                    
                    # Create mapping objects
                    roi = ROIConfig(
                        x=roi_config['x'],
                        y=roi_config['y'],
                        w=roi_config['w'],
                        h=roi_config['h']
                    )
                    video_dimensions = VideoDimensions(
                        width=video_dims['width'],
                        height=video_dims['height']
                    )
                    canvas_dimensions = CanvasDimensions(
                        width=canvas_dims['width'],
                        height=canvas_dims['height']
                    )
                    
                    # Use LandmarkMapper for coordinate transformation
                    qr_mapping_response = LandmarkMapper.create_canvas_qr_response(
                        qr_detections, roi, video_dimensions, canvas_dimensions
                    )
                    
                    if qr_mapping_response['success']:
                        response['canvas_qr_detections'] = qr_mapping_response['canvas_qr_detections']
                        response['mapping_algorithm'] = qr_mapping_response['mapping_algorithm']
                        response['mapping_info'] = qr_mapping_response['mapping_info']
                        logger.debug(f"LandmarkMapper: Mapped {len(qr_mapping_response['canvas_qr_detections'])} QR detections for timestamp {timestamp}")
                    else:
                        logger.warning(f"LandmarkMapper QR mapping failed: {qr_mapping_response.get('error')}")
                        response['canvas_qr_detections'] = []
                        
                except Exception as e:
                    logger.error(f"Error using LandmarkMapper for QR coordinate mapping: {e}")
                    response['canvas_qr_detections'] = []
            else:
                response['canvas_qr_detections'] = []
            
            return jsonify(response), 200
        else:
            return jsonify({
                "success": True,
                "qr_detections": [],
                "canvas_qr_detections": [],
                "exact_match": False,
                "matched_timestamp": None,
                "qr_count": 0,
                "message": f"No QR detection found near timestamp {timestamp}"
            }), 200
        
    except Exception as e:
        error_msg = f"Error getting cached QR detections: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

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

@qr_detection_bp.route('/test', methods=['GET'])
def test_qr_endpoint():
    """Test endpoint with sample video for QR detection development"""
    try:
        # Use the test video from the project
        test_video = "/Users/annhu/vtrack_app/V_Track/resources/Inputvideo/Cam1D/Cam1D_20250604_110517.mp4"
        test_time = 5.0  # Test at 5 seconds
        
        # Test ROI (center area)
        test_roi = {
            "x": 200,
            "y": 150, 
            "w": 400,
            "h": 300
        }
        
        logger.info(f"Running test QR detection at {test_time}s with ROI {test_roi}")
        
        result = detect_qr_at_time(
            video_path=test_video,
            time_seconds=test_time,
            roi_config=test_roi
        )
        
        return jsonify({
            "test_status": "completed",
            "test_video": test_video,
            "test_time": test_time,
            "test_roi": test_roi,
            "result": result
        }), 200
        
    except Exception as e:
        error_msg = f"Test QR endpoint error: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "test_status": "failed",
            "error": error_msg
        }), 500

@qr_detection_bp.route('/get-cached-trigger', methods=['POST'])
def get_cached_trigger():
    """
    Get QR trigger detections for specific timestamp from cached results
    Specifically looks for "timego" text in QR codes within trigger area
    
    Request body:
    {
        "cache_key": str,  # Can include "_trigger" suffix for trigger-specific cache
        "timestamp": float,
        "canvas_dims": {  # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "video_dims": {   # optional - for display coordinate mapping
            "width": int,
            "height": int
        },
        "roi_config": {   # trigger area ROI coordinates
            "x": int,
            "y": int,
            "w": int,
            "h": int
        },
        "trigger_mode": bool,  # Flag to indicate trigger detection mode
        "target_text": str     # Text to search for (default: "TimeGo")
    }
    
    Response:
    {
        "success": bool,
        "trigger_detected": bool,
        "trigger_text": str | null,
        "qr_detections": list,     # All QR detections in trigger area
        "canvas_qr_detections": list,  # Display-ready coordinates
        "exact_match": bool,
        "matched_timestamp": float | null,
        "detection_confidence": float,
        "error": str (if error)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        cache_key = data.get('cache_key')
        timestamp = data.get('timestamp')
        canvas_dims = data.get('canvas_dims')
        video_dims = data.get('video_dims')
        roi_config = data.get('roi_config')
        trigger_mode = data.get('trigger_mode', True)
        target_text = data.get('target_text', 'TimeGo').lower()  # Default to "TimeGo", convert to lowercase for comparison
        
        if not cache_key:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: cache_key"
            }), 400
            
        if timestamp is None:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: timestamp"
            }), 400
        
        try:
            timestamp = float(timestamp)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "Invalid timestamp value"
            }), 400
        
        # Remove "_trigger" suffix from cache key if present for main cache lookup
        main_cache_key = cache_key.replace('_trigger', '') if cache_key.endswith('_trigger') else cache_key
        
        # Check main QR cache (trigger detection uses same QR preprocessing)
        if main_cache_key not in qr_preprocessing_cache:
            return jsonify({
                "success": False,
                "error": "QR cache key not found or expired",
                "trigger_detected": False,
                "trigger_text": None
            }), 404
        
        cache_data = qr_preprocessing_cache[main_cache_key]
        if cache_data.get('expires_at', datetime.now()) <= datetime.now():
            del qr_preprocessing_cache[main_cache_key]
            return jsonify({
                "success": False,
                "error": "QR cache expired",
                "trigger_detected": False,
                "trigger_text": None
            }), 404
        
        # Find QR detections for timestamp (exact match within 0.15s tolerance)
        detections = cache_data['detections']
        closest_detection = None
        min_time_diff = float('inf')
        
        for detection in detections:
            time_diff = abs(detection['timestamp'] - timestamp)
            if time_diff < 0.15 and time_diff < min_time_diff:  # 0.15s tolerance for 5fps
                closest_detection = detection
                min_time_diff = time_diff
        
        if closest_detection:
            qr_detections = closest_detection.get('qr_detections', [])
            
            # Filter QR detections for trigger area and search for target text
            trigger_detected = False
            trigger_text = None
            detection_confidence = 0.0
            trigger_qr_detections = []
            
            if roi_config and qr_detections:
                # Filter QR detections that fall within trigger ROI area
                trigger_x, trigger_y, trigger_w, trigger_h = roi_config['x'], roi_config['y'], roi_config['w'], roi_config['h']
                
                for qr_detection in qr_detections:
                    qr_bbox = qr_detection.get('bbox', {})
                    if not qr_bbox:
                        continue
                    
                    # Check if QR detection bbox overlaps with trigger ROI
                    qr_x, qr_y, qr_w, qr_h = qr_bbox.get('x', 0), qr_bbox.get('y', 0), qr_bbox.get('w', 0), qr_bbox.get('h', 0)
                    
                    # Check for overlap between QR bbox and trigger ROI
                    overlap_x = max(0, min(trigger_x + trigger_w, qr_x + qr_w) - max(trigger_x, qr_x))
                    overlap_y = max(0, min(trigger_y + trigger_h, qr_y + qr_h) - max(trigger_y, qr_y))
                    overlap_area = overlap_x * overlap_y
                    
                    if overlap_area > 0:  # QR detection is within trigger area
                        trigger_qr_detections.append(qr_detection)
                        
                        # Check if QR text contains target text
                        qr_text = qr_detection.get('text', '').lower()
                        if target_text in qr_text:
                            trigger_detected = True
                            trigger_text = qr_detection.get('text', '')
                            detection_confidence = qr_detection.get('confidence', 0.0)
                            logger.info(f"Trigger detected: '{trigger_text}' at timestamp {timestamp}")
                            break
            
            response = {
                "success": True,
                "trigger_detected": trigger_detected,
                "trigger_text": trigger_text,
                "qr_detections": trigger_qr_detections,
                "exact_match": min_time_diff < 0.05,
                "matched_timestamp": closest_detection['timestamp'],
                "detection_confidence": detection_confidence,
                "time_difference": round(min_time_diff, 3),
                "target_text": target_text,
                "trigger_roi": roi_config,
                "total_qr_in_area": len(trigger_qr_detections)
            }
            
            # Add canvas_qr_detections for trigger area QR codes
            if canvas_dims and video_dims and roi_config and trigger_qr_detections:
                try:
                    from modules.technician.landmark_mapper import LandmarkMapper, ROIConfig, VideoDimensions, CanvasDimensions
                    
                    # Create mapping objects for trigger ROI
                    roi = ROIConfig(
                        x=roi_config['x'],
                        y=roi_config['y'],
                        w=roi_config['w'],
                        h=roi_config['h']
                    )
                    video_dimensions = VideoDimensions(
                        width=video_dims['width'],
                        height=video_dims['height']
                    )
                    canvas_dimensions = CanvasDimensions(
                        width=canvas_dims['width'],
                        height=canvas_dims['height']
                    )
                    
                    # Use LandmarkMapper for coordinate transformation
                    qr_mapping_response = LandmarkMapper.create_canvas_qr_response(
                        trigger_qr_detections, roi, video_dimensions, canvas_dimensions
                    )
                    
                    if qr_mapping_response['success']:
                        response['canvas_qr_detections'] = qr_mapping_response['canvas_qr_detections']
                        response['mapping_algorithm'] = qr_mapping_response['mapping_algorithm']
                        response['mapping_info'] = qr_mapping_response['mapping_info']
                        logger.debug(f"LandmarkMapper: Mapped {len(qr_mapping_response['canvas_qr_detections'])} trigger QR detections for timestamp {timestamp}")
                    else:
                        logger.warning(f"LandmarkMapper trigger QR mapping failed: {qr_mapping_response.get('error')}")
                        response['canvas_qr_detections'] = []
                        
                except Exception as e:
                    logger.error(f"Error using LandmarkMapper for trigger QR coordinate mapping: {e}")
                    response['canvas_qr_detections'] = []
            else:
                response['canvas_qr_detections'] = []
            
            return jsonify(response), 200
        else:
            return jsonify({
                "success": True,
                "trigger_detected": False,
                "trigger_text": None,
                "qr_detections": [],
                "canvas_qr_detections": [],
                "exact_match": False,
                "matched_timestamp": None,
                "detection_confidence": 0.0,
                "message": f"No QR detection found near timestamp {timestamp}"
            }), 200
        
    except Exception as e:
        error_msg = f"Error getting cached trigger detections: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg,
            "trigger_detected": False,
            "trigger_text": None
        }), 500

@qr_detection_bp.route('/detect-qr-image', methods=['POST'])
def detect_qr_from_uploaded_image():
    """
    Detect QR codes from uploaded image using WeChat QRCode model

    Request JSON:
    {
        "image_content": "base64_string",
        "image_name": "filename.jpg" (optional)
    }

    Response JSON:
    {
        "success": bool,
        "qr_detections": [str] - Array of detected QR code texts,
        "qr_count": int,
        "image_name": str (if provided),
        "error": str (if success=False)
    }
    """
    try:
        # Get request data
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400

        image_content = data.get('image_content')
        image_name = data.get('image_name', 'unknown.jpg')

        if not image_content:
            return jsonify({
                "success": False,
                "error": "image_content is required"
            }), 400

        logger.info(f"[QR-IMAGE] Processing image: {image_name}")

        # Call the QR detection function
        result = detect_qr_from_image(image_content)

        # Add image name to response
        if result.get('success'):
            result['image_name'] = image_name
            logger.info(f"[QR-IMAGE] Success: {result.get('qr_count', 0)} QR codes detected in {image_name}")
        else:
            logger.warning(f"[QR-IMAGE] Failed: {result.get('error', 'Unknown error')} for {image_name}")

        return jsonify(result), 200 if result.get('success') else 400

    except Exception as e:
        error_msg = f"Image QR detection endpoint error: {str(e)}"
        logger.error(f"[QR-IMAGE] {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@qr_detection_bp.route('/health', methods=['GET'])
def qr_health_check():
    """Health check endpoint for QR detection"""
    try:
        cleanup_expired_qr_cache()
        
        return jsonify({
            "status": "healthy",
            "service": "qr_detection",
            "version": "2.0_preprocessing",
            "endpoints": [
                "POST /select-qr-roi - Manual QR ROI selection (legacy)",
                "POST /run-qr-detector - Subprocess QR detection (legacy)",
                "POST /preprocess-video - Pre-process entire video at 5fps",
                "GET /preprocess-status/<cache_key> - Check preprocessing progress",
                "POST /get-cached-qr - Get QR detections from cache by timestamp",
                "POST /get-cached-trigger - Get QR trigger detections (search for 'TimeGo')",
                "POST /detect-qr-image - Detect QR codes from uploaded image",
                "GET /test - Test QR detection with sample video",
                "GET /health - Health check"
            ],
            "cache_status": {
                "active_cache_entries": len(qr_preprocessing_cache),
                "active_processing_jobs": len(qr_preprocessing_progress),
                "total_cached_detections": sum(
                    len(cache_data.get('detections', []))
                    for cache_data in qr_preprocessing_cache.values()
                ),
                "cache_ttl_minutes": 30
            },
            "features": [
                "5fps QR video preprocessing",
                "Perfect timestamp synchronization", 
                "Dynamic QR bbox mapping to canvas",
                "QR trigger detection for 'TimeGo' text",
                "Trigger area ROI filtering",
                "Automatic cache expiration",
                "Background processing",
                "WeChat QR model integration"
            ],
            "camera_roi_dir": CAMERA_ROI_DIR,
            "camera_roi_dir_exists": os.path.exists(CAMERA_ROI_DIR),
            "base_dir": BASE_DIR,
            "backend_dir": BACKEND_DIR,
            "script_path": os.path.join(BACKEND_DIR, "modules", "technician", "qr_detector.py"),
            "script_exists": os.path.exists(os.path.join(BACKEND_DIR, "modules", "technician", "qr_detector.py")),
            "description": "Advanced QR detection with preprocessing and caching for perfect video synchronization"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500