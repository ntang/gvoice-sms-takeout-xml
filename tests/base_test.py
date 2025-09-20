#!/usr/bin/env python3
"""
Base test class for SMS module tests with proper isolation.

This module provides a standardized base class that ensures proper test isolation
by clearing global state before and after each test.
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from typing import Optional
import pytest

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sms
from core import shared_constants


class BaseSMSTest(unittest.TestCase):
    """
    Base test class that provides proper isolation for SMS tests.
    
    This class ensures that each test runs in a clean environment by:
    1. Creating a temporary directory for each test
    2. Clearing all global state before and after each test
    3. Providing standard setup and teardown methods
    """
    
    # Default markers for all tests using this base class
    pytestmark = [
        pytest.mark.integration,
        pytest.mark.isolation
    ]
    
    def setUp(self):
        """Set up test environment with complete isolation."""
        # Create a temporary directory for this test
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        
        # Change to test directory
        os.chdir(self.test_dir)
        
        # Create required directory structure for SMS processing
        self._create_test_directory_structure()
        
        # Clear all global state
        self._clear_global_state()
        
    def tearDown(self):
        """Clean up test environment and restore global state."""
        # Restore global state
        self._restore_global_state()
        
        # Change back to original directory
        os.chdir(self.original_cwd)
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_directory_structure(self):
        """Create the required directory structure for SMS processing tests."""
        test_dir = self.test_dir
        
        # Create required subdirectories
        (test_dir / "Calls").mkdir(exist_ok=True)
        (test_dir / "Voicemails").mkdir(exist_ok=True)
        (test_dir / "Texts").mkdir(exist_ok=True)
        (test_dir / "conversations").mkdir(exist_ok=True)  # Add conversations directory
        
        # Create a dummy Phones.vcf file to satisfy validation
        phones_vcf = test_dir / "Phones.vcf"
        phones_vcf.write_text("BEGIN:VCARD\nVERSION:3.0\nFN:Test User\nEND:VCARD", encoding="utf-8")
        
        # Create some dummy HTML files in Calls directory
        calls_dir = test_dir / "Calls"
        dummy_html = """<html><head><title>Test</title></head><body>Test content</body></html>"""
        (calls_dir / "test_call.html").write_text(dummy_html, encoding="utf-8")
    
    def _clear_global_state(self):
        """Clear all global state for test isolation."""
        # Clear SMS module globals
        sms.PROCESSING_DIRECTORY = None
        sms.OUTPUT_DIRECTORY = None
        sms.CONVERSATION_MANAGER = None
        sms.PHONE_LOOKUP_MANAGER = None
        sms.PATH_MANAGER = None
        sms.LIMITED_HTML_FILES = None
        sms.INCLUDE_SERVICE_CODES = False
        sms.FILTER_NON_PHONE_NUMBERS = False
        
        # Clear shared constants globals
        shared_constants.PROCESSING_DIRECTORY = None
        shared_constants.OUTPUT_DIRECTORY = None
        shared_constants.CONVERSATION_MANAGER = None
        shared_constants.PHONE_LOOKUP_MANAGER = None
        shared_constants.PATH_MANAGER = None
        shared_constants.LIMITED_HTML_FILES = None
        shared_constants.INCLUDE_SERVICE_CODES = False
        shared_constants.FILTER_NON_PHONE_NUMBERS = False
        
        # Clear LRU caches
        try:
            if hasattr(sms, 'get_time_unix_cached'):
                sms.get_time_unix_cached.cache_clear()
            if hasattr(sms, 'get_time_formatted_cached'):
                sms.get_time_formatted_cached.cache_clear()
            if hasattr(sms, 'extract_phone_numbers_cached'):
                sms.extract_phone_numbers_cached.cache_clear()
            if hasattr(sms, 'get_conversation_id_cached'):
                sms.get_conversation_id_cached.cache_clear()
        except Exception:
            pass  # Ignore cache clearing errors
    
    def _restore_global_state(self):
        """Restore global state after test."""
        # Clear manager internal states if they exist
        if sms.CONVERSATION_MANAGER:
            try:
                if hasattr(sms.CONVERSATION_MANAGER, 'conversation_files'):
                    sms.CONVERSATION_MANAGER.conversation_files.clear()
                if hasattr(sms.CONVERSATION_MANAGER, 'conversation_stats'):
                    sms.CONVERSATION_MANAGER.conversation_stats.clear()
                if hasattr(sms.CONVERSATION_MANAGER, 'message_buffer'):
                    sms.CONVERSATION_MANAGER.message_buffer.clear()
            except Exception:
                pass
        
        if sms.PHONE_LOOKUP_MANAGER:
            try:
                if hasattr(sms.PHONE_LOOKUP_MANAGER, 'phone_aliases'):
                    sms.PHONE_LOOKUP_MANAGER.phone_aliases.clear()
            except Exception:
                pass
    
    def create_test_phone_lookup_file(self, aliases: Optional[dict] = None) -> Path:
        """Create a test phone lookup file with optional aliases."""
        if aliases is None:
            aliases = {
                "+15551234567": "Test User",
                "+15559876543": "Another User"
            }
        
        lookup_file = self.test_dir / "phone_lookup.txt"
        with open(lookup_file, 'w') as f:
            for phone, alias in aliases.items():
                f.write(f"{phone}|{alias}\n")
        
        return lookup_file
    
    def create_test_html_file(self, content: str, filename: str = "test.html") -> Path:
        """Create a test HTML file with given content."""
        html_file = self.test_dir / filename
        with open(html_file, 'w') as f:
            f.write(content)
        return html_file
