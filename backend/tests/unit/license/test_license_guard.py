"""
Unit tests for license_guard module
Tests decorators and guards for API endpoint protection
"""
import pytest
from flask import Flask, jsonify
from modules.license.license_guard import (
    require_valid_license,
    require_license_feature,
    check_license_status,
    _get_friendly_message
)


class TestRequireValidLicenseDecorator:
    """Tests for @require_valid_license decorator"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_decorator_allows_valid_license(self, app, client, mocker):
        """Test that decorator allows access when license is valid"""
        # Mock LicenseManager to return valid status
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={
                'status': 'valid',
                'has_license': True,
                'license': {'license_key': 'TEST-KEY'}
            }
        )

        @app.route('/test')
        @require_valid_license
        def test_endpoint():
            return jsonify({'success': True, 'data': 'allowed'})

        response = client.get('/test')

        assert response.status_code == 200
        assert response.json['success'] is True
        assert response.json['data'] == 'allowed'
        mock_get_status.assert_called_once()

    def test_decorator_blocks_no_license(self, app, client, mocker):
        """Test that decorator blocks access when no license found"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={
                'status': 'no_license',
                'has_license': False
            }
        )

        @app.route('/test')
        @require_valid_license
        def test_endpoint():
            return jsonify({'success': True})

        response = client.get('/test')

        assert response.status_code == 403
        assert response.json['success'] is False
        assert response.json['error'] == 'license_required'
        assert 'upgrade_url' in response.json
        mock_get_status.assert_called_once()

    def test_decorator_blocks_expired_license(self, app, client, mocker):
        """Test that decorator blocks access when license is expired"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={
                'status': 'invalid',
                'has_license': True,
                'reason': 'expired',
                'license': {
                    'license_key': 'TEST-KEY',
                    'expires_at': '2024-01-01T00:00:00'
                }
            }
        )

        @app.route('/test')
        @require_valid_license
        def test_endpoint():
            return jsonify({'success': True})

        response = client.get('/test')

        assert response.status_code == 403
        assert response.json['success'] is False
        assert 'expired' in response.json['message'].lower()
        mock_get_status.assert_called_once()

    def test_decorator_blocks_on_exception(self, app, client, mocker):
        """Test that decorator blocks access on license check exception"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            side_effect=Exception("Database error")
        )

        @app.route('/test')
        @require_valid_license
        def test_endpoint():
            return jsonify({'success': True})

        response = client.get('/test')

        assert response.status_code == 403
        assert response.json['success'] is False
        assert response.json['error'] == 'license_check_failed'
        mock_get_status.assert_called_once()

    def test_decorator_preserves_function_name(self, app):
        """Test that decorator preserves original function name"""
        @require_valid_license
        def my_endpoint():
            return jsonify({'success': True})

        assert my_endpoint.__name__ == 'my_endpoint'

    def test_decorator_includes_endpoint_name_in_response(self, app, client, mocker):
        """Test that blocked response includes endpoint name"""
        mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'no_license', 'has_license': False}
        )

        @app.route('/protected-endpoint')
        @require_valid_license
        def protected_endpoint():
            return jsonify({'success': True})

        response = client.get('/protected-endpoint')

        assert response.status_code == 403
        assert response.json['blocked_endpoint'] == 'protected_endpoint'

    def test_decorator_returns_json_format(self, app, client, mocker):
        """Test that decorator returns proper JSON error response"""
        mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'no_license', 'has_license': False}
        )

        @app.route('/test')
        @require_valid_license
        def test_endpoint():
            return jsonify({'success': True})

        response = client.get('/test')

        assert response.content_type == 'application/json'
        assert 'success' in response.json
        assert 'error' in response.json
        assert 'message' in response.json


class TestRequireLicenseFeatureDecorator:
    """Tests for @require_license_feature decorator"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_feature_decorator_allows_valid_license(self, app, client, mocker):
        """Test that feature decorator allows access with valid license"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'valid', 'has_license': True}
        )

        @app.route('/advanced')
        @require_license_feature('advanced_analytics')
        def advanced_endpoint():
            return jsonify({'success': True})

        response = client.get('/advanced')

        assert response.status_code == 200
        assert response.json['success'] is True
        mock_get_status.assert_called_once()

    def test_feature_decorator_blocks_no_license(self, app, client, mocker):
        """Test that feature decorator blocks when no license"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'no_license', 'has_license': False}
        )

        @app.route('/advanced')
        @require_license_feature('advanced_analytics')
        def advanced_endpoint():
            return jsonify({'success': True})

        response = client.get('/advanced')

        assert response.status_code == 403
        assert response.json['error'] == 'feature_requires_license'
        assert 'advanced_analytics' in response.json['message']

    def test_feature_decorator_includes_feature_name(self, app, client, mocker):
        """Test that feature decorator includes feature name in response"""
        mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'no_license', 'has_license': False}
        )

        @app.route('/premium')
        @require_license_feature('premium_reports')
        def premium_endpoint():
            return jsonify({'success': True})

        response = client.get('/premium')

        assert response.status_code == 403
        assert response.json['feature'] == 'premium_reports'

    def test_feature_decorator_handles_exception(self, app, client, mocker):
        """Test that feature decorator handles exceptions gracefully"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            side_effect=Exception("License error")
        )

        @app.route('/test')
        @require_license_feature('test_feature')
        def test_endpoint():
            return jsonify({'success': True})

        response = client.get('/test')

        assert response.status_code == 403
        assert response.json['error'] == 'feature_check_failed'


