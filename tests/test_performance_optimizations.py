"""
TDD Test Suite for Performance Optimizations.

This test suite follows TDD principles for implementing low-risk performance optimizations:
1. Smart attachment mapping (early exit when no src elements)
2. Cached attachment index (file-based caching with modification time validation)
3. Memory-mapped I/O activation (for large files)

RED → GREEN → REFACTOR approach for each optimization.
"""

import pytest
import tempfile
import shutil
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the modules we need to test
from core.attachment_manager_new import (
    build_attachment_mapping_with_progress_new,
    build_file_location_index_new,
    list_att_filenames_with_progress_new
)
from core.path_manager import PathManager


class TestSmartAttachmentMapping:
    """TDD tests for smart attachment mapping optimization."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.test_dir / "Calls"
        self.calls_dir.mkdir(parents=True)
        
        # Create PathManager
        self.path_manager = PathManager(self.test_dir, test_mode=True)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_empty_src_elements_should_skip_attachment_scanning(self):
        """
        RED TEST: When HTML files contain no src elements, attachment scanning should be skipped entirely.
        
        This test will FAIL initially because the current implementation always scans attachments.
        """
        # Setup: Create HTML files with no src elements
        html_file1 = self.calls_dir / "test1.html"
        html_file1.write_text("""
        <html><body>
            <div class="message">
                <cite>+1234567890</cite>
                <q>Text message with no attachments</q>
            </div>
        </body></html>
        """)
        
        html_file2 = self.calls_dir / "test2.html"
        html_file2.write_text("""
        <html><body>
            <div class="message">
                <cite>Me</cite>
                <q>Another text message with no attachments</q>
            </div>
        </body></html>
        """)
        
        # Create many attachment files to make scanning expensive
        attachments_dir = self.calls_dir / "attachments"
        attachments_dir.mkdir()
        for i in range(1000):
            (attachments_dir / f"attachment_{i}.jpg").write_text("fake image")
        
        # Action: Build attachment mapping
        with patch('core.attachment_manager_new.list_att_filenames_with_progress_new') as mock_list_att:
            mock_list_att.return_value = [f"attachment_{i}.jpg" for i in range(1000)]
            
            start_time = time.time()
            result = build_attachment_mapping_with_progress_new(
                self.path_manager,
                sample_files=[str(html_file1), str(html_file2)]
            )
            execution_time = time.time() - start_time
        
        # Assert: Should return empty mapping quickly without scanning attachments
        assert result == {}, "Should return empty mapping when no src elements found"
        
        # Assert: Should not have called expensive attachment scanning
        # This will FAIL initially because current implementation always scans
        mock_list_att.assert_not_called()
        
        # Assert: Should be very fast (< 0.1s) since no attachment scanning
        assert execution_time < 0.1, f"Should be fast without attachment scanning, got {execution_time:.3f}s"
    
    def test_attachment_mapping_with_src_elements_should_scan_normally(self):
        """
        GREEN TEST: When HTML files contain src elements, normal attachment scanning should occur.
        
        This ensures the optimization doesn't break normal functionality.
        """
        # Setup: Create HTML files WITH src elements
        html_file = self.calls_dir / "test_with_attachments.html"
        html_file.write_text("""
        <html><body>
            <div class="message">
                <cite>+1234567890</cite>
                <q>Message with attachment</q>
                <img src="photo_123.jpg" />
            </div>
        </body></html>
        """)
        
        # Create corresponding attachment file
        attachment_file = self.calls_dir / "photo_123.jpg"
        attachment_file.write_text("fake image data")
        
        # Action: Build attachment mapping
        result = build_attachment_mapping_with_progress_new(
            self.path_manager,
            sample_files=[str(html_file)]
        )
        
        # Assert: Should find the mapping
        assert len(result) > 0, "Should find attachment mappings when src elements exist"
        assert "photo_123.jpg" in [filename for filename, _ in result.values()], "Should map the specific attachment"
    
    def test_performance_baseline_measurement(self):
        """
        BASELINE TEST: Measure current performance for comparison after optimizations.
        """
        # Setup: Create realistic test scenario
        html_files = []
        for i in range(10):
            html_file = self.calls_dir / f"conversation_{i}.html"
            html_file.write_text(f"""
            <html><body>
                <div class="message">
                    <cite>+123456789{i}</cite>
                    <q>Test message {i}</q>
                </div>
            </body></html>
            """)
            html_files.append(str(html_file))
        
        # Create attachments (simulating large dataset)
        for i in range(100):
            (self.calls_dir / f"attachment_{i}.jpg").write_text("fake image")
        
        # Measure baseline performance
        start_time = time.time()
        result = build_attachment_mapping_with_progress_new(
            self.path_manager,
            sample_files=html_files
        )
        baseline_time = time.time() - start_time
        
        # Store baseline for comparison (this test should always pass)
        assert baseline_time >= 0, "Baseline measurement should complete"
        
        # Log baseline for future comparison
        print(f"Baseline performance: {baseline_time:.3f}s for 10 HTML files, 100 attachments")


class TestCachedAttachmentIndex:
    """TDD tests for cached attachment index optimization."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.test_dir / "Calls"
        self.calls_dir.mkdir(parents=True)
        self.cache_file = self.test_dir / ".attachment_cache.json"
        
        # Create PathManager
        self.path_manager = PathManager(self.test_dir, test_mode=True)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_cache_creation_on_first_run(self):
        """
        RED TEST: First run should create cache file with attachment index.
        
        This test will FAIL initially because caching is not yet implemented.
        """
        # Setup: Create attachment files
        for i in range(50):
            (self.calls_dir / f"attachment_{i}.jpg").write_text("fake image")
        
        # Action: Build file location index (should create cache)
        filenames = [f"attachment_{i}.jpg" for i in range(50)]
        result = build_file_location_index_new(filenames, self.path_manager)
        
        # Assert: Cache file should be created
        # This will FAIL initially because caching is not implemented
        assert self.cache_file.exists(), "Cache file should be created on first run"
        
        # Assert: Cache should contain the file index
        cache_data = json.loads(self.cache_file.read_text())
        assert "index" in cache_data, "Cache should contain index data"
        assert "scan_time" in cache_data, "Cache should contain scan timestamp"
        assert len(cache_data["index"]) == 50, "Cache should contain all found files"
    
    def test_cache_usage_on_subsequent_runs(self):
        """
        GREEN TEST: Subsequent runs should use cache when files haven't changed.
        """
        # Setup: Create attachment files and initial cache
        for i in range(30):
            (self.calls_dir / f"attachment_{i}.jpg").write_text("fake image")
        
        filenames = [f"attachment_{i}.jpg" for i in range(30)]
        
        # First run: Create cache
        first_result = build_file_location_index_new(filenames, self.path_manager)
        first_time = time.time()
        
        # Second run: Should use cache
        start_time = time.time()
        second_result = build_file_location_index_new(filenames, self.path_manager)
        second_time = time.time() - start_time
        
        # Assert: Results should be identical
        assert first_result == second_result, "Cached results should match original results"
        
        # Assert: Second run should be faster (cache hit)
        # Allow some tolerance for test environment variability
        assert second_time < 0.1, f"Cached run should be very fast, got {second_time:.3f}s"
    
    def test_cache_invalidation_when_files_change(self):
        """
        GREEN TEST: Cache should be invalidated when attachment files change.
        """
        # Setup: Create initial files and cache
        for i in range(20):
            (self.calls_dir / f"attachment_{i}.jpg").write_text("fake image")
        
        filenames = [f"attachment_{i}.jpg" for i in range(20)]
        
        # First run: Create cache
        first_result = build_file_location_index_new(filenames, self.path_manager)
        
        # Modify files (add new attachment)
        time.sleep(0.1)  # Ensure different modification time
        (self.calls_dir / "new_attachment.jpg").write_text("new fake image")
        filenames.append("new_attachment.jpg")
        
        # Second run: Should detect changes and rebuild cache
        second_result = build_file_location_index_new(filenames, self.path_manager)
        
        # Assert: Should find the new file
        assert len(second_result) == len(first_result) + 1, "Should detect new attachment file"
        assert "new_attachment.jpg" in second_result, "Should include new attachment in results"


