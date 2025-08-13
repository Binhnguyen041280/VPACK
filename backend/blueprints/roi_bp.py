from flask import Blueprint, request, jsonify, send_file, make_response
from modules.technician.hand_detection import finalize_roi
import os
import glob
import json
import sqlite3
from datetime import datetime
import logging

roi_bp = Blueprint('roi', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# ✅ CORRECTED: Path calculation to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Go up to project root V_Track/
DB_PATH = os.path.join(BASE_DIR, "backend", "database", "events.db")
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "resources", "output_clips", "CameraROI")

# ✅ FIXED: Proper OPTIONS handler with explicit return
@roi_bp.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, Cache-Control, Pragma, Expires")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response
    # ✅ FIXED: Explicit None return to avoid implicit None
    return None

# ✅ NEW: Missing /run-select-roi endpoint
@roi_bp.route('/run-select-roi', methods=['POST', 'OPTIONS'])
def run_select_roi():
    """Execute hand detection ROI selection subprocess"""
    try:
        data = request.get_json()
        logging.info(f"[RUN-SELECT-ROI] Received data: {data}")
        
        video_path = data.get('video_path') or data.get('videoPath')
        camera_id = data.get('camera_id') or data.get('cameraId') 
        step = data.get('step', 'packing')
        
        if not video_path or not camera_id:
            return jsonify({
                "success": False, 
                "error": "video_path and camera_id required"
            }), 400
        
        if not os.path.exists(video_path):
            return jsonify({
                "success": False,
                "error": f"Video file not found: {video_path}"
            }), 404
        
        # Import and call hand detection directly
        try:
            from modules.technician.hand_detection import select_roi
            
            logging.info(f"[RUN-SELECT-ROI] Calling select_roi with: video_path={video_path}, camera_id={camera_id}, step={step}")
            
            # Call the hand detection function
            result = select_roi(video_path, camera_id, step)
            
            logging.info(f"[RUN-SELECT-ROI] select_roi result: {result}")
            
            if result.get("success"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400
                
        except ImportError as e:
            logging.error(f"[RUN-SELECT-ROI] Import error: {e}")
            return jsonify({
                "success": False,
                "error": f"Module import failed: {str(e)}"
            }), 500
        except Exception as e:
            logging.error(f"[RUN-SELECT-ROI] Function call error: {e}")
            return jsonify({
                "success": False,
                "error": f"Hand detection failed: {str(e)}"
            }), 500
            
    except Exception as e:
        logging.error(f"[RUN-SELECT-ROI] Exception: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"System error: {str(e)}"
        }), 500

@roi_bp.route('/finalize-roi', methods=['POST', 'OPTIONS'])
def finalize_roi_endpoint():
    try:
        data = request.get_json()
        video_path = data.get('videoPath')
        camera_id = data.get('cameraId')
        rois = data.get('rois')

        if not video_path or not camera_id or not rois:
            return jsonify({"success": False, "error": "Thiếu videoPath, cameraId hoặc rois."}), 400

        if not os.path.exists(video_path):
            return jsonify({"success": False, "error": "Đường dẫn video không tồn tại."}), 404

        packing_roi = [0, 0, 0, 0]
        if os.path.exists("/tmp/roi.json"):
            with open("/tmp/roi.json", "r") as f:
                roi_data = json.load(f)
                if roi_data.get("success") and "roi" in roi_data:
                    packing_roi = [roi_data["roi"]["x"], roi_data["roi"]["y"], roi_data["roi"]["w"], roi_data["roi"]["h"]]
        
        qr_mvd_area = [0, 0, 0, 0]
        qr_trigger_area = [0, 0, 0, 0]
        table_type = None
        if os.path.exists("/tmp/qr_roi.json"):
            with open("/tmp/qr_roi.json", "r") as f:
                qr_roi_data = json.load(f)
                table_type = qr_roi_data.get("table_type")
                for roi in rois:
                    if roi["type"] == "mvd":
                        qr_mvd_area = [roi["x"], roi["y"], roi["w"], roi["h"]]
                    elif roi["type"] == "trigger" and table_type == "standard":
                        qr_trigger_area = [roi["x"], roi["y"], roi["w"], roi["h"]]

        profile_name = camera_id
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM packing_profiles WHERE profile_name = ?", (profile_name,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
                UPDATE packing_profiles
                SET qr_trigger_area = ?, qr_motion_area = ?, qr_mvd_area = ?, packing_area = ?,
                    min_packing_time = ?, jump_time_ratio = ?, scan_mode = ?, fixed_threshold = ?, margin = ?, additional_params = ?, mvd_jump_ratio = ?
                WHERE profile_name = ?
            ''', (
                json.dumps(qr_trigger_area),
                None,  # qr_motion_area
                json.dumps(qr_mvd_area),
                json.dumps(packing_roi),
                10, 0.5, "full", 20, 60, json.dumps({}),
                None,  # mvd_jump_ratio
                profile_name
            ))
        else:
            cursor.execute('''
                INSERT INTO packing_profiles (
                    profile_name, qr_trigger_area, qr_motion_area, qr_mvd_area, packing_area,
                    min_packing_time, jump_time_ratio, scan_mode, fixed_threshold, margin, additional_params, mvd_jump_ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile_name,
                json.dumps(qr_trigger_area),
                None,  # qr_motion_area
                json.dumps(qr_mvd_area),
                json.dumps(packing_roi),
                10, 0.5, "full", 20, 60, json.dumps({}),
                None   # mvd_jump_ratio
            ))
        conn.commit()
        conn.close()
        logging.info(f"Lưu ROI vào packing_profiles với profile_name: {profile_name}")

        result = finalize_roi(video_path, camera_id, rois)
        return jsonify(result), 200 if result["success"] else 400

    except Exception as e:
        logging.error(f"Exception in finalize_roi_endpoint: {str(e)}")
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500

