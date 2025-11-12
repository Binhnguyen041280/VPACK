"""Unit tests for version management."""

import pytest
from backend._version import (
    __version__,
    __version_info__,
    __version_history__,
    get_version,
    get_version_info
)


class TestVersionModule:
    """Test version module functionality."""

    def test_version_string_format(self):
        """Test that version string has correct format."""
        assert isinstance(__version__, str)
        parts = __version__.split(".")
        assert len(parts) == 3, "Version should be in format X.Y.Z"

        major, minor, patch = parts
        assert major.isdigit()
        assert minor.isdigit()
        assert patch.isdigit()

    def test_version_info_tuple(self):
        """Test that version_info is a tuple of integers."""
        assert isinstance(__version_info__, tuple)
        assert len(__version_info__) == 3
        assert all(isinstance(x, int) for x in __version_info__)

    def test_version_consistency(self):
        """Test that version string and tuple are consistent."""
        major, minor, patch = __version__.split(".")
        assert __version_info__ == (int(major), int(minor), int(patch))

    def test_current_version_value(self):
        """Test current version value."""
        assert __version__ == "2.1.0"
        assert __version_info__ == (2, 1, 0)

    def test_get_version_function(self):
        """Test get_version() returns correct version."""
        version = get_version()
        assert version == __version__
        assert isinstance(version, str)

    def test_get_version_info_function(self):
        """Test get_version_info() returns correct tuple."""
        version_info = get_version_info()
        assert version_info == __version_info__
        assert isinstance(version_info, tuple)

    def test_version_history_exists(self):
        """Test that version history dictionary exists."""
        assert isinstance(__version_history__, dict)
        assert len(__version_history__) > 0

    def test_current_version_in_history(self):
        """Test that current version is documented in history."""
        assert __version__ in __version_history__

    def test_version_history_format(self):
        """Test that version history has correct format."""
        for version, description in __version_history__.items():
            # Each version should be valid semver format
            parts = version.split(".")
            assert len(parts) == 3

            # Description should be non-empty string
            assert isinstance(description, str)
            assert len(description) > 0

    def test_version_ordering(self):
        """Test that versions in history are semantically ordered."""
        versions = list(__version_history__.keys())
        version_tuples = [tuple(map(int, v.split("."))) for v in versions]

        # Check that we have at least one version
        assert len(version_tuples) >= 1

        # Current version should be the highest
        assert __version_info__ >= max(version_tuples)
