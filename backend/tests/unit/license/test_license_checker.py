"""
Unit tests for license_checker module
Tests license validation at app startup with offline support
"""
import pytest
from datetime import datetime, timedelta
from modules.license.license_checker import LicenseChecker


class TestLicenseCheckerInitialization:
    """Tests for LicenseChecker initialization"""

    def test_checker_initializes_successfully(self):
        """Test that LicenseChecker can be instantiated"""
        checker = LicenseChecker()
        assert checker is not None
        assert hasattr(checker, 'license_manager')

    def test_checker_has_license_manager(self):
        """Test that checker creates license manager instance"""
        checker = LicenseChecker()
        assert checker.license_manager is not None

    def test_checker_has_connection_cache(self):
        """Test that checker initializes connection cache"""
        checker = LicenseChecker()
        assert checker._connection_cache is not None
        assert 'online' in checker._connection_cache
        assert 'last_check' in checker._connection_cache


class TestStartupLicenseCheck:
    """Tests for startup_license_check() method"""

    def test_startup_check_with_valid_license_online(self, mocker):
        """Test startup check with valid license and internet"""
        mock_status = {
            'status': 'valid',
            'has_license': True,
            'license': {'license_key': 'TEST-KEY'}
        }

        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            return_value=mock_status)
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=True)

        result = checker.startup_license_check()

        assert result['action'] == 'continue'
        assert result['status'] == 'valid'
        assert result['network_status'] == 'online'

    def test_startup_check_with_no_license_online(self, mocker):
        """Test startup check with no license and internet"""
        mock_status = {
            'status': 'no_license',
            'has_license': False
        }

        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            return_value=mock_status)
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=True)

        result = checker.startup_license_check()

        assert result['action'] == 'show_license_input'
        assert result['status'] == 'no_license'
        assert 'Please enter license key' in result['message']

    def test_startup_check_with_no_license_offline(self, mocker):
        """Test startup check with no license and no internet"""
        mock_status = {
            'status': 'no_license',
            'has_license': False
        }

        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            return_value=mock_status)
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=False)

        result = checker.startup_license_check()

        assert result['action'] == 'show_license_input'
        assert 'Offline mode' in result['message']

    def test_startup_check_with_expired_license_within_grace(self, mocker):
        """Test startup check with expired license within grace period (offline)"""
        mock_status = {
            'status': 'invalid',
            'has_license': True,
            'reason': 'expired',
            'license': {
                'expires_at': (datetime.now() - timedelta(days=2)).isoformat()
            }
        }

        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            return_value=mock_status)
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=False)
        mocker.patch.object(checker, '_check_grace_period',
                            return_value={'in_grace': True, 'days_remaining': 5})

        result = checker.startup_license_check()

        assert result['action'] == 'show_grace_warning'
        assert result['status'] == 'expired_grace_period'
        assert '5 days remaining' in result['message']

    def test_startup_check_with_expired_license_beyond_grace(self, mocker):
        """Test startup check with expired license beyond grace period"""
        mock_status = {
            'status': 'invalid',
            'has_license': True,
            'reason': 'expired',
            'license': {
                'expires_at': (datetime.now() - timedelta(days=30)).isoformat()
            }
        }

        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            return_value=mock_status)
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=True)
        mocker.patch.object(checker, '_check_grace_period',
                            return_value={'in_grace': False, 'days_remaining': 0})

        result = checker.startup_license_check()

        assert result['action'] == 'show_expired_warning'
        assert result['status'] == 'expired'

    def test_startup_check_with_expiring_soon(self, mocker):
        """Test startup check with license expiring soon"""
        expiry_date = datetime.now() + timedelta(days=5)
        mock_status = {
            'status': 'valid',
            'has_license': True,
            'license': {
                'license_key': 'TEST-KEY',
                'expires_at': expiry_date.isoformat()
            }
        }

        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            return_value=mock_status)
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=True)
        mocker.patch.object(checker, '_check_expiry_warning',
                            return_value={
                                'warning': True,
                                'days_remaining': 5,
                                'message': 'License expires in 5 days'
                            })

        result = checker.startup_license_check()

        assert result['action'] == 'show_expiry_warning'
        assert result['status'] == 'valid_expiring'
        assert result['days_remaining'] == 5

    def test_startup_check_handles_exception_online(self, mocker):
        """Test startup check handles exceptions when online"""
        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            side_effect=Exception("Database error"))
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=True)

        result = checker.startup_license_check()

        assert result['action'] == 'show_error'
        assert result['status'] == 'error'

    def test_startup_check_handles_exception_offline(self, mocker):
        """Test startup check handles exceptions gracefully when offline"""
        checker = LicenseChecker()
        mocker.patch.object(checker.license_manager, 'get_license_status',
                            side_effect=Exception("Database error"))
        mocker.patch.object(checker, '_check_internet_connectivity',
                            return_value=False)

        result = checker.startup_license_check()

        assert result['action'] == 'continue_offline'
        assert result['status'] == 'offline_error'


