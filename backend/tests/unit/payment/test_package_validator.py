"""
Unit tests for package_validator module
Tests package validation using CloudFunction as single source of truth
"""
import pytest
from modules.payments.package_validator import PackageValidator, get_package_validator


class TestPackageValidatorInitialization:
    """Tests for PackageValidator initialization"""

    def test_package_validator_initialization(self, mocker):
        """Test that PackageValidator initializes correctly"""
        mock_pricing_client = mocker.MagicMock()
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()

        assert validator.pricing_client is not None
        assert validator._package_cache is None
        assert validator._cache_timestamp is None

    def test_get_package_validator_singleton(self, mocker):
        """Test that get_package_validator returns singleton"""
        mock_pricing_client = mocker.MagicMock()
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        # Reset singleton for test
        import modules.payments.package_validator as pv_module
        pv_module._package_validator = None

        validator1 = get_package_validator()
        validator2 = get_package_validator()

        assert validator1 is validator2


class TestValidatePackageType:
    """Tests for validate_package_type() method"""

    def test_validate_package_type_valid(self, mocker):
        """Test validation with valid package type"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {
                'starter_1m': {
                    'name': 'Starter Monthly',
                    'price': 9.99
                },
                'pro_1m': {
                    'name': 'Pro Monthly',
                    'price': 19.99
                }
            }
        }
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()
        result = validator.validate_package_type('starter_1m')

        assert result['valid'] is True
        assert 'package_info' in result
        assert result['package_info']['name'] == 'Starter Monthly'
        assert 'starter_1m' in result['available_packages']

    def test_validate_package_type_invalid(self, mocker):
        """Test validation with invalid package type"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {
                'starter_1m': {'name': 'Starter'},
                'pro_1m': {'name': 'Pro'}
            }
        }
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()
        result = validator.validate_package_type('invalid_package')

        assert result['valid'] is False
        assert 'Invalid package type' in result['error']
        assert 'available_packages' in result

    def test_validate_package_type_pricing_service_unavailable(self, mocker):
        """Test validation when pricing service is unavailable"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': False,
            'error': 'Service unavailable'
        }
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()
        result = validator.validate_package_type('starter_1m')

        assert result['valid'] is False
        assert 'pricing service unavailable' in result['error']
        assert result['available_packages'] == []

    def test_validate_package_type_exception_handling(self, mocker):
        """Test validation handles exceptions gracefully"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.side_effect = Exception("Network error")
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()
        result = validator.validate_package_type('starter_1m')

        assert result['valid'] is False
        # The code returns "Cannot validate package" on exception from _get_available_packages
        assert ('Cannot validate package' in result['error'] or
                'Package validation failed' in result['error'])


class TestGetAvailablePackages:
    """Tests for _get_available_packages() method"""

    def test_get_available_packages_success(self, mocker):
        """Test successful package retrieval"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {
                'starter_1m': {'name': 'Starter'},
                'pro_1m': {'name': 'Pro'}
            }
        }
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()
        packages = validator._get_available_packages()

        assert len(packages) == 2
        assert 'starter_1m' in packages
        assert 'pro_1m' in packages

    def test_get_available_packages_failure(self, mocker):
        """Test package retrieval returns empty dict on failure"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': False,
            'error': 'Failed to fetch'
        }
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()
        packages = validator._get_available_packages()

        assert packages == {}

    def test_get_available_packages_exception(self, mocker):
        """Test package retrieval handles exceptions"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.side_effect = Exception("Connection timeout")
        mocker.patch('modules.payments.package_validator.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        validator = PackageValidator()
        packages = validator._get_available_packages()

        assert packages == {}
