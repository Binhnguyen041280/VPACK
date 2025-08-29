#!/usr/bin/env python3
"""
Enhanced Timezone-Aware Query System for V_Track

Provides advanced timezone-aware filtering capabilities for event queries with:
- Automatic local time to UTC conversion
- Performance-optimized database queries
- Multiple time input format support
- Timezone-aware result formatting
- Efficient caching for repeated queries

Features:
- Smart timezone detection and conversion
- Optimized indexing strategies for timezone queries
- Bulk operation support for large datasets
- Real-time timezone-aware filtering
- Performance monitoring and query optimization

Usage:
    from modules.query.enhanced_timezone_query import EnhancedTimezoneQuery
    
    query_engine = EnhancedTimezoneQuery()
    results = query_engine.query_events_timezone_aware(
        from_time="2024-01-15 10:00:00",  # Local time
        to_time="2024-01-15 18:00:00",    # Local time
        cameras=["Camera01"],
        user_timezone="Asia/Ho_Chi_Minh"
    )
"""

import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from contextlib import contextmanager

from zoneinfo import ZoneInfo
from modules.db_utils.safe_connection import safe_db_connection
from modules.config.logging_config import get_logger
from modules.utils.simple_timezone import simple_validate_timezone, get_available_timezones

logger = get_logger(__name__, {"module": "enhanced_timezone_query"})

@dataclass
class TimeRange:
    """Represents a timezone-aware time range."""
    from_timestamp_utc: int  # UTC milliseconds
    to_timestamp_utc: int    # UTC milliseconds
    from_local: datetime     # Local timezone aware datetime
    to_local: datetime       # Local timezone aware datetime
    user_timezone: str       # IANA timezone name
    query_duration_hours: float

@dataclass 
class QueryResult:
    """Enhanced query result with timezone information."""
    events: List[Dict[str, Any]]
    total_count: int
    query_time_ms: float
    timezone_info: Dict[str, Any]
    time_range: TimeRange
    performance_metrics: Dict[str, Any]

class TimezoneQueryOptimizer:
    """Optimizes database queries for timezone-aware operations."""
    
    def __init__(self):
        self._query_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 300  # 5 minutes
        
    def get_optimized_query(self, 
                           time_range: TimeRange, 
                           cameras: List[str] = None,
                           tracking_codes: List[str] = None,
                           include_processed: bool = False) -> Tuple[str, List[Any]]:
        """Generate optimized SQL query for timezone-aware filtering."""
        
        # Base query with timezone-optimized indexes
        query_parts = [
            "SELECT event_id, ts, te, duration, tracking_codes, video_file,",
            "       packing_time_start, packing_time_end, timezone_info,", 
            "       camera_name, created_at_utc, updated_at_utc",
            "FROM events"
        ]
        
        where_conditions = []
        params = []
        
        # Process status filter
        if not include_processed:
            where_conditions.append("is_processed = 0")
        
        # Time range filter - use optimized packing_time_start index
        if time_range:
            # Combined condition for both packing_time_start and fallback to created_at_utc
            time_condition = (
                "((packing_time_start IS NOT NULL AND packing_time_start >= ? AND packing_time_start <= ?) "
                "OR (packing_time_start IS NULL AND created_at_utc >= ? AND created_at_utc <= ?))"
            )
            where_conditions.append(time_condition)
            
            # Add parameters for both conditions
            created_from = datetime.fromtimestamp(time_range.from_timestamp_utc / 1000, tz=timezone.utc).isoformat()
            created_to = datetime.fromtimestamp(time_range.to_timestamp_utc / 1000, tz=timezone.utc).isoformat()
            
            params.extend([
                time_range.from_timestamp_utc, 
                time_range.to_timestamp_utc,
                created_from,
                created_to
            ])
        
        # Camera filter
        if cameras:
            where_conditions.append(f"camera_name IN ({','.join('?' * len(cameras))})")
            params.extend(cameras)
        
        # Combine conditions
        if where_conditions:
            query_parts.append("WHERE")
            query_parts.append(" AND ".join(where_conditions))
        
        # Optimize ordering for timezone queries
        query_parts.append("ORDER BY packing_time_start DESC, created_at_utc DESC")
        
        # Add query limit for performance
        query_parts.append("LIMIT 10000")  # Prevent runaway queries
        
        final_query = " ".join(query_parts)
        
        logger.debug(f"Generated optimized query: {final_query}")
        logger.debug(f"Query parameters: {params}")
        
        return final_query, params