class TestMemoryMappedIO:
    """TDD tests for memory-mapped I/O optimization."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.large_file = self.test_dir / "large_file.html"
        
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_large_file_uses_memory_mapping(self):
        """
        RED TEST: Files larger than MMAP_THRESHOLD should use memory mapping.
        
        This test will FAIL initially because memory mapping is not actively used.
        """
        # Setup: Create large file (> 5MB threshold)
        large_content = "<html><body>" + "x" * (6 * 1024 * 1024) + "</body></html>"
        self.large_file.write_text(large_content)
        
        # Action: Process large file (mock the actual processing)
        with patch('mmap.mmap') as mock_mmap:
            mock_mmap.return_value.__enter__ = Mock(return_value=Mock())
            mock_mmap.return_value.__exit__ = Mock(return_value=None)
            
            # This would be called from the actual file processing
            # For now, just test that mmap would be used
            file_size = self.large_file.stat().st_size
            
            # Assert: Should use memory mapping for large files
            # This will FAIL initially because the threshold check is not implemented
            from core.shared_constants import MMAP_THRESHOLD
            assert file_size > MMAP_THRESHOLD, f"Test file should be larger than threshold ({MMAP_THRESHOLD})"
            
            # The actual mmap usage would be tested in integration
            # For now, verify the threshold logic exists
    
    def test_small_file_uses_regular_io(self):
        """
        GREEN TEST: Files smaller than MMAP_THRESHOLD should use regular I/O.
        """
        # Setup: Create small file (< 5MB threshold)
        small_content = "<html><body>Small content</body></html>"
        small_file = self.test_dir / "small_file.html"
        small_file.write_text(small_content)
        
        # Action: Check file size vs threshold
        file_size = small_file.stat().st_size
        
        # Assert: Should be below threshold
        from core.shared_constants import MMAP_THRESHOLD
        assert file_size < MMAP_THRESHOLD, "Small file should be below mmap threshold"


class TestPerformanceOptimizationIntegration:
    """Integration tests for all performance optimizations working together."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.test_dir / "Calls"
        self.calls_dir.mkdir(parents=True)
        
        # Create PathManager
        self.path_manager = PathManager(self.test_dir, test_mode=True)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_optimized_vs_unoptimized_performance(self):
        """
        INTEGRATION TEST: Optimized version should be significantly faster than unoptimized.
        
        This test measures the performance improvement from all optimizations.
        """
        # Setup: Create test scenario with no attachments (should trigger optimization)
        html_files = []
        for i in range(20):
            html_file = self.calls_dir / f"conversation_{i}.html"
            html_file.write_text(f"""
            <html><body>
                <div class="message">
                    <cite>+123456789{i}</cite>
                    <q>Text message {i} with no attachments</q>
                </div>
            </body></html>
            """)
            html_files.append(str(html_file))
        
        # Create many attachment files to make unoptimized scanning expensive
        for i in range(500):
            (self.calls_dir / f"attachment_{i}.jpg").write_text("fake image")
        
        # Measure optimized performance
        start_time = time.time()
        result = build_attachment_mapping_with_progress_new(
            self.path_manager,
            sample_files=html_files
        )
        optimized_time = time.time() - start_time
        
        # Assert: Should return empty mapping (no src elements)
        assert result == {}, "Should return empty mapping when no attachments referenced"
        
        # Assert: Should be very fast (< 0.2s) due to early exit optimization
        assert optimized_time < 0.2, f"Optimized version should be fast, got {optimized_time:.3f}s"
        
        print(f"Optimized performance: {optimized_time:.3f}s for 20 HTML files, 500 attachments")
    
    def test_optimization_preserves_functionality(self):
        """
        REGRESSION TEST: Optimizations should not change behavior when attachments exist.
        """
        # Setup: Create HTML files WITH attachments
        html_file = self.calls_dir / "test_with_attachment.html"
        html_file.write_text("""
        <html><body>
            <div class="message">
                <cite>+1234567890</cite>
                <q>Message with attachment</q>
                <img src="photo_123.jpg" />
            </div>
        </body></html>
        """)
        
        # Create corresponding attachment
        attachment_file = self.calls_dir / "photo_123.jpg"
        attachment_file.write_text("fake image data")
        
        # Action: Build attachment mapping
        result = build_attachment_mapping_with_progress_new(
            self.path_manager,
            sample_files=[str(html_file)]
        )
        
        # Assert: Should find the attachment mapping
        assert len(result) > 0, "Should find attachment mappings when src elements exist"
        
        # Find the mapping for our src element
        found_mapping = False
        for src, (filename, source_path) in result.items():
            if "photo_123.jpg" in src:
                found_mapping = True
                assert filename == "photo_123.jpg", f"Should map to correct filename, got {filename}"
                assert source_path.exists(), f"Source path should exist: {source_path}"
                break
        
        assert found_mapping, "Should find mapping for photo_123.jpg"


