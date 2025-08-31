"""
Memory monitoring and profiling utilities for Google Voice SMS Converter.

This module provides comprehensive memory usage tracking, leak detection,
and memory optimization recommendations.
"""

import os
import time
import threading
import psutil
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time."""
    timestamp: float
    memory_mb: float
    memory_percent: float
    virtual_memory_mb: float
    open_files: int
    threads: int
    cpu_percent: float
    operation_name: str
    additional_info: Dict[str, Any]

class MemoryMonitor:
    """
    Comprehensive memory monitoring and profiling system.
    
    This class tracks memory usage over time, detects potential memory leaks,
    and provides optimization recommendations.
    """
    
    def __init__(self, enable_monitoring: bool = True, threshold_mb: float = 1000.0):
        """
        Initialize the memory monitor.
        
        Args:
            enable_monitoring: Whether to enable memory monitoring
            threshold_mb: Memory threshold in MB for warnings
        """
        self.enable_monitoring = enable_monitoring
        self.threshold_mb = threshold_mb
        self.snapshots: List[MemorySnapshot] = []
        self.monitoring_lock = threading.Lock()
        self.start_time = time.time()
        self.process = psutil.Process()
        
        # Memory leak detection
        self.leak_threshold = 0.1  # 10% increase over time
        self.leak_check_interval = 60  # Check every 60 seconds
        self.last_leak_check = time.time()
        
        # Performance tracking
        self.operation_memory_usage: Dict[str, List[float]] = {}
        self.peak_memory = 0.0
        self.peak_memory_time = 0.0
        
        logger.info(f"Memory monitor initialized (threshold: {threshold_mb:.1f}MB)")
    
    def take_snapshot(self, operation_name: str = "unknown", additional_info: Optional[Dict[str, Any]] = None) -> MemorySnapshot:
        """
        Take a snapshot of current memory usage.
        
        Args:
            operation_name: Name of the operation being monitored
            additional_info: Additional context information
            
        Returns:
            MemorySnapshot object with current memory state
        """
        if not self.enable_monitoring:
            return MemorySnapshot(0, 0, 0, 0, 0, 0, 0, operation_name, {})
        
        try:
            memory_info = self.process.memory_info()
            virtual_memory = psutil.virtual_memory()
            
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                memory_mb=memory_info.rss / 1024 / 1024,
                memory_percent=self.process.memory_percent(),
                virtual_memory_mb=virtual_memory.used / 1024 / 1024,
                open_files=len(self.process.open_files()),
                threads=self.process.num_threads(),
                cpu_percent=self.process.cpu_percent(),
                operation_name=operation_name,
                additional_info=additional_info or {}
            )
            
            with self.monitoring_lock:
                self.snapshots.append(snapshot)
                
                # Track peak memory
                if snapshot.memory_mb > self.peak_memory:
                    self.peak_memory = snapshot.memory_mb
                    self.peak_memory_time = snapshot.timestamp
                
                # Track operation-specific memory usage
                if operation_name not in self.operation_memory_usage:
                    self.operation_memory_usage[operation_name] = []
                self.operation_memory_usage[operation_name].append(snapshot.memory_mb)
                
                # Check for memory leaks
                self._check_for_memory_leaks()
                
                # Check threshold warnings
                if snapshot.memory_mb > self.threshold_mb:
                    logger.warning(f"⚠️  Memory usage ({snapshot.memory_mb:.1f}MB) exceeds threshold ({self.threshold_mb:.1f}MB)")
            
            return snapshot
            
        except Exception as e:
            logger.warning(f"Failed to take memory snapshot: {e}")
            return MemorySnapshot(0, 0, 0, 0, 0, 0, 0, operation_name, {})
    
    def _check_for_memory_leaks(self) -> None:
        """Check for potential memory leaks based on usage patterns."""
        current_time = time.time()
        if current_time - self.last_leak_check < self.leak_check_interval:
            return
        
        self.last_leak_check = current_time
        
        if len(self.snapshots) < 10:  # Need enough data points
            return
        
        try:
            # Calculate memory growth rate over the last 10 snapshots
            recent_snapshots = self.snapshots[-10:]
            memory_values = [s.memory_mb for s in recent_snapshots]
            
            if len(memory_values) >= 2:
                # Calculate linear regression slope
                x_values = list(range(len(memory_values)))
                slope = self._calculate_slope(x_values, memory_values)
                
                # If memory is growing consistently, warn about potential leak
                if slope > self.leak_threshold:
                    logger.warning(f"⚠️  Potential memory leak detected: memory growing at {slope:.2f}MB per snapshot")
                    logger.warning("  Consider reviewing memory-intensive operations or reducing batch sizes")
                    
        except Exception as e:
            logger.debug(f"Memory leak check failed: {e}")
    
    def _calculate_slope(self, x_values: List[int], y_values: List[float]) -> float:
        """Calculate the slope of a linear regression line."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            return slope
        except ZeroDivisionError:
            return 0.0
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of memory usage.
        
        Returns:
            Dictionary containing memory usage statistics
        """
        if not self.snapshots:
            return {"error": "No memory snapshots available"}
        
        try:
            latest = self.snapshots[-1]
            memory_values = [s.memory_mb for s in self.snapshots]
            
            summary = {
                "current_memory_mb": latest.memory_mb,
                "current_memory_percent": latest.memory_percent,
                "peak_memory_mb": self.peak_memory,
                "peak_memory_time": time.strftime("%H:%M:%S", time.localtime(self.peak_memory_time)),
                "average_memory_mb": sum(memory_values) / len(memory_values),
                "min_memory_mb": min(memory_values),
                "max_memory_mb": max(memory_values),
                "total_snapshots": len(self.snapshots),
                "monitoring_duration_seconds": time.time() - self.start_time,
                "open_files": latest.open_files,
                "threads": latest.threads,
                "cpu_percent": latest.cpu_percent
            }
            
            # Add operation-specific memory usage
            for operation, memory_list in self.operation_memory_usage.items():
                if memory_list:
                    summary[f"{operation}_avg_memory_mb"] = sum(memory_list) / len(memory_list)
                    summary[f"{operation}_peak_memory_mb"] = max(memory_list)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate memory summary: {e}")
            return {"error": f"Failed to generate summary: {e}"}
    
    def generate_optimization_recommendations(self) -> List[str]:
        """
        Generate memory optimization recommendations based on usage patterns.
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        if not self.snapshots:
            return ["No memory data available for recommendations"]
        
        try:
            summary = self.get_memory_summary()
            if "error" in summary:
                return [summary["error"]]
            
            current_memory = summary["current_memory_mb"]
            peak_memory = summary["peak_memory_mb"]
            open_files = summary["open_files"]
            threads = summary["threads"]
            
            # Memory usage recommendations
            if current_memory > 500:
                recommendations.append("Consider reducing batch sizes to lower memory usage")
            
            if peak_memory > 1000:
                recommendations.append("Peak memory usage is high - consider memory-efficient processing mode")
            
            # File handle recommendations
            if open_files > 100:
                recommendations.append("High number of open files - consider reducing parallel operations")
            
            # Thread recommendations
            if threads > 20:
                recommendations.append("High thread count - consider reducing max_workers setting")
            
            # General recommendations
            if len(self.snapshots) > 100:
                recommendations.append("Long-running process - consider periodic memory cleanup")
            
            if not recommendations:
                recommendations.append("Memory usage appears optimal - no specific recommendations")
                
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
            recommendations.append(f"Error generating recommendations: {e}")
        
        return recommendations
    
    def cleanup_old_snapshots(self, max_snapshots: int = 1000) -> None:
        """
        Clean up old snapshots to prevent memory bloat.
        
        Args:
            max_snapshots: Maximum number of snapshots to keep
        """
        with self.monitoring_lock:
            if len(self.snapshots) > max_snapshots:
                # Keep the most recent snapshots
                self.snapshots = self.snapshots[-max_snapshots:]
                logger.debug(f"Cleaned up memory snapshots, keeping {max_snapshots} most recent")
    
    def reset_monitoring(self) -> None:
        """Reset all monitoring data."""
        with self.monitoring_lock:
            self.snapshots.clear()
            self.operation_memory_usage.clear()
            self.peak_memory = 0.0
            self.peak_memory_time = 0.0
            self.start_time = time.time()
            logger.info("Memory monitoring data reset")

# Global memory monitor instance
_memory_monitor: Optional[MemoryMonitor] = None

def get_memory_monitor() -> MemoryMonitor:
    """Get the global memory monitor instance."""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor()
    return _memory_monitor

def monitor_memory_usage(operation_name: str = "unknown", additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """
    Convenience function to monitor memory usage for an operation.
    
    Args:
        operation_name: Name of the operation
        additional_info: Additional context information
        
    Returns:
        Dictionary with memory usage metrics
    """
    monitor = get_memory_monitor()
    snapshot = monitor.take_snapshot(operation_name, additional_info)
    
    return {
        "memory_mb": snapshot.memory_mb,
        "memory_percent": snapshot.memory_percent,
        "virtual_memory_mb": snapshot.virtual_memory_mb,
        "open_files": snapshot.open_files,
        "threads": snapshot.threads,
        "cpu_percent": snapshot.cpu_percent
    }

def get_memory_summary() -> Dict[str, Any]:
    """Get memory usage summary."""
    monitor = get_memory_monitor()
    return monitor.get_memory_summary()

def generate_memory_recommendations() -> List[str]:
    """Generate memory optimization recommendations."""
    monitor = get_memory_monitor()
    return monitor.generate_optimization_recommendations()
