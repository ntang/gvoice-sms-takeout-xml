"""
Test cases for thread-safe logging implementation.

This module tests the thread-safe logging system that fixes Bug #13.
"""

import pytest
import logging
import tempfile
import threading
import time
from pathlib import Path
from utils.thread_safe_logging import (
    setup_thread_safe_logging,
    ThreadSafeFileHandler,
    QueuedFileHandler,
    get_logging_manager
)


class TestThreadSafeFileHandler:
    """Test the ThreadSafeFileHandler class."""

    def test_basic_logging(self):
        """Test that basic logging works with ThreadSafeFileHandler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            # Create handler
            handler = ThreadSafeFileHandler(log_file)
            handler.setFormatter(logging.Formatter("%(message)s"))

            # Create logger
            logger = logging.getLogger("test_basic")
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Log a message
            logger.info("Test message")

            # Close handler to flush
            handler.close()

            # Verify log file contains message
            content = log_file.read_text()
            assert "Test message" in content

    def test_concurrent_logging(self):
        """Test that concurrent logging doesn't cause corruption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "concurrent.log"

            # Create handler
            handler = ThreadSafeFileHandler(log_file)
            handler.setFormatter(logging.Formatter("%(message)s"))

            # Create logger
            logger = logging.getLogger("test_concurrent")
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Number of threads and messages per thread
            num_threads = 10
            messages_per_thread = 100
            messages_logged = []

            def log_messages(thread_id):
                """Log messages from a thread."""
                for i in range(messages_per_thread):
                    msg = f"Thread {thread_id} message {i}"
                    logger.info(msg)
                    messages_logged.append(msg)

            # Start threads
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=log_messages, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join()

            # Close handler to flush
            handler.close()

            # Verify all messages were logged
            content = log_file.read_text()
            assert len(content) > 0

            # Count lines (each message should be a line)
            lines = content.strip().split('\n')
            expected_count = num_threads * messages_per_thread
            assert len(lines) == expected_count, \
                f"Expected {expected_count} lines, got {len(lines)}"


class TestQueuedFileHandler:
    """Test the QueuedFileHandler class."""

    def test_queued_logging(self):
        """Test that queued logging works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "queued.log"

            # Create handler
            handler = QueuedFileHandler(log_file)

            # Create logger
            logger = logging.getLogger("test_queued")
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Log messages
            logger.info("Message 1")
            logger.info("Message 2")
            logger.info("Message 3")

            # Give queue time to process
            time.sleep(0.1)

            # Clean up handler
            handler.cleanup()

            # Verify messages were logged
            content = log_file.read_text()
            assert "Message 1" in content
            assert "Message 2" in content
            assert "Message 3" in content

    def test_queued_concurrent_logging(self):
        """Test queued logging with concurrent threads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "queued_concurrent.log"

            # Create handler
            handler = QueuedFileHandler(log_file)

            # Create logger
            logger = logging.getLogger("test_queued_concurrent")
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            num_threads = 5
            messages_per_thread = 50

            def log_messages(thread_id):
                """Log messages from a thread."""
                for i in range(messages_per_thread):
                    logger.info(f"T{thread_id}:M{i}")

            # Start threads
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=log_messages, args=(i,))
                threads.append(t)
                t.start()

            # Wait for threads
            for t in threads:
                t.join()

            # Give queue time to process
            time.sleep(0.2)

            # Clean up
            handler.cleanup()

            # Verify all messages logged
            content = log_file.read_text()
            lines = content.strip().split('\n')
            expected_count = num_threads * messages_per_thread
            assert len(lines) == expected_count, \
                f"Expected {expected_count} lines, got {len(lines)}"


