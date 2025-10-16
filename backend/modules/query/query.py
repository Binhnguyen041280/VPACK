from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
import csv
import io
import os
import base64
import pandas as pd
import json
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple
from modules.db_utils import find_project_root
from modules.db_utils.safe_connection import safe_db_connection
from ..utils.file_parser import parse_uploaded_file
from modules.scheduler.db_sync import db_rwlock  # Thêm import db_rwlock
from zoneinfo import ZoneInfo
from modules.config.logging_config import get_logger
# Removed timezone_validation - using simple validation inline
# Removed enhanced_timezone_query import - consolidating into single file
from modules.utils.simple_timezone import simple_validate_timezone, get_available_timezones, get_system_timezone_from_db
# License guard for Trace page protection
from modules.license.license_guard import require_valid_license

query_bp = Blueprint('query', __name__)
logger = get_logger(__name__)

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
            return jsonify({"error": f"Column '{column_name}' does not exist in the file."}), 400

        values = df[column_name].dropna().astype(str).tolist()
        codes = []
        for val in values:
            # Try splitting by comma first
            split_vals = val.split(',')
            if len(split_vals) == 1:  # If no comma split, try semicolon
                split_vals = val.split(';')
            codes.extend(v.strip() for v in split_vals if v.strip())
        codes = list(set(codes))  # Remove duplicates

        return jsonify({"tracking_codes": codes}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV: {str(e)}. Ensure the file and column name are valid."}), 500

@query_bp.route('/query', methods=['POST'])
@require_valid_license
def query_events():
    """Query events with timezone-aware filtering and conversion.
    
    Supports multiple input formats for from_time/to_time:
    - ISO format with timezone: '2024-01-15T10:30:00+07:00'
    - ISO format UTC: '2024-01-15T03:30:00Z' 
    - Local time (assumes user timezone): '2024-01-15T10:30:00'
    - Unix timestamp (milliseconds): 1705287000000
    
    Returns events with both UTC and local time representations.
    """
    data = request.get_json()
    logger.info(f"Received query request: {data}")
    
    search_string = data.get('search_string', '')
    default_days = data.get('default_days', 7)
    from_time = data.get('from_time')
    to_time = data.get('to_time')
    selected_cameras = data.get('selected_cameras', [])
    user_timezone_name = data.get('user_timezone')  # Optional user timezone override

    # Note: tracking_codes will be parsed by validation module

    try:
        # Simple parameter validation (replacing complex timezone_validation)
        from_time = data.get('from_time')
        to_time = data.get('to_time')
        timezone_str = data.get('timezone', get_system_timezone_from_db())
        
        # Validate timezone
        tz_result = simple_validate_timezone(timezone_str)
        if not tz_result['valid']:
            return jsonify({"error": f"Invalid timezone: {timezone_str}"}), 400
            
        # Parse timestamps and convert to Unix milliseconds for database query
        time_range_result = parse_time_range(from_time, to_time, 7, tz_result['timezone'])
        if time_range_result['error']:
            return jsonify({"error": time_range_result['error']}), 400

        from_timestamp = time_range_result['from_timestamp']
        to_timestamp = time_range_result['to_timestamp']
        # Extract other parameters
        user_tz = ZoneInfo(tz_result['timezone'])
        tracking_codes = data.get('tracking_codes', [])
        selected_cameras = data.get('cameras', [])
        
        logger.info(f"Validated query: {from_timestamp} to {to_timestamp}, user_tz: {tz_result['timezone']}, cameras: {len(selected_cameras)}, codes: {len(tracking_codes)}")

        with db_rwlock.gen_rlock():  # Add read lock
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                SELECT event_id, ts, te, duration, tracking_codes, video_file, packing_time_start, packing_time_end,
                       timezone_info, camera_name, created_at_utc, updated_at_utc
                FROM events
                WHERE 1=1
            """
                params = []
                # Only add time condition if packing_time_start is not null
                if from_timestamp and to_timestamp:
                    query += " AND (packing_time_start IS NULL OR (packing_time_start >= ? AND packing_time_start <= ?))"
                    params.extend([from_timestamp, to_timestamp])
                if selected_cameras:
                    query += " AND camera_name IN ({})".format(','.join('?' * len(selected_cameras)))
                    params.extend(selected_cameras)

                logger.info(f"Executing query with params: {params}")
                cursor.execute(query, params)
                events = cursor.fetchall()
                logger.info(f"Fetched {len(events)} events")

                # Process and format events with timezone conversion
                filtered_events = []
                for event in events:
                    try:
                        # Convert event to timezone-aware format
                        event_dict = convert_event_to_timezone_aware(event, user_tz)
                        
                        # Parse tracking codes
                        tracking_codes_list = parse_tracking_codes(event[4], event[0])
                        event_dict['tracking_codes_parsed'] = tracking_codes_list
                        
                        # Apply tracking code filter
                        if not tracking_codes or any(code in tracking_codes_list for code in tracking_codes):
                            filtered_events.append(event_dict)
                            
                    except Exception as e:
                        logger.warning(f"Error processing event {event[0]}: {e}")
                        continue
                        
                logger.info(f"Filtered to {len(filtered_events)} events matching criteria")
        # Add metadata to response
        response_data = {
            'events': filtered_events,
            'metadata': {
                'total_events': len(filtered_events),
                'time_range': {
                    'from_utc': from_timestamp,
                    'to_utc': to_timestamp,
                    'user_timezone': str(user_tz)
                },
                'search_criteria': {
                    'tracking_codes': tracking_codes,
                    'cameras': selected_cameras
                }
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in query_events: {str(e)}")
        return jsonify({"error": f"Failed to query events: {str(e)}. Ensure the database is accessible and the events table exists."}), 500


def parse_time_range(from_time: Optional[str], to_time: Optional[str], 
                    default_days: int, user_timezone_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse and convert time range parameters to UTC timestamps.
    
    Args:
        from_time: Start time in various formats
        to_time: End time in various formats  
        default_days: Default number of days if no time range specified
        user_timezone_name: Optional user timezone override
        
    Returns:
        Dict with parsed timestamps and timezone info
    """
    try:
        # Get user timezone
        if user_timezone_name:
            try:
                validation_result = simple_validate_timezone(user_timezone_name)
                if validation_result['valid']:
                    try:
                        user_tz = ZoneInfo(validation_result['timezone'])
                    except:
                        user_tz = ZoneInfo(get_system_timezone_from_db())
                else:
                    user_tz = ZoneInfo(get_system_timezone_from_db())
            except:
                user_tz = ZoneInfo(get_system_timezone_from_db())
        else:
            user_tz = ZoneInfo(get_system_timezone_from_db())
        
        if from_time and to_time:
            # Parse custom time range
            from_dt = parse_datetime_with_timezone(from_time, user_tz)
            to_dt = parse_datetime_with_timezone(to_time, user_tz)
            
            if not from_dt or not to_dt:
                return {
                    'error': 'Invalid time format. Use ISO format (e.g., 2024-01-15T10:30:00+07:00, 2024-01-15T03:30:00Z, or 2024-01-15T10:30:00)',
                    'from_timestamp': None,
                    'to_timestamp': None,
                    'user_timezone': None
                }
            
            # Convert to UTC timestamps (milliseconds)
            from_timestamp = int(from_dt.astimezone(timezone.utc).timestamp() * 1000)
            to_timestamp = int(to_dt.astimezone(timezone.utc).timestamp() * 1000)
            
        else:
            # Use default time range
            to_dt = datetime.now(timezone.utc)
            from_dt = to_dt - timedelta(days=default_days)
            
            from_timestamp = int(from_dt.timestamp() * 1000)
            to_timestamp = int(to_dt.timestamp() * 1000)
        
        return {
            'error': None,
            'from_timestamp': from_timestamp,
            'to_timestamp': to_timestamp,
            'user_timezone': user_tz
        }
        
    except Exception as e:
        logger.error(f"Error parsing time range: {e}")
        return {
            'error': f"Error parsing time range: {str(e)}",
            'from_timestamp': None,
            'to_timestamp': None,
            'user_timezone': None
        }


def parse_datetime_with_timezone(time_str: str, user_tz) -> Optional[datetime]:
    """
    Parse datetime string with timezone awareness.
    
    Supports multiple formats:
    - ISO with timezone: '2024-01-15T10:30:00+07:00'
    - ISO UTC: '2024-01-15T03:30:00Z'
    - Local time: '2024-01-15T10:30:00' (assumes user timezone)
    - Unix timestamp: '1705287000000' (milliseconds)
    """
    try:
        # Try Unix timestamp (milliseconds)
        if time_str.isdigit():
            timestamp_ms = int(time_str)
            return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        
        # Try ISO format with timezone
        try:
            # Handle Z suffix for UTC
            if time_str.endswith('Z'):
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
            # Try direct ISO parsing
            return datetime.fromisoformat(time_str)
            
        except ValueError:
            pass
        
        # Try parsing as naive datetime and apply user timezone
        try:
            naive_dt = datetime.fromisoformat(time_str)
            return naive_dt.replace(tzinfo=user_tz)
        except ValueError:
            pass
        
        # Try common datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                naive_dt = datetime.strptime(time_str, fmt)
                if hasattr(user_tz, 'localize'):
                    return user_tz.localize(naive_dt)
                else:
                    return naive_dt.replace(tzinfo=user_tz)
            except ValueError:
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing datetime '{time_str}': {e}")
        return None


def convert_event_to_timezone_aware(event: Tuple, user_tz) -> Dict[str, Any]:
    """
    Convert database event row to timezone-aware format.
    
    Args:
        event: Database row tuple
        user_tz: User timezone for conversion
        
    Returns:
        Dictionary with timezone-aware event data
    """
    try:
        # Parse timezone info if available
        timezone_info = {}
        if len(event) > 8 and event[8]:  # timezone_info column
            try:
                timezone_info = json.loads(event[8]) if isinstance(event[8], str) else event[8]
            except (json.JSONDecodeError, TypeError):
                timezone_info = {}
        
        # Convert timestamps to both UTC and user timezone
        packing_time_start_utc = event[6] if event[6] else None
        packing_time_end_utc = event[7] if event[7] else None
        
        # Convert to user timezone for display
        packing_time_start_local = None
        packing_time_end_local = None
        
        if packing_time_start_utc:
            utc_dt = datetime.fromtimestamp(packing_time_start_utc / 1000, tz=timezone.utc)
            packing_time_start_local = utc_dt.astimezone(user_tz).isoformat()
            
        if packing_time_end_utc:
            utc_dt = datetime.fromtimestamp(packing_time_end_utc / 1000, tz=timezone.utc)
            packing_time_end_local = utc_dt.astimezone(user_tz).isoformat()
        
        return {
            'event_id': event[0],
            'ts': event[1],
            'te': event[2], 
            'duration': event[3],
            'tracking_codes': event[4],
            'video_file': event[5],
            'packing_time_start': packing_time_start_utc,  # UTC milliseconds (original format)
            'packing_time_end': packing_time_end_utc,      # UTC milliseconds (original format)
            'packing_time_start_local': packing_time_start_local,  # User timezone ISO format
            'packing_time_end_local': packing_time_end_local,      # User timezone ISO format
            'timezone_info': timezone_info,
            'camera_name': event[9] if len(event) > 9 else None,
            'created_at_utc': event[10] if len(event) > 10 else None,
            'updated_at_utc': event[11] if len(event) > 11 else None,
        }
        
    except Exception as e:
        logger.error(f"Error converting event to timezone-aware format: {e}")
        # Fallback to original format
        return {
            'event_id': event[0],
            'ts': event[1],
            'te': event[2],
            'duration': event[3],
            'tracking_codes': event[4],
            'video_file': event[5],
            'packing_time_start': event[6],
            'packing_time_end': event[7],
            'timezone_info': event[8] if len(event) > 8 else None,
            'error': f"Timezone conversion failed: {str(e)}"
        }


def parse_tracking_codes(tracking_codes_raw: Optional[str], event_id: int = None) -> List[str]:
    """
    Parse tracking codes from database format to list.
    
    Args:
        tracking_codes_raw: Raw tracking codes from database
        event_id: Event ID for logging purposes
        
    Returns:
        List of tracking codes
    """
    try:
        if not tracking_codes_raw:
            return []
        
        # Try JSON parsing first
        try:
            tracking_codes_list = json.loads(tracking_codes_raw)
            if isinstance(tracking_codes_list, list):
                return [str(code).strip() for code in tracking_codes_list if code]
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Fallback to string parsing
        if isinstance(tracking_codes_raw, str):
            # Remove brackets and quotes
            raw = tracking_codes_raw.strip("[]").replace("'", "").replace('"', "")
            if raw:
                return [code.strip() for code in raw.split(',') if code.strip()]
        
        return []
        
    except Exception as e:
        logger.warning(f"Error parsing tracking codes for event {event_id}: {e}")
        return []


@query_bp.route('/events', methods=['GET'])
def get_events():
    """
    Get events with timezone support via query parameters.
    
    Query parameters:
    - from_time: Start time (various formats supported)
    - to_time: End time (various formats supported)
    - timezone: User timezone name (optional)
    - cameras: Comma-separated camera names
    - tracking_codes: Comma-separated tracking codes
    - limit: Maximum number of events to return
    - offset: Number of events to skip
    """
    try:
        # Parse query parameters
        from_time = request.args.get('from_time')
        to_time = request.args.get('to_time')
        user_timezone_name = request.args.get('timezone')
        cameras_param = request.args.get('cameras', '')
        tracking_codes_param = request.args.get('tracking_codes', '')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Parse comma-separated parameters
        selected_cameras = [c.strip() for c in cameras_param.split(',') if c.strip()]
        tracking_codes = [c.strip() for c in tracking_codes_param.split(',') if c.strip()]
        
        # Use the same logic as POST endpoint
        data = {
            'from_time': from_time,
            'to_time': to_time,
            'user_timezone': user_timezone_name,
            'selected_cameras': selected_cameras,
            'search_string': '\\n'.join(tracking_codes),
            'default_days': 7
        }
        
        # Reuse query_events logic (without jsonify)
        # This is a simplified version - in production you might want to refactor common logic
        time_range_result = parse_time_range(from_time, to_time, 7, user_timezone_name)
        if time_range_result['error']:
            return jsonify({"error": time_range_result['error']}), 400
            
        from_timestamp = time_range_result['from_timestamp']
        to_timestamp = time_range_result['to_timestamp']
        user_tz = time_range_result['user_timezone']
        
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with limit and offset
                query = '''
                SELECT event_id, ts, te, duration, tracking_codes, video_file, packing_time_start, packing_time_end,
                       timezone_info, camera_name, created_at_utc, updated_at_utc
                FROM events
                WHERE 1=1
                '''
                params = []
                
                if from_timestamp and to_timestamp:
                    query += " AND (packing_time_start IS NULL OR (packing_time_start >= ? AND packing_time_start <= ?))"
                    params.extend([from_timestamp, to_timestamp])
                    
                if selected_cameras:
                    query += " AND camera_name IN ({})".format(','.join('?' * len(selected_cameras)))
                    params.extend(selected_cameras)
                
                query += " ORDER BY packing_time_start DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                events = cursor.fetchall()
                
                # Process events
                filtered_events = []
                for event in events:
                    try:
                        event_dict = convert_event_to_timezone_aware(event, user_tz)
                        tracking_codes_list = parse_tracking_codes(event[4], event[0])
                        event_dict['tracking_codes_parsed'] = tracking_codes_list
                        
                        # Apply tracking code filter
                        if not tracking_codes or any(code in tracking_codes_list for code in tracking_codes):
                            filtered_events.append(event_dict)
                            
                    except Exception as e:
                        logger.warning(f"Error processing event {event[0]}: {e}")
                        continue
        
        response_data = {
            'events': filtered_events,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': len(filtered_events)
            },
            'metadata': {
                'time_range': {
                    'from_utc': from_timestamp,
                    'to_utc': to_timestamp,
                    'user_timezone': str(user_tz)
                },
                'search_criteria': {
                    'tracking_codes': tracking_codes,
                    'cameras': selected_cameras
                }
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in get_events: {str(e)}")
        return jsonify({"error": f"Failed to get events: {str(e)}"}), 500

@query_bp.route('/query-enhanced', methods=['POST'])
def query_events_enhanced():
    """Enhanced timezone-aware event query endpoint.
    
    This endpoint provides advanced timezone-aware filtering with:
    - Automatic local time to UTC conversion
    - Performance-optimized queries
    - Multiple time input format support
    - Comprehensive timezone-aware result formatting
    
    Request format:
    {
        "from_time": "2024-01-15 10:00:00",  // Local time or various formats
        "to_time": "2024-01-15 18:00:00",    // Local time or various formats
        "cameras": ["Camera01", "Camera02"],  // Optional camera filter
        "tracking_codes": ["TC001", "TC002"], // Optional tracking code filter
        "user_timezone": "<system_timezone>",  // Optional timezone override (defaults to system timezone)
        "search_string": "search text",       // Optional text search
        "include_processed": false            // Include processed events
    }
    
    Response includes timezone-aware timestamps and performance metrics.
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        logger.info(f"Enhanced timezone query request: {data}")
        
        # Extract parameters
        from_time = data.get('from_time')
        to_time = data.get('to_time')
        cameras = data.get('cameras', [])
        tracking_codes = data.get('tracking_codes', [])
        user_timezone = data.get('user_timezone')
        search_string = data.get('search_string', '')
        include_processed = data.get('include_processed', False)
        
        # Use system timezone if not specified
        if not user_timezone:
            user_timezone = get_system_timezone_from_db()
        
        # Use the existing query logic in this file instead of enhanced module
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                SELECT event_id, ts, te, duration, tracking_codes, video_file, packing_time_start, packing_time_end,
                       timezone_info, camera_name, created_at_utc, updated_at_utc
                FROM events
                WHERE 1=1
            """
                params = []

                # Add time filtering
                if from_timestamp and to_timestamp:
                    query += " AND (packing_time_start IS NULL OR (packing_time_start >= ? AND packing_time_start <= ?))"
                    params.extend([from_timestamp, to_timestamp])

                # Add camera filtering
                if cameras:
                    query += " AND camera_name IN ({})".format(','.join('?' * len(cameras)))
                    params.extend(cameras)

                logger.info(f"Executing consolidated query with params: {params}")
                cursor.execute(query, params)
                events = cursor.fetchall()

                # Process and format events
                formatted_events = []
                for event in events:
                    event_dict = {
                        'event_id': event[0],
                        'ts': event[1],
                        'te': event[2],
                        'duration': event[3],
                        'tracking_codes_raw': event[4],
                        'video_file': event[5],
                        'packing_time_start': event[6],
                        'packing_time_end': event[7],
                        'timezone_info': event[8],
                        'camera_name': event[9],
                        'created_at_utc': event[10],
                        'updated_at_utc': event[11]
                    }

                    # Parse tracking codes
                    tracking_codes_parsed = parse_tracking_codes(event[4], event[0])
                    event_dict['tracking_codes_parsed'] = tracking_codes_parsed

                    formatted_events.append(event_dict)

                result = {
                    'events': formatted_events,
                    'total_count': len(formatted_events),
                    'query_time_ms': 0,  # Simplified - no performance tracking
                    'timezone_info': user_timezone
                }
        
        # Format response
        response_data = {
            'success': True,
            'events': result.events,
            'pagination': {
                'total_count': result.total_count,
                'returned_count': len(result.events)
            },
            'timezone_info': result.timezone_info,
            'time_range': {
                'from_local': result.time_range.from_local.isoformat(),
                'to_local': result.time_range.to_local.isoformat(),
                'from_utc_ms': result.time_range.from_timestamp_utc,
                'to_utc_ms': result.time_range.to_timestamp_utc,
                'duration_hours': result.time_range.query_duration_hours,
                'user_timezone': result.time_range.user_timezone
            },
            'performance': {
                'query_time_ms': result.query_time_ms,
                'metrics': result.performance_metrics
            },
            'query_info': {
                'endpoint': 'query-enhanced',
                'timezone_aware': True,
                'optimization_enabled': True
            }
        }
        
        total_time_ms = (time.time() - start_time) * 1000
        response_data['performance']['total_time_ms'] = total_time_ms
        
        logger.info(f"Enhanced timezone query completed: {result.total_count} events in {total_time_ms:.2f}ms")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        error_time_ms = (time.time() - start_time) * 1000
        logger.error(f"Enhanced timezone query failed after {error_time_ms:.2f}ms: {e}")
        
        return jsonify({
            'success': False,
            'error': f"Enhanced query failed: {str(e)}",
            'query_info': {
                'endpoint': 'query-enhanced',
                'timezone_aware': True,
                'error_time_ms': error_time_ms
            }
        }), 500

@query_bp.route('/timezone-info', methods=['GET'])
def get_timezone_info():
    """Get current timezone configuration for query interface."""
    try:
        # Get timezone info using simple implementation
        current_tz_name = get_system_timezone_from_db()
        current_tz = ZoneInfo(current_tz_name)
        now = datetime.now(current_tz)
        utc_offset_hours = now.utcoffset().total_seconds() / 3600
        
        # Get available timezones for UI
        common_timezones = get_available_timezones()
        
        response_data = {
            'current_timezone': {
                'iana_name': current_tz_name,
                'display_name': current_tz_name,
                'utc_offset_hours': utc_offset_hours,
                'is_validated': True,
                'source': 'hardcoded_default'
            },
            'zoneinfo': {
                'user_timezone': current_tz_name,
                'using_standard_library': True
            },
            'available_timezones': common_timezones[:50],  # Limit for UI performance
            'query_capabilities': {
                'timezone_aware_filtering': True,
                'automatic_utc_conversion': True,
                'multiple_time_formats': True,
                'performance_optimized': True
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting timezone info: {e}")
        return jsonify({
            'error': f"Failed to get timezone info: {str(e)}"
        }), 500

@query_bp.route('/performance-metrics', methods=['GET'])
def get_query_performance_metrics():
    """Get query performance metrics for monitoring."""
    try:
        # Simplified metrics without enhanced module
        response_data = {
            'performance_metrics': {
                'total_queries': 0,
                'average_query_time_ms': 0,
                'cache_hit_rate': 0  # No cache anymore
            },
            'optimization_info': {
                'query_optimizer_enabled': False,
                'timezone_aware_indexing': True,
                'caching_enabled': False  # Cache removed
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({
            'error': f"Failed to get performance metrics: {str(e)}"
        }), 500

@query_bp.route('/get-cameras', methods=['GET'])
def get_cameras():
    """Get active cameras from active_cameras view - single source of truth.

    Note: No license required - camera list is needed for UI rendering
    """
    try:
        with db_rwlock.gen_rlock():
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT camera_name FROM active_cameras ORDER BY camera_name")
                cameras = [row[0] for row in cursor.fetchall()]

        return jsonify({
            "cameras": [{"name": camera} for camera in cameras],
            "count": len(cameras),
            "source": "active_cameras_view"
        }), 200

    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        return jsonify({
            "error": f"Failed to get cameras: {str(e)}"
        }), 500

import time
import threading
import uuid

# Store processing tasks
processing_tasks = {}

# File-level download locks to prevent duplicate downloads
download_locks = {}
download_locks_mutex = threading.Lock()

def get_or_create_download_lock(file_path: str) -> threading.Lock:
    """
    Get or create a lock for a specific file path.
    Ensures only one thread downloads the same file at a time.

    Args:
        file_path: Full path to the video file

    Returns:
        Threading lock for this file
    """
    with download_locks_mutex:
        if file_path not in download_locks:
            download_locks[file_path] = threading.Lock()
            logger.debug(f"🔐 Created download lock for: {os.path.basename(file_path)}")
        return download_locks[file_path]

@query_bp.route('/process-event', methods=['POST'])
@require_valid_license
def process_event():
    """
    Process event video for playback
    - Cloud source: Pre-cut available (instant)
    - Local source: On-demand cutting (if needed)
    """
    try:
        data = request.get_json()
        event_id = data.get('event_id')
        tracking_code = data.get('tracking_code')

        if not event_id or not tracking_code:
            return jsonify({"error": "Missing event_id or tracking_code"}), 400

        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Get event info
            cursor.execute("""
                SELECT event_id, video_file, output_video_path, is_processed,
                       ts, te, duration, camera_name, tracking_codes
                FROM events
                WHERE event_id = ?
            """, (event_id,))

            event = cursor.fetchone()

            if not event:
                return jsonify({"error": f"Event {event_id} not found"}), 404

            event_id, video_file, output_video_path, is_processed, ts, te, duration, camera_name, tracking_codes_str = event

            # Check if output file already exists (cached from previous trace)
            if output_video_path and os.path.exists(output_video_path):
                logger.info(f"✅ Event {event_id} already cut - using cached file: {os.path.basename(output_video_path)}")
                return jsonify({
                    "status": "completed",
                    "output_path": output_video_path,
                    "message": "Video ready (cached)",
                    "instant": True
                }), 200

            # Need to cut video on-demand
            logger.info(f"🎬 Starting on-demand cutting for event {event_id}")

            # Generate unique task ID
            task_id = str(uuid.uuid4())

            # Initialize task
            processing_tasks[task_id] = {
                "status": "starting",
                "progress": 0,
                "event_id": event_id,
                "tracking_code": tracking_code,
                "output_path": None,
                "error": None
            }

            # Start background processing
            def process_video():
                try:
                    import subprocess
                    import ast

                    # Update status
                    processing_tasks[task_id]["status"] = "checking"
                    processing_tasks[task_id]["progress"] = 10

                    # Check if video file exists
                    if not os.path.exists(video_file):
                        # Get file-specific lock to prevent duplicate downloads
                        file_lock = get_or_create_download_lock(video_file)

                        # Acquire lock for this file
                        with file_lock:
                            # Double-check if file exists after acquiring lock
                            # (another thread may have already downloaded it)
                            if os.path.exists(video_file):
                                logger.info(f"✅ File already downloaded by another thread: {os.path.basename(video_file)}")
                            else:
                                # File still missing - proceed with download
                                logger.warning(f"⚠️ Video file missing: {video_file}")
                                logger.info(f"🔒 Acquired download lock for: {os.path.basename(video_file)}")

                                # Lookup file in downloaded_files table to get drive_file_id
                                with safe_db_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        SELECT drive_file_id, source_id, camera_name
                                        FROM downloaded_files
                                        WHERE local_file_path = ?
                                    """, (video_file,))
                                    file_record = cursor.fetchone()

                                if file_record and file_record[0]:  # Has drive_file_id
                                    drive_file_id, source_id, cam_name = file_record
                                    logger.info(f"🔄 Re-downloading cloud file (force): {os.path.basename(video_file)}")

                                    processing_tasks[task_id]["status"] = "downloading"
                                    processing_tasks[task_id]["progress"] = 5

                                    try:
                                        # Import PyDriveCore class to download
                                        from modules.sources.pydrive_core import PyDriveCore

                                        # Create core instance and get drive client
                                        core = PyDriveCore()
                                        drive = core.get_drive_client(source_id)

                                        if not drive:
                                            raise Exception("Failed to get Drive client - check authentication")

                                        # Prepare file info for download
                                        file_info = {'id': drive_file_id, 'title': os.path.basename(video_file)}

                                        # Ensure parent directory exists
                                        os.makedirs(os.path.dirname(video_file), exist_ok=True)

                                        # Force download
                                        success = core.download_single_file(drive, file_info, video_file)

                                        if success and os.path.exists(video_file):
                                            logger.info(f"✅ File re-downloaded successfully: {os.path.basename(video_file)}")
                                        else:
                                            raise Exception("Download failed or file not created")

                                    except Exception as download_error:
                                        logger.error(f"❌ Re-download failed: {download_error}")
                                        raise Exception(f"Failed to re-download cloud file: {download_error}")
                                else:
                                    raise Exception(f"Video file not found and no cloud file record exists: {video_file}")

                    # Get output directory from config
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT output_path FROM processing_config WHERE id = 1")
                        result = cursor.fetchone()
                        output_dir = result[0] if result else "/Users/annhu/Movies/VTrack/Output"

                    # Create date-organized output directory
                    today = datetime.now().strftime("%Y-%m-%d")
                    date_output_dir = os.path.join(output_dir, today)
                    os.makedirs(date_output_dir, exist_ok=True)

                    # Parse tracking codes
                    tracking_codes = ast.literal_eval(tracking_codes_str) if tracking_codes_str else []
                    tracking_code = tracking_codes[0] if tracking_codes else f"event{event_id}"

                    # Generate readable filename with timestamp
                    timestamp = datetime.now().strftime("%H%M%S")
                    output_filename = f"{tracking_code}_{camera_name}_{timestamp}.mp4"
                    output_path = os.path.join(date_output_dir, output_filename)

                    # Get video FPS
                    processing_tasks[task_id]["status"] = "analyzing"
                    processing_tasks[task_id]["progress"] = 20

                    fps_cmd = [
                        'ffprobe', '-v', 'error',
                        '-select_streams', 'v:0',
                        '-show_entries', 'stream=r_frame_rate',
                        '-of', 'default=noprint_wrappers=1:nokey=1',
                        video_file
                    ]
                    fps_result = subprocess.run(fps_cmd, capture_output=True, text=True, timeout=10)
                    fps_str = fps_result.stdout.strip()

                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        fps = float(num) / float(den)
                    else:
                        fps = float(fps_str) if fps_str else 30.0

                    logger.info(f"Detected FPS: {fps}")

                    # ts/te are already in seconds (not frame indices)
                    start_time = ts
                    cut_duration = duration if duration else (te - ts) if te else 10

                    # Add buffer (2 seconds)
                    buffer = 2
                    start_time = max(0, start_time - buffer)
                    cut_duration = cut_duration + (2 * buffer)

                    # Cut video with ffmpeg
                    processing_tasks[task_id]["status"] = "cutting"
                    processing_tasks[task_id]["progress"] = 40

                    logger.info(f"Cutting event {event_id}: start={start_time:.2f}s, duration={cut_duration:.2f}s")

                    cmd = [
                        'ffmpeg',
                        '-i', video_file,
                        '-ss', str(start_time),
                        '-t', str(cut_duration),
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-y',  # Overwrite
                        output_path
                    ]

                    # Run ffmpeg with progress tracking
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )

                    # Monitor progress
                    for line in process.stderr:
                        # FFmpeg outputs progress to stderr
                        if 'time=' in line:
                            # Update progress (40-90%)
                            processing_tasks[task_id]["progress"] = min(40 + int(time.time() % 50), 90)

                    process.wait(timeout=120)

                    if process.returncode != 0:
                        raise Exception(f"FFmpeg failed with code {process.returncode}")

                    # Verify output file exists
                    if not os.path.exists(output_path):
                        raise Exception("Output file not created")

                    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                    logger.info(f"✅ Video cut successfully: {output_filename} ({file_size:.1f}MB)")

                    # Update database
                    processing_tasks[task_id]["status"] = "finalizing"
                    processing_tasks[task_id]["progress"] = 95

                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE events
                            SET output_video_path = ?,
                                is_processed = 1,
                                processed_timestamp = ?
                            WHERE event_id = ?
                        """, (output_path, int(datetime.now().timestamp() * 1000), event_id))
                        conn.commit()

                    # Complete
                    processing_tasks[task_id]["status"] = "completed"
                    processing_tasks[task_id]["progress"] = 100
                    processing_tasks[task_id]["output_path"] = output_path

                    logger.info(f"🎉 Event {event_id} processed successfully: {output_filename}")

                except subprocess.TimeoutExpired:
                    logger.error(f"❌ Timeout cutting video for event {event_id}")
                    processing_tasks[task_id]["status"] = "error"
                    processing_tasks[task_id]["error"] = "Video cutting timed out (2 min limit)"
                except Exception as e:
                    logger.error(f"❌ Error processing event {event_id}: {e}")
                    processing_tasks[task_id]["status"] = "error"
                    processing_tasks[task_id]["error"] = str(e)

            # Start processing in background thread
            thread = threading.Thread(target=process_video)
            thread.daemon = True
            thread.start()

            return jsonify({
                "task_id": task_id,
                "status": "started",
                "message": f"Processing started for {tracking_code}"
            }), 200

    except Exception as e:
        logger.error(f"Error starting event processing: {e}")
        return jsonify({"error": str(e)}), 500

@query_bp.route('/process-status/<task_id>', methods=['GET'])
@require_valid_license
def get_process_status(task_id):
    """Get processing status for a task"""
    try:
        if task_id not in processing_tasks:
            return jsonify({"error": "Task not found"}), 404

        task = processing_tasks[task_id]
        return jsonify(task), 200

    except Exception as e:
        logger.error(f"Error getting process status: {e}")
        return jsonify({"error": str(e)}), 500

@query_bp.route('/play-video', methods=['POST'])
@require_valid_license
def play_video():
    """Play video in default video player"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')

        if not video_path:
            return jsonify({"error": "Missing video_path"}), 400

        if not os.path.exists(video_path):
            return jsonify({"error": f"Video file not found: {video_path}"}), 404

        # Open video with default player
        import subprocess
        import platform

        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["open", video_path])
        elif system == "Windows":
            subprocess.run(["start", "", video_path], shell=True)
        else:  # Linux
            subprocess.run(["xdg-open", video_path])

        logger.info(f"✅ Playing video: {os.path.basename(video_path)}")
        return jsonify({"message": f"Playing video: {os.path.basename(video_path)}"}), 200

    except Exception as e:
        logger.error(f"Error playing video: {e}")
        return jsonify({"error": str(e)}), 500

@query_bp.route('/get-platform-list', methods=['GET'])
def get_platform_list():
    """Get simple list of available platforms from database"""
    try:
        platforms = []

        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT platform_name, column_letter
                FROM platform_column_mappings
                WHERE is_active = 1
                ORDER BY platform_name
            """)

            for row in cursor.fetchall():
                platforms.append({
                    'name': row[0],
                    'column': row[1]
                })

        logger.info(f"Retrieved {len(platforms)} platforms from database")
        return jsonify({'platforms': platforms}), 200

    except Exception as e:
        logger.error(f"Error getting platform list: {e}")
        return jsonify({'error': str(e)}), 500

@query_bp.route('/save-platform-preference', methods=['POST'])
def save_platform_preference():
    """Save simple platform preference (name and column only)"""
    try:
        data = request.get_json()
        platform_name = data.get('platform_name')
        column_letter = data.get('column_letter')

        if not platform_name or not column_letter:
            return jsonify({'error': 'Platform name and column letter are required'}), 400

        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Check if platform already exists
            cursor.execute("""
                SELECT id FROM platform_column_mappings
                WHERE platform_name = ? AND is_active = 1
            """, (platform_name,))

            existing = cursor.fetchone()

            if existing:
                # Update existing platform
                cursor.execute("""
                    UPDATE platform_column_mappings
                    SET column_letter = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE platform_name = ? AND is_active = 1
                """, (column_letter, platform_name))
                action = 'updated'
            else:
                # Create new platform
                cursor.execute("""
                    INSERT INTO platform_column_mappings (platform_name, column_letter)
                    VALUES (?, ?)
                """, (platform_name, column_letter))
                action = 'created'

            conn.commit()

        logger.info(f"Platform preference saved: {platform_name} -> column {column_letter} ({action})")

        return jsonify({
            'success': True,
            'action': action,
            'message': f'Platform preference {action} for {platform_name}'
        }), 200

    except Exception as e:
        logger.error(f"Error saving platform preference: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# REMOVED: get-platform-preferences endpoint (complex auto-detection)
# Replaced by simple get-platform-list endpoint above

# REMOVED: get-platform-suggestions endpoint (complex auto-detection)
# Replaced by simple text-based detection in frontend

# REMOVED: update-platform-usage endpoint (complex auto-detection)
# No usage statistics needed for simplified approach

@query_bp.route('/browse-location', methods=['POST'])
def browse_location():
    """Open file explorer at the folder containing the video file"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')

        if not file_path:
            return jsonify({"error": "Missing file_path"}), 400

        # Get the directory containing the file
        if os.path.isfile(file_path):
            directory = os.path.dirname(file_path)
        elif os.path.isdir(file_path):
            directory = file_path
        else:
            return jsonify({"error": f"Path not found: {file_path}"}), 404

        # Open file explorer at that directory
        import subprocess
        import platform

        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["open", directory])
        elif system == "Windows":
            subprocess.run(["explorer", directory])
        else:  # Linux
            subprocess.run(["nautilus", directory])

        logger.info(f"✅ Opened directory: {directory}")
        return jsonify({"message": f"Opened directory: {os.path.basename(directory)}"}), 200

    except Exception as e:
        logger.error(f"Error opening directory: {e}")
        return jsonify({"error": str(e)}), 500

@query_bp.route('/browse-output', methods=['GET'])
def browse_output():
    """Open output directory in file explorer"""
    try:
        with safe_db_connection() as conn:
            cursor = conn.cursor()

            # Get output_path from config
            cursor.execute("SELECT output_path FROM processing_config WHERE id = 1")
            result = cursor.fetchone()

            if not result or not result[0]:
                return jsonify({"success": False, "error": "Output path not configured"}), 500

            output_dir = result[0]

            # Check if directory exists
            if not os.path.exists(output_dir):
                return jsonify({"success": False, "error": f"Output directory not found: {output_dir}"}), 404

            # Open file explorer
            import subprocess
            import platform

            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            elif system == "Windows":
                subprocess.run(["explorer", output_dir])
            else:  # Linux
                subprocess.run(["nautilus", output_dir])

            logger.info(f"✅ Opened output directory: {output_dir}")
            return jsonify({"success": True, "message": f"Opened: {output_dir}"}), 200

    except Exception as e:
        logger.error(f"Error opening output directory: {e}")
        return jsonify({"success": False, "error": str(e)}), 500