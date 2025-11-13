# = BACKWARD COMPATIBILITY: Import all essential components
from .config import config_bp, init_app_and_config, init_config
from .security_config import SecurityConfig
from .config_manager import ConfigManager

# For external module imports
__all__ = ["config_bp", "init_app_and_config", "init_config", "SecurityConfig", "ConfigManager"]
