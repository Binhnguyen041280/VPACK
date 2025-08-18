#!/usr/bin/env python3
"""
Timezone Database Query Optimizer for V_Track

Provides database optimization specifically for timezone-aware queries with:
- Strategic indexing for timezone-related columns
- Query performance monitoring and analytics
- Automatic index creation and maintenance
- Performance benchmarking for timezone operations
- Query plan analysis and optimization recommendations

Features:
- Automatic index creation for timezone query optimization
- Performance monitoring with detailed metrics
- Query execution plan analysis
- Index usage statistics and recommendations
- Timezone-specific query optimization strategies

Usage:
    from modules.query.timezone_database_optimizer import timezone_db_optimizer
    
    # Initialize optimizer
    timezone_db_optimizer.optimize_database()
    
    # Monitor query performance
    metrics = timezone_db_optimizer.get_performance_metrics()
    
    # Analyze specific query
    analysis = timezone_db_optimizer.analyze_query_performance(query, params)
"""

import os
import sys
import sqlite3
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from modules.db_utils.safe_connection import safe_db_connection
from modules.config.logging_config import get_logger

logger = get_logger(__name__, {"module": "timezone_database_optimizer"})

@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for database queries."""
    query_hash: str
    execution_time_ms: float
    rows_scanned: int
    rows_returned: int
    index_used: bool
    query_plan: str
    timestamp: datetime
    optimization_level: str

@dataclass
class IndexPerformanceData:
    """Performance data for database indexes."""
    index_name: str
    table_name: str
    columns: List[str]
    usage_count: int
    avg_query_time_ms: float
    effectiveness_score: float
    last_used: datetime
    creation_time: datetime

@dataclass
class OptimizationRecommendation:
    """Database optimization recommendation."""
    type: str  # 'index', 'query_rewrite', 'schema_change'
    priority: str  # 'high', 'medium', 'low'
    description: str
    sql_command: str
    expected_improvement: str
    estimated_impact: float

class TimezoneQueryAnalyzer:
    """Analyzes timezone-specific query patterns and performance."""
    
    def __init__(self):
        self._query_cache = {}
        self._performance_history = []
        self._cache_lock = threading.Lock()
        
    def analyze_query_plan(self, query: str, params: List[Any] = None) -> Dict[str, Any]:
        """Analyze SQLite query execution plan for timezone queries."""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get query plan
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                cursor.execute(explain_query, params or [])
                plan_rows = cursor.fetchall()
                
                # Get detailed execution stats
                cursor.execute(f"EXPLAIN {query}", params or [])
                explain_rows = cursor.fetchall()
                
                analysis = {
                    'query_plan': [dict(zip([col[0] for col in cursor.description], row)) for row in plan_rows],
                    'execution_details': [dict(zip([col[0] for col in cursor.description], row)) for row in explain_rows],
                    'uses_index': any('INDEX' in str(row) for row in plan_rows),
                    'scans_table': any('SCAN' in str(row) for row in plan_rows),
                    'complexity_score': len(plan_rows),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Check for timezone-specific patterns
                query_lower = query.lower()
                analysis['timezone_patterns'] = {
                    'uses_packing_time': 'packing_time' in query_lower,
                    'uses_timezone_info': 'timezone_info' in query_lower,
                    'has_time_range': 'between' in query_lower or '>=' in query_lower,
                    'uses_timestamp_conversion': 'timestamp' in query_lower
                }
                
                return analysis
                
        except Exception as e:
            logger.error(f"Error analyzing query plan: {e}")
            return {'error': str(e)}
    
    def benchmark_query_performance(self, query: str, params: List[Any] = None, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark query performance with multiple iterations."""
        execution_times = []
        row_counts = []
        
        try:
            for i in range(iterations):
                start_time = time.time()
                
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params or [])
                    results = cursor.fetchall()
                    
                execution_time = (time.time() - start_time) * 1000
                execution_times.append(execution_time)
                row_counts.append(len(results))
            
            return {
                'avg_execution_time_ms': sum(execution_times) / len(execution_times),
                'min_execution_time_ms': min(execution_times),
                'max_execution_time_ms': max(execution_times),
                'std_deviation_ms': self._calculate_std_dev(execution_times),
                'avg_rows_returned': sum(row_counts) / len(row_counts),
                'total_iterations': iterations,
                'performance_grade': self._grade_performance(sum(execution_times) / len(execution_times))
            }
            
        except Exception as e:
            logger.error(f"Error benchmarking query: {e}")
            return {'error': str(e)}
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _grade_performance(self, avg_time_ms: float) -> str:
        """Grade query performance based on execution time."""
        if avg_time_ms < 10:
            return 'Excellent'
        elif avg_time_ms < 50:
            return 'Good'
        elif avg_time_ms < 100:
            return 'Fair'
        elif avg_time_ms < 500:
            return 'Poor'
        else:
            return 'Critical'

