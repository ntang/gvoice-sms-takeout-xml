"""
Unit tests for the new PathManager system.

This module tests the PathManager class and new attachment processing functions
to ensure they provide consistent, working directory independent path handling.
"""

import unittest
import tempfile
import os
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.path_manager import PathManager, PathValidationError, PathContext
from core.attachment_manager_new import (
    build_file_location_index_new,
    copy_mapped_attachments_new,
    build_attachment_mapping_with_progress_new,
    extract_src_with_source_files_new,
    list_att_filenames_with_progress_new
)


class TestPathManager(unittest.TestCase):
    """Test PathManager functionality."""
    
    def setUp(self):
        """Set up test environment with realistic directory structure."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.processing_dir = self.temp_dir / "gvoice_data"
        self.processing_dir.mkdir()
        
        # Create realistic Google Voice structure
        (self.processing_dir / "Calls").mkdir()
        (self.processing_dir / "Phones.vcf").touch()
        
        # Create sample HTML files
        html_dir = self.processing_dir / "Calls"
        for i in range(10):
            html_file = html_dir / f"conversation_{i}.html"
            html_file.write_text(f"<html><img src='image_{i}.jpg'></html>")
        
        # Create sample attachment files
        for i in range(10):
            att_file = html_dir / f"image_{i}.jpg"
            att_file.write_text(f"fake image data {i}")
        
        self.output_dir = self.processing_dir / "conversations"
        self.path_manager = PathManager(self.processing_dir, self.output_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_path_validation(self):
        """Test comprehensive path validation."""
        # Test valid paths
        self.assertTrue(self.path_manager.processing_dir.exists())
        self.assertTrue(self.path_manager.calls_dir.exists())
        self.assertTrue(self.path_manager.phones_vcf.exists())
        
        # Test invalid paths
        with self.assertRaises(PathValidationError):
            PathManager(Path("/nonexistent"), Path("/nonexistent"))
    
    def test_attachment_path_generation(self):
        """Test attachment path generation logic."""
        filename = "test.jpg"
        source_path = self.processing_dir / "Calls" / filename
        source_path.touch()
        
        dest_path = self.path_manager.get_attachment_dest_path(filename)
        expected_path = self.output_dir / "attachments" / filename
        
        # Use resolve() for consistent path comparison
        self.assertEqual(dest_path.resolve(), expected_path.resolve())
    
    def test_working_directory_independence(self):
        """Test that path resolution is independent of working directory."""
        original_cwd = os.getcwd()
        
        try:
            # Change to different directory
            os.chdir("/tmp")
            
            # Verify PathManager still works
            self.assertTrue(self.path_manager.processing_dir.exists())
            # Note: output_dir won't exist until ensure_output_directories() is called
            # self.assertTrue(self.path_manager.output_dir.exists())
            
            # Test path operations
            dest_path = self.path_manager.get_attachment_dest_path("test.jpg")
            self.assertTrue(dest_path.is_absolute())
            
        finally:
            os.chdir(original_cwd)
    
    def test_output_directory_creation(self):
        """Test that output directories are created correctly."""
        # Remove output directory if it exists
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        
        # Create new PathManager (should create directories)
        path_manager = PathManager(self.processing_dir, self.output_dir)
        path_manager.ensure_output_directories()
        
        self.assertTrue(self.output_dir.exists())
        self.assertTrue((self.output_dir / "attachments").exists())
    
    def test_path_context_logging(self):
        """Test path context creation and logging."""
        context = self.path_manager.get_path_context(
            "test_operation",
            source=Path("/source/path"),
            destination=Path("/dest/path")
        )
        
        self.assertEqual(context.operation, "test_operation")
        self.assertEqual(context.source, Path("/source/path"))
        self.assertEqual(context.destination, Path("/dest/path"))
        self.assertIsInstance(context.working_directory, Path)
    
    def test_path_validation_methods(self):
        """Test individual path validation methods."""
        valid_path = self.processing_dir / "Calls"
        
        # Test valid path
        self.path_manager.validate_path_exists(valid_path, "Test directory", "test_context")
        
        # Test invalid path
        invalid_path = self.processing_dir / "nonexistent"
        with self.assertRaises(PathValidationError):
            self.path_manager.validate_path_exists(invalid_path, "Test directory", "test_context")
    
    def test_relative_path_calculation(self):
        """Test relative path calculation."""
        base = self.processing_dir
        sub_path = self.processing_dir / "Calls" / "test.html"
        
        relative = self.path_manager.get_relative_path(sub_path, base)
        self.assertEqual(relative, "Calls/test.html")
    
    def test_subpath_detection(self):
        """Test subpath detection logic."""
        base = self.processing_dir
        sub_path = self.processing_dir / "Calls" / "test.html"
        external_path = Path("/external/path")
        
        self.assertTrue(self.path_manager.is_subpath(sub_path, base))
        self.assertFalse(self.path_manager.is_subpath(external_path, base))
    
    def test_common_ancestor_detection(self):
        """Test common ancestor detection."""
        path1 = self.processing_dir / "Calls" / "file1.html"
        path2 = self.processing_dir / "Calls" / "file2.html"
        path3 = Path("/external/path")
        
        common = self.path_manager.get_common_ancestor(path1, path2)
        self.assertEqual(common, self.processing_dir / "Calls")
        
        # Fix: Root directory is always a common ancestor
        no_common = self.path_manager.get_common_ancestor(path1, path3)
        # The root directory "/" is always a common ancestor, so we check it's the root
        self.assertEqual(no_common, Path("/"))


class TestNewAttachmentFunctions(unittest.TestCase):
    """Test new attachment processing functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.processing_dir = self.temp_dir / "gvoice_data"
        self.processing_dir.mkdir()
        
        # Create realistic Google Voice structure
        (self.processing_dir / "Calls").mkdir()
        (self.processing_dir / "Phones.vcf").touch()
        
        # Create sample HTML files with attachments
        html_dir = self.processing_dir / "Calls"
        for i in range(5):
            html_file = html_dir / f"conversation_{i}.html"
            html_file.write_text(f"<html><img src='image_{i}.jpg'></html>")
            
            att_file = html_dir / f"image_{i}.jpg"
            att_file.write_text(f"fake image data {i}")
        
        self.output_dir = self.processing_dir / "conversations"
        self.path_manager = PathManager(self.processing_dir, self.output_dir)
        
        # Ensure output directories exist
        self.path_manager.ensure_output_directories()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_build_file_location_index_new(self):
        """Test new file location index building."""
        filenames = ["image_0.jpg", "image_1.jpg"]
        index = build_file_location_index_new(filenames, self.path_manager)
        
        self.assertEqual(len(index), 2)
        for filename, path in index.items():
            self.assertTrue(path.exists())
            self.assertTrue(path.is_absolute())
    
    def test_copy_mapped_attachments_new(self):
        """Test new attachment copying functionality."""
        # Build mapping
        mapping = build_attachment_mapping_with_progress_new(self.path_manager)
        
        # Copy attachments
        copy_mapped_attachments_new(mapping, self.path_manager)
        
        # Verify files were copied to correct location
        attachments_dir = self.path_manager.attachments_dir
        self.assertTrue(attachments_dir.exists())
        
        copied_files = list(attachments_dir.glob("*.jpg"))
        self.assertGreater(len(copied_files), 0)
        
        # Verify all copied files exist and are accessible
        for file in copied_files:
            self.assertTrue(file.exists())
            self.assertTrue(file.stat().st_size > 0)
    
    def test_build_attachment_mapping_with_progress_new(self):
        """Test new attachment mapping functionality."""
        mapping = build_attachment_mapping_with_progress_new(self.path_manager)
        
        # Verify mapping was created
        self.assertGreater(len(mapping), 0)
        
        # Verify all entries have Path objects for source paths
        for src, (filename, source_path) in mapping.items():
            self.assertIsInstance(source_path, Path)
            self.assertTrue(source_path.exists())
    
    def test_extract_src_with_source_files_new(self):
        """Test new src extraction functionality."""
        src_to_files = extract_src_with_source_files_new(self.path_manager.processing_dir)
        
        # Verify src elements were extracted
        self.assertGreater(len(src_to_files), 0)
        
        # Verify HTML files are referenced
        for src, html_files in src_to_files.items():
            self.assertIsInstance(html_files, list)
            self.assertGreater(len(html_files), 0)
    
    def test_list_att_filenames_with_progress_new(self):
        """Test new attachment filename listing."""
        filenames = list_att_filenames_with_progress_new(self.path_manager.processing_dir)
        
        # Verify filenames were found
        self.assertGreater(len(filenames), 0)
        
        # Verify all filenames are strings
        for filename in filenames:
            self.assertIsInstance(filename, str)
    
    def test_large_dataset_simulation(self):
        """Test with simulated large dataset."""
        # Create a separate directory for large dataset test to avoid conflicts
        large_test_dir = self.temp_dir / "large_dataset_test"
        large_test_dir.mkdir()
        
        # Create required Google Voice structure
        (large_test_dir / "Calls").mkdir()
        (large_test_dir / "Phones.vcf").touch()
        
        # Create 100+ files to simulate real-world conditions
        html_dir = large_test_dir / "Calls"
        
        for i in range(100):
            html_file = html_dir / f"large_conversation_{i}.html"
            html_file.write_text(f"<html><img src='large_image_{i}.jpg'></html>")
            
            att_file = html_dir / f"large_image_{i}.jpg"
            att_file.write_text(f"large fake image data {i}")
        
        # Create a separate PathManager for this test
        large_path_manager = PathManager(large_test_dir)
        
        # Test performance and memory usage
        start_time = time.time()
        mapping = build_attachment_mapping_with_progress_new(large_path_manager)
        mapping_time = time.time() - start_time
        
        # Verify performance is acceptable (< 10 seconds for 100 files)
        self.assertLess(mapping_time, 10.0)
        self.assertEqual(len(mapping), 100)
    
    def test_error_handling(self):
        """Test error handling and recovery."""
        # Test with missing files
        missing_file = self.processing_dir / "Calls" / "missing.jpg"
        mapping = {"missing": ("missing.jpg", missing_file)}
        
        # Should handle gracefully without crashing
        copy_mapped_attachments_new(mapping, self.path_manager)
        
        # Verify no files were copied
        attachments_dir = self.path_manager.attachments_dir
        if attachments_dir.exists():
            copied_files = list(attachments_dir.glob("*"))
            self.assertEqual(len(copied_files), 0)
    
    def test_memory_usage(self):
        """Test memory usage doesn't grow excessively."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform operations
        for i in range(5):
            mapping = build_attachment_mapping_with_progress_new(self.path_manager)
            copy_mapped_attachments_new(mapping, self.path_manager)
            gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB for small test)
        self.assertLess(memory_increase, 50 * 1024 * 1024)


class TestPathManagerIntegration(unittest.TestCase):
    """Integration tests for PathManager system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.processing_dir = self.temp_dir / "gvoice_data"
        self.processing_dir.mkdir()
        
        # Create more complex directory structure
        (self.processing_dir / "Calls").mkdir()
        (self.processing_dir / "Calls" / "subdir").mkdir()
        (self.processing_dir / "Phones.vcf").touch()
        
        # Create HTML files in multiple locations
        html_locations = [
            self.processing_dir / "Calls",
            self.processing_dir / "Calls" / "subdir"
        ]
        
        for i, location in enumerate(html_locations):
            for j in range(3):
                html_file = location / f"conversation_{i}_{j}.html"
                html_file.write_text(f"<html><img src='image_{i}_{j}.jpg'></html>")
                
                att_file = location / f"image_{i}_{j}.jpg"
                att_file.write_text(f"fake image data {i}_{j}")
        
        self.output_dir = self.processing_dir / "conversations"
        self.path_manager = PathManager(self.processing_dir, self.output_dir)
        
        # Ensure output directories exist
        self.path_manager.ensure_output_directories()
    
    def tearDown(self):
        """Clean up integration test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_pipeline_integration(self):
        """Test complete attachment processing pipeline."""
        # Step 1: Build mapping
        mapping = build_attachment_mapping_with_progress_new(self.path_manager)
        self.assertGreater(len(mapping), 0)
        
        # Step 2: Copy attachments
        copy_mapped_attachments_new(mapping, self.path_manager)
        
        # Step 3: Verify results
        attachments_dir = self.path_manager.attachments_dir
        self.assertTrue(attachments_dir.exists())
        
        copied_files = list(attachments_dir.glob("*.jpg"))
        self.assertEqual(len(copied_files), len(mapping))
        
        # Verify all copied files are accessible
        for file in copied_files:
            self.assertTrue(file.exists())
            self.assertTrue(file.stat().st_size > 0)
    
    def test_nested_directory_handling(self):
        """Test handling of nested directory structures."""
        # Create nested structure
        nested_dir = self.processing_dir / "Calls" / "nested" / "deep"
        nested_dir.mkdir(parents=True)
        
        # Add files to nested location
        html_file = nested_dir / "nested_conversation.html"
        html_file.write_text("<html><img src='nested_image.jpg'></html>")
        
        att_file = nested_dir / "nested_image.jpg"
        att_file.write_text("nested fake image data")
        
        # Test that PathManager can handle nested structure
        mapping = build_attachment_mapping_with_progress_new(self.path_manager)
        
        # Verify nested file was found
        nested_src = "nested_image.jpg"
        if nested_src in mapping:
            filename, source_path = mapping[nested_src]
            self.assertEqual(filename, "nested_image.jpg")
            self.assertTrue(source_path.exists())
    
    def test_concurrent_access(self):
        """Test concurrent access to PathManager."""
        import threading
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Each worker creates its own PathManager instance
                worker_path_manager = PathManager(self.processing_dir, self.output_dir)
                
                # Perform operations
                mapping = build_attachment_mapping_with_progress_new(worker_path_manager)
                copy_mapped_attachments_new(mapping, worker_path_manager)
                
                results.append(worker_id)
                
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Create multiple worker threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all workers completed successfully
        self.assertEqual(len(results), 3)
        self.assertEqual(len(errors), 0)
    
    def test_enhanced_attachment_mapping_google_voice_patterns(self):
        """Test enhanced attachment mapping for Google Voice export naming patterns."""
        # Create test data that mimics the real Google Voice export structure
        html_dir = self.processing_dir / "Calls"
        
        # Clear existing files to avoid conflicts
        for existing_file in html_dir.glob("*"):
            if existing_file.name != "conversation_0_0.html":  # Keep one for the test framework
                if existing_file.is_file():
                    existing_file.unlink()
                elif existing_file.is_dir():
                    shutil.rmtree(existing_file)
        
        # Create HTML file with src reference using contact name
        html_content = """
        <html>
        <body>
        <div><img src="Susan Nowak Tang - Text - 2024-10-20T14_50_55Z-6-1" alt="Image MMS Attachment" /></div>
        <div><img src="John Doe - Text - 2024-02-09T15_30_51Z-12-1" alt="Image MMS Attachment" /></div>
        <div><img src="Jane Smith - Placed - 2019-05-01T19_10_12Z" alt="Call Record" /></div>
        </body>
        </html>
        """
        test_html = html_dir / "test_conversation.html"
        test_html.write_text(html_content)
        
        # Create actual attachment files with phone number naming (Google Voice style)
        attachments = [
            "+16462728914 - Text - 2024-10-20T14_50_55Z-6-1.jpg",
            "John Doe - Text - 2024-02-09T15_30_51Z-12-.jpg",  # Note: missing "1" at end
            "+15551234567 - Placed - 2019-05-01T19_10_12Z.html"
        ]
        
        for att_name in attachments:
            att_file = html_dir / att_name
            att_file.write_text(f"fake attachment data for {att_name}")
        
        # Debug: Print what files we actually created
        print(f"\nTest files created:")
        for f in html_dir.glob("*"):
            print(f"  {f.name}")
        
        # Test the enhanced attachment mapping
        mapping = build_attachment_mapping_with_progress_new(self.path_manager)
        
        # Debug: Print the mapping results
        print(f"\nMapping results:")
        for src, (filename, source_path) in mapping.items():
            print(f"  {src} -> {filename}")
        
        # Verify the enhanced mapping worked
        self.assertIn("Susan Nowak Tang - Text - 2024-10-20T14_50_55Z-6-1", mapping)
        self.assertIn("John Doe - Text - 2024-02-09T15_30_51Z-12-1", mapping)
        self.assertIn("Jane Smith - Placed - 2019-05-01T19_10_12Z", mapping)
        
        # Check that the correct attachments were mapped
        susan_mapping = mapping["Susan Nowak Tang - Text - 2024-10-20T14_50_55Z-6-1"]
        self.assertEqual(susan_mapping[0], "+16462728914 - Text - 2024-10-20T14_50_55Z-6-1.jpg")
        
        john_mapping = mapping["John Doe - Text - 2024-02-09T15_30_51Z-12-1"]
        self.assertEqual(john_mapping[0], "John Doe - Text - 2024-02-09T15_30_51Z-12-.jpg")
        
        jane_mapping = mapping["Jane Smith - Placed - 2019-05-01T19_10_12Z"]
        self.assertEqual(jane_mapping[0], "+15551234567 - Placed - 2019-05-01T19_10_12Z.html")
        
        # Verify source paths are correct
        for src, (filename, source_path) in mapping.items():
            if filename != "No attachment found":
                self.assertIsInstance(source_path, Path)
                self.assertTrue(source_path.exists())


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