@roi_bp.route('/get-roi-frame', methods=['GET', 'OPTIONS'])
def get_roi_frame():
    # ✅ FIXED: Handle both GET and OPTIONS explicitly
    if request.method == 'OPTIONS':
        # OPTIONS already handled by before_request, but return explicit response
        return jsonify({"success": True}), 200
        
    # Handle GET request
    camera_id = request.args.get('camera_id')
    file = request.args.get('file')
    
    logging.info(f"[GET-ROI-FRAME] camera_id: {camera_id}, file: {file}")
    logging.info(f"[GET-ROI-FRAME] CAMERA_ROI_DIR: {CAMERA_ROI_DIR}")
    
    if not camera_id or not file:
        return jsonify({"success": False, "error": "Thiếu camera_id hoặc file."}), 400

    # ✅ IMPROVED: Handle different file naming patterns
    if file == "roi_packing.jpg":
        file_name = f"camera_{camera_id}_roi_packing.jpg"
    elif file == "roi_MVD.jpg":
        file_name = f"camera_{camera_id}_roi_MVD.jpg"
    elif file == "roi_trigger.jpg":
        file_name = f"camera_{camera_id}_roi_trigger.jpg"
    elif file == "original.jpg":
        file_name = f"camera_{camera_id}_original.jpg"
    else:
        # Fallback: use the file parameter as-is with camera prefix
        file_name = f"camera_{camera_id}_{file}"
    
    file_path = os.path.join(CAMERA_ROI_DIR, file_name)
    logging.info(f"[GET-ROI-FRAME] Attempting to fetch file: {file_path}")
    logging.info(f"[GET-ROI-FRAME] File exists: {os.path.exists(file_path)}")

    if not os.path.exists(file_path):
        logging.error(f"[GET-ROI-FRAME] File không tồn tại: {file_path}")
        # ✅ List available files for debugging
        try:
            if os.path.exists(CAMERA_ROI_DIR):
                available_files = os.listdir(CAMERA_ROI_DIR)
                camera_files = [f for f in available_files if f.startswith(f"camera_{camera_id}")]
                logging.info(f"[GET-ROI-FRAME] Available files for camera {camera_id}: {camera_files}")
                logging.info(f"[GET-ROI-FRAME] All files in CAMERA_ROI_DIR: {available_files}")
            else:
                logging.error(f"[GET-ROI-FRAME] CAMERA_ROI_DIR does not exist: {CAMERA_ROI_DIR}")
        except Exception as e:
            logging.error(f"[GET-ROI-FRAME] Error listing directory: {e}")
        
        return jsonify({
            "success": False, 
            "error": "Không tìm thấy ảnh.", 
            "file_path": file_path,
            "camera_roi_dir": CAMERA_ROI_DIR,
            "dir_exists": os.path.exists(CAMERA_ROI_DIR)
        }), 404

    try:
        # ✅ Serve file with proper cache control headers
        response = send_file(file_path, mimetype='image/jpeg', as_attachment=False)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logging.error(f"[GET-ROI-FRAME] Error serving file: {e}")
        return jsonify({"success": False, "error": f"Lỗi khi serve file: {str(e)}"}), 500

