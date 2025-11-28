"""
Unit tests for license_manager module
Tests core license management operations with repository pattern
"""
import pytest
from datetime import datetime, timedelta
from modules.license.license_manager import LicenseManager


class TestLicenseManagerInitialization:
    """Tests for LicenseManager initialization"""

    def test_manager_initializes_successfully(self):
        """Test that LicenseManager can be instantiated"""
        manager = LicenseManager()
        assert manager is not None
        assert hasattr(manager, 'machine_fingerprint')

    def test_manager_has_machine_fingerprint(self):
        """Test that manager generates machine fingerprint on init"""
        manager = LicenseManager()
        assert manager.machine_fingerprint is not None
        assert isinstance(manager.machine_fingerprint, str)
        assert len(manager.machine_fingerprint) > 0

    def test_manager_lazy_loads_repository(self):
        """Test that repository is lazy-loaded"""
        manager = LicenseManager()
        # Repository should be None initially
        assert manager._repository is None

    def test_manager_lazy_loads_cloud_client(self):
        """Test that cloud client is lazy-loaded"""
        manager = LicenseManager()
        # Cloud client should be None initially
        assert manager._cloud_client is None


class TestGetLocalLicense:
    """Tests for get_local_license() method"""

    def test_get_local_license_with_valid_repository(self, mocker):
        """Test getting license when repository is available"""
        # Mock repository
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.return_value = {
            'license_key': 'TEST-KEY-123',
            'status': 'active',
            'expires_at': '2026-12-31T23:59:59',
            'features': ['full_access']
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        result = manager.get_local_license()

        assert result is not None
        assert result['license_key'] == 'TEST-KEY-123'
        assert result['status'] == 'active'
        mock_repo.get_active_license.assert_called_once()

    def test_get_local_license_when_no_license_exists(self, mocker):
        """Test getting license when none exists in database"""
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.return_value = None

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        result = manager.get_local_license()

        assert result is None
        mock_repo.get_active_license.assert_called_once()

    def test_get_local_license_without_repository(self, mocker):
        """Test getting license when repository is unavailable"""
        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=None)

        result = manager.get_local_license()

        assert result is None

    def test_get_local_license_handles_exception(self, mocker):
        """Test that get_local_license handles repository exceptions"""
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.side_effect = Exception("Database error")

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        result = manager.get_local_license()

        assert result is None