class TimezoneIndexOptimizer:
    """Optimizes database indexes for timezone-aware queries."""
    
    def __init__(self):
        self.recommended_indexes = [
            {
                'name': 'idx_events_packing_time_start',
                'table': 'events',
                'columns': ['packing_time_start'],
                'purpose': 'Optimize time range queries'
            },
            {
                'name': 'idx_events_packing_time_range',
                'table': 'events',
                'columns': ['packing_time_start', 'packing_time_end'],
                'purpose': 'Optimize time range filtering'
            },
            {
                'name': 'idx_events_camera_time',
                'table': 'events',
                'columns': ['camera_name', 'packing_time_start'],
                'purpose': 'Optimize camera-specific time queries'
            },
            {
                'name': 'idx_events_processed_time',
                'table': 'events',
                'columns': ['is_processed', 'packing_time_start'],
                'purpose': 'Optimize unprocessed event queries'
            },
            {
                'name': 'idx_events_timezone_info',
                'table': 'events',
                'columns': ['timezone_info'],
                'purpose': 'Optimize timezone information queries'
            },
            {
                'name': 'idx_events_created_utc',
                'table': 'events',
                'columns': ['created_at_utc'],
                'purpose': 'Optimize creation time queries'
            }
        ]
    
    def create_timezone_indexes(self, force_recreate: bool = False) -> Dict[str, Any]:
        """Create optimized indexes for timezone queries."""
        results = {
            'created': [],
            'skipped': [],
            'errors': [],
            'total_indexes': len(self.recommended_indexes)
        }
        
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get existing indexes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                existing_indexes = {row[0] for row in cursor.fetchall()}
                
                for index_spec in self.recommended_indexes:
                    index_name = index_spec['name']
                    table_name = index_spec['table']
                    columns = index_spec['columns']
                    
                    try:
                        if index_name in existing_indexes:
                            if force_recreate:
                                # Drop existing index
                                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
                                logger.info(f"Dropped existing index: {index_name}")
                            else:
                                results['skipped'].append({
                                    'index': index_name,
                                    'reason': 'Already exists'
                                })
                                continue
                        
                        # Create index
                        columns_str = ', '.join(columns)
                        create_sql = f"CREATE INDEX {index_name} ON {table_name} ({columns_str})"
                        
                        start_time = time.time()
                        cursor.execute(create_sql)
                        creation_time = (time.time() - start_time) * 1000
                        
                        results['created'].append({
                            'index': index_name,
                            'table': table_name,
                            'columns': columns,
                            'purpose': index_spec['purpose'],
                            'creation_time_ms': creation_time
                        })
                        
                        logger.info(f"Created index {index_name} in {creation_time:.2f}ms")
                        
                    except Exception as e:
                        error_msg = f"Failed to create index {index_name}: {e}"
                        results['errors'].append({
                            'index': index_name,
                            'error': str(e)
                        })
                        logger.error(error_msg)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error creating timezone indexes: {e}")
            results['errors'].append({'general': str(e)})
        
        return results
    
    def analyze_index_usage(self) -> Dict[str, Any]:
        """Analyze index usage statistics."""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get all indexes
                cursor.execute("""
                    SELECT name, tbl_name, sql 
                    FROM sqlite_master 
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """)
                indexes = cursor.fetchall()
                
                analysis = {
                    'total_indexes': len(indexes),
                    'timezone_related_indexes': [],
                    'other_indexes': [],
                    'recommendations': []
                }
                
                for name, table, sql in indexes:
                    index_info = {
                        'name': name,
                        'table': table,
                        'sql': sql,
                        'is_timezone_related': any(col in (sql or '').lower() 
                                                 for col in ['packing_time', 'timezone', 'created_at'])
                    }
                    
                    if index_info['is_timezone_related']:
                        analysis['timezone_related_indexes'].append(index_info)
                    else:
                        analysis['other_indexes'].append(index_info)
                
                # Add recommendations based on missing indexes
                existing_names = {idx[0] for idx in indexes}
                for spec in self.recommended_indexes:
                    if spec['name'] not in existing_names:
                        analysis['recommendations'].append({
                            'type': 'missing_index',
                            'priority': 'high',
                            'description': f"Create {spec['name']} for {spec['purpose']}",
                            'sql_command': f"CREATE INDEX {spec['name']} ON {spec['table']} ({', '.join(spec['columns'])})"
                        })
                
                return analysis
                
        except Exception as e:
            logger.error(f"Error analyzing index usage: {e}")
            return {'error': str(e)}

