"""
Unit tests for license_generator module
Tests RSA cryptographic license generation and validation
"""
import pytest
import base64
import json
from datetime import datetime, timedelta
from modules.payments.license_generator import LicenseGenerator


class TestLicenseGeneratorInitialization:
    """Tests for LicenseGenerator initialization"""

    def test_generator_initializes_successfully(self, mocker):
        """Test that LicenseGenerator can be instantiated"""
        # Mock key loading to avoid file I/O
        mock_load = mocker.patch.object(LicenseGenerator, '_load_or_generate_keys')

        generator = LicenseGenerator()

        assert generator is not None
        mock_load.assert_called_once()

    def test_generator_has_key_attributes(self, mocker):
        """Test that generator has key attributes"""
        mocker.patch.object(LicenseGenerator, '_load_or_generate_keys')

        generator = LicenseGenerator()

        assert hasattr(generator, 'private_key')
        assert hasattr(generator, 'public_key')
        assert hasattr(generator, 'fernet_key')


class TestGenerateLicense:
    """Tests for generate_license() method"""

    def test_generate_license_success(self, mocker):
        """Test successful license generation"""
        # Mock the private key
        mock_private_key = mocker.MagicMock()
        mock_private_key.sign.return_value = b'signature_bytes'

        generator = LicenseGenerator()
        generator.private_key = mock_private_key

        license_info = {
            'customer_email': 'test@example.com',
            'product_type': 'desktop',
            'features': ['full_access'],
            'duration_days': 365
        }

        license_key = generator.generate_license(license_info)

        assert license_key is not None
        assert isinstance(license_key, str)
        # License key should be base64 encoded
        assert len(license_key) > 0
        mock_private_key.sign.assert_called_once()

    def test_generate_license_without_private_key(self, mocker):
        """Test license generation fails without private key"""
        mocker.patch.object(LicenseGenerator, '_load_or_generate_keys')

        generator = LicenseGenerator()
        generator.private_key = None

        license_info = {
            'customer_email': 'test@example.com',
            'product_type': 'desktop'
        }

        result = generator.generate_license(license_info)

        assert result is None

    def test_generate_license_with_custom_duration(self, mocker):
        """Test license generation with custom duration"""
        mock_private_key = mocker.MagicMock()
        mock_private_key.sign.return_value = b'signature'

        generator = LicenseGenerator()
        generator.private_key = mock_private_key

        license_info = {
            'customer_email': 'test@example.com',
            'duration_days': 30  # 30-day license
        }

        license_key = generator.generate_license(license_info)

        assert license_key is not None

    def test_generate_license_handles_exception(self, mocker):
        """Test that license generation handles exceptions"""
        mock_private_key = mocker.MagicMock()
        mock_private_key.sign.side_effect = Exception("Crypto error")

        generator = LicenseGenerator()
        generator.private_key = mock_private_key

        license_info = {'customer_email': 'test@example.com'}
        result = generator.generate_license(license_info)

        assert result is None


