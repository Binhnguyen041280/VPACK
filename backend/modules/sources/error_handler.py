#!/usr/bin/env python3
"""
V_Track Error Handler Module
Centralized error handling with retry mechanisms, exponential backoff, and error classification
"""

import functools
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error classification for different handling strategies"""

    CRITICAL = "critical"  # Stop sync immediately
    RECOVERABLE = "recoverable"  # Retry with backoff
    WARNING = "warning"  # Log and continue
    NETWORK = "network"  # Network-specific handling
    OAUTH = "oauth"  # OAuth-specific handling
    DATABASE = "database"  # Database-specific handling
    FILE_OPERATION = "file_op"  # File operation handling
    QUOTA = "quota"  # API quota/limit errors


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class VTrackError(Exception):
    """Base exception class for V_Track errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Dict = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.now()


class NetworkError(VTrackError):
    """Network-related errors"""

    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, ErrorType.NETWORK, ErrorSeverity.MEDIUM, details)


class OAuthError(VTrackError):
    """OAuth authentication errors"""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, details: Dict = None
    ):
        super().__init__(message, ErrorType.OAUTH, severity, details)


class DatabaseError(VTrackError):
    """Database operation errors"""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, details: Dict = None
    ):
        super().__init__(message, ErrorType.DATABASE, severity, details)


class FileOperationError(VTrackError):
    """File operation errors"""

    def __init__(
        self, message: str, severity: ErrorSeverity = ErrorSeverity.LOW, details: Dict = None
    ):
        super().__init__(message, ErrorType.FILE_OPERATION, severity, details)


class RetryConfig:
    """Configuration for retry mechanisms"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter


class ErrorHandler:
    """Centralized error handler with retry mechanisms"""

    # Default configurations for different error types
    NETWORK_CONFIG = RetryConfig(max_retries=3, base_delay=2.0, max_delay=60.0)
    OAUTH_CONFIG = RetryConfig(max_retries=2, base_delay=10.0, max_delay=300.0)
    DATABASE_CONFIG = RetryConfig(max_retries=5, base_delay=1.0, max_delay=30.0)
    FILE_CONFIG = RetryConfig(max_retries=3, base_delay=5.0, max_delay=120.0)
    QUOTA_CONFIG = RetryConfig(
        max_retries=2, base_delay=60.0, max_delay=600.0
    )  # Longer delays for quota

    def __init__(self):
        self.error_counts = {}  # Track error frequencies
        self.last_errors = {}  # Track last error times
        self.cooldown_until = {}  # Track cooldown periods

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error based on exception type and message"""
        error_msg = str(error).lower()

        # Network errors
        if any(
            keyword in error_msg
            for keyword in [
                "timeout",
                "connection",
                "network",
                "unreachable",
                "dns",
                "socket",
                "httperror",
                "connectionerror",
            ]
        ):
            return ErrorType.NETWORK

        # Signal threading error - should be classified specifically
        elif "signal only works in main thread" in error_msg:
            return ErrorType.FILE_OPERATION

        # OAuth errors
        elif any(
            keyword in error_msg
            for keyword in [
                "oauth",
                "token",
                "credentials",
                "unauthorized",
                "invalid_grant",
                "access_denied",
                "authentication",
            ]
        ):
            return ErrorType.OAUTH

        # Quota/limit errors
        elif any(
            keyword in error_msg
            for keyword in ["quota", "limit", "exceeded", "rate limit", "too many requests"]
        ):
            return ErrorType.QUOTA

        # Database errors
        elif any(
            keyword in error_msg
            for keyword in [
                "database is locked",
                "sqlite",
                "no such table",
                "constraint",
                "database",
                "operational error",
            ]
        ):
            return ErrorType.DATABASE

        # File operation errors
        elif any(
            keyword in error_msg
            for keyword in [
                "permission denied",
                "no space left",
                "file not found",
                "directory",
                "disk",
                "io error",
                "file size mismatch",
            ]
        ):
            return ErrorType.FILE_OPERATION

        # Recoverable network error
        elif "recoverable" in error_msg.lower():
            return ErrorType.NETWORK

        # Default to network for download-related errors
        elif any(keyword in error_msg for keyword in ["download", "upload", "transfer"]):
            return ErrorType.NETWORK

        # Default to recoverable
        return ErrorType.RECOVERABLE

    def should_retry(self, error_type: ErrorType, attempt: int, source_id: int = None) -> bool:
        """Determine if error should be retried"""
        key = f"{error_type.value}_{source_id or 'global'}"

        # Check if in cooldown period
        if key in self.cooldown_until:
            if datetime.now() < self.cooldown_until[key]:
                logger.warning(f"🕒 In cooldown period for {error_type.value}, skipping retry")
                return False

        # Get max retries for error type
        config = self._get_retry_config(error_type)

        if attempt >= config.max_retries:
            logger.error(f"❌ Max retries ({config.max_retries}) exceeded for {error_type.value}")
            return False

        return True

    def calculate_delay(self, error_type: ErrorType, attempt: int) -> float:
        """Calculate delay before next retry using exponential backoff"""
        config = self._get_retry_config(error_type)

        # Exponential backoff
        delay = config.base_delay * (config.backoff_multiplier**attempt)
        delay = min(delay, config.max_delay)

        # Add jitter to prevent thundering herd
        if config.jitter:
            import random

            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def _get_retry_config(self, error_type: ErrorType) -> RetryConfig:
        """Get retry configuration for error type"""
        config_map = {
            ErrorType.NETWORK: self.NETWORK_CONFIG,
            ErrorType.OAUTH: self.OAUTH_CONFIG,
            ErrorType.DATABASE: self.DATABASE_CONFIG,
            ErrorType.FILE_OPERATION: self.FILE_CONFIG,
            ErrorType.QUOTA: self.QUOTA_CONFIG,
        }
        return config_map.get(error_type, self.NETWORK_CONFIG)

    def handle_error(
        self, error: Exception, context: Dict = None, source_id: int = None
    ) -> Dict[str, Any]:
        """Handle error with appropriate strategy"""
        error_type = self.classify_error(error)
        context = context or {}

        # Track error frequency
        key = f"{error_type.value}_{source_id or 'global'}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.last_errors[key] = datetime.now()

        # Log error with context
        logger.error(f"❌ {error_type.value.upper()} ERROR: {str(error)}")
        if context:
            logger.error(f"📋 Context: {context}")

        # Determine action based on error type and frequency
        action = self._determine_action(error_type, error, key)

        return {
            "error_type": error_type.value,
            "message": str(error),
            "action": action,
            "should_retry": action == "retry",
            "should_stop": action == "stop",
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "error_count": self.error_counts[key],
        }

    def _determine_action(self, error_type: ErrorType, error: Exception, key: str) -> str:
        """Determine action based on error type and frequency"""
        error_count = self.error_counts.get(key, 0)

        # Critical errors always stop
        if error_type == ErrorType.CRITICAL:
            return "stop"

        # Too many consecutive errors trigger cooldown
        if error_count >= 5:
            self.cooldown_until[key] = datetime.now() + timedelta(minutes=30)
            logger.warning(f"⏸️ Entering 30-minute cooldown for {error_type.value}")
            return "cooldown"

        # OAuth errors need special handling
        if error_type == ErrorType.OAUTH:
            if "invalid_grant" in str(error).lower():
                return "reauth_required"
            return "retry"

        # Network errors are usually retryable
        if error_type == ErrorType.NETWORK:
            return "retry"

        # Database errors are retryable with short delay
        if error_type == ErrorType.DATABASE:
            return "retry"

        # File operation errors might be skippable
        if error_type == ErrorType.FILE_OPERATION:
            return "skip"

        return "retry"

    def reset_error_count(self, error_type: ErrorType = None, source_id: int = None):
        """Reset error count for successful operations"""
        if error_type and source_id:
            key = f"{error_type.value}_{source_id}"
            self.error_counts.pop(key, None)
            self.cooldown_until.pop(key, None)
        else:
            # Reset all counts
            self.error_counts.clear()
            self.cooldown_until.clear()

        logger.info("✅ Error counts reset - successful operation")