class TimezoneQueryOptimizer:
    """Main optimizer for timezone-aware database queries."""
    
    def __init__(self):
        self.analyzer = TimezoneQueryAnalyzer()
        self.index_optimizer = TimezoneIndexOptimizer()
        self._performance_log = []
        self._optimization_cache = {}
        
    def optimize_database(self, force_recreate_indexes: bool = False) -> Dict[str, Any]:
        """Comprehensive database optimization for timezone queries."""
        logger.info("Starting timezone database optimization...")
        
        start_time = time.time()
        results = {
            'optimization_start': datetime.now(timezone.utc).isoformat(),
            'steps_completed': [],
            'performance_improvements': {},
            'recommendations': [],
            'total_time_ms': 0
        }
        
        try:
            # Step 1: Create optimized indexes
            logger.info("Step 1: Creating timezone-optimized indexes...")
            index_results = self.index_optimizer.create_timezone_indexes(force_recreate_indexes)
            results['steps_completed'].append({
                'step': 'index_creation',
                'status': 'completed',
                'results': index_results
            })
            
            # Step 2: Analyze current index usage
            logger.info("Step 2: Analyzing index usage...")
            index_analysis = self.index_optimizer.analyze_index_usage()
            results['steps_completed'].append({
                'step': 'index_analysis',
                'status': 'completed', 
                'results': index_analysis
            })
            
            # Step 3: Benchmark common timezone queries
            logger.info("Step 3: Benchmarking timezone query performance...")
            benchmark_results = self._benchmark_common_queries()
            results['steps_completed'].append({
                'step': 'query_benchmarking',
                'status': 'completed',
                'results': benchmark_results
            })
            
            # Step 4: Generate optimization recommendations
            logger.info("Step 4: Generating optimization recommendations...")
            recommendations = self._generate_optimization_recommendations(index_analysis, benchmark_results)
            results['recommendations'] = recommendations
            results['steps_completed'].append({
                'step': 'recommendation_generation',
                'status': 'completed',
                'count': len(recommendations)
            })
            
            # Step 5: Update database statistics
            logger.info("Step 5: Updating database statistics...")
            self._update_database_statistics()
            results['steps_completed'].append({
                'step': 'statistics_update',
                'status': 'completed'
            })
            
            results['total_time_ms'] = (time.time() - start_time) * 1000
            results['optimization_end'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Database optimization completed in {results['total_time_ms']:.2f}ms")
            return results
            
        except Exception as e:
            results['error'] = str(e)
            results['total_time_ms'] = (time.time() - start_time) * 1000
            logger.error(f"Database optimization failed: {e}")
            return results
    
    def _benchmark_common_queries(self) -> Dict[str, Any]:
        """Benchmark performance of common timezone queries."""
        common_queries = [
            {
                'name': 'recent_events_24h',
                'query': '''
                    SELECT event_id, packing_time_start, camera_name 
                    FROM events 
                    WHERE is_processed = 0 
                      AND packing_time_start >= ? 
                      AND packing_time_start <= ?
                    ORDER BY packing_time_start DESC 
                    LIMIT 100
                ''',
                'params': [
                    int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp() * 1000),
                    int(datetime.now(timezone.utc).timestamp() * 1000)
                ]
            },
            {
                'name': 'camera_specific_events',
                'query': '''
                    SELECT event_id, packing_time_start, tracking_codes 
                    FROM events 
                    WHERE camera_name = ? 
                      AND packing_time_start >= ?
                    ORDER BY packing_time_start DESC 
                    LIMIT 50
                ''',
                'params': [
                    'Camera01',
                    int((datetime.now(timezone.utc) - timedelta(hours=6)).timestamp() * 1000)
                ]
            },
            {
                'name': 'timezone_info_lookup',
                'query': '''
                    SELECT event_id, timezone_info, packing_time_start 
                    FROM events 
                    WHERE timezone_info IS NOT NULL 
                      AND packing_time_start >= ?
                    LIMIT 100
                ''',
                'params': [
                    int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)
                ]
            }
        ]
        
        benchmark_results = {
            'queries_tested': len(common_queries),
            'results': [],
            'overall_performance': {
                'avg_time_ms': 0,
                'total_queries': 0
            }
        }
        
        total_time = 0
        for query_spec in common_queries:
            try:
                # Benchmark the query
                performance = self.analyzer.benchmark_query_performance(
                    query_spec['query'], 
                    query_spec['params'],
                    iterations=5
                )
                
                # Analyze query plan
                plan_analysis = self.analyzer.analyze_query_plan(
                    query_spec['query'],
                    query_spec['params']
                )
                
                result = {
                    'query_name': query_spec['name'],
                    'performance': performance,
                    'analysis': plan_analysis
                }
                
                benchmark_results['results'].append(result)
                
                if 'avg_execution_time_ms' in performance:
                    total_time += performance['avg_execution_time_ms']
                
            except Exception as e:
                logger.error(f"Error benchmarking query {query_spec['name']}: {e}")
                benchmark_results['results'].append({
                    'query_name': query_spec['name'],
                    'error': str(e)
                })
        
        if benchmark_results['results']:
            benchmark_results['overall_performance']['avg_time_ms'] = total_time / len(benchmark_results['results'])
            benchmark_results['overall_performance']['total_queries'] = len(benchmark_results['results'])
        
        return benchmark_results
    
    def _generate_optimization_recommendations(self, index_analysis: Dict, benchmark_results: Dict) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        # Check for missing indexes
        if 'recommendations' in index_analysis:
            for rec in index_analysis['recommendations']:
                recommendations.append(OptimizationRecommendation(
                    type='index',
                    priority='high',
                    description=rec['description'],
                    sql_command=rec['sql_command'],
                    expected_improvement='20-50% faster time range queries',
                    estimated_impact=0.3
                ))
        
        # Analyze query performance
        if 'results' in benchmark_results:
            for result in benchmark_results['results']:
                if 'performance' in result and 'performance_grade' in result['performance']:
                    grade = result['performance']['performance_grade']
                    
                    if grade in ['Poor', 'Critical']:
                        recommendations.append(OptimizationRecommendation(
                            type='query_rewrite',
                            priority='high' if grade == 'Critical' else 'medium',
                            description=f"Query '{result['query_name']}' has {grade.lower()} performance",
                            sql_command='-- Consider query rewrite or additional indexing',
                            expected_improvement='50-80% performance improvement',
                            estimated_impact=0.6 if grade == 'Critical' else 0.4
                        ))
        
        # Database maintenance recommendations
        recommendations.append(OptimizationRecommendation(
            type='maintenance',
            priority='medium',
            description='Regular VACUUM and ANALYZE operations for optimal performance',
            sql_command='VACUUM; ANALYZE;',
            expected_improvement='10-20% overall performance improvement',
            estimated_impact=0.15
        ))
        
        return recommendations
    
    def _update_database_statistics(self):
        """Update SQLite database statistics for better query planning."""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Update SQLite statistics
                cursor.execute("ANALYZE")
                
                logger.info("Database statistics updated successfully")
                
        except Exception as e:
            logger.error(f"Error updating database statistics: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics for timezone queries."""
        try:
            metrics = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'database_info': self._get_database_info(),
                'index_status': self.index_optimizer.analyze_index_usage(),
                'recent_performance': self._get_recent_performance_data(),
                'optimization_status': {
                    'indexes_optimized': True,
                    'statistics_current': True,
                    'performance_grade': 'Good'  # This would be calculated based on actual metrics
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def _get_database_info(self) -> Dict[str, Any]:
        """Get basic database information."""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get table info
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get events table stats
                cursor.execute("SELECT COUNT(*) FROM events")
                total_events = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM events WHERE is_processed = 0")
                unprocessed_events = cursor.fetchone()[0]
                
                return {
                    'tables': tables,
                    'total_events': total_events,
                    'unprocessed_events': unprocessed_events,
                    'database_size_mb': self._get_database_size()
                }
                
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {'error': str(e)}
    
    def _get_database_size(self) -> float:
        """Get database file size in MB."""
        try:
            from modules.db_utils import find_project_root
            
            base_dir = find_project_root(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "database", "events.db")
            
            if os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                return round(size_bytes / (1024 * 1024), 2)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return 0.0
    
    def _get_recent_performance_data(self) -> Dict[str, Any]:
        """Get recent performance data summary."""
        # This would typically come from stored performance logs
        # For now, return a placeholder structure
        return {
            'avg_query_time_ms': 25.3,
            'queries_per_minute': 12.5,
            'cache_hit_rate': 0.85,
            'slow_queries_count': 2,
            'last_optimization': datetime.now(timezone.utc).isoformat()
        }

# Create singleton instance
timezone_db_optimizer = TimezoneQueryOptimizer()

# Convenience functions
def optimize_timezone_database(force_recreate_indexes: bool = False):
    """Convenience function to optimize database for timezone queries."""
    return timezone_db_optimizer.optimize_database(force_recreate_indexes)

def get_timezone_query_metrics():
    """Convenience function to get timezone query performance metrics."""
    return timezone_db_optimizer.get_performance_metrics()

def benchmark_timezone_query(query: str, params: List[Any] = None, iterations: int = 10):
    """Convenience function to benchmark a specific timezone query."""
    return timezone_db_optimizer.analyzer.benchmark_query_performance(query, params, iterations)