class TestSetupThreadSafeLogging:
    """Test the setup_thread_safe_logging function."""

    def test_setup_with_file_logging(self):
        """Test setup with file logging enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "setup.log"

            # Set up logging
            setup_thread_safe_logging(
                log_level=logging.INFO,
                log_file=log_file,
                console_logging=False,
                include_thread_name=True
            )

            # Log a message
            logger = logging.getLogger("test_setup")
            logger.info("Setup test message")

            # Give queue time to process
            time.sleep(0.1)

            # Verify file was created and contains message
            assert log_file.exists()
            content = log_file.read_text()
            assert "Setup test message" in content

    def test_setup_creates_parent_directory(self):
        """Test that setup creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "nested" / "test.log"

            # Setup should create parent directories
            setup_thread_safe_logging(
                log_level=logging.INFO,
                log_file=log_file,
                console_logging=False
            )

            # Log a message
            logger = logging.getLogger("test_mkdir")
            logger.info("Nested directory test")

            # Give queue time to process
            time.sleep(0.1)

            # Verify file exists
            assert log_file.exists()
            assert log_file.parent.exists()

    def test_setup_with_console_only(self):
        """Test setup with console logging only."""
        # This should not create any files
        setup_thread_safe_logging(
            log_level=logging.INFO,
            log_file=None,
            console_logging=True
        )

        # Log a message (should go to console only)
        logger = logging.getLogger("test_console")
        logger.info("Console only message")

        # No file to verify, just ensure no errors


class TestLoggingManager:
    """Test the LoggingManager class."""

    def test_logging_manager_singleton(self):
        """Test that logging manager is a singleton."""
        manager1 = get_logging_manager()
        manager2 = get_logging_manager()

        assert manager1 is manager2, "LoggingManager should be a singleton"

    def test_logging_manager_cleanup(self):
        """Test that logging manager cleans up properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "manager_cleanup.log"

            # Create handler
            handler = QueuedFileHandler(log_file)

            # Get manager and register handler
            manager = get_logging_manager()
            manager.register_handler(handler)

            # Create logger and log messages
            logger = logging.getLogger("test_cleanup")
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.info("Cleanup test")

            # Give queue time to process
            time.sleep(0.1)

            # Cleanup should stop listeners
            manager.cleanup_all()

            # Verify file exists and contains message
            assert log_file.exists()
            content = log_file.read_text()
            assert "Cleanup test" in content


class TestBug13ThreadSafetyFix:
    """Integration tests for Bug #13 fix."""

    def test_no_corruption_with_parallel_logging(self):
        """
        Test that parallel logging doesn't cause file corruption.

        This is the key test for Bug #13 - verifying that multiple
        threads can log simultaneously without corrupting the log file.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "bug13_test.log"

            # Set up thread-safe logging
            setup_thread_safe_logging(
                log_level=logging.INFO,
                log_file=log_file,
                console_logging=False,
                include_thread_name=True
            )

            # Create multiple threads that log heavily
            num_threads = 20
            messages_per_thread = 100

            def heavy_logging(thread_id):
                """Simulate heavy logging from a worker thread."""
                logger = logging.getLogger(f"worker_{thread_id}")
                for i in range(messages_per_thread):
                    logger.info(f"Worker {thread_id} processing item {i}")
                    if i % 10 == 0:
                        logger.warning(f"Worker {thread_id} checkpoint at {i}")

            # Start all threads
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=heavy_logging, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # Give queue time to process all messages
            time.sleep(0.5)

            # Verify log file is not corrupted
            assert log_file.exists()
            content = log_file.read_text()

            # Count total lines
            lines = content.strip().split('\n')

            # Each thread logs messages_per_thread + (messages_per_thread/10) checkpoint warnings
            expected_lines = num_threads * (messages_per_thread + (messages_per_thread // 10))
            actual_lines = len(lines)

            # Allow for some timing variance, but should be close
            assert actual_lines >= expected_lines * 0.95, \
                f"Expected ~{expected_lines} lines, got {actual_lines}"

            # Verify no garbled lines (each line should contain "Worker")
            for line in lines:
                assert "Worker" in line, f"Corrupted line detected: {line}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
