"""
Unit tests for qr_detector module
Tests QR code detection helper functions and error handling
"""
import pytest
import os
import tempfile
from modules.technician.qr_detector import CAMERA_ROI_DIR, MODEL_DIR


class TestQRDetectorConfiguration:
    """Tests for QR detector configuration and constants"""

    def test_model_dir_path(self):
        """Test MODEL_DIR path is properly defined"""
        assert isinstance(MODEL_DIR, str)
        assert "models" in MODEL_DIR
        assert "wechat_qr" in MODEL_DIR

    def test_camera_roi_dir_path(self):
        """Test CAMERA_ROI_DIR path is properly defined"""
        assert isinstance(CAMERA_ROI_DIR, str)
        assert "CameraROI" in CAMERA_ROI_DIR
        assert "output_clips" in CAMERA_ROI_DIR

    def test_model_file_paths(self):
        """Test model file paths are properly defined"""
        from modules.technician.qr_detector import (
            DETECT_PROTO, DETECT_MODEL, SR_PROTO, SR_MODEL
        )

        assert isinstance(DETECT_PROTO, str)
        assert isinstance(DETECT_MODEL, str)
        assert isinstance(SR_PROTO, str)
        assert isinstance(SR_MODEL, str)

        assert "detect.prototxt" in DETECT_PROTO
        assert "detect.caffemodel" in DETECT_MODEL
        assert "sr.prototxt" in SR_PROTO
        assert "sr.caffemodel" in SR_MODEL


class TestDetectQRAtTimeErrorHandling:
    """Tests for detect_qr_at_time() error handling"""

    def test_detect_qr_at_time_with_nonexistent_video(self, mocker):
        """Test detect_qr_at_time with non-existent video"""
        from modules.technician.qr_detector import detect_qr_at_time

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        result = detect_qr_at_time(
            "/nonexistent/video.mp4",
            10.0,
            {'rois': [{'x': 0, 'y': 0, 'w': 100, 'h': 100}]}
        )

        assert result['success'] is False
        assert 'error' in result

    def test_detect_qr_at_time_with_negative_time(self, mocker):
        """Test detect_qr_at_time with negative time"""
        from modules.technician.qr_detector import detect_qr_at_time

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = True
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        result = detect_qr_at_time(
            "/test/video.mp4",
            -5.0,
            {'rois': [{'x': 0, 'y': 0, 'w': 100, 'h': 100}]}
        )

        # Should handle negative time
        assert isinstance(result, dict)
        assert 'success' in result

    def test_detect_qr_at_time_with_cancellation_flag(self, mocker):
        """Test detect_qr_at_time with cancellation flag"""
        from modules.technician.qr_detector import detect_qr_at_time
        import threading

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        cancellation_flag = threading.Event()
        cancellation_flag.set()  # Set cancellation immediately

        result = detect_qr_at_time(
            "/test/video.mp4",
            10.0,
            {'rois': [{'x': 0, 'y': 0, 'w': 100, 'h': 100}]},
            cancellation_flag=cancellation_flag
        )

        # Should respect cancellation flag
        assert isinstance(result, dict)

    def test_detect_qr_at_time_with_invalid_roi_config(self, mocker):
        """Test detect_qr_at_time with invalid ROI config"""
        from modules.technician.qr_detector import detect_qr_at_time

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = True
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        # Empty ROI config
        result = detect_qr_at_time("/test/video.mp4", 10.0, {})

        assert result['success'] is False