@roi_bp.route('/get-final-roi-frame', methods=['GET', 'OPTIONS'])
def get_final_roi_frame():
    # ✅ FIXED: Handle both GET and OPTIONS explicitly
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
        
    # Handle GET request
    camera_id = request.args.get('camera_id')
    logging.info(f"[GET-FINAL-ROI] camera_id: {camera_id}")
    logging.info(f"[GET-FINAL-ROI] CAMERA_ROI_DIR: {CAMERA_ROI_DIR}")
    
    if not camera_id:
        return jsonify({"success": False, "error": "Thiếu camera_id."}), 400
    
    final_pattern = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_final_*.jpg")
    final_files = glob.glob(final_pattern)
    logging.info(f"[GET-FINAL-ROI] Pattern: {final_pattern}")
    logging.info(f"[GET-FINAL-ROI] Files found for camera_id={camera_id}: {final_files}")

    if not final_files:
        logging.error(f"[GET-FINAL-ROI] Không tìm thấy file tổng hợp nào trong {CAMERA_ROI_DIR} với pattern {final_pattern}")
        # ✅ List all files for debugging
        try:
            if os.path.exists(CAMERA_ROI_DIR):
                all_files = os.listdir(CAMERA_ROI_DIR)
                camera_files = [f for f in all_files if f.startswith(f"camera_{camera_id}")]
                logging.info(f"[GET-FINAL-ROI] All files for camera {camera_id}: {camera_files}")
                logging.info(f"[GET-FINAL-ROI] All files in directory: {all_files}")
            else:
                logging.error(f"[GET-FINAL-ROI] CAMERA_ROI_DIR does not exist: {CAMERA_ROI_DIR}")
        except Exception as e:
            logging.error(f"[GET-FINAL-ROI] Error listing directory: {e}")
        
        return jsonify({
            "success": False, 
            "error": "Không tìm thấy ảnh tổng hợp.",
            "pattern": final_pattern,
            "camera_roi_dir": CAMERA_ROI_DIR,
            "dir_exists": os.path.exists(CAMERA_ROI_DIR)
        }), 404

    latest_file = max(final_files, key=os.path.getmtime)
    logging.info(f"[GET-FINAL-ROI] Latest file selected: {latest_file}")

    if not os.path.exists(latest_file):
        logging.error(f"[GET-FINAL-ROI] File mới nhất {latest_file} không tồn tại")
        return jsonify({"success": False, "error": "Không tìm thấy ảnh tổng hợp."}), 404

    try:
        # ✅ Serve file with proper cache control headers
        response = send_file(latest_file, mimetype='image/jpeg', as_attachment=False)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logging.error(f"[GET-FINAL-ROI] Error serving file: {e}")
        return jsonify({"success": False, "error": f"Lỗi khi serve file: {str(e)}"}), 500

# ✅ DEBUG ENDPOINT: To check paths and files
@roi_bp.route('/debug-roi-paths', methods=['GET', 'OPTIONS'])
def debug_roi_paths():
    """Debug endpoint to check file paths and availability"""
    # ✅ FIXED: Handle both GET and OPTIONS explicitly
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
        
    # Handle GET request
    try:
        camera_id = request.args.get('camera_id', 'Hik_recorde')
        
        debug_info = {
            "current_file": __file__,
            "base_dir": BASE_DIR,
            "camera_roi_dir": CAMERA_ROI_DIR,
            "db_path": DB_PATH,
            "camera_roi_dir_exists": os.path.exists(CAMERA_ROI_DIR),
            "expected_file_path": f"/Users/annhu/vtrack_app/V_Track/resources/output_clips/CameraROI/camera_{camera_id}_roi_packing.jpg",
            "test_file_exists": os.path.exists(f"/Users/annhu/vtrack_app/V_Track/resources/output_clips/CameraROI/camera_{camera_id}_roi_packing.jpg")
        }
        
        # List files in directory
        if os.path.exists(CAMERA_ROI_DIR):
            all_files = os.listdir(CAMERA_ROI_DIR)
            camera_files = [f for f in all_files if f.startswith(f"camera_{camera_id}")]
            debug_info.update({
                "all_files_count": len(all_files),
                "camera_files": camera_files,
                "all_files": all_files[:10]  # Show first 10 files
            })
        else:
            debug_info.update({
                "error": "CAMERA_ROI_DIR does not exist",
                "all_files": []
            })
        
        return jsonify({
            "success": True,
            "debug_info": debug_info
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "debug_info": {
                "current_file": __file__ if '__file__' in globals() else "Unknown"
            }
        })