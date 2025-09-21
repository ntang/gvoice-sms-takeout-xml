"""
Test suite for refactoring process_html_files() function.

This test suite follows the TDD approach used successfully for get_limited_file_list():
1. RED: Write failing tests for new parameter-based function
2. GREEN: Implement function to make tests pass  
3. REFACTOR: Improve edge case handling and performance

The goal is to create a parameter-based version of process_html_files() that eliminates
global variable dependencies while preserving identical behavior.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Optional, Any

# Import the functions we're testing
from sms import process_html_files
from core.processing_config import ProcessingConfig
from core.processing_context import ProcessingContext


class TestProcessHtmlFilesRefactor:
    """Test suite for process_html_files() refactoring using TDD approach."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.processing_dir = Path(self.temp_dir)
        self.calls_dir = self.processing_dir / "Calls"
        self.calls_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test HTML files
        self.test_files = []
        for i in range(5):
            test_file = self.calls_dir / f"test_file_{i}.html"
            test_file.write_text(f"<html>Test content {i}</html>")
            self.test_files.append(test_file)
        
        # Create mock managers
        self.mock_conversation_manager = Mock()
        self.mock_phone_lookup_manager = Mock()
        
        # Create test configuration
        self.config = ProcessingConfig(
            processing_dir=self.processing_dir,
            test_mode=False,
            test_limit=100
        )
        
        # Create mock path manager
        self.mock_path_manager = Mock()
        
        # Create test context
        self.context = ProcessingContext(
            config=self.config,
            conversation_manager=self.mock_conversation_manager,
            phone_lookup_manager=self.mock_phone_lookup_manager,
            path_manager=self.mock_path_manager,
            processing_dir=self.processing_dir,
            output_dir=self.processing_dir / "conversations",
            log_filename="test.log"
        )
        
        # Create test filename map
        self.src_filename_map = {
            str(f): f"conversation_{i}" 
            for i, f in enumerate(self.test_files)
        }
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_html_files_current_behavior(self):
        """Test that the current process_html_files() function still works correctly."""
        # This test ensures we don't break existing functionality
        with patch('sms.PROCESSING_DIRECTORY', self.processing_dir), \
             patch('sms.CONVERSATION_MANAGER', self.mock_conversation_manager), \
             patch('sms.PHONE_LOOKUP_MANAGER', self.mock_phone_lookup_manager), \
             patch('sms.process_single_html_file') as mock_process_single:
            
            # Mock the single file processing to return consistent stats
            mock_process_single.return_value = {
                "num_sms": 1,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": "+1234567890"
            }
            
            # Call the current function
            stats = process_html_files(self.src_filename_map, self.config, self.context)
            
            # Verify it returns the expected structure
            assert isinstance(stats, dict)
            assert "num_sms" in stats
            assert "num_img" in stats
            assert "num_vcf" in stats
            assert "num_calls" in stats
            assert "num_voicemails" in stats
            
            # Verify it processed the expected number of files
            assert mock_process_single.call_count == len(self.test_files)
    
    def test_process_html_files_param_behavior(self):
        """Test that the new parameter-based process_html_files_param() function works correctly."""
        # This test will fail initially (RED phase) until we implement the function
        
        # Import the new function (we'll implement this)
        from sms import process_html_files_param
        
        with patch('sms.process_single_html_file') as mock_process_single:
            # Mock the single file processing
            mock_process_single.return_value = {
                "num_sms": 1,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": "+1234567890"
            }
            
            # Call the new parameter-based function
            stats = process_html_files_param(
                processing_dir=self.processing_dir,
                src_filename_map=self.src_filename_map,
                conversation_manager=self.mock_conversation_manager,
                phone_lookup_manager=self.mock_phone_lookup_manager,
                config=self.config,
                context=self.context
            )
            
            # Verify it returns the expected structure
            assert isinstance(stats, dict)
            assert "num_sms" in stats
            assert "num_img" in stats
            assert "num_vcf" in stats
            assert "num_calls" in stats
            assert "num_voicemails" in stats
            
            # Verify it processed the expected number of files
            assert mock_process_single.call_count == len(self.test_files)
    
    def test_process_html_files_equivalence(self):
        """Test that both functions produce equivalent results."""
        # This test ensures behavior preservation
        
        with patch('sms.PROCESSING_DIRECTORY', self.processing_dir), \
             patch('sms.CONVERSATION_MANAGER', self.mock_conversation_manager), \
             patch('sms.PHONE_LOOKUP_MANAGER', self.mock_phone_lookup_manager), \
             patch('sms.process_single_html_file') as mock_process_single:
            
            # Mock consistent behavior for both calls
            mock_process_single.return_value = {
                "num_sms": 1,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": "+1234567890"
            }
            
            # Call both functions
            stats_current = process_html_files(self.src_filename_map, self.config, self.context)
            call_count_after_current = mock_process_single.call_count
            
            # Reset mock for second call
            mock_process_single.reset_mock()
            mock_process_single.return_value = {
                "num_sms": 1,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": "+1234567890"
            }
            
            # Import and call the new function
            from sms import process_html_files_param
            stats_param = process_html_files_param(
                processing_dir=self.processing_dir,
                src_filename_map=self.src_filename_map,
                conversation_manager=self.mock_conversation_manager,
                phone_lookup_manager=self.mock_phone_lookup_manager,
                config=self.config,
                context=self.context
            )
            call_count_after_param = mock_process_single.call_count
            
            # Verify equivalent results
            assert stats_current == stats_param
            # Each function should process the same number of files
            assert call_count_after_current == len(self.test_files)
            assert call_count_after_param == len(self.test_files)
    
    def test_process_html_files_performance(self):
        """Test that the new function has similar or better performance."""
        import time
        
        with patch('sms.process_single_html_file') as mock_process_single:
            # Mock fast processing
            mock_process_single.return_value = {
                "num_sms": 1,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": "+1234567890"
            }
            
            # Time the new function
            start_time = time.time()
            
            from sms import process_html_files_param
            stats = process_html_files_param(
                processing_dir=self.processing_dir,
                src_filename_map=self.src_filename_map,
                conversation_manager=self.mock_conversation_manager,
                phone_lookup_manager=self.mock_phone_lookup_manager,
                config=self.config,
                context=self.context
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify it completes in reasonable time (< 1 second for test data)
            assert execution_time < 1.0
            assert isinstance(stats, dict)
    
    def test_process_html_files_edge_cases(self):
        """Test edge cases for the new function."""
        
        # Test with empty directory
        empty_dir = Path(tempfile.mkdtemp())
        empty_calls_dir = empty_dir / "Calls"
        empty_calls_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            from sms import process_html_files_param
            
            stats = process_html_files_param(
                processing_dir=empty_dir,
                src_filename_map={},
                conversation_manager=self.mock_conversation_manager,
                phone_lookup_manager=self.mock_phone_lookup_manager,
                config=self.config,
                context=self.context
            )
            
            # Should return empty stats
            assert stats["num_sms"] == 0
            assert stats["num_img"] == 0
            assert stats["num_vcf"] == 0
            assert stats["num_calls"] == 0
            assert stats["num_voicemails"] == 0
            
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)
        
        # Test with non-existent directory - should return empty stats, not raise error
        non_existent_dir = Path("/non/existent/directory")
        
        from sms import process_html_files_param
        stats = process_html_files_param(
            processing_dir=non_existent_dir,
            src_filename_map={},
            conversation_manager=self.mock_conversation_manager,
            phone_lookup_manager=self.mock_phone_lookup_manager,
            config=self.config,
            context=self.context
        )
        
        # Should return empty stats for non-existent directory
        assert stats["num_sms"] == 0
        assert stats["num_img"] == 0
        assert stats["num_vcf"] == 0
        assert stats["num_calls"] == 0
        assert stats["num_voicemails"] == 0
    
    def test_process_html_files_test_mode(self):
        """Test that the new function handles test mode correctly."""
        
        # Create test mode configuration
        test_config = ProcessingConfig(
            processing_dir=self.processing_dir,
            test_mode=True,
            test_limit=3
        )
        
        test_context = ProcessingContext(
            config=test_config,
            conversation_manager=self.mock_conversation_manager,
            phone_lookup_manager=self.mock_phone_lookup_manager,
            path_manager=self.mock_path_manager,
            processing_dir=self.processing_dir,
            output_dir=self.processing_dir / "conversations",
            log_filename="test.log"
        )
        
        with patch('sms.process_single_html_file') as mock_process_single:
            mock_process_single.return_value = {
                "num_sms": 1,
                "num_img": 0,
                "num_vcf": 0,
                "num_calls": 0,
                "num_voicemails": 0,
                "own_number": "+1234567890"
            }
            
            from sms import process_html_files_param
            
            # Test with limited file list (simulating test mode)
            limited_files = self.test_files[:3]  # Only first 3 files
            
            stats = process_html_files_param(
                processing_dir=self.processing_dir,
                src_filename_map=self.src_filename_map,
                conversation_manager=self.mock_conversation_manager,
                phone_lookup_manager=self.mock_phone_lookup_manager,
                config=test_config,
                context=test_context,
                limited_files=limited_files  # New parameter for test mode
            )
            
            # Should only process the limited number of files
            assert mock_process_single.call_count == 3
            assert isinstance(stats, dict)
    
    def test_process_html_files_batch_processing(self):
        """Test that the new function handles batch processing correctly."""
        
        # Create many files to trigger batch processing
        large_calls_dir = Path(tempfile.mkdtemp()) / "Calls"
        large_calls_dir.mkdir(parents=True, exist_ok=True)
        
        large_files = []
        for i in range(10):  # Create 10 files to test batching
            test_file = large_calls_dir / f"large_test_{i}.html"
            test_file.write_text(f"<html>Large test content {i}</html>")
            large_files.append(test_file)
        
        large_src_map = {
            str(f): f"large_conversation_{i}" 
            for i, f in enumerate(large_files)
        }
        
        try:
            with patch('sms.process_html_files_batch') as mock_batch_process:
                mock_batch_process.return_value = {
                    "num_sms": 10,
                    "num_img": 0,
                    "num_vcf": 0,
                    "num_calls": 0,
                    "num_voicemails": 0
                }
                
                from sms import process_html_files_param
                
                # Use a lower threshold to trigger batch processing
                stats = process_html_files_param(
                    processing_dir=large_calls_dir.parent,
                    src_filename_map=large_src_map,
                    conversation_manager=self.mock_conversation_manager,
                    phone_lookup_manager=self.mock_phone_lookup_manager,
                    config=self.config,
                    context=self.context,
                    large_dataset_threshold=5  # Lower threshold to trigger batching
                )
                
                # Should use batch processing for large datasets
                mock_batch_process.assert_called_once()
                assert stats["num_sms"] == 10
                
        finally:
            shutil.rmtree(large_calls_dir.parent, ignore_errors=True)
    
    def test_process_html_files_error_handling(self):
        """Test error handling in the new function."""
        
        with patch('sms.process_single_html_file') as mock_process_single:
            # Mock an error for one file
            def mock_process_side_effect(*args, **kwargs):
                if "test_file_2" in str(args[0]):
                    raise Exception("Simulated processing error")
                return {
                    "num_sms": 1,
                    "num_img": 0,
                    "num_vcf": 0,
                    "num_calls": 0,
                    "num_voicemails": 0,
                    "own_number": "+1234567890"
                }
            
            mock_process_single.side_effect = mock_process_side_effect
            
            from sms import process_html_files_param
            
            # Should handle errors gracefully and continue processing
            stats = process_html_files_param(
                processing_dir=self.processing_dir,
                src_filename_map=self.src_filename_map,
                conversation_manager=self.mock_conversation_manager,
                phone_lookup_manager=self.mock_phone_lookup_manager,
                config=self.config,
                context=self.context
            )
            
            # Should still process other files despite the error
            assert mock_process_single.call_count == len(self.test_files)
            assert isinstance(stats, dict)
            # Should have processed 4 files successfully (5 total - 1 error)
            assert stats["num_sms"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])