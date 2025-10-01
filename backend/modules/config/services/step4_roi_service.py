"""
ROI Configuration Service Layer
Handles video streaming, frame extraction, and ROI processing for web-based configuration
"""

import os
import cv2
import json
import base64
import logging
from typing import Dict, Any, Optional, Tuple, List
from flask import Response
import mimetypes
from werkzeug.datastructures import Range
import uuid
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class ROIVideoService:
    """Service class for handling ROI video operations"""
    
    def __init__(self):
        # Define supported video formats
        self.supported_formats = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo', 
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm'
        }
        
        # Video processing settings
        self.max_video_size = 1024 * 1024 * 1024  # 1GB limit
        self.chunk_size = 8192  # 8KB chunks for streaming
        
    def validate_video_path(self, video_path: str) -> Dict[str, Any]:
        """
        Validate video file exists, is readable, and supported format
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with validation results
        """
        try:
            # Basic path validation
            if not video_path or not isinstance(video_path, str):
                return {
                    'valid': False,
                    'error': 'Invalid video path provided',
                    'details': {'path': video_path}
                }
            
            # Normalize path
            normalized_path = os.path.normpath(video_path)
            
            # Check if file exists
            if not os.path.exists(normalized_path):
                return {
                    'valid': False,
                    'error': f'Video file does not exist: {normalized_path}',
                    'details': {'path': normalized_path, 'exists': False}
                }
            
            # Check if it's a file (not directory)
            if not os.path.isfile(normalized_path):
                return {
                    'valid': False,
                    'error': f'Path is not a file: {normalized_path}',
                    'details': {'path': normalized_path, 'is_file': False}
                }
            
            # Check file extension
            file_ext = os.path.splitext(normalized_path)[1].lower()
            if file_ext not in self.supported_formats:
                return {
                    'valid': False,
                    'error': f'Unsupported video format: {file_ext}',
                    'details': {
                        'path': normalized_path,
                        'extension': file_ext,
                        'supported_formats': list(self.supported_formats.keys())
                    }
                }
            
            # Check file size
            file_size = os.path.getsize(normalized_path)
            if file_size > self.max_video_size:
                return {
                    'valid': False,
                    'error': f'Video file too large: {file_size / (1024*1024):.1f}MB (max: {self.max_video_size / (1024*1024)}MB)',
                    'details': {'path': normalized_path, 'size_mb': file_size / (1024*1024)}
                }
            
            # Check if file is readable
            try:
                with open(normalized_path, 'rb') as f:
                    f.read(1024)  # Try to read first 1KB
            except PermissionError:
                return {
                    'valid': False,
                    'error': f'No permission to read video file: {normalized_path}',
                    'details': {'path': normalized_path, 'readable': False}
                }
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'Cannot read video file: {str(e)}',
                    'details': {'path': normalized_path, 'read_error': str(e)}
                }
            
            return {
                'valid': True,
                'path': normalized_path,
                'extension': file_ext,
                'mime_type': self.supported_formats[file_ext],
                'size_mb': file_size / (1024*1024),
                'details': {
                    'path': normalized_path,
                    'size_bytes': file_size,
                    'exists': True,
                    'readable': True,
                    'is_file': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating video path {video_path}: {str(e)}")
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}',
                'details': {'path': video_path, 'exception': str(e)}
            }
    
    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """
        Extract video metadata using OpenCV
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with video metadata
        """
        try:
            # First validate the video path
            validation = self.validate_video_path(video_path)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'details': validation['details']
                }
            
            # Open video with OpenCV
            cap = cv2.VideoCapture(validation['path'])
            
            if not cap.isOpened():
                return {
                    'success': False,
                    'error': f'Cannot open video file with OpenCV: {validation["path"]}',
                    'details': {'opencv_error': True}
                }
            
            try:
                # Extract video properties
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # Calculate duration
                duration_seconds = frame_count / fps if fps > 0 else 0
                
                # Format duration
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                duration_formatted = f"{minutes}m {seconds}s"
                
                # Get codec information
                fourcc = cap.get(cv2.CAP_PROP_FOURCC)
                codec = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)]).strip()
                
                return {
                    'success': True,
                    'metadata': {
                        'path': validation['path'],
                        'filename': os.path.basename(validation['path']),
                        'extension': validation['extension'],
                        'mime_type': validation['mime_type'],
                        'size_mb': validation['size_mb'],
                        'duration_seconds': duration_seconds,
                        'duration_formatted': duration_formatted,
                        'frame_count': frame_count,
                        'fps': fps,
                        'resolution': {
                            'width': width,
                            'height': height,
                            'aspect_ratio': round(width / height, 2) if height > 0 else 0
                        },
                        'codec': codec,
                        'is_valid': True
                    }
                }
                
            finally:
                cap.release()
                
        except Exception as e:
            logger.error(f"Error extracting video metadata from {video_path}: {str(e)}")
            return {
                'success': False,
                'error': f'Metadata extraction error: {str(e)}',
                'details': {'exception': str(e)}
            }
    
    def stream_video_range(self, video_path: str, range_header: Optional[str] = None) -> Response:
        """
        Stream video with range request support for seeking
        
        Args:
            video_path: Path to video file
            range_header: HTTP Range header value
            
        Returns:
            Flask Response object for streaming
        """
        try:
            # Validate video path
            validation = self.validate_video_path(video_path)
            if not validation['valid']:
                return Response(
                    json.dumps({
                        'error': validation['error'],
                        'details': validation['details']
                    }),
                    status=400,
                    mimetype='application/json'
                )
            
            file_path = validation['path']
            file_size = validation['details']['size_bytes']
            mime_type = validation['mime_type']
            
            # Handle range requests for video seeking
            start = 0
            end = file_size - 1
            
            if range_header:
                try:
                    # Parse range header (e.g., "bytes=0-1023")
                    range_match = range_header.replace('bytes=', '')
                    if '-' in range_match:
                        start_str, end_str = range_match.split('-', 1)
                        if start_str:
                            start = int(start_str)
                        if end_str:
                            end = int(end_str)
                        
                        # Ensure valid range
                        start = max(0, start)
                        end = min(file_size - 1, end)
                        
                except (ValueError, IndexError) as e:
                    logger.warning(f"Invalid range header: {range_header}, error: {str(e)}")
                    # Continue with full file if range parsing fails
            
            # Create generator for streaming chunks
            def generate_video_chunks():
                with open(file_path, 'rb') as video_file:
                    video_file.seek(start)
                    remaining = end - start + 1
                    
                    while remaining > 0:
                        chunk_size = min(self.chunk_size, remaining)
                        chunk = video_file.read(chunk_size)
                        
                        if not chunk:
                            break
                            
                        remaining -= len(chunk)
                        yield chunk
            
            # Create response
            response = Response(
                generate_video_chunks(),
                status=206 if range_header else 200,
                mimetype=mime_type,
                direct_passthrough=True
            )
            
            # Add headers for video streaming
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Length'] = str(end - start + 1)
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            if range_header:
                response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            
            # CORS headers for frontend access
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Range'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range, Content-Length'
            
            return response
            
        except Exception as e:
            logger.error(f"Error streaming video {video_path}: {str(e)}")
            return Response(
                json.dumps({
                    'error': f'Video streaming error: {str(e)}',
                    'details': {'exception': str(e)}
                }),
                status=500,
                mimetype='application/json'
            )
    
    def extract_frame_at_time(self, video_path: str, timestamp_seconds: float, 
                             frame_format: str = 'jpg', quality: int = 85) -> Dict[str, Any]:
        """
        Extract frame at specific timestamp and return as base64
        
        Args:
            video_path: Path to video file
            timestamp_seconds: Time in seconds to extract frame
            frame_format: Output format ('jpg' or 'png')
            quality: JPEG quality (1-100)
            
        Returns:
            Dict with frame data or error
        """
        try:
            # Validate video path
            validation = self.validate_video_path(video_path)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error'],
                    'details': validation['details']
                }
            
            # Get video metadata to validate timestamp
            metadata_result = self.get_video_metadata(video_path)
            if not metadata_result['success']:
                return metadata_result
            
            metadata = metadata_result['metadata']
            max_duration = metadata['duration_seconds']
            
            # Validate timestamp
            if timestamp_seconds < 0 or timestamp_seconds > max_duration:
                return {
                    'success': False,
                    'error': f'Timestamp {timestamp_seconds}s is out of range (0-{max_duration}s)',
                    'details': {
                        'timestamp': timestamp_seconds,
                        'max_duration': max_duration
                    }
                }
            
            # Open video and seek to timestamp
            cap = cv2.VideoCapture(validation['path'])
            if not cap.isOpened():
                return {
                    'success': False,
                    'error': f'Cannot open video file: {validation["path"]}',
                    'details': {'opencv_error': True}
                }
            
            try:
                # Seek to the desired timestamp
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)
                
                # Read the frame
                ret, frame = cap.read()
                if not ret or frame is None:
                    return {
                        'success': False,
                        'error': f'Cannot extract frame at timestamp {timestamp_seconds}s',
                        'details': {'timestamp': timestamp_seconds, 'frame_read': False}
                    }
                
                # Encode frame to specified format
                if frame_format.lower() == 'png':
                    encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
                    success, buffer = cv2.imencode('.png', frame, encode_params)
                    mime_type = 'image/png'
                else:  # Default to JPEG
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, max(1, min(100, quality))]
                    success, buffer = cv2.imencode('.jpg', frame, encode_params)
                    mime_type = 'image/jpeg'
                    frame_format = 'jpg'
                
                if not success:
                    return {
                        'success': False,
                        'error': f'Failed to encode frame to {frame_format.upper()}',
                        'details': {'encoding_error': True}
                    }
                
                # Convert to base64
                frame_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
                
                return {
                    'success': True,
                    'frame': {
                        'data': frame_base64,
                        'format': frame_format,
                        'mime_type': mime_type,
                        'timestamp': timestamp_seconds,
                        'data_url': f'data:{mime_type};base64,{frame_base64}',
                        'dimensions': {
                            'width': frame.shape[1],
                            'height': frame.shape[0]
                        },
                        'size_bytes': len(buffer.tobytes())
                    },
                    'video_metadata': metadata
                }
                
            finally:
                cap.release()
                
        except Exception as e:
            logger.error(f"Error extracting frame from {video_path} at {timestamp_seconds}s: {str(e)}")
            return {
                'success': False,
                'error': f'Frame extraction error: {str(e)}',
                'details': {
                    'exception': str(e),
                    'timestamp': timestamp_seconds
                }
            }
    
    def extract_frame_by_number(self, video_path: str, frame_number: int, 
                               frame_format: str = 'jpg', quality: int = 85) -> Dict[str, Any]:
        """
        Extract frame by frame number
        
        Args:
            video_path: Path to video file
            frame_number: Frame number to extract (0-based)
            frame_format: Output format ('jpg' or 'png')
            quality: JPEG quality (1-100)
            
        Returns:
            Dict with frame data or error
        """
        try:
            # Get video metadata
            metadata_result = self.get_video_metadata(video_path)
            if not metadata_result['success']:
                return metadata_result
                
            metadata = metadata_result['metadata']
            max_frames = metadata['frame_count']
            fps = metadata['fps']
            
            # Validate frame number
            if frame_number < 0 or frame_number >= max_frames:
                return {
                    'success': False,
                    'error': f'Frame number {frame_number} is out of range (0-{max_frames-1})',
                    'details': {
                        'frame_number': frame_number,
                        'max_frames': max_frames
                    }
                }
            
            # Calculate timestamp from frame number
            timestamp_seconds = frame_number / fps if fps > 0 else 0
            
            # Use timestamp extraction method
            return self.extract_frame_at_time(video_path, timestamp_seconds, frame_format, quality)
            
        except Exception as e:
            logger.error(f"Error extracting frame {frame_number} from {video_path}: {str(e)}")
            return {
                'success': False,
                'error': f'Frame extraction error: {str(e)}',
                'details': {
                    'exception': str(e),
                    'frame_number': frame_number
                }
            }
    
    def validate_roi_coordinates(self, roi_data: List[Dict[str, Any]], 
                                video_width: int, video_height: int) -> Dict[str, Any]:
        """
        Validate ROI coordinate data
        
        Args:
            roi_data: List of ROI dictionaries with x, y, w, h
            video_width: Video width in pixels
            video_height: Video height in pixels
            
        Returns:
            Dict with validation results
        """
        try:
            if not isinstance(roi_data, list):
                return {
                    'valid': False,
                    'error': 'ROI data must be a list',
                    'details': {'roi_data_type': type(roi_data).__name__}
                }
            
            validated_rois = []
            errors = []
            
            for i, roi in enumerate(roi_data):
                if not isinstance(roi, dict):
                    errors.append(f'ROI {i}: Must be a dictionary')
                    continue
                
                # Check required fields
                required_fields = ['x', 'y', 'w', 'h']
                missing_fields = [f for f in required_fields if f not in roi]
                if missing_fields:
                    errors.append(f'ROI {i}: Missing fields: {missing_fields}')
                    continue
                
                try:
                    x = int(roi['x'])
                    y = int(roi['y'])
                    w = int(roi['w'])
                    h = int(roi['h'])
                except (ValueError, TypeError):
                    errors.append(f'ROI {i}: Coordinates must be integers')
                    continue
                
                # Validate coordinate bounds
                if x < 0 or y < 0:
                    errors.append(f'ROI {i}: Coordinates cannot be negative (x={x}, y={y})')
                    continue
                
                if w <= 0 or h <= 0:
                    errors.append(f'ROI {i}: Width and height must be positive (w={w}, h={h})')
                    continue
                
                if x + w > video_width or y + h > video_height:
                    errors.append(f'ROI {i}: ROI extends beyond video bounds ({x+w} > {video_width} or {y+h} > {video_height})')
                    continue
                
                # Minimum size validation (e.g., 10x10 pixels)
                min_size = 10
                if w < min_size or h < min_size:
                    errors.append(f'ROI {i}: ROI too small (minimum {min_size}x{min_size}, got {w}x{h})')
                    continue
                
                # Add validated ROI
                validated_roi = {
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'type': roi.get('type', 'detection'),  # Default type
                    'label': roi.get('label', f'ROI_{i+1}')  # Default label
                }
                validated_rois.append(validated_roi)
            
            if errors:
                return {
                    'valid': False,
                    'error': 'ROI validation failed',
                    'errors': errors,
                    'valid_rois': validated_rois
                }
            
            return {
                'valid': True,
                'validated_rois': validated_rois,
                'count': len(validated_rois)
            }
            
        except Exception as e:
            logger.error(f"Error validating ROI coordinates: {str(e)}")
            return {
                'valid': False,
                'error': f'ROI validation error: {str(e)}',
                'details': {'exception': str(e)}
            }

# Service instance
roi_video_service = ROIVideoService()