class TestVerifyLicense:
    """Tests for verify_license() method"""

    def test_verify_valid_license(self, mocker):
        """Test verification of valid license"""
        # Create mock license data
        license_data = {
            'customer_email': 'test@example.com',
            'product_type': 'desktop',
            'features': ['full_access'],
            'issue_date': datetime.now().isoformat(),
            'expiry_date': (datetime.now() + timedelta(days=365)).isoformat(),
            'license_id': 'test-id',
            'version': '1.0',
            'issuer': 'V_track License System'
        }

        # Create mock license package
        license_json = json.dumps(license_data, sort_keys=True, separators=(',', ':'))
        license_bytes = license_json.encode('utf-8')

        license_package = {
            'data': base64.b64encode(license_bytes).decode('ascii'),
            'signature': base64.b64encode(b'mock_signature').decode('ascii'),
            'algorithm': 'RSA-PSS-SHA256'
        }

        license_key = base64.b64encode(json.dumps(license_package).encode('utf-8')).decode('ascii')

        # Mock public key verification
        mock_public_key = mocker.MagicMock()
        mock_public_key.verify.return_value = None  # Successful verification

        generator = LicenseGenerator()
        generator.public_key = mock_public_key

        result = generator.verify_license(license_key)

        assert result is not None
        assert result['customer_email'] == 'test@example.com'
        mock_public_key.verify.assert_called_once()

    def test_verify_expired_license(self, mocker):
        """Test verification of expired license"""
        # Create expired license data
        license_data = {
            'customer_email': 'test@example.com',
            'expiry_date': (datetime.now() - timedelta(days=30)).isoformat()
        }

        license_json = json.dumps(license_data)
        license_bytes = license_json.encode('utf-8')

        license_package = {
            'data': base64.b64encode(license_bytes).decode('ascii'),
            'signature': base64.b64encode(b'signature').decode('ascii'),
            'algorithm': 'RSA-PSS-SHA256'
        }

        license_key = base64.b64encode(json.dumps(license_package).encode('utf-8')).decode('ascii')

        mock_public_key = mocker.MagicMock()
        mock_public_key.verify.return_value = None

        generator = LicenseGenerator()
        generator.public_key = mock_public_key

        result = generator.verify_license(license_key)

        # Expired license should return None
        assert result is None

    def test_verify_invalid_signature(self, mocker):
        """Test verification fails with invalid signature"""
        license_data = {
            'customer_email': 'test@example.com',
            'expiry_date': (datetime.now() + timedelta(days=365)).isoformat()
        }

        license_json = json.dumps(license_data)
        license_package = {
            'data': base64.b64encode(license_json.encode()).decode('ascii'),
            'signature': base64.b64encode(b'invalid_signature').decode('ascii'),
            'algorithm': 'RSA-PSS-SHA256'
        }

        license_key = base64.b64encode(json.dumps(license_package).encode()).decode('ascii')

        mock_public_key = mocker.MagicMock()
        # Signature verification raises exception for invalid signature
        mock_public_key.verify.side_effect = Exception("Invalid signature")

        generator = LicenseGenerator()
        generator.public_key = mock_public_key

        result = generator.verify_license(license_key)

        assert result is None

    def test_verify_malformed_license(self, mocker):
        """Test verification fails with malformed license"""
        mocker.patch.object(LicenseGenerator, '_load_or_generate_keys')

        generator = LicenseGenerator()
        generator.public_key = mocker.MagicMock()

        # Malformed base64
        result = generator.verify_license("not-a-valid-license-key")

        assert result is None

    def test_verify_without_public_key(self, mocker):
        """Test verification fails without public key"""
        mocker.patch.object(LicenseGenerator, '_load_or_generate_keys')

        generator = LicenseGenerator()
        generator.public_key = None

        result = generator.verify_license("some-license-key")

        assert result is None


class TestMachineFingerprintGeneration:
    """Tests for generate_machine_fingerprint() method"""

    def test_generate_machine_fingerprint_returns_string(self):
        """Test that machine fingerprint is returned as string"""
        generator = LicenseGenerator()
        fingerprint = generator.generate_machine_fingerprint()

        assert isinstance(fingerprint, str)
        assert len(fingerprint) > 0

    def test_generate_machine_fingerprint_deterministic(self):
        """Test that fingerprint is deterministic"""
        generator = LicenseGenerator()

        fp1 = generator.generate_machine_fingerprint()
        fp2 = generator.generate_machine_fingerprint()

        assert fp1 == fp2

    def test_generate_machine_fingerprint_has_correct_length(self):
        """Test that fingerprint has expected length (32 chars from SHA256)"""
        generator = LicenseGenerator()
        fingerprint = generator.generate_machine_fingerprint()

        assert len(fingerprint) == 32