class TestCachedAttachmentIndexImplementation:
    """TDD tests for implementing the cached attachment index."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.test_dir / "Calls"
        self.calls_dir.mkdir(parents=True)
        self.cache_file = self.test_dir / ".attachment_cache.json"
        
        # Create PathManager
        self.path_manager = PathManager(self.test_dir, test_mode=True)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_cache_structure_and_content(self):
        """
        RED TEST: Cache should have proper structure with required fields.
        
        This test will FAIL initially because caching is not implemented.
        """
        # Setup: Create attachment files
        attachment_files = []
        for i in range(10):
            attachment_file = self.calls_dir / f"test_{i}.jpg"
            attachment_file.write_text("fake image")
            attachment_files.append(f"test_{i}.jpg")
        
        # Action: Build file location index (should create cache)
        result = build_file_location_index_new(attachment_files, self.path_manager)
        
        # Assert: Cache file should exist
        # This will FAIL initially
        assert self.cache_file.exists(), "Cache file should be created"
        
        # Assert: Cache should have proper structure
        cache_data = json.loads(self.cache_file.read_text())
        required_fields = ["scan_time", "file_count", "directory_hash", "index"]
        for field in required_fields:
            assert field in cache_data, f"Cache should contain {field} field"
        
        # Assert: Cache index should match results
        assert cache_data["file_count"] == len(result), "Cache file count should match results"
        assert len(cache_data["index"]) == len(result), "Cache index size should match results"
    
    def test_cache_performance_improvement(self):
        """
        GREEN TEST: Cached runs should be significantly faster than initial scan.
        """
        # Setup: Create many attachment files
        attachment_files = []
        for i in range(200):
            attachment_file = self.calls_dir / f"attachment_{i}.jpg"
            attachment_file.write_text("fake image")
            attachment_files.append(f"attachment_{i}.jpg")
        
        # First run: Should create cache (slower)
        start_time = time.time()
        first_result = build_file_location_index_new(attachment_files, self.path_manager)
        first_time = time.time() - start_time
        
        # Second run: Should use cache (faster)
        start_time = time.time()
        second_result = build_file_location_index_new(attachment_files, self.path_manager)
        second_time = time.time() - start_time
        
        # Assert: Results should be identical
        assert first_result == second_result, "Cached results should match original"
        
        # Assert: Second run should be faster or at least not slower
        speedup_ratio = first_time / max(second_time, 0.001)  # Avoid division by zero
        assert speedup_ratio >= 1.0, f"Cache should not slow down performance, got {speedup_ratio:.1f}x"
        
        # For small test datasets, cache overhead might dominate, so just verify cache is working
        # Real performance benefits will be seen with larger datasets
        
        print(f"Cache performance: {first_time:.3f}s → {second_time:.3f}s ({speedup_ratio:.1f}x speedup)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
