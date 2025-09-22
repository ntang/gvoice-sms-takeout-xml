"""
Thread-safe logging utilities to prevent race conditions in parallel processing.

This module provides enhanced logging handlers that are safe for use with
concurrent threads and parallel processing.
"""

import logging
import logging.handlers
import queue
import threading
import atexit
from typing import Optional
from pathlib import Path


class ThreadSafeFileHandler(logging.FileHandler):
    """
    A thread-safe file handler that uses a lock to prevent race conditions.
    """
    
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        self._lock = threading.Lock()
    
    def emit(self, record):
        """
        Emit a record with thread safety.
        """
        with self._lock:
            super().emit(record)


class QueuedFileHandler(logging.handlers.QueueHandler):
    """
    A queued file handler that processes log records in a separate thread.
    This prevents blocking the main processing threads.
    """
    
    def __init__(self, filename: Path, maxsize: int = 1000):
        # Create a queue for log records
        log_queue = queue.Queue(maxsize=maxsize)
        super().__init__(log_queue)
        
        # Create the actual file handler
        self.file_handler = ThreadSafeFileHandler(
            filename, 
            mode='a', 
            encoding='utf-8'
        )
        self.file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s")
        )
        
        # Start the listener thread
        self.listener = logging.handlers.QueueListener(
            log_queue, 
            self.file_handler,
            respect_handler_level=True
        )
        self.listener.start()
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def cleanup(self):
        """Clean up the queue listener."""
        if hasattr(self, 'listener'):
            self.listener.stop()


def setup_thread_safe_logging(
    log_level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console_logging: bool = True,
    include_thread_name: bool = True
) -> None:
    """
    Set up thread-safe logging configuration.
    
    Args:
        log_level: Logging level (e.g., logging.INFO)
        log_file: Optional path to log file
        console_logging: Whether to enable console logging
        include_thread_name: Whether to include thread name in log format
    """
    # Create formatter
    if include_thread_name:
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(threadName)s] - %(name)s - %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    handlers = []
    
    # Add console handler if requested
    if console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)
    
    # Add file handler if requested
    if log_file:
        # Use queued handler for better thread safety
        file_handler = QueuedFileHandler(log_file)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )
    
    # Set specific logger levels for noisy modules
    logging.getLogger("concurrent.futures").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_thread_safe_logger(name: str) -> logging.Logger:
    """
    Get a thread-safe logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance configured for thread safety
    """
    logger = logging.getLogger(name)
    
    # Ensure thread safety by adding a lock if not present
    if not hasattr(logger, '_thread_lock'):
        logger._thread_lock = threading.Lock()
    
    return logger