class TestCheckLicenseStatus:
    """Tests for check_license_status() utility function"""

    def test_check_status_returns_valid_for_valid_license(self, mocker):
        """Test that check_license_status returns valid=True for valid license"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={
                'status': 'valid',
                'has_license': True,
                'license': {'license_key': 'TEST'}
            }
        )

        result = check_license_status()

        assert result['valid'] is True
        assert result['status'] == 'valid'
        assert 'license' in result
        assert 'message' in result

    def test_check_status_returns_invalid_for_no_license(self, mocker):
        """Test that check_license_status returns valid=False when no license"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'no_license', 'has_license': False}
        )

        result = check_license_status()

        assert result['valid'] is False
        assert result['status'] == 'no_license'

    def test_check_status_returns_invalid_for_expired(self, mocker):
        """Test that check_license_status returns valid=False for expired license"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={
                'status': 'invalid',
                'has_license': True,
                'reason': 'expired',
                'license': {'expires_at': '2024-01-01'}
            }
        )

        result = check_license_status()

        assert result['valid'] is False
        assert result['status'] == 'invalid'

    def test_check_status_handles_exception(self, mocker):
        """Test that check_license_status handles exceptions gracefully"""
        mock_get_status = mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            side_effect=Exception("Database unavailable")
        )

        result = check_license_status()

        assert result['valid'] is False
        assert result['status'] == 'error'
        assert 'error' in result

    def test_check_status_returns_dict(self, mocker):
        """Test that check_license_status always returns a dictionary"""
        mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'valid'}
        )

        result = check_license_status()

        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'status' in result
        assert 'message' in result


class TestGetFriendlyMessage:
    """Tests for _get_friendly_message() helper function"""

    def test_friendly_message_for_no_license(self):
        """Test friendly message for no license status"""
        status_result = {'status': 'no_license'}
        message = _get_friendly_message(status_result)

        assert isinstance(message, str)
        assert 'no license' in message.lower() or 'activate' in message.lower()

    def test_friendly_message_for_expired_license(self):
        """Test friendly message for expired license with date"""
        status_result = {
            'status': 'invalid',
            'reason': 'expired',
            'license': {'expires_at': '2024-12-31T23:59:59'}
        }
        message = _get_friendly_message(status_result)

        assert isinstance(message, str)
        assert 'expired' in message.lower()
        assert '2024-12-31' in message

    def test_friendly_message_for_invalid_license(self):
        """Test friendly message for invalid license"""
        status_result = {'status': 'invalid', 'reason': 'invalid_signature'}
        message = _get_friendly_message(status_result)

        assert isinstance(message, str)
        assert 'invalid' in message.lower()

    def test_friendly_message_for_error(self):
        """Test friendly message for error status"""
        status_result = {'status': 'error'}
        message = _get_friendly_message(status_result)

        assert isinstance(message, str)
        assert len(message) > 0

    def test_friendly_message_for_unknown_status(self):
        """Test friendly message for unknown status"""
        status_result = {'status': 'unknown_status'}
        message = _get_friendly_message(status_result)

        assert isinstance(message, str)
        assert len(message) > 0

    def test_friendly_message_includes_upgrade_guidance(self):
        """Test that messages include helpful upgrade guidance"""
        status_result = {'status': 'no_license'}
        message = _get_friendly_message(status_result)

        # Should mention activation or upgrade
        assert any(word in message.lower() for word in ['activate', 'license', 'plan'])


@pytest.mark.integration
class TestLicenseGuardIntegration:
    """Integration tests for license guard with Flask app"""

    @pytest.fixture
    def app(self):
        """Create Flask app with multiple protected endpoints"""
        app = Flask(__name__)
        app.config['TESTING'] = True

        @app.route('/public')
        def public_endpoint():
            return jsonify({'success': True, 'message': 'Public access'})

        @app.route('/protected')
        @require_valid_license
        def protected_endpoint():
            return jsonify({'success': True, 'message': 'Protected access'})

        @app.route('/feature/advanced')
        @require_license_feature('advanced_analytics')
        def feature_endpoint():
            return jsonify({'success': True, 'message': 'Feature access'})

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_public_endpoint_always_accessible(self, client):
        """Test that public endpoints are not affected by license guard"""
        response = client.get('/public')

        assert response.status_code == 200
        assert response.json['success'] is True

    def test_protected_endpoint_requires_license(self, client, mocker):
        """Test that protected endpoints check license"""
        mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'no_license', 'has_license': False}
        )

        response = client.get('/protected')

        assert response.status_code == 403

    def test_feature_endpoint_requires_valid_license(self, client, mocker):
        """Test that feature endpoints require valid license"""
        mocker.patch(
            'modules.license.license_guard.LicenseManager.get_license_status',
            return_value={'status': 'valid', 'has_license': True}
        )

        response = client.get('/feature/advanced')

        assert response.status_code == 200
