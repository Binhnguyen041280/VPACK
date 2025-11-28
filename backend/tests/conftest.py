"""
Pytest Configuration and Shared Fixtures

This module provides shared fixtures and configuration for all tests.
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# ============================================================================
# Application Fixtures
# ============================================================================

@pytest.fixture
def app():
    """
    Create Flask app instance for testing.

    Creates a temporary database and configures app for testing mode.
    """
    from flask import Flask
    from modules.payments.payment_routes import payment_bp

    # Create temporary directories for database and session
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    session_dir = tempfile.mkdtemp()

    # Create minimal Flask app for testing
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': session_dir,
    })

    # Register payment blueprint
    app.register_blueprint(payment_bp)

    yield app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

    # Cleanup session directory
    import shutil
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)


@pytest.fixture
def client(app):
    """
    Flask test client.

    Provides a test client for making HTTP requests to Flask app.
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Flask CLI test runner.

    Provides a test runner for Flask CLI commands.
    """
    return app.test_cli_runner()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def db_session(app):
    """
    Database session for testing.

    Provides a database session that rolls back after each test.
    """
    from database import get_db

    with app.app_context():
        db = get_db()
        yield db
        db.rollback()


@pytest.fixture
def clean_db(app):
    """
    Clean database state.

    Ensures database is empty before each test.
    """
    from database import get_db, init_db

    with app.app_context():
        init_db()
        db = get_db()

        # Clear all tables
        db.execute("DELETE FROM licenses")
        db.execute("DELETE FROM activations")
        db.execute("DELETE FROM events")
        db.commit()

        yield db


# ============================================================================
# License Fixtures
# ============================================================================

@pytest.fixture
def sample_license_key():
    """Sample valid license key for testing."""
    return "EPACK-ANNUAL-1Y-ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX234YZ"


@pytest.fixture
def sample_expired_license_key():
    """Sample expired license key for testing."""
    return "EPACK-TRIAL-30D-EXPIRED123EXPIRED456EXPIRED789EXPIRED012EXPIRED"


@pytest.fixture
def sample_machine_fingerprint():
    """Sample machine fingerprint for testing."""
    return "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"


@pytest.fixture
def sample_license_data():
    """Sample license data dictionary."""
    return {
        'license_key': 'EPACK-ANNUAL-1Y-ABC123DEF456GHI789',
        'package_type': 'annual_1y',
        'status': 'active',
        'created_at': '2025-01-01T00:00:00Z',
        'expires_at': '2026-01-01T00:00:00Z',
        'features': {
            'default_mode': True,
            'custom_mode': True,
            'max_cameras': 10
        }
    }


# ============================================================================
# Payment Fixtures
# ============================================================================

@pytest.fixture
def sample_payment_request():
    """Sample payment request data."""
    return {
        'customer_email': 'test@example.com',
        'package_type': 'annual_1y',
        'callback_url': 'https://epack.local/success'
    }


@pytest.fixture
def sample_payment_response():
    """Sample payment response from CloudFunction."""
    return {
        'success': True,
        'order_url': 'https://payos.vn/order/123456',
        'order_code': 123456,
        'amount': 2000000,
        'formatted_amount': '2.000.000đ'
    }


@pytest.fixture
def sample_packages():
    """Sample pricing packages."""
    return [
        {
            'id': 'trial_30d',
            'name': 'Trial 30 Days',
            'price': 0,
            'duration': 30,
            'features': {'default_mode': True, 'custom_mode': False, 'max_cameras': 3}
        },
        {
            'id': 'basic_1m',
            'name': 'Basic Monthly',
            'price': 500000,
            'duration': 30,
            'features': {'default_mode': True, 'custom_mode': True, 'max_cameras': 5}
        },
        {
            'id': 'annual_1y',
            'name': 'Annual Package',
            'price': 2000000,
            'duration': 365,
            'features': {'default_mode': True, 'custom_mode': True, 'max_cameras': 10}
        }
    ]


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_cloud_client(mocker):
    """
    Mock CloudFunctionClient.

    Mocks all CloudFunction API calls for offline testing.
    """
    mock = mocker.Mock()
    mock.check_activation.return_value = {
        'success': True,
        'can_activate': True,
        'message': 'License can be activated'
    }
    mock.record_activation.return_value = {
        'success': True,
        'activation_id': 'act_123456'
    }
    mock.deactivate.return_value = {
        'success': True
    }
    return mock


@pytest.fixture
def mock_video_capture(mocker):
    """
    Mock cv2.VideoCapture for video processing tests.

    Provides a mock video capture object with sample frames.
    """
    import numpy as np

    mock = mocker.Mock()
    mock.isOpened.return_value = True
    mock.get.return_value = 30.0  # FPS

    # Mock frame (640x480 RGB)
    sample_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock.read.return_value = (True, sample_frame)

    return mock


@pytest.fixture
def mock_mediapipe_hands(mocker):
    """
    Mock MediaPipe Hands for hand detection tests.

    Provides mock hand landmarks.
    """
    mock = mocker.Mock()
    mock.process.return_value.multi_hand_landmarks = []
    return mock


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def test_env(monkeypatch):
    """
    Set test environment variables.

    Configures environment for testing mode.
    """
    monkeypatch.setenv('FLASK_ENV', 'testing')
    monkeypatch.setenv('EPACK_IN_DOCKER', 'false')
    monkeypatch.setenv('DATABASE_URL', ':memory:')


@pytest.fixture
def offline_mode(monkeypatch, mocker):
    """
    Simulate offline mode.

    Disables network connectivity for testing offline scenarios.
    """
    import socket

    def mock_socket_error(*args, **kwargs):
        raise socket.error("Network unreachable")

    mocker.patch('socket.create_connection', side_effect=mock_socket_error)
    mocker.patch('requests.get', side_effect=ConnectionError("No internet"))
    mocker.patch('requests.post', side_effect=ConnectionError("No internet"))


# ============================================================================
# Time Fixtures
# ============================================================================

@pytest.fixture
def freeze_time():
    """
    Freeze time for testing time-dependent logic.

    Requires freezegun library.
    """
    from freezegun import freeze_time as _freeze_time
    return _freeze_time


# ============================================================================
# Cleanup Hooks
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Reset singleton instances between tests.

    Ensures clean state for each test.
    """
    yield
    # Add singleton reset logic here if needed


def pytest_configure(config):
    """
    Pytest configuration hook.

    Runs once before all tests.
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "unit: Unit tests (isolate single function/class)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (multi-module)"
    )
    config.addinivalue_line(
        "markers", "api: API endpoint tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests"
    )
    config.addinivalue_line(
        "markers", "requires_internet: Tests requiring network"
    )
    config.addinivalue_line(
        "markers", "requires_cloud: Tests requiring CloudFunction"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test items during collection.

    Automatically skip tests based on markers and environment.
    """
    skip_slow = pytest.mark.skip(reason="Use --runslow to run slow tests")
    skip_internet = pytest.mark.skip(reason="Use --runinternet to run internet tests")

    for item in items:
        if "slow" in item.keywords and not config.getoption("--runslow", default=False):
            item.add_marker(skip_slow)
        if "requires_internet" in item.keywords and not config.getoption("--runinternet", default=False):
            item.add_marker(skip_internet)


def pytest_addoption(parser):
    """
    Add custom command-line options.
    """
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--runinternet",
        action="store_true",
        default=False,
        help="Run tests requiring internet"
    )