class TestCheckInternetConnectivity:
    """Tests for _check_internet_connectivity() method"""

    def test_check_connectivity_returns_cached_result(self, mocker):
        """Test that connectivity check uses cached result"""
        checker = LicenseChecker()

        # Set cache
        checker._connection_cache = {
            'online': True,
            'last_check': datetime.now()
        }

        result = checker._check_internet_connectivity()

        # Should return cached result without calling tests
        assert result is True

    def test_check_connectivity_expired_cache(self, mocker):
        """Test that expired cache triggers new check"""
        checker = LicenseChecker()

        # Set old cache (>30 seconds ago)
        checker._connection_cache = {
            'online': True,
            'last_check': datetime.now() - timedelta(seconds=60)
        }

        # Mock test methods
        mocker.patch.object(checker, '_test_dns_resolution', return_value=True)

        result = checker._check_internet_connectivity()

        assert result is True
        # Cache should be updated
        assert (datetime.now() - checker._connection_cache['last_check']).seconds < 5

    def test_check_connectivity_all_tests_fail(self, mocker):
        """Test connectivity check when all tests fail"""
        checker = LicenseChecker()
        checker._connection_cache = {'online': None, 'last_check': None}

        # Mock all tests to fail
        mocker.patch.object(checker, '_test_dns_resolution', return_value=False)
        mocker.patch.object(checker, '_test_http_connection', return_value=False)
        mocker.patch.object(checker, '_test_socket_connection', return_value=False)

        result = checker._check_internet_connectivity()

        assert result is False

    def test_check_connectivity_dns_test_succeeds(self, mocker):
        """Test connectivity check when DNS test succeeds"""
        checker = LicenseChecker()
        checker._connection_cache = {'online': None, 'last_check': None}

        mocker.patch.object(checker, '_test_dns_resolution', return_value=True)

        result = checker._check_internet_connectivity()

        assert result is True

    def test_check_connectivity_http_test_succeeds(self, mocker):
        """Test connectivity check when HTTP test succeeds"""
        checker = LicenseChecker()
        checker._connection_cache = {'online': None, 'last_check': None}

        mocker.patch.object(checker, '_test_dns_resolution', return_value=False)
        mocker.patch.object(checker, '_test_http_connection', return_value=True)

        result = checker._check_internet_connectivity()

        assert result is True


