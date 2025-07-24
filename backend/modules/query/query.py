from flask import Blueprint, request, jsonify
from datetime import datetime
import csv
import io
import os
import base64
import pandas as pd
import json
from io import BytesIO
from modules.db_utils import find_project_root, get_db_connection
from ..utils.file_parser import parse_uploaded_file
from modules.scheduler.db_sync import db_rwlock  # Thêm import db_rwlock

query_bp = Blueprint('query', __name__)

# Xác định thư mục gốc của dự án
BASE_DIR = find_project_root(os.path.abspath(__file__))

# Định nghĩa DB_PATH dựa trên BASE_DIR
DB_PATH = os.path.join(BASE_DIR, "database", "events.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

@query_bp.route('/get-csv-headers', methods=['POST'])
def get_csv_headers():
    data = request.get_json()
    file_content = data.get('file_content', '')
    file_path = data.get('file_path', '')
    is_excel = data.get('is_excel', False)

    if file_content:
        if not file_content.strip():
            return jsonify({"error": "File CSV is empty. Please provide a valid CSV file with content."}), 400

        try:
            df = parse_uploaded_file(file_content=file_content, is_excel=is_excel)
            rows = [df.columns.tolist()]
        except Exception as e:
            return jsonify({"error": f"Failed to read file content: {str(e)}. Ensure the content is properly formatted."}), 400
    elif file_path:
        if not os.path.exists(file_path):
            return jsonify({"error": f"File not found at path: {file_path}. Please check the file path and try again."}), 404

        try:
            with open(file_path, "rb") as f:
                file_content = base64.b64encode(f.read()).decode("utf-8")
            df = parse_uploaded_file(file_content=file_content, is_excel=is_excel)
            rows = [df.columns.tolist()]
        except Exception as e:
            return jsonify({"error": f"Failed to read file from path {file_path}: {str(e)}. Ensure the file is accessible and properly formatted."}), 400
    else:
        return jsonify({"error": "No file content or path provided. Please provide either file content or a valid file path."}), 400

    if not rows or len(rows) < 1:
        return jsonify({"error": "CSV file has no header. Please ensure the CSV file contains at least one row with headers."}), 400

    header = rows[0]
    if not header:
        return jsonify({"error": "CSV file header is empty. Please ensure the first row contains valid headers."}), 400

    return jsonify({"headers": header}), 200

@query_bp.route('/parse-csv', methods=['POST'])
def parse_csv():
    data = request.get_json()
    file_content = data.get('file_content', '')
    file_path = data.get('file_path', '')
    column_name = data.get('column_name', 'tracking_codes')
    is_excel = data.get('is_excel', False)

    try:
        if file_content:
            df = parse_uploaded_file(file_content=file_content, is_excel=is_excel)
        elif file_path:
            with open(file_path, "rb") as f:
                file_content = base64.b64encode(f.read()).decode("utf-8")
            df = parse_uploaded_file(file_content=file_content, is_excel=is_excel)
        else:
            return jsonify({"error": "No file provided"}), 400

        if column_name not in df.columns:
            return jsonify({"error": f"Cột '{column_name}' không tồn tại trong file."}), 400

        values = df[column_name].dropna().astype(str).tolist()
        codes = []
        for val in values:
            # Thử cắt chuỗi theo dấu phẩy trước
            split_vals = val.split(',')
            if len(split_vals) == 1:  # Nếu không cắt được, thử dấu chấm phẩy
                split_vals = val.split(';')
            codes.extend(v.strip() for v in split_vals if v.strip())
        codes = list(set(codes))  # Loại bỏ trùng lặp

        return jsonify({"tracking_codes": codes}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV: {str(e)}. Ensure the file and column name are valid."}), 500

@query_bp.route('/query', methods=['POST'])
def query_events():
    data = request.get_json()
    print(f"Received data: {data}")  # Log dữ liệu nhận được
    search_string = data.get('search_string', '')
    default_days = data.get('default_days', 7)  # Thêm giá trị mặc định 7 nếu không có trong request
    from_time = data.get('from_time')
    to_time = data.get('to_time')
    selected_cameras = data.get('selected_cameras', [])  # Lấy selected_cameras

    # Tách search_string theo dòng và loại bỏ số thứ tự
    tracking_codes = []
    if search_string:
        lines = search_string.splitlines()
        for line in lines:
            line = line.strip()
            if line:
                # Loại bỏ số thứ tự (e.g., "1. " hoặc "2. ")
                code = line.split('. ', 1)[-1].strip()
                if code:
                    tracking_codes.append(code)
    print(f"Parsed tracking_codes from search_string: {tracking_codes}")  # Log tracking_codes đã tách

    try:
        if from_time and to_time:
            try:
                from_timestamp = int(datetime.fromisoformat(from_time.replace('Z', '+00:00')).timestamp() * 1000)
                to_timestamp = int(datetime.fromisoformat(to_time.replace('Z', '+00:00')).timestamp() * 1000)
            except ValueError as e:
                return jsonify({"error": f"Invalid time format for from_time or to_time: {str(e)}. Use ISO format (e.g., 2023-10-01T00:00:00Z)."}), 400
        else:
            to_timestamp = int(datetime.now().timestamp() * 1000)
            from_timestamp = to_timestamp - (default_days * 24 * 60 * 60 * 1000)
        print(f"Time range: from_timestamp={from_timestamp}, to_timestamp={to_timestamp}")  # Log khoảng thời gian

        with db_rwlock.gen_rlock():  # Thêm khóa đọc
            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
                SELECT event_id, ts, te, duration, tracking_codes, video_file, packing_time_start, packing_time_end
                FROM events
                WHERE is_processed = 0
            """
            params = []
            # Chỉ thêm điều kiện thời gian nếu packing_time_start không null
            if from_timestamp and to_timestamp:
                query += " AND (packing_time_start IS NULL OR (packing_time_start >= ? AND packing_time_start <= ?))"
                params.extend([from_timestamp, to_timestamp])
            if selected_cameras:
                query += " AND camera_name IN ({})".format(','.join('?' * len(selected_cameras)))
                params.extend(selected_cameras)

            print(f"Executing query: {query} with params: {params}")  # Log truy vấn
            cursor.execute(query, params)
            events = cursor.fetchall()
            print(f"Fetched events: {events}")  # Log kết quả truy vấn

            filtered_events = []
            for event in events:
                event_dict = {
                    'event_id': event[0],
                    'ts': event[1],
                    'te': event[2],
                    'duration': event[3],
                    'tracking_codes': event[4],
                    'video_file': event[5],
                    'packing_time_start': event[6],
                    'packing_time_end': event[7]
                }
                print(f"Raw tracking_codes for event {event[0]}: {event[4]}")  # Log giá trị thô của tracking_codes
                try:
                    tracking_codes_list = json.loads(event[4]) if event[4] else []
                    if not isinstance(tracking_codes_list, list):
                        raise ValueError("tracking_codes is not a list")
                except Exception:
                    print(f"[WARN] tracking_codes fallback for event {event[0]}")
                    tracking_codes_list = []
                    if event[4]:
                        raw = event[4].strip("[]").replace("'", "").replace('"', "")
                        tracking_codes_list = [code.strip() for code in raw.split(',')]
                print(f"Parsed tracking_codes for event {event[0]}: {tracking_codes_list}")  # Log tracking_codes đã parse
                if not tracking_codes:
                    filtered_events.append(event_dict)
                else:
                    for code in tracking_codes:
                        if code in tracking_codes_list:
                            filtered_events.append(event_dict)
                            break
            print(f"Filtered events: {filtered_events}")  # Log kết quả sau khi lọc

            conn.close()
        return jsonify({'events': filtered_events}), 200
    except Exception as e:
        print(f"Error in query_events: {str(e)}")  # Log lỗi chi tiết
        return jsonify({"error": f"Failed to query events: {str(e)}. Ensure the database is accessible and the events table exists."}), 500