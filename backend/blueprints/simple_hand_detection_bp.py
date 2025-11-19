"""
Simple Hand Detection Blueprint
Single synchronous endpoint for hand detection at specific video times
Following the simple pattern from 2hand_detection.py
"""

from flask import Blueprint, request, jsonify
from modules.technician.hand_detection import detect_hands_at_time, preprocess_video_hands
from modules.config.logging_config import get_logger
import time
import threading
from datetime import datetime, timedelta

simple_hand_detection_bp = Blueprint('simple_hand_detection', __name__)
logger = get_logger(__name__)

# In-memory cache for pre-processed video hand detections
# Structure: {cache_key: {'detections': [...], 'metadata': {...}, 'expires_at': datetime}}
preprocessing_cache = {}
preprocessing_progress = {}  # Track progress for ongoing processing

@simple_hand_detection_bp.route('/process-frame', methods=['POST'])
def process_frame():
    """
    Process single frame for hand detection at specific video time
    
    Request body:
    {
        "video_path": str,
        "time_seconds": float,
        "roi_config": {  # optional
            "x": int,
            "y": int, 
            "w": int,
            "h": int
        }
    }
    
    Response:
    {
        "success": bool,
        "landmarks": list,  # Hand landmarks in normalized coordinates
        "confidence": float,
        "frame_number": int,
        "video_time": float,
        "hands_detected": int,
        "processing_time_ms": float,
        "error": str (if error)
    }
    """
    try:
        start_time = time.time()
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate required parameters
        video_path = data.get('video_path')
        time_seconds = data.get('time_seconds')
        
        if not video_path:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: video_path"
            }), 400
            
        if time_seconds is None:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: time_seconds"
            }), 400
        
        # Validate time_seconds type
        try:
            time_seconds = float(time_seconds)
            if time_seconds < 0:
                raise ValueError("time_seconds must be non-negative")
        except (ValueError, TypeError) as e:
            return jsonify({
                "success": False,
                "error": f"Invalid time_seconds value: {str(e)}"
            }), 400
        
        # Get optional ROI configuration
        roi_config = data.get('roi_config')
        if roi_config:
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
        
        logger.debug(f"Processing frame at time {time_seconds}s for video: {video_path}")
        
        # Call hand detection function
        result = detect_hands_at_time(
            video_path=video_path,
            time_seconds=time_seconds, 
            roi_config=roi_config
        )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        result['processing_time_ms'] = round(processing_time, 2)
        
        if result.get('success'):
            logger.debug(f"Hand detection successful: {result.get('hands_detected', 0)} hands detected in {processing_time:.1f}ms")
            return jsonify(result), 200
        else:
            logger.error(f"Hand detection failed: {result.get('error', 'Unknown error')}")
            return jsonify(result), 500
            
    except Exception as e:
        error_msg = f"Unexpected error in hand detection endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@simple_hand_detection_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for simple hand detection service"""
    try:
        cleanup_expired_cache()
        
        return jsonify({
            "status": "healthy",
            "service": "simple_hand_detection",
            "version": "2.0_preprocessing",
            "endpoints": [
                "POST /process-frame - Process single frame for hand detection",
                "POST /preprocess-video - Pre-process entire video at 5fps",
                "GET /preprocess-status/<cache_key> - Check preprocessing progress",
                "POST /get-cached-landmarks - Get landmarks from cache by timestamp",
                "DELETE /clear-cache/<cache_key> - Clear cached results",
                "GET /cache-info - Cache statistics and memory usage",
                "GET /health - Health check"
            ],
            "cache_status": {
                "active_cache_entries": len(preprocessing_cache),
                "active_processing_jobs": len(preprocessing_progress),
                "total_cached_detections": sum(
                    len(cache_data.get('detections', []))
                    for cache_data in preprocessing_cache.values()
                ),
                "cache_ttl_minutes": 30
            },
            "features": [
                "5fps video preprocessing",
                "Perfect timestamp synchronization",
                "Dynamic landmarks sizing",
                "Automatic cache expiration",
                "Background processing"
            ],
            "description": "Advanced hand detection with preprocessing and caching for perfect video synchronization"
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@simple_hand_detection_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint with sample video for development"""
    try:
        # Use the test video from the project (Docker-compatible path)
        # In Docker: /app/resources/Inputvideo/Cam1D/...
        # In local dev: use relative path from project root
        if os.getenv('EPACK_IN_DOCKER') == 'true':
            test_video = "/app/resources/Inputvideo/Cam1D/Cam1D_20250604_110517.mp4"
        else:
            # Local development - use relative path
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            test_video = os.path.join(project_root, "resources/Inputvideo/Cam1D/Cam1D_20250604_110517.mp4")
        test_time = 5.0  # Test at 5 seconds
        
        # Test ROI (center area)
        test_roi = {
            "x": 200,
            "y": 150, 
            "w": 400,
            "h": 300
        }
        
        logger.info(f"Running test detection at {test_time}s with ROI {test_roi}")
        
        result = detect_hands_at_time(
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
        error_msg = f"Test endpoint error: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "test_status": "failed",
            "error": error_msg
        }), 500

def generate_cache_key(video_path: str, roi_config: dict) -> str:
    """Generate unique cache key for video + ROI combination"""
    import hashlib
    
    roi_str = f"{roi_config['x']}_{roi_config['y']}_{roi_config['w']}_{roi_config['h']}"
    cache_input = f"{video_path}_{roi_str}"
    return hashlib.md5(cache_input.encode()).hexdigest()

def cleanup_expired_cache():
    """Remove expired cache entries"""
    global preprocessing_cache
    
    now = datetime.now()
    expired_keys = [
        key for key, cache_data in preprocessing_cache.items()
        if cache_data.get('expires_at', now) <= now
    ]
    
    for key in expired_keys:
        del preprocessing_cache[key]
        logger.info(f"Removed expired cache entry: {key}")

@simple_hand_detection_bp.route('/preprocess-video', methods=['POST'])
def preprocess_video():
    """
    Pre-process entire video for hand detection at 5fps
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
        cleanup_expired_cache()
        
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
        cache_key = generate_cache_key(video_path, roi_config)
        
        # Check if already cached and not expired
        if cache_key in preprocessing_cache:
            cache_data = preprocessing_cache[cache_key]
            if cache_data.get('expires_at', datetime.now()) > datetime.now():
                logger.info(f"Returning cached results for {cache_key}")
                return jsonify({
                    "success": True,
                    "cache_key": cache_key,
                    "status": "completed",
                    "progress": 100.0,
                    "detections": cache_data['detections'],
                    "metadata": cache_data['metadata']
                }), 200
        
        # Check if processing is already in progress
        if cache_key in preprocessing_progress:
            progress_data = preprocessing_progress[cache_key]
            return jsonify({
                "success": True,
                "cache_key": cache_key,
                "status": "in_progress",
                "progress": progress_data.get('progress', 0.0),
                "estimated_completion": progress_data.get('estimated_completion')
            }), 202  # 202 Accepted - Processing
        
        # Start background processing
        def background_processing():
            try:
                # Initialize progress tracking
                preprocessing_progress[cache_key] = {
                    'progress': 0.0,
                    'started_at': datetime.now(),
                    'estimated_completion': None,
                    'processed_count': 0,
                    'total_frames': 0
                }
                
                # Initialize main cache entry for progressive accumulation
                preprocessing_cache[cache_key] = {
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
                
                # Progress callback function to update real-time progress and accumulate detections
                def update_progress(progress, processed_count, total_frames, new_detections=None):
                    preprocessing_progress[cache_key].update({
                        'progress': progress,
                        'processed_count': processed_count,
                        'total_frames': total_frames
                    })
                    
                    # Accumulate new detections into main cache (không overwrite)
                    if new_detections and len(new_detections) > 0:
                        if cache_key in preprocessing_cache:
                            # Append new detections to existing list instead of replacing
                            preprocessing_cache[cache_key]['detections'].extend(new_detections)
                            preprocessing_cache[cache_key]['metadata'].update({
                                'progress': progress,
                                'processed_count': processed_count,
                                'total_frames': total_frames
                            })
                            total_detections = len(preprocessing_cache[cache_key]['detections'])
                            logger.debug(f"Accumulated {len(new_detections)} new detections. Total: {total_detections} for {cache_key}")
                        else:
                            logger.warning(f"Cache key {cache_key} not found during update")
                
                logger.info(f"Starting video pre-processing for cache key: {cache_key}")
                
                # Call the pre-processing function with progress callback
                result = preprocess_video_hands(video_path, roi_config, fps, progress_callback=update_progress)
                
                if result.get('success'):
                    # Cache the results for 30 minutes
                    expires_at = datetime.now() + timedelta(minutes=30)
                    preprocessing_cache[cache_key] = {
                        'detections': result['detections'],
                        'metadata': result['metadata'],
                        'expires_at': expires_at,
                        'processed_at': datetime.now()
                    }
                    
                    logger.info(f"Pre-processing completed for {cache_key}: {len(result['detections'])} detections cached")
                else:
                    logger.error(f"Pre-processing failed for {cache_key}: {result.get('error')}")
                
                # Clean up progress tracking
                if cache_key in preprocessing_progress:
                    del preprocessing_progress[cache_key]
                    
            except Exception as e:
                logger.error(f"Background processing error for {cache_key}: {str(e)}")
                if cache_key in preprocessing_progress:
                    del preprocessing_progress[cache_key]
        
        # Start processing in background thread
        thread = threading.Thread(target=background_processing, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "cache_key": cache_key,
            "status": "started",
            "progress": 0.0,
            "message": f"Pre-processing started for video at {fps}fps",
            "estimated_duration_seconds": "10-30"  # Rough estimate
        }), 202  # 202 Accepted - Processing started
        
    except Exception as e:
        error_msg = f"Unexpected error in preprocess-video endpoint: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@simple_hand_detection_bp.route('/preprocess-status/<cache_key>', methods=['GET'])
def preprocess_status(cache_key: str):
    """
    Check status of video pre-processing
    
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
        cleanup_expired_cache()
        
        # Check if completed and cached
        if cache_key in preprocessing_cache:
            cache_data = preprocessing_cache[cache_key]
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
        if cache_key in preprocessing_progress:
            progress_data = preprocessing_progress[cache_key]
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
            "error": f"No processing found for cache key: {cache_key}"
        }), 404
        
    except Exception as e:
        error_msg = f"Error checking preprocess status: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@simple_hand_detection_bp.route('/get-cached-landmarks', methods=['POST'])
def get_cached_landmarks():
    """
    Get landmarks for specific timestamp from cached results
    
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
        "landmarks": list | null,
        "canvas_landmarks": list | null,  # NEW - display-ready coordinates
        "confidence": float | null,
        "exact_match": bool,
        "matched_timestamp": float | null,
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
        
        # Check main cache (now contains progressive accumulation)
        if cache_key not in preprocessing_cache:
            return jsonify({
                "success": False,
                "error": "Cache key not found or expired"
            }), 404
        
        cache_data = preprocessing_cache[cache_key]
        if cache_data.get('expires_at', datetime.now()) <= datetime.now():
            del preprocessing_cache[cache_key]
            return jsonify({
                "success": False,
                "error": "Cache expired"
            }), 404
        
        # Find landmarks for timestamp (exact match within 0.15s tolerance)
        detections = cache_data['detections']
        closest_detection = None
        min_time_diff = float('inf')
        
        for detection in detections:
            time_diff = abs(detection['timestamp'] - timestamp)
            if time_diff < 0.15 and time_diff < min_time_diff:  # 0.15s tolerance for 5fps (0.2s interval)
                closest_detection = detection
                min_time_diff = time_diff
        
        if closest_detection:
            response = {
                "success": True,
                "landmarks": closest_detection['landmarks'],
                "confidence": closest_detection['confidence'],
                "exact_match": min_time_diff < 0.05,  # Consider <0.05s as exact match (looser)
                "matched_timestamp": closest_detection['timestamp'],
                "time_difference": round(min_time_diff, 3)
            }
            
            # Add canvas_landmarks if mapping parameters provided
            if canvas_dims and video_dims and roi_config and closest_detection['landmarks']:
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
                    
                    # Generate canvas landmarks with fixed sizing
                    canvas_response = LandmarkMapper.create_canvas_landmarks_response(
                        closest_detection['landmarks'], roi, video_dimensions, canvas_dimensions
                    )
                    
                    if canvas_response['success']:
                        response['canvas_landmarks'] = canvas_response['canvas_landmarks']
                        response['fixed_sizes'] = canvas_response['fixed_sizes']
                        response['mapping_algorithm'] = 'fixed_size_mapping'
                        logger.debug(f"Added canvas landmarks for timestamp {timestamp}")
                    else:
                        logger.warning(f"Canvas landmark mapping failed: {canvas_response.get('error')}")
                        response['canvas_landmarks'] = None
                        
                except Exception as e:
                    logger.error(f"Error generating canvas landmarks: {e}")
                    response['canvas_landmarks'] = None
            else:
                response['canvas_landmarks'] = None
            
            return jsonify(response), 200
        else:
            return jsonify({
                "success": True,
                "landmarks": None,
                "confidence": None,
                "exact_match": False,
                "matched_timestamp": None,
                "message": f"No hand detection found near timestamp {timestamp}"
            }), 200
        
    except Exception as e:
        error_msg = f"Error getting cached landmarks: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@simple_hand_detection_bp.route('/clear-cache/<cache_key>', methods=['DELETE'])
def clear_cache(cache_key: str):
    """
    Clear cached preprocessing results
    Used when ROI is modified or deleted
    
    Response:
    {
        "success": bool,
        "message": str,
        "error": str (if error)
    }
    """
    try:
        global preprocessing_cache, preprocessing_progress
        
        cache_cleared = False
        progress_cleared = False
        
        # Remove from cache
        if cache_key in preprocessing_cache:
            del preprocessing_cache[cache_key]
            cache_cleared = True
            logger.info(f"Cache cleared for key: {cache_key}")
        
        # Remove from progress tracking
        if cache_key in preprocessing_progress:
            del preprocessing_progress[cache_key]
            progress_cleared = True
            logger.info(f"Progress tracking cleared for key: {cache_key}")
        
        if cache_cleared or progress_cleared:
            return jsonify({
                "success": True,
                "message": f"Cache and progress data cleared for key: {cache_key}",
                "cache_cleared": cache_cleared,
                "progress_cleared": progress_cleared
            }), 200
        else:
            return jsonify({
                "success": True,
                "message": f"No cache found for key: {cache_key} (already cleared)"
            }), 200
        
    except Exception as e:
        error_msg = f"Error clearing cache: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@simple_hand_detection_bp.route('/cache-info', methods=['GET'])
def cache_info():
    """
    Get information about current cache state
    Useful for debugging and monitoring
    
    Response:
    {
        "success": bool,
        "cache_count": int,
        "progress_count": int,
        "cache_keys": list,
        "progress_keys": list,
        "memory_usage_estimate": str
    }
    """
    try:
        cleanup_expired_cache()
        
        cache_keys = list(preprocessing_cache.keys())
        progress_keys = list(preprocessing_progress.keys())
        
        # Rough memory estimate
        total_detections = sum(
            len(cache_data.get('detections', []))
            for cache_data in preprocessing_cache.values()
        )
        memory_estimate_kb = total_detections * 1.5  # ~1.5KB per detection estimate
        
        return jsonify({
            "success": True,
            "cache_count": len(cache_keys),
            "progress_count": len(progress_keys),
            "cache_keys": cache_keys,
            "progress_keys": progress_keys,
            "total_cached_detections": total_detections,
            "memory_usage_estimate_kb": round(memory_estimate_kb, 1),
            "memory_usage_estimate_mb": round(memory_estimate_kb / 1024, 2)
        }), 200
        
    except Exception as e:
        error_msg = f"Error getting cache info: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