def with_retry(error_types: List[ErrorType] = None, max_retries: int = 3):
    """Decorator for automatic retry with error handling"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler()
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    # Reset error count on success
                    if attempt > 0:
                        handler.reset_error_count()
                    return result

                except Exception as e:
                    last_error = e
                    error_type = handler.classify_error(e)

                    # Check if this error type should be retried
                    if error_types and error_type not in error_types:
                        logger.error(
                            f"❌ Error type {error_type.value} not in retry list, raising immediately"
                        )
                        raise

                    if attempt < max_retries:
                        if handler.should_retry(error_type, attempt):
                            delay = handler.calculate_delay(error_type, attempt)
                            logger.warning(
                                f"⏳ Retry attempt {attempt + 1}/{max_retries} in {delay:.1f}s: {str(e)}"
                            )
                            time.sleep(delay)
                        else:
                            break
                    else:
                        logger.error(f"❌ All retry attempts exhausted for {func.__name__}")
                        break

            # If we get here, all retries failed
            raise last_error

        return wrapper

    return decorator


# Global error handler instance
error_handler = ErrorHandler()


# Convenience functions
def handle_network_error(error: Exception, context: Dict = None) -> Dict:
    """Handle network-specific errors"""
    return error_handler.handle_error(NetworkError(str(error), context), context)


def handle_oauth_error(error: Exception, context: Dict = None) -> Dict:
    """Handle OAuth-specific errors"""
    return error_handler.handle_error(OAuthError(str(error), details=context), context)


def handle_database_error(error: Exception, context: Dict = None) -> Dict:
    """Handle database-specific errors"""
    return error_handler.handle_error(DatabaseError(str(error), details=context), context)


def handle_file_error(error: Exception, context: Dict = None) -> Dict:
    """Handle file operation errors"""
    return error_handler.handle_error(FileOperationError(str(error), details=context), context)
