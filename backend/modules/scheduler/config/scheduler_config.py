"""
Centralized configuration for the scheduler module.

This module contains all configuration constants used throughout the scheduler system,
including batch processing settings, system monitoring thresholds, and timing parameters.
"""

import logging
from typing import Dict, Any


class SchedulerConfig:
    """Centralized configuration class for the scheduler module."""
    
    # Batch processing configuration
    BATCH_SIZE_MIN = 2
    BATCH_SIZE_MAX = 6
    BATCH_SIZE_DEFAULT = 2
    
    # Timing configuration (seconds)
    SCAN_INTERVAL_SECONDS = 60
    TIMEOUT_SECONDS = 3600
    QUEUE_LIMIT = 5
    
    # System monitoring thresholds (percentages)
    CPU_THRESHOLD_LOW = 70
    CPU_THRESHOLD_HIGH = 90
    MEMORY_THRESHOLD = 85
    
    # Thread management (seconds)
    THREAD_JOIN_TIMEOUT = 5.0
    EVENT_WAIT_TIMEOUT = 30
    
    # File scanning configuration
    DEFAULT_SCAN_DAYS = 7
    BUFFER_SECONDS = 360  # 6 minutes in seconds
    N_FILES_FOR_ESTIMATE = 3
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """
        Get all configuration values as a dictionary.
        
        Returns:
            Dict containing all configuration constants
        """
        return {
            'batch_size_min': cls.BATCH_SIZE_MIN,
            'batch_size_max': cls.BATCH_SIZE_MAX,
            'batch_size_default': cls.BATCH_SIZE_DEFAULT,
            'scan_interval_seconds': cls.SCAN_INTERVAL_SECONDS,
            'timeout_seconds': cls.TIMEOUT_SECONDS,
            'queue_limit': cls.QUEUE_LIMIT,
            'cpu_threshold_low': cls.CPU_THRESHOLD_LOW,
            'cpu_threshold_high': cls.CPU_THRESHOLD_HIGH,
            'memory_threshold': cls.MEMORY_THRESHOLD,
            'thread_join_timeout': cls.THREAD_JOIN_TIMEOUT,
            'event_wait_timeout': cls.EVENT_WAIT_TIMEOUT,
            'default_scan_days': cls.DEFAULT_SCAN_DAYS,
            'buffer_seconds': cls.BUFFER_SECONDS,
            'n_files_for_estimate': cls.N_FILES_FOR_ESTIMATE,
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate configuration values to ensure they are within acceptable ranges.
        
        Returns:
            True if all configuration is valid, False otherwise
        """
        try:
            # Validate batch size ranges
            assert cls.BATCH_SIZE_MIN > 0, "BATCH_SIZE_MIN must be greater than 0"
            assert cls.BATCH_SIZE_MAX >= cls.BATCH_SIZE_MIN, "BATCH_SIZE_MAX must be >= BATCH_SIZE_MIN"
            assert cls.BATCH_SIZE_DEFAULT >= cls.BATCH_SIZE_MIN, "BATCH_SIZE_DEFAULT must be >= BATCH_SIZE_MIN"
            assert cls.BATCH_SIZE_DEFAULT <= cls.BATCH_SIZE_MAX, "BATCH_SIZE_DEFAULT must be <= BATCH_SIZE_MAX"
            
            # Validate timing parameters
            assert cls.SCAN_INTERVAL_SECONDS > 0, "SCAN_INTERVAL_SECONDS must be positive"
            assert cls.TIMEOUT_SECONDS > 0, "TIMEOUT_SECONDS must be positive"
            assert cls.QUEUE_LIMIT > 0, "QUEUE_LIMIT must be positive"
            assert cls.THREAD_JOIN_TIMEOUT > 0, "THREAD_JOIN_TIMEOUT must be positive"
            assert cls.EVENT_WAIT_TIMEOUT > 0, "EVENT_WAIT_TIMEOUT must be positive"
            
            # Validate system monitoring thresholds
            assert 0 < cls.CPU_THRESHOLD_LOW <= 100, "CPU_THRESHOLD_LOW must be between 0 and 100"
            assert 0 < cls.CPU_THRESHOLD_HIGH <= 100, "CPU_THRESHOLD_HIGH must be between 0 and 100"
            assert cls.CPU_THRESHOLD_LOW < cls.CPU_THRESHOLD_HIGH, "CPU_THRESHOLD_LOW must be < CPU_THRESHOLD_HIGH"
            assert 0 < cls.MEMORY_THRESHOLD <= 100, "MEMORY_THRESHOLD must be between 0 and 100"
            
            # Validate file scanning parameters
            assert cls.DEFAULT_SCAN_DAYS > 0, "DEFAULT_SCAN_DAYS must be positive"
            assert cls.BUFFER_SECONDS >= 0, "BUFFER_SECONDS must be non-negative"
            assert cls.N_FILES_FOR_ESTIMATE > 0, "N_FILES_FOR_ESTIMATE must be positive"
            
            return True
            
        except AssertionError as e:
            logging.error(f"Configuration validation failed: {e}")
            return False


# Validate configuration on import
if not SchedulerConfig.validate_config():
    raise ValueError("Invalid scheduler configuration detected. Please check the configuration values.")