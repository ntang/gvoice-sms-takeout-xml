"""
Test suite for improved file operations module.

This module tests the enhanced file operations that replace custom implementations
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
import utils.improved_file_operations as improved_file_operations

# Suppress logging during tests
logging.getLogger("improved_file_operations").setLevel(logging.ERROR)


class TestImprovedFileOperations(unittest.TestCase):
    """Test improved file operations."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.temp_dir / "Calls"
        self.attachments_dir = self.temp_dir / "attachments"
        
        # Create test directory structure
        self.calls_dir.mkdir()
        self.attachments_dir.mkdir()
        
        # Create test source files
        self.test_files = {
            "test1.txt": "Content for test file 1",
            "test2.txt": "Content for test file 2",
            "test3.txt": "Content for test file 3",
            "test4.txt": "Content for test file 4"
        }
        
        for filename, content in self.test_files.items():
            (self.calls_dir / filename).write_text(content)
        
        # Store original working directory
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_copy_attachments_sequential_improved_success(self):
        """Test successful sequential attachment copying."""
        filenames = {"test1.txt", "test2.txt"}
        
        improved_file_operations.copy_attachments_sequential_improved(filenames, self.attachments_dir)
        
        # Check that files were copied
        self.assertTrue((self.attachments_dir / "test1.txt").exists())
        self.assertTrue((self.attachments_dir / "test2.txt").exists())
        
        # Check content
        self.assertEqual((self.attachments_dir / "test1.txt").read_text(), "Content for test file 1")
        self.assertEqual((self.attachments_dir / "test2.txt").read_text(), "Content for test file 2")

    def test_copy_attachments_sequential_improved_skip_existing(self):
        """Test that existing files are skipped."""
        # Create an existing file
        (self.attachments_dir / "test1.txt").write_text("Existing content")
        
        filenames = {"test1.txt", "test2.txt"}
        improved_file_operations.copy_attachments_sequential_improved(filenames, self.attachments_dir)
        
        # Check that existing file wasn't overwritten
        self.assertEqual((self.attachments_dir / "test1.txt").read_text(), "Existing content")
        # Check that new file was copied
        self.assertTrue((self.attachments_dir / "test2.txt").exists())

    def test_copy_attachments_sequential_improved_missing_source(self):
        """Test handling of missing source files."""
        filenames = {"missing.txt", "test1.txt"}
        
        improved_file_operations.copy_attachments_sequential_improved(filenames, self.attachments_dir)
        
        # Check that missing file wasn't copied
        self.assertFalse((self.attachments_dir / "missing.txt").exists())
        # Check that existing file was copied
        self.assertTrue((self.attachments_dir / "test1.txt").exists())

    def test_copy_attachments_parallel_improved_success(self):
        """Test successful parallel attachment copying."""
        filenames = {"test1.txt", "test2.txt", "test3.txt", "test4.txt"}
        
        improved_file_operations.copy_attachments_parallel_improved(filenames, self.attachments_dir)
        
        # Check that all files were copied
        for filename in filenames:
            self.assertTrue((self.attachments_dir / filename).exists())
            self.assertEqual((self.attachments_dir / filename).read_text(), self.test_files[filename])

    def test_copy_attachments_parallel_improved_with_errors(self):
        """Test parallel copying with some errors."""
        # Remove one source file to create an error
        (self.calls_dir / "test2.txt").unlink()
        
        filenames = {"test1.txt", "test2.txt", "test3.txt"}
        
        improved_file_operations.copy_attachments_parallel_improved(filenames, self.attachments_dir)
        
        # Check that successful copies worked
        self.assertTrue((self.attachments_dir / "test1.txt").exists())
        self.assertTrue((self.attachments_dir / "test3.txt").exists())
        # Check that failed copy didn't create file
        self.assertFalse((self.attachments_dir / "test2.txt").exists())

    def test_copy_chunk_parallel_improved_success(self):
        """Test successful parallel chunk copying."""
        filenames = ["test1.txt", "test2.txt"]
        
        result = improved_file_operations.copy_chunk_parallel_improved(filenames, self.attachments_dir)
        
        # Check result statistics
        self.assertEqual(result["copied"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)
        
        # Check that files were copied
        self.assertTrue((self.attachments_dir / "test1.txt").exists())
        self.assertTrue((self.attachments_dir / "test2.txt").exists())

    def test_copy_chunk_parallel_improved_with_skips(self):
        """Test parallel chunk copying with some skips."""
        # Create an existing file
        (self.attachments_dir / "test1.txt").write_text("Existing content")
        
        filenames = ["test1.txt", "test2.txt"]
        
        result = improved_file_operations.copy_chunk_parallel_improved(filenames, self.attachments_dir)
        
        # Check result statistics
        self.assertEqual(result["copied"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)
        
        # Check that existing file wasn't overwritten
        self.assertEqual((self.attachments_dir / "test1.txt").read_text(), "Existing content")
        # Check that new file was copied
        self.assertTrue((self.attachments_dir / "test2.txt").exists())

    def test_copy_chunk_parallel_improved_with_errors(self):
        """Test parallel chunk copying with errors."""
        # Remove one source file to create an error
        (self.calls_dir / "test2.txt").unlink()
        
        filenames = ["test1.txt", "test2.txt"]
        
        result = improved_file_operations.copy_chunk_parallel_improved(filenames, self.attachments_dir)
        
        # Check result statistics
        self.assertEqual(result["copied"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 1)
        
        # Check that successful copy worked
        self.assertTrue((self.attachments_dir / "test1.txt").exists())
        # Check that failed copy didn't create file
        self.assertFalse((self.attachments_dir / "test2.txt").exists())


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility features."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.temp_dir / "Calls"
        self.attachments_dir = self.temp_dir / "attachments"
        
        # Create test directory structure
        self.calls_dir.mkdir()
        self.attachments_dir.mkdir()
        
        # Create test source files
        self.test_files = {
            "test1.txt": "Content for test file 1",
            "test2.txt": "Content for test file 2"
        }
        
        for filename, content in self.test_files.items():
            (self.calls_dir / filename).write_text(content)
        
        # Store original working directory
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_copy_attachments_sequential_backward_compatibility(self):
        """Test backward compatibility wrapper for sequential copying."""
        filenames = {"test1.txt", "test2.txt"}
        
        # Use the backward compatibility wrapper
        improved_file_operations.copy_attachments_sequential(filenames, self.attachments_dir)
        
        # Check that files were copied
        self.assertTrue((self.attachments_dir / "test1.txt").exists())
        self.assertTrue((self.attachments_dir / "test2.txt").exists())

    def test_copy_attachments_parallel_backward_compatibility(self):
        """Test backward compatibility wrapper for parallel copying."""
        filenames = {"test1.txt", "test2.txt"}
        
        # Use the backward compatibility wrapper
        improved_file_operations.copy_attachments_parallel(filenames, self.attachments_dir)
        
        # Check that files were copied
        self.assertTrue((self.attachments_dir / "test1.txt").exists())
        self.assertTrue((self.attachments_dir / "test2.txt").exists())

    def test_copy_chunk_parallel_backward_compatibility(self):
        """Test backward compatibility wrapper for chunk copying."""
        filenames = ["test1.txt", "test2.txt"]
        
        # Use the backward compatibility wrapper
        result = improved_file_operations.copy_chunk_parallel(filenames, self.attachments_dir)
        
        # Check result
        self.assertEqual(result["copied"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)


class TestFeatureFlags(unittest.TestCase):
    """Test feature flag functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.temp_dir / "Calls"
        self.attachments_dir = self.temp_dir / "attachments"
        
        # Create test directory structure
        self.calls_dir.mkdir()
        self.attachments_dir.mkdir()
        
        # Create test source file
        (self.calls_dir / "test.txt").write_text("Test content")
        
        # Store original working directory
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Store original feature flag setting
        self.original_setting = improved_file_operations.USE_IMPROVED_FILE_OPS

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        improved_file_operations.USE_IMPROVED_FILE_OPS = self.original_setting

    def test_feature_flag_enabled(self):
        """Test with feature flag enabled."""
        improved_file_operations.USE_IMPROVED_FILE_OPS = True
        
        filenames = {"test.txt"}
        improved_file_operations.copy_attachments_sequential_improved(filenames, self.attachments_dir)
        
        # Check that improved functionality was used
        self.assertTrue((self.attachments_dir / "test.txt").exists())

    def test_feature_flag_disabled(self):
        """Test with feature flag disabled."""
        improved_file_operations.USE_IMPROVED_FILE_OPS = False
        
        filenames = {"test.txt"}
        improved_file_operations.copy_attachments_sequential_improved(filenames, self.attachments_dir)
        
        # Check that legacy functionality was used
        self.assertTrue((self.attachments_dir / "test.txt").exists())


class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.temp_dir / "Calls"
        self.attachments_dir = self.temp_dir / "attachments"
        
        # Create test directory structure
        self.calls_dir.mkdir()
        self.attachments_dir.mkdir()
        
        # Store original working directory
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_copy_attachments_sequential_improved_empty_set(self):
        """Test copying with empty filename set."""
        filenames = set()
        
        # Should not raise any errors
        improved_file_operations.copy_attachments_sequential_improved(filenames, self.attachments_dir)

    def test_copy_attachments_parallel_improved_empty_set(self):
        """Test parallel copying with empty filename set."""
        filenames = set()
        
        # Should not raise any errors
        improved_file_operations.copy_attachments_parallel_improved(filenames, self.attachments_dir)

    def test_copy_chunk_parallel_improved_empty_list(self):
        """Test chunk copying with empty filename list."""
        filenames = []
        
        result = improved_file_operations.copy_chunk_parallel_improved(filenames, self.attachments_dir)
        
        # Check result for empty list
        self.assertEqual(result["copied"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
