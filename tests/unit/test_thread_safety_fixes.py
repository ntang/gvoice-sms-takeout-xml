"""
Thread-Safety Fixes - Comprehensive Test Suite

This module tests the specific thread-safety issues identified in THREAD_SAFETY_ISSUES.md:
- Issue #1: PhoneLookupManager dictionary access race conditions
- Issue #2: ConversationManager.get_total_stats() unprotected iteration
- Issue #3: Content type tracking race condition
- Issue #4: finalize() dictionary iteration safety

These tests demonstrate the bugs exist (should fail before fixes) and validate
the fixes work correctly (should pass after fixes).
"""

import unittest
import threading
import time
import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.phone_lookup import PhoneLookupManager
from core.conversation_manager import ConversationManager
from core.processing_config import ProcessingConfig


class TestPhoneLookupManagerThreadSafety(unittest.TestCase):
    """Test thread-safety of PhoneLookupManager dictionary access (Issue #1)."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.phone_lookup_file = self.temp_dir / "phone_lookup.txt"

        # Create empty phone lookup file
        self.phone_lookup_file.write_text("")

        # Create manager
        self.manager = PhoneLookupManager(
            self.phone_lookup_file,
            enable_prompts=False
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_get_alias_read_write_race(self):
        """
        Test concurrent reads and writes to phone_aliases dictionary.

        This test stresses the get_alias() method which both reads and writes
        to the phone_aliases dictionary without proper locking.

        Expected behavior BEFORE fix: Potential data corruption, missing entries
        Expected behavior AFTER fix: All phone numbers properly mapped
        """
        num_threads = 16
        iterations_per_thread = 100

        def worker(worker_id: int):
            """Worker that concurrently reads/writes phone aliases."""
            for i in range(iterations_per_thread):
                phone_number = f"+1555{worker_id:02d}{i:04d}"
                alias_name = f"Person_{worker_id}_{i}"

                # This triggers write to phone_aliases
                self.manager.add_alias(phone_number, alias_name)

                # Then read it back to test concurrent read/write
                retrieved_alias = self.manager.get_alias(phone_number, soup=None)

                # Verify we got the correct alias back
                self.assertEqual(retrieved_alias, alias_name)

        # Run concurrent workers
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all phone numbers are in the dictionary
        expected_count = num_threads * iterations_per_thread
        actual_count = len(self.manager.phone_aliases)

        # Should have exactly expected_count entries
        self.assertEqual(
            actual_count,
            expected_count,
            f"Expected {expected_count} phone aliases, got {actual_count}. "
            f"Data corruption likely occurred due to race condition."
        )

    def test_concurrent_add_alias_write_write_race(self):
        """
        Test concurrent writes to phone_aliases dictionary via add_alias().

        This tests the write-write race condition where multiple threads
        simultaneously write to the dictionary.

        Expected behavior BEFORE fix: Lost updates, incorrect final count
        Expected behavior AFTER fix: All updates preserved
        """
        num_threads = 16
        iterations_per_thread = 50

        def worker(worker_id: int):
            """Worker that concurrently adds aliases."""
            for i in range(iterations_per_thread):
                phone_number = f"+1666{worker_id:02d}{i:04d}"
                alias = f"Person_{worker_id}_{i}"

                # Concurrent writes to dictionary
                self.manager.add_alias(phone_number, alias)

        # Run concurrent workers
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all aliases were added (no lost updates)
        expected_count = num_threads * iterations_per_thread
        actual_count = len(self.manager.phone_aliases)

        self.assertEqual(
            actual_count,
            expected_count,
            f"Expected {expected_count} phone aliases, got {actual_count}. "
            f"Lost updates due to write-write race condition."
        )

    def test_concurrent_mixed_operations(self):
        """
        Test mixed concurrent operations: get_alias, add_alias, exclusion checks.

        This simulates real-world usage where multiple operations happen
        simultaneously on the shared dictionary.

        Expected behavior BEFORE fix: Dictionary corruption, RuntimeError
        Expected behavior AFTER fix: All operations complete successfully
        """
        num_threads = 12
        iterations = 100
        errors = []

        def read_worker(worker_id: int):
            """Worker that reads aliases."""
            try:
                for i in range(iterations):
                    phone_number = f"+1777{worker_id:02d}{i:04d}"
                    alias = self.manager.get_alias(phone_number, soup=None)
                    self.assertIsNotNone(alias)
            except Exception as e:
                errors.append(f"Read worker {worker_id}: {e}")

        def write_worker(worker_id: int):
            """Worker that writes aliases."""
            try:
                for i in range(iterations):
                    phone_number = f"+1888{worker_id:02d}{i:04d}"
                    self.manager.add_alias(phone_number, f"Contact_{worker_id}_{i}")
            except Exception as e:
                errors.append(f"Write worker {worker_id}: {e}")

        def exclusion_worker(worker_id: int):
            """Worker that checks exclusions."""
            try:
                for i in range(iterations):
                    phone_number = f"+1999{worker_id:02d}{i:04d}"
                    # These methods iterate over phone_aliases/contact_filters
                    self.manager.is_filtered(phone_number)
                    self.manager.is_excluded(phone_number)
            except Exception as e:
                errors.append(f"Exclusion worker {worker_id}: {e}")

        # Create mixed workload
        threads = []
        for i in range(num_threads // 3):
            threads.append(threading.Thread(target=read_worker, args=(i,)))
            threads.append(threading.Thread(target=write_worker, args=(i,)))
            threads.append(threading.Thread(target=exclusion_worker, args=(i,)))

        # Run all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check for errors
        if errors:
            self.fail(f"Concurrent operations failed with errors:\n" + "\n".join(errors))

    def test_dictionary_resize_during_read(self):
        """
        Test dictionary resize during concurrent reads.

        Python dictionaries resize when they grow. This test ensures that
        reads happening during resize don't cause corruption.

        Expected behavior BEFORE fix: Potential corruption during resize
        Expected behavior AFTER fix: Safe resizing
        """
        # Pre-populate with some entries
        for i in range(50):
            self.manager.add_alias(f"+1000000{i:04d}", f"Existing_{i}")

        num_threads = 8
        iterations = 200  # Enough to trigger multiple resizes

        def reader():
            """Continuously read from dictionary."""
            for i in range(iterations):
                # Read existing entries
                phone_number = f"+1000000{i % 50:04d}"
                alias = self.manager.get_alias(phone_number, soup=None)
                self.assertIsNotNone(alias)

        def writer():
            """Add new entries to trigger resize."""
            for i in range(iterations):
                phone_number = f"+12222{threading.current_thread().ident % 10000:06d}{i:04d}"
                self.manager.add_alias(phone_number, f"New_{i}")

        # Create mix of readers and writers
        threads = []
        for i in range(num_threads // 2):
            threads.append(threading.Thread(target=reader))
            threads.append(threading.Thread(target=writer))

        # Run all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no corruption (all original entries still exist)
        for i in range(50):
            phone_number = f"+1000000{i:04d}"
            self.assertIn(
                phone_number,
                self.manager.phone_aliases,
                f"Original entry {phone_number} was lost during concurrent resize"
            )


class TestConversationManagerGetTotalStatsThreadSafety(unittest.TestCase):
    """Test thread-safety of ConversationManager.get_total_stats() (Issue #2)."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "conversations"
        self.output_dir.mkdir()

        # Create manager
        self.manager = ConversationManager(
            output_dir=self.output_dir,
            buffer_size=32768,
            output_format="html"
        )

        # Create a basic config
        self.config = ProcessingConfig(
            processing_dir=self.temp_dir,
            output_dir=self.output_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_total_stats_during_conversation_addition(self):
        """
        Test get_total_stats() while conversations are being added.

        This reproduces the race condition where get_total_stats() iterates
        over conversation_files while other threads are adding new conversations.

        Expected behavior BEFORE fix: RuntimeError "dictionary changed size during iteration"
        Expected behavior AFTER fix: Stats returned successfully
        """
        num_writer_threads = 8
        num_reader_threads = 4
        iterations = 100
        errors = []

        def writer(worker_id: int):
            """Add conversations concurrently."""
            try:
                for i in range(iterations):
                    conversation_id = f"Writer{worker_id}_Conv{i}"
                    timestamp = 1000000 + i

                    # This adds to conversation_files dictionary
                    self.manager.write_message_with_content(
                        conversation_id=conversation_id,
                        timestamp=timestamp,
                        sender="Alice",
                        message="Test message",
                        message_type="sms",
                        config=self.config
                    )

                    time.sleep(0.0001)  # Small delay to increase race condition probability
            except Exception as e:
                errors.append(f"Writer {worker_id}: {type(e).__name__}: {e}")

        def reader(worker_id: int):
            """Read total stats concurrently."""
            try:
                for i in range(iterations * 2):
                    # This iterates over conversation_files
                    stats = self.manager.get_total_stats()

                    # Verify stats are valid
                    self.assertIsInstance(stats, dict)
                    self.assertIn("num_sms", stats)

                    time.sleep(0.0001)  # Small delay
            except RuntimeError as e:
                if "dictionary changed size during iteration" in str(e):
                    errors.append(f"Reader {worker_id}: RuntimeError during iteration (EXPECTED BUG)")
                else:
                    errors.append(f"Reader {worker_id}: {type(e).__name__}: {e}")
            except Exception as e:
                errors.append(f"Reader {worker_id}: {type(e).__name__}: {e}")

        # Create threads
        threads = []
        for i in range(num_writer_threads):
            threads.append(threading.Thread(target=writer, args=(i,)))
        for i in range(num_reader_threads):
            threads.append(threading.Thread(target=reader, args=(i,)))

        # Run all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check for RuntimeError (indicates bug exists)
        runtime_errors = [e for e in errors if "RuntimeError" in e]

        # BEFORE fix: This test SHOULD fail with RuntimeError
        # AFTER fix: No errors should occur
        if runtime_errors:
            self.fail(
                f"get_total_stats() is NOT thread-safe. RuntimeError occurred:\n"
                + "\n".join(runtime_errors)
                + "\n\nThis is EXPECTED BEFORE the fix is applied."
            )

        # If no runtime errors, verify all other operations succeeded
        if errors:
            self.fail(f"Unexpected errors occurred:\n" + "\n".join(errors))

    def test_get_total_stats_consistency(self):
        """
        Test that get_total_stats() returns consistent results.

        Even without RuntimeError, the stats might be inconsistent if
        iteration happens during modification.

        Expected behavior BEFORE fix: Inconsistent stats (some conversations counted, others not)
        Expected behavior AFTER fix: Consistent stats
        """
        # Add initial conversations
        for i in range(100):
            self.manager.write_message_with_content(
                conversation_id=f"Initial_Conv{i}",
                timestamp=1000000 + i,
                sender="Alice",
                message=f"Message {i}",
                message_type="sms",
                config=self.config
            )

        num_threads = 8
        iterations = 50
        stats_snapshots = []

        def writer():
            """Add more conversations."""
            for i in range(iterations):
                self.manager.write_message_with_content(
                    conversation_id=f"Concurrent_Conv{threading.current_thread().ident}_{i}",
                    timestamp=2000000 + i,
                    sender="Charlie",
                    message=f"Concurrent message {i}",
                    message_type="sms",
                    config=self.config
                )
                time.sleep(0.001)

        def reader():
            """Read stats and verify consistency."""
            for i in range(iterations):
                stats = self.manager.get_total_stats()
                stats_snapshots.append(stats.get("num_sms", 0))
                time.sleep(0.001)

        # Create threads
        threads = []
        for i in range(num_threads // 2):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        # Run all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Get final stats
        final_stats = self.manager.get_total_stats()
        final_sms_count = final_stats.get("num_sms", 0)

        # Verify all snapshots are <= final count (monotonically increasing)
        for snapshot in stats_snapshots:
            self.assertLessEqual(
                snapshot,
                final_sms_count,
                f"Stats snapshot {snapshot} exceeds final count {final_sms_count}. "
                f"Inconsistent stats due to unprotected iteration."
            )


class TestContentTypeTrackingThreadSafety(unittest.TestCase):
    """Test thread-safety of content type tracking (Issue #3)."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "conversations"
        self.output_dir.mkdir()

        # Create manager
        self.manager = ConversationManager(
            output_dir=self.output_dir,
            buffer_size=32768,
            output_format="html"
        )

        # Create config
        self.config = ProcessingConfig(
            processing_dir=self.temp_dir,
            output_dir=self.output_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_content_type_initialization(self):
        """
        Test check-then-act race in _track_conversation_content_type().

        Multiple threads checking "if conversation_id not in dict" then
        initializing can cause lost updates.

        Expected behavior BEFORE fix: Lost updates, incorrect content type flags
        Expected behavior AFTER fix: All content types tracked correctly
        """
        num_threads = 16
        iterations = 50

        # Use same conversation ID to maximize race condition
        conversation_id = "SharedConversation"

        def worker(worker_id: int):
            """Write different message types to same conversation."""
            for i in range(iterations):
                # Alternate between SMS and MMS to trigger content type tracking
                if i % 2 == 0:
                    message_type = "sms"
                else:
                    message_type = "mms"

                self.manager.write_message_with_content(
                    conversation_id=conversation_id,
                    timestamp=1000000 + worker_id * 1000 + i,
                    sender="Alice",
                    message=f"Message {i}",
                    message_type=message_type,
                    config=self.config
                )

        # Run concurrent workers
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify content types were tracked correctly
        content_types = self.manager.conversation_content_types.get(conversation_id, {})

        # Should have both SMS and MMS marked as True
        self.assertTrue(
            content_types.get("has_sms", False),
            "SMS content type not tracked (lost update)"
        )
        self.assertTrue(
            content_types.get("has_mms", False),
            "MMS content type not tracked (lost update)"
        )


class TestFinalizeConversationFilesThreadSafety(unittest.TestCase):
    """Test thread-safety of finalize_conversation_files() (Issue #4)."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "conversations"
        self.output_dir.mkdir()

        # Create manager
        self.manager = ConversationManager(
            output_dir=self.output_dir,
            buffer_size=32768,
            output_format="html"
        )

        # Create config
        self.config = ProcessingConfig(
            processing_dir=self.temp_dir,
            output_dir=self.output_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dictionary_iteration_during_finalization(self):
        """
        Test that dictionary iterations in finalize_conversation_files() are safe.

        While finalization acquires a lock, the pattern of iterating multiple times
        and deleting entries between iterations could be fragile.

        Expected behavior BEFORE fix: Potential RuntimeError if iteration pattern changes
        Expected behavior AFTER fix: Safe iteration with snapshot approach
        """
        # Add many conversations
        for i in range(200):
            self.manager.write_message_with_content(
                conversation_id=f"Conv{i}",
                timestamp=1000000 + i,
                sender="Alice",
                message=f"Message {i}",
                message_type="sms",
                config=self.config
            )

        # Add empty conversations (will be removed during finalization)
        for i in range(50):
            conversation_id = f"Empty{i}"
            # Initialize but don't add messages
            if conversation_id not in self.manager.conversation_files:
                self.manager.conversation_files[conversation_id] = {
                    "messages": [],
                    "file_handle": None,
                    "html_builder": None
                }

        # Finalize should handle iteration safely
        try:
            self.manager.finalize_conversation_files(self.config)
        except RuntimeError as e:
            if "dictionary changed size during iteration" in str(e):
                self.fail(
                    f"finalize_conversation_files() has unsafe dictionary iteration: {e}\n"
                    "This indicates Issue #4 is present."
                )
            else:
                raise


if __name__ == "__main__":
    unittest.main()
