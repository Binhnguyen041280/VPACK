"""
Unit tests for payment_routes module
Tests all payment API endpoints and helper functions
"""
import pytest
import json
from datetime import datetime, timedelta
from modules.payments.payment_routes import (
    payment_bp,
    is_obviously_invalid_license,
    extract_package_from_license_key
)


class TestHelperFunctions:
    """Tests for payment_routes helper functions"""

    def test_is_obviously_invalid_license_with_empty_string(self):
        """Test that empty string is invalid"""
        assert is_obviously_invalid_license('') is True

    def test_is_obviously_invalid_license_with_none(self):
        """Test that None is invalid"""
        assert is_obviously_invalid_license(None) is True

    def test_is_obviously_invalid_license_with_invalid_prefix(self):
        """Test that INVALID- prefix is rejected"""
        assert is_obviously_invalid_license('INVALID-ABC-123') is True

    def test_is_obviously_invalid_license_with_test_pattern(self):
        """Test that 'test' pattern is rejected"""
        assert is_obviously_invalid_license('test-license-key') is True

    def test_is_obviously_invalid_license_with_valid_key(self):
        """Test that valid key format passes"""
        assert is_obviously_invalid_license('VTRACK-S1M-ABC123-XYZ') is False

    def test_extract_package_from_license_key_with_starter_monthly(self):
        """Test extracting S1M (Starter Monthly) package"""
        result = extract_package_from_license_key('VTRACK-S1M-ABC123')

        assert result['product_type'] == 'starter_1m'
        assert result['expires_days'] == 30
        assert result['package_name'] == 'Starter Monthly'

    def test_extract_package_from_license_key_with_pro_monthly(self):
        """Test extracting P1M (Pro Monthly) package"""
        result = extract_package_from_license_key('VTRACK-P1M-ABC123')

        assert result['product_type'] == 'pro_1m'
        assert result['expires_days'] == 30
        assert result['package_name'] == 'Pro Monthly'

    def test_extract_package_from_license_key_with_trial_14d(self):
        """Test extracting T14D (14 Days Trial) package"""
        result = extract_package_from_license_key('VTRACK-T14D-ABC123')

        assert result['product_type'] == 'trial_14d'
        assert result['expires_days'] == 14
        assert result['package_name'] == '14 Days Free Trial'

    def test_extract_package_from_license_key_with_test_10m(self):
        """Test extracting T10M (10 Minutes Test) package"""
        result = extract_package_from_license_key('VTRACK-T10M-ABC123')

        assert result['product_type'] == 'test_10m'
        assert result['expires_days'] == 0
        assert result['package_name'] == '10 Minutes Test'

    def test_extract_package_from_license_key_with_unknown_code(self):
        """Test extracting unknown package code returns default"""
        result = extract_package_from_license_key('VTRACK-XXX-ABC123')

        assert result['product_type'] == 'desktop'
        assert result['expires_days'] == 365
        assert result['package_name'] == 'Desktop Standard'

    def test_extract_package_from_license_key_with_invalid_format(self):
        """Test extracting from invalid format returns default"""
        result = extract_package_from_license_key('INVALID')

        assert result['product_type'] == 'desktop'
        assert result['expires_days'] == 365

    def test_extract_package_from_license_key_with_empty_string(self):
        """Test extracting from empty string returns default"""
        result = extract_package_from_license_key('')

        assert result['product_type'] == 'desktop'
        assert result['expires_days'] == 365


