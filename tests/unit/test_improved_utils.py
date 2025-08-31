"""
Test suite for improved utilities module.

This module tests the enhanced utilities that replace custom implementations
while maintaining the same interface.
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, Mock
import logging

# Import the module to test
import utils.improved_utils as improved_utils

# Suppress logging during tests
logging.getLogger("improved_utils").setLevel(logging.ERROR)


class TestImprovedFileOperations(unittest.TestCase):
    """Test improved file operations."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_file = self.temp_dir / "source.txt"
        self.dest_file = self.temp_dir / "dest.txt"
        
        # Create test source file
        self.source_file.write_text("Test content for file operations")
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_copy_file_safely_success(self):
        """Test successful file copy."""
        result = improved_utils.copy_file_safely(self.source_file, self.dest_file)
        
        self.assertTrue(result)
        self.assertTrue(self.dest_file.exists())
        self.assertEqual(self.source_file.read_text(), self.dest_file.read_text())
        self.assertEqual(self.source_file.stat().st_size, self.dest_file.stat().st_size)

    def test_copy_file_safely_with_metadata(self):
        """Test file copy with metadata preservation."""
        result = improved_utils.copy_file_safely(self.source_file, self.dest_file, preserve_metadata=True)
        
        self.assertTrue(result)
        # Check that timestamps are preserved (within reasonable tolerance)
        source_mtime = self.source_file.stat().st_mtime
        dest_mtime = self.dest_file.stat().st_mtime
        self.assertAlmostEqual(source_mtime, dest_mtime, delta=1)

    def test_copy_file_safely_destination_directory_creation(self):
        """Test that destination directory is created automatically."""
        nested_dest = self.temp_dir / "nested" / "deep" / "dest.txt"
        result = improved_utils.copy_file_safely(self.source_file, nested_dest)
        
        self.assertTrue(result)
        self.assertTrue(nested_dest.exists())
        self.assertTrue(nested_dest.parent.exists())

    def test_copy_file_safely_source_not_exists(self):
        """Test copy with non-existent source file."""
        non_existent_source = self.temp_dir / "non_existent.txt"
        result = improved_utils.copy_file_safely(non_existent_source, self.dest_file)
        
        self.assertFalse(result)
        self.assertFalse(self.dest_file.exists())

    def test_ensure_directory_with_permissions_success(self):
        """Test successful directory creation with permissions."""
        test_dir = self.temp_dir / "test_permissions"
        result = improved_utils.ensure_directory_with_permissions(test_dir, 0o755)
        
        self.assertTrue(result)
        self.assertTrue(test_dir.exists())
        self.assertTrue(test_dir.is_dir())

    def test_ensure_directory_with_permissions_parent_creation(self):
        """Test that parent directories are created automatically."""
        nested_dir = self.temp_dir / "parent" / "child" / "grandchild"
        result = improved_utils.ensure_directory_with_permissions(nested_dir)
        
        self.assertTrue(result)
        self.assertTrue(nested_dir.exists())
        self.assertTrue(nested_dir.parent.exists())
        self.assertTrue(nested_dir.parent.parent.exists())

    def test_safe_delete_file_to_trash(self):
        """Test safe file deletion to trash."""
        test_file = self.temp_dir / "to_delete.txt"
        test_file.write_text("Delete me")
        
        with patch('utils.improved_utils.send2trash') as mock_send2trash:
            result = improved_utils.safe_delete_file(test_file, use_trash=True)
            
            self.assertTrue(result)
            mock_send2trash.assert_called_once_with(str(test_file))

    def test_safe_delete_file_permanent(self):
        """Test permanent file deletion."""
        test_file = self.temp_dir / "to_delete_permanent.txt"
        test_file.write_text("Delete me permanently")
        
        result = improved_utils.safe_delete_file(test_file, use_trash=False)
        
        self.assertTrue(result)
        self.assertFalse(test_file.exists())


class TestImprovedProgressTracking(unittest.TestCase):
    """Test improved progress tracking."""

    def test_progress_tracker_context_manager(self):
        """Test ProgressTracker as context manager."""
        with improved_utils.ProgressTracker("Test Progress", 10) as tracker:
            self.assertIsNotNone(tracker)
            # Test that it can be used as a context manager
            pass

    def test_progress_tracker_update(self):
        """Test progress tracker update functionality."""
        with improved_utils.ProgressTracker("Test Progress", 5) as tracker:
            tracker.update(1)
            tracker.update(1, "Updated description")
            # Should not raise any errors

    def test_track_progress_simple_generator(self):
        """Test simple progress tracking generator."""
        test_items = ["item1", "item2", "item3"]
        
        # Test that it yields all items
        result = list(improved_utils.track_progress_simple(test_items, "Processing items"))
        self.assertEqual(result, test_items)

    def test_track_progress_simple_empty_list(self):
        """Test progress tracking with empty list."""
        empty_items = []
        result = list(improved_utils.track_progress_simple(empty_items, "Processing empty"))
        self.assertEqual(result, [])


class TestImprovedTimestampParsing(unittest.TestCase):
    """Test improved timestamp parsing."""

    def test_parse_timestamp_flexible_iso_format(self):
        """Test parsing ISO format timestamps."""
        timestamp_str = "2024-01-15T10:30:00Z"
        result = improved_utils.parse_timestamp_flexible(timestamp_str)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_parse_timestamp_flexible_us_format(self):
        """Test parsing US date format timestamps."""
        timestamp_str = "01/15/2024 10:30:00"
        result = improved_utils.parse_timestamp_flexible(timestamp_str)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_parse_timestamp_flexible_invalid_format(self):
        """Test parsing invalid timestamp format."""
        timestamp_str = "invalid timestamp"
        result = improved_utils.parse_timestamp_flexible(timestamp_str)
        
        self.assertIsNone(result)

    def test_parse_timestamp_flexible_empty_string(self):
        """Test parsing empty timestamp string."""
        timestamp_str = ""
        result = improved_utils.parse_timestamp_flexible(timestamp_str)
        
        self.assertIsNone(result)


