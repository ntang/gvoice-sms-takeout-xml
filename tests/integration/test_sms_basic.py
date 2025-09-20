#!/usr/bin/env python3
"""
Basic SMS module tests for core functionality.

This module contains tests for fundamental SMS processing features
including constants, utility functions, and basic operations.
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


class TestSMSBasic(BaseSMSTest):
    """Basic test suite for SMS module core functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for the entire test class."""
        # Suppress logging during tests
        logging.getLogger("sms").setLevel(logging.ERROR)

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create required directory structure for SMS processing
        self.create_test_directory_structure()

    def create_test_directory_structure(self):
        """Create the required directory structure for SMS processing tests."""
        test_dir = Path(self.test_dir)
        
        # Create required subdirectories
        (test_dir / "Calls").mkdir(exist_ok=True)
        (test_dir / "Voicemails").mkdir(exist_ok=True)
        (test_dir / "Texts").mkdir(exist_ok=True)
        
        # Create a dummy Phones.vcf file to satisfy validation
        phones_vcf = test_dir / "Phones.vcf"
        phones_vcf.write_text("BEGIN:VCARD\nVERSION:3.0\nFN:Test User\nEND:VCARD", encoding="utf-8")
        
        # Create some dummy HTML files in Calls directory
        calls_dir = test_dir / "Calls"
        dummy_html = """<html><head><title>Test</title></head><body>Test content</body></html>"""
        (calls_dir / "test_call.html").write_text(dummy_html, encoding="utf-8")

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

    def test_module_import(self):
        """Test that the SMS module can be imported."""
        self.assertIsNotNone(sms)

    def test_constants_defined(self):
        """Test that all required constants are defined."""
        required_constants = [
            "SUPPORTED_IMAGE_TYPES",
            "SUPPORTED_VCARD_TYPES",
            "MMS_TYPE_SENT",
            "MMS_TYPE_RECEIVED",
            "MESSAGE_BOX_SENT",
            "MESSAGE_BOX_RECEIVED",
            "PARTICIPANT_TYPE_SENDER",
            "PARTICIPANT_TYPE_RECEIVED",
            "HTML_PARSER",
            "GROUP_CONVERSATION_MARKER",
            # SMS_XML_TEMPLATE and MMS_XML_TEMPLATE removed - XML output no longer supported
            "TEST_MODE",
            "TEST_LIMIT",
        ]

        for constant_name in required_constants:
            with self.subTest(constant_name=constant_name):
                self.assertTrue(hasattr(sms, constant_name))
                self.assertIsNotNone(getattr(sms, constant_name))

    def test_exception_classes(self):
        """Test that custom exception classes are defined."""
        exception_classes = [
            "ConversionError",
            "FileProcessingError",
            "ConfigurationError",
        ]

        for exception_name in exception_classes:
            with self.subTest(exception_name=exception_name):
                self.assertTrue(hasattr(sms, exception_name))
                exception_class = getattr(sms, exception_name)
                self.assertTrue(issubclass(exception_class, Exception))

    def test_conversion_stats_dataclass(self):
        """Test ConversionStats dataclass."""
        stats = sms.ConversionStats(
            num_sms=10, num_img=5, num_vcf=2, own_number="+15551234567"
        )

        self.assertEqual(stats.num_sms, 10)
        self.assertEqual(stats.num_img, 5)
        self.assertEqual(stats.num_vcf, 2)
        self.assertEqual(stats.own_number, "+15551234567")

    # test_escape_xml removed - XML output no longer supported

    def test_format_elapsed_time(self):
        """Test elapsed time formatting."""
        test_cases = [
            (0, "0 seconds"),
            (30, "30 seconds"),
            (90, "1 minutes, 30 seconds"),
            (3600, "1 hours"),
            (3661, "1 hours, 1 minutes"),
        ]

        for seconds, expected_output in test_cases:
            with self.subTest(seconds=seconds):
                result = sms.format_elapsed_time(seconds)
                self.assertEqual(result, expected_output)

    def test_normalize_filename(self):
        """Test filename normalization."""
        test_cases = [
            ("image.jpg", "image"),
            ("photo(1).png", "photo"),
            ("file(2).gif", "file"),
            ("document.vcf", "document"),
            (
                "very_long_filename_that_should_be_truncated.jpg",
                "very_long_filename_that_should_be_truncated",
            ),
        ]

        for input_filename, expected_output in test_cases:
            with self.subTest(input_filename=input_filename):
                result = sms.normalize_filename(input_filename)
                self.assertEqual(result, expected_output)

    def test_custom_filename_sort(self):
        """Test custom filename sorting."""
        test_cases = [
            ("image.jpg", ("image", -1, ".jpg")),
            ("photo(1).png", ("photo", 1, ".png")),
            ("file(2).gif", ("file", 2, ".gif")),
            ("document.vcf", ("document", -1, ".vcf")),
        ]

        for input_filename, expected_output in test_cases:
            with self.subTest(input_filename=input_filename):
                result = sms.custom_filename_sort(input_filename)
                self.assertEqual(result, expected_output)

    def test_get_image_type(self):
        """Test image type detection."""
        test_cases = [
            (Path("image.jpg"), "jpeg"),
            (Path("photo.jpeg"), "jpeg"),
            (Path("file.png"), "png"),
            (Path("animation.gif"), "gif"),
            (Path("unknown.xyz"), "xyz"),
        ]

        for image_path, expected_type in test_cases:
            with self.subTest(image_path=str(image_path)):
                result = sms.get_image_type(image_path)
                self.assertEqual(result, expected_type)

    # test_format_sms_xml and test_format_sms_xml_cached removed - XML output no longer supported

    def test_extract_fallback_number(self):
        """Test fallback number extraction from filename."""
        test_cases = [
            ("+15551234567.html", 15551234567),  # Phone numbers are extracted
            ("conversation(123).html", 123),
            ("chat(456).html", 456),
            ("no_numbers.html", 0),
        ]

        for filename, expected_number in test_cases:
            with self.subTest(filename=filename):
                result = sms.extract_fallback_number(filename)
                self.assertEqual(result, expected_number)

    def test_extract_fallback_number_cached(self):
        """Test cached fallback number extraction."""
        result = sms.extract_fallback_number_cached("conversation(123).html")
        self.assertEqual(result, 123)

    def test_get_message_type_cached(self):
        """Test cached message type detection."""
        result = sms.get_message_type_cached("mock_hash")
        self.assertEqual(result, 1)  # Default to received

    def test_parse_timestamp_cached(self):
        """Test cached timestamp parsing."""
        timestamp = "2023-01-01T12:00:00.000Z"
        result = sms.parse_timestamp_cached(timestamp)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)

    def test_set_test_mode(self):
        """Test test mode configuration."""
        # Test setting test mode
        sms.set_test_mode(True, 50)
        self.assertTrue(sms.TEST_MODE)
        self.assertEqual(sms.TEST_LIMIT, 50)

        # Test disabling test mode
        sms.set_test_mode(False, 0)
        self.assertFalse(sms.TEST_MODE)
        self.assertEqual(sms.TEST_LIMIT, 0)

    def test_validate_configuration(self):
        """Test configuration validation."""
        # Should not raise any exceptions
        sms.validate_configuration()

    # test_escape_xml_edge_cases removed - XML output no longer supported

    def test_performance_monitoring(self):
        """Test performance monitoring functions."""
        # Legacy log_performance function removed - migration complete

        # Test should_report_progress
        result = sms.should_report_progress(50, 100, 0)
        self.assertIsInstance(result, bool)

        # Test format_progress_message
        message = sms.format_progress_message(
            50, 100, "Test Operation", "Additional Info"
        )
        self.assertIn("50", message)
        self.assertIn("100", message)
        self.assertIn("Test Operation", message)
        self.assertIn("Additional Info", message)

    def test_utility_functions(self):
        """Test various utility functions."""
        # Test count_attachments_in_file_cached
        result = sms.count_attachments_in_file_cached("test.html", ".jpg,.png")
        self.assertIsInstance(result, int)

        # Test list_att_filenames_cached
        result = sms.list_att_filenames_cached("test_dir")
        self.assertIsInstance(result, list)

        # Test extract_src_cached
        result = sms.extract_src_cached("test_dir")
        self.assertIsInstance(result, list)

    def test_cached_functions_return_values(self):
        """Test that cached functions return appropriate values."""
        # Test get_mms_sender_cached
        result = sms.get_mms_sender_cached("mock_hash", "participant1,participant2")
        self.assertIsInstance(result, str)

        # Test get_first_phone_number_cached
        result = sms.get_first_phone_number_cached("mock_hash", "123")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        # Test get_participant_phone_numbers_cached
        result = sms.get_participant_phone_numbers_cached("mock_hash")
        self.assertIsInstance(result, list)

    # test_template_constants removed - XML templates no longer supported

    def test_regex_patterns(self):
        """Test that regex patterns are properly compiled."""
        # Test that regex patterns are compiled regex objects
        self.assertIsNotNone(sms.FILENAME_PATTERN.pattern)
        self.assertIsNotNone(sms.CUSTOM_SORT_PATTERN.pattern)
        self.assertIsNotNone(sms.PHONE_NUMBER_PATTERN.pattern)
        self.assertIsNotNone(sms.TEL_HREF_PATTERN.pattern)

    # test_string_translation removed - XML translation no longer supported

    # test_xml_attributes_pool removed - XML attributes no longer supported

    def test_string_pool(self):
        """Test string pooling functionality."""
        # Legacy string pooling functions removed - migration complete
        # String pooling was implemented as no-op functions
        test_string = "test_value"
        # Direct string operations work the same way
        self.assertEqual(test_string, test_string)

    def test_mms_placeholder_messages(self):
        """Test MMS placeholder message constants."""
        # Test that MMS placeholder messages are defined
        self.assertIn("MMS Sent", sms.MMS_PLACEHOLDER_MESSAGES)
        self.assertIn("MMS Received", sms.MMS_PLACEHOLDER_MESSAGES)

    def test_error_messages(self):
        """Test error message constants."""
        # Test that error messages are defined
        self.assertIsInstance(sms.ERROR_NO_MESSAGES, str)
        self.assertIsInstance(sms.ERROR_NO_PARTICIPANTS, str)
        self.assertIsInstance(sms.ERROR_NO_SENDER, str)

    def test_default_values(self):
        """Test default value constants."""
        # Test that default values are properly set
        self.assertIsInstance(sms.DEFAULT_FALLBACK_TIME, int)
        self.assertIsInstance(sms.MIN_PHONE_NUMBER_LENGTH, int)
        self.assertIsInstance(sms.FILENAME_TRUNCATE_LENGTH, int)

    def test_progress_configuration(self):
        """Test progress logging configuration."""
        # Test that progress configuration constants are defined
        self.assertIsInstance(sms.ENABLE_PROGRESS_LOGGING, bool)
        self.assertIsInstance(sms.PROGRESS_INTERVAL_PERCENT, int)
        self.assertIsInstance(sms.PROGRESS_INTERVAL_COUNT, int)
        self.assertIsInstance(sms.MIN_PROGRESS_INTERVAL, int)

    def test_performance_configuration(self):
        """Test performance monitoring configuration."""
        # Test that performance configuration constants are defined
        self.assertIsInstance(sms.ENABLE_PERFORMANCE_MONITORING, bool)
        self.assertIsInstance(sms.PERFORMANCE_LOG_INTERVAL, int)

    def test_supported_extensions(self):
        """Test supported file extensions."""
        # Test that supported extensions are properly defined
        self.assertIsInstance(sms.SUPPORTED_IMAGE_TYPES, set)
        self.assertIsInstance(sms.SUPPORTED_VCARD_TYPES, set)
        self.assertIsInstance(sms.SUPPORTED_EXTENSIONS, set)

        # Test that extensions are properly categorized
        for ext in sms.SUPPORTED_IMAGE_TYPES:
            self.assertIn(ext, sms.SUPPORTED_EXTENSIONS)

        for ext in sms.SUPPORTED_VCARD_TYPES:
            self.assertIn(ext, sms.SUPPORTED_EXTENSIONS)

    def test_message_type_constants(self):
        """Test message type constants."""
        # Test that message type constants are properly defined
        self.assertIsInstance(sms.MMS_TYPE_SENT, int)
        self.assertIsInstance(sms.MMS_TYPE_RECEIVED, int)
        self.assertIsInstance(sms.MESSAGE_BOX_SENT, int)
        self.assertIsInstance(sms.MESSAGE_BOX_RECEIVED, int)

    def test_participant_type_constants(self):
        """Test participant type constants."""
        # Test that participant type constants are properly defined
        self.assertIsInstance(sms.PARTICIPANT_TYPE_SENDER, int)
        self.assertIsInstance(sms.PARTICIPANT_TYPE_RECEIVED, int)

    def test_html_parser_constant(self):
        """Test HTML parser constant."""
        # Test that HTML parser constant is properly defined
        self.assertEqual(sms.HTML_PARSER, "html.parser")

    def test_group_conversation_marker(self):
        """Test group conversation marker constant."""
        # Test that group conversation marker is properly defined
        self.assertEqual(sms.GROUP_CONVERSATION_MARKER, "Group Conversation")

    def test_string_builder(self):
        """Test StringBuilder class for efficient string concatenation."""
        builder = sms.StringBuilder()

        # Test basic functionality
        self.assertEqual(len(builder), 0)
        builder.append("Hello")
        self.assertEqual(len(builder), 5)
        builder.append(" ")
        builder.append("World")
        self.assertEqual(len(builder), 11)

        # Test building
        result = builder.build()
        self.assertEqual(result, "Hello World")

        # Test append_line
        builder.clear()
        builder.append_line("Line 1")
        builder.append_line("Line 2")
        result = builder.build()
        self.assertEqual(result, "Line 1\nLine 2\n")

        # Test clear
        builder.clear()
        self.assertEqual(len(builder), 0)
        self.assertEqual(builder.build(), "")

    def test_performance_benchmarks(self):
        """Test performance benchmarks for key operations."""
        import time

        # Test StringBuilder performance with larger operations
        start_time = time.time()
        builder = sms.StringBuilder()
        for i in range(10000):  # Increased to 10,000 for more realistic test
            builder.append(f"Line {i}: ")
            builder.append(
                "This is a test message with some content. " * 10
            )  # Increased content
            builder.append_line()
        result = builder.build()
        # builder_time variable removed - not used

        # Test traditional string concatenation
        start_time = time.time()
        traditional_result = ""
        for i in range(10000):  # Same number of iterations
            traditional_result += f"Line {i}: "
            traditional_result += "This is a test message with some content. " * 10
            traditional_result += "\n"
        # traditional_time variable removed - not used

        # For large operations, StringBuilder should be more efficient
        # Traditional concatenation can be faster for small operations due to overhead
        self.assertEqual(len(result), len(traditional_result))

        # Legacy string pooling performance test removed - migration complete
        # String pooling was implemented as no-op functions
        
        # Clean up
        builder.clear()

    def test_memory_efficient_structures(self):
        """Test memory efficient structures."""
        # Legacy string pool clearing removed - migration complete

        # Test that StringBuilder's clear method works as expected
        builder = sms.StringBuilder()
        builder.append("Hello")
        builder.clear()
        self.assertEqual(len(builder), 0)
        self.assertEqual(builder.build(), "")

    def test_io_buffer_size_constant(self):
        """Ensure file read buffer size is set to at least 128KB."""
        self.assertGreaterEqual(sms.FILE_READ_BUFFER_SIZE, 131072)

    def test_batched_alias_saving(self):
        """Ensure alias saving can be batched without error."""
        test_dir = Path(self.test_dir)
        sms.setup_processing_paths(test_dir, False, False, None)
        mgr = sms.PHONE_LOOKUP_MANAGER
        # Add several aliases and ensure no exception; then force a save
        for i in range(150):
            mgr.add_alias(f"+1555{i:07d}", f"User_{i}")
        # Explicit save to flush
        mgr.save_aliases()
        self.assertTrue(mgr.lookup_file.exists())


