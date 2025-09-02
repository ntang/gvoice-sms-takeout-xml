"""
Enhanced logging utilities for SMS processing system.

Provides structured logging with correlation IDs, metrics collection,
and better observability for debugging and monitoring.
"""

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import threading

# Thread-local storage for correlation IDs
_thread_local = threading.local()


@dataclass
class ProcessingMetrics:
    """Metrics collected during file processing."""
    file_id: str
    conversation_id: Optional[str] = None
    processing_stage: str = "unknown"
    file_format: str = "unknown"
    risk_factors: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    processing_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    messages_processed: int = 0
    messages_skipped: int = 0
    participants_extracted: int = 0
    attachments_found: int = 0

    def __post_init__(self):
        """Calculate processing time when end_time is set."""
        if self.end_time is not None:
            self.processing_time_ms = (self.end_time - self.start_time) * 1000

    def mark_success(self):
        """Mark processing as successful."""
        self.success = True
        self.end_time = time.time()

    def mark_failure(self, error_message: str):
        """Mark processing as failed."""
        self.success = False
        self.error_message = error_message
        self.end_time = time.time()

    def add_risk_factor(self, factor: str):
        """Add a risk factor to the metrics."""
        if factor not in self.risk_factors:
            self.risk_factors.append(factor)


class CorrelationContext:
    """Context manager for correlation IDs in logging."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]
        self.previous_correlation_id = None
    
    def __enter__(self):
        self.previous_correlation_id = getattr(_thread_local, 'correlation_id', None)
        _thread_local.correlation_id = self.correlation_id
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_correlation_id:
            _thread_local.correlation_id = self.previous_correlation_id
        else:
            delattr(_thread_local, 'correlation_id')


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID for this thread."""
    return getattr(_thread_local, 'correlation_id', None)


def set_correlation_id(correlation_id: str):
    """Set the correlation ID for this thread."""
    _thread_local.correlation_id = correlation_id


class StructuredFormatter(logging.Formatter):
    """Custom formatter that includes correlation IDs and structured data."""
    
    def format(self, record):
        # Add correlation ID to the record
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = get_correlation_id() or 'N/A'
        
        # Add timestamp in ISO format
        if not hasattr(record, 'iso_timestamp'):
            record.iso_timestamp = datetime.fromtimestamp(record.created).isoformat()
        
        # Format the message with correlation ID
        if record.correlation_id and record.correlation_id != 'N/A':
            record.msg = f"[{record.correlation_id}] {record.msg}"
        
        return super().format(record)


class MetricsCollector:
    """Collects and manages processing metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, ProcessingMetrics] = {}
        self.lock = threading.Lock()
    
    def start_processing(self, file_id: str, **kwargs) -> ProcessingMetrics:
        """Start tracking metrics for a file."""
        with self.lock:
            metrics = ProcessingMetrics(file_id=file_id, **kwargs)
            self.metrics[file_id] = metrics
            return metrics
    
    def update_metrics(self, file_id: str, **kwargs):
        """Update metrics for a file."""
        with self.lock:
            if file_id in self.metrics:
                for key, value in kwargs.items():
                    if hasattr(self.metrics[file_id], key):
                        setattr(self.metrics[file_id], key, value)
    
    def get_metrics(self, file_id: str) -> Optional[ProcessingMetrics]:
        """Get metrics for a specific file."""
        return self.metrics.get(file_id)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics."""
        with self.lock:
            if not self.metrics:
                return {"error": "No metrics collected"}
            
            total_files = len(self.metrics)
            successful_files = len([m for m in self.metrics.values() if m.success])
            failed_files = total_files - successful_files
            
            total_processing_time = sum(
                m.processing_time_ms or 0 for m in self.metrics.values()
            )
            
            total_messages = sum(
                m.messages_processed for m in self.metrics.values()
            )
            
            total_participants = sum(
                m.participants_extracted for m in self.metrics.values()
            )
            
            risk_factors = {}
            for metrics in self.metrics.values():
                for factor in metrics.risk_factors:
                    risk_factors[factor] = risk_factors.get(factor, 0) + 1
            
            return {
                "total_files_processed": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "success_rate": f"{(successful_files / total_files) * 100:.1f}%" if total_files > 0 else "0%",
                "total_processing_time_ms": total_processing_time,
                "average_processing_time_ms": total_processing_time / total_files if total_files > 0 else 0,
                "total_messages_processed": total_messages,
                "total_participants_extracted": total_participants,
                "risk_factor_distribution": risk_factors,
                "processing_efficiency": {
                    "messages_per_file": total_messages / total_files if total_files > 0 else 0,
                    "participants_per_file": total_participants / total_files if total_files > 0 else 0,
                    "processing_time_per_message": total_processing_time / total_messages if total_messages > 0 else 0
                }
            }


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics_collector


@contextmanager
def track_processing(file_id: str, **kwargs):
    """Context manager for tracking file processing metrics."""
    metrics = metrics_collector.start_processing(file_id, **kwargs)
    correlation_id = str(uuid.uuid4())[:8]
    
    try:
        with CorrelationContext(correlation_id):
            set_correlation_id(correlation_id)
            yield metrics
            metrics.mark_success()
    except Exception as e:
        metrics.mark_failure(str(e))
        raise
    finally:
        # Update the metrics with final values
        metrics.end_time = time.time()
        if hasattr(metrics, 'processing_time_ms'):
            metrics.processing_time_ms = (metrics.end_time - metrics.start_time) * 1000


def log_processing_event(
    logger: logging.Logger,
    event: str,
    file_id: str,
    processing_stage: str,
    **kwargs
):
    """Log a processing event with structured data."""
    extra_data = {
        "file_id": file_id,
        "processing_stage": processing_stage,
        "correlation_id": get_correlation_id(),
        "timestamp": datetime.now().isoformat(),
        **kwargs
    }
    
    logger.info(f"Processing event: {event}", extra=extra_data)


def log_risk_factor(
    logger: logging.Logger,
    file_id: str,
    factor: str,
    description: str,
    severity: str = "MEDIUM"
):
    """Log a risk factor with structured data."""
    extra_data = {
        "file_id": file_id,
        "risk_factor": factor,
        "severity": severity,
        "correlation_id": get_correlation_id(),
        "timestamp": datetime.now().isoformat()
    }
    
    log_level = logging.WARNING if severity == "HIGH" else logging.INFO
    logger.log(log_level, f"Risk factor detected: {factor} - {description}", extra=extra_data)
    
    # Update metrics if available
    metrics = metrics_collector.get_metrics(file_id)
    if metrics:
        metrics.add_risk_factor(factor)
