"""
Safe Database Connection Manager for ePACK
Simple, reliable context manager for SQLite connections
"""

import sqlite3
import time
import logging
import threading
from contextlib import contextmanager
from typing import Generator

from modules.db_utils import get_db_connection

logger = logging.getLogger(__name__)

@contextmanager
def safe_db_connection(timeout: int = 60, retry_attempts: int = 3, retry_delay: float = 0.5) -> Generator[sqlite3.Connection, None, None]:
    """
    Safe database connection context manager with automatic cleanup.
    
    Args:
        timeout: Connection timeout in seconds
        retry_attempts: Number of retry attempts for connection failures
        retry_delay: Delay between retry attempts in seconds
    
    Yields:
        sqlite3.Connection: Database connection object
        
    Raises:
        sqlite3.Error: If connection fails after all retry attempts
    """
    connection = None
    attempt = 0
    
    
    while attempt < retry_attempts:
        try:
            # Get connection with timeout
            connection = get_db_connection()
            connection.execute(f"PRAGMA busy_timeout = {timeout * 1000}")  # Convert to milliseconds
            
            # Test connection with a simple query
            connection.execute("SELECT 1").fetchone()
            
            yield connection
            
            # If we reach here, operation was successful
            connection.commit()
            return
            
        except sqlite3.OperationalError as e:
            attempt += 1
            if connection:
                try:
                    connection.rollback()
                    logger.warning(f"Database transaction rolled back due to error: {e}")
                except:
                    pass
                    
            if attempt >= retry_attempts:
                logger.error(f"Database connection failed after {retry_attempts} attempts: {e}")
                raise sqlite3.Error(f"Failed to connect to database after {retry_attempts} attempts: {e}")
            else:
                logger.warning(f"Database connection attempt {attempt} failed, retrying in {retry_delay}s: {e}")
                time.sleep(retry_delay)
                
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                    logger.warning(f"Database transaction rolled back due to unexpected error: {e}")
                except:
                    pass
            logger.error(f"Unexpected database error: {e}")
            raise sqlite3.Error(f"Unexpected database error: {e}")
            
        finally:
            if connection:
                try:
                    connection.close()
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")


class ConnectionPoolError(Exception):
    """Exception raised for connection pool errors"""
    pass


class SimpleConnectionPool:
    """
    Simple database connection pool for high-frequency operations.
    Manages a pool of reusable connections to reduce connection overhead.
    """
    
    def __init__(self, pool_size: int = 5, max_connections: int = 10, connection_timeout: int = 30):
        """
        Initialize connection pool.
        
        Args:
            pool_size: Number of connections to maintain in pool
            max_connections: Maximum number of connections allowed
            connection_timeout: Timeout for individual connections
        """
        self.pool_size = pool_size
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self._pool = []
        self._active_connections = set()
        self._lock = threading.Lock()
        
        logger.info(f"Initialized connection pool: size={pool_size}, max={max_connections}")
    
    @contextmanager
    def get_pooled_connection(self):
        """
        Get connection from pool with automatic return.
        
        Yields:
            sqlite3.Connection: Database connection from pool
        """
        connection = None
        try:
            with self._lock:
                # Try to get connection from pool
                if self._pool:
                    connection = self._pool.pop()
                    logger.debug("Retrieved connection from pool")
                elif len(self._active_connections) < self.max_connections:
                    connection = get_db_connection()
                    connection.execute(f"PRAGMA busy_timeout = {self.connection_timeout * 1000}")
                    logger.debug("Created new pooled connection")
                else:
                    raise ConnectionPoolError("Connection pool exhausted")
                
                self._active_connections.add(connection)
            
            yield connection
            
        except Exception as e:
            logger.error(f"Error in pooled connection: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise
            
        finally:
            if connection:
                with self._lock:
                    self._active_connections.discard(connection)
                    
                    # Return to pool if pool not full, otherwise close
                    if len(self._pool) < self.pool_size:
                        try:
                            # Reset connection state
                            connection.rollback()
                            self._pool.append(connection)
                            logger.debug("Returned connection to pool")
                        except:
                            # If reset fails, close the connection
                            try:
                                connection.close()
                            except:
                                pass
                            logger.debug("Closed faulty connection")
                    else:
                        try:
                            connection.close()
                            logger.debug("Closed excess connection")
                        except:
                            pass
    
    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            # Close pooled connections
            while self._pool:
                conn = self._pool.pop()
                try:
                    conn.close()
                except:
                    pass
            
            # Close active connections
            for conn in list(self._active_connections):
                try:
                    conn.close()
                except:
                    pass
            self._active_connections.clear()
            
        logger.info("All pooled connections closed")
    
    def get_stats(self):
        """Get connection pool statistics"""
        with self._lock:
            return {
                "pool_size": len(self._pool),
                "active_connections": len(self._active_connections),
                "max_connections": self.max_connections
            }


# Global connection pool instance (optional usage)
_global_pool = None

def get_connection_pool() -> SimpleConnectionPool:
    """Get or create global connection pool"""
    global _global_pool
    if _global_pool is None:
        _global_pool = SimpleConnectionPool()
    return _global_pool