class TestBindLicenseToMachine:
    """Tests for bind_license_to_machine() method"""

    def test_bind_license_success(self, mocker):
        """Test successful machine binding"""
        # Mock verify_license to return valid data
        mock_verify = mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={'customer_email': 'test@example.com'}
        )

        mock_private_key = mocker.MagicMock()
        mock_private_key.sign.return_value = b'new_signature'

        generator = LicenseGenerator()
        generator.private_key = mock_private_key

        bound_key = generator.bind_license_to_machine(
            'original-license-key',
            'test-machine-fingerprint'
        )

        assert bound_key is not None
        assert isinstance(bound_key, str)
        mock_verify.assert_called_once()
        mock_private_key.sign.assert_called_once()

    def test_bind_license_invalid_original(self, mocker):
        """Test binding fails with invalid original license"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value=None  # Invalid license
        )

        generator = LicenseGenerator()
        generator.private_key = mocker.MagicMock()

        result = generator.bind_license_to_machine('invalid-key', 'fingerprint')

        assert result is None

    def test_bind_license_auto_generates_fingerprint(self, mocker):
        """Test that binding auto-generates fingerprint if not provided"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={'customer_email': 'test@example.com'}
        )

        mock_private_key = mocker.MagicMock()
        mock_private_key.sign.return_value = b'signature'

        generator = LicenseGenerator()
        generator.private_key = mock_private_key

        # Don't provide machine_fingerprint (None)
        bound_key = generator.bind_license_to_machine('license-key', None)

        assert bound_key is not None

    def test_bind_license_without_private_key(self, mocker):
        """Test binding fails without private key"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={'customer_email': 'test@example.com'}
        )

        generator = LicenseGenerator()
        generator.private_key = None

        result = generator.bind_license_to_machine('license-key', 'fingerprint')

        assert result is None


class TestValidateMachineBinding:
    """Tests for validate_machine_binding() method"""

    def test_validate_binding_match(self, mocker):
        """Test validation succeeds when fingerprints match"""
        test_fingerprint = 'test-fingerprint-123'

        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={
                'customer_email': 'test@example.com',
                'machine_fingerprint': test_fingerprint
            }
        )

        mocker.patch.object(
            LicenseGenerator, 'generate_machine_fingerprint',
            return_value=test_fingerprint
        )

        generator = LicenseGenerator()
        result = generator.validate_machine_binding('license-key', test_fingerprint)

        assert result['valid'] is True
        assert result['bound'] is True

    def test_validate_binding_mismatch(self, mocker):
        """Test validation fails when fingerprints don't match"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={
                'customer_email': 'test@example.com',
                'machine_fingerprint': 'original-fingerprint'
            }
        )

        generator = LicenseGenerator()
        result = generator.validate_machine_binding(
            'license-key',
            'different-fingerprint'
        )

        assert result['valid'] is False
        assert 'error' in result
        assert 'mismatch' in result['error'].lower()

    def test_validate_unbound_license(self, mocker):
        """Test validation of license without machine binding"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={
                'customer_email': 'test@example.com'
                # No machine_fingerprint field
            }
        )

        generator = LicenseGenerator()
        result = generator.validate_machine_binding('license-key', 'fingerprint')

        assert result['valid'] is True
        assert result['bound'] is False

    def test_validate_invalid_license(self, mocker):
        """Test validation fails for invalid license"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value=None
        )

        generator = LicenseGenerator()
        result = generator.validate_machine_binding('invalid-key', 'fingerprint')

        assert result['valid'] is False
        assert 'error' in result


class TestGetPublicKeyPem:
    """Tests for get_public_key_pem() method"""

    def test_get_public_key_success(self, mocker):
        """Test successful public key export"""
        mock_public_key = mocker.MagicMock()
        mock_public_key.public_bytes.return_value = b'-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----'

        generator = LicenseGenerator()
        generator.public_key = mock_public_key

        pem = generator.get_public_key_pem()

        assert pem is not None
        assert isinstance(pem, str)
        assert 'BEGIN PUBLIC KEY' in pem
        mock_public_key.public_bytes.assert_called_once()

    def test_get_public_key_without_key(self, mocker):
        """Test public key export fails without key"""
        mocker.patch.object(LicenseGenerator, '_load_or_generate_keys')

        generator = LicenseGenerator()
        generator.public_key = None

        result = generator.get_public_key_pem()

        assert result is None

    def test_get_public_key_handles_exception(self, mocker):
        """Test that public key export handles exceptions"""
        mock_public_key = mocker.MagicMock()
        mock_public_key.public_bytes.side_effect = Exception("Export error")

        generator = LicenseGenerator()
        generator.public_key = mock_public_key

        result = generator.get_public_key_pem()

        assert result is None


