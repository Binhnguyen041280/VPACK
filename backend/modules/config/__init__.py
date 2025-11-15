# = BACKWARD COMPATIBILITY: Import all essential components
from .config import config_bp, init_app_and_config, init_config
from .config_manager import ConfigManager
from .security_config import SecurityConfig

# For external module imports
__all__ = ["config_bp", "init_app_and_config", "init_config", "SecurityConfig", "ConfigManager"]
