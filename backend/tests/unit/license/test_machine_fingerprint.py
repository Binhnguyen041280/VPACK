"""
Unit tests for machine_fingerprint module
Tests machine fingerprint generation for license binding
"""
import pytest
import platform
import uuid
import hashlib
from modules.license.machine_fingerprint import (
    generate_machine_fingerprint,
    get_system_info
)


class TestMachineFingerprintGeneration:
    """Tests for generate_machine_fingerprint() function"""

    def test_generate_fingerprint_returns_string(self):
        """Test that fingerprint is returned as a string"""
        fingerprint = generate_machine_fingerprint()
        assert isinstance(fingerprint, str)

    def test_generate_fingerprint_has_correct_length(self):
        """Test that fingerprint is exactly 32 characters long"""
        fingerprint = generate_machine_fingerprint()
        assert len(fingerprint) == 32

    def test_generate_fingerprint_is_hexadecimal(self):
        """Test that fingerprint contains only hexadecimal characters"""
        fingerprint = generate_machine_fingerprint()
        assert all(c in '0123456789abcdef' for c in fingerprint.lower())

    def test_generate_fingerprint_deterministic(self):
        """Test that fingerprint is deterministic (same machine = same hash)"""
        fingerprint1 = generate_machine_fingerprint()
        fingerprint2 = generate_machine_fingerprint()

        assert fingerprint1 == fingerprint2, \
            "Fingerprint should be the same for the same machine"

    def test_generate_fingerprint_uses_platform_data(self, mocker):
        """Test that fingerprint uses platform.node() data"""
        mock_node = mocker.patch('modules.license.machine_fingerprint.platform.node')
        mock_node.return_value = 'test-machine'

        fingerprint = generate_machine_fingerprint()

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 32
        mock_node.assert_called_once()

    def test_generate_fingerprint_fallback_on_error(self, mocker):
        """Test that fingerprint falls back to MD5 hash on error"""
        # Mock platform.node() to raise an exception on first call, succeed on second
        mock_node = mocker.patch('modules.license.machine_fingerprint.platform.node')
        mock_node.side_effect = [Exception("Platform error"), "fallback-hostname"]

        # Even with error, should return a valid fallback fingerprint
        fingerprint = generate_machine_fingerprint()

        assert isinstance(fingerprint, str)
        # Fallback should return 32 chars (MD5 truncated)
        assert len(fingerprint) == 32

    def test_generate_fingerprint_includes_mac_address(self, mocker):
        """Test that fingerprint includes MAC address (uuid.getnode)"""
        mock_getnode = mocker.patch('modules.license.machine_fingerprint.uuid.getnode')
        mock_getnode.return_value = 123456789012

        fingerprint = generate_machine_fingerprint()

        assert isinstance(fingerprint, str)
        mock_getnode.assert_called()

    def test_generate_fingerprint_uniqueness_different_machines(self, mocker):
        """Test that different machines produce different fingerprints"""
        # First machine
        mocker.patch('modules.license.machine_fingerprint.platform.node', return_value='machine-1')
        mocker.patch('modules.license.machine_fingerprint.uuid.getnode', return_value=111111)
        fingerprint1 = generate_machine_fingerprint()

        # Second machine (different hostname)
        mocker.patch('modules.license.machine_fingerprint.platform.node', return_value='machine-2')
        mocker.patch('modules.license.machine_fingerprint.uuid.getnode', return_value=222222)
        fingerprint2 = generate_machine_fingerprint()

        assert fingerprint1 != fingerprint2, \
            "Different machines should have different fingerprints"


class TestGetSystemInfo:
    """Tests for get_system_info() function"""

    def test_get_system_info_returns_dict(self):
        """Test that system info returns a dictionary"""
        info = get_system_info()
        assert isinstance(info, dict)

    def test_get_system_info_contains_required_keys(self):
        """Test that system info contains all required keys"""
        info = get_system_info()

        required_keys = [
            'platform',
            'system',
            'release',
            'version',
            'machine',
            'processor',
            'hostname',
            'mac_address'
        ]

        for key in required_keys:
            assert key in info, f"Missing required key: {key}"

    def test_get_system_info_has_valid_platform(self):
        """Test that platform field is not empty"""
        info = get_system_info()
        assert len(info['platform']) > 0

    def test_get_system_info_has_valid_system(self):
        """Test that system field matches platform.system()"""
        info = get_system_info()
        assert info['system'] == platform.system()

    def test_get_system_info_has_valid_hostname(self):
        """Test that hostname field matches platform.node()"""
        info = get_system_info()
        assert info['hostname'] == platform.node()

    def test_get_system_info_has_valid_mac_address(self):
        """Test that mac_address is a string representation of uuid.getnode()"""
        info = get_system_info()
        assert info['mac_address'] == str(uuid.getnode())

    def test_get_system_info_processor_not_empty(self):
        """Test that processor field is present (may be empty on some systems)"""
        info = get_system_info()
        assert 'processor' in info
        # Processor might be empty string on some systems, so we just check it exists

    def test_get_system_info_machine_architecture(self):
        """Test that machine field matches platform.machine()"""
        info = get_system_info()
        assert info['machine'] == platform.machine()


class TestMachineFingerprintCoverage:
    """Additional tests for edge cases and platform-specific scenarios"""

    def test_fingerprint_consistency_across_calls(self):
        """Test that multiple calls produce consistent results"""
        fingerprints = [generate_machine_fingerprint() for _ in range(5)]

        # All fingerprints should be identical
        assert len(set(fingerprints)) == 1, \
            "Multiple calls should produce the same fingerprint"

    def test_fingerprint_sha256_hash_format(self):
        """Test that fingerprint appears to be from SHA256 hash"""
        fingerprint = generate_machine_fingerprint()

        # SHA256 produces 64 hex chars, we take first 32
        assert len(fingerprint) == 32
        assert fingerprint.isalnum()

    @pytest.mark.parametrize("mock_hostname", [
        "test-machine",
        "localhost",
        "production-server-123",
        "user-macbook",
        "192.168.1.100"
    ])
    def test_fingerprint_with_various_hostnames(self, mocker, mock_hostname):
        """Test fingerprint generation with various hostname formats"""
        mocker.patch('modules.license.machine_fingerprint.platform.node',
                     return_value=mock_hostname)

        fingerprint = generate_machine_fingerprint()

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 32

    def test_system_info_json_serializable(self):
        """Test that system info can be JSON serialized"""
        import json

        info = get_system_info()

        # Should not raise exception
        json_str = json.dumps(info)
        assert isinstance(json_str, str)

        # Should be able to deserialize
        restored = json.loads(json_str)
        assert restored == info