class TestImprovedConfiguration(unittest.TestCase):
    """Test improved configuration management."""

    def test_app_config_defaults(self):
        """Test AppConfig default values."""
        config = improved_utils.AppConfig()
        
        self.assertEqual(config.supported_image_types, [".jpg", ".jpeg", ".png", ".gif", ".bmp"])
        self.assertEqual(config.supported_vcard_types, [".vcf"])
        self.assertEqual(config.mms_type_sent, 128)
        self.assertEqual(config.mms_type_received, 132)
        self.assertEqual(config.message_box_sent, 2)
        self.assertEqual(config.message_box_received, 1)

    def test_app_config_validation_file_extensions(self):
        """Test file extension validation."""
        with self.assertRaises(ValueError):
            improved_utils.AppConfig(supported_image_types=["jpg", ".png"])  # Missing dot

    def test_app_config_validation_max_workers(self):
        """Test max workers validation."""
        with self.assertRaises(ValueError):
            improved_utils.AppConfig(max_workers=0)  # Must be positive

    def test_load_config_success(self):
        """Test successful configuration loading."""
        config = improved_utils.load_config()
        
        self.assertIsInstance(config, improved_utils.AppConfig)
        self.assertIsInstance(config.supported_image_types, list)
        self.assertIsInstance(config.supported_vcard_types, list)

    def test_get_legacy_config_format(self):
        """Test legacy configuration format."""
        legacy_config = improved_utils.get_legacy_config()
        
        self.assertIn("SUPPORTED_IMAGE_TYPES", legacy_config)
        self.assertIn("SUPPORTED_VCARD_TYPES", legacy_config)
        self.assertIn("MMS_TYPE_SENT", legacy_config)
        self.assertIn("MMS_TYPE_RECEIVED", legacy_config)
        self.assertIn("MESSAGE_BOX_SENT", legacy_config)
        self.assertIn("MESSAGE_BOX_RECEIVED", legacy_config)


class TestImprovedLoggingAndOutput(unittest.TestCase):
    """Test improved logging and output formatting."""

    def test_create_rich_table_success(self):
        """Test successful table creation."""
        title = "Test Table"
        columns = ["Column1", "Column2", "Column3"]
        
        table = improved_utils.create_rich_table(title, columns)
        
        if table is not None:  # Only check if rich is available
            self.assertEqual(table.title, title)
            # Rich tables don't expose column count directly, but we can check it was created
            self.assertIsNotNone(table)

    def test_display_processing_summary_success(self):
        """Test successful processing summary display."""
        stats = {
            "num_sms": 100,
            "num_images": 25,
            "processing_time": 45.5,
            "status": "completed"
        }
        
        # Should not raise any errors
        improved_utils.display_processing_summary(stats)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility features."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_file = self.temp_dir / "source.txt"
        self.dest_file = self.temp_dir / "dest.txt"
        self.source_file.write_text("Test content")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_legacy_copy_file_fallback(self):
        """Test legacy copy file fallback."""
        # Temporarily disable improved utils
        original_setting = improved_utils.USE_IMPROVED_UTILS
        improved_utils.USE_IMPROVED_UTILS = False
        
        try:
            result = improved_utils.copy_file_safely(self.source_file, self.dest_file)
            self.assertTrue(result)
            self.assertTrue(self.dest_file.exists())
        finally:
            improved_utils.USE_IMPROVED_UTILS = original_setting

    def test_legacy_directory_creation_fallback(self):
        """Test legacy directory creation fallback."""
        # Temporarily disable improved utils
        original_setting = improved_utils.USE_IMPROVED_UTILS
        improved_utils.USE_IMPROVED_UTILS = False
        
        try:
            test_dir = self.temp_dir / "legacy_test"
            result = improved_utils.ensure_directory_with_permissions(test_dir)
            self.assertTrue(result)
            self.assertTrue(test_dir.exists())
        finally:
            improved_utils.USE_IMPROVED_UTILS = original_setting

    def test_legacy_timestamp_parsing_fallback(self):
        """Test legacy timestamp parsing fallback."""
        # Temporarily disable improved utils
        original_setting = improved_utils.USE_IMPROVED_UTILS
        improved_utils.USE_IMPROVED_UTILS = False
        
        try:
            timestamp_str = "2024-01-15T10:30:00Z"
            result = improved_utils.parse_timestamp_flexible(timestamp_str)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, int)
        finally:
            improved_utils.USE_IMPROVED_UTILS = original_setting


class TestFeatureFlags(unittest.TestCase):
    """Test feature flag functionality."""

    def setUp(self):
        """Set up test environment."""
        self.original_setting = improved_utils.USE_IMPROVED_UTILS

    def tearDown(self):
        """Clean up test environment."""
        improved_utils.USE_IMPROVED_UTILS = self.original_setting

    def test_feature_flag_enabled(self):
        """Test with feature flag enabled."""
        improved_utils.USE_IMPROVED_UTILS = True
        
        # Test that improved functionality is used
        config = improved_utils.load_config()
        self.assertIsInstance(config, improved_utils.AppConfig)

    def test_feature_flag_disabled(self):
        """Test with feature flag disabled."""
        improved_utils.USE_IMPROVED_UTILS = False
        
        # Test that legacy functionality is used
        config = improved_utils.load_config()
        self.assertIsInstance(config, improved_utils.AppConfig)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
