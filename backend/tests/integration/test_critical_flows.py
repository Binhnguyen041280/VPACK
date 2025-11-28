"""
Integration tests for critical backend workflows
Simplified tests focusing on key integration points
"""
import pytest
from datetime import datetime, timedelta


class TestPackageValidationIntegration:
    """Integration tests for package validation across payment flow"""

    def test_valid_package_accepted_for_payment(self, app, client, mocker):
        """Test that valid package passes validation and allows payment creation"""
        # Mock pricing client
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {
                'starter_1m': {'name': 'Starter', 'price': 9.99}
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

    def test_invalid_package_rejected_for_payment(self, app, client, mocker):
        """Test that invalid package is rejected before payment creation"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {'starter_1m': {}, 'pro_1m': {}}
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        response = client.post('/api/payment/create', json={
            'customer_email': 'test@example.com',
            'package_type': 'nonexistent_package'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid package type' in data['error']


class TestLicenseValidationSources:
    """Integration tests for license validation source handling"""

    def test_cloud_validation_provides_source_metadata(self, app, client, mocker):
        """Test that cloud validation includes source information"""
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
            'license_key': 'VTRACK-S1M-TEST123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['validation']['source'] == 'cloud'
        assert data['validation']['method'] == 'cloud'
        assert 'timestamp' in data['validation']

    def test_offline_validation_includes_warning(self, app, client, mocker):
        """Test that offline validation includes appropriate warnings"""
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
            'license_key': 'VTRACK-S1M-OFFLINE'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['validation']['method'] == 'offline'
        assert 'warning' in data
        assert 'offline' in data['warning']['message'].lower()


class TestInvalidLicenseRejection:
    """Integration tests for invalid license rejection"""

    def test_obviously_invalid_license_rejected_immediately(self, app, client):
        """Test that obviously invalid licenses are rejected without cloud call"""
        invalid_licenses = [
            'INVALID-TEST-123',
            'test-license',
            'fake-key'
        ]

        for license_key in invalid_licenses:
            response = client.post('/api/payment/validate-license', json={
                'license_key': license_key
            })

            data = response.get_json()
            assert data['success'] is False
            assert data['valid'] is False
            assert data.get('source') == 'local_validation'

    def test_invalid_license_rejected_for_activation(self, app, client):
        """Test that invalid licenses are rejected during activation"""
        response = client.post('/api/payment/activate-license', json={
            'license_key': 'INVALID-LICENSE'
        })

        data = response.get_json()
        assert data['success'] is False
        assert 'Invalid license key format' in data['error']


class TestPackageExtraction:
    """Integration tests for package extraction from license keys"""

    def test_extract_package_from_various_license_formats(self):
        """Test extracting package information from different license key formats"""
        from modules.payments.payment_routes import extract_package_from_license_key

        test_cases = [
            ('VTRACK-S1M-ABC', 'starter_1m', 30),
            ('VTRACK-P1M-DEF', 'pro_1m', 30),
            ('VTRACK-T14D-GHI', 'trial_14d', 14),
            ('VTRACK-T10M-JKL', 'test_10m', 0),
            ('VTRACK-UNKNOWN-XYZ', 'desktop', 365),  # Unknown code
            ('INVALID', 'desktop', 365),  # Invalid format
            ('', 'desktop', 365),  # Empty string
        ]

        for license_key, expected_type, expected_days in test_cases:
            result = extract_package_from_license_key(license_key)
            assert result['product_type'] == expected_type
            assert result['expires_days'] == expected_days


class TestHealthCheckIntegration:
    """Integration tests for health check endpoint"""

    def test_health_check_success(self, app, client, mocker):
        """Test health check returns success when services are available"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.health_check.return_value = {
            'success': True,
            'status': 'healthy',
            'services': {
                'cloud_function': 'online',
                'firestore': 'online'
            }
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.get('/api/payment/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_health_check_failure(self, app, client, mocker):
        """Test health check reports failure when services are down"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.health_check.side_effect = Exception("Service unavailable")
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.get('/api/payment/health')

        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False


class TestGetPackagesIntegration:
    """Integration tests for package retrieval"""

    def test_get_packages_returns_available_packages(self, app, client, mocker):
        """Test retrieving available packages from CloudFunction"""
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
        assert len(data['packages']) == 2

    def test_get_packages_for_upgrade_fetches_fresh(self, app, client, mocker):
        """Test that upgrade request fetches fresh pricing"""
        mock_pricing_client = mocker.MagicMock()
        mock_pricing_client.fetch_pricing_for_upgrade.return_value = {
            'success': True,
            'packages': {'starter_1m': {}}
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_pricing_client',
                    return_value=mock_pricing_client)

        response = client.get('/api/payment/packages?for_upgrade=true')

        assert response.status_code == 200
        # Verify that fetch_pricing_for_upgrade was called (not get_cached_pricing)
        mock_pricing_client.fetch_pricing_for_upgrade.assert_called_once()


class TestGetUserLicenses:
    """Integration tests for user license retrieval"""

    def test_get_user_licenses_success(self, app, client, mocker):
        """Test retrieving licenses for a user"""
        customer_email = "user@example.com"

        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.get_user_licenses.return_value = {
            'success': True,
            'licenses': [
                {
                    'license_key': 'VTRACK-S1M-USER123',
                    'package_type': 'starter_1m',
                    'status': 'active',
                    'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
                }
            ]
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.get(f'/api/payment/licenses/{customer_email}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['licenses']) == 1

    def test_get_user_licenses_empty(self, app, client, mocker):
        """Test retrieving licenses for user with no licenses"""
        mock_cloud_client = mocker.MagicMock()
        mock_cloud_client.get_user_licenses.return_value = {
            'success': True,
            'licenses': []
        }
        mocker.patch('modules.payments.payment_routes.get_cloud_client',
                    return_value=mock_cloud_client)

        response = client.get('/api/payment/licenses/newuser@example.com')

        assert response.status_code == 200
        data = response.get_json()
        assert data['licenses'] == []