class TestIsLicenseValid:
    """Tests for is_license_valid() method"""

    def test_is_license_valid_with_active_license(self, mocker):
        """Test validation of active, non-expired license"""
        mock_repo = mocker.MagicMock()
        mock_repo.check_license_expiry.return_value = {
            'expired': False,
            'days_remaining': 365
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        license_data = {
            'license_key': 'TEST-KEY',
            'status': 'active',
            'expires_at': '2026-12-31T23:59:59'
        }

        result = manager.is_license_valid(license_data)

        assert result['valid'] is True
        assert 'license' in result

    def test_is_license_valid_with_expired_license(self, mocker):
        """Test validation of expired license"""
        mock_repo = mocker.MagicMock()
        mock_repo.check_license_expiry.return_value = {
            'expired': True,
            'days_expired': 10
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        license_data = {
            'license_key': 'TEST-KEY',
            'status': 'active',
            'expires_at': '2024-01-01T00:00:00'
        }

        result = manager.is_license_valid(license_data)

        assert result['valid'] is False
        assert result['reason'] == 'expired'
        assert 'days_expired' in result

    def test_is_license_valid_with_inactive_status(self, mocker):
        """Test validation of license with inactive status"""
        manager = LicenseManager()

        license_data = {
            'license_key': 'TEST-KEY',
            'status': 'suspended',
            'expires_at': '2026-12-31T23:59:59'
        }

        result = manager.is_license_valid(license_data)

        assert result['valid'] is False
        assert result['reason'] == 'status_suspended'

    def test_is_license_valid_with_no_data(self):
        """Test validation when no license data provided"""
        manager = LicenseManager()

        result = manager.is_license_valid(None)

        assert result['valid'] is False
        assert result['reason'] == 'no_license_data'

    def test_is_license_valid_without_repository(self, mocker):
        """Test validation fallback when repository unavailable"""
        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=None)

        license_data = {
            'license_key': 'TEST-KEY',
            'status': 'active',
            'expires_at': '2026-12-31T23:59:59'
        }

        result = manager.is_license_valid(license_data)

        # Should still pass with fallback validation
        assert result['valid'] is True


class TestValidateWithCloud:
    """Tests for validate_with_cloud() method"""

    def test_validate_with_cloud_success(self, mocker):
        """Test successful cloud validation"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.return_value = {
            'success': True,
            'valid': True,
            'data': {'customer_email': 'test@example.com'}
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)

        result = manager.validate_with_cloud('TEST-LICENSE-KEY')

        assert result['success'] is True
        assert result['valid'] is True
        mock_cloud.validate_license.assert_called_once_with('TEST-LICENSE-KEY')

    def test_validate_with_cloud_invalid_license(self, mocker):
        """Test cloud validation with invalid license"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.return_value = {
            'success': True,
            'valid': False,
            'error': 'License not found'
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)

        result = manager.validate_with_cloud('INVALID-KEY')

        assert result['success'] is True
        assert result['valid'] is False

    def test_validate_with_cloud_unavailable(self, mocker):
        """Test cloud validation when cloud is unavailable"""
        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=None)

        result = manager.validate_with_cloud('TEST-KEY')

        assert result['success'] is False
        assert result['error'] == 'cloud_unavailable'

    def test_validate_with_cloud_exception(self, mocker):
        """Test cloud validation handles exceptions"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.side_effect = Exception("Network error")

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)

        result = manager.validate_with_cloud('TEST-KEY')

        assert result['success'] is False
        assert result['error'] == 'cloud_unavailable'


class TestActivateLicense:
    """Tests for activate_license() method"""

    def test_activate_license_success(self, mocker):
        """Test successful license activation"""
        # Mock cloud validation
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.return_value = {
            'valid': True,
            'data': {
                'customer_email': 'test@example.com',
                'product_type': 'desktop',
                'features': ['full_access']
            }
        }

        # Mock repository
        mock_repo = mocker.MagicMock()
        mock_repo.create_license.return_value = 123  # license_id

        # Mock activation record creation
        mock_create_activation = mocker.patch.object(
            LicenseManager, '_create_activation_record'
        )

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        result = manager.activate_license('TEST-LICENSE-KEY')

        assert result['success'] is True
        assert result['license_id'] == 123
        assert 'machine_fingerprint' in result
        mock_create_activation.assert_called_once()

    def test_activate_license_invalid_key(self, mocker):
        """Test activation with invalid license key"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.return_value = {
            'valid': False,
            'error': 'Invalid key'
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)

        result = manager.activate_license('INVALID-KEY')

        assert result['success'] is False
        assert 'error' in result

    def test_activate_license_no_repository(self, mocker):
        """Test activation fails when repository unavailable"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.return_value = {
            'valid': True,
            'data': {}
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)
        mocker.patch.object(manager, '_get_repository', return_value=None)

        result = manager.activate_license('TEST-KEY')

        assert result['success'] is False
        assert result['error'] == 'Repository unavailable'

    def test_activate_license_handles_exception(self, mocker):
        """Test that activation handles exceptions gracefully"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.side_effect = Exception("Network timeout")

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)

        result = manager.activate_license('TEST-KEY')

        assert result['success'] is False
        assert 'error' in result


class TestCheckTableExists:
    """Tests for _check_table_exists() method"""

    def test_check_table_exists_success(self, mocker):
        """Test table existence check when table exists"""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = ('licenses',)

        mock_conn = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = mocker.Mock(return_value=mock_conn)
        mock_conn.__exit__ = mocker.Mock(return_value=False)

        mocker.patch('modules.license.license_manager.safe_db_connection',
                     return_value=mock_conn)

        manager = LicenseManager()
        result = manager._check_table_exists('licenses')

        assert result is True

    def test_check_table_exists_missing_table(self, mocker):
        """Test table existence check when table doesn't exist"""
        mock_cursor = mocker.MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = mocker.Mock(return_value=mock_conn)
        mock_conn.__exit__ = mocker.Mock(return_value=False)

        mocker.patch('modules.license.license_manager.safe_db_connection',
                     return_value=mock_conn)

        manager = LicenseManager()
        result = manager._check_table_exists('licenses')

        assert result is False

    def test_check_table_exists_handles_exception(self, mocker):
        """Test table check handles database exceptions"""
        mock_conn = mocker.MagicMock()
        mock_conn.__enter__ = mocker.Mock(side_effect=Exception("DB error"))
        mock_conn.__exit__ = mocker.Mock(return_value=False)

        mocker.patch('modules.license.license_manager.safe_db_connection',
                     return_value=mock_conn)

        manager = LicenseManager()
        result = manager._check_table_exists('licenses')

        assert result is False


