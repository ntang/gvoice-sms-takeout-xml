#!/usr/bin/env python3
"""
Advanced SMS module tests for enhanced functionality.

This module contains tests for advanced SMS processing features
including message parsing, time extraction, and number formatting.
"""

import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil
import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
import phonenumbers
from bs4 import BeautifulSoup
import logging
import dateutil.parser
import sms

# Add the current directory to the path so we can import sms
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.base_test import BaseSMSTest


class TestSMSAdvanced(BaseSMSTest):
    """Advanced test suite for SMS module functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for the entire test class."""
        # Suppress logging during tests
        logging.getLogger("sms").setLevel(logging.ERROR)

        # Create test constants once
        cls.test_phone_number = "+15551234567"
        cls.test_timestamp = "2023-01-01T12:00:00.000Z"
        cls.test_message = "Hello, world!"

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up after each test method."""
        # Reset SMS module global variables to allow fresh setup in next test
        import sms
        from core import shared_constants
        # Reset all global variables
        shared_constants.PROCESSING_DIRECTORY = None
        shared_constants.OUTPUT_DIRECTORY = None
        shared_constants.LOG_FILENAME = None
        
        # Clear manager internal state before resetting
        if shared_constants.CONVERSATION_MANAGER:
            try:
                # Clear internal state if the manager has cleanup methods
                if hasattr(shared_constants.CONVERSATION_MANAGER, 'conversation_files'):
                    shared_constants.CONVERSATION_MANAGER.conversation_files.clear()
                if hasattr(shared_constants.CONVERSATION_MANAGER, 'conversation_stats'):
                    shared_constants.CONVERSATION_MANAGER.conversation_stats.clear()
                if hasattr(shared_constants.CONVERSATION_MANAGER, 'message_buffer'):
                    shared_constants.CONVERSATION_MANAGER.message_buffer.clear()
            except Exception:
                pass  # Ignore cleanup errors
        
        if shared_constants.PHONE_LOOKUP_MANAGER:
            try:
                # Clear phone lookup manager state
                if hasattr(shared_constants.PHONE_LOOKUP_MANAGER, 'phone_aliases'):
                    shared_constants.PHONE_LOOKUP_MANAGER.phone_aliases.clear()
            except Exception:
                pass  # Ignore cleanup errors
        
        shared_constants.CONVERSATION_MANAGER = None
        shared_constants.PHONE_LOOKUP_MANAGER = None
        shared_constants.PATH_MANAGER = None
        shared_constants.LIMITED_HTML_FILES = None
        # Reset filtering configuration
        shared_constants.DATE_FILTER_OLDER_THAN = None
        shared_constants.DATE_FILTER_NEWER_THAN = None
        shared_constants.FILTER_NUMBERS_WITHOUT_ALIASES = False
        shared_constants.FILTER_NON_PHONE_NUMBERS = False
        shared_constants.FULL_RUN = False
        shared_constants.TEST_MODE = False
        shared_constants.TEST_LIMIT = 100
        
        # Clear all LRU caches to prevent test interference
        sms.extract_src_cached.cache_clear()
        sms.list_att_filenames_cached.cache_clear()
        sms.normalize_filename.cache_clear()
        sms.src_to_filename_mapping_cached.cache_clear()
        sms.build_attachment_mapping_cached.cache_clear()
        sms.count_attachments_in_file_cached.cache_clear()
        sms.extract_fallback_number_cached.cache_clear()
        sms.search_fallback_numbers_cached.cache_clear()
        sms.get_message_type_cached.cache_clear()
        sms.get_mms_sender_cached.cache_clear()
        sms.get_first_phone_number_cached.cache_clear()
        sms.get_participant_phone_numbers_cached.cache_clear()
        sms.parse_timestamp_cached.cache_clear()
        # sms.build_attachment_xml_part_cached.cache_clear()  # Function removed - only HTML output supported
        sms.get_image_type.cache_clear()
        sms.encode_file_content.cache_clear()
        
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_get_message_type(self):
        """Test message type detection."""
        # Create a mock BeautifulSoup message
        mock_message = Mock()
        mock_cite = Mock()
        mock_span = Mock()

        # Test received message (cite text is not "Me")
        mock_message.cite = mock_cite
        mock_cite.text = "John Doe"  # Not "Me"
        mock_cite.span = mock_span
        result = sms.get_message_type(mock_message)
        self.assertEqual(result, 1)  # received

        # Test sent message (cite text is "Me")
        mock_cite.text = "Me"  # This indicates a sent message
        mock_cite.span = None
        result = sms.get_message_type(mock_message)
        self.assertEqual(result, 2)  # sent

    def test_get_message_text(self):
        """Test message text extraction."""
        # Create a mock BeautifulSoup message with q tag
        mock_message = Mock()
        mock_q = Mock()

        # Mock the find method to return a q tag mock
        mock_message.find.return_value = mock_q

        # Mock the string representation of the q tag
        mock_q.__str__ = Mock(return_value="<q>Hello, world!</q>")

        result = sms.get_message_text(mock_message)
        self.assertEqual(result, "Hello, world!")

    def test_get_time_unix(self):
        """Test timestamp conversion to Unix milliseconds."""
        # Create a mock BeautifulSoup message with time element
        mock_message = Mock()
        mock_time = Mock()
        # Set up the attrs attribute as a dictionary-like object
        mock_time.attrs = {"title": "2023-01-01T12:00:00.000Z"}
        # Set up dictionary-style access for the title attribute
        mock_time.__getitem__ = Mock(
            side_effect=lambda key: {"title": "2023-01-01T12:00:00.000Z"}[key]
        )
        # Also set up the get method for compatibility
        mock_time.get.return_value = "2023-01-01T12:00:00.000Z"

        mock_message.find.return_value = mock_time

        result = sms.get_time_unix(mock_message)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_format_number(self):
        """Test phone number formatting."""
        # Create a mock PhoneNumber object
        mock_phone = Mock()
        mock_phone.__str__ = Mock(return_value="+15551234567")

        # Mock the phonenumbers.format_number function
        with patch("sms.phonenumbers.format_number") as mock_format:
            mock_format.return_value = "+15551234567"
            result = sms.format_number(mock_phone)
            self.assertEqual(result, "+15551234567")


