"""
Test Suite for File Selection Fix

This module tests the file selection functionality to ensure get_limited_file_list
scans the correct directory (Calls) instead of the output directory (conversations).
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.append('.')

from sms import get_limited_file_list


class TestFileSelectionFix:
    """Test suite for file selection functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Create directory structure
        self.calls_dir = self.test_dir / "Calls"
        self.conversations_dir = self.test_dir / "conversations"
        self.calls_dir.mkdir(parents=True)
        self.conversations_dir.mkdir(parents=True)
        
        # Create test files in Calls directory (input files)
        self.create_test_file(self.calls_dir / "Test1 - Text - 2023-06-15T12_00_00Z.html", "2023 input file")
        self.create_test_file(self.calls_dir / "Test2 - Text - 2023-06-16T12_00_00Z.html", "2023 input file 2")
        
        # Create test files in conversations directory (output files - should NOT be selected)
        self.create_test_file(self.conversations_dir / "OldOutput.html", "old output file")
        self.create_test_file(self.conversations_dir / "SusanT.html", "processed output file")
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def create_test_file(self, filepath: Path, content: str):
        """Helper to create a test file with content."""
        filepath.write_text(content)
    
    def test_get_limited_file_list_scans_correct_directory(self):
        """
        TEST: get_limited_file_list should scan Calls directory, not output directory.
        
        This is the failing test that will drive our file selection fix.
        Currently FAILS because function scans entire PROCESSING_DIRECTORY.
        """
        with patch('sms.PROCESSING_DIRECTORY', self.test_dir):
            limited_files = get_limited_file_list(2)
            
            # Verify we got some files
            assert len(limited_files) > 0, "Should find some files"
            
            # Verify all selected files are from Calls directory
            for file_path in limited_files:
                assert "Calls" in str(file_path), f"File {file_path} not from Calls directory"
                assert "conversations" not in str(file_path), f"File {file_path} incorrectly from output directory"
                assert file_path.exists(), f"Selected file {file_path} should exist"
    
    def test_file_selection_limit_respected(self):
        """Test that the limit parameter is respected."""
        with patch('sms.PROCESSING_DIRECTORY', self.test_dir):
            limited_files = get_limited_file_list(1)
            assert len(limited_files) <= 1, f"Should respect limit of 1, but got {len(limited_files)} files"