class TestGetLicenseStatus:
    """Tests for get_license_status() method"""

    def test_get_license_status_valid_license(self, mocker):
        """Test getting status for valid license"""
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.return_value = {
            'license_key': 'TEST-KEY',
            'status': 'active',
            'expires_at': '2026-12-31T23:59:59',
            'features': ['full_access']
        }
        mock_repo.check_license_expiry.return_value = {
            'expired': False,
            'days_remaining': 365
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)
        mocker.patch.object(manager, '_check_table_exists', return_value=True)

        result = manager.get_license_status()

        assert result['status'] == 'valid'
        assert result['has_license'] is True
        assert 'license' in result
        assert 'machine_fingerprint' in result

    def test_get_license_status_no_license(self, mocker):
        """Test getting status when no license exists"""
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.return_value = None

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)
        mocker.patch.object(manager, '_check_table_exists', return_value=True)

        result = manager.get_license_status()

        assert result['status'] == 'no_license'
        assert result['has_license'] is False

    def test_get_license_status_table_missing(self, mocker):
        """Test getting status when licenses table is missing (security check)"""
        manager = LicenseManager()
        mocker.patch.object(manager, '_check_table_exists', return_value=False)

        result = manager.get_license_status()

        assert result['status'] == 'no_license'
        assert result['reason'] == 'table_missing'
        assert 'database is unavailable' in result['message'].lower()

    def test_get_license_status_invalid_license(self, mocker):
        """Test getting status for invalid/expired license"""
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.return_value = {
            'license_key': 'TEST-KEY',
            'status': 'active',
            'expires_at': '2024-01-01T00:00:00'
        }
        mock_repo.check_license_expiry.return_value = {
            'expired': True,
            'days_expired': 30
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)
        mocker.patch.object(manager, '_check_table_exists', return_value=True)

        result = manager.get_license_status()

        assert result['status'] == 'invalid'
        assert result['has_license'] is True
        assert result['reason'] == 'expired'

    def test_get_license_status_handles_exception(self, mocker):
        """Test that get_license_status handles exceptions"""
        manager = LicenseManager()
        mocker.patch.object(manager, '_check_table_exists',
                            side_effect=Exception("Database crash"))

        result = manager.get_license_status()

        assert result['status'] == 'error'
        assert result['has_license'] is False
        assert 'error' in result


class TestGetLicenseFeatures:
    """Tests for get_license_features() method"""

    def test_get_license_features_with_data(self, mocker):
        """Test getting features from license data"""
        manager = LicenseManager()

        license_data = {
            'license_key': 'TEST-KEY',
            'features': ['custom_mode', 'advanced_analytics', 'export']
        }

        features = manager.get_license_features(license_data)

        assert isinstance(features, list)
        assert 'custom_mode' in features
        assert 'advanced_analytics' in features

    def test_get_license_features_without_data(self, mocker):
        """Test getting features when no license data provided"""
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.return_value = {
            'features': ['full_access']
        }

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        features = manager.get_license_features()

        assert isinstance(features, list)
        assert 'full_access' in features

    def test_get_license_features_no_license(self, mocker):
        """Test getting features when no license exists"""
        mock_repo = mocker.MagicMock()
        mock_repo.get_active_license.return_value = None

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)

        features = manager.get_license_features()

        assert isinstance(features, list)
        assert 'basic_access' in features  # Default fallback

    def test_get_license_features_handles_exception(self, mocker):
        """Test that get_license_features handles exceptions"""
        manager = LicenseManager()
        mocker.patch.object(manager, 'get_local_license',
                            side_effect=Exception("Database error"))

        features = manager.get_license_features()

        assert isinstance(features, list)
        assert 'basic_access' in features  # Fallback


class TestGetMachineInfo:
    """Tests for get_machine_info() debugging method"""

    def test_get_machine_info_success(self, mocker):
        """Test getting machine information"""
        mock_repo = mocker.MagicMock()
        mock_cloud = mocker.MagicMock()

        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=mock_repo)
        mocker.patch.object(manager, '_get_cloud_client', return_value=mock_cloud)

        info = manager.get_machine_info()

        assert isinstance(info, dict)
        assert 'machine_fingerprint' in info
        assert 'fingerprint_short' in info
        assert 'repository_available' in info
        assert 'cloud_client_available' in info
        assert 'timestamp' in info

    def test_get_machine_info_with_unavailable_services(self, mocker):
        """Test getting machine info when services unavailable"""
        manager = LicenseManager()
        mocker.patch.object(manager, '_get_repository', return_value=None)
        mocker.patch.object(manager, '_get_cloud_client', return_value=None)

        info = manager.get_machine_info()

        assert info['repository_available'] is False
        assert info['cloud_client_available'] is False

    def test_get_machine_info_handles_exception(self, mocker):
        """Test that get_machine_info handles exceptions"""
        manager = LicenseManager()
        # Mock fingerprint to raise exception
        manager.machine_fingerprint = None

        info = manager.get_machine_info()

        assert isinstance(info, dict)
        assert info['machine_fingerprint'] == 'unknown'
        assert 'error' in info
