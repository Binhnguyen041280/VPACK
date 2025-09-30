import psutil
import logging
import os
from datetime import datetime
from typing import Tuple
from modules.config.logging_config import get_logger


# Đường dẫn tương đối từ project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SystemMonitor:
    def __init__(self):
        self.min_batch_size = 2
        self.max_batch_size = 6
        self.cpu_threshold_low = 70  # Tăng batch_size nếu CPU < 70%
        self.cpu_threshold_high = 90  # Giảm batch_size nếu CPU > 90%
        self.setup_logging()

    def setup_logging(self):
        self.logger = get_logger(__name__, {"module": "system_monitor"})
        self.logger.info("SystemMonitor logging initialized")

    def get_system_metrics(self) -> Tuple[float, float]:
        """Get system CPU and memory usage metrics.
        
        Returns:
            Tuple[float, float]: CPU usage percentage and memory usage percentage
            
        Note:
            Handles both single float and list returns from psutil.cpu_percent()
            to ensure consistent float output for comparison operations.
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Handle case where psutil.cpu_percent() returns list instead of float
            if isinstance(cpu_percent, list):
                cpu_percent = sum(cpu_percent) / len(cpu_percent)

            # Ensure always float
            cpu_percent = float(cpu_percent)
            
            memory = psutil.virtual_memory()
            memory_percent = float(memory.percent)
            
            logging.info(f"System metrics retrieved: CPU={cpu_percent}%, Memory={memory_percent}%")
            return cpu_percent, memory_percent
        except Exception as e:
            logging.error(f"Error getting system metrics: {str(e)}")
            return 50.0, 50.0  # Giá trị mặc định nếu lỗi

    def get_batch_size(self, current_batch_size: int = 2) -> int:
        """Calculate optimal batch size based on system metrics.
        
        Args:
            current_batch_size (int): Current batch size being used
            
        Returns:
            int: Recommended batch size between min_batch_size and max_batch_size
            
        Algorithm:
            - Increase batch size if both CPU and memory are below low threshold
            - Decrease batch size if either CPU or memory exceeds high threshold
            - Keep current size if resources are in stable range
        """
        logging.info(f"Calculating batch size, current={current_batch_size}")
        cpu_percent, memory_percent = self.get_system_metrics()
        
        if cpu_percent < self.cpu_threshold_low and memory_percent < self.cpu_threshold_low:
            new_batch_size = min(current_batch_size + 1, self.max_batch_size)
        elif cpu_percent > self.cpu_threshold_high or memory_percent > self.cpu_threshold_high:
            new_batch_size = max(current_batch_size - 1, self.min_batch_size)
        else:
            new_batch_size = current_batch_size
            
        logging.info(f"Calculated batch_size: {new_batch_size}")
        return new_batch_size

    def log_timeout_warning(self, timeout_files: int, total_files: int) -> None:
        """Log warning if timeout rate exceeds acceptable threshold.
        
        Args:
            timeout_files (int): Number of files that timed out
            total_files (int): Total number of files processed
            
        Logs a warning if more than 10% of files time out, indicating
        potential resource constraints or system performance issues.
        """
        logging.info(f"Checking timeout: {timeout_files}/{total_files} files")
        if total_files > 0 and timeout_files > total_files * 0.1:
            logging.warning(f"Warning: {timeout_files}/{total_files} files timed out, consider increasing resources")
        else:
            logging.info("No timeout warning triggered")