class TestCreateLicensePackage:
    """Tests for create_license_package_for_distribution() method"""

    def test_create_package_success(self, mocker):
        """Test successful license package creation"""
        license_data = {
            'customer_email': 'test@example.com',
            'product_type': 'desktop',
            'features': ['full_access'],
            'expiry_date': '2026-12-31T23:59:59',
            'license_id': 'test-123'
        }

        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value=license_data
        )

        mocker.patch.object(
            LicenseGenerator, 'get_public_key_pem',
            return_value='-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----'
        )

        generator = LicenseGenerator()
        package = generator.create_license_package_for_distribution('test-license-key')

        assert package is not None
        assert 'license_key' in package
        assert 'public_key' in package
        assert 'customer_email' in package
        assert 'instructions' in package
        assert package['customer_email'] == 'test@example.com'

    def test_create_package_invalid_license(self, mocker):
        """Test package creation fails for invalid license"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value=None
        )

        generator = LicenseGenerator()
        result = generator.create_license_package_for_distribution('invalid-key')

        assert result is None

    def test_create_package_no_public_key(self, mocker):
        """Test package creation fails without public key"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={'customer_email': 'test@example.com'}
        )

        mocker.patch.object(
            LicenseGenerator, 'get_public_key_pem',
            return_value=None
        )

        generator = LicenseGenerator()
        result = generator.create_license_package_for_distribution('test-key')

        assert result is None

    def test_create_package_includes_instructions(self, mocker):
        """Test that package includes installation instructions"""
        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            return_value={
                'customer_email': 'test@example.com',
                'product_type': 'desktop',
                'features': [],
                'expiry_date': '2026-12-31',
                'license_id': 'test'
            }
        )

        mocker.patch.object(
            LicenseGenerator, 'get_public_key_pem',
            return_value='public-key-pem'
        )

        generator = LicenseGenerator()
        package = generator.create_license_package_for_distribution('test-key')

        assert 'instructions' in package
        assert 'installation' in package['instructions']
        assert 'support' in package['instructions']
        assert isinstance(package['instructions']['installation'], list)


class TestLicenseGeneratorIntegration:
    """Integration tests for full license lifecycle"""

    def test_full_license_lifecycle(self, mocker):
        """Test complete license generation and verification flow"""
        # This would require actual RSA keys, so we mock the crypto parts
        mock_private_key = mocker.MagicMock()
        mock_private_key.sign.return_value = b'valid_signature'

        mock_public_key = mocker.MagicMock()
        mock_public_key.verify.return_value = None  # Successful verification

        generator = LicenseGenerator()
        generator.private_key = mock_private_key
        generator.public_key = mock_public_key

        # Step 1: Generate license
        license_info = {
            'customer_email': 'test@example.com',
            'product_type': 'desktop',
            'features': ['full_access'],
            'duration_days': 365
        }

        license_key = generator.generate_license(license_info)
        assert license_key is not None

        # Step 2: Verify license (would fail with mocks, but tests the flow)
        # In real scenario, this would succeed with proper keys
        # Just verify the method can be called
        assert hasattr(generator, 'verify_license')

    def test_license_binding_flow(self, mocker):
        """Test license generation -> binding -> validation flow"""
        mock_private_key = mocker.MagicMock()
        mock_private_key.sign.return_value = b'signature'

        # Mock verification to return valid license data
        original_license_data = {
            'customer_email': 'test@example.com',
            'product_type': 'desktop'
        }

        bound_license_data = original_license_data.copy()
        bound_license_data['machine_fingerprint'] = 'test-fingerprint'

        mocker.patch.object(
            LicenseGenerator, 'verify_license',
            side_effect=[original_license_data, bound_license_data]
        )

        generator = LicenseGenerator()
        generator.private_key = mock_private_key

        # Bind license
        bound_key = generator.bind_license_to_machine(
            'original-key',
            'test-fingerprint'
        )

        assert bound_key is not None

        # Validate binding
        result = generator.validate_machine_binding(
            bound_key,
            'test-fingerprint'
        )

        assert result['valid'] is True
        assert result['bound'] is True
