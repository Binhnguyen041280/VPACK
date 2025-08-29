"""
Analysis Streaming Blueprint
Real-time video analysis streaming using Server-Sent Events
Tận dụng các blueprints và services có sẵn
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from modules.technician.streaming_analyzer import streaming_analyzer, AnalysisMethod
from modules.technician.hand_detection_streaming import HandDetectionStreaming
from modules.technician.qr_detector_streaming import QRDetectorStreaming
from modules.config.services.step4_roi_service import roi_video_service
import json
import time
import logging
from typing import Dict, Any, Generator

analysis_streaming_bp = Blueprint('analysis_streaming', __name__)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@analysis_streaming_bp.route('/start-analysis', methods=['POST'])
def start_analysis_session():
    """
    Bắt đầu session phân tích video
    Tận dụng roi_video_service để validate video
    """
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        method = data.get('method', 'traditional')  # 'traditional' hoặc 'qr_code'
        rois = data.get('rois', [])
        
        logger.info(f"Starting analysis session: method={method}, video={video_path}")
        
        # Input validation
        if not video_path:
            return jsonify({
                "success": False, 
                "error": "Missing video_path parameter"
            }), 400
        
        if not rois:
            return jsonify({
                "success": False, 
                "error": "Missing ROI configurations"
            }), 400
            
        # Validate video using existing service
        validation = roi_video_service.validate_video_path(video_path)
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": validation['error'],
                "details": validation['details']
            }), 400
        
        # Get video metadata
        metadata_result = roi_video_service.get_video_metadata(video_path)
        if not metadata_result['success']:
            return jsonify({
                "success": False,
                "error": metadata_result['error']
            }), 400
            
        metadata = metadata_result['metadata']
        
        # Validate ROI coordinates against video dimensions
        roi_validation = roi_video_service.validate_roi_coordinates(
            rois, metadata['resolution']['width'], metadata['resolution']['height']
        )
        if not roi_validation['valid']:
            return jsonify({
                "success": False,
                "error": roi_validation['error'],
                "errors": roi_validation.get('errors', [])
            }), 400
        
        # Create analysis session
        analysis_method = AnalysisMethod.TRADITIONAL if method == 'traditional' else AnalysisMethod.QR_CODE
        session_id = streaming_analyzer.create_session(
            video_path=video_path,
            method=analysis_method,
            rois=roi_validation['validated_rois']
        )
        
        # Start analysis
        success = streaming_analyzer.start_analysis(session_id)
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to start analysis"
            }), 500
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "method": method,
            "video_metadata": metadata,
            "validated_rois": roi_validation['validated_rois'],
            "stream_url": f"/api/analysis-streaming/stream/{session_id}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting analysis session: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"System error: {str(e)}"
        }), 500

@analysis_streaming_bp.route('/stream/<session_id>')
def stream_analysis_data(session_id: str):
    """
    Server-Sent Events stream cho real-time analysis data
    """
    try:
        def generate_analysis_stream() -> Generator[str, None, None]:
            logger.info(f"Starting SSE stream for session {session_id}")
            
            # Send initial connection confirmation
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected', 'session_id': session_id})}\n\n"
            
            consecutive_empty_count = 0
            max_empty_count = 50  # Stop after 50 consecutive empty responses (5 seconds)
            
            while consecutive_empty_count < max_empty_count:
                try:
                    # Get session status
                    status = streaming_analyzer.get_session_status(session_id)
                    if not status:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
                        break
                    
                    # Send status update
                    yield f"data: {json.dumps({'type': 'status', 'data': status})}\n\n"
                    
                    # Check if analysis is complete
                    if status['status'] in ['stopped', 'error']:
                        yield f"data: {json.dumps({'type': 'complete', 'status': status['status']})}\n\n"
                        break
                    
                    # Get stream data
                    stream_data = streaming_analyzer.get_stream_data(session_id, timeout=0.1)
                    if stream_data:
                        consecutive_empty_count = 0
                        yield f"data: {json.dumps({'type': 'analysis', 'data': stream_data})}\n\n"
                    else:
                        consecutive_empty_count += 1
                        
                    time.sleep(0.1)  # 10 FPS update rate
                    
                except GeneratorExit:
                    logger.info(f"Client disconnected from stream {session_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in stream generation: {str(e)}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break
            
            logger.info(f"Ending SSE stream for session {session_id}")
            
        return Response(
            stream_with_context(generate_analysis_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': 'http://localhost:3000',
                'Access-Control-Allow-Credentials': 'true'
            }
        )
        
    except Exception as e:
        logger.error(f"Error setting up stream for session {session_id}: {str(e)}")
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            mimetype='text/event-stream'
        )

@analysis_streaming_bp.route('/stop-analysis/<session_id>', methods=['POST'])
def stop_analysis_session(session_id: str):
    """Dừng session phân tích"""
    try:
        success = streaming_analyzer.stop_analysis(session_id)
        if success:
            return jsonify({
                "success": True,
                "message": f"Analysis session {session_id} stopped successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to stop analysis session {session_id}"
            }), 400
            
    except Exception as e:
        logger.error(f"Error stopping analysis session {session_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"System error: {str(e)}"
        }), 500

@analysis_streaming_bp.route('/session-status/<session_id>', methods=['GET'])
def get_session_status(session_id: str):
    """Lấy trạng thái session phân tích"""
    try:
        status = streaming_analyzer.get_session_status(session_id)
        if status:
            return jsonify({
                "success": True,
                "status": status
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Session {session_id} not found"
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting session status {session_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"System error: {str(e)}"
        }), 500

@analysis_streaming_bp.route('/cleanup-session/<session_id>', methods=['POST'])
def cleanup_analysis_session(session_id: str):
    """Dọn dẹp resources của session"""
    try:
        streaming_analyzer.cleanup_session(session_id)
        return jsonify({
            "success": True,
            "message": f"Session {session_id} cleaned up successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"System error: {str(e)}"
        }), 500

@analysis_streaming_bp.route('/test-traditional', methods=['POST'])
def test_traditional_detection():
    """
    Endpoint test cho traditional hand detection
    Sử dụng video test có sẵn
    """
    try:
        # Sử dụng video test được cung cấp
        test_video = "/Users/annhu/vtrack_app/V_Track/resources/Inputvideo/Cam1D/Cam1D_20250604_110517.mp4"
        
        # Validate video
        validation = roi_video_service.validate_video_path(test_video)
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": f"Test video not valid: {validation['error']}"
            }), 400
        
        # Get video metadata
        metadata_result = roi_video_service.get_video_metadata(test_video)
        if not metadata_result['success']:
            return jsonify({
                "success": False,
                "error": f"Cannot get video metadata: {metadata_result['error']}"
            }), 400
            
        metadata = metadata_result['metadata']
        
        # Create test ROI (center area of video)
        center_x = metadata['resolution']['width'] // 4
        center_y = metadata['resolution']['height'] // 4
        roi_width = metadata['resolution']['width'] // 2
        roi_height = metadata['resolution']['height'] // 2
        
        test_rois = [{
            'x': center_x,
            'y': center_y,
            'w': roi_width,
            'h': roi_height,
            'type': 'packing_area',
            'label': 'Test Packing Area'
        }]
        
        # Create and start analysis session
        session_id = streaming_analyzer.create_session(
            video_path=test_video,
            method=AnalysisMethod.TRADITIONAL,
            rois=test_rois
        )
        
        success = streaming_analyzer.start_analysis(session_id)
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to start test analysis"
            }), 500
        
        return jsonify({
            "success": True,
            "message": "Traditional detection test started",
            "session_id": session_id,
            "test_video": test_video,
            "video_metadata": metadata,
            "test_rois": test_rois,
            "stream_url": f"/api/analysis-streaming/stream/{session_id}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in traditional detection test: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Test error: {str(e)}"
        }), 500

@analysis_streaming_bp.route('/test-qr', methods=['POST'])
def test_qr_detection():
    """
    Endpoint test cho QR code detection
    """
    try:
        # Sử dụng video test được cung cấp
        test_video = "/Users/annhu/vtrack_app/V_Track/resources/Inputvideo/Cam1D/Cam1D_20250604_110517.mp4"
        
        # Validate video
        validation = roi_video_service.validate_video_path(test_video)
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": f"Test video not valid: {validation['error']}"
            }), 400
        
        # Get video metadata
        metadata_result = roi_video_service.get_video_metadata(test_video)
        if not metadata_result['success']:
            return jsonify({
                "success": False,
                "error": f"Cannot get video metadata: {metadata_result['error']}"
            }), 400
            
        metadata = metadata_result['metadata']
        
        # Create test ROIs for QR detection
        center_x = metadata['resolution']['width'] // 4
        center_y = metadata['resolution']['height'] // 4
        roi_width = metadata['resolution']['width'] // 3
        roi_height = metadata['resolution']['height'] // 3
        
        test_rois = [
            {
                'x': center_x,
                'y': center_y,
                'w': roi_width,
                'h': roi_height,
                'type': 'qr_mvd',
                'label': 'Test QR MVD Area'
            },
            {
                'x': center_x + roi_width + 50,
                'y': center_y,
                'w': roi_width // 2,
                'h': roi_height // 2,
                'type': 'qr_trigger',
                'label': 'Test QR Trigger Area'
            }
        ]
        
        # Create and start analysis session
        session_id = streaming_analyzer.create_session(
            video_path=test_video,
            method=AnalysisMethod.QR_CODE,
            rois=test_rois
        )
        
        success = streaming_analyzer.start_analysis(session_id)
        if not success:
            return jsonify({
                "success": False,
                "error": "Failed to start QR test analysis"
            }), 500
        
        return jsonify({
            "success": True,
            "message": "QR detection test started",
            "session_id": session_id,
            "test_video": test_video,
            "video_metadata": metadata,
            "test_rois": test_rois,
            "stream_url": f"/api/analysis-streaming/stream/{session_id}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in QR detection test: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Test error: {str(e)}"
        }), 500

@analysis_streaming_bp.route('/health', methods=['GET'])
def health_check():
    """Health check cho analysis streaming service"""
    try:
        # Check các dependencies
        hand_detector = HandDetectionStreaming()
        qr_detector = QRDetectorStreaming()
        
        return jsonify({
            "status": "healthy",
            "active_sessions": len(streaming_analyzer.sessions),
            "hand_detector_ready": hasattr(hand_detector, 'hands') and hand_detector.hands is not None,
            "qr_detector_ready": qr_detector.initialized,
            "endpoints": [
                "/start-analysis",
                "/stream/<session_id>",
                "/stop-analysis/<session_id>",
                "/session-status/<session_id>",
                "/cleanup-session/<session_id>",
                "/test-traditional",
                "/test-qr"
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500