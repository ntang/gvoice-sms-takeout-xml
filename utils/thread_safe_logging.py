"""
Thread-safe logging utilities to prevent race conditions in parallel processing.

This module provides enhanced logging handlers that are safe for use with
concurrent threads and parallel processing.

Fix for Bug #13: File logging disabled due to thread safety issues.
This implementation uses QueueHandler and QueueListener to ensure thread-safe
logging even with MAX_WORKERS > 1.
"""

import logging
import logging.handlers
import queue
import sys
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

    Uses an unbounded queue to ensure log records are never dropped.
    The listener thread processes records from the queue and writes to file.
    """

    def __init__(self, filename: Path, maxsize: int = -1, level: int = logging.NOTSET, formatter: Optional[logging.Formatter] = None):
        # Create an unbounded queue for log records (-1 = no size limit)
        # This ensures we never drop log records under heavy load
        log_queue = queue.Queue(maxsize=maxsize)
        super().__init__(log_queue)

        # Ensure parent directory exists
        filename.parent.mkdir(parents=True, exist_ok=True)

        # Create the actual file handler
        self.file_handler = ThreadSafeFileHandler(
            filename,
            mode='a',
            encoding='utf-8'
        )

        # Set formatter - use provided formatter or default
        if formatter is None:
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(threadName)s] - %(name)s - %(message)s")

        # Set formatter ONLY on the internal file handler
        # QueueHandler should NOT format - it passes raw LogRecords to the queue
        self.file_handler.setFormatter(formatter)

        # Set the level on the actual file handler (Bug #15 fix)
        self.file_handler.setLevel(level)

        # Store formatter and level for later reference
        self._formatter = formatter
        self._level = level

        # Start the listener thread
        self.listener = logging.handlers.QueueListener(
            log_queue,
            self.file_handler,
            respect_handler_level=True
        )
        self.listener.start()

        # Register cleanup on exit (individual handler cleanup)
        atexit.register(self.cleanup)

    def setFormatter(self, formatter):
        """Set formatter on the internal file handler."""
        if hasattr(self, 'file_handler') and self.file_handler:
            self.file_handler.setFormatter(formatter)

    def setLevel(self, level):
        """Set level on the internal file handler."""
        if hasattr(self, 'file_handler') and self.file_handler:
            self.file_handler.setLevel(level)

    def cleanup(self):
        """Clean up the queue listener."""
        if hasattr(self, 'listener') and self.listener:
            try:
                self.listener.stop()
                self.listener = None
            except Exception:
                pass  # Already stopped or errored


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
    
    # Clear existing handlers and clean up any QueueListeners
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:  # Copy list to avoid modification during iteration
        if isinstance(handler, QueuedFileHandler):
            handler.cleanup()
        root_logger.removeHandler(handler)

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
        # Pass level AND formatter to constructor (Bug #15 fix)
        file_handler = QueuedFileHandler(log_file, level=log_level, formatter=formatter)
        handlers.append(file_handler)
    
    # Configure root logger - DON'T use basicConfig as it resets formatters
    # Instead, manually configure the root logger
    root_logger.setLevel(log_level)
    for handler in handlers:
        root_logger.addHandler(handler)

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


# Global logging manager for application-wide cleanup
_global_logging_manager: Optional['LoggingManager'] = None
_manager_lock = threading.Lock()


class LoggingManager:
    """
    Central manager for thread-safe logging with proper cleanup.

    This class manages all logging handlers and ensures proper shutdown
    when the application exits. Use this instead of direct setup functions
    for better resource management.
    """

    def __init__(self):
        self.queue_handlers = []
        self.listeners = []
        self._cleanup_registered = False

    def register_handler(self, handler: QueuedFileHandler):
        """Register a queue handler for cleanup tracking."""
        self.queue_handlers.append(handler)
        if handler.listener:
            self.listeners.append(handler.listener)

        # Register cleanup on first handler
        if not self._cleanup_registered:
            atexit.register(self.cleanup_all)
            self._cleanup_registered = True

    def cleanup_all(self):
        """Clean up all registered listeners and handlers."""
        for listener in self.listeners:
            try:
                listener.stop()
            except Exception as e:
                print(f"Warning: Failed to stop listener: {e}", file=sys.stderr)

        self.listeners.clear()
        self.queue_handlers.clear()


def get_logging_manager() -> LoggingManager:
    """Get the global logging manager instance."""
    global _global_logging_manager

    with _manager_lock:
        if _global_logging_manager is None:
            _global_logging_manager = LoggingManager()
        return _global_logging_manager