class TestConnectivityTests:
    """Tests for individual connectivity test methods"""

    def test_dns_resolution_success(self, mocker):
        """Test DNS resolution when it succeeds"""
        mock_getaddrinfo = mocker.patch('socket.getaddrinfo')
        mock_getaddrinfo.return_value = [('family', 'type', 'proto', 'canonname', 'sockaddr')]

        checker = LicenseChecker()
        result = checker._test_dns_resolution()

        assert result is True
        mock_getaddrinfo.assert_called_once()

    def test_dns_resolution_failure(self, mocker):
        """Test DNS resolution when it fails"""
        import socket
        mock_getaddrinfo = mocker.patch('socket.getaddrinfo')
        mock_getaddrinfo.side_effect = socket.error("DNS failed")

        checker = LicenseChecker()
        result = checker._test_dns_resolution()

        assert result is False

    def test_http_connection_success(self, mocker):
        """Test HTTP connection when it succeeds"""
        mock_response = mocker.MagicMock()
        mock_response.status_code = 200

        mock_get = mocker.patch('requests.get', return_value=mock_response)

        checker = LicenseChecker()
        result = checker._test_http_connection()

        assert result is True

    def test_http_connection_failure(self, mocker):
        """Test HTTP connection when it fails"""
        import requests
        mock_get = mocker.patch('requests.get')
        mock_get.side_effect = requests.RequestException("Connection failed")

        checker = LicenseChecker()
        result = checker._test_http_connection()

        assert result is False

    def test_socket_connection_success(self, mocker):
        """Test socket connection when it succeeds"""
        mock_socket = mocker.MagicMock()
        mock_create = mocker.patch('socket.create_connection', return_value=mock_socket)

        checker = LicenseChecker()
        result = checker._test_socket_connection()

        assert result is True
        mock_socket.close.assert_called_once()

    def test_socket_connection_failure(self, mocker):
        """Test socket connection when it fails"""
        import socket
        mock_create = mocker.patch('socket.create_connection')
        mock_create.side_effect = socket.error("Socket failed")

        checker = LicenseChecker()
        result = checker._test_socket_connection()

        assert result is False


class TestCheckGracePeriod:
    """Tests for _check_grace_period() method"""

    def test_grace_period_within_limit(self):
        """Test grace period check when within 7 days"""
        checker = LicenseChecker()

        # License expired 3 days ago
        expiry = datetime.now() - timedelta(days=3)
        license_data = {'expires_at': expiry.isoformat()}

        result = checker._check_grace_period(license_data)

        assert result['in_grace'] is True
        assert result['days_remaining'] >= 3  # At least 3 days remaining

    def test_grace_period_expired(self):
        """Test grace period check when beyond 7 days"""
        checker = LicenseChecker()

        # License expired 10 days ago
        expiry = datetime.now() - timedelta(days=10)
        license_data = {'expires_at': expiry.isoformat()}

        result = checker._check_grace_period(license_data)

        assert result['in_grace'] is False
        assert result['days_remaining'] == 0

    def test_grace_period_no_license_data(self):
        """Test grace period check with no license data"""
        checker = LicenseChecker()

        result = checker._check_grace_period(None)

        assert result['in_grace'] is False
        assert result['days_remaining'] == 0

    def test_grace_period_no_expiry_date(self):
        """Test grace period check with no expiry date"""
        checker = LicenseChecker()

        license_data = {'license_key': 'TEST'}
        result = checker._check_grace_period(license_data)

        assert result['in_grace'] is False


class TestCanUseOfflineGrace:
    """Tests for _can_use_offline_grace() method"""

    def test_offline_grace_with_recent_validation(self):
        """Test offline grace allowed with recent validation"""
        checker = LicenseChecker()

        # License validated 2 days ago
        last_validation = datetime.now() - timedelta(days=2)
        status_result = {
            'license': {
                'last_validation': last_validation.isoformat()
            }
        }

        result = checker._can_use_offline_grace(status_result)

        assert result is True

    def test_offline_grace_with_old_validation(self):
        """Test offline grace denied with old validation"""
        checker = LicenseChecker()

        # License validated 10 days ago
        last_validation = datetime.now() - timedelta(days=10)
        status_result = {
            'license': {
                'last_validation': last_validation.isoformat()
            }
        }

        result = checker._can_use_offline_grace(status_result)

        assert result is False

    def test_offline_grace_with_recent_creation(self):
        """Test offline grace allowed for recently created license"""
        checker = LicenseChecker()

        # License created 3 days ago
        created_at = datetime.now() - timedelta(days=3)
        status_result = {
            'license': {
                'created_at': created_at.isoformat()
            }
        }

        result = checker._can_use_offline_grace(status_result)

        assert result is True

    def test_offline_grace_no_license_data(self):
        """Test offline grace denied with no license"""
        checker = LicenseChecker()

        status_result = {}
        result = checker._can_use_offline_grace(status_result)

        assert result is False


