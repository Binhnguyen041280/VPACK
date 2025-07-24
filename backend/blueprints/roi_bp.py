from flask import Blueprint, request, jsonify, send_file
from modules.technician.hand_detection import finalize_roi
import os
import glob
import json
import sqlite3
from datetime import datetime
import logging

roi_bp = Blueprint('roi', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database", "events.db")
CAMERA_ROI_DIR = os.path.join(BASE_DIR, "..", "..", "resources/output_clips/CameraROI")

@roi_bp.route('/finalize-roi', methods=['POST'])
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
                SET qr_trigger_area = ?, qr_mvd_area = ?, packing_area = ?,
                    min_packing_time = ?, jump_time_ratio = ?, scan_mode = ?, fixed_threshold = ?, margin = ?, additional_params = ?
                WHERE profile_name = ?
            ''', (
                json.dumps(qr_trigger_area),
                json.dumps(qr_mvd_area),
                json.dumps(packing_roi),
                10, 0.5, "full", 20, 60, json.dumps({}),
                profile_name
            ))
        else:
            cursor.execute('''
                INSERT INTO packing_profiles (
                    profile_name, qr_trigger_area, qr_mvd_area, packing_area,
                    min_packing_time, jump_time_ratio, scan_mode, fixed_threshold, margin, additional_params
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile_name,
                json.dumps(qr_trigger_area),
                json.dumps(qr_mvd_area),
                json.dumps(packing_roi),
                10, 0.5, "full", 20, 60, json.dumps({})
            ))
        conn.commit()
        conn.close()
        logging.info(f"Lưu ROI vào packing_profiles với profile_name: {profile_name}")

        result = finalize_roi(video_path, camera_id, rois)
        return jsonify(result), 200 if result["success"] else 400
    
    except Exception as e:
        logging.error(f"Exception in finalize_roi_endpoint: {str(e)}")
        return jsonify({"success": False, "error": f"Lỗi hệ thống: {str(e)}"}), 500

@roi_bp.route('/get-roi-frame', methods=['GET'])
def get_roi_frame():
    camera_id = request.args.get('camera_id')
    file = request.args.get('file')
    if not camera_id or not file:
        return jsonify({"success": False, "error": "Thiếu camera_id hoặc file."}), 400

    file_path = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_{file}")
    logging.info(f"Attempting to fetch file: {file_path}")

    if not os.path.exists(file_path):
        logging.error(f"File không tồn tại: {file_path}")
        return jsonify({"success": False, "error": "Không tìm thấy ảnh."}), 404

    return send_file(file_path, mimetype='image/jpeg')

@roi_bp.route('/get-final-roi-frame', methods=['GET'])
def get_final_roi_frame():
    camera_id = request.args.get('camera_id')
    if not camera_id:
        return jsonify({"success": False, "error": "Thiếu camera_id."}), 400
    
    final_pattern = os.path.join(CAMERA_ROI_DIR, f"camera_{camera_id}_roi_final_*.jpg")
    final_files = glob.glob(final_pattern)
    logging.info(f"Files found for camera_id={camera_id}: {final_files}")

    if not final_files:
        logging.error(f"Không tìm thấy file tổng hợp nào trong {CAMERA_ROI_DIR} với pattern {final_pattern}")
        return jsonify({"success": False, "error": "Không tìm thấy ảnh tổng hợp."}), 404

    latest_file = max(final_files, key=os.path.getmtime)
    logging.info(f"Latest file selected: {latest_file}")

    if not os.path.exists(latest_file):
        logging.error(f"File mới nhất {latest_file} không tồn tại")
        return jsonify({"success": False, "error": "Không tìm thấy ảnh tổng hợp."}), 404

    return send_file(latest_file, mimetype='image/jpeg')