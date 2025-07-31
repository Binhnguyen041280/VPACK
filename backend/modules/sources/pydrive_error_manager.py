#!/usr/bin/env python3
"""
Simplified PyDriveErrorManager for VTrack
Focus: Essential error recovery only, no complex user communication
"""

import logging
import socket
import time
import threading
from typing import Dict, Callable
from enum import Enum

logger = logging.getLogger(__name__)

class SimpleErrorType(Enum):
    """Simplified error types - just what we need for recovery"""
    NETWORK = "network"
    AUTH = "auth" 
    QUOTA = "quota"
    OTHER = "other"

class PyDriveErrorManager:
    """
    Simplified error manager - focus on recovery, not communication
    No complex notifications, no user messages, just reliable recovery
    """
    
    def __init__(self):
        self.error_counts = {}  # Simple error counting
        logger.info("🛡️ Simplified PyDriveErrorManager initialized")
    
    def handle_with_retry(self, operation: Callable, source_id: int, max_retries: int = 2) -> Dict:
        """Simple retry mechanism - no complex strategies"""
        for attempt in range(max_retries):
            try:
                result = operation()
                # Success - reset error count
                self.error_counts.pop(source_id, None)
                return {'success': True, 'result': result}
                
            except Exception as e:
                # Classify error simply
                error_type = self._classify_simple_error(str(e))
                
                # Track error count
                self.error_counts[source_id] = self.error_counts.get(source_id, 0) + 1
                
                # Log error
                logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries} failed for source {source_id}: {e}")
                
                # Simple retry logic
                if attempt < max_retries - 1:
                    if error_type == SimpleErrorType.NETWORK:
                        # Wait for network issues
                        time.sleep(30)
                    elif error_type == SimpleErrorType.QUOTA:
                        # Wait longer for quota
                        time.sleep(60) 
                    else:
                        # Short wait for other errors
                        time.sleep(10)
                    continue
                else:
                    # Final failure
                    return {
                        'success': False, 
                        'error_type': error_type.value,
                        'message': str(e)
                    }
        
        return {'success': False, 'message': 'Max retries exceeded'}
    
    def _classify_simple_error(self, error_str: str) -> SimpleErrorType:
        """Simple error classification"""
        error_lower = error_str.lower()
        
        if any(keyword in error_lower for keyword in ['network', 'timeout', 'connection', 'dns']):
            return SimpleErrorType.NETWORK
        elif any(keyword in error_lower for keyword in ['oauth', 'token', 'unauthorized', 'auth']):
            return SimpleErrorType.AUTH
        elif any(keyword in error_lower for keyword in ['quota', 'limit', 'rate']):
            return SimpleErrorType.QUOTA
        else:
            return SimpleErrorType.OTHER
    
    def check_network_connectivity(self, timeout: int = 5) -> bool:
        """Simple network check"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except (socket.timeout, socket.error, OSError):
            return False
    
    def get_error_count(self, source_id: int) -> int:
        """Get simple error count"""
        return self.error_counts.get(source_id, 0)
    
    def reset_error_count(self, source_id: int):
        """Reset error count on success"""
        self.error_counts.pop(source_id, None)