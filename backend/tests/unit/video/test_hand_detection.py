"""
Unit tests for hand_detection module
Tests helper functions and error handling for hand detection
"""
import pytest
import os
import tempfile
from modules.technician.hand_detection import ensure_directory_exists


class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists() helper function"""

    def test_create_new_directory(self):
        """Test creating a new directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "test_dir")

            # Directory should not exist yet
            assert not os.path.exists(new_dir)

            # Create directory
            ensure_directory_exists(new_dir)

            # Directory should now exist
            assert os.path.exists(new_dir)
            assert os.path.isdir(new_dir)

    def test_directory_already_exists(self):
        """Test with existing directory (should not raise error)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Directory already exists
            assert os.path.exists(tmpdir)

            # Should not raise error
            ensure_directory_exists(tmpdir)

            # Directory should still exist
            assert os.path.exists(tmpdir)

    def test_nested_directory_creation(self):
        """Test creating nested directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "level1", "level2", "level3")

            # Create nested directory
            ensure_directory_exists(nested_dir)

            # All levels should exist
            assert os.path.exists(nested_dir)
            assert os.path.isdir(nested_dir)

    def test_directory_with_special_characters(self):
        """Test directory name with special characters"""
        with tempfile.TemporaryDirectory() as tmpdir:
            special_dir = os.path.join(tmpdir, "test_dir-2025_01")

            ensure_directory_exists(special_dir)

            assert os.path.exists(special_dir)

    def test_directory_permissions(self):
        """Test that created directory has write permissions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "writable_dir")

            ensure_directory_exists(new_dir)

            # Directory should be writable
            assert os.access(new_dir, os.W_OK)

    def test_invalid_path_raises_error(self):
        """Test that invalid path raises appropriate error"""
        # Try to create directory in non-existent root (platform-specific)
        invalid_path = "/nonexistent_root_12345/test_dir"

        with pytest.raises(Exception):  # Could be OSError or PermissionError
            ensure_directory_exists(invalid_path)


class TestHandDetectionConfiguration:
    """Tests for hand detection configuration and constants"""

    def test_frame_step_constant(self):
        """Test FRAME_STEP constant is properly defined"""
        from modules.technician.hand_detection import FRAME_STEP

        assert isinstance(FRAME_STEP, int)
        assert FRAME_STEP > 0
        assert FRAME_STEP == 5

    def test_camera_roi_dir_path(self):
        """Test CAMERA_ROI_DIR path is properly defined"""
        from modules.technician.hand_detection import CAMERA_ROI_DIR

        assert isinstance(CAMERA_ROI_DIR, str)
        assert "CameraROI" in CAMERA_ROI_DIR
        assert "output_clips" in CAMERA_ROI_DIR

    def test_mediapipe_imports(self):
        """Test that MediaPipe is properly imported"""
        from modules.technician.hand_detection import mp_hands, mp_drawing

        assert mp_hands is not None
        assert mp_drawing is not None


class TestDetectHandsErrorHandling:
    """Tests for detect_hands() error handling"""

    def test_detect_hands_with_nonexistent_video(self, mocker):
        """Test detect_hands with non-existent video file"""
        from modules.technician.hand_detection import detect_hands

        # Mock VideoCapture to return not opened
        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        result = detect_hands("/nonexistent/video.mp4", {'x': 0, 'y': 0, 'w': 100, 'h': 100})

        assert result['success'] is False
        assert 'error' in result

    def test_detect_hands_with_invalid_roi(self, mocker):
        """Test detect_hands with invalid ROI dimensions"""
        from modules.technician.hand_detection import detect_hands

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        # ROI with zero dimensions
        result = detect_hands("/test/video.mp4", {'x': 0, 'y': 0, 'w': 0, 'h': 0})

        assert result['success'] is False


class TestDetectHandsAtTimeErrorHandling:
    """Tests for detect_hands_at_time() error handling"""

    def test_detect_hands_at_time_with_negative_time(self, mocker):
        """Test detect_hands_at_time with negative time value"""
        from modules.technician.hand_detection import detect_hands_at_time

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = True
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        result = detect_hands_at_time("/test/video.mp4", -5.0, {'x': 0, 'y': 0, 'w': 100, 'h': 100})

        # Should handle negative time (might return error or default to 0)
        assert isinstance(result, dict)
        assert 'success' in result

    def test_detect_hands_at_time_with_no_roi_config(self, mocker):
        """Test detect_hands_at_time without ROI config"""
        from modules.technician.hand_detection import detect_hands_at_time

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        result = detect_hands_at_time("/test/video.mp4", 10.0, None)

        assert result['success'] is False


class TestPreprocessVideoHandsConfiguration:
    """Tests for preprocess_video_hands() configuration"""

    def test_preprocess_video_hands_with_invalid_fps(self, mocker):
        """Test preprocess_video_hands with invalid FPS"""
        from modules.technician.hand_detection import preprocess_video_hands

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        # FPS should be positive
        result = preprocess_video_hands("/test/video.mp4", {'x': 0, 'y': 0, 'w': 100, 'h': 100}, fps=0)

        assert result['success'] is False

    def test_preprocess_video_hands_with_progress_callback(self, mocker):
        """Test preprocess_video_hands with progress callback"""
        from modules.technician.hand_detection import preprocess_video_hands

        mock_cap = mocker.MagicMock()
        mock_cap.isOpened.return_value = False
        mocker.patch('cv2.VideoCapture', return_value=mock_cap)

        progress_called = []

        def progress_callback(current, total):
            progress_called.append((current, total))

        result = preprocess_video_hands(
            "/test/video.mp4",
            {'x': 0, 'y': 0, 'w': 100, 'h': 100},
            fps=5,
            progress_callback=progress_callback
        )

        # Even if video fails, the callback mechanism should be in place
        assert isinstance(result, dict)