class TestAttemptCloudValidation:
    """Tests for _attempt_cloud_validation() method"""

    def test_cloud_validation_success(self, mocker):
        """Test successful cloud validation"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.return_value = {
            'success': True,
            'valid': True
        }

        # The actual code uses inline import, so patch both possible paths
        mock_get_client = mocker.patch(
            'modules.payments.cloud_function_client.get_cloud_client',
            return_value=mock_cloud
        )

        # Mock timestamp update
        mock_update = mocker.patch.object(
            LicenseChecker, '_update_cloud_validation_timestamp'
        )

        checker = LicenseChecker()
        result = checker._attempt_cloud_validation('TEST-KEY')

        assert result is True
        mock_cloud.validate_license.assert_called_once_with('TEST-KEY')
        mock_update.assert_called_once()

    def test_cloud_validation_failure(self, mocker):
        """Test failed cloud validation"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.return_value = {
            'success': False,
            'valid': False,
            'error': 'Invalid license'
        }

        mocker.patch(
            'modules.payments.cloud_function_client.get_cloud_client',
            return_value=mock_cloud
        )

        checker = LicenseChecker()
        result = checker._attempt_cloud_validation('INVALID-KEY')

        assert result is False

    def test_cloud_validation_exception(self, mocker):
        """Test cloud validation handles exceptions"""
        mock_cloud = mocker.MagicMock()
        mock_cloud.validate_license.side_effect = Exception("Network error")

        mocker.patch(
            'modules.payments.cloud_function_client.get_cloud_client',
            return_value=mock_cloud
        )

        checker = LicenseChecker()
        result = checker._attempt_cloud_validation('TEST-KEY')

        assert result is False


class TestGetConnectivityStatus:
    """Tests for get_connectivity_status() method"""

    def test_get_connectivity_status_online(self, mocker):
        """Test getting connectivity status when online"""
        checker = LicenseChecker()
        mocker.patch.object(checker, '_check_internet_connectivity', return_value=True)

        status = checker.get_connectivity_status()

        assert status['online'] is True
        assert 'last_check' in status
        assert 'cache_age_seconds' in status

    def test_get_connectivity_status_offline(self, mocker):
        """Test getting connectivity status when offline"""
        checker = LicenseChecker()
        mocker.patch.object(checker, '_check_internet_connectivity', return_value=False)

        status = checker.get_connectivity_status()

        assert status['online'] is False

    def test_get_connectivity_status_handles_exception(self, mocker):
        """Test that get_connectivity_status handles exceptions"""
        checker = LicenseChecker()
        mocker.patch.object(checker, '_check_internet_connectivity',
                            side_effect=Exception("Error"))

        status = checker.get_connectivity_status()

        assert status['online'] is False
        assert 'error' in status


class TestForceOnlineValidation:
    """Tests for force_online_validation() method"""

    def test_force_validation_success(self, mocker):
        """Test forcing online validation successfully"""
        checker = LicenseChecker()
        mocker.patch.object(checker, '_check_internet_connectivity', return_value=True)
        mocker.patch.object(checker, '_attempt_cloud_validation', return_value=True)

        result = checker.force_online_validation('TEST-KEY')

        assert result['success'] is True
        assert result['validated'] is True
        assert result['network_status'] == 'online'

    def test_force_validation_offline(self, mocker):
        """Test forcing validation when offline"""
        checker = LicenseChecker()
        mocker.patch.object(checker, '_check_internet_connectivity', return_value=False)

        result = checker.force_online_validation('TEST-KEY')

        assert result['success'] is False
        assert result['network_status'] == 'offline'

    def test_force_validation_cloud_failed(self, mocker):
        """Test forcing validation when cloud validation fails"""
        checker = LicenseChecker()
        mocker.patch.object(checker, '_check_internet_connectivity', return_value=True)
        mocker.patch.object(checker, '_attempt_cloud_validation', return_value=False)

        result = checker.force_online_validation('TEST-KEY')

        assert result['success'] is True
        assert result['validated'] is False

    def test_force_validation_handles_exception(self, mocker):
        """Test that force validation handles exceptions"""
        checker = LicenseChecker()
        mocker.patch.object(checker, '_check_internet_connectivity',
                            side_effect=Exception("Network error"))

        result = checker.force_online_validation('TEST-KEY')

        assert result['success'] is False
        assert 'error' in result
