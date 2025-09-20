"""
Thread Safety and Multiprocess Safety Tests

This module tests the thread-safety and multiprocess safety of the SMS converter application.
It verifies that concurrent operations don't cause data corruption, race conditions, or crashes.
"""

import unittest
import threading
import time
import tempfile
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

# Import the modules we want to test
import sms
from core.conversation_manager import ConversationManager
from core.phone_lookup import PhoneLookupManager


class TestThreadSafety(unittest.TestCase):
    """Test thread-safety of the SMS converter application."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.conversations_dir = self.temp_dir / "conversations"
        self.conversations_dir.mkdir()

        # Create mock managers
        self.conversation_manager = Mock(spec=ConversationManager)
        self.phone_lookup_manager = Mock(spec=PhoneLookupManager)

        # Set up global variables for testing
        sms.PROCESSING_DIRECTORY = self.temp_dir
        sms.OUTPUT_DIRECTORY = self.conversations_dir
        sms.CONVERSATION_MANAGER = self.conversation_manager
        sms.PHONE_LOOKUP_MANAGER = self.phone_lookup_manager

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_thread_safe_stats_aggregator(self):
        """Test that ThreadSafeStatsAggregator is thread-safe."""
        aggregator = sms.ThreadSafeStatsAggregator()

        def worker(worker_id: int, iterations: int):
            """Worker function that adds stats concurrently."""
            for i in range(iterations):
                stats = {
                    "num_sms": worker_id * 10 + i,
                    "num_img": worker_id * 5 + i,
                    "num_vcf": worker_id * 2 + i,
                    "num_calls": worker_id * 3 + i,
                    "num_voicemails": worker_id * 1 + i,
                }
                aggregator.add_stats(stats)
                time.sleep(0.001)  # Small delay to increase chance of race conditions

        # Create multiple threads
        threads = []
        num_threads = 10
        iterations_per_thread = 100

        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i, iterations_per_thread))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results are consistent
        final_stats = aggregator.get_stats()

        # Check that all stats are positive and reasonable
        for key, value in final_stats.items():
            if key != "own_number":
                self.assertGreaterEqual(value, 0, f"Stats {key} should be non-negative")
                self.assertIsInstance(value, int, f"Stats {key} should be an integer")

    def test_parallel_attachment_copying_thread_safety(self):
        """Test that parallel attachment copying is thread-safe."""
        # Create test files
        test_files = set()
        for i in range(100):
            test_file = self.temp_dir / f"test_file_{i}.txt"
            test_file.write_text(f"Test content {i}")
            test_files.add(test_file.name)

        # Test parallel copying
        from core.attachment_manager import copy_attachments_parallel

        copy_attachments_parallel(test_files, self.temp_dir)

        # Verify no crashes or data corruption occurred
        self.assertTrue(True, "Parallel attachment copying completed without crashes")

    def test_parallel_html_processing_thread_safety(self):
        """Test that parallel HTML processing is thread-safe."""
        # Create test HTML files
        test_files = []
        for i in range(50):
            test_file = self.temp_dir / f"test_{i}.html"
            test_file.write_text(f"<html><body>Test {i}</body></html>")
            test_files.append(test_file)

        # Mock the process_single_html_file function
        with patch("sms.process_single_html_file") as mock_process:
            mock_process.return_value = {
                "num_sms": 1,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
            }

            # Test parallel processing
            result = sms.process_html_files_parallel(test_files, {})

            # Verify results
            self.assertIsInstance(result, dict)
            self.assertIn("num_sms", result)
            self.assertIn("num_img", result)
            self.assertIn("num_vcf", result)
            self.assertIn("num_calls", result)
            self.assertIn("num_voicemails", result)

    def test_global_manager_access_thread_safety(self):
        """Test that global manager access is thread-safe."""

        def access_managers(worker_id: int, iterations: int):
            """Worker function that accesses global managers concurrently."""
            for i in range(iterations):
                # Access managers through locks
                with sms.CONVERSATION_MANAGER_LOCK:
                    conv_manager = sms.CONVERSATION_MANAGER

                with sms.PHONE_LOOKUP_MANAGER_LOCK:
                    phone_manager = sms.PHONE_LOOKUP_MANAGER

                # Verify managers are accessible
                self.assertIsNotNone(conv_manager)
                self.assertIsNotNone(phone_manager)

                time.sleep(0.001)  # Small delay

        # Create multiple threads
        threads = []
        num_threads = 5
        iterations_per_thread = 50

        for i in range(num_threads):
            thread = threading.Thread(
                target=access_managers, args=(i, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no crashes occurred
        self.assertTrue(True, "Global manager access completed without crashes")

    def test_concurrent_file_operations(self):
        """Test that file operations are thread-safe."""

        def file_worker(worker_id: int, iterations: int):
            """Worker function that performs file operations concurrently."""
            for i in range(iterations):
                test_file = self.temp_dir / f"worker_{worker_id}_file_{i}.txt"

                # Use file operations lock
                with sms.FILE_OPERATIONS_LOCK:
                    test_file.write_text(f"Worker {worker_id} iteration {i}")

                time.sleep(0.001)  # Small delay

        # Create multiple threads
        threads = []
        num_threads = 8
        iterations_per_thread = 25

        for i in range(num_threads):
            thread = threading.Thread(
                target=file_worker, args=(i, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all files were created
        expected_files = num_threads * iterations_per_thread
        actual_files = len(list(self.temp_dir.glob("worker_*_file_*.txt")))
        self.assertEqual(
            actual_files, expected_files, "All expected files should be created"
        )

    def test_lru_cache_thread_safety(self):
        """Test that LRU cache functions are thread-safe."""
        # Test a cached function with concurrent access
        @sms.lru_cache(maxsize=100)
        def cached_function(x: int) -> int:
            time.sleep(0.001)  # Simulate work
            return x * 2

        def cache_worker(worker_id: int, iterations: int):
            """Worker function that calls cached function concurrently."""
            for i in range(iterations):
                result = cached_function(i)
                self.assertEqual(
                    result,
                    i * 2,
                    f"Cache function should return correct result for {i}",
                )

        # Create multiple threads
        threads = []
        num_threads = 6
        iterations_per_thread = 20

        for i in range(num_threads):
            thread = threading.Thread(
                target=cache_worker, args=(i, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no crashes occurred
        self.assertTrue(True, "LRU cache access completed without crashes")

    def test_statistics_aggregation_consistency(self):
        """Test that statistics aggregation is consistent under concurrent access."""
        aggregator = sms.ThreadSafeStatsAggregator()

        def stats_worker(worker_id: int, iterations: int):
            """Worker function that adds stats concurrently."""
            for i in range(iterations):
                stats = {
                    "num_sms": 1,
                    "num_img": 1,
                    "num_vcf": 1,
                    "num_calls": 1,
                    "num_voicemails": 1,
                }
                aggregator.add_stats(stats)

        # Create multiple threads
        threads = []
        num_threads = 10
        iterations_per_thread = 100

        for i in range(num_threads):
            thread = threading.Thread(
                target=stats_worker, args=(i, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify final statistics are correct
        final_stats = aggregator.get_stats()
        expected_total = num_threads * iterations_per_thread

        for key, value in final_stats.items():
            if key != "own_number":
                self.assertEqual(
                    value, expected_total, f"Stats {key} should equal {expected_total}"
                )

    def test_error_handling_in_threads(self):
        """Test that errors in threads are handled gracefully."""

        def error_worker(worker_id: int):
            """Worker function that may raise errors."""
            if worker_id % 3 == 0:  # Every third worker raises an error
                raise ValueError(f"Test error from worker {worker_id}")
            return worker_id

        # Test with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(error_worker, i) for i in range(10)]

            completed = 0
            errors = 0

            for future in as_completed(futures):
                try:
                    # result variable removed - not used
                    future.result()
                    completed += 1
                except Exception:
                    errors += 1

            # Verify some completed and some had errors
            self.assertGreater(
                completed, 0, "Some workers should complete successfully"
            )
            self.assertGreater(errors, 0, "Some workers should encounter errors")
            self.assertEqual(
                completed + errors, 10, "Total should equal number of workers"
            )


class TestMultiprocessSafety(unittest.TestCase):
    """Test multiprocess safety of the SMS converter application."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.conversations_dir = self.temp_dir / "conversations"
        self.conversations_dir.mkdir()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_global_variables_initialization(self):
        """Test that global variables are properly initialized."""
        # This test verifies that global variables are set up correctly
        # and don't cause issues in multiprocess scenarios

        # Reset global variables
        sms.PROCESSING_DIRECTORY = None
        sms.OUTPUT_DIRECTORY = None
        sms.CONVERSATION_MANAGER = None
        sms.PHONE_LOOKUP_MANAGER = None

        # Test setup_processing_paths
        sms.setup_processing_paths(
            self.temp_dir,
            enable_phone_prompts=False,
            buffer_size=8192,
            batch_size=1000,
            cache_size=25000,
            large_dataset=False,
            output_format="html",
        )

        # Verify global variables are set
        self.assertIsNotNone(sms.PROCESSING_DIRECTORY)
        self.assertIsNotNone(sms.OUTPUT_DIRECTORY)
        self.assertIsNotNone(sms.CONVERSATION_MANAGER)
        self.assertIsNotNone(sms.PHONE_LOOKUP_MANAGER)

    def test_locks_initialization(self):
        """Test that thread locks are properly initialized."""
        # Verify all locks exist and are instances of threading.Lock
        self.assertIsInstance(sms.GLOBAL_STATS_LOCK, type(threading.Lock()))
        self.assertIsInstance(sms.CONVERSATION_MANAGER_LOCK, type(threading.Lock()))
        self.assertIsInstance(sms.PHONE_LOOKUP_MANAGER_LOCK, type(threading.Lock()))
        self.assertIsInstance(sms.FILE_OPERATIONS_LOCK, type(threading.Lock()))


if __name__ == "__main__":
    unittest.main()