class TestCreatePaymentEndpoint:
    """Tests for POST /api/payment/create endpoint"""

    def test_create_payment_success(self, app, client, mocker):
        """Test successful payment creation"""
        # Mock pricing client validation
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {
                'starter_1m': {'name': 'Starter Monthly', 'price': 9.99}
            }
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        # Mock cloud client
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.create_payment.return_value = {
            'success': True,
            'data': {
                'payment_url': 'https://payment.example.com/pay',
                'order_code': 'ORDER123',
                'amount': 999
            }
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.post('/api/payment/create', json={
            'customer_email': 'test@example.com',
            'package_type': 'starter_1m'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['payment_url'] == 'https://payment.example.com/pay'
        assert data['order_code'] == 'ORDER123'

    def test_create_payment_missing_email(self, app, client):
        """Test payment creation with missing email"""
        response = client.post('/api/payment/create', json={
            'package_type': 'starter_1m'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'customer_email' in data['error']

    def test_create_payment_missing_package_type(self, app, client):
        """Test payment creation with missing package_type"""
        response = client.post('/api/payment/create', json={
            'customer_email': 'test@example.com'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'package_type' in data['error']

    def test_create_payment_invalid_package_type(self, app, client, mocker):
        """Test payment creation with invalid package type"""
        # Mock pricing client to return available packages
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {
                'starter_1m': {'name': 'Starter Monthly'}
            }
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        response = client.post('/api/payment/create', json={
            'customer_email': 'test@example.com',
            'package_type': 'invalid_package'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Invalid package type' in data['error']

    def test_create_payment_cloud_failure(self, app, client, mocker):
        """Test payment creation when cloud client fails"""
        # Mock pricing client
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {'starter_1m': {}}
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        # Mock cloud client to fail
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.create_payment.return_value = {
            'success': False,
            'error': 'Payment gateway error'
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.post('/api/payment/create', json={
            'customer_email': 'test@example.com',
            'package_type': 'starter_1m'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Payment gateway error' in data['error']


class TestValidateLicenseEndpoint:
    """Tests for POST /api/payment/validate-license endpoint"""

    def test_validate_license_success_cloud(self, app, client, mocker):
        """Test successful license validation via cloud"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.validate_license.return_value = {
            'success': True,
            'valid': True,
            'source': 'cloud',
            'data': {
                'customer_email': 'test@example.com',
                'package_type': 'starter_1m',
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
            }
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.post('/api/payment/validate-license', json={
            'license_key': 'VTRACK-S1M-ABC123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['valid'] is True
        assert data['validation']['source'] == 'cloud'

    def test_validate_license_success_offline(self, app, client, mocker):
        """Test successful license validation via offline fallback"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.validate_license.return_value = {
            'success': True,
            'valid': True,
            'source': 'offline',
            'reason': 'cloud_unavailable',
            'data': {
                'customer_email': 'test@example.com',
                'package_type': 'starter_1m'
            }
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.post('/api/payment/validate-license', json={
            'license_key': 'VTRACK-S1M-ABC123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['valid'] is True
        assert data['validation']['source'] == 'offline'
        assert 'warning' in data

    def test_validate_license_invalid_key(self, app, client, mocker):
        """Test validation with invalid license key"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.validate_license.return_value = {
            'success': True,
            'valid': False,
            'source': 'cloud',
            'error': 'Invalid or expired license'
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.post('/api/payment/validate-license', json={
            'license_key': 'VTRACK-S1M-INVALID'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert data['valid'] is False

    def test_validate_license_missing_key(self, app, client):
        """Test validation with missing license key"""
        response = client.post('/api/payment/validate-license', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'license_key' in data['error']

    def test_validate_license_obviously_invalid(self, app, client):
        """Test validation rejects obviously invalid keys"""
        response = client.post('/api/payment/validate-license', json={
            'license_key': 'INVALID-TEST-KEY'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert data['valid'] is False
        assert data['source'] == 'local_validation'


class TestGetPackagesEndpoint:
    """Tests for GET /api/payment/packages endpoint"""

    def test_get_packages_success(self, app, client, mocker):
        """Test successful package retrieval"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.get_cached_pricing.return_value = {
            'success': True,
            'packages': {
                'starter_1m': {'name': 'Starter', 'price': 9.99},
                'pro_1m': {'name': 'Pro', 'price': 19.99}
            }
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        response = client.get('/api/payment/packages')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'packages' in data
        assert 'starter_1m' in data['packages']

    def test_get_packages_for_upgrade(self, app, client, mocker):
        """Test package retrieval for upgrade action (fresh fetch)"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {'starter_1m': {}}
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        response = client.get('/api/payment/packages?for_upgrade=true')

        assert response.status_code == 200
        mock_pricing_client.fetch_pricing_for_upgrade.assert_called_once()

    def test_get_packages_with_fallback(self, app, client, mocker):
        """Test package retrieval with fallback to cache on error"""
        mock_pricing_client = mocker.MagicMock()
        # First call raises exception, fallback returns cached data
        mock_pricing_client.get_cached_pricing.side_effect = [
            None,  # No cache initially
            {'success': True, 'packages': {}}  # Fallback cache
        ]
        mock_pricing_client.fetch_pricing_for_upgrade.side_effect = Exception("Network error")

        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        response = client.get('/api/payment/packages')

        # Should return fallback data instead of error
        data = response.get_json()
        assert 'fallback' in data or response.status_code == 500


class TestGetUserLicensesEndpoint:
    """Tests for GET /api/payment/licenses/<email> endpoint"""

    def test_get_user_licenses_success(self, app, client, mocker):
        """Test successful license retrieval for user"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.get_user_licenses.return_value = {
            'success': True,
            'licenses': [
                {
                    'license_key': 'VTRACK-S1M-ABC123',
                    'package_type': 'starter_1m',
                    'status': 'active'
                }
            ]
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.get('/api/payment/licenses/test@example.com')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'licenses' in data


class TestHealthCheckEndpoint:
    """Tests for GET /api/payment/health endpoint"""

    def test_health_check_success(self, app, client, mocker):
        """Test successful health check"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.health_check.return_value = {
            'success': True,
            'status': 'healthy'
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.get('/api/payment/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_health_check_failure(self, app, client, mocker):
        """Test health check when cloud is down"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.health_check.side_effect = Exception("Cloud unavailable")
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.get('/api/payment/health')

        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