class TestPreprocessVideoQRConfiguration:
    """Tests for preprocess_video_qr() configuration"""

    def test_preprocess_video_qr_with_invalid_fps(self, mocker):
        """Test preprocess_video_qr with invalid FPS"""
        from modules.technician.qr_detector import preprocess_video_qr

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        result = preprocess_video_qr(
            "/test/video.mp4",
            {'rois': [{'x': 0, 'y': 0, 'w': 100, 'h': 100}]},
            fps=0
        )

        assert result['success'] is False

    def test_preprocess_video_qr_with_progress_callback(self, mocker):
        """Test preprocess_video_qr with progress callback"""
        from modules.technician.qr_detector import preprocess_video_qr

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        progress_called = []

        def progress_callback(current, total):
            progress_called.append((current, total))

        result = preprocess_video_qr(
            "/test/video.mp4",
            {'rois': [{'x': 0, 'y': 0, 'w': 100, 'h': 100}]},
            fps=5,
            progress_callback=progress_callback
        )

        assert isinstance(result, dict)

    def test_preprocess_video_qr_with_multiple_rois(self, mocker):
        """Test preprocess_video_qr with multiple ROIs"""
        from modules.technician.qr_detector import preprocess_video_qr

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        roi_config = {
            'rois': [
                {'x': 0, 'y': 0, 'w': 100, 'h': 100},
                {'x': 100, 'y': 100, 'w': 200, 'h': 200}
            ]
        }

        result = preprocess_video_qr("/test/video.mp4", roi_config, fps=5)

        assert isinstance(result, dict)


class TestDetectQRFromImage:
    """Tests for detect_qr_from_image() function"""

    def test_detect_qr_from_image_with_empty_string(self):
        """Test detect_qr_from_image with empty string"""
        from modules.technician.qr_detector import detect_qr_from_image

        result = detect_qr_from_image("")

        assert result['success'] is False
        assert 'error' in result

    def test_detect_qr_from_image_with_invalid_base64(self):
        """Test detect_qr_from_image with invalid base64 string"""
        from modules.technician.qr_detector import detect_qr_from_image

        result = detect_qr_from_image("invalid_base64_string")

        assert result['success'] is False
        assert 'error' in result

    def test_detect_qr_from_image_with_valid_format(self, mocker):
        """Test detect_qr_from_image with valid base64 format"""
        from modules.technician.qr_detector import detect_qr_from_image
        import base64

        # Create a small 1x1 black image as base64
        import numpy as np
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        _, buffer = mocker.MagicMock(return_value=(True, img.tobytes()))()

        # Mock cv2.imdecode to return empty array
        mocker.patch('cv2.imdecode', return_value=np.array([]))

        # Simple valid base64 string
        test_base64 = base64.b64encode(b"test").decode()

        result = detect_qr_from_image(test_base64)

        # Should handle the image even if QR detection fails
        assert isinstance(result, dict)
        assert 'success' in result


class TestSelectQRROIErrorHandling:
    """Tests for select_qr_roi() error handling"""

    def test_select_qr_roi_with_missing_model_files(self, mocker):
        """Test select_qr_roi with missing model files"""
        from modules.technician.qr_detector import select_qr_roi

        # Mock os.path.exists to return False for model files
        def mock_exists(path):
            if "wechat_qr" in path and path.endswith((".prototxt", ".caffemodel")):
                return False
            return True

        mocker.patch('os.path.exists', side_effect=mock_exists)

        result = select_qr_roi("/test/video.mp4", "cam1", "/test/roi_frame.jpg", "mvd")

        assert result['success'] is False
        assert 'Model file not found' in result['error']

    def test_select_qr_roi_with_missing_roi_frame(self, mocker):
        """Test select_qr_roi with missing ROI frame image"""
        from modules.technician.qr_detector import select_qr_roi

        # Mock os.path.exists to return False for roi_frame_path
        def mock_exists(path):
            if path == "/nonexistent/roi_frame.jpg":
                return False
            return True

        mocker.patch('os.path.exists', side_effect=mock_exists)

        result = select_qr_roi(
            "/test/video.mp4",
            "cam1",
            "/nonexistent/roi_frame.jpg",
            "mvd"
        )

        assert result['success'] is False
        assert 'Temporary image does not exist' in result['error']

    def test_select_qr_roi_with_missing_video(self, mocker):
        """Test select_qr_roi with missing video file"""
        from modules.technician.qr_detector import select_qr_roi

        # Mock os.path.exists
        def mock_exists(path):
            if path == "/nonexistent/video.mp4":
                return False
            return True

        mocker.patch('os.path.exists', side_effect=mock_exists)

        result = select_qr_roi(
            "/nonexistent/video.mp4",
            "cam1",
            "/test/roi_frame.jpg",
            "mvd"
        )

        assert result['success'] is False
        assert 'Video does not exist' in result['error']