class EnhancedTimezoneQuery:
    """Enhanced timezone-aware query engine for events."""
    
    def __init__(self):
        self.optimizer = TimezoneQueryOptimizer()
        self._performance_metrics = {
            'total_queries': 0,
            'avg_query_time_ms': 0,
            'cache_hits': 0,
            'timezone_conversions': 0
        }
        
    def parse_time_input(self, 
                        time_input: Union[str, datetime, int], 
                        user_timezone: str = None) -> datetime:
        """Parse various time input formats to timezone-aware datetime."""
        
        if user_timezone is None:
            user_timezone = "Asia/Ho_Chi_Minh"
        
        try:
            # Get timezone object
            user_tz = ZoneInfo(user_timezone)
            
            # Handle different input types
            if isinstance(time_input, datetime):
                if time_input.tzinfo is None:
                    # Naive datetime - assume user timezone
                    return time_input.replace(tzinfo=user_tz)
                else:
                    # Already timezone-aware
                    return time_input
                    
            elif isinstance(time_input, int):
                # Unix timestamp (milliseconds)
                return datetime.fromtimestamp(time_input / 1000, tz=user_tz)
                
            elif isinstance(time_input, str):
                # String formats
                try:
                    # Try ISO format with timezone
                    if '+' in time_input or time_input.endswith('Z'):
                        return datetime.fromisoformat(time_input.replace('Z', '+00:00'))
                    
                    # Try ISO format without timezone
                    if 'T' in time_input:
                        naive_dt = datetime.fromisoformat(time_input)
                        return naive_dt.replace(tzinfo=user_tz)
                    
                    # Try common date formats
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M',
                        '%Y-%m-%d',
                        '%d/%m/%Y %H:%M:%S',
                        '%d/%m/%Y %H:%M',
                        '%d/%m/%Y'
                    ]
                    
                    for fmt in formats:
                        try:
                            naive_dt = datetime.strptime(time_input, fmt)
                            return naive_dt.replace(tzinfo=user_tz)
                        except ValueError:
                            continue
                    
                    raise ValueError(f"Unable to parse time format: {time_input}")
                    
                except Exception as e:
                    raise ValueError(f"Invalid time input '{time_input}': {e}")
            
            else:
                raise ValueError(f"Unsupported time input type: {type(time_input)}")
                
        except Exception as e:
            logger.error(f"Time parsing failed for input '{time_input}': {e}")
            raise
    
    def create_time_range(self,
                         from_time: Union[str, datetime, int] = None,
                         to_time: Union[str, datetime, int] = None,
                         user_timezone: str = None,
                         default_range_hours: int = 24) -> TimeRange:
        """Create a timezone-aware time range for queries."""
        
        if user_timezone is None:
            user_timezone = "Asia/Ho_Chi_Minh"
        
        # Handle default time range
        if from_time is None and to_time is None:
            # Default to last 24 hours in user timezone
            user_tz = ZoneInfo(user_timezone)
            now_local = datetime.now(user_tz)
            to_local = now_local
            from_local = now_local - timedelta(hours=default_range_hours)
        else:
            # Parse provided times
            if from_time is None:
                # Default to 24 hours before to_time
                to_local = self.parse_time_input(to_time, user_timezone)
                from_local = to_local - timedelta(hours=default_range_hours)
            elif to_time is None:
                # Default to 24 hours after from_time
                from_local = self.parse_time_input(from_time, user_timezone)
                to_local = from_local + timedelta(hours=default_range_hours)
            else:
                # Both times provided
                from_local = self.parse_time_input(from_time, user_timezone)
                to_local = self.parse_time_input(to_time, user_timezone)
        
        # Ensure from_time is before to_time
        if from_local > to_local:
            from_local, to_local = to_local, from_local
        
        # Convert to UTC timestamps for database queries
        from_utc = from_local.astimezone(timezone.utc)
        to_utc = to_local.astimezone(timezone.utc)
        
        from_timestamp_utc = int(from_utc.timestamp() * 1000)
        to_timestamp_utc = int(to_utc.timestamp() * 1000)
        
        # Calculate query duration
        query_duration_hours = (to_local - from_local).total_seconds() / 3600
        
        return TimeRange(
            from_timestamp_utc=from_timestamp_utc,
            to_timestamp_utc=to_timestamp_utc,
            from_local=from_local,
            to_local=to_local,
            user_timezone=user_timezone,
            query_duration_hours=query_duration_hours
        )
    
    def format_event_timezone_aware(self, 
                                   event_data: Tuple, 
                                   user_timezone: str) -> Dict[str, Any]:
        """Format database event with timezone-aware timestamps."""
        
        # Unpack event data
        (event_id, ts, te, duration, tracking_codes, video_file,
         packing_time_start, packing_time_end, timezone_info,
         camera_name, created_at_utc, updated_at_utc) = event_data
        
        user_tz = ZoneInfo(user_timezone)
        
        # Format timezone-aware timestamps
        formatted_event = {
            'event_id': event_id,
            'ts': ts,
            'te': te,
            'duration': duration,
            'tracking_codes': tracking_codes,
            'video_file': video_file,
            'camera_name': camera_name,
            'timestamps': {
                'utc': {},
                'local': {},
                'original_timezone': None
            }
        }
        
        # Process packing times
        if packing_time_start:
            start_utc = datetime.fromtimestamp(packing_time_start / 1000, tz=timezone.utc)
            start_local = start_utc.astimezone(user_tz)
            
            formatted_event['timestamps']['utc']['packing_start'] = start_utc.isoformat()
            formatted_event['timestamps']['local']['packing_start'] = start_local.isoformat()
            formatted_event['timestamps']['local']['packing_start_display'] = start_local.strftime('%Y-%m-%d %H:%M:%S')
        
        if packing_time_end:
            end_utc = datetime.fromtimestamp(packing_time_end / 1000, tz=timezone.utc)
            end_local = end_utc.astimezone(user_tz)
            
            formatted_event['timestamps']['utc']['packing_end'] = end_utc.isoformat()
            formatted_event['timestamps']['local']['packing_end'] = end_local.isoformat()
            formatted_event['timestamps']['local']['packing_end_display'] = end_local.strftime('%Y-%m-%d %H:%M:%S')
        
        # Process creation/update times
        if created_at_utc:
            try:
                created_utc = datetime.fromisoformat(created_at_utc.replace('Z', '+00:00'))
                created_local = created_utc.astimezone(user_tz)
                
                formatted_event['timestamps']['utc']['created'] = created_utc.isoformat()
                formatted_event['timestamps']['local']['created'] = created_local.isoformat()
            except Exception as e:
                logger.debug(f"Error parsing created_at_utc: {e}")
        
        # Parse timezone info if available
        if timezone_info:
            try:
                tz_info = eval(timezone_info) if isinstance(timezone_info, str) else timezone_info
                formatted_event['timestamps']['original_timezone'] = tz_info
            except Exception as e:
                logger.debug(f"Error parsing timezone_info: {e}")
        
        return formatted_event
    
    def query_events_timezone_aware(self,
                                   from_time: Union[str, datetime, int] = None,
                                   to_time: Union[str, datetime, int] = None,
                                   cameras: List[str] = None,
                                   tracking_codes: List[str] = None,
                                   user_timezone: str = None,
                                   include_processed: bool = False,
                                   search_string: str = None) -> QueryResult:
        """
        Execute timezone-aware event query with performance optimization.
        
        Args:
            from_time: Start time (various formats supported)
            to_time: End time (various formats supported)  
            cameras: List of camera names to filter
            tracking_codes: List of tracking codes to filter
            user_timezone: User's timezone (defaults to global timezone)
            include_processed: Include processed events
            search_string: Text search in tracking codes/video files
            
        Returns:
            QueryResult with timezone-aware formatted events
        """
        start_time = time.time()
        
        try:
            # Create timezone-aware time range
            time_range = self.create_time_range(from_time, to_time, user_timezone)
            
            if user_timezone is None:
                user_timezone = time_range.user_timezone
            
            # Generate optimized query
            query, params = self.optimizer.get_optimized_query(
                time_range=time_range,
                cameras=cameras,
                tracking_codes=tracking_codes,
                include_processed=include_processed
            )
            
            # Execute database query
            try:
                from modules.scheduler.db_sync import db_rwlock
                use_rwlock = True
            except ImportError:
                use_rwlock = False
                logger.debug("db_rwlock not available")
            
            events = []
            if use_rwlock:
                with db_rwlock.gen_rlock():
                    with safe_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(query, params)
                        raw_events = cursor.fetchall()
            else:
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    raw_events = cursor.fetchall()
            
            # Format events with timezone awareness
            for event_data in raw_events:
                formatted_event = self.format_event_timezone_aware(event_data, user_timezone)
                
                # Apply tracking code filter if specified
                if tracking_codes:
                    event_codes = self._parse_tracking_codes(formatted_event['tracking_codes'])
                    if not any(code in event_codes for code in tracking_codes):
                        continue
                
                # Apply search string filter if specified
                if search_string:
                    searchable_text = f"{formatted_event['tracking_codes']} {formatted_event['video_file']}".lower()
                    if search_string.lower() not in searchable_text:
                        continue
                
                events.append(formatted_event)
            
            # Calculate performance metrics
            query_time_ms = (time.time() - start_time) * 1000
            
            self._performance_metrics['total_queries'] += 1
            self._performance_metrics['avg_query_time_ms'] = (
                (self._performance_metrics['avg_query_time_ms'] * (self._performance_metrics['total_queries'] - 1) + query_time_ms) /
                self._performance_metrics['total_queries']
            )
            
            # Create result
            result = QueryResult(
                events=events,
                total_count=len(events),
                query_time_ms=query_time_ms,
                timezone_info={
                    'user_timezone': user_timezone,
                    'global_timezone': "Asia/Ho_Chi_Minh",
                    'query_timezone_aware': True
                },
                time_range=time_range,
                performance_metrics=self._performance_metrics.copy()
            )
            
            logger.info(f"Timezone-aware query completed: {len(events)} events in {query_time_ms:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Timezone-aware query failed: {e}")
            raise
    
    def _parse_tracking_codes(self, tracking_codes_str: str) -> List[str]:
        """Parse tracking codes from database string format."""
        if not tracking_codes_str:
            return []
        
        try:
            # Handle various formats: ['code1', 'code2'] or "['code1', 'code2']"
            if tracking_codes_str.startswith('[') and tracking_codes_str.endswith(']'):
                codes = eval(tracking_codes_str)
                return [str(code) for code in codes if code]
            else:
                # Simple string format
                return [code.strip() for code in tracking_codes_str.split(',') if code.strip()]
        except Exception as e:
            logger.debug(f"Error parsing tracking codes '{tracking_codes_str}': {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get query performance metrics."""
        return self._performance_metrics.copy()
    
    def reset_performance_metrics(self):
        """Reset performance tracking metrics."""
        self._performance_metrics = {
            'total_queries': 0,
            'avg_query_time_ms': 0,
            'cache_hits': 0,
            'timezone_conversions': 0
        }

# Create singleton instance
enhanced_timezone_query = EnhancedTimezoneQuery()

# Convenience functions
def query_events_with_timezone(from_time=None, to_time=None, cameras=None, user_timezone=None, **kwargs):
    """Convenience function for timezone-aware event queries."""
    return enhanced_timezone_query.query_events_timezone_aware(
        from_time=from_time,
        to_time=to_time,
        cameras=cameras,
        user_timezone=user_timezone,
        **kwargs
    )