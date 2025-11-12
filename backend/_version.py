"""Version information for ePACK."""

__version__ = "1.0.0"
__version_info__ = tuple(int(x) for x in __version__.split("."))

# Version history
__version_history__ = {
    "1.0.0": "Initial release - Enterprise-grade video processing platform with production-ready infrastructure",
}

def get_version() -> str:
    """Get the current version string."""
    return __version__

def get_version_info() -> tuple:
    """Get the version as a tuple of integers."""
    return __version_info__
