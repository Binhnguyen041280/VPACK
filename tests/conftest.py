"""Pytest configuration and shared fixtures for VPACK tests."""

import os
import sys
import pytest
import tempfile
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def temp_dir():
    """Create and return a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def mock_database(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test_vtrack.db"
    return str(db_path)


@pytest.fixture(scope="function")
def flask_app():
    """Create and configure a Flask app instance for testing."""
    # Import here to avoid circular imports
    import sys
    import os

    # Set test environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'

    # Disable logging during tests
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    os.environ['PYTHONWARNINGS'] = 'ignore'

    # Import app after setting env vars
    from app import app

    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    yield app


@pytest.fixture(scope="function")
def client(flask_app):
    """Create a test client for the Flask app."""
    return flask_app.test_client()


@pytest.fixture(scope="function")
def runner(flask_app):
    """Create a test CLI runner for the Flask app."""
    return flask_app.test_cli_runner()


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables after each test."""
    old_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def sample_video_path(test_data_dir):
    """Return path to a sample video file (if exists)."""
    video_path = test_data_dir / "sample_video.mp4"
    if video_path.exists():
        return str(video_path)
    return None


@pytest.fixture
def sample_qr_image(test_data_dir):
    """Return path to a sample QR code image (if exists)."""
    qr_path = test_data_dir / "sample_qr.png"
    if qr_path.exists():
        return str(qr_path)
    return None
