"""Version information for VPACK."""

__version__ = "2.1.0"
__version_info__ = tuple(int(x) for x in __version__.split("."))

# Version history
__version_history__ = {
    "2.1.0": "Production-ready packaging and build automation",
    "2.0.0": "Major refactor with multi-source support",
    "1.0.0": "Initial release",
}

def get_version() -> str:
    """Get the current version string."""
    return __version__

def get_version_info() -> tuple:
    """Get the version as a tuple of integers."""
    return __version_info__
