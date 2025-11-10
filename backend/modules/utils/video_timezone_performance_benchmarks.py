#!/usr/bin/env python3
"""
V_Track Video Timezone Performance Benchmarks

Performance testing and benchmarking for timezone-aware video processing.
Tests video scanning, timezone detection, and metadata extraction performance
to ensure no degradation compared to the original hardcoded implementation.

Features:
- Video scanning performance comparison
- Timezone detection speed benchmarks
- Memory usage monitoring
- Batch processing performance
- Error rate tracking
- Performance regression detection

Usage:
    python3 video_timezone_performance_benchmarks.py
    python3 video_timezone_performance_benchmarks.py --benchmark-type scanning
    python3 video_timezone_performance_benchmarks.py --quick-test
"""

import os
import time
import tempfile
import subprocess
import json
import psutil
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass, asdict

# Import V_Track modules
from modules.config.logging_config import get_logger
from modules.utils.video_timezone_detector import video_timezone_detector, get_timezone_aware_creation_time
from modules.utils.timezone_manager import timezone_manager
from modules.scheduler.file_lister import get_file_creation_time, scan_files

logger = get_logger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for video processing operations."""
    operation_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    files_processed: int
    errors_count: int
    success_rate: float
    throughput_files_per_second: float
    additional_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_metrics is None:
            self.additional_metrics = {}

class VideoTimezonePerformanceBenchmarks:
    """
    Performance benchmarking system for timezone-aware video processing.
    
    Provides comprehensive performance testing to ensure timezone enhancements
    don't degrade video processing performance.
    """
    
    def __init__(self):
        """Initialize performance benchmarks."""
        self.test_results = []
        self.baseline_results = {}
        
        # Test configuration
        self.test_video_formats = ['.mp4', '.avi', '.mov', '.mkv']
        self.test_file_sizes = ['small', 'medium', 'large']  # Different video sizes
        
        # Performance thresholds
        self.max_acceptable_slowdown = 1.2  # 20% slower than baseline
        self.max_memory_increase = 1.5      # 50% more memory than baseline
        
        logger.info("VideoTimezonePerformanceBenchmarks initialized")
    
    def run_comprehensive_benchmarks(self, test_video_dir: Optional[str] = None, 
                                   iterations: int = 100) -> Dict[str, Any]:
        """
        Run comprehensive performance benchmarks.
        
        Args:
            test_video_dir: Directory containing test videos (optional)
            iterations: Number of iterations for each test
            
        Returns:
            Comprehensive benchmark results
        """
        logger.info(f"🚀 Starting comprehensive timezone performance benchmarks ({iterations} iterations)")
        
        benchmark_start = time.time()
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_configuration': {
                'iterations': iterations,
                'test_video_dir': test_video_dir,
                'system_info': self._get_system_info()
            },
            'benchmarks': {},
            'summary': {},
            'recommendations': []
        }
        
        try:
            # Benchmark 1: Video file scanning performance
            logger.info("📊 Benchmarking video file scanning...")
            scanning_results = self._benchmark_video_scanning(test_video_dir, iterations)
            results['benchmarks']['video_scanning'] = scanning_results
            
            # Benchmark 2: Timezone detection performance
            logger.info("📊 Benchmarking timezone detection...")
            timezone_results = self._benchmark_timezone_detection(test_video_dir, iterations)
            results['benchmarks']['timezone_detection'] = timezone_results
            
            # Benchmark 3: Creation time extraction performance
            logger.info("📊 Benchmarking creation time extraction...")
            creation_time_results = self._benchmark_creation_time_extraction(test_video_dir, iterations)
            results['benchmarks']['creation_time_extraction'] = creation_time_results
            
            # Benchmark 4: Memory usage and cleanup
            logger.info("📊 Benchmarking memory usage...")
            memory_results = self._benchmark_memory_usage(test_video_dir, iterations)
            results['benchmarks']['memory_usage'] = memory_results
            
            # Benchmark 5: Concurrent processing
            logger.info("📊 Benchmarking concurrent processing...")
            concurrent_results = self._benchmark_concurrent_processing(test_video_dir, min(iterations, 20))
            results['benchmarks']['concurrent_processing'] = concurrent_results
            
            # Generate summary and recommendations
            results['summary'] = self._generate_benchmark_summary(results['benchmarks'])
            results['recommendations'] = self._generate_recommendations(results['benchmarks'])
            
            total_duration = time.time() - benchmark_start
            results['total_duration'] = total_duration
            
            logger.info(f"✅ Comprehensive benchmarks completed in {total_duration:.2f}s")
            
            # Save results
            self._save_benchmark_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Benchmark execution failed: {e}")
            results['error'] = str(e)
            return results
    
    def _benchmark_video_scanning(self, test_dir: Optional[str], iterations: int) -> Dict[str, Any]:
        """Benchmark video file scanning performance."""
        if not test_dir or not Path(test_dir).exists():
            # Create temporary test environment
            test_dir = self._create_test_video_environment()
        
        results = {
            'baseline_performance': {},
            'enhanced_performance': {},
            'comparison': {}
        }
        
        try:
            # Baseline test: Original hardcoded timezone scanning
            baseline_metrics = self._run_scanning_benchmark_baseline(test_dir, iterations)
            results['baseline_performance'] = asdict(baseline_metrics)
            
            # Enhanced test: New timezone-aware scanning
            enhanced_metrics = self._run_scanning_benchmark_enhanced(test_dir, iterations)
            results['enhanced_performance'] = asdict(enhanced_metrics)
            
            # Performance comparison
            results['comparison'] = self._compare_performance_metrics(baseline_metrics, enhanced_metrics)
            
        except Exception as e:
            logger.error(f"Video scanning benchmark failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _benchmark_timezone_detection(self, test_dir: Optional[str], iterations: int) -> Dict[str, Any]:
        """Benchmark timezone detection performance."""
        if not test_dir:
            test_dir = self._create_test_video_environment()
        
        results = {
            'detection_methods': {},
            'caching_impact': {},
            'accuracy_metrics': {}
        }
        
        try:
            video_files = list(Path(test_dir).glob('**/*.mp4'))[:min(10, iterations)]
            
            if not video_files:
                results['error'] = "No video files found for testing"
                return results
            
            # Test different detection methods
            for method in ['metadata', 'camera_config', 'user_setting', 'fallback']:
                method_metrics = self._benchmark_detection_method(video_files, method, iterations)
                results['detection_methods'][method] = asdict(method_metrics)
            
            # Test caching impact
            caching_metrics = self._benchmark_caching_impact(video_files, iterations)
            results['caching_impact'] = caching_metrics
            
            # Test detection accuracy
            accuracy_metrics = self._benchmark_detection_accuracy(video_files)
            results['accuracy_metrics'] = accuracy_metrics
            
        except Exception as e:
            logger.error(f"Timezone detection benchmark failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _benchmark_creation_time_extraction(self, test_dir: Optional[str], iterations: int) -> Dict[str, Any]:
        """Benchmark creation time extraction performance."""
        if not test_dir:
            test_dir = self._create_test_video_environment()
        
        results = {
            'ffprobe_performance': {},
            'enhanced_extraction': {},
            'format_specific': {}
        }
        
        try:
            video_files = list(Path(test_dir).glob('**/*'))
            video_files = [f for f in video_files if f.suffix.lower() in self.test_video_formats][:min(20, iterations)]
            
            if not video_files:
                results['error'] = "No video files found for testing"
                return results
            
            # Test FFprobe performance
            ffprobe_metrics = self._benchmark_ffprobe_extraction(video_files, iterations)
            results['ffprobe_performance'] = asdict(ffprobe_metrics)
            
            # Test enhanced extraction
            enhanced_metrics = self._benchmark_enhanced_extraction(video_files, iterations)
            results['enhanced_extraction'] = asdict(enhanced_metrics)
            
            # Test format-specific performance
            format_metrics = self._benchmark_format_specific_extraction(video_files, iterations)
            results['format_specific'] = format_metrics
            
        except Exception as e:
            logger.error(f"Creation time extraction benchmark failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _benchmark_memory_usage(self, test_dir: Optional[str], iterations: int) -> Dict[str, Any]:
        """Benchmark memory usage and cleanup."""
        if not test_dir:
            test_dir = self._create_test_video_environment()
        
        results = {
            'baseline_memory': {},
            'enhanced_memory': {},
            'memory_growth': {},
            'cleanup_efficiency': {}
        }
        
        try:
            # Monitor memory during baseline operations
            baseline_memory = self._monitor_memory_usage_baseline(test_dir, iterations)
            results['baseline_memory'] = baseline_memory
            
            # Monitor memory during enhanced operations
            enhanced_memory = self._monitor_memory_usage_enhanced(test_dir, iterations)
            results['enhanced_memory'] = enhanced_memory
            
            # Test memory growth over time
            memory_growth = self._test_memory_growth(test_dir, iterations)
            results['memory_growth'] = memory_growth
            
            # Test cleanup efficiency
            cleanup_efficiency = self._test_cleanup_efficiency(iterations)
            results['cleanup_efficiency'] = cleanup_efficiency
            
        except Exception as e:
            logger.error(f"Memory usage benchmark failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _benchmark_concurrent_processing(self, test_dir: Optional[str], iterations: int) -> Dict[str, Any]:
        """Benchmark concurrent video processing performance."""
        if not test_dir:
            test_dir = self._create_test_video_environment()
        
        results = {
            'single_threaded': {},
            'multi_threaded': {},
            'scalability': {}
        }
        
        try:
            video_files = list(Path(test_dir).glob('**/*.mp4'))[:min(10, iterations)]
            
            if not video_files:
                results['error'] = "No video files found for testing"
                return results
            
            # Single-threaded performance
            single_metrics = self._benchmark_single_threaded_processing(video_files)
            results['single_threaded'] = asdict(single_metrics)
            
            # Multi-threaded performance
            multi_metrics = self._benchmark_multi_threaded_processing(video_files)
            results['multi_threaded'] = asdict(multi_metrics)
            
            # Scalability testing
            scalability_metrics = self._benchmark_scalability(video_files)
            results['scalability'] = scalability_metrics
            
        except Exception as e:
            logger.error(f"Concurrent processing benchmark failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _create_test_video_environment(self) -> str:
        """Create a temporary test environment with sample video files."""
        test_dir = tempfile.mkdtemp(prefix='vtrack_timezone_test_')
        
        try:
            # Create sample video metadata files for testing
            for i in range(5):
                video_name = f"test_video_{i}.mp4"
                video_path = str(Path(test_dir) / video_name)
                
                # Create minimal video file for testing (just metadata)
                # This is a placeholder - in real testing you'd use actual video files
                with open(video_path, 'wb') as f:
                    f.write(b'fake_video_data_for_testing')
                
                # Set file timestamps for testing
                timestamp = time.time() - (i * 3600)  # Spread over several hours
                os.utime(video_path, (timestamp, timestamp))
            
            logger.info(f"Created test environment: {test_dir}")
            return test_dir
            
        except Exception as e:
            logger.error(f"Failed to create test environment: {e}")
            return test_dir
    
    def _run_scanning_benchmark_baseline(self, test_dir: str, iterations: int) -> PerformanceMetrics:
        """Run baseline video scanning benchmark."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        files_processed = 0
        errors = 0
        
        for i in range(iterations):
            try:
                # Simulate baseline scanning with hardcoded timezone
                video_files = []
                for root, dirs, files in os.walk(test_dir):
                    for file in files:
                        if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                            file_path = str(Path(root) / file)
                            # Simulate baseline creation time extraction
                            file_ctime = datetime.fromtimestamp(Path(file_path).stat().st_ctime)
                            video_files.append((file_path, file_ctime))
                            files_processed += 1
            except Exception:
                errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        success_rate = (iterations - errors) / iterations if iterations > 0 else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name="baseline_scanning",
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0.0,  # Not measured in this simple test
            files_processed=files_processed,
            errors_count=errors,
            success_rate=success_rate,
            throughput_files_per_second=throughput
        )
    
    def _run_scanning_benchmark_enhanced(self, test_dir: str, iterations: int) -> PerformanceMetrics:
        """Run enhanced video scanning benchmark."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        files_processed = 0
        errors = 0
        
        for i in range(iterations):
            try:
                # Use enhanced scanning with timezone detection
                video_files = []
                for root, dirs, files in os.walk(test_dir):
                    for file in files:
                        if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                            file_path = str(Path(root) / file)
                            try:
                                # Use enhanced creation time extraction
                                file_ctime = get_file_creation_time(file_path, "TestCamera")
                                video_files.append((file_path, file_ctime))
                                files_processed += 1
                            except Exception:
                                errors += 1
            except Exception:
                errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        success_rate = (files_processed) / (files_processed + errors) if (files_processed + errors) > 0 else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name="enhanced_scanning",
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0.0,
            files_processed=files_processed,
            errors_count=errors,
            success_rate=success_rate,
            throughput_files_per_second=throughput
        )
    
    def _benchmark_detection_method(self, video_files: List[Path], method: str, iterations: int) -> PerformanceMetrics:
        """Benchmark specific timezone detection method."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        files_processed = 0
        errors = 0
        
        for i in range(min(iterations, len(video_files))):
            try:
                video_file = video_files[i % len(video_files)]
                
                # Test specific detection method
                if method == 'metadata':
                    result = video_timezone_detector._detect_from_metadata(str(video_file))
                elif method == 'camera_config':
                    result = video_timezone_detector._get_camera_timezone("TestCamera")
                elif method == 'user_setting':
                    result = timezone_manager.get_user_timezone_name()
                else:  # fallback
                    result = "Asia/Ho_Chi_Minh"
                
                files_processed += 1
                
            except Exception:
                errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        success_rate = files_processed / (files_processed + errors) if (files_processed + errors) > 0 else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name=f"{method}_detection",
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0.0,
            files_processed=files_processed,
            errors_count=errors,
            success_rate=success_rate,
            throughput_files_per_second=throughput
        )
    
    def _benchmark_caching_impact(self, video_files: List[Path], iterations: int) -> Dict[str, Any]:
        """Benchmark caching impact on performance."""
        if not video_files:
            return {'error': 'No video files for caching test'}
        
        test_file = str(video_files[0])
        
        # Test without cache (cold)
        video_timezone_detector.clear_cache()
        start_time = time.time()
        
        for i in range(iterations):
            try:
                timezone_info = video_timezone_detector.detect_video_timezone(test_file, "TestCamera")
            except Exception:
                pass
        
        cold_time = time.time() - start_time
        
        # Test with cache (warm)
        start_time = time.time()
        
        for i in range(iterations):
            try:
                timezone_info = video_timezone_detector.detect_video_timezone(test_file, "TestCamera")
            except Exception:
                pass
        
        warm_time = time.time() - start_time
        
        cache_speedup = cold_time / warm_time if warm_time > 0 else 1.0
        
        return {
            'cold_cache_time': cold_time,
            'warm_cache_time': warm_time,
            'cache_speedup_factor': cache_speedup,
            'iterations': iterations
        }
    
    def _benchmark_detection_accuracy(self, video_files: List[Path]) -> Dict[str, Any]:
        """Benchmark timezone detection accuracy."""
        results = {
            'total_files': len(video_files),
            'successful_detections': 0,
            'failed_detections': 0,
            'confidence_scores': [],
            'detection_sources': {}
        }
        
        for video_file in video_files:
            try:
                timezone_info = video_timezone_detector.detect_video_timezone(str(video_file), "TestCamera")
                
                if timezone_info.detected_timezone:
                    results['successful_detections'] += 1
                    results['confidence_scores'].append(timezone_info.confidence_score)
                    
                    source = timezone_info.timezone_source
                    results['detection_sources'][source] = results['detection_sources'].get(source, 0) + 1
                else:
                    results['failed_detections'] += 1
                    
            except Exception:
                results['failed_detections'] += 1
        
        if results['confidence_scores']:
            results['average_confidence'] = sum(results['confidence_scores']) / len(results['confidence_scores'])
        else:
            results['average_confidence'] = 0.0
        
        results['success_rate'] = results['successful_detections'] / results['total_files'] if results['total_files'] > 0 else 0
        
        return results
    
    def _benchmark_ffprobe_extraction(self, video_files: List[Path], iterations: int) -> PerformanceMetrics:
        """Benchmark FFprobe metadata extraction performance."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        files_processed = 0
        errors = 0
        
        for i in range(min(iterations, len(video_files))):
            try:
                video_file = video_files[i % len(video_files)]
                
                # Test FFprobe extraction directly
                cmd = [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_entries", "format_tags=creation_time:format=creation_time",
                    str(video_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    files_processed += 1
                else:
                    errors += 1
                    
            except Exception:
                errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        success_rate = files_processed / (files_processed + errors) if (files_processed + errors) > 0 else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name="ffprobe_extraction",
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0.0,
            files_processed=files_processed,
            errors_count=errors,
            success_rate=success_rate,
            throughput_files_per_second=throughput
        )
    
    def _benchmark_enhanced_extraction(self, video_files: List[Path], iterations: int) -> PerformanceMetrics:
        """Benchmark enhanced creation time extraction."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        files_processed = 0
        errors = 0
        
        for i in range(min(iterations, len(video_files))):
            try:
                video_file = video_files[i % len(video_files)]
                
                # Test enhanced extraction
                creation_time = get_timezone_aware_creation_time(str(video_file), "TestCamera")
                files_processed += 1
                
            except Exception:
                errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        success_rate = files_processed / (files_processed + errors) if (files_processed + errors) > 0 else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name="enhanced_extraction",
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0.0,
            files_processed=files_processed,
            errors_count=errors,
            success_rate=success_rate,
            throughput_files_per_second=throughput
        )
    
    def _benchmark_format_specific_extraction(self, video_files: List[Path], iterations: int) -> Dict[str, Any]:
        """Benchmark format-specific extraction performance."""
        format_results = {}
        
        # Group files by format
        format_groups = {}
        for video_file in video_files:
            ext = video_file.suffix.lower()
            if ext not in format_groups:
                format_groups[ext] = []
            format_groups[ext].append(video_file)
        
        for format_ext, files in format_groups.items():
            if not files:
                continue
                
            start_time = time.time()
            files_processed = 0
            errors = 0
            
            for i in range(min(iterations, len(files))):
                try:
                    video_file = files[i % len(files)]
                    creation_time = get_timezone_aware_creation_time(str(video_file), "TestCamera")
                    files_processed += 1
                except Exception:
                    errors += 1
            
            execution_time = time.time() - start_time
            success_rate = files_processed / (files_processed + errors) if (files_processed + errors) > 0 else 0
            throughput = files_processed / execution_time if execution_time > 0 else 0
            
            format_results[format_ext] = {
                'execution_time': execution_time,
                'files_processed': files_processed,
                'errors': errors,
                'success_rate': success_rate,
                'throughput': throughput
            }
        
        return format_results
    
    def _monitor_memory_usage_baseline(self, test_dir: str, iterations: int) -> Dict[str, Any]:
        """Monitor memory usage during baseline operations."""
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        memory_samples = []
        
        # Simulate baseline operations
        for i in range(iterations):
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            peak_memory = max(peak_memory, current_memory)
            
            # Simulate video processing
            time.sleep(0.001)  # Small delay to simulate work
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        return {
            'initial_memory_mb': initial_memory,
            'peak_memory_mb': peak_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': final_memory - initial_memory,
            'average_memory_mb': sum(memory_samples) / len(memory_samples) if memory_samples else 0
        }
    
    def _monitor_memory_usage_enhanced(self, test_dir: str, iterations: int) -> Dict[str, Any]:
        """Monitor memory usage during enhanced operations."""
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        memory_samples = []
        
        # Enhanced operations with timezone detection
        for i in range(iterations):
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            peak_memory = max(peak_memory, current_memory)
            
            # Simulate enhanced video processing
            try:
                # This would normally process actual video files
                timezone_info = video_timezone_detector.detect_video_timezone("/fake/path", "TestCamera")
            except Exception:
                pass
            
            time.sleep(0.001)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        return {
            'initial_memory_mb': initial_memory,
            'peak_memory_mb': peak_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': final_memory - initial_memory,
            'average_memory_mb': sum(memory_samples) / len(memory_samples) if memory_samples else 0
        }
    
    def _test_memory_growth(self, test_dir: str, iterations: int) -> Dict[str, Any]:
        """Test memory growth over extended operations."""
        process = psutil.Process()
        
        memory_checkpoints = []
        checkpoint_interval = iterations // 10  # 10 checkpoints
        
        initial_memory = process.memory_info().rss / 1024 / 1024
        memory_checkpoints.append(('start', initial_memory))
        
        for i in range(iterations):
            # Simulate processing
            try:
                timezone_info = video_timezone_detector.detect_video_timezone("/fake/path", f"Camera{i%5}")
            except Exception:
                pass
            
            # Take memory checkpoints
            if i % checkpoint_interval == 0 and i > 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_checkpoints.append((f'iteration_{i}', current_memory))
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_checkpoints.append(('end', final_memory))
        
        # Calculate memory growth rate
        total_growth = final_memory - initial_memory
        growth_rate = total_growth / iterations if iterations > 0 else 0
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'total_growth_mb': total_growth,
            'growth_rate_mb_per_iteration': growth_rate,
            'memory_checkpoints': memory_checkpoints,
            'shows_memory_leak': total_growth > 50  # Arbitrary threshold
        }
    
    def _test_cleanup_efficiency(self, iterations: int) -> Dict[str, Any]:
        """Test cache cleanup efficiency."""
        # Fill cache
        for i in range(iterations):
            try:
                timezone_info = video_timezone_detector.detect_video_timezone(f"/fake/path_{i}", f"Camera{i}")
            except Exception:
                pass
        
        memory_before_cleanup = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Clear cache
        cleanup_start = time.time()
        video_timezone_detector.clear_cache()
        cleanup_time = time.time() - cleanup_start
        
        memory_after_cleanup = psutil.Process().memory_info().rss / 1024 / 1024
        memory_freed = memory_before_cleanup - memory_after_cleanup
        
        return {
            'cleanup_time_seconds': cleanup_time,
            'memory_before_mb': memory_before_cleanup,
            'memory_after_mb': memory_after_cleanup,
            'memory_freed_mb': memory_freed,
            'cleanup_efficiency': memory_freed / memory_before_cleanup if memory_before_cleanup > 0 else 0
        }
    
    def _benchmark_single_threaded_processing(self, video_files: List[Path]) -> PerformanceMetrics:
        """Benchmark single-threaded video processing."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        files_processed = 0
        errors = 0
        
        for video_file in video_files:
            try:
                creation_time = get_timezone_aware_creation_time(str(video_file), "TestCamera")
                files_processed += 1
            except Exception:
                errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        success_rate = files_processed / len(video_files) if video_files else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name="single_threaded",
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0.0,
            files_processed=files_processed,
            errors_count=errors,
            success_rate=success_rate,
            throughput_files_per_second=throughput
        )
    
    def _benchmark_multi_threaded_processing(self, video_files: List[Path]) -> PerformanceMetrics:
        """Benchmark multi-threaded video processing."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        files_processed = 0
        errors = 0
        results_lock = threading.Lock()
        
        def process_file(video_file):
            nonlocal files_processed, errors
            try:
                creation_time = get_timezone_aware_creation_time(str(video_file), "TestCamera")
                with results_lock:
                    files_processed += 1
            except Exception:
                with results_lock:
                    errors += 1
        
        # Use thread pool
        threads = []
        max_threads = min(4, len(video_files))  # Limit to 4 threads
        
        for i, video_file in enumerate(video_files):
            if len(threads) >= max_threads:
                # Wait for a thread to complete
                for thread in threads:
                    if not thread.is_alive():
                        thread.join()
                        threads.remove(thread)
                        break
                else:
                    # All threads still running, wait for first to complete
                    threads[0].join()
                    threads.pop(0)
            
            thread = threading.Thread(target=process_file, args=(video_file,))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        success_rate = files_processed / len(video_files) if video_files else 0
        throughput = files_processed / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            operation_name="multi_threaded",
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0.0,
            files_processed=files_processed,
            errors_count=errors,
            success_rate=success_rate,
            throughput_files_per_second=throughput
        )
    
    def _benchmark_scalability(self, video_files: List[Path]) -> Dict[str, Any]:
        """Benchmark scalability with different file counts."""
        scalability_results = {}
        
        file_counts = [1, 5, 10, 20, 50] if len(video_files) >= 50 else [1, len(video_files)//2, len(video_files)]
        
        for count in file_counts:
            if count > len(video_files):
                continue
                
            test_files = video_files[:count]
            metrics = self._benchmark_single_threaded_processing(test_files)
            
            scalability_results[f'{count}_files'] = {
                'execution_time': metrics.execution_time,
                'throughput': metrics.throughput_files_per_second,
                'memory_usage': metrics.memory_usage_mb,
                'success_rate': metrics.success_rate
            }
        
        return scalability_results
    
    def _compare_performance_metrics(self, baseline: PerformanceMetrics, enhanced: PerformanceMetrics) -> Dict[str, Any]:
        """Compare baseline and enhanced performance metrics."""
        comparison = {}
        
        # Execution time comparison
        if baseline.execution_time > 0:
            time_ratio = enhanced.execution_time / baseline.execution_time
            comparison['execution_time_ratio'] = time_ratio
            comparison['execution_time_change'] = f"{((time_ratio - 1) * 100):+.1f}%"
            comparison['within_acceptable_slowdown'] = time_ratio <= self.max_acceptable_slowdown
        
        # Memory usage comparison
        if baseline.memory_usage_mb > 0:
            memory_ratio = enhanced.memory_usage_mb / baseline.memory_usage_mb
            comparison['memory_usage_ratio'] = memory_ratio
            comparison['memory_usage_change'] = f"{((memory_ratio - 1) * 100):+.1f}%"
            comparison['within_acceptable_memory'] = memory_ratio <= self.max_memory_increase
        
        # Throughput comparison
        if baseline.throughput_files_per_second > 0:
            throughput_ratio = enhanced.throughput_files_per_second / baseline.throughput_files_per_second
            comparison['throughput_ratio'] = throughput_ratio
            comparison['throughput_change'] = f"{((throughput_ratio - 1) * 100):+.1f}%"
        
        # Success rate comparison
        comparison['baseline_success_rate'] = baseline.success_rate
        comparison['enhanced_success_rate'] = enhanced.success_rate
        comparison['success_rate_change'] = enhanced.success_rate - baseline.success_rate
        
        # Overall assessment
        performance_acceptable = (
            comparison.get('within_acceptable_slowdown', True) and
            comparison.get('within_acceptable_memory', True) and
            enhanced.success_rate >= baseline.success_rate
        )
        comparison['performance_acceptable'] = performance_acceptable
        
        return comparison
    
    def _generate_benchmark_summary(self, benchmarks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate benchmark summary."""
        summary = {
            'overall_performance': 'acceptable',
            'key_metrics': {},
            'performance_issues': [],
            'performance_improvements': []
        }
        
        # Analyze video scanning performance
        if 'video_scanning' in benchmarks and 'comparison' in benchmarks['video_scanning']:
            comparison = benchmarks['video_scanning']['comparison']
            
            if comparison.get('performance_acceptable', True):
                summary['performance_improvements'].append("Video scanning performance within acceptable limits")
            else:
                summary['performance_issues'].append("Video scanning performance degradation detected")
                summary['overall_performance'] = 'needs_attention'
            
            summary['key_metrics']['scanning_time_change'] = comparison.get('execution_time_change', 'N/A')
            summary['key_metrics']['scanning_memory_change'] = comparison.get('memory_usage_change', 'N/A')
        
        # Analyze timezone detection performance
        if 'timezone_detection' in benchmarks:
            tz_detection = benchmarks['timezone_detection']
            
            if 'caching_impact' in tz_detection:
                cache_speedup = tz_detection['caching_impact'].get('cache_speedup_factor', 1.0)
                if cache_speedup > 2.0:
                    summary['performance_improvements'].append(f"Caching provides {cache_speedup:.1f}x speedup")
                
                summary['key_metrics']['cache_speedup'] = f"{cache_speedup:.1f}x"
            
            if 'accuracy_metrics' in tz_detection:
                accuracy = tz_detection['accuracy_metrics'].get('success_rate', 0)
                summary['key_metrics']['timezone_detection_accuracy'] = f"{accuracy*100:.1f}%"
                
                if accuracy < 0.8:
                    summary['performance_issues'].append("Low timezone detection accuracy")
                    summary['overall_performance'] = 'needs_attention'
        
        # Analyze memory usage
        if 'memory_usage' in benchmarks:
            memory_usage = benchmarks['memory_usage']
            
            if 'memory_growth' in memory_usage:
                shows_leak = memory_usage['memory_growth'].get('shows_memory_leak', False)
                if shows_leak:
                    summary['performance_issues'].append("Potential memory leak detected")
                    summary['overall_performance'] = 'needs_attention'
                else:
                    summary['performance_improvements'].append("No memory leaks detected")
        
        return summary
    
    def _generate_recommendations(self, benchmarks: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        # Analyze benchmarks and provide recommendations
        if 'video_scanning' in benchmarks:
            comparison = benchmarks['video_scanning'].get('comparison', {})
            
            if not comparison.get('performance_acceptable', True):
                if not comparison.get('within_acceptable_slowdown', True):
                    recommendations.append("Consider optimizing video scanning algorithm to reduce execution time")
                
                if not comparison.get('within_acceptable_memory', True):
                    recommendations.append("Optimize memory usage in video scanning operations")
        
        if 'timezone_detection' in benchmarks:
            accuracy = benchmarks['timezone_detection'].get('accuracy_metrics', {}).get('success_rate', 1.0)
            
            if accuracy < 0.9:
                recommendations.append("Improve timezone detection accuracy by enhancing metadata extraction")
            
            cache_speedup = benchmarks['timezone_detection'].get('caching_impact', {}).get('cache_speedup_factor', 1.0)
            
            if cache_speedup < 2.0:
                recommendations.append("Consider improving caching strategy for better performance")
        
        if 'memory_usage' in benchmarks:
            shows_leak = benchmarks['memory_usage'].get('memory_growth', {}).get('shows_memory_leak', False)
            
            if shows_leak:
                recommendations.append("Investigate and fix potential memory leaks in timezone processing")
            
            cleanup_efficiency = benchmarks['memory_usage'].get('cleanup_efficiency', {}).get('cleanup_efficiency', 1.0)
            
            if cleanup_efficiency < 0.5:
                recommendations.append("Improve cache cleanup efficiency")
        
        if 'concurrent_processing' in benchmarks:
            single_threaded = benchmarks['concurrent_processing'].get('single_threaded', {})
            multi_threaded = benchmarks['concurrent_processing'].get('multi_threaded', {})
            
            if (single_threaded.get('throughput_files_per_second', 0) > 
                multi_threaded.get('throughput_files_per_second', 0)):
                recommendations.append("Multi-threading may not be beneficial for current workload size")
        
        if not recommendations:
            recommendations.append("Performance is acceptable across all benchmarks")
        
        return recommendations
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for benchmark context."""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
            'platform': __import__('platform').system(),
        }
    
    def _save_benchmark_results(self, results: Dict[str, Any]):
        """Save benchmark results to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"video_timezone_benchmarks_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"📄 Benchmark results saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save benchmark results: {e}")

# Convenience functions
def run_quick_performance_test() -> Dict[str, Any]:
    """Run a quick performance test."""
    benchmarks = VideoTimezonePerformanceBenchmarks()
    return benchmarks.run_comprehensive_benchmarks(iterations=10)

def run_full_performance_benchmarks(test_dir: Optional[str] = None, iterations: int = 100) -> Dict[str, Any]:
    """Run full performance benchmarks."""
    benchmarks = VideoTimezonePerformanceBenchmarks()
    return benchmarks.run_comprehensive_benchmarks(test_dir, iterations)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='V_Track Video Timezone Performance Benchmarks')
    parser.add_argument('--benchmark-type', choices=['scanning', 'detection', 'memory', 'concurrent'], 
                       help='Specific benchmark type to run')
    parser.add_argument('--test-dir', help='Directory containing test videos')
    parser.add_argument('--iterations', type=int, default=100, help='Number of iterations')
    parser.add_argument('--quick-test', action='store_true', help='Run quick test with fewer iterations')
    
    args = parser.parse_args()
    
    if args.quick_test:
        print("🚀 Running quick performance test...")
        results = run_quick_performance_test()
    else:
        print(f"🚀 Running full performance benchmarks ({args.iterations} iterations)...")
        results = run_full_performance_benchmarks(args.test_dir, args.iterations)
    
    # Print summary
    summary = results.get('summary', {})
    print(f"\n📊 Performance Summary:")
    print(f"   Overall: {summary.get('overall_performance', 'unknown')}")
    
    key_metrics = summary.get('key_metrics', {})
    for metric, value in key_metrics.items():
        print(f"   {metric}: {value}")
    
    improvements = summary.get('performance_improvements', [])
    if improvements:
        print(f"\n✅ Performance Improvements:")
        for improvement in improvements:
            print(f"   • {improvement}")
    
    issues = summary.get('performance_issues', [])
    if issues:
        print(f"\n⚠️ Performance Issues:")
        for issue in issues:
            print(f"   • {issue}")
    
    recommendations = results.get('recommendations', [])
    if recommendations:
        print(f"\n💡 Recommendations:")
        for rec in recommendations:
            print(f"   • {rec}")
    
    print(f"\n✅ Benchmarks completed. Results saved to file.")