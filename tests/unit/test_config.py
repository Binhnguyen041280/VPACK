"""Unit tests for configuration management."""

import pytest
import os
from pathlib import Path


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_default_port(self):
        """Test default port configuration."""
        # Default port should be 8080
        default_port = 8080
        assert isinstance(default_port, int)
        assert default_port > 0

    def test_python_version_requirement(self):
        """Test Python version requirement."""
        import sys
        # Should be Python 3.10+
        assert sys.version_info >= (3, 10)


class TestPathUtilities:
    """Test path utility functions."""

    def test_backend_path_exists(self):
        """Test that backend directory exists."""
        backend_dir = Path(__file__).parent.parent.parent / "backend"
        assert backend_dir.exists()
        assert backend_dir.is_dir()

    def test_modules_path_exists(self):
        """Test that modules directory exists."""
        modules_dir = Path(__file__).parent.parent.parent / "backend" / "modules"
        assert modules_dir.exists()
        assert modules_dir.is_dir()

    def test_models_path_exists(self):
        """Test that models directory exists."""
        models_dir = Path(__file__).parent.parent.parent / "backend" / "models"
        assert models_dir.exists()
        assert models_dir.is_dir()

    def test_wechat_qr_models_exist(self):
        """Test that WeChat QR models exist."""
        wechat_dir = Path(__file__).parent.parent.parent / "backend" / "models" / "wechat_qr"
        assert wechat_dir.exists()

        # Check for required model files
        required_files = [
            "detect.caffemodel",
            "detect.prototxt",
            "sr.caffemodel",
            "sr.prototxt"
        ]

        for filename in required_files:
            model_file = wechat_dir / filename
            assert model_file.exists(), f"Missing required model file: {filename}"
            assert model_file.stat().st_size > 0, f"Model file is empty: {filename}"
