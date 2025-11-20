# backend/modules/licensing/repositories/base_repository.py
"""
Base Repository Pattern - Foundation for V_Track License System
Eliminates duplicate database patterns found in 8+ locations
Created: 2025-08-11 - Phase 1 Refactoring
"""

import sqlite3
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

# Import database utilities with proper error handling
try:
    from modules.db_utils import get_db_connection
    from modules.db_utils.safe_connection import safe_db_connection
except ImportError as e:
    import sys
    import os
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Critical: Cannot import database utilities: {e}")
    logger.error("💡 Ensure you're running from backend/ directory:")
    logger.error("   cd /Users/annhu/vtrack_app/V_Track/backend")
    logger.error("   python3 your_script.py")
    logger.error("📁 Current working directory: %s", os.getcwd())
    logger.error("🐍 Python path: %s", sys.path[:3])
    raise ImportError("Database utilities not found. Check PYTHONPATH and working directory.")

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom database error for better error handling"""
    pass

class BaseRepository(ABC):
    """
    Base repository pattern for all database operations
    Eliminates duplicate patterns found across license system
    """
    
    def __init__(self):
        """Initialize base repository"""
        self._connection_tested = False
    
    def _test_connection(self) -> bool:
        """Test database connection - run once per instance"""
        if self._connection_tested:
            return True
            
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self._connection_tested = (result is not None)
                
                if self._connection_tested:
                    pass
                else:
                    logger.error("❌ Database connection test failed")
                    
                return self._connection_tested
                
        except Exception as e:
            logger.error(f"❌ Database connection error: {str(e)}")
            return False
    
    def _get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a table - UNIFIED PATTERN
        ELIMINATES: 8 duplicate PRAGMA table_info calls
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                if not columns:
                    raise DatabaseError(f"Table '{table_name}' not found or has no columns")
                
                return columns
                
        except Exception as e:
            logger.error(f"❌ Failed to get columns for table '{table_name}': {str(e)}")
            raise DatabaseError(f"Column retrieval failed: {str(e)}")
    
    def _row_to_dict(self, row: Tuple, table_name: str) -> Dict[str, Any]:
        """
        Convert database row to dictionary - UNIFIED PATTERN
        ELIMINATES: 6 duplicate row-to-dict conversions
        
        Args:
            row: Database row tuple
            table_name: Name of table for column mapping
            
        Returns:
            dict: Row data as dictionary
        """
        if not row:
            return {}
            
        try:
            columns = self._get_table_columns(table_name)
            
            if len(row) != len(columns):
                logger.warning(f"⚠️ Row length ({len(row)}) != columns length ({len(columns)}) for table '{table_name}'")
                # Handle partial rows
                min_length = min(len(row), len(columns))
                columns = columns[:min_length]
                row = row[:min_length]
            
            result = dict(zip(columns, row))
            return result
            
        except Exception as e:
            logger.error(f"❌ Row to dict conversion failed: {str(e)}")
            raise DatabaseError(f"Row conversion failed: {str(e)}")
    
    def _parse_json_field(self, data: Dict[str, Any], field_name: str, default: Any = None) -> Any:
        """
        Parse JSON field with fallback - UNIFIED PATTERN
        ELIMINATES: 4 duplicate JSON parsing blocks
        
        Args:
            data: Dictionary containing the field
            field_name: Name of JSON field to parse
            default: Default value if parsing fails
            
        Returns:
            Parsed JSON data or default value
        """
        try:
            field_value = data.get(field_name)
            
            if not field_value:
                return default
            
            # Already parsed
            if not isinstance(field_value, str):
                return field_value
            
            # Parse JSON string
            parsed_data = json.loads(field_value)
            return parsed_data
            
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"⚠️ JSON parsing failed for field '{field_name}': {str(e)}")
            return default
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing JSON field '{field_name}': {str(e)}")
            return default
    
    def _execute_query_with_result(self, query: str, params: Tuple = (), 
                                 table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return list of dictionaries - UNIFIED PATTERN
        ELIMINATES: Multiple query execution patterns
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            table_name: Table name for column mapping (auto-detect if None)
            
        Returns:
            List of dictionaries representing rows
        """
        try:
            if not self._test_connection():
                raise DatabaseError("Database connection not available")
            
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                if not rows:
                    return []
                
                # Auto-detect table name from query if not provided
                if not table_name:
                    table_name = self._extract_table_name_from_query(query)
                
                if not table_name:
                    logger.warning("⚠️ Could not determine table name, returning raw tuples")
                    # Convert to List[Dict[str, Any]] for type consistency
                    return [{str(i): val for i, val in enumerate(row)} for row in rows]
                
                # Convert all rows to dictionaries
                results = []
                for row in rows:
                    row_dict = self._row_to_dict(row, table_name)
                    results.append(row_dict)
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error: {str(e)}")
            raise DatabaseError(f"Database query failed: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Query execution error: {str(e)}")
            raise DatabaseError(f"Query execution failed: {str(e)}")
    
    def _execute_query_single(self, query: str, params: Tuple = (), 
                            table_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Execute query and return single result as dictionary
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            table_name: Table name for column mapping
            
        Returns:
            Single row as dictionary or None if not found
        """
        results = self._execute_query_with_result(query, params, table_name)
        return results[0] if results else None
    
    def _execute_insert_update(self, query: str, params: Tuple = ()) -> Union[int, bool]:
        """
        Execute INSERT/UPDATE/DELETE query - UNIFIED PATTERN
        ELIMINATES: Scattered transaction handling
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            
        Returns:
            lastrowid for INSERT, rowcount > 0 for UPDATE/DELETE
        """
        try:
            # Validate query is not None before string operations
            if query is None:
                logger.error("❌ Query is None - cannot execute")
                raise DatabaseError("Query parameter cannot be None")

            if not self._test_connection():
                raise DatabaseError("Database connection not available")

            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

                # Determine operation type
                operation = query.strip().upper()
                
                if operation.startswith('INSERT'):
                    result = cursor.lastrowid
                    conn.commit()
                    # Ensure we return int, not int | None
                    return result if result is not None else 0
                elif operation.startswith(('UPDATE', 'DELETE')):
                    affected_rows = cursor.rowcount
                    conn.commit()
                    success = affected_rows > 0
                    return success
                else:
                    conn.commit()
                    return True
                    
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ Database integrity error: {str(e)}")
            raise DatabaseError(f"Integrity constraint violation: {str(e)}")
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            raise DatabaseError(f"Unexpected database error: {str(e)}")
    
    def _extract_table_name_from_query(self, query: str) -> Optional[str]:
        """
        Extract table name from SQL query - simple pattern matching
        
        Args:
            query: SQL query string
            
        Returns:
            Table name if detected, None otherwise
        """
        try:
            query_upper = query.upper().strip()
            
            # Handle SELECT queries
            if query_upper.startswith('SELECT'):
                from_index = query_upper.find(' FROM ')
                if from_index != -1:
                    after_from = query_upper[from_index + 6:].strip()
                    table_name = after_from.split()[0].strip()
                    return table_name.lower()
            
            # Handle INSERT queries
            elif query_upper.startswith('INSERT'):
                into_index = query_upper.find(' INTO ')
                if into_index != -1:
                    after_into = query_upper[into_index + 6:].strip()
                    table_name = after_into.split()[0].strip()
                    return table_name.lower()
            
            # Handle UPDATE queries
            elif query_upper.startswith('UPDATE'):
                parts = query_upper.split()
                if len(parts) >= 2:
                    return parts[1].lower()
            
            # Handle DELETE queries
            elif query_upper.startswith('DELETE'):
                from_index = query_upper.find(' FROM ')
                if from_index != -1:
                    after_from = query_upper[from_index + 6:].strip()
                    table_name = after_from.split()[0].strip()
                    return table_name.lower()
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Could not extract table name from query: {str(e)}")
            return None
    
    def _format_datetime(self, dt: Union[str, datetime, None]) -> Optional[str]:
        """
        Standardize datetime formatting - UNIFIED PATTERN
        ELIMINATES: 3 different datetime handling approaches
        
        Args:
            dt: Datetime in various formats
            
        Returns:
            ISO format string or None
        """
        if not dt:
            return None
            
        try:
            if isinstance(dt, str):
                # Try to parse and reformat
                parsed_dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                return parsed_dt.isoformat()
            elif isinstance(dt, datetime):
                return dt.isoformat()
            else:
                logger.warning(f"⚠️ Unexpected datetime type: {type(dt)}")
                return str(dt)
                
        except Exception as e:
            logger.warning(f"⚠️ Datetime formatting failed: {str(e)}")
            return str(dt) if dt else None
    
    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate that required fields are present and not empty
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            
        Returns:
            True if all required fields are present and valid
        """
        try:
            missing_fields = []
            empty_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
                elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                    empty_fields.append(field)
            
            if missing_fields:
                logger.error(f"❌ Missing required fields: {missing_fields}")
                return False
                
            if empty_fields:
                logger.error(f"❌ Empty required fields: {empty_fields}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Field validation error: {str(e)}")
            return False
    
    # Abstract methods for subclasses
    @abstractmethod
    def get_table_name(self) -> str:
        """Return the primary table name for this repository"""
        pass
    
    @abstractmethod  
    def get_required_fields(self) -> List[str]:
        """Return list of required fields for this repository"""
        pass

class RepositoryError(Exception):
    """General repository error"""
    pass

# Utility functions for backward compatibility
def get_repository_logger(name: str) -> logging.Logger:
    """Get logger for repository classes"""
    return logging.getLogger(f"repository.{name}")

# Test connection on module import
def test_repository_connection() -> bool:
    """Test repository database connection"""
    try:
        temp_repo = type('TempRepo', (BaseRepository,), {
            'get_table_name': lambda self: 'test',
            'get_required_fields': lambda self: []
        })()
        return temp_repo._test_connection()
    except Exception as e:
        logger.error(f"❌ Repository connection test failed: {str(e)}")
        return False

# Module-level initialization
if __name__ != "__main__":
    try:
        connection_ok = test_repository_connection()
        if connection_ok:
            logger.info("✅ Base repository initialized successfully")
        else:
            logger.warning("⚠️ Base repository initialized with connection issues")
    except Exception as e:
        logger.warning(f"⚠️ Base repository initialization warning: {str(e)}")